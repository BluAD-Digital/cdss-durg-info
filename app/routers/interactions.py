import asyncio
import itertools
import time
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.db import get_pool
from app.cache import get_cached, set_cached, build_key
from app.config import settings
from app.services.resolver import resolve_drug
from app.services.interactions import get_interactions, check_drug_interaction
from app.models.responses import DrugResponse, MetaResponse, ErrorResponse
from app.models.requests import MultiInteractionRequest
from app.exceptions import DrugNotFoundException, NoFormulationException, NoLabelDataException

router = APIRouter(tags=["interactions"])
logger = structlog.get_logger(__name__)


@router.get("/drug/{drug_id_1mg}/interactions")
async def drug_interactions(drug_id_1mg: str, request: Request):
    start = time.perf_counter()
    pool = get_pool()

    try:
        resolved = await resolve_drug(drug_id_1mg, pool)
    except (DrugNotFoundException, NoFormulationException, NoLabelDataException) as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                request_id=str(id(request)),
            ).model_dump(),
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="DB_ERROR",
                message=str(e),
                request_id=str(id(request)),
            ).model_dump(),
        )

    cache_key = build_key("interactions", resolved.formulation_id)
    cached = await get_cached(cache_key)
    cached_hit = cached is not None

    if cached_hit:
        result = cached
    else:
        result = await get_interactions(resolved.formulation_id, pool)
        await set_cached(cache_key, result, ttl=settings.CACHE_TTL)

    severity_counts = result.get("severity_counts", {})
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    meta = MetaResponse(source="database", cached=cached_hit, response_time_ms=duration_ms, is_partial_match=resolved.is_partial_match)
    meta_dict = meta.model_dump()
    meta_dict["severity_counts"] = severity_counts

    return {
        "success": True,
        "drug_id_1mg": drug_id_1mg,
        "generic_name": resolved.generic_name,
        "data": result.get("interactions", []),
        "meta": meta_dict,
    }


@router.get("/drug/{drug_id_1mg}/check-interaction/{other_drug_id}")
async def check_interaction_between_drugs(
    drug_id_1mg: str,
    other_drug_id: str,
    request: Request,
):
    start = time.perf_counter()
    pool = get_pool()

    # Resolve both drugs in parallel
    try:
        resolved1, resolved2 = await asyncio.gather(
            resolve_drug(drug_id_1mg, pool),
            resolve_drug(other_drug_id, pool),
        )
    except (DrugNotFoundException, NoFormulationException, NoLabelDataException) as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                request_id=str(id(request)),
            ).model_dump(),
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="DB_ERROR",
                message=str(e),
                request_id=str(id(request)),
            ).model_dump(),
        )

    # Cache key is order-independent (sort so drug1+drug2 == drug2+drug1)
    sorted_ids = sorted([resolved1.formulation_id, resolved2.formulation_id])
    cache_key = build_key("check_interaction", sorted_ids[0], sorted_ids[1])
    cached = await get_cached(cache_key)
    cached_hit = cached is not None

    try:
        if cached_hit:
            result = cached
        else:
            result = await check_drug_interaction(
                resolved1.formulation_id, resolved2.formulation_id, pool
            )
            await set_cached(cache_key, result, ttl=settings.CACHE_TTL)
    except Exception as e:
        logger.error("check_interaction_error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="DB_ERROR",
                message=str(e),
                request_id=str(id(request)),
            ).model_dump(),
        )

    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "success": True,
        "drug_1": {
            "drug_id_1mg": drug_id_1mg,
            "generic_name": resolved1.generic_name,
        },
        "drug_2": {
            "drug_id_1mg": other_drug_id,
            "generic_name": resolved2.generic_name,
        },
        "has_interaction": result["has_interaction"],
        "highest_severity": result["highest_severity"],
        "severity_summary": result["severity_counts"],
        "data": result["interactions"],
        "meta": {
            "source": "database",
            "cached": cached_hit,
            "response_time_ms": duration_ms,
            "is_partial_match": resolved1.is_partial_match or resolved2.is_partial_match,
        },
    }


@router.post("/drugs/check-interactions")
async def check_all_pair_interactions(
    body: MultiInteractionRequest,
    request: Request,
):
    start = time.perf_counter()
    pool = get_pool()

    # Phase 1: resolve all drugs in parallel — whole-request failure if any fails
    try:
        resolved_list = await asyncio.gather(
            *[resolve_drug(drug_id, pool) for drug_id in body.drug_ids]
        )
    except (DrugNotFoundException, NoFormulationException, NoLabelDataException) as e:
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error_code=e.error_code,
                message=e.message,
                request_id=str(id(request)),
            ).model_dump(),
        )
    except Exception as e:
        logger.error("check_all_pairs_resolve_error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="DB_ERROR",
                message=str(e),
                request_id=str(id(request)),
            ).model_dump(),
        )

    resolved_by_id = {did: r for did, r in zip(body.drug_ids, resolved_list)}
    pairs = list(itertools.combinations(body.drug_ids, 2))

    # Phase 2: check all pairs in parallel, reusing the per-pair cache
    async def _check_pair(id1: str, id2: str):
        r1, r2 = resolved_by_id[id1], resolved_by_id[id2]
        sorted_fids = sorted([r1.formulation_id, r2.formulation_id])
        cache_key = build_key("check_interaction", sorted_fids[0], sorted_fids[1])
        cached = await get_cached(cache_key)
        if cached is not None:
            return cached
        result = await check_drug_interaction(r1.formulation_id, r2.formulation_id, pool)
        await set_cached(cache_key, result, ttl=settings.CACHE_TTL)
        return result

    try:
        pair_results = await asyncio.gather(
            *[_check_pair(id1, id2) for id1, id2 in pairs]
        )
    except Exception as e:
        logger.error("check_all_pairs_interaction_error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="DB_ERROR",
                message=str(e),
                request_id=str(id(request)),
            ).model_dump(),
        )

    # Phase 3: build and sort pairs by severity (major → moderate → minor → none)
    _sev_rank = {"major": 1, "moderate": 2, "minor": 3}

    pairs_output = []
    for (id1, id2), result in zip(pairs, pair_results):
        r1, r2 = resolved_by_id[id1], resolved_by_id[id2]
        pairs_output.append({
            "drug_1": {"drug_id_1mg": id1, "generic_name": r1.generic_name},
            "drug_2": {"drug_id_1mg": id2, "generic_name": r2.generic_name},
            "has_interaction": result["has_interaction"],
            "highest_severity": result["highest_severity"],
            "severity_summary": result["severity_counts"],
            "interactions": result["interactions"],
        })

    pairs_output.sort(key=lambda p: _sev_rank.get(p["highest_severity"], 99))

    overall_has_interaction = any(p["has_interaction"] for p in pairs_output)
    all_severities = [p["highest_severity"] for p in pairs_output if p["highest_severity"]]
    overall_highest_severity = (
        min(all_severities, key=lambda s: _sev_rank.get(s, 99)) if all_severities else None
    )
    any_partial = any(resolved_by_id[did].is_partial_match for did in body.drug_ids)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    return {
        "success": True,
        "drugs": [
            {"drug_id_1mg": did, "generic_name": resolved_by_id[did].generic_name}
            for did in body.drug_ids
        ],
        "pairs": pairs_output,
        "overall_has_interaction": overall_has_interaction,
        "overall_highest_severity": overall_highest_severity,
        "meta": {
            "source": "database",
            "response_time_ms": duration_ms,
            "pair_count": len(pairs),
            "is_partial_match": any_partial,
        },
    }
