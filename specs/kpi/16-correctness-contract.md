# Correctness contract: why the totals are right

This document gives the business rule first, then the mathematics that makes it precise. The rule is simple: **each cell and total answers the KPI question over the rows eligible for that scope**. A faster execution plan must answer the same question.

Date: 2026-11-12. Status: normative product specification. The existing prototype exercises a subset; [14](14-test-strategy-and-traceability.md) distinguishes tested behavior from proposed requirements.

## C-SCOPE: define the population before calculating

The message fact has **one row per sent message**, identified by a non-null unique message key. Define:

| Symbol | Meaning |
|---|---|
| $R_v$ | Message rows at an immutable source version $v$ |
| $A_u(r)$ | The caller is authorized to use row $r$ |
| $P(r)$ | The report filters and approved period admit the row |
| $g$ | A requested grouping shape, such as `(typology, market)` |
| $x$ | A typed member tuple, such as `(New, HK)` |
| $p_a(r)$ | The population predicate of atom $a$, such as `is_delivered` |

The eligible rows for a member node are:

$$
R_{u,v,P,g,x}=\{r\in R_v : A_u(r)\land P(r)\land \pi_g(r)=x\}.
$$

Here $\pi_g$ retains only the grouping columns. For the grand total, $g=()$, so there is no member restriction. The total retains report and access filters. A total of HK/SG is a total of the selected HK/SG population, unless the definition explicitly requests a different benchmark.

The notation identifies records by their fact key. SQL count/sum operates on the corresponding **bag of fact rows**; deduplicating equal-looking rows changes those measures. Entity sets are used specifically for distinct/client calculations.

Filters must have an equivalent mapping on every required fact. If Campaign does not describe a sales fact, the planner cannot silently drop Campaign from the sales query or repeat market sales under every campaign.

## C-FORMULA: aggregate first, evaluate the formula last

Within an eligible node, let:

$$
S=|R|,\quad
D=\sum_{r\in R}\mathbf{1}[\text{delivered}(r)],\quad
O=\sum_{r\in R}\mathbf{1}[\text{opened}(r)],\quad
C=\sum_{r\in R}\mathbf{1}[\text{clicked}(r)].
$$

Then `delivery_rate = D/S`, `open_rate = O/D`, `click_rate = C/D`, and `CTOR = C/O`, with a declared rule that a zero denominator returns no value. These formulas count messages with the relevant flag, not raw event records. Whether numerator populations must also require a delivered/opened flag is an owner-approved definition, not a deduction from the column names.

For disjoint groups $i$, the correct combined rate is:

$$
q=\frac{\sum_i n_i}{\sum_i d_i}
 =\sum_i\left(\frac{d_i}{\sum_jd_j}\right)q_i,
\qquad q_i=n_i/d_i.
$$

The weighted form assumes nonzero group denominators; the direct ratio of counts requires a nonzero total denominator. Zero-denominator groups must follow the approved population and NULL policy. The weights are the **denominators of that particular rate**. Delivery Rate is weighted by sent messages, Open/Click Rate by delivered messages, and CTOR by opened messages. If a denominator is unavailable, a table of percentages does not contain enough information to reconstruct the correct total.

Example: one campaign has 1 open out of 2 delivered messages; another has 9 opens out of 18 delivered messages. Both open rates are 50%, and the total is 10/20 = 50%. More revealingly, 1/2 and 9/10 give a total 10/12 = 83.3%, while their unweighted average is 70%. Weighting by some unrelated sent count can be wrong too.

Round only for display. Recomputing from rounded cell percentages adds another source of error.

### How far off is an average of rates?

Let $w_i=d_i/\sum_jd_j$ be each group's share of the denominator, $n$ the number of groups and $\bar q=\frac1n\sum_iq_i$ the plain average of their rates. Subtracting the two forms of the total gives an exact expression for the error:

$$
\bar q-q=\sum_i\Big(\frac1n-w_i\Big)q_i=-\,n\operatorname{Cov}(w,q),
\qquad
\operatorname{Cov}(w,q)=\frac1n\sum_i\Big(w_i-\frac1n\Big)(q_i-\bar q).
$$

