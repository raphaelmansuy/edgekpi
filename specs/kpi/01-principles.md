# Principles

> **In plain words.** Eleven short rules, all coming from one idea: keep the ingredients, cook the number last, choose the grouping when reading, compute every total at its own scope, and refuse to guess. Each rule names available evidence or the implementation gate; prototype tests do not establish production enforcement.
>
> New here? Read [START-HERE](START-HERE.md) first.

Date: 2026-11-12. Derived from [00-five-whys.md](00-five-whys.md) (`GOV-1`). Every later document cites these ids. They do not move without an ADR in [13-implementation-plan.md](13-implementation-plan.md).

## First principles

| Id | Principle | Why it holds | Evidence / implementation gate |
|---|---|---|---|
| FP-1 | Preserve sufficient aggregate state for the requested operation. | Sums can merge as numbers; rates need numerator and denominator, distincts need identity state or recomputation. | `test_mean_of_rates_is_wrong`, `test_unique_clients_do_not_add_up` |
| FP-2 | Apply each KPI formula at its registered evaluation grain. | A total rate is `SUM(numerator) / SUM(denominator)`. A deliberately defined average of entity rates is a different KPI. | `test_mean_of_cell_ctor_is_not_total_ctor` |
| FP-3 | Grouping is an argument of the read, not part of the definition. | The same KPI is read at S1 grain, S2 grain and S4 grain. | `test_s4_matches_business_case_grid` |
| FP-4 | Every total is a member node at a requested grouping shape and is computed at its own scope. | The three total rules (additive counts, rates, distinct counts) reduce to this. | `test_single_statement_equals_one_query_per_node` |
| FP-5 | Share compatible aggregation work; select the physical plan by measurement. | One scan is an optimization, not a correctness requirement. Cost also grows with grouping count, state size, cardinality and new sources. Historical measurements motivate split distinct plans ([08](08-complexity-and-performance.md)). | `test_baseline_statement_count_vs_one_pass`, [08-complexity-and-performance.md](08-complexity-and-performance.md) |
| FP-6 | Declare grain and prove that joins preserve the intended population. | A cardinality declaration alone cannot prevent fan-out; source uniqueness and event-reduction checks are required. | `test_ec_event_fanout_inflates_open_count`, `test_ec_scd2_dimension_duplicates_facts` |
| FP-7 | Fail closed. Unknown atom, dimension, dialect or placeholder is an error, never a guess. | A guessed number looks like a real one. | `test_ec_unknown_atom_fails_closed` |
| FP-8 | Preserve the difference between an unknown dimension and a rolled-up dimension. SQL grouping-set plans identify totals with `GROUPING_ID` or equivalent scope metadata. | An unknown market and a grand total both print as NULL. | `test_ec_null_member_looks_like_subtotal` |
| FP-9 | Definitions and requests are typed, validated data. Bind values and allowlist identifiers before execution. | Removes injection and string-replace drift (the same root cause as EdgeSQL's WHY-L1 to WHY-L3). | Phase 2 in [13-implementation-plan.md](13-implementation-plan.md) |
| FP-10 | Every optimisation ships with a naive oracle and a parity test. | The oracle is slow and obviously right. | `oracle_sql`, [14-test-strategy-and-traceability.md](14-test-strategy-and-traceability.md) |
| FP-11 | Distinguish empty population, a zero count, missing observations and undefined rates. | A known empty count can be zero; a rate with zero denominator is NULL with a reason. Missing or failed data must not become zero. | `test_ec_zero_denominator_in_a_non_empty_node_gives_null_rates_through_the_planner` |

## Operating rules: always / approval gate / never

| Always | Approval gate | Never |
|---|---|---|
| Declare each atom's aggregate class (distributive, algebraic, holistic). | Publish a new source relationship only after a grain review. | Average displayed rates. |
| Carry the grouping schema, `GROUPING_ID` and typed member values for node identity. | Switching a distinct count from exact to HLL sketch. | Add displayed distinct counts. |
| Generate the zero-denominator guard in one place (`Kpi.ratio`). | Widening the date context for a period comparison. | Let a model write SQL that runs without a parse and a plan check. |
| Bind filter values as parameters. Validate identifiers against the model. | Raising the cell cap. | Reconstruct totals from rounded display values in the UI. |
| Return scope, definition version and provenance; expose SQL to authorized technical users. | Approve and version semantic changes used by a published dashboard. | Use string concatenation or Jinja for new SQL. |
| Compare each new plan shape against the oracle in a test. | | Hide a failed node. A partial grid is labelled partial. |

## KILL list (out of scope on purpose)

| Id | Not built | Reason |
|---|---|---|
| KILL-1 | Fabric / T-SQL dialect | The target is Databricks. DuckDB exists only as a local test engine. |
| KILL-2 | A planner inside EdgeSQL | EdgeSQL is a typed SQL tree toolkit with no planner (its own KILL list). The planner lives here and uses EdgeSQL for parse, inspect, validate. See [10-edgesql-integration.md](10-edgesql-integration.md). |
| KILL-3 | Free-form natural-language SQL | AI proposes an intent object. The planner builds SQL ([11-api-system-and-ai.md](11-api-system-and-ai.md)). |
| KILL-4 | A general BI platform | Deliver the focused pivot behavior in S1–S4; reuse the existing report surface when practical ([12](12-ux-and-wireframes.md)). |
| KILL-5 | Streaming / incremental view maintenance in v1 | Documented as a future option in [08-complexity-and-performance.md](08-complexity-and-performance.md). |

## Lens map

Each document is written from one or more lenses. The README table links them.

| Lens | Primary document |
|---|---|
| Product Owner | [03-problem-catalogue.md](03-problem-catalogue.md), [13-implementation-plan.md](13-implementation-plan.md) |
| Database expert | [09-data-model-and-databricks.md](09-data-model-and-databricks.md) |
| System design | [11-api-system-and-ai.md](11-api-system-and-ai.md) |
| Full stack | [11-api-system-and-ai.md](11-api-system-and-ai.md), [13-implementation-plan.md](13-implementation-plan.md) |
| UX / UI | [12-ux-and-wireframes.md](12-ux-and-wireframes.md) |
| AI engineer | [11-api-system-and-ai.md](11-api-system-and-ai.md) |
| O(n) | [08-complexity-and-performance.md](08-complexity-and-performance.md) |
