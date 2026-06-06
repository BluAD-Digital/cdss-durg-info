# Graph Report - .  (2026-06-04)

## Corpus Check
- Corpus is ~36,359 words - fits in a single context window. You may not need a graph.

## Summary
- 613 nodes · 1211 edges · 53 communities (42 shown, 11 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 118 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Cache Layer|Cache Layer]]
- [[_COMMUNITY_Comprehensive Test Fixtures|Comprehensive Test Fixtures]]
- [[_COMMUNITY_Missing Coverage Tests|Missing Coverage Tests]]
- [[_COMMUNITY_Indian Brand Coverage Suite|Indian Brand Coverage Suite]]
- [[_COMMUNITY_Dosing Service & Fallback|Dosing Service & Fallback]]
- [[_COMMUNITY_Text Formatter & Tests|Text Formatter & Tests]]
- [[_COMMUNITY_Label Service & SQL|Label Service & SQL]]
- [[_COMMUNITY_Concurrency Tests|Concurrency Tests]]
- [[_COMMUNITY_Architecture Concepts|Architecture Concepts]]
- [[_COMMUNITY_App Lifecycle & FastAPI|App Lifecycle & FastAPI]]
- [[_COMMUNITY_Performance Tests|Performance Tests]]
- [[_COMMUNITY_Coverage Hybrid Testing|Coverage Hybrid Testing]]
- [[_COMMUNITY_Request & Response Models|Request & Response Models]]
- [[_COMMUNITY_Comprehensive Test Runner|Comprehensive Test Runner]]
- [[_COMMUNITY_Auth Middleware|Auth Middleware]]
- [[_COMMUNITY_Logging Middleware|Logging Middleware]]
- [[_COMMUNITY_Endpoint Integration Tests|Endpoint Integration Tests]]
- [[_COMMUNITY_1000 Drugs Benchmark|1000 Drugs Benchmark]]
- [[_COMMUNITY_Custom Exceptions|Custom Exceptions]]
- [[_COMMUNITY_Drug ID Fill Scripts|Drug ID Fill Scripts]]
- [[_COMMUNITY_Timing Middleware|Timing Middleware]]
- [[_COMMUNITY_Max Concurrency Finder|Max Concurrency Finder]]
- [[_COMMUNITY_Interactions Service|Interactions Service]]
- [[_COMMUNITY_API Coverage Scripts|API Coverage Scripts]]
- [[_COMMUNITY_Top500 Coverage Scripts|Top500 Coverage Scripts]]
- [[_COMMUNITY_Gunicorn & App Config|Gunicorn & App Config]]
- [[_COMMUNITY_Top500 Coverage Check|Top500 Coverage Check]]
- [[_COMMUNITY_Drug Classes Service|Drug Classes Service]]
- [[_COMMUNITY_Comprehensive Test Orchestration|Comprehensive Test Orchestration]]
- [[_COMMUNITY_Test Infrastructure|Test Infrastructure]]
- [[_COMMUNITY_App Settings|App Settings]]
- [[_COMMUNITY_Auth Edge Cases|Auth Edge Cases]]
- [[_COMMUNITY_Severity Ranking|Severity Ranking]]
- [[_COMMUNITY_Wrong Auth Helper|Wrong Auth Helper]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_100 Concurrent Test|100 Concurrent Test]]
- [[_COMMUNITY_Data Isolation Test|Data Isolation Test]]
- [[_COMMUNITY_Auth Isolation Test|Auth Isolation Test]]
- [[_COMMUNITY_200 Stress Test|200 Stress Test]]
- [[_COMMUNITY_Max Concurrency Level|Max Concurrency Level]]

## God Nodes (most connected - your core abstractions)
1. `split_to_bullets()` - 35 edges
2. `resolve_drug()` - 33 edges
3. `timed_get()` - 33 edges
4. `DrugNotFoundException` - 27 edges
5. `ErrorResponse` - 26 edges
6. `_label_endpoint()` - 25 edges
7. `MetaResponse` - 24 edges
8. `run_coverage()` - 24 edges
9. `set_cached()` - 23 edges
10. `NoFormulationException` - 23 edges

## Surprising Connections (you probably didn't know these)
- `drug_id_1mg Resolution (Indian brand ID to generic clinical data)` --conceptually_related_to--> `Resolver Fallback Chain (primary → UNII bridge)`  [EXTRACTED]
  README.md → tests/test_fallback_flows.py