| Consequence | Meaning for the report |
|---|---|
| The error is zero only when group size and group rate are uncorrelated | Equal denominators or equal rates make the average right. Otherwise it is wrong in a predictable direction: it overstates when large groups have low rates |
| $\min_iq_i\le q\le\max_iq_i$ | A correct total always lies between its smallest and largest child rate, so the error is smaller than their spread. An average lies in the same range, so a range check cannot detect averaging |
| Displayed rates do not determine the total | Rates of 50% and 90% give 83.3%, 70% or 60% for denominators (2, 10), (10, 10) or (30, 10). One input, three correct outputs: no formula over displayed percentages can be right |

The first pattern is easy to hit: whenever the largest group has the lowest rate, the plain average overstates the total (see [BUSINESS-CASE](BUSINESS-CASE.md)). Tests: `test_mean_of_rates_error_is_group_count_times_covariance_of_weight_and_rate`, `test_displayed_rates_alone_cannot_determine_the_total`.

### Ratio cancellation must preserve its domain

$$
\frac{C/D}{O/D}=\frac CO\quad\text{when }D>0\text{ and }O>0.
$$

At $D=0$, the guarded ratio-of-ratios is NULL. For inconsistent tracking data $(C,O,D)=(1,1,0)$, the direct CTOR formula gives 1 while the ratio-of-ratios is undefined. A compiler must not erase that difference by symbolic cancellation. Both formulations can produce correct totals when re-evaluated at each scope on their defined domains; averaging finished cell ratios is the failure.

## C-STATE: what can be merged

An aggregate has a state $s_a$, merge operation $\oplus_a$, and finalizer $f_a$. For complete, disjoint fact-row partitions $R_i$:

$$
s_a\left(\biguplus_iR_i\right)=\bigoplus_i s_a(R_i),
\qquad \operatorname{KPI}(R)=F(f_1(s_1(R)),\ldots,f_m(s_m(R))).
$$

The $\biguplus$ symbol means each fact row belongs to exactly one child partition. The merge must be associative and commutative, have a declared empty identity, and preserve its data type and precision. Formula references are a dependency graph, not permission to add finished values.

| Calculation | State | Merge | Finalize |
|---|---|---|---|
| Message count | Integer count | Add | Identity |
| Minimum amount | Minimum plus presence | Minimum of present values | NULL if empty |
| Average | `(sum, count)` | Add components | `sum / count` |
| Rate | `(numerator, denominator)` | Add components | Guarded division |
| Exact distinct clients | Set of eligible non-null client IDs | Set union | Cardinality |
| Approximate distinct | Compatible HLL sketch | Sketch union | Estimate with approximation metadata |

An exact distinct **integer** is not the set state. If HK clients are `{c1,c2}` and SG clients are `{c2,c3}`, both scalar counts are 2, but the total is 3:

$$
|H\cup S|=|H|+|S|-|H\cap S|=2+2-1=3.
$$

Without identities or overlap information, the total cannot be recovered from the two integers. Compute distinct directly at each scope, or retain compatible exact identity states. An exact set can grow with the population; it is not a bounded-cost rollup.

The displayed counts only bound the answer:

$$
\max_i|A_i|\;\le\;\Big|\bigcup_iA_i\Big|\;\le\;\sum_i|A_i|.
$$

Both ends are reachable, so adding $n$ displayed counts can overstate the audience by up to a factor of $n$. The upper end is reached exactly when no client appears in two groups. Additivity therefore belongs to a **measure and a partition together**, never to the measure alone. In the fixture, unique clients add up across typologies (120 + 60 = 180) because no client has two typologies there, and do not add up across the 2025 markets (165 + 125 = 290 for 175 clients). A dimension that separates clients today can stop doing so when a client changes typology within the period. Tests: `test_distinct_scalars_only_bound_the_total`, `test_additivity_probe_separates_counts_rates_and_distincts`.

Scalar count/sum states require disjoint row partitions. Set/sketch union tolerates repeated identities, but still requires complete coverage, matching identity encoding, populations, definition versions and source versions. Never mix a parent subtotal and its own children as a partition.

Snapshot balances and other semi-additive measures need a declared time-rollup rule; this count/rate solution does not automatically authorize summing every KPI across time.

## C-IDENTITY: grouping shapes, member nodes and cells differ

Scenario 4 has three row levels and two column levels. With prefix totals:

$$
G=(3+1)(2+1)=12\text{ grouping sets}.
$$

The fixture produces **56 result member rows** across those shapes. For six KPIs that is **336 KPI cells**, before adding comparison contexts. None of these numbers describes the entire Cartesian product of all possible dimension members.

