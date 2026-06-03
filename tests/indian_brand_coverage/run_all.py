#!/usr/bin/env python3
"""
Run all indian_brand coverage tests simultaneously.

Hits the live cdss-drug-info API — 100% faithful to real service behaviour.
All 4 tests fire concurrently via asyncio.gather(); drug list fetched once.

Usage (from project root):
    python3 tests/indian_brand_coverage/run_all.py

Optional env overrides:
    DRUG_INFO_BASE_URL=http://<host>:8002   (default: http://34.14.197.45:8002)
    API_KEY=<key>                           (default: dev)
"""
import asyncio
import os
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import aiohttp
import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
DB_URL  = os.environ["DATABASE_URL"]
API_KEY = os.environ.get("API_KEY", "dev")

from _common import FETCH_ALL_DRUGS_SQL, CONCURRENCY, BASE_URL, find_latest_log, run_coverage

from test_resolver     import LABEL as LABEL_RESOLVER
from test_label        import LABEL as LABEL_LABEL,       ENDPOINT_MAP as EP_LABEL
from test_interactions import LABEL as LABEL_INTERACTIONS, ENDPOINT_MAP as EP_INTERACTIONS
from test_population   import LABEL as LABEL_POPULATION,  AGE_GROUP_MAP as AGE_POP


async def main() -> None:
    print("=" * 80)
    print("indian_brand coverage  —  cdss-drug-info  —  all tests starting NOW")
    print(f"  Endpoint base : {BASE_URL}")
    print("  Test 1 : resolver       → /generic-name")
    print("  Test 2 : label          → contraindications, warnings, mechanism, indications, …")
    print("  Test 3 : interactions   → interactions, food-interactions, ingredients, drug-classes, products")
    print("  Test 4 : population     → population-info at ages 0, 1, 10, 30, 70")
    print("=" * 80)

    prior_logs = {
        LABEL_RESOLVER:     find_latest_log(LABEL_RESOLVER),
        LABEL_LABEL:        find_latest_log(LABEL_LABEL),
        LABEL_INTERACTIONS: find_latest_log(LABEL_INTERACTIONS),
        LABEL_POPULATION:   find_latest_log(LABEL_POPULATION),
    }
    for label, log in prior_logs.items():
        status = f"continuing from {log.name}" if log else "starting from scratch"
        print(f"  [{'resume' if log else 'fresh '}] {label}: {status}")
    print("─" * 80)

    t0 = time.perf_counter()

    print("Fetching drug list from drugdb.indian_brand …", flush=True)
    pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=3, command_timeout=30)
    async with pool.acquire() as conn:
        drugs = await conn.fetch(FETCH_ALL_DRUGS_SQL)
    await pool.close()
    print(f"  → {len(drugs):,} drug_ids fetched in {time.perf_counter()-t0:.1f}s")
    print("─" * 80)

    connector = aiohttp.TCPConnector(limit=CONCURRENCY * 4)
    async with aiohttp.ClientSession(connector=connector, headers={"X-API-Key": API_KEY}) as session:
        results = await asyncio.gather(
            run_coverage(label=LABEL_RESOLVER,     mode="resolver",   session=session, drugs=drugs, resume_log=prior_logs[LABEL_RESOLVER]),
            run_coverage(label=LABEL_LABEL,        mode="endpoints",  endpoint_map=EP_LABEL,        session=session, drugs=drugs, resume_log=prior_logs[LABEL_LABEL]),
            run_coverage(label=LABEL_INTERACTIONS, mode="endpoints",  endpoint_map=EP_INTERACTIONS, session=session, drugs=drugs, resume_log=prior_logs[LABEL_INTERACTIONS]),
            run_coverage(label=LABEL_POPULATION,   mode="population", age_group_map=AGE_POP,        session=session, drugs=drugs, resume_log=prior_logs[LABEL_POPULATION]),
            return_exceptions=True,
        )

    elapsed = time.perf_counter() - t0
    labels  = [LABEL_RESOLVER, LABEL_LABEL, LABEL_INTERACTIONS, LABEL_POPULATION]

    print("\n" + "═" * 80)
    print(f"ALL DONE  —  wall time {elapsed:.1f}s  ({elapsed/60:.1f} min)")
    print("═" * 80)
    for label, result in zip(labels, results):
        if isinstance(result, Exception):
            print(f"  [{label}]  FAILED: {result}")
        else:
            print(f"  [{label}]  OK  — logs in tests/indian_brand_coverage/logs/")
    print("═" * 80)


if __name__ == "__main__":
    asyncio.run(main())
