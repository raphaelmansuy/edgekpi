# Start here: correct KPI totals in ten minutes

A reporting team wants one engagement pivot that can expand from Client Typology to Tier and Campaign, put Year and Market in columns, and show totals on both axes. The difficult part is preserving the meaning of every KPI as the grouping changes.

A sent-message count adds. A rate needs its numerator and denominator. A unique-client count needs to account for people present in several groups. **The solution is to evaluate each approved KPI at the population of each cell and total.**

This tutorial uses eight synthetic messages. Its worked cell values are covered by [test_tutorial.py](fixtures/test_tutorial.py). It demonstrates a failure mode on synthetic data. The business decision is in [BUSINESS-CASE](BUSINESS-CASE.md).

## 1. A small example

**Grain: one row per message sent.** The flags say whether that message was delivered, opened or clicked at least once.

| Message | Client | Typology | Market | Delivered | Opened | Clicked |
|---|---|---|---|---|---|---|
| 1 | c1 | New | HK | yes | yes | yes |
| 2 | c1 | New | HK | yes | yes | no |
| 3 | c2 | New | HK | no | no | no |
| 4 | c3 | New | SG | yes | yes | no |
| 5 | c4 | VIP | HK | yes | yes | yes |
| 6 | c4 | VIP | SG | yes | no | no |
| 7 | c5 | VIP | SG | yes | yes | yes |
| 8 | c5 | VIP | SG | no | no | no |

Client c1 receives two messages. Client c4 appears in both HK and SG. Neither is a duplicate message.

For this example, **Delivery Rate = delivered messages ÷ sent messages** and **Unique Clients = distinct non-NULL client ids among sent messages**. This example does not settle the definition of Reach, which this study leaves open (PRB-REACH in [03](03-problem-catalogue.md)).

The requested pivot has Typology in rows and Market in columns:

| Delivery Rate | HK | SG | All markets |
|---|---:|---:|---:|
| New | 66.7% | 100.0% | **75.0%** |
| VIP | 100.0% | 66.7% | **75.0%** |
| All typologies | **75.0%** | **75.0%** | **75.0%** |

Why are those totals 75%?

## 2. A rate needs its denominator

At the four detail groups:

| Group | Sent | Delivered | Delivery Rate | Unique Clients |
|---|---:|---:|---:|---:|
| New / HK | 3 | 2 | 66.7% | 2 |
| New / SG | 1 | 1 | 100.0% | 1 |
| VIP / HK | 1 | 1 | 100.0% | 1 |
| VIP / SG | 3 | 2 | 66.7% | 2 |

For New clients, the HK group contains three messages and the SG group one. An unweighted mean treats them equally:

```text
Mean of displayed rates:  (66.7% + 100.0%) / 2 = 83.3%
Rate over all New messages: (2 + 1) / (3 + 1) = 75.0%
```

More generally, let group i have delivered count d_i and sent count s_i:

$$
r_{total} = \frac{\sum_i d_i}{\sum_i s_i}
          = \frac{\sum_i s_i r_i}{\sum_i s_i},\qquad r_i=\frac{d_i}{s_i}.
$$

The weighted form assumes nonzero group denominators and complete, disjoint groups. The direct ratio of counts is clearer and avoids rounding the percentages first.

**Each rate has its own weights.** Delivery Rate uses Sent; Open Rate uses Delivered; CTOR uses Opened. Sent is not a universal weight.

## 3. Unique clients need overlap information

HK contains clients {c1, c2, c4}. SG contains {c3, c4, c5}. Adding their counts gives 3 + 3 = 6, but c4 appears twice.

$$
|HK \cup SG| = |HK| + |SG| - |HK \cap SG| = 3 + 3 - 1 = 5.
$$

At the grand total there are **five people**, not six. For VIP clients across both markets, the answer is two people (c4 and c5), not 1 + 2 = 3.

A scalar such as "3 unique clients" loses the identities needed to detect overlap. Either count distinct clients again over the total population, retain identity sets internally, or use an explicitly approved approximate sketch. Adding distinct-count scalars cannot solve the general case.

### Three kinds of number, three behaviours

