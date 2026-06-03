#!/usr/bin/env python3
"""
Indian-brand coverage: INTERACTIONS & INGREDIENTS

Tests interaction-related and ingredient endpoints for every drug_id_1mg.

Endpoints tested:
  interactions      — drug-drug interactions list
  food_interactions — food interactions list
  ingredients       — ingredient breakdown
  drug_classes      — drug class assignments
  products          — available product forms

Run standalone : python tests/indian_brand_coverage/test_interactions.py
Run all        : python tests/indian_brand_coverage/run_all.py
"""
import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _common import run_coverage  # noqa: E402

LABEL = "interactions"

ENDPOINT_MAP = {
    "interactions":       "interactions",
    "food_interactions":  "food-interactions",
    "ingredients":        "ingredients",
    "drug_classes":       "drug-classes",
    "products":           "products",
}


async def main() -> dict:
    return await run_coverage(label=LABEL, mode="endpoints", endpoint_map=ENDPOINT_MAP)


if __name__ == "__main__":
    asyncio.run(main())
