# Test strategy and traceability

> **In plain words.** A synthetic fixture can prove a calculation without proving a production KPI. This document separates synthetic examples, executable local checks, reported warehouse results and planned product tests.
>
> New here? Read [START-HERE](START-HERE.md) first.

Date: 2026-11-12. Lens: all. Principles: FP-10 (every optimisation has an oracle), FP-7 (fail closed). This document says **what is proven, where, and what is not**. A claim in the other documents must not be stronger than its evidence. The authoritative meaning is in [16](16-correctness-contract.md); backend choice does not change that meaning.

## Current evidence

Local suite: **64 passed, 52 skipped, 2 expected failures** with Python 3.12.7, DuckDB 2.0.0, EdgeSQL 0.1.0 and sqlglot 30.25.0, installed from the pinned [requirements-test.txt](fixtures/requirements-test.txt). The skips are the Databricks-tier variants, which are off unless a warehouse is configured. The retained output in [validation](validation/2026-11-12/README.md) (54 passed, 43 skipped, 2 expected failures on Python 3.12.14) was recorded before the following files were added:

| Added file | Passing tests | What they establish |
|---|---:|---|
| [test_business_case_math.py](fixtures/test_business_case_math.py) | 4 | Exact arithmetic: the error identity for averaged rates, bounds for rates and unique counts, and the mix/rate split of a comparison |
| [test_grid_reconciliation.py](fixtures/test_grid_reconciliation.py) | 7 | The self-checks of [16](16-correctness-contract.md) C-CHECK on the S4 grid, what they detect, what they cannot detect, and the additivity probe of [10](10-edgesql-integration.md) EDGE-PROBE |
| [test_tutorial.py](fixtures/test_tutorial.py), step 8 | 1 | A relation that stores a finished rate cannot be regrouped correctly ([05](05-first-principles-solution.md)) |

The mutation check kills 7 of 7 mutants, and the offline replay of the retained Databricks responses passes.

Nine standard-library mathematical tests in `test_correctness_contract.py` cover denominator weights, overlapping identities, formula domains, complete partitions, prior-year display alignment and backdated corrections.

**Malloy probe (local DuckDB only).** One Malloy nested query over the same fixture returned the 56 reference groups with five integer aggregates equal and four ratios within `1e-12`. The generated SQL is one statement that repeats each row once per grouping shape. An unguarded Malloy ratio returned `NaN` for a zero denominator. Model, script, generated SQL, result and limits are in [validation/2026-11-12-malloy](validation/2026-11-12-malloy/README.md). No Databricks connection was used.

**Databricks probe (not rerun for the additions above).** The statements ran on a Databricks serverless SQL warehouse (2X-Small, Photon; identifiers withheld). The warehouse was initially stopped and was started by the validation statements. The source table was described before SQL execution.

Two warehouse statements each returned 56 rows, one complete chunk, `truncated: false`:
- Generated SQL over the synthetic message fixture.
- A session-scoped temporary metric view, composed measures and `MEASURE()` over the same 12 default grouping sets.

Both match the local fixture at all grouping/member keys, all five integer atoms exactly, and all four ratios within `1e-12` numeric tolerance. This proves the tested native calculation shape, not production KPI definitions, full null/empty behavior, complete adapter conformance, policies or speed. The source version was not pinned across these two probes; they are not a multi-query snapshot-consistency test. No persistent tables or metric views were created or replaced.

[Validation evidence](validation/2026-11-12/README.md) retains query text, requests, full responses, replay checks, source hash and a pinned local dependency set. Benchmark claims below are separate.

## How to run

```bash
# Reproduce the local environment from the repository root
python3 -m venv .venv
.venv/bin/python -m pip install -r specs/kpi/fixtures/requirements-test.txt
env -u DATABRICKS_CONFIG_PROFILE -u EDGEKPI_DBX_WAREHOUSE PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest specs/kpi/fixtures -q -p no:cacheprovider

# Add the Databricks tier only in an authorized scratch schema; tests create/replace fixtures
export DATABRICKS_CONFIG_PROFILE=your-profile EDGEKPI_DBX_WAREHOUSE=your-warehouse-id
uv run --with duckdb --with pytest --with edgesql --with databricks-sdk pytest specs/kpi/fixtures -q

# Mutation check (DuckDB only unless --dbx)
python specs/kpi/fixtures/mutation_check.py

# Malloy probe (local DuckDB, dependencies installed outside the repository)
npm install --prefix /tmp/edgekpi-malloy @malloydata/malloy@0.0.437 @malloydata/db-duckdb@0.0.437
NODE_PATH=/tmp/edgekpi-malloy/node_modules node specs/kpi/validation/2026-11-12-malloy/malloy_s4_probe.js

# Benchmarks (see 08)
python specs/kpi/fixtures/bench.py 3000000          # DuckDB
python specs/kpi/fixtures/bench_dbx.py 3000000 1    # Databricks, costs warehouse time
```