| Kind | Example here | What a total needs | If you combine displayed cells instead |
|---|---|---|---|
| Count | Sent | Nothing extra: parts add up | Correct, as long as every message sits in exactly one part |
| Rate | Delivery Rate | Its numerator and its denominator | An average lands between the smallest and largest part. It lands on the answer only when part size and part rate are unrelated |
| Unique count | Unique Clients | The identities, or a fresh count at the total | A sum is the largest value the truth could take. The truth lies between the largest part and the sum |

Whether a unique count adds up depends on the split, not only on the metric. By typology the parts add up, 3 + 2 = 5, because no client has two typologies here. By market they do not, 3 + 3 = 6, because c4 is in both. The exact formulas and bounds are in [16](16-correctness-contract.md).

## 4. Define the inputs separately from the formula

Why not store each KPI as a SQL view and reuse it? Because a view fixes its grouping:

```sql
CREATE VIEW kpi_delivery AS
SELECT typology, market,
       COUNT(*) FILTER (WHERE is_delivered) * 1.0 / COUNT(*) AS delivery_rate
FROM message GROUP BY typology, market;

SELECT typology, AVG(delivery_rate) FROM kpi_delivery GROUP BY typology;   -- New: 83.3%, not 75.0%
```

The view kept the rate and discarded the counts, so the second query can only average. Standard SQL lets a query reuse another query's rows. It has no built-in way to reuse a KPI at a different grouping. Splitting a KPI into reusable inputs and a formula supplies that missing piece ([05](05-first-principles-solution.md) discusses SQL composability, Databricks metric views and Malloy). The rest of this guide uses these terms:

| Term | Plain meaning | Example |
|---|---|---|
| Atom | A named aggregate definition | delivered-message count |
| State | Information sufficient to merge or recompute | (delivered, sent), or a set of client ids |
| KPI | A formula evaluated after the required aggregation | delivered ÷ sent |
| Grouping set | Which dimensions are retained | (Typology, Market) or (Typology) |
| Node | One member group within a grouping set | New / all markets |
| Cell | One KPI value at one node | Delivery Rate for New / all markets |

The definition keeps the same meaning whether users group by Market, by Typology or by both. The model also records which filters and dimensions it supports, its time basis and its identity rule.

Definitions are reusable; SQL statements are an implementation choice. [05](05-first-principles-solution.md) compares the choices.

## 5. One SQL statement can compute the four grouping shapes

For this pivot, the grouping shapes are:

| Grouping set | Meaning | Output groups in this example |
|---|---|---:|
| (Typology, Market) | Detail | 4 |
| (Typology) | Each typology across markets | 2 |
| (Market) | Each market across typologies | 2 |
| () | Grand total | 1 |

That is **four grouping sets, nine output groups, and eighteen values for two KPIs**.

SQL `GROUPING SETS` can request all four shapes together:

```sql
-- Synthetic fixture: one row per message, columns defined in section 1.
WITH aggregate_counts AS (
  SELECT typology, market,
         GROUPING_ID(typology, market) AS gid,
         COUNT(*) AS sent,
         COUNT(*) FILTER (WHERE is_delivered) AS delivered,
         COUNT(DISTINCT client_id) AS clients
  FROM message
  GROUP BY GROUPING SETS ((typology, market), (typology), (market), ())
  HAVING COUNT(*) > 0
)
SELECT typology, market, gid, sent, delivered, clients,
       delivered * 1.0 / NULLIF(sent, 0) AS delivery_rate
FROM aggregate_counts;
```

The total rate is computed from counts at the total scope. The distinct count is also computed at that scope. The UI places the returned values into the pivot.

The `HAVING` clause implements this product's chosen "no input means no data" policy. `NULLIF` returns no rate when the denominator is zero. These are explicit conventions; a product can show a known zero count separately from an absent group.

### Tell an unknown member from a total

A real unknown Market and a rolled-up Market can both be SQL NULL. `gid` records which dimensions were rolled up:

| gid | Meaning |
|---:|---|
| 0 | Detail: neither dimension rolled up |
| 1 | Market rolled up: a Typology total |
| 2 | Typology rolled up: a Market total |
| 3 | Both rolled up: grand total |