- `5-CTE Dosing Query (salt_ingredients -> candidate_formulations -> best_formulation -> ranked -> final)` --conceptually_related_to--> `UNII Bridge Fallback (rxcui has no direct drug row, use UNII to resolve)`  [EXTRACTED]
  queries/ALL_ENDPOINT_QUERIES.md → tests/test_fallback_flows.py
- `Session-Scoped Fixture Pattern (DB pool + Redis shared once)` --rationale_for--> `Pure ASGI Middleware (avoids BaseHTTPMiddleware + asyncpg conflict in tests)`  [INFERRED]
  tests/conftest.py → README.md
- `health_check()` --calls--> `get_pool()`  [EXTRACTED]
  main.py → app/db.py
- `db_pool()` --calls--> `get_pool()`  [EXTRACTED]
  tests/conftest.py → app/db.py

## Import Cycles
- 1-file cycle: `main.py -> main.py`

## Hyperedges (group relationships)
- **Cache-Aside Read-Through Flow (get_pool + get_cached + set_cached)** — app_db_get_pool, app_cache_get_cached, app_cache_set_cached, app_cache_build_key [INFERRED 0.95]
- **Pure ASGI Middleware Stack (Auth + Logging + Timing)** — middleware_auth_authmiddleware, middleware_logging_loggingmiddleware, middleware_timing_timingmiddleware [INFERRED 0.85]
- **Drug Resolution Exception Handling Pattern** — app_exceptions_drugnotfoundexception, app_exceptions_noformulationexception, app_exceptions_nolabeldataexception, models_responses_errorresponse [INFERRED 0.85]
- **Label Extraction Pipeline (safe_get + extract_rich/dailymed + has_content)** — services_label_safe_get, services_label_extract_rich, services_label_extract_dailymed, services_label_has_content [EXTRACTED 0.95]
- **Drug Resolver 3-Step Lookup (indian_brand -> drug -> UNII bridge)** — services_resolver_resolve_drug, services_resolver_unii_bridge, services_resolver_partial_match_flag, services_resolver_resolveddrug [EXTRACTED 0.95]
- **Comprehensive Test Suite (endpoints + edge-cases + concurrency)** — tests_comprehensive_test_all_endpoints_label_structure, tests_comprehensive_test_edge_cases_invalid_drug_404, tests_comprehensive_test_concurrency_100_concurrent, tests_comprehensive_run_all_tests_main [EXTRACTED 0.95]
- **Indian Brand Coverage Test Suite (resolver + label + interactions + population via _common.run_coverage)** — indian_brand_coverage_test_resolver_test_resolver, indian_brand_coverage_test_label_test_label, indian_brand_coverage_test_interactions_test_interactions, indian_brand_coverage_test_population_test_population, indian_brand_coverage_common_run_coverage, indian_brand_coverage_run_all_run_all [EXTRACTED 1.00]
- **Resolver Fallback Test Coverage (primary + step1 fallback + step2 UNII bridge)** — tests_test_fallback_flows_testfallbackflows, tests_test_missing_coverage_testmissingcoverage, concept_resolver_fallback_chain, concept_unii_bridge [EXTRACTED 1.00]
- **Session Fixture Dependency Chain (_startup -> client/db_pool/redis_client -> valid_drug_id)** — tests_conftest_startup_fixture, tests_conftest_client_fixture, tests_conftest_valid_drug_id_fixture, concept_session_scoped_fixture_pattern [EXTRACTED 1.00]

## Communities (53 total, 11 thin omitted)

### Community 0 - "Cache Layer"
Cohesion: 0.12
Nodes (64): build_key(), delete_cached(), get_cached(), is_connected(), Any, bool, int, str (+56 more)

### Community 1 - "Comprehensive Test Fixtures"
Cohesion: 0.05
Nodes (54): http_client(), Comprehensive test suite configuration. Connects to the live server at localhost, Same as timed_get but without API key header., Same as timed_get but with wrong API key., Synchronous-style fixture that exposes a thin async GET helper., Make a GET request with the API key header.     Returns (response, elapsed_ms)., timed_get(), timed_get_no_auth() (+46 more)