Result recorded on 2026-11-12 for the whole folder, before the additions above (raw run logs and a locked dependency environment are not retained): DuckDB only 45 passed, 43 skipped (Databricks tier off), 2 expected failures. DuckDB plus Databricks 84 passed, 4 skipped (the 72-statement baseline is a benchmark, not a test), 2 expected failures. Of those, `test_databricks.py` holds 7 Databricks-only tests and `test_tutorial.py` holds the parametrized checks behind the small worked example in START-HERE. The mutation report said 7 of 7 killed. These counts are not a fresh Databricks verification.

## Tiers

| Tier | What it proves | Engine | Status |
|---|---|---|---|
| TIER-UNIT | Pure functions: lattice, gid decoding, validation | none | partly exercised through the spike |
| TIER-ORACLE | The prototype equals one `GROUP BY` per populated node on the synthetic fixture | DuckDB and Databricks | **executable; target run reported, logs not retained** (`test_single_statement_equals_one_query_per_node`) |
| TIER-CONTRACT | Small-fixture rows and selected edge behavior agree; not full product adapter conformance | DuckDB and Databricks | **executable; target run reported, logs not retained**: the same functions run on both through the `con`, `sc` and `retail` fixtures |
| TIER-DBX | Selected target-engine behaviors | Databricks | **reported, logs not retained** for 7 tests in `test_databricks.py` |
| TIER-EDGE | EdgeSQL parses and round-trips planner SQL. Placeholder gap is pinned | none (library) | **executable**, 2 strict `xfail` |
| TIER-MUT | Tests are able to fail | DuckDB | **executable**, 7 mutants; harness limitations below |
| TIER-E2E | API and UI against the reporting scenarios | product | planned (P3), ids in [12](12-ux-and-wireframes.md) UX-01 to UX-14, gated by capability |
| TIER-AI | Assistant intents and refusals | product | planned (P3 and P4) |
| TIER-PERF | Candidate cost observations, not a production SLO | DuckDB, Databricks | reported, logs not retained: 3 M rows on both, 100 M rows on Databricks ([08](08-complexity-and-performance.md)). Not a gate yet |

The two-engine design is deliberate. The empty-input difference between DuckDB and Databricks (EC-EMPTY-TOTAL) was found only because the same test ran on both. A local pass alone does not establish target-engine behavior.

## Test inventory

Column "Engines": **both** means the test runs on DuckDB and on Databricks. **local** means it needs no database or uses DuckDB features on purpose.

