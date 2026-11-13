# KPI pivots: business case and solution specification

Date: 2026-11-12. Target platform: Databricks.

**The problem:** a reporting team wants the same engagement KPIs by Client Typology, Tier and Campaign, across Year and Market, with flexible totals. Counts, rates and unique audiences require different total calculations. A system that treats each KPI as an opaque scalar cannot safely infer those calculations.

Two causes combine. The first is arithmetic: a displayed percentage or unique count does not contain what its total needs. The second is the language: standard SQL can reuse a query's rows, but it cannot define a KPI once and evaluate it at any grouping, so KPI registries store SQL text with a grouping slot. [05](05-first-principles-solution.md) separates the two and explains what Databricks metric views and Malloy each solve.

**How large the error can be:** on the 13-message example of [`examples/registry/data.sql`](../../examples/registry/data.sql), the delivery rate over all messages is 10/13 = 76.9%, while averaging the three typology rates (New, VIP and an unknown typology) gives 81.9%. In the 100-message campaign example of [BUSINESS-CASE](BUSINESS-CASE.md), averaging two campaign rates gives 70% where the total is 86%.

**The recommendation:** agree each KPI's population, denominator and identity rule; compute it at every requested scope; use native Databricks metric views as the preferred starting implementation, with custom SQL for verified gaps. Choose plans by correctness, cost and maintainability. One statement is an optimisation, not the definition of success.

## Start with your question

| Read | What you will understand |
|---|---|
| [BUSINESS-CASE](BUSINESS-CASE.md) | Users, business value, the cost of a wrong total, recommendation, scope and owner decisions |
| [Briefing note (13 pages)](briefing/why-a-sql-query-is-not-a-kpi.pdf) | For business readers: why a parameterised SQL query is not the right place to define a KPI, the solution with schemas, how to implement it with metric views, Malloy or generated SQL, and how to migrate by inferring measures and expressions from existing templates ([runnable examples](../../examples/walkthrough/README.md), [Databricks run of the migration test](validation/2026-11-12-migration/README.md)) |
| [START-HERE](START-HERE.md) | Why totals break and how to fix them, using eight messages |
| [05 · Solution decision](05-first-principles-solution.md) | Whether SQL composability is the root cause, the alternatives including Malloy, and the capability test that chooses the implementation |
| [16 · Correctness contract](16-correctness-contract.md) | Precise population, state, formula and grouping rules, with algebra, error bounds and self-checks |
| [13 · Delivery plan](13-implementation-plan.md) | Implementation order and release gates |
| [**Library specification and plan**](../library/README.md) | The implemented library (`/edgekpi`): one definition, three backends (metric view, Malloy, generated SQL) run on DuckDB and Databricks, template inference, 14 documents with lenses, edge-case register, state charts and a retained run record |
| [14 · Evidence and tests](14-test-strategy-and-traceability.md) | What is tested, proposed and unverified |

## Three rules explain the design

1. **Rates:** add numerator counts and denominator counts, then divide. Do not average percentages without their denominator weights.
2. **Unique audiences:** count identities at the total's scope or merge identity sets/sketches. Do not add distinct-count scalars when people overlap.
3. **Totals:** evaluate the approved definition over the total population, preserving filters, policy, time basis and source version.

If one campaign delivers 2 of 3 messages and another delivers 1 of 1, the total is `3/4 = 75%`. Averaging `66.7%` and `100%` gives `83.3%`. A person receiving both campaigns still counts once in the combined audience. [START-HERE](START-HERE.md) explains the full example.

Any returned grid can be checked against these rules without a second query: counts add up along every breakdown, each rate equals its own numerator over its own denominator, and a unique total lies between its largest part and the sum of its parts ([16](16-correctness-contract.md) C-CHECK).

## Detailed reference

| Document | Purpose |
|---|---|
| [00 · Five whys](00-five-whys.md) | Root causes and governing rule |
| [01 · Principles](01-principles.md) | Invariants and boundaries |
| [02 · Glossary](02-glossary.md) | Terms, including grouping set, node and cell |
| [03 · Problem catalogue](03-problem-catalogue.md) | Reporting scenarios S1–S4, the problems each raises and unresolved definitions |
| [04 · Article review](04-article-reformulated.md) | Supporting ideas and limits of prior research |
| [05 · Solution](05-first-principles-solution.md) | Architecture and alternatives |
| [06 · Semantic model](06-semantic-model-and-dsl.md) | Atoms, formulas, scope and validation |
| [07 · Planner](07-planner-and-sql-generation.md) | Grouping sets, identity and alternative plans |
| [08 · Performance](08-complexity-and-performance.md) | Costs, recorded measurements and limits |
| [09 · Data model](09-data-model-and-databricks.md) | Grain, identity and governance |
| [10 · Migration](10-edgesql-integration.md) | Registry migration, EdgeSQL gaps and the additivity probe for KPIs of unknown semantics |
| [11 · API and system](11-api-system-and-ai.md) | Requests, results, adapters, cache and AI |
| [12 · User experience](12-ux-and-wireframes.md) | Pivot controls, explanations and failure states |
| [13 · Delivery](13-implementation-plan.md) | Phases, decisions and release criteria |
| [14 · Tests](14-test-strategy-and-traceability.md) | Traceability and validation commands |
| [15 · Edge cases](15-edge-cases-and-state-charts.md) | Failure cases and required behavior |
| [16 · Correctness](16-correctness-contract.md) | Mathematical contract shared by implementations |

## Evidence and limits

The four reporting scenarios S1 to S4 (one row dimension; three row dimensions; Year x Market columns added; subtotals and grand totals added) are this study's own requirements. Every number in these documents comes from synthetic data. The [fixtures](fixtures/) are an executable demonstration, not product code: they build a synthetic S4 grid and construct examples of overlap, fan-out and division by zero. Claims are labelled as **demonstrated** (reproduced on synthetic data) or **proposal** (design still to implement or accept).

The local fixture suite passes; tests that need a Databricks workspace skip without credentials, and two are expected failures that document known gaps. A native temporary metric view and generated SQL each returned 56 complete S4 fixture groups matching the local calculation. [Retained validation](validation/2026-11-12/README.md) includes exact SQL, responses and replay checks. A [Malloy probe](validation/2026-11-12-malloy/README.md) matched the same 56 groups on local DuckDB. Production KPI definitions, policy behavior and comparative performance are still unverified.

Some documents also record earlier local and Databricks tests and timings. Retained scripts do not reproduce every one of those experiments, and raw run manifests are absent. Treat those timings as prior observations, not production promises. Current validation and remaining gaps belong in [14](14-test-strategy-and-traceability.md).

The baseline `6 KPIs × 12 grouping sets = 72 statements` is a deliberately naïve strategy. Twelve grouping sets are twelve grouping shapes, not twelve output rows or cells. Other correct strategies issue fewer statements.

## Decisions still needed

Metric owners must confirm any KPI whose population or identity is ambiguous (Reach in this study), the CTR/CTOR naming and denominator, any unnamed metric, optional Market-across-years totals and any cross-KPI union. A two-query additivity probe on the registry can show whether such a KPI behaves as a message count or a unique count before that discussion ([10](10-edgesql-integration.md) EDGE-PROBE). Engineering must validate production grain, identities, filters, security and the native metric-view capability gate. Proposed owners and acceptance criteria are in [BUSINESS-CASE](BUSINESS-CASE.md).

Stable ids (`PRB-*`, `SEM-*`, `PLAN-*`, `EC-*`, `ADR-*`) remain in their numbered chapters for traceability.
