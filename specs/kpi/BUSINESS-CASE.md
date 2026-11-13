# Business case: trustworthy engagement pivots

CRM managers and campaign owners need to compare client engagement by typology, tier, campaign, year and market. They use the results to adjust targeting, contact frequency, content and channel mix. A report is useful only if a subtotal answers the same business question as a detail cell, over a larger selected population.

This study asks for that behavior. The risks it addresses, wrong totals and many repeated queries, are properties of the SQL-template pattern. They are demonstrated on synthetic data with a deliberately simple baseline, not measured in any production system.

**Recommendation:** agree the metric and population contracts first; use Databricks metric views as the preferred starting implementation after a successful core S4 fixture probe, complete the remaining Phase 0 gates, then use the least complex execution backend that passes the same correctness, security and performance checks. Use generated SQL when it is needed. Keep metric meaning independent of the execution plan. The decision and alternatives are in [05](05-first-principles-solution.md).

## What users need to decide

| User question | View needed | Decision supported |
|---|---|---|
| Which client typologies receive the most messages? | Message counts by typology | Review communication volume and contact frequency |
| Which segments engage less? | Delivery, open, click and click-to-open rates at a consistent scope | Investigate audience rules, creative and channel choices |
| Where does a typology's result come from? | Typology, Tier and Campaign grouping | Locate a segment or campaign requiring investigation |
| Does the pattern differ by market or year? | Year and Market columns | Compare selected categories with the same metric definitions |
| What is the overall result? | Subtotals and grand totals on either axis | Compare a segment with its selected population without arithmetic bias |

These are reporting needs. This study supplies no measured business benefit, production query count, production latency or implementation budget; the value model below lists the inputs to collect.

## The four scenarios describe one product

The scenario names S1 to S4 are this study's vocabulary for four increasingly flexible reporting scenarios.

| Scenario | Rows | Columns | Required behavior |
|---|---|---|---|
| S1 | Client Typology | Selected KPIs | One value per selected typology and KPI |
| S2 | Typology → Tier → Campaign | Selected KPIs | Evaluate the same definitions for each present row combination |
| S3 | Same as S2 | Year → Market → KPI | Evaluate at the intersection of row and column categories |
| S4 | Same, with selected totals | Same, with selected totals | Evaluate each total at its own row × column scope |

These are ordered display groupings. They do not imply that a campaign belongs to only one tier or typology, and indentation must not be read as a business relationship. Keep complete grouping keys even when labels repeat.

A total broadens the grouping while retaining report filters, the selected member population, and the caller's access rights. For example, a total for selected markets HK and SG covers HK and SG; it does not silently include every market in the database. Sorting or paging the display must not change that total. Prior-period comparisons are a separately declared context operation.

## Why ordinary arithmetic can give the wrong answer

Assume **one row per outbound message**. A message is either delivered or not. Two disjoint campaign populations have these counts:

| Campaign | Sent messages | Delivered messages | Delivery rate |
|---|---:|---:|---:|
| A | 90 | 81 | 90% |
| B | 10 | 5 | 50% |
| Selected campaigns | 100 | 86 | **86%** |

Averaging the two percentages gives 70%. It gives a campaign with ten messages the same weight as one with ninety. The total rate instead gives every message the appropriate weight:

$$
R = \frac{81+5}{90+10}=86\%.
$$

For any disjoint groups with numerators $n_i$ and denominators $d_i$:

$$
R=\frac{\sum_i n_i}{\sum_i d_i}
 =\frac{\sum_i d_i r_i}{\sum_i d_i}, \qquad r_i=\frac{n_i}{d_i}.
$$

The weighted form assumes positive group denominators; the ratio of counts requires a positive total denominator. Groups with zero denominators need the approved NULL policy. The weight is **the registered denominator**: sent for delivery rate, delivered for open rate, and opened for click-to-open rate. A weighted average of rounded display values is still only an approximation; compute with the underlying counts and round at presentation time.

Unique clients need a different rule. If campaign A reaches clients `{c1, c2}` and B reaches `{c2, c3}`, the combined audience is three clients. Adding 2 + 2 counts `c2` twice:

$$
|A\cup B|=|A|+|B|-|A\cap B|=2+2-1=3.
$$

The two counts alone do not reveal the overlap. An exact total requires the underlying client identities, an equivalent exact state, or a fresh exact computation at that scope. An approximate sketch is a separate business choice with a visible approximation label.

These examples explain failure modes. They are teaching examples on synthetic data. [START-HERE](START-HERE.md) supplies a larger executable example; [16](16-correctness-contract.md) states the formal contract, including an exact formula for the size of the error.

