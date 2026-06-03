#!/usr/bin/env python3
"""
Indian-brand coverage: RESOLVER

Tests /api/v1/drug/{drug_id}/generic-name for every drug_id_1mg in
drugdb.indian_brand. This exercises the full resolver flow:
  Step 1: indian_brand → rxcui  (primary: quality source; fallback: any source)
  Step 2: rxcui → drug + drug_master_linkage_unique  (direct or UNII bridge)

Run standalone : python tests/indian_brand_coverage/test_resolver.py
Run all        : python tests/indian_brand_coverage/run_all.py
"""
import asyncio
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _common import run_coverage  # noqa: E402

LABEL = "resolver"


async def main() -> dict:
    return await run_coverage(label=LABEL, mode="resolver")


if __name__ == "__main__":
    asyncio.run(main())
