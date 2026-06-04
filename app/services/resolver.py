import json
import structlog
from dataclasses import dataclass, asdict
from typing import Optional, List
from app.exceptions import DrugNotFoundException, NoFormulationException, NoLabelDataException
from app.cache import get_cached, set_cached, build_key

logger = structlog.get_logger(__name__)

_RESOLVER_TTL = 86400  # 24 hours


@dataclass
class ResolvedDrug:
    drug_id_1mg: str
    brand_name: Optional[str]
    salt_composition: Optional[str]
    rxcui: Optional[List[str]]
    formulation_id: Optional[str]
    master_linkage_id: Optional[str]
    generic_name: Optional[str]
    combined_clean_jsonb: Optional[dict]
    is_partial_match: bool = False


async def resolve_drug(drug_id_1mg: str, pool) -> ResolvedDrug:
    cache_key = build_key("resolver", drug_id_1mg)
    cached = await get_cached(cache_key)
    if cached is not None:
        logger.info("resolver_cache_hit", drug_id_1mg=drug_id_1mg)
        return ResolvedDrug(**cached)
    async with pool.acquire() as conn:
        # Step 1 — prefer quality sources; fall back to any source if not found
        row1 = await conn.fetchrow(
            """
            SELECT ib.rxcui, ib.salt_composition, ib.brand_name
            FROM drugdb.indian_brand ib
            WHERE ib.drug_id_1mg = $1
              AND ib.match_combination NOT IN ('drugbank', 'us_unapproved')
            LIMIT 1
            """,
            drug_id_1mg,
        )
        if not row1:
            logger.info("resolver_step1_fallback", drug_id_1mg=drug_id_1mg)
            row1 = await conn.fetchrow(
                """
                SELECT ib.rxcui, ib.salt_composition, ib.brand_name
                FROM drugdb.indian_brand ib
                WHERE ib.drug_id_1mg = $1
                LIMIT 1
                """,
                drug_id_1mg,
            )
        if not row1:
            logger.warning("drug_not_found", drug_id_1mg=drug_id_1mg)
            raise DrugNotFoundException(drug_id_1mg)

        raw_rxcui = row1["rxcui"]
        # Handle both list and single string from asyncpg
        if raw_rxcui is None:
            rxcui = []
        elif isinstance(raw_rxcui, list):
            rxcui = raw_rxcui
        elif isinstance(raw_rxcui, str):
            rxcui = [raw_rxcui]
        else:
            rxcui = list(raw_rxcui)

        brand_name = row1["brand_name"]
        salt_composition = row1["salt_composition"]

        logger.info("resolver_step1_ok", drug_id_1mg=drug_id_1mg, rxcui=rxcui)

        # Step 2 — direct rxcui join; fall back to UNII bridge if no formulation found
        row2 = await conn.fetchrow(
            """
            SELECT d.formulation_id, d.master_linkage_id, d.generic_name,
                   COALESCE(m.combined_clean_jsonb, mf.combined_clean_jsonb) AS combined_clean_jsonb,
                   COALESCE(m.generic_name, mf.generic_name, d.generic_name) AS ml_generic_name
            FROM drugdb.drug d
            LEFT JOIN drugdb.drug_master_linkage_unique m USING (master_linkage_id)
            LEFT JOIN drugdb.drug_master_linkage_unique mf
                   ON mf.generic_formulation = d.generic_formulation
                  AND m.master_linkage_id IS NULL
            WHERE d.rxcui = ANY($1::text[])
            LIMIT 1
            """,
            rxcui,
        )
        is_partial_match = False
        if not row2 and rxcui:
            logger.info("resolver_step2_fallback", drug_id_1mg=drug_id_1mg, rxcui=rxcui)
            row2 = await conn.fetchrow(
                """
                WITH active_resolvable AS (
                  SELECT DISTINCT i.rxcui, dml.master_linkage_id
                  FROM drugdb.ingredients i
                  JOIN public."DrugMasterLinkage" dml ON dml.unii_ids @> ARRAY[i.unii::text]
                  WHERE i.rxcui = ANY($1::text[])
                    AND (i.type = 'active' OR i.type IS NULL)
                    AND i.unii IS NOT NULL
                    AND array_length(dml.rxcui_ids, 1) = 1
                ),
                inactive_resolvable AS (
                  SELECT DISTINCT ON (i.rxcui) i.rxcui, dml.master_linkage_id
                  FROM drugdb.ingredients i
                  JOIN public."DrugMasterLinkage" dml ON dml.unii_ids @> ARRAY[i.unii::text]
                  WHERE i.rxcui = ANY($1::text[])
                    AND i.type = 'inactive'
                    AND i.unii IS NOT NULL
                  ORDER BY i.rxcui, array_length(dml.rxcui_ids, 1) DESC
                ),
                resolvable_rxcuis AS (
                  SELECT rxcui, master_linkage_id FROM active_resolvable
                  UNION
                  SELECT rxcui, master_linkage_id FROM inactive_resolvable
                ),
                pass_counts AS (
                  SELECT
                    (SELECT COUNT(DISTINCT rxcui) FROM resolvable_rxcuis) AS resolved,
                    array_length($1::text[], 1)                           AS total
                ),
                linkage AS (
                  SELECT DISTINCT master_linkage_id
                  FROM resolvable_rxcuis
                  WHERE (SELECT resolved >= 1 FROM pass_counts)
                )
                SELECT d.formulation_id, d.master_linkage_id, d.generic_name,
                       COALESCE(m.combined_clean_jsonb, mf.combined_clean_jsonb) AS combined_clean_jsonb,
                       COALESCE(m.generic_name, mf.generic_name, d.generic_name) AS ml_generic_name,
                       (SELECT resolved < total AND resolved >= 1 FROM pass_counts) AS is_partial_match
                FROM drugdb.drug d
                LEFT JOIN drugdb.drug_master_linkage_unique m USING (master_linkage_id)
                LEFT JOIN drugdb.drug_master_linkage_unique mf
                       ON mf.generic_formulation = d.generic_formulation
                      AND m.master_linkage_id IS NULL
                JOIN linkage l ON d.master_linkage_id = l.master_linkage_id
                LIMIT 1
                """,
                rxcui,
            )
            if row2:
                is_partial_match = bool(row2["is_partial_match"])
        if not row2:
            logger.warning("no_formulation", drug_id_1mg=drug_id_1mg, rxcui=rxcui)
            raise NoFormulationException(drug_id_1mg)

        formulation_id = row2["formulation_id"]
        master_linkage_id = row2["master_linkage_id"]
        generic_name = row2["generic_name"]

        logger.info(
            "resolver_step2_ok",
            formulation_id=formulation_id,
            master_linkage_id=master_linkage_id,
        )

        row3 = row2

        raw_jsonb = row3["combined_clean_jsonb"]
        if raw_jsonb is None:
            combined_clean_jsonb = {}
        elif isinstance(raw_jsonb, str):
            try:
                combined_clean_jsonb = json.loads(raw_jsonb)
            except (json.JSONDecodeError, ValueError):
                combined_clean_jsonb = {}
        elif isinstance(raw_jsonb, dict):
            combined_clean_jsonb = raw_jsonb
        else:
            combined_clean_jsonb = {}

        final_generic_name = row3["ml_generic_name"] or generic_name

        logger.info("resolver_step3_ok", master_linkage_id=master_linkage_id)

        resolved = ResolvedDrug(
            drug_id_1mg=drug_id_1mg,
            brand_name=brand_name,
            salt_composition=salt_composition,
            rxcui=rxcui,
            formulation_id=str(formulation_id) if formulation_id else None,
            master_linkage_id=str(master_linkage_id) if master_linkage_id else None,
            generic_name=final_generic_name,
            combined_clean_jsonb=combined_clean_jsonb,
            is_partial_match=is_partial_match,
        )
        await set_cached(cache_key, asdict(resolved), ttl=_RESOLVER_TTL)
        return resolved