### Community 2 - "Missing Coverage Tests"
Cohesion: 0.05
Nodes (25): Tests for gaps identified in existing coverage:   1. check-interaction endpoint, A drug checked against itself — should succeed (no interactions expected)., Fallback-resolved drugs must serve every label endpoint without 500., Primary drug must accept every age group without 500., UNII-bridge fallback drug must also handle every age group without 500., Second request for a fallback-dosing drug must be served from cache., Cached response must be identical to the original fallback response., Primary drug vs step1-fallback drug — should not 500. (+17 more)

### Community 3 - "Indian Brand Coverage Suite"
Cohesion: 0.10
Nodes (30): _classify_endpoints(), _classify_population(), _classify_resolver(), find_latest_log(), _hit_endpoint(), load_prior_results(), Shared helpers and core runner for indian_brand coverage tests.  Hits the live c, Hit a single URL, return 'success' / 'not_found' / 'error'. (+22 more)

### Community 4 - "Dosing Service & Fallback"
Cohesion: 0.09
Nodes (32): NoDosingDataException, Any, str, Dosing Fallback via UNII Bridge, get_dosing(), _find_dosing_fallback_drug(), _find_dosing_primary_drug(), _find_primary_resolver_drug() (+24 more)

### Community 5 - "Text Formatter & Tests"
Cohesion: 0.11
Nodes (32): str, Unit tests for app/utils/text_formatter.py  Tests verify that split_to_bullets c, test_all_bullets_are_non_empty_strings(), test_allcaps_section_title_split(), test_allcaps_title_splits_from_sentence(), test_already_newlined_text(), test_empty_string_returns_empty_list(), test_inline_cross_ref_splits_correctly() (+24 more)

### Community 6 - "Label Service & SQL"
Cohesion: 0.16
Nodes (28): Any, bool, int, str, _extract_dailymed(), _extract_rich(), _fi_to_str(), get_adverse_reactions() (+20 more)

### Community 7 - "Concurrency Tests"
Cohesion: 0.17
Nodes (21): _get(), _print_table(), Concurrency and data-isolation tests.  Verifies two properties under concurrent, 10 users each request a different drug at the exact same moment.     Every respo, 100 concurrent requests (10 drugs × 10 rounds).     Every single response must c, 20 authorized + 20 unauthorized requests fire at the same time.     Auth'd users, 10 waves of 10 concurrent requests (100 total, sequential waves).     Checks the, 20 users request the same drug simultaneously.     All 20 responses must return (+13 more)

### Community 8 - "Architecture Concepts"
Cohesion: 0.14
Nodes (21): 5-CTE Dosing Query (salt_ingredients -> candidate_formulations -> best_formulation -> ranked -> final), Pure ASGI Middleware (avoids BaseHTTPMiddleware + asyncpg conflict in tests), CDSS Drug Info 3-Layer Architecture (API + Cache + DB), combined_clean_jsonb JSONB blob (merged openFDA + DailyMed + DrugBank + RxNorm), drug_id_1mg Resolution (Indian brand ID to generic clinical data), Redis Silent Fallback (Redis down -> non-fatal, fall through to DB), Resolver Fallback Chain (primary → UNII bridge), Session-Scoped Fixture Pattern (DB pool + Redis shared once) (+13 more)

### Community 9 - "App Lifecycle & FastAPI"
Cohesion: 0.20
Nodes (13): close_redis(), create_redis(), close_pool(), create_pool(), FastAPI, health_check(), lifespan(), Pool (+5 more)

### Community 10 - "Performance Tests"
Cohesion: 0.22
Nodes (17): _get(), _print_table(), Performance tests: response times, cache behaviour, concurrent load. Prints summ, 10 concurrent requests to /contraindications — all must succeed under 10000ms to, Concurrent should be significantly faster than sequential for 5 drugs., /dosing-regimen uses 5-CTE query — must be under 5000ms per drug., All 10 drugs — sequential, each must be under 2000ms., Second call for same drug must be faster (cache hit) and meta.cached=true. (+9 more)

### Community 11 - "Coverage Hybrid Testing"
Cohesion: 0.25
Nodes (13): Indian Brand Coverage Testing Pattern, check_drug(), coverage_hybrid, hit(), main(), print_spotcheck_report(), run_http_spotcheck(), run_sql_coverage() (+5 more)

### Community 12 - "Request & Response Models"
Cohesion: 0.31
Nodes (11): BaseModel, DrugRequest, ActiveIngredientItem, InactiveProductIngredients, IngredientsData, LabelData, PopulationInfoData, ProductIngredients (+3 more)

