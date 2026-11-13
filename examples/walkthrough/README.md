# Walkthrough examples

The same small pivot, Typology × Market with totals over eight messages, written three ways, followed by a migration example that infers measures and expressions from legacy templates. These are the code samples printed in [the briefing note](../../specs/kpi/briefing/why-a-sql-query-is-not-a-kpi.pdf).

| File | Option | Status |
|---|---|---|
| [message.sql](message.sql) | Example data: one row per message | Loaded by both verification scripts |
| [1-metric-view.sql](1-metric-view.sql) | Databricks metric view | **Not executed in this form.** Reduced from the [scenario 4 statement](../../specs/kpi/validation/2026-11-12/native-s4.sql) that ran on a Databricks serverless SQL warehouse. The `CREATE OR REPLACE VIEW … WITH METRICS LANGUAGE YAML` form and the `comment` keys follow the Databricks documentation; the retained run used a temporary view without comments |
| [2-engagement.malloy](2-engagement.malloy) | Malloy | Executed on DuckDB: nine member groups match |
| [3-definitions.yaml](3-definitions.yaml), [3-request.json](3-request.json) | Generated SQL: catalogue entry and report request | Proposed formats, not implemented |
| [3-generated.sql](3-generated.sql) | Generated SQL: the statement the prototype planner produces | Executed on DuckDB: nine member groups match |
| [4-legacy-templates.sql](4-legacy-templates.sql) | Migration input: four KPI templates in the common registry pattern | Synthetic |
| [migrate_templates.py](migrate_templates.py), [4-migrated.sql](4-migrated.sql) | Migration by inference: parses the templates, infers measures and expressions, writes one statement with totals | Executed on DuckDB: 31 legacy values compared, none different |
| [templates.sql](../registry/templates.sql), [data.sql](../registry/data.sql) | Harder migration input: six KPI ids with a join, optional date parameters and Databricks functions, plus two templates that must be refused | Synthetic |
| [migrate_registry.py](migrate_registry.py), [5-migrated-databricks.sql](5-migrated-databricks.sql), [5-inferred.json](5-inferred.json) | Harder migration: join checks, parameters, optional filters, one measure per spelling, a Databricks statement and the inferred definitions | Executed on DuckDB **and natively on Databricks**: 200 legacy values compared on each, none different ([evidence](../../specs/kpi/validation/2026-11-12-migration/README.md)) |

## Migration by inference

`migrate_templates.py` reads each legacy template as a syntax tree with sqlglot and keeps the shape it can rewrite: one aggregation over one source, grouped by the grouping slot alone. From the three templates of that shape it infers:

| Inferred | Value |
|---|---|
| Measure `m1` | `COUNT(*)`, shared by `sent` and `delivery_rate` |
| Measure `m2` | `COUNT(*) FILTER(WHERE C.is_delivered)` |
| Measure `m3` | `COUNT(DISTINCT C.client_id) FILTER(WHERE C.is_delivered)` |
| Expressions | `sent = m1`, `delivery_rate = m2 * 1.0 / NULLIF(m1, 0)`, `reached_clients = m3` |
| Refused | `messages_per_client`: more than one aggregation |

It then runs every template the legacy way at each of the four groupings and compares each value with the migrated statement. The data is `message.sql` plus one undelivered message in a market of its own.

- 11 groups, 31 legacy values compared, 0 different.
- Two groups exist only after migration: `reached_clients` is 0 where the legacy query returns no row. Moving a `WHERE` condition into a measure turns "no row" into zero, so an empty-group rule has to be chosen.
- The legacy template has no valid form for a grand total, because an empty column list is a syntax error. The script obtains that reference by removing the slot from the parsed tree.

Not covered by this first test: joins, date parameters, optional filters and Databricks functions. The next section covers them. Measure names `m1` to `m3` are placeholders for an owner to rename.

## Harder cases

`migrate_registry.py` runs the same inference on eight templates written in Databricks SQL: six KPI ids and two templates that must be refused.

| Case | What the script does | Result |
|---|---|---|
| Joins | Runs each join on the data and accepts it only if joined rows = distinct message keys = messages | The client join passes (13 = 13 = 13). `open-events`, which joins message events, is refused: 13 messages become 14 rows covering 7 messages |
| Date parameters | Keeps `:start_date` and `:end_date` as named parameters | Bound on DuckDB and through the Databricks Statement Execution API, NULL included |
| Optional filters | Recognises `:p IS NULL OR …` and keeps it as a shared row filter | Values match with no date, a start date only, and both dates |
| Databricks functions | Parses `try_cast`, `try_divide`, `count_if`, `FILTER`, `NULLIF`, and writes Databricks SQL that parses back to the same text | Legacy templates and migrated statement executed natively on the warehouse |
| The six KPI ids | Infers five measures and six expressions. `COUNT_IF(p)`, `SUM(CASE WHEN p THEN 1 ELSE 0 END)` and `COUNT(*) FILTER (WHERE p)` become one measure | 3 parameter settings, 34 groups, 200 legacy values compared, 18 of them NULL on both sides, 0 different |

Four values exist only after migration, all `reached = 0`, for the same empty-group reason as in the first test. `messages-per-client` is refused for having two aggregations.

Still open: real registry rows. All eight templates are synthetic and are **not** production definitions. A registry's structured join and filter columns, if it has them, are not read; joins and filters are taken from the SQL text. Type-2 dimensions and several fact tables are not covered.

## Expected result

| Typology | Market | Sent | Delivery rate | Unique clients |
|---|---|---:|---:|---:|
| New | HK | 3 | 66.7% | 2 |
| New | SG | 1 | 100.0% | 1 |
| VIP | HK | 1 | 100.0% | 1 |
| VIP | SG | 3 | 66.7% | 2 |
| New | all markets | 4 | 75.0% | 3 |
| VIP | all markets | 4 | 75.0% | 2 |
| all typologies | HK | 4 | 75.0% | 3 |
| all typologies | SG | 4 | 75.0% | 3 |
| all typologies | all markets | 8 | 75.0% | 5 |

## Verify

From the repository root. Python uses the pinned [requirements-test.txt](../../specs/kpi/fixtures/requirements-test.txt). Node dependencies are installed outside the repository.

```bash
python verify_generated.py
python migrate_templates.py
python migrate_registry.py

npm install --prefix /tmp/edgekpi-malloy @malloydata/malloy@0.0.437 @malloydata/db-duckdb@0.0.437
NODE_PATH=/tmp/edgekpi-malloy/node_modules node verify_malloy.js
```

`verify_generated.py` also fails if `3-generated.sql` differs from what the prototype planner generates, and the two migration scripts fail if their generated files differ from what the rewrite produces. `migrate_registry.py --databricks` repeats its proof natively on a warehouse; it creates three small tables in `workspace.edgekpi_migration` and is described in the [validation record](../../specs/kpi/validation/2026-11-12-migration/README.md). Last run on 12 November 2026: DuckDB 2.0.0 and sqlglot 30.25.0 (Python), databricks-sdk 0.166.0, Malloy 0.0.437 with its bundled DuckDB, Node v24.14.1.

## Limits

- Apart from `migrate_registry.py --databricks`, nothing here ran on Databricks. To execute `1-metric-view.sql`, replace the example names with a real catalog, schema and source table; it creates a persistent view.
- The Malloy model reads `duckdb.table('message')`. A Databricks source needs a configured Databricks connection, which was not tested.
- The data is synthetic and the formulas are not approved production definitions.