| Test | Engines | Covers |
|---|---|---|
| `test_s4_matches_business_case_grid` | both | CASE-S4-PARITY: Sent and Delivery Rate in the illustrative S4 grid; not other production KPIs |
| `test_s4_is_12_grouping_sets_and_56_rows` | both | PLAN-AXIS |
| `test_single_statement_equals_one_query_per_node` | both | FP-10 oracle |
| `test_mean_of_rates_is_wrong`, `test_year_total_mean_of_rates_is_wrong` | both | PRB-TOTALS-RATE, EC-RATE-WEIGHT |
| `test_unique_clients_do_not_add_up` | both | PRB-TOTALS-DISTINCT |
| `test_cross_kpi_union_is_not_a_sum` | both | PRB-TOTALS-UNION |
| `test_ctor_from_atoms_equals_click_rate_over_open_rate`, `test_mean_of_cell_ctor_is_not_total_ctor` | both | PRB-COMPOSE, EC-COMPOSE-ORDER |
| `test_a_ctr_label_has_two_readings_that_disagree` | both | PRB-NAMING |
| `test_baseline_statement_count_vs_one_pass[S1..S4]` | DuckDB (Databricks skipped, see benchmark) | PRB-BASELINE |
| `test_ec_null_member_looks_like_subtotal` | both | EC-NULL-MEMBER |
| `test_ec_empty_cell_ratio_is_null_not_zero` | both | EC-DIV0 (raw SQL) |
| `test_ec_zero_denominator_in_a_non_empty_node_gives_null_rates_through_the_planner` | both | EC-DIV0 (planner). Mutation M1 dies here |
| `test_ec_empty_input_yields_no_node_rows_on_every_engine` | both | EC-EMPTY-TOTAL, ADR-006 |
| `test_ec_event_fanout_inflates_open_count` | both | EC-FANOUT-EVENT |
| `test_ec_scd2_dimension_duplicates_facts` | both | EC-SCD2 |
| `test_ec_period_filter_and_year_column_and_prior_year` | both | EC-PERIOD-CTX |
| `test_ec_single_child_subtotal_duplicates_parent` | both | EC-SINGLE-CHILD |
| `test_ec_gid_first_column_is_the_highest_bit` | both | EC-GID |
| `test_ec_ctor_above_one_when_a_click_has_no_open` | both | EC-CTOR-GT-ONE |
| `test_ec_unknown_atom_fails_closed` | local | EC-DEP, V-01 |
| `test_ec_dimension_cap_and_duplicates_fail_closed` | local | EC-GSET-EXPLOSION, EC-DUP-DIM |
| `test_ec_time_zone_decides_the_year` | local (DuckDB) | EC-TZ |
| `test_article_wrong_totals`, `test_article_fanout`, `test_article_distinct_union_and_conversion`, `test_article_yoy_table` | both | ART-WORKED |
| `test_drill_across_matches_per_fact_oracle_and_avoids_fanout` | both | PLAN-DRILL, EC-FANOUT-FACTS |
| `test_drill_across_keeps_null_member_and_subtotal_apart` | both | PLAN-DRILL x EC-NULL-MEMBER. Mutation M4 dies here |
| `test_planner_without_kpi_formulas_is_valid_sql_on_every_engine` | both | EC-SQL-SYNTAX (found by the Databricks benchmark) |
| Seven `test_tutorial_step*` functions (engine-parametrized) | both | tiny-example cells, totals, rates, overlap and join examples in [START-HERE](START-HERE.md); not warehouse timings |
| `test_tutorial_step8_a_view_of_a_rate_cannot_be_regrouped` | both | PRB-COMPOSE: SQL composes relations, not measures ([05](05-first-principles-solution.md)) |
| `test_mean_of_rates_error_is_group_count_times_covariance_of_weight_and_rate`, `test_displayed_rates_alone_cannot_determine_the_total` | local | C-FORMULA: size, sign and irreparability of the averaging error |
| `test_distinct_scalars_only_bound_the_total` | local | C-STATE: bounds on a unique total |
| `test_a_correct_total_can_reverse_a_comparison_and_the_gap_splits_into_mix_and_rate` | local | C-CONTEXT: comparison of segments with different mix |
| `test_s4_grid_reconciles_on_every_lattice_edge`, `test_a_real_null_member_is_a_child_and_not_a_total` | both | C-CHECK I1 to I4 hold on correct grids; 17 parent/child shape pairs in S4 |
| `test_reconciliation_detects_mixed_snapshots_and_truncated_results`, `test_an_averaged_rate_passes_the_bounds_and_fails_the_formula` | both | C-CHECK detects EC-SNAPSHOT, EC-RESULT-TRUNCATION and EC-RATE-WEIGHT symptoms from the rows alone |
| `test_reconciliation_cannot_see_an_error_repeated_at_every_scope`, `test_a_summed_audience_is_caught_only_when_another_breakdown_bounds_it` | both | Limits of C-CHECK: uniform fan-out and summed audiences can pass |
| `test_additivity_probe_separates_counts_rates_and_distincts` | both | EDGE-PROBE on synthetic data |
| `test_edge_parses_and_round_trips_planner_sql_for_databricks` | local | EDGE-OK-01, EC-PLAN-INVALID |
| `test_edge_can_inspect_tables_and_inject_a_typed_filter_into_the_agg_scope` | local | EDGE-OK-02 |
| `test_edge_gap_01_template_slot_keeps_its_name` (xfail) | local | EDGE-GAP-01, EC-SLOT-NAME |
| `test_edge_gap_02_slot_is_listed_once` (xfail) | local | EDGE-GAP-02, EC-DUP-SLOT |
| `test_dbx_ansi_mode_raises_on_division_by_zero_and_the_guard_returns_null` | Databricks | EC-DIV0 on the target, FP-11 |
| `test_dbx_null_safe_equality_both_spellings` | Databricks | EC-NULLSAFE-EQ |
| `test_dbx_grouping_id_type_is_wide_enough` | Databricks | EC-GID (type is `bigint`) |
| `test_dbx_hll_sketch_tracks_exact_distinct_and_mismatched_lgk_fails` | Databricks | EC-HLL-LGK, SEM-CLASS |
| `test_dbx_edgesql_gated_sql_executes_and_returns_the_same_rows` | Databricks | EDGE-OK-01 on the target |
| `test_dbx_time_zone_must_be_declared` | Databricks | EC-TZ on the target |
| `test_dbx_explain_shows_one_scan_and_an_expand_for_the_grouping_sets` | Databricks | plan contains a scan and an Expand; the current assertion does not establish exactly one of each |

