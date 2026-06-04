import pytest
from tests.conftest import API_KEY

DRUG_A = "1000006"
DRUG_B = "1000037"
DRUG_C = "1000030"


@pytest.mark.asyncio
async def test_interactions_valid(client, valid_drug_id):
    resp = await client.get(
        f"/api/v1/drug/{valid_drug_id}/interactions",
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "severity_counts" in body["meta"]
    sc = body["meta"]["severity_counts"]
    assert "major" in sc and "moderate" in sc and "minor" in sc


@pytest.mark.asyncio
async def test_interactions_invalid_drug(client, invalid_drug_id):
    resp = await client.get(
        f"/api/v1/drug/{invalid_drug_id}/interactions",
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_interactions_cache(client, valid_drug_id, redis_client):
    if redis_client is None:
        pytest.skip("Redis not available in this environment")
    headers = {"X-API-Key": API_KEY}
    url = f"/api/v1/drug/{valid_drug_id}/interactions"
    await client.get(url, headers=headers)
    resp2 = await client.get(url, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["meta"]["cached"] is True


# ── POST /api/v1/drugs/check-interactions ────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_check_two_drugs_response_shape(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, DRUG_B]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["drugs"]) == 2
    for drug in body["drugs"]:
        assert "drug_id_1mg" in drug and "generic_name" in drug
    assert len(body["pairs"]) == 1
    pair = body["pairs"][0]
    assert isinstance(pair["has_interaction"], bool)
    assert pair["highest_severity"] in ("major", "moderate", "minor", None)
    assert all(k in pair["severity_summary"] for k in ("major", "moderate", "minor"))
    assert isinstance(pair["interactions"], list)
    assert isinstance(body["overall_has_interaction"], bool)
    assert body["overall_highest_severity"] in ("major", "moderate", "minor", None)
    meta = body["meta"]
    assert meta["pair_count"] == 1
    assert meta["source"] == "database"
    assert "response_time_ms" in meta
    assert "is_partial_match" in meta


@pytest.mark.asyncio
async def test_multi_check_three_drugs_pair_count(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, DRUG_B, DRUG_C]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["pair_count"] == 3
    assert len(body["pairs"]) == 3
    assert len(body["drugs"]) == 3


@pytest.mark.asyncio
async def test_multi_check_pairs_sorted_by_severity(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, DRUG_B, DRUG_C]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    _rank = {"major": 1, "moderate": 2, "minor": 3}
    pairs = resp.json()["pairs"]
    ranks = [_rank.get(p["highest_severity"], 99) for p in pairs]
    assert ranks == sorted(ranks), "pairs must be sorted major→moderate→minor→none"


@pytest.mark.asyncio
async def test_multi_check_overall_severity_is_highest(client):
    _rank = {"major": 1, "moderate": 2, "minor": 3}
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, DRUG_B, DRUG_C]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    overall = body["overall_highest_severity"]
    if overall is None:
        assert body["overall_has_interaction"] is False
    else:
        for pair in body["pairs"]:
            ps = pair["highest_severity"]
            if ps is not None:
                assert _rank[overall] <= _rank[ps]


@pytest.mark.asyncio
async def test_multi_check_one_drug_returns_422(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_multi_check_one_invalid_drug_fails_all(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, "INVALID_999999", DRUG_B]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "DRUG_NOT_FOUND"


@pytest.mark.asyncio
async def test_multi_check_all_invalid_returns_404(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": ["INVALID_A", "INVALID_B"]},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_multi_check_no_api_key_returns_401(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, DRUG_B]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_multi_check_empty_body_returns_422(client):
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_multi_check_cache_reuse(client, redis_client):
    if redis_client is None:
        pytest.skip("Redis not available")
    headers = {"X-API-Key": API_KEY}
    # Warm the A-B pair via the 2-drug endpoint
    await client.get(
        f"/api/v1/drug/{DRUG_A}/check-interaction/{DRUG_B}",
        headers=headers,
    )
    # Multi endpoint must still succeed (shared cache key)
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [DRUG_A, DRUG_B]},
        headers=headers,
    )
    assert resp.status_code == 200