## How wrong can a shortcut be?

The [13-message example](../../examples/registry/data.sql) (one row per message, seven clients, three typologies including one unknown) shows the size of the error on a small, fully inspectable data set. A "shortcut" total combines displayed cell values; the correct total is computed at the total's own scope.

| KPI | Shortcut over displayed values | Correct, at total scope | Error |
|---|---:|---:|---|
| Delivery rate by typology | Mean of the three typology rates: **81.9%** | 10 / 13 = **76.9%** | +5.0 points |
| Delivered clients (unique) by typology x market | Sum of the six cell counts: **9** | **6** distinct clients | +50% |

Both errors have the same cause. The rate shortcut gives a typology with one message the same weight as one with seven; the unique-count shortcut counts a client once for every cell it appears in. Neither can be repaired after the fact from the displayed numbers.

This also narrows a question that no displayed value can answer: whether a KPI such as Reach is a message count or a unique-recipient count. A message count adds up exactly across a partition (a quarter equals the sum of its months). A unique count comes out below the sum as soon as one client is contacted in two months. One experiment on the registry therefore separates the two readings before anyone reads its SQL ([10](10-edgesql-integration.md) EDGE-PROBE): evaluate the KPI for a quarter and for each of its months, then compare.

## The metric contract comes before optimization

These are the proposed meanings of the six registry KPIs used in this study. Publication requires confirmation against the actual registry and source data.

| Metric | Intended calculation | What must be confirmed |
|---|---|---|
| Message Sent | Count outbound messages attempted/sent | What constitutes one outbound message; retries and duplicates |
| Message Reached | Unresolved | Messages or recipients; identity, eligibility and total rule |
| Delivery Rate | Delivered messages / sent messages | Delivery status, denominator population and attribution window |
| Open Rate | Opened delivered messages / delivered messages | At least one open, event qualification and observation window |
| Click Rate | Delivered messages generating at least one click / delivered messages | Qualified click, identity and observation window |
| Click to Open Rate | Provisionally clicked messages / opened messages | CTR versus CTOR label, shared population and zero-denominator policy |
| Seventh metric | Unresolved | Label, definition, source and owner |

A registry entry is evidence that a metric exists, not evidence that its full semantics are agreed. Every formula must be read before migration. The prototype's `clients` atom illustrates distinct counting and is **not** an approved definition of Message Reached.

Every published definition needs a stable id, version, owner, source grain, numerator/denominator or count identity, event predicates, dimension attribution time, filters, time zone, refresh policy and precision policy. Grain and event preparation prevent an open-event join from counting one message several times.

## Recommended solution and why it fits

Use a small governed semantic contract with three parts:

1. **Measures:** the counts, sums or identity sets needed by the KPI, with declared grain and merge behavior.
2. **Formulas:** combine those measures after aggregation, with explicit zero-denominator and missing-data behavior.
3. **Requests:** choose dimensions, filters, periods and total scopes without redefining the KPI.

The service resolves a request into all required scopes. An adapter executes them, and the UI formats the result. `GROUPING SETS` is one useful SQL implementation. A native metric view, a two-stage rollup, or a split exact-distinct query may also satisfy the contract. Correctness does not depend on using one statement or one scan.

**Why plain SQL does not already provide this.** SQL can compute every number in this document. It cannot name a KPI once and reuse it at any grouping: an aggregate belongs to the `GROUP BY` of its statement, and a view that stores a finished rate cannot be regrouped correctly. Registries therefore fall back on text templates with a grouping slot, such as `{{ group_by_list }}`. The three parts above are that missing reusable measure. Databricks metric views and the open-source Malloy language both provide it; each matched all 56 groups of the scenario 4 fixture, the first on the target warehouse and the second on local DuckDB. Metric views are preferred here because the target is Databricks and they are governed in Unity Catalog. No tool settles the owner decisions below. See [05](05-first-principles-solution.md).

Choose the adapter in Phase 0 using the acceptance suite in [14](14-test-strategy-and-traceability.md). Compare native metric views with generated SQL under the same definitions, caller permissions, snapshot assumptions and workload. Build only the planner capabilities required by any verified gap. See [05](05-first-principles-solution.md) for the decision and [13](13-implementation-plan.md) for delivery gates.

For S4's standard prefix totals there are four row grouping sets and three column grouping sets: $4\times3=12$. Those are **grouping shapes**, not twelve cells. Each shape produces as many rows as it has distinct member combinations. Adding the optional Market-across-years subtotal creates a fourth column grouping and $4\times4=16$ shapes. Calculate only the requested scopes.