An `xfail(strict=True)` test fails the run when it unexpectedly passes. The day EdgeSQL accepts placeholders, the build tells us to remove the markers and close the gap.

## Mutation check (TIER-MUT)

A mutation check asks whether deliberate mistakes are detected. `mutation_check.py` applies one change at a time to the prototype. Its current implementation treats every nonzero pytest exit as a kill, including collection or infrastructure errors. Before using mutation scores as a release gate, require a clean unmutated baseline and verify that a relevant assertion failure killed each mutant.

| Mutant | Killed by |
|---|---|
| M1 remove the `NULLIF` guard | `test_ec_zero_denominator_in_a_non_empty_node_...` |
| M2 reverse the `GROUPING_ID` argument order | `test_ec_gid_first_column_is_the_highest_bit` |
| M3 drop the grand-total node | `test_s4_matches_business_case_grid` |
| M4 join drill-across parts without `gid` | `test_drill_across_keeps_null_member_and_subtotal_apart` |
| M5 use `=` where null-safe equality is needed | `test_drill_across_matches_per_fact_oracle_and_avoids_fanout` |
| M6 remove the dimension cap | `test_ec_dimension_cap_and_duplicates_fail_closed` |
| M7 ignore unknown atoms | `test_ec_unknown_atom_fails_closed` |

M4 is killed only because a drill-across test uses a NULL member. The script asserts that each mutation pattern is found before running, so a mutant cannot survive vacuously.

## Traceability matrix: problem to proof

Read left to right. Every problem of [03](03-problem-catalogue.md) reaches a principle, a place in the spec, an edge case and at least one test. Rows without a test say so.