### Community 15 - "Comprehensive Test Runner"
Cohesion: 0.26
Nodes (12): build_report(), check_server(), collect_cache_data(), collect_performance_data(), extract_failures(), main(), Measure cache miss vs hit for a fresh warm-up call sequence., Pull out FAILED test lines from pytest output. (+4 more)

### Community 16 - "Auth Middleware"
Cohesion: 0.20
Nodes (8): ASGIApp, Receive, Scope, Send, str, AuthMiddleware, Pure ASGI middleware — avoids BaseHTTPMiddleware's anyio task-group conflicts., _send_401

### Community 17 - "Logging Middleware"
Cohesion: 0.17
Nodes (9): ASGIApp, Receive, Scope, Send, str, Pure ASGI Middleware Pattern, LoggingMiddleware, Pure ASGI middleware — avoids BaseHTTPMiddleware's anyio task-group conflicts. (+1 more)

### Community 18 - "Endpoint Integration Tests"
Cohesion: 0.17
Nodes (12): timed_get, assert_base_envelope, assert_rich_label_structure, test_dosing_regimen_adult, test_drug_classes_structure, test_interactions_structure, test_label_endpoint_structure, test_population_info (+4 more)

### Community 19 - "1000 Drugs Benchmark"
Cohesion: 0.31
Nodes (10): call_endpoint(), fetch_drug_ids(), main(), make_results_dict(), print_stats(), ClientSession, int, Semaphore (+2 more)

### Community 20 - "Custom Exceptions"
Cohesion: 0.36
Nodes (4): CacheException, DatabaseException, str, Exception

### Community 21 - "Drug ID Fill Scripts"
Cohesion: 0.38
Nodes (9): auto_lookup(), best_of(), main(), bool, str, Crocin 500 → Crocin, Norflox TZ stays unchanged., salt_keywords(), salt_match() (+1 more)

### Community 22 - "Timing Middleware"
Cohesion: 0.22
Nodes (6): ASGIApp, Receive, Scope, Send, Pure ASGI middleware — avoids BaseHTTPMiddleware's anyio task-group conflicts., TimingMiddleware

### Community 23 - "Max Concurrency Finder"
Cohesion: 0.38
Nodes (6): check_server(), main(), Fire n concurrent requests and collect per-request latencies., run_level(), bool, int

### Community 24 - "Interactions Service"
Cohesion: 0.53
Nodes (5): Any, str, check_drug_interaction(), get_interactions(), Find interactions specifically between the ingredients of two drugs.     Checks

### Community 25 - "API Coverage Scripts"
Cohesion: 0.53
Nodes (5): check_drug(), main(), AsyncClient, Semaphore, str

### Community 26 - "Top500 Coverage Scripts"
Cohesion: 0.33
Nodes (6): lookup, check_top500_coverage.py main, auto_lookup, CORRECTIONS dict, fill_missing_drug_ids.py main, salt_match

### Community 28 - "Gunicorn & App Config"
Cohesion: 0.50
Nodes (3): FastAPI app (main.py), custom_openapi(), slowapi Limiter

### Community 30 - "Drug Classes Service"
Cohesion: 0.50
Nodes (3): Any, str, get_drug_classes()

### Community 31 - "Comprehensive Test Orchestration"
Cohesion: 0.50
Nodes (4): collect_cache_data, collect_performance_data, run_all_tests.py main, run_pytest

### Community 32 - "Test Infrastructure"
Cohesion: 0.50
Nodes (4): TestPerformance, Comprehensive Test Report, conftest, TestTextFormatter

## Knowledge Gaps
- **70 isolated node(s):** `Any`, `int`, `Config`, `ASGIApp`, `Scope` (+65 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `resolve_drug()` connect `Cache Layer` to `App Lifecycle & FastAPI`, `Dosing Service & Fallback`, `Label Service & SQL`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `split_to_bullets()` connect `Text Formatter & Tests` to `Cache Layer`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `UNII Bridge Fallback` connect `Label Service & SQL` to `Cache Layer`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `DrugNotFoundException` (e.g. with `NoFormulationException` and `Request`) actually correct?**
  _`DrugNotFoundException` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `ErrorResponse` (e.g. with `Request` and `str`) actually correct?**
  _`ErrorResponse` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Any`, `int`, `Config` to the rest of the system?**
  _152 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Cache Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.11790840738209159 - nodes in this community are weakly interconnected._