## Business decisions and proposed owners

The roles below are proposed responsibilities, not evidence of a staffing commitment.

| Decision | Proposed accountable role | Consequence until resolved |
|---|---|---|
| Reach definition and exact identity | CRM metric owner, with data steward | Do not publish a replacement Reach metric. Run the additivity probe to learn whether Reach behaves as a message count or a unique count |
| CTR/CTOR name and denominator | CRM metric owner | Keep provisional label and formula out of published replacements |
| Seventh metric | Campaign owner | Exclude it from the supported catalog |
| Event windows, retries and segment attribution | Data owner with CRM metric owner | Gate affected metrics on a verified source contract |
| Optional Market-across-years totals and single-child display | Report owner | Use explicit request options; proposed defaults require acceptance |
| Cross-KPI client union | CRM metric owner | Defer until populations and common client identity are agreed |
| Exact versus approximate audience counts | Business owner | Keep exact as default; require explicit opt-in for approximation |
| Native semantic backend versus generated SQL | Technical owner | Resolve in Phase 0 with measured parity and operating cost. Malloy enters the comparison only if several engines or nested results become requirements |

Reporting teams also ask for comparisons, thresholds, sort orders, drill paths and refresh after each campaign wave. These are useful requirements, but they need separate definitions: previous campaign ordering, benchmark population, threshold values and refresh service level. They do not justify inventing a year-over-year or share formula.

## How success will be measured

| Outcome | Acceptance evidence |
|---|---|
| Trustworthy totals | Counts, rates and distincts agree with independent queries at every requested scope; filter and permission boundaries hold |
| Self-consistent results | Every returned grid passes the reconciliation checks: parts add up to their total, and each rate equals its own numerator over its own denominator ([16](16-correctness-contract.md) C-CHECK) |
| Preserved KPI meaning | Each migrated definition reconciles with approved source logic at detail and total scopes; every disagreement is explained |
| Faster useful reporting | Compare p50/p95 elapsed time, warehouse consumption, returned rows and concurrency against the actual current implementation |
| Less maintenance | Track effort and defects for adding a KPI or changing an approved definition |
| Understandable results | Users can identify scope, denominator, data freshness and approximation status without reading SQL |

Performance targets, budget and tolerances are to be agreed in Phase 0. Historical synthetic benchmark figures in [08](08-complexity-and-performance.md) show tradeoffs; they are not a production SLA or an ROI estimate.

A simple annual value model makes the missing inputs explicit:

$$
\text{Annual net value}
=Q(t_{old}-t_{new})w+C_{old}-C_{new}-M.
$$

Here $Q$ is completed report runs per year; $t$ is **avoidable person-hours per run**, not simply query runtime; $w$ is the loaded hourly value of that time; $C$ is annual execution cost; and $M$ is additional annual maintenance. Convert time units consistently. Initial delivery cost $I$ is separate. If annual net value is positive, a simple payback estimate is $I/\text{annual net value}$ years. Avoided reporting mistakes may add value, but no defensible monetary estimate exists yet.

Collect these inputs from representative users and warehouse billing before presenting a financial return. The decision can still be justified by correctness, but it should not claim savings that have not been measured.

## Evidence and limits

Every number in this study comes from synthetic data. The S4 fixture is a synthetic grid with added client identities to test overlap behaviour; the 13-message and 100-message examples above are small enough to check by hand. What is **demonstrated** on that data: the total-rate, unique-count and fan-out failures, and the agreement of native metric views, Malloy and generated SQL on all 56 groups of the S4 fixture. What is a **proposal**: the contract, the owner decisions, the migration route and the cost model. Nothing here measures a production system.

A correct total can still mislead a comparison between segments whose campaign mix differs; [16](16-correctness-contract.md) C-CONTEXT gives an example and the exact split of a gap into mix and rate. The Typology -> Tier -> Campaign drill path is the remedy within S1 to S4.

Historical DuckDB and Databricks tests and benchmarks are recorded in the notes. Those claims require their own run provenance; the retained check ran a narrow S4 native-versus-SQL comparison on a Databricks serverless SQL warehouse and did not rerun historical benchmarks or establish production readiness ([validation](validation/2026-11-12/README.md)). A separate local probe expressed the same pivot in Malloy and matched all 56 groups on DuckDB; it did not touch Databricks ([validation](validation/2026-11-12-malloy/README.md)). [14](14-test-strategy-and-traceability.md) separates prototype evidence from release gates. The Notion article summarised in [04](04-article-reformulated.md) is background context; its assertions do not replace evidence from the selected execution adapter.