| Problem ([03](03-problem-catalogue.md)) | Principle | Spec | Edge case | Tests |
|---|---|---|---|---|
| PRB-TOTALS-ADD | FP-4 | PLAN-TOTAL | EC-SINGLE-CHILD | `test_ec_single_child_subtotal_duplicates_parent`, `test_s4_matches_business_case_grid` |
| PRB-TOTALS-RATE | FP-1, FP-2, FP-4 | SEM-L1, PLAN-TOTAL, C-FORMULA | EC-RATE-WEIGHT | `test_mean_of_rates_is_wrong`, `test_year_total_mean_of_rates_is_wrong`, `test_mean_of_rates_error_is_...` |
| PRB-TOTALS-DISTINCT | FP-1, FP-4 | SEM-CLASS, C-STATE | EC-DISTINCT-OVERLAP | `test_unique_clients_do_not_add_up`, `test_distinct_scalars_only_bound_the_total` |
| PRB-TOTALS-UNION | FP-4 | SEM-UNION | EC-DISTINCT-OVERLAP | `test_cross_kpi_union_is_not_a_sum` (definition gated by the business) |
| PRB-COMPOSE | FP-2 | SEM-L1, [05](05-first-principles-solution.md) | EC-COMPOSE-ORDER | `test_ctor_from_atoms_...`, `test_mean_of_cell_ctor_...`, `test_tutorial_step8_...`; Malloy probe in [validation](validation/2026-11-12-malloy/README.md) |
| PRB-BASELINE | FP-5 | PLAN-ONEPASS, PLAN-SPLIT | EC-DISTINCT-COST, EC-HLL-ERROR | `test_baseline_statement_count_vs_one_pass`, `test_dbx_explain_...`; timings in [08](08-complexity-and-performance.md) (3 M and 100 M rows). The split plan itself: **no test yet (B6)** |
| PRB-COLUMN-PIVOT | FP-3 | PLAN-AXIS | EC-GSET-EXPLOSION | `test_s4_is_12_...`, `test_s4_matches_business_case_grid` |
| PRB-FILTER-VS-COLUMN | FP-3 | PLAN-CONTEXT | EC-PERIOD-CTX, EC-TZ | `test_ec_period_filter_...`, `test_article_yoy_table`, `test_ec_time_zone_...`, `test_dbx_time_zone_...` |
| PRB-PERIOD-COMPARE | FP-3 | SEM-L2 | EC-PERIOD-CTX | window rule tested. General planner: **no test yet (P4)** |
| PRB-GRAIN-FANOUT | FP-6 | PLAN-GRAIN, DB-GRAIN | EC-FANOUT-EVENT, EC-SCD2, EC-FANOUT-FACTS, EC-M2M | `test_ec_event_fanout_...`, `test_ec_scd2_...`, `test_article_fanout`, `test_drill_across_...`. M2M: **no test yet (P2)** |
| PRB-NAMING | FP-7 | SEM-GATE | EC-NAMING | `test_a_ctr_label_has_two_readings_that_disagree`. Gate: **no test yet (P1)** |
| PRB-REACH | FP-7 | SEM-GATE, EDGE-PROBE | EC-REACH-AMBIG | `test_additivity_probe_...` (synthetic). Gate: **no test yet (P1)**. Probe on a real registry: **not run (P0)** |
| PRB-TRUNC | FP-7 | SEM-GATE | EC-TRUNC | decision, no code |
| PRB-REGISTRY-TEMPLATE | FP-9 | EDGE-GAP, EDGE-MAP | EC-FILTER-NOPLACEHOLDER, EC-SLOT-NAME, EC-DUP-SLOT | the two `xfail` tests. Migration: **no test yet (P2)** |
| PRB-REGISTRY-LOOKUP | FP-9 | SEM-ER | EC-NAMES | **no test yet (P2)** |
| PRB-UNVERIFIED | FP-10 | fixtures | none | the fixture reproduces the illustrative grid: `test_s4_matches_business_case_grid` on both engines |

### Scope table, row by row

The scope table lists ten kinds of cell. The prefix-rollup prototype covers the core Sent/Delivery scopes. The optional Market-only scope is not produced; cross-KPI union is demonstrated in handwritten SQL, not supported by the generic planner.

| Cell kind | Node (row scope x column scope) | Covered by |
|---|---|---|
| Ordinary KPI cell | detail x detail | `test_s4_matches_business_case_grid` (`gid` 0) |
| Row subtotal per Year and Market | typology+tier x year+market | same, row `New / Gold` |
| Higher row subtotal | typology x year+market | same |
| Column subtotal for Year | detail x year | same, "2025 Total" and "2026 Total" |
| Optional column subtotal by Market | detail x market only | **not produced** (not a rollup prefix, PLAN-AXIS `extra_sets`, P4) |
| Row subtotal x column subtotal | e.g. typology+tier x year | same |
| Row grand total per Year and Market | () x year+market | same, "Total" row |
| Column grand total per row | detail x () | same, "Grand total" column |
| Grand total x grand total | () x () | same, 1,050 and 82.4 percent |
| Cross-KPI union | any x any | `test_cross_kpi_union_is_not_a_sum` (handwritten SQL only; definition and planner support gated) |

## End-to-end tests (planned, P3)

One per applicable acceptance criterion of [12](12-ux-and-wireframes.md): UX-01 to UX-14. Initial-release checks and optional-capability checks are identified there. No UI or API implementation exists yet. Plus API-level:

| Id | Check |
|---|---|
| E2E-API-01 | S4 Sent/Delivery returns the expected values at 56 populated node rows and 12 grouping-set ids before presentation hiding. Report actual statements; equivalent physical plans may use different counts |
| E2E-API-02 | Unknown KPI id returns 422 `SEM_UNKNOWN_REF` naming the id |
| E2E-API-03 | Unconfirmed KPI on a published report returns 422 `SEM_UNCONFIRMED` |
| E2E-API-04 | One failed fact is named; independent KPIs remain available and all dependent KPIs have `dependency_failed`. Nothing is silently filled with zero |
| E2E-API-05 | Two users with different row policies never share a cache entry |
| E2E-API-06 | If cache is enabled, identical authorized intent/version/snapshot/policy can hit it; any change invalidates it. If disabled, both requests execute normally |
| E2E-API-07 | A model-proposed intent with a SQL-looking string in a filter value is refused or bound as a value, never executed |