`GROUPING_ID` identifies a grouping shape relative to an **ordered dimension schema**. A result key includes that schema, the grouping ID, and typed retained member values. It distinguishes an actual NULL/Unknown market from “All markets.” The grouping ID alone does not identify New versus VIP.

Request-level caps apply to KPI cells, contexts and bytes; estimates also need runtime enforcement. A request with no dimensions is a legitimate grand-total request and needs explicit product coverage; the current prototype does not fully implement that case.

## C-CONTEXT: comparisons need explicit scope and alignment

“Compared with overall” can mean an overall rate, a percentage-point difference, a relative index, or a share of an additive amount. These are different questions:

$$
\text{difference (percentage points)}=100(q-q_0),\qquad
\text{relative lift}=q/q_0-1.
$$

The definition names the benchmark population, which filters it retains, and the zero-denominator rule. Removing a grouping column does not remove caller authorization or silently cancel report filters.

For prior-year results displayed under 2026, pair current-year 2026 rows with source-year 2025 rows using an aligned display key. Reading both years and grouping by source year alone leaves them in different groups. The mathematical alignment test covers this counterexample; the general SQL planner remains to be built.

Use an explicit calendar, timezone, interval boundaries and observation cutoff. A rolling-period grand total evaluates its own eligible population; summing overlapping windows counts records repeatedly.

### A correct total can still mislead a comparison

A natural question is "which segments engage less?", answered by comparing a client typology with an overall benchmark. Correct totals are necessary for that question and not sufficient. Suppose VIP and New clients each have 1,000 delivered messages in two campaigns:

| Open rate | Promotion | Newsletter | All campaigns |
|---|---:|---:|---:|
| New | 720 / 900 = 80% | 20 / 100 = 20% | 740 / 1,000 = **74%** |
| VIP | 90 / 100 = 90% | 270 / 900 = 30% | 360 / 1,000 = **36%** |

VIP clients open more than New clients in each campaign and less overall. Both totals are right. They differ because most VIP messages are newsletters, which few people open. For two segments $A$ and $B$ with denominator shares $w_j$ and rates $q_j$ over the same categories $j$, the gap splits exactly into two parts:

$$
q^A-q^B=\underbrace{\sum_j\big(w^A_j-w^B_j\big)\frac{q^A_j+q^B_j}{2}}_{\text{mix: where the messages went}}
+\underbrace{\sum_j\frac{w^A_j+w^B_j}{2}\big(q^A_j-q^B_j\big)}_{\text{rate: how each category performed}}.
$$

Here the gap of −38 points is −48 points of mix and +10 points of rate. The first suggests reviewing which campaigns VIP clients receive; the second says their engagement is higher where campaigns are comparable. The S1–S4 release needs no new operator for this: keep the typology-to-campaign drill path and show each rate's denominator. A mix and rate breakdown is a candidate context operation for later, once the benchmark is defined. Test: `test_a_correct_total_can_reverse_a_comparison_and_the_gap_splits_into_mix_and_rate`.

## C-FACTS: avoid fan-out and preserve entity membership

Independent message and sales measures can be aggregated separately and matched at conformed member nodes. This avoids multiplying message rows by transaction rows. A join declared many-to-one must still be validated against actual key uniqueness and temporal ranges; a declaration is not a proof.

Client conversion requires more than drill-across totals. If 100 clients were reached and 50 clients bought, the number of reached buyers could be anything from zero to 50 without identity overlap information. Establish eligible reached and buyer sets, apply the agreed attribution period, and count their intersection before finalization.

Cross-KPI audience union likewise requires a common identity namespace and the union of eligible populations. `COUNT(DISTINCT)` excludes NULL IDs. Unknown identity must have an explicit exclusion/error/separate-count policy; do not replace every unknown person with one shared fake ID.

## C-SNAPSHOT: every part of a report reads compatible data

Combined, split, two-stage and native metric-view plans must produce the same result from the same definition and source-version manifest. A numerator read before ingestion and a denominator read after it do not form a valid rate.

Pin versions for every constituent query and retry. Multiple fact versions are reproducible, but a common business snapshot additionally needs a committed batch/as-of contract and completeness boundary. A maximum event-date watermark does not detect backdated corrections or deletes. Cache entries and exports retain source versions, definition dependencies and observation cutoff.

## C-EMPTY: no data is different from zero and failure

