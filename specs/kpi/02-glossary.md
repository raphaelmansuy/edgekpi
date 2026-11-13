# Glossary

Use these words consistently. A **measure** is an aggregate; a **KPI** is its business formula; a **scope** identifies the population being evaluated. SQL and UI implementations may differ while preserving those meanings.

Date: 2026-11-12.

| Term | Meaning | Example / reference |
|---|---|---|
| Fact | Data at a declared row grain. | One row per outbound message, after approved deduplication. SEM-FACT |
| Grain | What one record or intermediate result represents. | Source grain: one message. Output grain: one scope and member key. FP-6 |
| Population | Records or entities eligible for a metric under the request and permissions. | Selected outbound messages in HK and SG. |
| Dimension | An attribute used to group or filter. | Typology, Tier, Campaign, Year, Market. SEM-DIM |
| Grouping path | Ordered display dimensions on an axis. It does not assert a business hierarchy or functional dependency. | Typology → Tier → Campaign. PLAN-AXIS |
| Axis | Rows or columns of the pivot. | The axes independently contribute constraints to a cell. |
| Grouping set / shape | Dimensions retained for one kind of result. A shape may produce many result rows. | `(typology, year)` produces one row per present typology/year combination. |
| Node / member node | One member group at a grouping shape and context. Complete identity includes the ordered dimension schema, grouping id and retained typed member values. | New / all markets is one node; VIP / all markets is another. S4 has 12 grouping shapes and 56 populated member nodes in the fixture. |
| Scope / result key | A grouping shape plus its member values, filters and context. | New clients in 2026, all selected markets. |
| Pivot cell | One KPI at one result key. | New × 2026 × Delivery Rate. |
| Lattice | Groupings ordered by refinement. Standard pivot prefixes form a product of axis chains. | Three row levels and two column levels yield `(3+1)(2+1)=12` shapes; arbitrary subsets yield up to `2^5=32`. |
| Atom / measure | A declared aggregate with population, source grain, expression, predicate and merge behavior. | `sent = COUNT(*)` over the message population. SEM-L0 |
| Atom state | Information sufficient for a valid merge or finalization. | Count; `(sum, count)` for a mean; identity set for exact distinct; approximate HLL sketch. |
| KPI | Business calculation evaluated from measures at a declared scope. | `delivery_rate = delivered / sent`. SEM-L1 |
| Finalization | Convert aggregate state into a displayed scalar after aggregation. | Divide total delivered by total sent. |
| Context modifier | Explicitly change a metric's evaluation context. | Prior period or a specified benchmark population. SEM-L2 |
| Nested-grain KPI | Evaluate first at an entity grain, then aggregate those results. | Mean client-level conversion, distinct from overall conversion. SEM-L3 |
| Aggregate class | Distributive, algebraic or holistic, describing sufficient state and merge cost. | Exact distinct is holistic with unbounded identity state; HLL is approximate bounded state. SEM-CLASS |
| `GROUPING_ID` / `gid` | SQL bit mask identifying dimensions rolled up by grouping sets. | First listed dimension has the highest bit. A real NULL member and a total can then be distinguished. |
| Drill-across | Aggregate compatible facts independently, then align on conformed scope and member keys. | Message counts alongside purchases, with filters valid for both facts. PLAN-DRILL |
| Intent | Validated request for KPIs, axes, filters, period, precision and totals. | SYS-INTENT |
| Plan | Executable steps implementing an intent while preserving its contract. | Native metric view, grouping sets, two-stage or split queries. |
| KPI registry | A catalogue storing one templated SQL text per KPI, with a grouping placeholder such as `{{ group_by_list }}`. | Typical columns: formula, select, from, join, where, filter, group-by. PRB-REGISTRY-TEMPLATE |
| Reach | A KPI whose population and identity are unresolved in this study. | Do not equate it with delivered or the prototype's `clients`. PRB-REACH |
| CTR / CTOR | Labels requiring owner confirmation: click-through rate is often clicked / delivered, click-to-open rate is clicked / opened. | The same label can hide two denominators. PRB-NAMING |
| Oracle | Independent reference calculation used to check another plan. | Simple per-scope query; must also use the approved population and source semantics. FP-10 |
| Reconciliation check | Test on the returned rows alone: parts add up to their total, a rate equals its own numerator over its own denominator, a unique total lies between its largest part and the sum of its parts. Necessary, not sufficient. | Needs no second query, so it can run on production results. [16](16-correctness-contract.md) C-CHECK |
| Additivity probe | Evaluate a KPI at a broad scope and over a partition of it, then compare the whole with the parts. | Whole = sum suggests a count; whole below the sum suggests a unique count; whole between the parts suggests a rate. [10](10-edgesql-integration.md) EDGE-PROBE |
| Measure composability | The ability to define a KPI once, with no grouping in it, and evaluate it at any grouping. Standard SQL composes relations and lacks this. | Provided by Databricks metric views, Malloy, or this specification's atoms and formulas. [05](05-first-principles-solution.md) |
| Mix effect / rate effect | Exact split of the gap between two segments' rates into where their volume went and how each category performed. | A segment can lead in every campaign and trail overall. [16](16-correctness-contract.md) C-CONTEXT |
| Fail closed | Reject an unsupported or ambiguous operation with a named reason. | Unknown dimension, unapproved metric or incompatible filter. FP-7 |
| Provenance | Evidence identifying definitions, data version, permissions and execution. | A historical benchmark without a run record is reported evidence, not a new measurement. |
