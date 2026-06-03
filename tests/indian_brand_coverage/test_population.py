#!/usr/bin/env python3
"""
Indian-brand coverage: POPULATION INFO

Tests /api/v1/drug/{drug_id}/population-info?age={age} for every drug_id_1mg
across representative ages (same age groups as the dosing service tests).

Run standalone : python tests/indian_brand_coverage/test_population.py
Run all        : python tests/indian_brand_coverage/run_all.py
"""
import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _common import run_coverage  # noqa: E402

LABEL = "population"

# display_name → representative age in years (matches dosing service convention)
AGE_GROUP_MAP = {
    "neonate":   0,
    "infant":    1,
    "pediatric": 10,
    "adult":     30,
    "geriatric": 70,
}


async def main() -> dict:
    return await run_coverage(label=LABEL, mode="population", age_group_map=AGE_GROUP_MAP)


if __name__ == "__main__":
    asyncio.run(main())
