# Why composable KPI definitions matter

The business goal is a pivot that gives trustworthy answers at every selected scope. The same delivery rate must mean the same thing in a campaign cell, a typology subtotal and the grand total. Read [BUSINESS-CASE](BUSINESS-CASE.md) for the decision, scope, owners and value model, or [START-HERE](START-HERE.md) for the worked example.

Date: 2026-11-12. These chains explain **failure modes** of the SQL-template pattern. They are demonstrated on synthetic data, not observed in a production system.

## Chain A: why can a total be wrong?

| Id | Why | Explanation |
|---|---|---|
| WHY-1 | A total is calculated from displayed numbers using the wrong rule. | Rates require their numerator and denominator; distinct counts require overlap information. |
| WHY-2 | The consumer has insufficient information. | A finished percentage does not reveal its denominator; a unique count does not reveal the client identities behind it. |
| WHY-3 | The query result is being used as the reusable metric contract. | A typical KPI registry stores each KPI as a templated query that returns one `kpi_value` per group. Such registries often also keep formula, source, filter and grouping in separate columns, so the catalog need not be one opaque string. |
| WHY-4 | Reuse needs explicit aggregation semantics, and SQL has no construct for them. | SQL composes relations, not measures: an aggregate is bound to the `GROUP BY` of its statement, so a stored query or view cannot be regrouped correctly. The consumer must instead know the source grain, state, formula, valid dimensions, filters and context. |
| WHY-5 | Grouping must change without changing metric meaning. | A formula over correctly aggregated state can be evaluated at every requested scope, using either a native semantic engine or generated SQL. |

A local teaching fixture demonstrates the risks: averaging campaign delivery rates gives 81.9% instead of 82.4%; summing synthetic campaign audiences gives 240 instead of 120. These are reproducible examples, not observed production defects ([03](03-problem-catalogue.md), [14](14-test-strategy-and-traceability.md)). On the 13-message example, averaging the three typology delivery rates gives 81.9% where the total at its own scope is 76.9% ([BUSINESS-CASE](BUSINESS-CASE.md)).

WHY-1 and WHY-2 are arithmetic and hold in any language. WHY-3 to WHY-5 are about reuse, and they are where SQL's missing measure abstraction matters. [05](05-first-principles-solution.md) treats the two separately and assesses Databricks metric views and Malloy against them.

### GOV-1

A published KPI declares its population, aggregate state and final formula. Every result is evaluated at its requested scope under the selected filters and caller permissions. Reuse state only when its merge rule preserves that meaning. Never calculate a total from rounded displayed cells.

## Chain B: why can a pivot repeat work?

| Id | Why | Explanation |
|---|---|---|
| WHY-B1 | A simple implementation executes separately for every KPI and grouping. | Six KPIs × twelve grouping shapes gives 72 statements in the prototype baseline. This is an example, not a lower bound or measured current behavior. |
| WHY-B2 | Those statements may repeat source scans, joins and fixed overhead. | The amount of repeated work depends on plans, caches, scheduling and common-source reuse. |
| WHY-B3 | Shared measures and scopes are not exposed to the planner. | The engine cannot intentionally share work without understanding compatible populations and dependencies. |
| WHY-B4 | Text templates hide structure from a generic planner. | The visible grouping slot is already dynamic; the gap is typed, validated composition, not the impossibility of changing a grouping. |
| WHY-B5 | The execution strategy has been coupled to metric definitions. | Separating meaning from execution permits shared aggregation, native metric views, preaggregation and split plans. |

`GOV-1` establishes correctness. Measurement chooses the physical plan. A single `GROUPING SETS` statement can share work, but an exact distinct count may be cheaper separately, and additional KPIs can introduce new state or sources. See [05](05-first-principles-solution.md) and [08](08-complexity-and-performance.md).

```mermaid
flowchart LR
  Q["Business question and selected population"] --> M["Metric contract: grain, state, formula, context"]
  M --> S["Required detail and total scopes"]
  S --> A["Verified execution adapter"]
  A --> R["Values with scope and evidence"]
```

## Where each why is addressed

| Why | Main specification |
|---|---|
| WHY-1 | [03](03-problem-catalogue.md) PRB-TOTALS-* |
| WHY-2 | [06](06-semantic-model-and-dsl.md) SEM-L0 |
| WHY-3 | [10](10-edgesql-integration.md) migration |
| WHY-4 | [06](06-semantic-model-and-dsl.md), [16](16-correctness-contract.md) |
| WHY-5 / GOV-1 | [01](01-principles.md), [05](05-first-principles-solution.md) |
| WHY-B* | [07](07-planner-and-sql-generation.md), [08](08-complexity-and-performance.md) |
