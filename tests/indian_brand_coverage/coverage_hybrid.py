#!/usr/bin/env python3
"""
Hybrid coverage report for cdss-drug-info.

Part 1 — SQL  : Full 359k breakdown by match_combination (resolver coverage).
                Runs the saved SQL in queries/resolver_coverage_by_match_combination.sql
                Takes ~30 seconds.

Part 2 — HTTP : Spot-check 50 drugs per match_combination × all 4 endpoint suites
                (resolver, label, interactions, population) in parallel.
                Takes ~5-8 minutes.

Usage:
    python3 tests/indian_brand_coverage/coverage_hybrid.py
    python3 tests/indian_brand_coverage/coverage_hybrid.py --sample 100
"""
import argparse
import asyncio
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import aiohttp
import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

DB_URL   = os.environ["DATABASE_URL"]
BASE_URL = os.environ.get("DRUG_INFO_BASE_URL", "http://34.14.197.45:8002")
API_KEY  = os.environ.get("API_KEY", "dev")

CONCURRENCY = 30   # higher than full run — small sample so server handles it fine

# ── Endpoint suites ───────────────────────────────────────────────────────────

SUITES = {
    "resolver": {
        "resolver": "generic-name",
    },
    "label": {
        "contraindications": "contraindications",
        "warnings":          "warnings",
        "mechanism":         "mechanism-of-action",
        "indications":       "indications",
        "adverse_reactions": "adverse-reactions",
        "drug_description":  "drug-description",
        "microbiology":      "microbiology",
        "patient_info":      "patient-info",
    },
    "interactions": {
        "interactions":      "interactions",
        "food_interactions": "food-interactions",
        "ingredients":       "ingredients",
        "drug_classes":      "drug-classes",
        "products":          "products",
    },
    "population": {
        "neonate":   "population-info?age=0",
        "infant":    "population-info?age=1",
        "pediatric": "population-info?age=10",
        "adult":     "population-info?age=30",
        "geriatric": "population-info?age=70",
    },
}

# ── SQL ───────────────────────────────────────────────────────────────────────

COVERAGE_SQL = (
    Path(__file__).resolve().parent.parent.parent
    / "queries" / "resolver_coverage_by_match_combination.sql"
).read_text()

SAMPLE_SQL = """
SELECT drug_id_1mg, match_combination
FROM (
    SELECT drug_id_1mg, match_combination,
           ROW_NUMBER() OVER (PARTITION BY match_combination ORDER BY RANDOM()) AS rn
    FROM drugdb.indian_brand
    WHERE drug_id_1mg IS NOT NULL
) ranked
WHERE rn <= $1
ORDER BY match_combination, drug_id_1mg
"""


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def hit(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url) as r:
            if r.status == 200:  return "success"
            if r.status == 404:  return "not_found"
            return "error"
    except Exception:
        return "error"


async def check_drug(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    drug_id: str,
    suite_endpoints: dict[str, str],
) -> dict[str, str]:
    async with sem:
        results = await asyncio.gather(*[
            hit(session, f"{BASE_URL}/api/v1/drug/{drug_id}/{suffix}")
            for suffix in suite_endpoints.values()
        ])
    return dict(zip(suite_endpoints.keys(), results))


# ── Part 1: SQL coverage ──────────────────────────────────────────────────────

async def run_sql_coverage(pool) -> list[dict]:
    print("\n" + "═" * 80)
    print("PART 1 — SQL COVERAGE  (full 359k, ~30 seconds)")
    print("═" * 80)
    t0 = time.perf_counter()
    async with pool.acquire() as conn:
        rows = await conn.fetch(COVERAGE_SQL)
    elapsed = time.perf_counter() - t0

    print(f"\n{'match_combination':<22} {'total':>9} {'primary':>9} {'fallback':>9} {'either':>9} {'no_results':>11} {'coverage':>10}")
    print("─" * 82)
    for r in rows:
        print(
            f"{r['match_combination']:<22}"
            f"{r['total_drugs']:>9}"
            f"{r['primary_hits']:>9}"
            f"{r['fallback_hits']:>9}"
            f"{r['either_path']:>9}"
            f"{r['no_results']:>11}"
            f"{r['coverage %']:>10}"
        )
    print(f"\n  SQL completed in {elapsed:.1f}s")
    return [dict(r) for r in rows]