## Required contract checks still to implement

These are planned tests, not evidence of current support. Each compares the enabled backend with an independent oracle.

| Id | Required behavior | Gate |
|---|---|---|
| CONTRACT-SCOPE | Grand totals remove grouping dimensions while retaining selected date, market, channel and authorization filters | P1/P3 |
| CONTRACT-PLAN | Fused, split and two-stage exact plans return the same node values and statuses | before each optimization |
| CONTRACT-SNAPSHOT | Multi-statement execution and retries use compatible source versions; late data cannot create a mixed-snapshot ratio | before multi-statement published execution |
| CONTRACT-PERIOD | Prior period aligns calendar boundaries, timezone, partial periods and leap-day policy; it never widens non-time filters | before comparison capability |
| CONTRACT-IDENTITY | Distinct and union require the same entity namespace, identity expression and null policy; test overlapping, disjoint and all-null populations | P1 for distinct; before union |
| CONTRACT-RESULT | Executor retrieves all result chunks or explicitly fails on truncation; row counts reconcile with the manifest | P1 |
| CONTRACT-POLICY | Two effective policies cannot share unauthorized results; rollups preserve authorized populations or are bypassed | before cache/rollup publication |
| CONTRACT-STATUS | `no_data`, zero denominator, failed dependency, zero count and unknown identity remain distinguishable | P1/P3 |
| CONTRACT-NATIVE | Native and custom candidates are assessed against the same required S1–S4 contract | P0 backend decision |
| CONTRACT-RECONCILE | The assembler runs the C-CHECK invariants on the complete result before display filtering and fails or flags the report on a violation. Prototype helper and tests exist; the product check does not | P1, and before any multi-statement plan |

## Reproducible evidence pack

For a new run, retain the fixture and source hashes, dependency versions, test command and output, engine/runtime and warehouse configuration, exact intent/SQL, execution identity and snapshot identifiers. For benchmarks retain each trial, query ids, cache conditions, concurrency, full result retrieval and query-profile metrics. Check parity before comparing speed. A changing literal is an attempted cache avoidance technique, not proof that result caching was bypassed.

The checked-in Databricks benchmark covers sequential baseline, fused exact, additive-only, HLL lgK 12 and two-stage candidates. It does not currently reproduce every separately reported exact-distinct or lgK 14 observation. The adapter currently consumes the initial `data_array` only; complete retrieval and truncation checks need implementation. These limits do not change the small fixture's arithmetic, but constrain generality and reproducibility claims.

## What is NOT proven yet

Stated plainly, so nobody reads more into the green runs than they show:

| Not proven | Why | Where it goes |
|---|---|---|
| Any product code | Only the spike exists | P1 |
| A real KPI registry and its SQL | Only synthetic templates exist in this repository | P2 |
| Any production KPI value | All values come from synthetic fixtures and the definitions are examples | [03](03-problem-catalogue.md) PRB-UNVERIFIED |
| Performance at production scale | One 2X-Small warehouse, synthetic data, one to three runs per number. The 100 M run shows one pass is no faster than 72 statements when an exact distinct atom is present | [08](08-complexity-and-performance.md), B4 to B7 |
| Row-level security, rollups, cache | Not built | published-use gate; optimizations can remain disabled |
| The UI and the AI assistant | Not built | P3 |
| Production metric-view backend | Core default S4 calculation parity is retained; production filters, policy, complete source mapping and comparative cost are still open | P0, ADR-001 |
| Malloy on Databricks | The probe ran on local DuckDB. The Databricks connector, policies under the caller's identity, ANSI division behaviour and cost are untested | Only if Malloy enters the P0 comparison ([05](05-first-principles-solution.md)) |
| What Reach means | The additivity probe has run on synthetic data only | P0, EDGE-PROBE, then owner decision |
| The article's own claims (LLM accuracy gain, semantic-cache hit rate, Yardstick, Malloy) | Quoted, not reproduced | [04](04-article-reformulated.md) |