| Situation | Meaning | Cell result |
|---|---|---|
| Rows exist, no delivered messages, sent > 0 | Measured zero delivery | Numeric `0` |
| Rows exist, denominator = 0 | Rate undefined | NULL, `zero_denominator` |
| No eligible fact rows | No observations in this report scope | NULL, `no_data` under the chosen product policy |
| Fact/filter unsupported | Calculation is not defined | Refuse validation |
| One required fact execution failed | Answer unavailable | NULL, `failed`/`unavailable`; dependent formulas also unavailable |
| Access rules suppress a value | Hidden by policy | `suppressed` when disclosure of that state is allowed |

The product's chosen empty-population presentation does not change SQL's mathematical count identity. The existing prototype uses `HAVING COUNT(*) > 0` to normalize empty grouping-set output and lets the assembler show `no_data`. This policy needs matching client behavior.

## C-CHECK: a correct grid reconciles with itself

An oracle needs a second, independent computation. These checks need only the rows already returned, so they can run on every production request.

Take two requested grouping shapes where the child keeps exactly one more dimension than the parent, such as `(typology)` and `(typology, year)`. Grouping assigns each fact row to exactly one member of the added dimension, an unknown (NULL) member included. The children of a parent node therefore partition its rows, and four invariants follow:

| Id | Invariant | Applies to | Detects |
|---|---|---|---|
| I1 | Parent value = sum of its children | Counts and sums | Totals and details read from different data versions; a truncated or partly fetched result; a lost NULL member; a filter dropped at one scope; a node placed under the wrong `gid` |
| I2 | Rate = numerator ÷ denominator of the **same** node; NULL exactly when the denominator is zero | Every ratio KPI | An averaged or summed rate; a rate rebuilt from rounded cells |
| I3 | Largest child ≤ parent ≤ min(sum of children, fact rows of the parent) | Exact unique counts | A unique count outside its feasible range. A summed audience sits exactly on the upper bound, so it is caught only when another breakdown of the same node adds up to less |
| I4 | Smallest child rate ≤ parent rate ≤ largest child rate | Every ratio KPI | Gross errors when policy hides numerators and denominators. Implied by I1 and I2 |

**Why I1 and I2 are enough for counts and rates.** If the detail counts are right and I1 holds on every step from detail to a total, that total's numerator and denominator are sums over a partition of its rows, which is the count over those rows. I2 then makes its rate the ratio at that scope. So correct details, I1 and I2 imply correct count and rate totals. Unique counts are different: I3 only brackets the value, and exactness still requires evaluation at the scope.

The 12 shapes of scenario 4 form a grid of 4 row levels by 3 column levels. With $r$ row dimensions and $c$ column dimensions there are $r(c+1)+c(r+1)$ parent and child pairs: 17 for $r=3$, $c=2$.

The checks are necessary, not sufficient:

- An error repeated at every scope passes. A join that duplicates every message doubles details and totals alike. Source grain and key checks remain mandatory ([09](09-data-model-and-databricks.md) DB-DQ).
- I1 needs every child. Run it on the complete result, before paging, top-N, single-child hiding or suppression.
- A many-to-many dimension does not partition rows. It is excluded from the first release ([07](07-planner-and-sql-generation.md) PLAN-GRAIN).
- A grid can reconcile and still implement the wrong business definition.

[fixtures/grid_checks.py](fixtures/grid_checks.py) implements the four invariants for the prototype. [fixtures/test_grid_reconciliation.py](fixtures/test_grid_reconciliation.py) shows them passing on the scenario 4 grid and on a grid with a real NULL member, failing on a mixed snapshot, a truncated result and an averaged rate, and deliberately passing on a uniformly duplicated grid and on a summed audience that has a single breakdown. A product assembler check is **specified**, not built.

## What acceptance proves

The oracle computes each requested grouping independently over approved eligible source rows. Candidate outputs must match exact values and explicit NULL/cell states at the same versions. Approximate metrics have a separate owner-approved probabilistic acceptance contract; a single low observed error is not a bound.

[fixtures/test_correctness_contract.py](fixtures/test_correctness_contract.py) checks the algebraic counterexamples with standard-library tests. [fixtures/test_business_case_math.py](fixtures/test_business_case_math.py) checks the error identity, the bounds and the mix/rate split with exact rational arithmetic. They prove the small examples, not a product compiler, source mapping, warehouse security policy or production performance. The best backend is whichever passes this contract with the least operational complexity and acceptable measured cost.
