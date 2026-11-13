# Retained validation: migration by inference on Databricks — 12 November 2026

**Question:** does the inferred, rewritten statement return the same values as the legacy templates when both run natively on Databricks, with joins, named date parameters, optional filters and Databricks functions?

**Answer for the tested case: yes.** 200 legacy values compared, none different, under three parameter settings. The inference made on Databricks is identical to the one made locally on DuckDB.

This is a synthetic test. The six KPI ids are generic examples and all eight templates are written for this study. It says nothing about any real registry, production data, access rules or cost.

## What ran

| Item | Value |
|---|---|
| Script | [migrate_registry.py](../../../../examples/walkthrough/migrate_registry.py) with `--databricks` |
| Input | [templates.sql](../../../../examples/registry/templates.sql): eight templates in Databricks SQL |
| Data | [data.sql](../../../../examples/registry/data.sql): 13 messages, 6 clients, 14 events |
| Warehouse | serverless SQL warehouse, 2X-Small (identifiers withheld). It was stopped, was started by this run, and was stopped again afterwards |
| Statements | 93 in total: setup, join checks, 72 legacy executions and 3 migrated executions |
| Record | [databricks-run.json](databricks-run.json) |

The run **creates or replaces a schema and three tables**: `workspace.edgekpi_migration.client`, `.message` and `.message_event`. They are small and synthetic. To remove them, drop the schema `workspace.edgekpi_migration`.

## Result

| Check | DuckDB | Databricks |
|---|---|---|
| Templates accepted / refused | 6 / 2 | 6 / 2 |
| Measures inferred | 5 | 5, the same |
| Optional filters and parameters inferred | 2 filters, `start_date` and `end_date` | the same |
| Join check: joined rows = distinct message keys = messages | 13 = 13 = 13 | 13 = 13 = 13 |
| Parameter settings | 3 | 3 |
| Groups returned by the migrated statement | 34 | 34 |
| Legacy values compared | 200 | 200 |
| of which NULL for a zero denominator, on both sides | 18 | 18 |
| Values that differ | 0 | 0 |
| Values that exist only after migration | 4, all `reached` = 0 | 4, all `reached` = 0 |

The two refusals are intended. `open-events` joins messages to their events: 13 messages become 14 rows covering 7 messages, so the join changes the grain. `messages-per-client` has two aggregations.

## What each case shows

| Case | Evidence |
|---|---|
| Joins | A join is accepted only when the data shows one row per message afterwards. The dimension join passes; the event join is refused with its counts |
| Date parameters | `:start_date` and `:end_date` stay named parameters. On Databricks they were bound through the Statement Execution API, including NULL |
| Optional filters | The `:p IS NULL OR …` pattern is recognised and kept unchanged in the shared row filter. Results match with no date, a start date only, and both dates |
| Databricks functions | `try_cast`, `try_divide`, `count_if`, `FILTER (WHERE …)`, `NULLIF`, `SUM(CASE …)` and `COUNT(DISTINCT …)` were executed natively, in the legacy templates and in the migrated statement |
| The six KPI ids | Sent, Reached, Delivery Rate, Open Rate, Click Rate and CTOR are inferred as five measures and six expressions. `COUNT_IF(p)`, `SUM(CASE WHEN p THEN 1 ELSE 0 END)` and `COUNT(*) FILTER (WHERE p)` are recognised as one measure |

## Limits

- **No real registry was used.** All templates are synthetic. Running the tool on an export of a real registry is the next step and may reveal shapes this test does not contain.
- A registry's structured join and filter columns, if it has them, are not read; joins and filters are taken from the SQL text.
- One source with one many-to-one join. Type-2 dimensions with validity dates, several facts and many-to-many joins are not covered.
- The join check counts rows on the data present at migration time. It does not prove the join stays one-to-one as data changes; that needs a recurring data-quality check.
- No access rules, no production volumes, no timing. The compute runtime version was not captured.
- The grand-total reference cannot be written with the legacy slot, so it is obtained by removing the slot from the parsed template.

## Reproduce

```bash
python ../../../../examples/walkthrough/migrate_registry.py              # DuckDB only, no network

export DATABRICKS_CONFIG_PROFILE=your-profile EDGEKPI_DBX_WAREHOUSE=your-warehouse-id
uv run --with duckdb==2.0.0 --with sqlglot==30.25.0 --with databricks-sdk \
  python ../../../../examples/walkthrough/migrate_registry.py --databricks
```

The Databricks run starts the warehouse if needed, creates or replaces the three tables, and rewrites `databricks-run.json`. The local run used DuckDB 2.0.0 and sqlglot 30.25.0; the Databricks run used databricks-sdk 0.166.0.