`gid` identifies the grouping shape. The complete node key also includes its retained dimension values. New / all markets and VIP / all markets share gid 1 but are different nodes.

## 6. Reuse counts for new KPIs

The same eight messages contain 6 delivered, 5 opened and 3 clicked messages:

| KPI | Grand-total calculation | Value |
|---|---|---:|
| Delivery Rate | 6 / 8 | 75.0% |
| Open Rate | 5 / 6 | 83.3% |
| Click Rate | 3 / 6 | 50.0% |
| CTOR | 3 / 5 | 60.0% |

CTOR is `ratio(clicked, opened)`. Averaging the four cell CTORs gives 62.5%, which answers a different question: the equally weighted mean of cell rates.

Dividing Click Rate by Open Rate gives CTOR when the populations and nonzero denominators align. It needs domain checks. Defining CTOR directly as clicked/opened makes its denominator explicit.

## 7. Keep the message grain intact

One message can have several open events. An inner join of these eight messages to seven open events produces seven joined rows: message 1 appears three times and messages without opens vanish.

Counting those rows as "sent" gives 7; the actual sent count is 8. Counting them as opened messages gives 7; five messages were opened.

Reduce events to "at least one open per message" before joining, or aggregate separate facts independently and align the results. Match historical dimensions using valid time intervals. Grain and identity checks matter as much as the formula.

## 8. Choose the implementation after checking correctness

The six-KPI reporting example has twelve default grouping shapes. A naïve per-KPI/per-shape strategy issues 6 × 12 = 72 statements. That is a comparison baseline, not a necessary cost of correct reporting.

Compatible counts and rates often benefit from fused queries. Exact distincts can make grouping-set expansion expensive; separate queries or a different plan may be cheaper. A sketch trades exactness for estimation and needs a business-approved accuracy policy.

Native Databricks metric views are the preferred starting implementation: the retained default S4 fixture probe matches the SQL prototype at all 56 groups. A Malloy model matched the same 56 groups on local DuckDB, which confirms that the calculation contract can be met by more than one tool. These probes demonstrate the core calculation shape; remaining production contracts still need testing. Every implementation must meet the same calculation and governance contract ([05](05-first-principles-solution.md)). Prior recorded timing observations and their limits are in [08](08-complexity-and-performance.md).

## 9. What users should see

| Situation | Behavior |
|---|---|
| No rows for a group | "No data", with a separate status |
| Rows exist but no delivered messages | Known count 0; Delivery Rate 0 if Sent is positive |
| Rate denominator is zero | No rate; reason "zero denominator" |
| Unknown Market alongside a total | Separate "Unknown" and "All markets" labels |
| Unconfirmed Reach definition | Visible as unconfirmed; blocked from published reports |
| One required query fails | Failed/dependent cells labelled; a partial grid is never presented as complete |
| Data changes during separate queries | Use the planned source versions or return a consistency failure |
| Approximate client count | Visible approximate label and estimator metadata |

## 10. Verify the example and continue

Three checks work on any pivot, including this one, with no extra query:

1. **Counts add up.** Sent for New is 3 + 1 = 4; the two typology totals give 4 + 4 = 8.
2. **A rate is its own numerator over its own denominator.** The grand-total Delivery Rate is 6 / 8, read from the grand-total row.
3. **A unique total sits between its largest part and the sum of its parts.** By market: 3 ≤ 5 ≤ 6.

A grid that fails one of them is wrong. A grid that passes all three can still be wrong, for example if a join duplicated every message, so source checks remain necessary ([16](16-correctness-contract.md) C-CHECK).

Run the local fixture tests using the documented environment in [14](14-test-strategy-and-traceability.md). Databricks tests create/replace scratch tables and require an intentional workspace test setup; they are not a read-only check.

Then read [BUSINESS-CASE](BUSINESS-CASE.md) for the decision and the cost of a wrong total, [03](03-problem-catalogue.md) for the problems each scenario raises, [05](05-first-principles-solution.md) for alternatives, or [16](16-correctness-contract.md) for the complete algebra.
