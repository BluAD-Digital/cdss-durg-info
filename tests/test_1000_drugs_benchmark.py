"""
Benchmark all APIs against 1000 random drug_id_1mg values from the indian_brand table.
Skips check-interaction and dosing-regimen (require extra params).
Reports per-endpoint stats: success rate, avg response time, error breakdown.
"""

import asyncio
import time
import random
import json
import sys
from collections import defaultdict
import asyncpg
import aiohttp

BASE_URL = "http://localhost:8002/api/v1"
API_KEY = "dev"
DB_URL = "postgresql://postgres:Blumax%40123@178.236.185.230:5432/postgres"
CONCURRENCY = 20
SAMPLE_SIZE = 1000

ENDPOINTS = [
    "generic-name",
    "indications",
    "contraindications",
    "warnings",
    "mechanism-of-action",
    "adverse-reactions",
    "drug-description",
    "patient-info",
    "population-info",
    "pregnancy-use",
    "specific-populations",
    "products",
    "food-interactions",
    "ingredients",
    "interactions",
    "drug-classes",
    "microbiology",
]


async def fetch_drug_ids() -> list[str]:
    import csv, os
    base = os.path.dirname(__file__)
    ids = []
    for fname in ("top500_coverage_result.csv", "missing_brands.csv"):
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for row in csv.DictReader(f):
                did = row.get("drug_id_1mg", "").strip()
                if did and did.isdigit():
                    ids.append(did)
    ids = list(dict.fromkeys(ids))
    random.shuffle(ids)
    return ids[:SAMPLE_SIZE]


async def call_endpoint(
    session: aiohttp.ClientSession,
    drug_id: str,
    endpoint: str,
    results: dict,
    sem: asyncio.Semaphore,
):
    url = f"{BASE_URL}/drug/{drug_id}/{endpoint}"
    if endpoint == "population-info":
        url += "?age=30"
    async with sem:
        t0 = time.perf_counter()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                body = await resp.json(content_type=None)
                status = resp.status

                if status == 200:
                    results[endpoint]["success"] += 1
                    results[endpoint]["times"].append(elapsed_ms)
                    # Check if data is non-empty
                    if body.get("data") or body.get("success"):
                        results[endpoint]["has_data"] += 1
                elif status == 404:
                    results[endpoint]["not_found"] += 1
                    err = body.get("error_code") or body.get("detail") or "404"
                    results[endpoint]["error_codes"][err] += 1
                else:
                    results[endpoint]["other_errors"] += 1
                    results[endpoint]["error_codes"][str(status)] += 1
        except asyncio.TimeoutError:
            results[endpoint]["timeouts"] += 1
        except Exception as e:
            results[endpoint]["exceptions"] += 1
            results[endpoint]["error_codes"][type(e).__name__] += 1


def make_results_dict():
    return {
        ep: {
            "success": 0,
            "has_data": 0,
            "not_found": 0,
            "other_errors": 0,
            "timeouts": 0,
            "exceptions": 0,
            "times": [],
            "error_codes": defaultdict(int),
        }
        for ep in ENDPOINTS
    }


def print_stats(results: dict, total_drugs: int):
    print(f"\n{'='*90}")
    print(f"  BENCHMARK RESULTS  —  {total_drugs} drugs × {len(ENDPOINTS)} endpoints")
    print(f"{'='*90}")
    print(
        f"{'Endpoint':<28} {'200 OK':>7} {'HasData':>8} {'404':>6} {'Error':>6} "
        f"{'Timeout':>8} {'Avg ms':>8} {'P95 ms':>8} {'Rate':>7}"
    )
    print("-" * 90)

    totals = defaultdict(int)
    for ep, r in results.items():
        times = sorted(r["times"])
        avg = sum(times) / len(times) if times else 0
        p95 = times[int(len(times) * 0.95)] if times else 0
        total = total_drugs
        rate = r["success"] / total * 100

        totals["success"] += r["success"]
        totals["has_data"] += r["has_data"]
        totals["not_found"] += r["not_found"]
        totals["other_errors"] += r["other_errors"]
        totals["timeouts"] += r["timeouts"]

        print(
            f"{ep:<28} {r['success']:>7} {r['has_data']:>8} {r['not_found']:>6} "
            f"{r['other_errors']:>6} {r['timeouts']:>8} {avg:>8.1f} {p95:>8.1f} {rate:>6.1f}%"
        )

    print("-" * 90)
    total_calls = total_drugs * len(ENDPOINTS)
    overall_rate = totals["success"] / total_calls * 100
    print(
        f"{'TOTAL':<28} {totals['success']:>7} {totals['has_data']:>8} "
        f"{totals['not_found']:>6} {totals['other_errors']:>6} {totals['timeouts']:>8} "
        f"{'':>8} {'':>8} {overall_rate:>6.1f}%"
    )
    print(f"{'='*90}\n")

    # Top error codes per endpoint
    print("Error code breakdown (top issues per endpoint):")
    print("-" * 60)
    for ep, r in results.items():
        if r["error_codes"]:
            top = sorted(r["error_codes"].items(), key=lambda x: -x[1])[:3]
            codes_str = ", ".join(f"{k}:{v}" for k, v in top)
            print(f"  {ep:<28} {codes_str}")
    print()


async def main():
    print("Fetching 1000 random drug IDs from drugdb.indian_brand ...")
    drug_ids = await fetch_drug_ids()
    print(f"Got {len(drug_ids)} drug IDs. Starting benchmark ...\n")

    results = make_results_dict()
    sem = asyncio.Semaphore(CONCURRENCY)

    headers = {"X-API-Key": API_KEY}
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)

    t_start = time.perf_counter()
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = []
        for drug_id in drug_ids:
            for ep in ENDPOINTS:
                tasks.append(call_endpoint(session, drug_id, ep, results, sem))

        total_tasks = len(tasks)
        done = 0
        for coro in asyncio.as_completed(tasks):
            await coro
            done += 1
            if done % 1000 == 0:
                pct = done / total_tasks * 100
                print(f"  Progress: {done}/{total_tasks} ({pct:.0f}%)", flush=True)

    elapsed = time.perf_counter() - t_start
    print(f"\nCompleted {total_tasks} calls in {elapsed:.1f}s ({total_tasks/elapsed:.0f} req/s)")
    print_stats(results, len(drug_ids))


if __name__ == "__main__":
    asyncio.run(main())
