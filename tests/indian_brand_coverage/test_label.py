#!/usr/bin/env python3
"""
Indian-brand coverage: LABEL ENDPOINTS

Tests every label endpoint for every drug_id_1mg in drugdb.indian_brand.
Each endpoint resolves the drug first (resolver flow), then fetches label data
from drug_master_linkage_unique. A 404 means either the resolver failed or no
label data exists for that section.

Endpoints tested:
  contraindications, warnings, mechanism-of-action, indications,
  adverse-reactions, drug-description, microbiology, patient-info

Run standalone : python tests/indian_brand_coverage/test_label.py
Run all        : python tests/indian_brand_coverage/run_all.py
"""
import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _common import run_coverage  # noqa: E402

LABEL = "label"

# Each key becomes a column in the summary; value is the endpoint path suffix
ENDPOINT_MAP = {
    "contraindications":  "contraindications",
    "warnings":           "warnings",
    "mechanism":          "mechanism-of-action",
    "indications":        "indications",
    "adverse_reactions":  "adverse-reactions",
    "drug_description":   "drug-description",
    "microbiology":       "microbiology",
    "patient_info":       "patient-info",
}


async def main() -> dict:
    return await run_coverage(label=LABEL, mode="endpoints", endpoint_map=ENDPOINT_MAP)


if __name__ == "__main__":
    asyncio.run(main())
