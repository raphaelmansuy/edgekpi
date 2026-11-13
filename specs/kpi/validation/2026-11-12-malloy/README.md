# Retained validation: Malloy probe — 12 November 2026

**Question:** can a composable-measure language such as [Malloy](https://github.com/malloydata/malloy) express the scenario 4 pivot and return correct totals at every scope?

**Answer for the tested case: yes.** One Malloy query returned the same 56 member groups as the SQL reference, with all five integer aggregates equal and all four rates equal within `1e-12`. This is a local DuckDB probe of the synthetic fixture. It says nothing about Databricks execution, security policies, production definitions or performance. The decision it informs is in [05](../../05-first-principles-solution.md).

## What ran

| Item | Value |
|---|---|
| Data | [s4_messages.sql](../../fixtures/s4_messages.sql): 1,050 rows, 1,050 distinct message ids (same fixture hash as the [Databricks evidence](../2026-11-12/README.md)) |
| Reference | [generated-s4.sql](../2026-11-12/generated-s4.sql), the retained `GROUPING SETS` statement, run on the same in-memory DuckDB connection |
| Candidate | [s4.malloy](s4.malloy): nine measures defined once, then one nested query |
| Engine | DuckDB v1.5.5 bundled with `@malloydata/db-duckdb` 0.0.437; `@malloydata/malloy` 0.0.437; Node v24.14.1 |
| Result | [probe-result.json](probe-result.json): 56 groups, 56 distinct keys, 0 mismatches |

## What the probe shows

| Observation | Evidence | Consequence |
|---|---|---|
| Measures compose across grains | Each measure is written once in [s4.malloy](s4.malloy) and reused at 12 nesting levels. No grouping is stored in a definition | Malloy removes the need for `{{ group_by_list }}` text templates |
| Totals are computed at their own scope | Unique clients match at every level, including the overlapping ones (175 and 180 by year, 180 in total) | The nested result is a correct implementation of the scope rule, not a sum of cells |
| The plan is the same idea as `GROUPING SETS` | [malloy-generated-s4.sql](malloy-generated-s4.sql) has one statement, one `FROM message`, a `CROSS JOIN GENERATE_SERIES(0,11,1)` and 12 `count(distinct ...)` expressions | Each fact row is expanded once per grouping shape. Malloy does not remove the exact-distinct cost recorded in [08](../../08-complexity-and-performance.md) |
| No zero-denominator guard is added | `opened / delivered` with zero delivered returned `NaN` on DuckDB. The generated SQL contains no `NULLIF` unless the model writes `nullif(...)` | Every ratio measure needs an explicit guard. On Databricks ANSI mode an unguarded division is expected to raise; this was **not** tested |
| The result is a nested tree | The probe flattens it to `(typology, tier, campaign, year, market)` keys | Node identity comes from the nesting path instead of `gid`, and the pivot assembler would read a tree instead of flat rows. Behaviour with a real NULL member was not tested |

## Reproduce

Dependencies are installed outside the repository. Only the two top-level packages are pinned; their transitive dependencies are not locked here.

```bash
npm install --prefix /tmp/edgekpi-malloy @malloydata/malloy@0.0.437 @malloydata/db-duckdb@0.0.437
NODE_PATH=/tmp/edgekpi-malloy/node_modules node specs/kpi/validation/2026-11-12-malloy/malloy_s4_probe.js
```

The script exits non-zero on any mismatch. Add `--write-sql` to regenerate `malloy-generated-s4.sql`.

| File | SHA-256 |
|---|---|
| `s4.malloy` | `7469476d9ba9d5d8fba5ac9865673d904c0c19256ea37d972587bfd16aebbba2` |
| `malloy_s4_probe.js` | `832c9df78c2856724171d08ff69e45f7f4bbdb40fb552447d915fb1eee7885b6` |
| `malloy-generated-s4.sql` | `91c39625347c394ac81bf5b384a20486070a90b174eb527fc53e48a0393e65e3` |
| `probe-result.json` | `483267c195d99cbd9c97ca625943042c80fd6b3f4516dae225a53f0f8bfcfb5d` |
| `../../fixtures/s4_messages.sql` | `f66d9a440eb12d6299825a661d7e96ac40590c32a246542eb2aef27f36f58528` |

## Limits of this evidence

- **DuckDB only.** The Malloy repository contains a `malloy-db-databricks` package, published as `@malloydata/db-databricks` 0.0.437. It was not installed or run. Dialect coverage, Unity Catalog row filters and masks under the caller's identity, and result paging are untested.
- **One shape.** Only the non-empty default scenario 4 pivot was compared. Real NULL members, empty populations, the optional Market-across-years scope, filters, mixed facts and prior-period contexts were not exercised.
- **No timing.** No latency, plan profile or cost was measured. The generated SQL suggests the same row expansion as `GROUPING SETS`; that is a reading of the SQL text, not a measurement.
- **Not a product assessment.** Version 0.0.x packages, the release cadence, support and the operating cost of a second modelling language and a Node runtime are for the technical owner to weigh.
- The synthetic formulas and client identities are not approved production definitions.
