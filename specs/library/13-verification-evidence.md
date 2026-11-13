# 13. Verification evidence

> What ran, where, with what result, and what none of it proves. The numbers below come from commands in this repository; the Databricks record is a retained file.

Related: [README](README.md) · [11 test strategy](11-test-strategy-and-e2e.md) · [12 plan](12-implementation-plan.md) · [10 open cases](10-edge-cases-and-state-charts.md#envisioned-and-not-mitigated-open) · [kpi validation](../kpi/validation/2026-11-12/README.md)

## Summary

| Claim | Evidence | Where |
|---|---|---|
| One definition, five backend/engine pairs, nine request shapes: 45 comparisons with the independent reference, **0 differences, 0 violations** | [run-2026-11-12-databricks.json](evidence/run-2026-11-12-databricks.json) | `python scripts/record_evidence.py --databricks` |
| All three approaches execute on Databricks: generated SQL, a native metric view, and Malloy through its own Databricks connection | the same file; `sql on databricks`, `metric view on databricks`, `malloy on databricks` | pairs 3, 4 and 5 |
| Migration keeps every legacy value: 200 compared, 0 different, on DuckDB and on the warehouse | `test_inference_and_intent.py::test_parity_with_the_legacy_templates_on_every_value`, `test_inference_and_intent.py::test_the_migration_keeps_every_legacy_value_on_a_databricks_warehouse` | |
| The suite notices broken rules: 19 of 19 mutants killed | `python scripts/mutation_check.py` | [11](11-test-strategy-and-e2e.md#mutation-check) |
| The documents match the code | `tests/test_docs.py` | [11](11-test-strategy-and-e2e.md#the-documents-are-tested) |

## The Databricks run

From the retained record, [run-2026-11-12-databricks.json](evidence/run-2026-11-12-databricks.json):

| Item | Value |
|---|---|
| Date | 2026-11-12 |
| Platform | Databricks, serverless SQL warehouse (workspace, user and warehouse identifiers withheld) |
| Warehouse | Serverless Starter Warehouse, 2X-Small |
| Schema | `workspace.edgekpi_lib`, created by the run |
| Tables created or replaced | `client`, `message`, `message_event`: small synthetic tables from [data.sql](../../examples/registry/data.sql) |
| Also created | one metric view per model version: `edgekpi_engagement_<fingerprint>` |
| Statements run by the library's SQL engine | 31, each with a retained statement id |
| Statements run by Malloy's connection | not counted: they use Malloy's own connection |
| Versions | Python 3.12.7, sqlglot 30.25.0, duckdb 2.0.0, Malloy 0.0.437, edgekpi 0.1.0 |
| Comparisons | 9 requests × 5 pairs = 45; failed 0 |

Per request, every pair returned the same grid as the reference:

| Request | Nodes | sql duckdb | malloy duckdb | sql warehouse | metric view | malloy warehouse |
|---|---|---|---|---|---|---|
| `pivot-with-params-and-where` | 9 | ok | ok | ok | ok | ok |
| `grand-total-only` | 1 | ok | ok | ok | ok | ok |
| `two-row-levels` | 26 | ok | ok | ok | ok | ok |
| `year-function-no-params` | 11 | ok | ok | ok | ok | ok |
| `totals-off` | 6 | ok | ok | ok | ok | ok |
| `empty-input` | 0 | ok | ok | ok | ok | ok |
| `where-eq-off-axis` | 3 | ok | ok | ok | ok | ok |
| `end-date-only` | 3 | ok | ok | ok | ok | ok |
| `zero-denominator-group` | 3 | ok | ok | ok | ok | ok |

**What was done in the workspace.** The warehouse was started by the first statement and stopped by auto-stop after the run. The schema and tables listed above remain; drop `workspace.edgekpi_lib` to remove them, with the metric views it contains. The earlier schemas `workspace.edgekpi_spec` and `workspace.edgekpi_migration` were not touched.

**How the Malloy run authenticates.** The Databricks SDK session supplies a short-lived access token; it is given to the Node process through its environment and appears in no file, log or record. The record holds the warehouse's HTTP path and the package version, not the token ([ADR-L-11](12-implementation-plan.md#decisions)).

## The local suite

| Command | Result |
|---|---|
| `pytest -m "not databricks and not malloy"` | 206 passed, 39 deselected; needs neither node nor a warehouse |
| `pytest -m "not databricks"` | 217 passed, 28 deselected; adds the Malloy-on-DuckDB pairs |
| `pytest` with `DATABRICKS_CONFIG_PROFILE` and `EDGEKPI_DBX_WAREHOUSE` | all 245 tests (library, service layer and documents), including the three warehouse pairs and the migration parity on the warehouse |
| `python scripts/mutation_check.py` | 19 of 19 killed |

Counts change with every test added; the suite is the authority.

## Limits

Read these before relying on the results.

1. **Synthetic data.** Thirteen messages, six clients. The matrix proves the logic and the engine agreement on cases the data contains; it says nothing about production volume, skew or data quality.
2. **Example registry.** The templates are written for this repository ([06](06-inference-and-migration.md)). A production registry may hold shapes they do not contain, for instance joins and filters kept in separate JSON columns.
3. **No cost or latency measurement.** [09](09-complexity-and-performance.md) gives the shape of the cost and one linear-time measurement of the reconciliation, not warehouse timings.
4. **Grain proved on today's data.** `check-grain` reads the tables once; a later load can break it.
5. **The oracle shares the rendering of dimensions, joins and filters** with the backends ([11](11-test-strategy-and-e2e.md#what-the-reference-shares)).
6. **The mutation check does not run the Malloy or warehouse paths.** Those are protected by their text-level tests and the matrix, which was run once on the warehouse and is not part of every local run.
7. **Not covered**: type-2 dimensions, several fact tables, row-level permissions, time zones, concurrency, results above one chunk ([10](10-edge-cases-and-state-charts.md#envisioned-and-not-mitigated-open)).
8. **One workspace, one warehouse size, one day.** Another workspace may differ in metric-view syntax support or defaults.
9. **A shared environment.** The run used a personal development workspace and its own credentials; nothing was run against a production catalogue.

## Reproduce

```
uv venv .venv --python 3.12 && uv pip install -e ".[dev]"
(cd edgekpi/backends/malloy_runtime && npm install)
export DATABRICKS_CONFIG_PROFILE=<profile> EDGEKPI_DBX_WAREHOUSE=<warehouse id>
python -m pytest
python scripts/mutation_check.py
python scripts/record_evidence.py --databricks
```
