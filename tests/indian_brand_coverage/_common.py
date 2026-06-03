"""
Shared helpers and core runner for indian_brand coverage tests.

Hits the live cdss-drug-info API endpoints instead of raw SQL — 100% faithful
to real service behaviour.

Two runner types:
  run_resolver_coverage()  — tests /api/v1/drug/{id}/generic-name (resolver only)
  run_dosing_coverage()    — tests /api/v1/drug/{id}/dosing-regimen?age={age}
                             AGE_GROUP_MAP format: { display_name: representative_age }

Result codes:
  success   ✓  HTTP 200
  not_found ✗  HTTP 404
  error     !  HTTP 5xx or exception
"""
import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Sequence

import aiohttp
import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DB_URL           = os.environ["DATABASE_URL"]
BASE_URL         = os.environ.get("DRUG_INFO_BASE_URL", "http://34.14.197.45:8002")
API_KEY          = os.environ.get("API_KEY", "dev")
CONCURRENCY      = 20

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)

RESULTS = ("success", "not_found", "error")
ICONS   = {"success": "✓", "not_found": "✗", "error": "!"}

FETCH_ALL_DRUGS_SQL = """
SELECT
    drug_id_1mg,
    MIN(brand_name)  AS brand_name,
    STRING_AGG(DISTINCT match_combination, ', ' ORDER BY match_combination) AS match_combinations
FROM drugdb.indian_brand
WHERE drug_id_1mg IS NOT NULL
GROUP BY drug_id_1mg
ORDER BY drug_id_1mg
"""


def _zero() -> dict:
    return {r: 0 for r in RESULTS}


def find_latest_log(label: str) -> Path | None:
    candidates = [p for p in LOG_DIR.glob(f"{label}_*.log") if p.stat().st_size > 0]
    return max(candidates, key=lambda p: p.stat().st_size) if candidates else None


def load_prior_results(log_path: Path) -> dict[str, dict]:
    prior: dict[str, dict] = {}
    if not log_path or not log_path.exists():
        return prior
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                rec = json.loads(line)
                drug_id = rec.get("drug_id")
                results = rec.get("results")
                if drug_id and isinstance(results, dict):
                    prior[str(drug_id)] = {
                        "results":            results,
                        "match_combinations": rec.get("match_combinations", "unknown"),
                    }
            except json.JSONDecodeError:
                pass
    return prior