# ── Part 2: HTTP spot-check ───────────────────────────────────────────────────

async def run_http_spotcheck(pool, sample_per_combo: int) -> dict:
    print("\n" + "═" * 80)
    print(f"PART 2 — HTTP SPOT-CHECK  ({sample_per_combo} drugs per match_combination × 4 suites)")
    print("═" * 80)

    async with pool.acquire() as conn:
        rows = await conn.fetch(SAMPLE_SQL, sample_per_combo)

    drugs_by_combo: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        drugs_by_combo[r["match_combination"]].append(r["drug_id_1mg"])

    total_drugs   = len(rows)
    total_requests = total_drugs * sum(len(e) for e in SUITES.values())
    print(f"  {total_drugs} drugs sampled  ·  ~{total_requests:,} HTTP requests  ·  {BASE_URL}")

    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY + 10)

    # suite_name → combo → endpoint_name → {success, not_found, error}
    results: dict[str, dict[str, dict[str, dict[str, int]]]] = {
        suite: defaultdict(lambda: defaultdict(lambda: {"success": 0, "not_found": 0, "error": 0}))
        for suite in SUITES
    }

    t0 = time.perf_counter()

    async with aiohttp.ClientSession(
        connector=connector, headers={"X-API-Key": API_KEY}
    ) as session:

        async def process_drug(drug_id: str, combo: str):
            suite_results = await asyncio.gather(*[
                check_drug(session, sem, drug_id, endpoints)
                for endpoints in SUITES.values()
            ])
            for suite_name, ep_results in zip(SUITES.keys(), suite_results):
                for ep_name, status in ep_results.items():
                    results[suite_name][combo][ep_name][status] += 1

        await asyncio.gather(*[
            process_drug(drug_id, combo)
            for combo, drug_ids in drugs_by_combo.items()
            for drug_id in drug_ids
        ])

    elapsed = time.perf_counter() - t0
    print(f"  HTTP spot-check completed in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    return results


# ── Report ────────────────────────────────────────────────────────────────────

def print_spotcheck_report(results: dict):
    print("\n" + "═" * 80)
    print("SPOT-CHECK RESULTS  (success rate per match_combination per endpoint)")
    print("═" * 80)

    for suite_name, combo_data in results.items():
        ep_names = list(SUITES[suite_name].keys())
        print(f"\n  Suite: {suite_name.upper()}")
        header = f"  {'match_combination':<22}" + "".join(f"{ep[:10]:>12}" for ep in ep_names)
        print(header)
        print("  " + "─" * (len(header) - 2))
        for combo in sorted(combo_data):
            row = f"  {combo:<22}"
            for ep in ep_names:
                counts = combo_data[combo][ep]
                total  = sum(counts.values())
                pct    = f"{counts['success']/total*100:.0f}%" if total else "n/a"
                row   += f"{pct:>12}"
            print(row)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(sample_per_combo: int):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 80)
    print(f"HYBRID COVERAGE REPORT — cdss-drug-info — {ts}")
    print(f"  Service  : {BASE_URL}")
    print(f"  Sample   : {sample_per_combo} drugs per match_combination")
    print("=" * 80)

    pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=5, command_timeout=300)
    t_total = time.perf_counter()

    sql_rows    = await run_sql_coverage(pool)
    http_results = await run_http_spotcheck(pool, sample_per_combo)

    await pool.close()

    print_spotcheck_report(http_results)

    print("\n" + "═" * 80)
    print(f"DONE  —  total wall time {time.perf_counter()-t_total:.1f}s  ({(time.perf_counter()-t_total)/60:.1f} min)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=50,
                        help="Drugs per match_combination to HTTP spot-check (default: 50)")
    args = parser.parse_args()
    asyncio.run(main(args.sample))