def setup_logging(label: str, log_path: Path) -> logging.Logger:
    logger = logging.getLogger(f"ib.{label}")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = logging.FileHandler(str(log_path), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(fh)
    return logger


async def _hit_endpoint(
    session: aiohttp.ClientSession,
    url: str,
) -> str:
    """Hit a single URL, return 'success' / 'not_found' / 'error'."""
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                return "success"
            if resp.status == 404:
                return "not_found"
            return "error"
    except Exception:
        return "error"


async def _classify_resolver(
    session: aiohttp.ClientSession,
    drug_id: str,
) -> dict[str, str]:
    """Test generic-name — verifies the full resolver flow for this drug."""
    url = f"{BASE_URL}/api/v1/drug/{drug_id}/generic-name"
    return {"resolver": await _hit_endpoint(session, url)}


async def _classify_endpoints(
    session: aiohttp.ClientSession,
    drug_id: str,
    endpoint_map: dict[str, str],
) -> dict[str, str]:
    """Test multiple label/interaction endpoints in parallel."""
    async def check_one(name: str, suffix: str) -> tuple[str, str]:
        url = f"{BASE_URL}/api/v1/drug/{drug_id}/{suffix}"
        return name, await _hit_endpoint(session, url)

    return dict(await asyncio.gather(*[
        check_one(name, suffix) for name, suffix in endpoint_map.items()
    ]))


async def _classify_population(
    session: aiohttp.ClientSession,
    drug_id: str,
    age_group_map: dict[str, int],
) -> dict[str, str]:
    """Test population-info?age=X for each age group in parallel."""
    async def check_one(display_name: str, age: int) -> tuple[str, str]:
        url = f"{BASE_URL}/api/v1/drug/{drug_id}/population-info?age={age}"
        return display_name, await _hit_endpoint(session, url)

    return dict(await asyncio.gather(*[
        check_one(name, age) for name, age in age_group_map.items()
    ]))


# ── Core runner ───────────────────────────────────────────────────────────────

async def run_coverage(
    *,
    label: str,
    mode: str,                           # "resolver" | "endpoints" | "population"
    age_group_map: dict[str, int] | None = None,
    endpoint_map: dict[str, str] | None = None,
    session: aiohttp.ClientSession | None = None,
    drugs: Sequence | None = None,
    resume_log: Path | None = None,
) -> dict:
    """
    For every drug_id_1mg in drugdb.indian_brand, hit the relevant endpoint(s)
    and record stats + per-match_combination breakdown.

    mode="resolver"   → hits /api/v1/drug/{id}/generic-name
    mode="endpoints"  → hits each path in endpoint_map in parallel per drug
    mode="population" → hits /api/v1/drug/{id}/population-info?age=X per age_group_map
    """
    if mode == "endpoints" and not endpoint_map:
        raise ValueError("endpoint_map is required for mode='endpoints'")
    if mode == "population" and not age_group_map:
        raise ValueError("age_group_map is required for mode='population'")

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{label}_{ts}.log"
    logger   = setup_logging(label, log_path)

    own_session = session is None
    if own_session:
        connector = aiohttp.TCPConnector(limit=CONCURRENCY + 4)
        session   = aiohttp.ClientSession(connector=connector, headers={"X-API-Key": API_KEY})

    if drugs is None:
        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=3, command_timeout=30)
        async with pool.acquire() as conn:
            drugs = await conn.fetch(FETCH_ALL_DRUGS_SQL)
        await pool.close()

    total    = len(drugs)
    if mode == "resolver":
        ag_names = ["resolver"]
    elif mode == "endpoints":
        ag_names = list(endpoint_map.keys())
    else:
        ag_names = list(age_group_map.keys())
    sem      = asyncio.Semaphore(CONCURRENCY)
    lock     = asyncio.Lock()

    prior: dict[str, dict] = load_prior_results(resume_log) if resume_log else {}
    skipped = len(prior)

    stats: dict[str, dict[str, int]] = {ag: _zero() for ag in ag_names}
    combo_stats: dict[str, defaultdict] = {ag: defaultdict(_zero) for ag in ag_names}

    for rec in prior.values():
        combos_raw = rec.get("match_combinations", "unknown")
        combo_list = [c.strip() for c in combos_raw.split(",")]
        for ag_name in ag_names:
            result = rec["results"].get(ag_name, "error")
            if result in RESULTS:
                stats[ag_name][result] += 1
                for combo in combo_list:
                    combo_stats[ag_name][combo][result] += 1

    done = [skipped]

    logger.info(f"[{label}]  {total:,} drug_ids  ·  mode={mode}  ·  groups={ag_names}  ·  {BASE_URL}")
    if skipped:
        logger.info(f"[{label}]  (resuming — {skipped:,} done, {total - skipped:,} remaining)")
    logger.info(f"[{label}]  log → {log_path}")
    logger.info("─" * 80)

    async def process(drug_row):
        drug_id    = str(drug_row["drug_id_1mg"])
        combos_raw = drug_row["match_combinations"] or "unknown"
        combo_list = [c.strip() for c in combos_raw.split(",")]

        if drug_id in prior:
            return

        async with sem:
            if mode == "resolver":
                ag_results = await _classify_resolver(session, drug_id)
            elif mode == "endpoints":
                ag_results = await _classify_endpoints(session, drug_id, endpoint_map)
            else:
                ag_results = await _classify_population(session, drug_id, age_group_map)

        async with lock:
            done[0] += 1
            n = done[0]
            for ag_name, result in ag_results.items():
                stats[ag_name][result] += 1
                for combo in combo_list:
                    combo_stats[ag_name][combo][result] += 1

            ag_parts = "  ".join(f"{ag}={ICONS[r]}{r}" for ag, r in ag_results.items())
            logger.info(
                f"[{label}] [{n:5d}/{total}] drug_id={drug_id:<10}| {ag_parts}"
                f"  match=[{combos_raw[:45]}]"
            )
            logger.debug(json.dumps({
                "label":              label,
                "drug_id":            drug_id,
                "brand_name":         drug_row["brand_name"],
                "match_combinations": combos_raw,
                "results":            ag_results,
            }, ensure_ascii=False))

    await asyncio.gather(*[process(d) for d in drugs])

    if own_session:
        await session.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    logger.info("\n" + "═" * 80)
    logger.info(f"[{label}]  SUMMARY  —  {total:,} drug_ids total")

    for ag_name in ag_names:
        s    = stats[ag_name]
        have = s["success"]
        logger.info(f"\n  ┌─ Group : {ag_name}")
        logger.info(f"  │  ✓ success   : {s['success']:6,}  ({s['success']/total*100:.1f}%)")
        logger.info(f"  │  ✗ not_found : {s['not_found']:6,}  ({s['not_found']/total*100:.1f}%)")
        logger.info(f"  │  ! error     : {s['error']:6,}  ({s['error']/total*100:.1f}%)")
        logger.info(f"  └─ COVERAGE    : {have:6,}  ({have/total*100:.1f}%)")

        cs_map = combo_stats[ag_name]
        logger.info(f"\n  Per match_combination  [{ag_name}]:")
        hdr = (
            f"  {'match_combination':<32}"
            f"{'total':>7}{'success':>9}{'not_found':>11}{'error':>7}"
        )
        logger.info(hdr)
        logger.info("  " + "─" * (len(hdr) - 2))
        for combo in sorted(cs_map):
            cs  = cs_map[combo]
            ct  = sum(cs.values())
            pct = cs["success"] / ct * 100 if ct else 0
            logger.info(
                f"  {combo:<32}{ct:>7}{cs['success']:>9}{cs['not_found']:>11}"
                f"{cs['error']:>7}  ({pct:.1f}%)"
            )

    logger.info("\n" + "═" * 80)
    logger.info(f"[{label}]  Full log → {log_path}")
    return stats
