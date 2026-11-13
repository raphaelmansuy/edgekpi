# Complexity and performance

> **In plain words.** Sharing compatible work can reduce repeated scans and scheduling overhead. Exact distinct counts can change the best plan. Choose the fastest plan that preserves the approved meaning, then measure it on the real workload.
>
> New here? Read [START-HERE](START-HERE.md) first.

Date: 2026-11-12. Plan candidates are defined in [07](07-planner-and-sql-generation.md). The correctness contract in [16](16-correctness-contract.md) is mandatory for every candidate.

**Evidence status.** The timing tables below are historical observations, preserved for investigation. The folder contains benchmark scripts, but no retained statement IDs, raw timing outputs, immutable source-version manifests or query profiles for those sessions. The Databricks benchmarks have not been rerun. Treat these numbers as unverified records, not production targets or proven platform behavior. The current local test result is reported separately in [14](14-test-strategy-and-traceability.md).

The recorded workloads were synthetic: DuckDB on a laptop at 3 M rows, and a serverless 2X-Small Photon warehouse at 3 M/100 M rows. The notes describe warm file cache, result-cache defeat and one to three runs per Databricks figure. Those setup claims also need reproduction. Production volumes, skew, concurrency, scheduling, cache state and other warehouse sizes are unknown.

## Symbols

| Symbol | Meaning | S4 example |
|---|---|---|
| N | Rows of the fact in the filtered window | 3,000,000 (benchmark) |
| K | KPIs requested | 6 |
| A | Distinct atoms those KPIs need | 5 (benchmark), 6 KPIs share them |
| G | Requested grouping sets (shapes, not result rows) | 12 |
| M | Result member rows across all grouping sets | 56 on the S4 fixture |
| L | KPI cells = M x K, before additional contexts | 336 for six KPIs |
| C | Distinct finest-grain cells | 4,320 (benchmark) |
| F | Facts touched by the request | 1 |

## PERF-ASYMPTOTICS

| Approach | Statements | Fact scans | Aggregation work | Memory |
|---|---|---|---|---|
| One query per KPI per node (baseline) | K x G = 72 | K x G | O(N x sum of atoms per statement) | M-sized per statement |
| One query per KPI, scalar totals in UI | K = 6 | up to K | Insufficient state for general rate/distinct totals | small |
| **Combined** candidate | Often F, or one statement with F fact subplans | Engine-dependent; inspect plan | O(N x G x A) state updates as a simple upper model; partial aggregation may reduce work | O(M x state size), including distinct state cardinality |
| Two-stage candidate | One CTE statement or multiple materialized stages | Engine-dependent | O(N x A) + O(C x G x A) | O(C x compatible state size) |
| **Split** candidate | Strategy-dependent; can batch compatible atoms/grouping sets | Inspect plan | Shared count/rate work plus scope-specific distinct work | Distinct-state memory and spill can dominate |
| Stored rollup + sketches | 1 read of the rollup | 0 base scans | O(M_stored x G) | O(M_stored x sketch size) |

The article states the honest second term: expanding grouping sets still touches every fact row once per requested set (`|F| x |G| x agg`), unless an order is reused. The one-pass plan accepts that term because it removes the **I/O** term (K x G scans) and the per-statement overhead, which are what scale with the number of KPIs. **Recorded warning:** the exact-distinct workload was slower in the combined candidate (F6/F7). This suggests testing split strategies; no retained profile establishes operator-level attribution. Adding a KPI whose dependencies are already present avoids another fact aggregation, but still adds O(M) formula evaluation and serialization. Total projection/payload work grows with K. A KPI introducing a new atom or context adds aggregation work too. A single SQL statement is not proof of one physical scan.

Other costs:

| Step | Cost |
|---|---|
| Model validation | O(atoms + KPIs + edges), done at load and on edit |
| Planning | At least dependency-graph traversal O(vertices + edges), plus grouping/context expansion and estimation |
| Assembly | O(M x K) cell placement/serialization, plus requested ordering; use full member-node keys, not `gid` alone |
| Intent signature and cache lookup | O(size of the intent), constant for a given report |
| Lattice size | rollup prefixes: product of (levels + 1) per axis. Full cube: 2^d. Capped (EC-GSET-EXPLOSION) |

## PERF-MEASURED-DUCKDB

3 M rows, 6 KPIs, 12 grouping sets, DuckDB, median of 5 runs. Two full runs on the same machine:

| Variant | Statements | Scans | Run 1 | Run 2 |
|---|---|---|---|---|
| Baseline (one statement per KPI per node) | 72 | 72 | 0.90 s | 0.88 s |
| One pass | 1 | 1 | 0.38 s | 0.38 s |

Another 3-run session on the same machine gave 1.38 s and 0.59 s, so absolute times drift by up to 2x between sessions. A partial third run gave 0.72 s and 0.34 s. The ratio stayed between 2.1x and 2.4x. So: **the statement count falls 72x, the elapsed time about 2.3x on this engine and size.** The small time ratio is expected: DuckDB runs cache-hot in memory, so repeated scans are cheap. A warehouse that reads Delta from object storage and pays per-statement overhead is a different regime. That was a hypothesis here, and the Databricks section below tests it.

### Finding F1 (DuckDB): exact `COUNT(DISTINCT)` dominates

Same table, same 12 grouping sets, stand-alone timings:

| Atoms | Time |
|---|---|
| Four distributive atoms (sent, delivered, opened, clicked) | 0.025 s |
| One exact `COUNT(DISTINCT client_id)` | 0.292 s |
| All five | 0.379 s |

The stand-alone timings are separate experiments, not additive parts of one query. Do not subtract them to assign a measured CPU or elapsed-time percentage to an operator. A query profile is needed for attribution. The records suggest distinct-heavy workloads deserve a separate candidate plan.

Consequence: benchmark exact distinct strategies as well as scan sharing. Approximation is a different, approved semantic contract, not an automatic optimizer substitution.

### Finding F2 (DuckDB): cost grows linearly with atoms

Adding synthetic atoms to the one-pass statement (each atom `COUNT(*) FILTER (WHERE hash(message_id + i) % 7 = 0)`):

| Atoms in statement | Run 1 | Run 2 |
|---|---|---|
| 11 | 0.55 s | 0.50 s |
| 17 | 0.72 s | 0.70 s |
| 29 | 1.10 s | 1.06 s |
| 53 | 2.10 s | 2.21 s |

Linear in A, as the table above predicts (about 0.04 s per added atom). Caveat: these synthetic atoms evaluate a hash per row, so they are heavier than plain flag counts. The slope depends on the atom expression.

### Finding F3 (DuckDB, 3 M rows): the two-stage plan does not pay

Stage 1 aggregates to the finest grain (4,320 cells for 3 M rows, a 694x reduction), stage 2 rolls cells up with `GROUPING SETS`. Parity with the one-pass result holds (asserted in `bench.py`). Distributive atoms only:

| Plan | Run 1 | Run 2 |
|---|---|---|
| One pass | 0.03 s | 0.02 s |
| Two stage | 0.03 s | 0.04 s |

No gain: DuckDB already aggregates four flag counts over 3 M rows in about 25 ms. It also does not help exact distinct counts: the stage-1 table would have to keep `(cell, client)` pairs, which is close to N when clients rarely repeat in a cell.

### Finding F4: what the DuckDB benchmark cannot show

- Scan I/O from object storage, Photon, AQE, shuffle cost of the grouping-sets expansion, warehouse queueing (historical Databricks observations below, for one warehouse size).
- Concurrency (several users issuing the same report).
- Skew (a typology with 90 percent of rows).
- Behaviour above memory.

## PERF-MEASURED-DBX

A Databricks serverless 2X-Small Photon warehouse. Same atoms, KPIs and 12 grouping sets as above. `bench_message_<N>` is generated with `range(N)` and hash functions (400,000 distinct clients, 4,320 finest cells). Every statement carries a unique harmless predicate so the query result cache cannot answer it.

### 3 million rows

| Variant | Statements | Median |
|---|---|---|
| Baseline: 6 KPIs x 12 grouping sets, one after the other | 72 | 67.9 s (67.4 to 68.4, 2 runs) |
| One pass, 5 atoms (exact `COUNT(DISTINCT client_id)`) | 1 | 3.99 s |
| One pass, 4 distributive atoms only | 1 | 1.57 s |
| One pass, 4 distributive + HLL lgK 12 | 1 | 2.13 s |
| Two stage, 4 distributive atoms (cells table, then rollup) | 2 | 3.19 s |

### 100 million rows

| Variant | Statements | Time |
|---|---|---|
| Baseline: 72 statements | 72 | 142.2 s (1 run) |
| of which 12 exact-distinct statements | 12 | 62.3 s (5.2 s each) |
| of which 60 other statements | 60 | 80.2 s (1.3 s each) |
| One pass, 5 atoms (exact `COUNT(DISTINCT)`) | 1 | **140.5 s** (139.3 to 141.6, 3 runs) |
| One pass, 4 distributive atoms only | 1 | **8.1 s** (8.0 to 8.5) |
| One pass, 4 distributive + HLL lgK 12 | 1 | 15.2 s (15.1 to 15.4) |
| Two stage, 4 distributive atoms | 2 | **4.1 s** (4.06 to 4.16) |

The split of the baseline (62.3 s and 80.2 s) comes from a separate run that measured the 12 exact-distinct statements and the 60 others on their own (sum 142.5 s, matching the 142.2 s total).

```
 100 M rows, Databricks serverless 2X-Small          each block = about 10 seconds
 ------------------------------------------------------------------------------------
 72 statements (baseline)      ██████████████ 142 s
   60 non-distinct statements  ████████ 80 s
   12 exact-distinct           ██████ 62 s
 ONE pass, exact distinct      ██████████████ 140 s      <- no gain: the distinct atom dominates
 ONE pass, HLL lgK 12          █▌ 15 s
 ONE pass, no unique clients   ▊ 8 s                      <- vs 80 s for the 60 matching statements
 TWO stages, no unique clients ▍ 4 s
```

### Finding F5 (recorded Databricks, 3 M): statement overhead is a plausible explanation

The recorded 67.9 s over 72 sequential statements averages about 0.94 s each. The records do not separate API, planning, queueing and execution time, so they cannot establish that almost all latency is fixed overhead. Fewer statements are a plausible explanation for the recorded 17x difference. Reproduce with profiles and include a batched multi-measure baseline before attributing the improvement.

### Finding F6 (Databricks, 100 M): the exact distinct atom decides everything

At 100 M rows one pass with all five atoms (140.5 s) is **no faster than the baseline (142.2 s)**. Remove the exact distinct atom and one pass drops to 8.1 s. The 60 baseline statements that do not count unique clients take 80.2 s, so for those KPIs one pass is about 10x faster and two stages about 20x. The headline "72 statements become 1" is true for the number of statements. For elapsed time it holds only for the distributive and algebraic atoms.

### Finding F7 (recorded Databricks, 100 M): test a split exact candidate

The recorded 12 exact-distinct statements took 62.3 s in total, while the combined plan took 140.5 s. The difference `140.5 - 8.1 = 132.4 s` is **not** an isolated operator timing: adding distinct can change the whole physical plan. The notes record a Photon expansion and multiple aggregation stages, but the plan artifact is not retained. Profile both candidates to explain the result. At 3 M rows the order reverses: one pass (4.0 s) beats 12 separate statements (about 11 s at 0.94 s each). The better plan depends on the workload and execution environment. No crossover has been established; N alone is insufficient.

### Finding F8 (recorded Databricks, 100 M): HLL is a promising approximate candidate

One pass with HLL lgK 12 takes 15.2 s, 9x faster than with the exact count, and about 9x faster than the whole baseline. Accuracy on this synthetic set (400,000 distinct clients, one sample):

| lgConfigK | Estimate vs exact (400,000) | Relative error |
|---|---|---|
| 10 | 380,342 | 4.91 % |
| 12 | 390,131 | 2.47 % |
| 14 | 398,103 | 0.47 % |

These three outcomes describe one population, not a guaranteed error bound. The classic `1.04 / sqrt(2^lgK)` rule is a rough scale estimate, not a confidence guarantee for the exact engine sketch implementation. A recorded sample below 2% at lgK 14 does not prove a universal 2% acceptance target. Agree an error budget and confidence/validation method, test representative populations and partitions, and show approximation metadata. Time at lgK 14 was not recorded. Exact alternatives such as layout improvements, batched splits and deduplicated relations remain candidates.

### What this does to the design

| Decision | Evidence |
|---|---|
| Keep the **single pass** for distributive and algebraic atoms | F6 |
| Benchmark **Split** against combined execution; enable only after parity and workload-specific evidence | Recorded F6/F7 suggest this experiment |
| Keep **exact** as the default for numbers that need it, **HLL** as a declared atom mode with an agreed error | F8 |
| Keep two-stage as an **opt-in**, enabled after representative benefit is measured | F3 (loses at N/C = 694 on DuckDB, loses on Databricks at 3 M: 3.19 s vs 1.57 s, the two statements include creating the cells table), wins 2x at N/C = 23,000 (4.1 s vs 8.1 s) |

## PLAN-TWOSTAGE (specified, optional)

```
stage 1:  cells = SELECT <finest dims>, <atom states> FROM fact WHERE ... GROUP BY <finest dims>
stage 2:  SELECT <dims>, GROUPING_ID(...), SUM(sent), SUM(delivered), ...
          FROM cells GROUP BY GROUPING SETS (...)       -- formulas applied after
```

Consider it when compatible mergeable states substantially reduce rows and a benchmark demonstrates a net benefit. Include stage creation, reuse, freshness and access-control costs. The recorded `N/C` ratios are workload examples, not selection thresholds. Algebraic atoms store their declared state tuple. Exact holistic atoms are excluded. HLL atoms use `hll_union_agg` in stage 2 with a fixed lgK. Parity rule: the plan must equal the one-pass result in the oracle test (FP-10). The derivation guard is SC-TOTAL in [15](15-edge-cases-and-state-charts.md).

## PERF-BUDGET

Targets for the product (to be validated on Databricks, not claimed):

| Metric | Target | Why |
|---|---|---|
| Statements / scans per request | Minimize compatible repeated work within the correctness and latency budget | Strategy-dependent; inspect actual physical plan |
| Planner overhead | below 50 ms for 100 KPIs and 5 dimensions (pure Python, no I/O) | negligible next to the warehouse |
| KPI cells per response | cap 50,000 by default, plus a response-byte limit | Count M x K x contexts; enforce during execution too |
| Dimensions per request | at most 8 (31 absolute) | G growth |

## PERF-DBX: benchmark plan and status

| Id | Experiment | Status | Result |
|---|---|---|---|
| B1 | S4: baseline 72 statements vs one pass, 3 M and 100 M rows | **historically recorded** | Recorded 17x at 3 M (cause not isolated). 1.0x at 100 M with exact distinct (F6) |
| B2 | Exact distinct vs `hll_sketch_agg` | **historically recorded** (time, 100 M and 3 M; error, 100 M) | 9x faster, error 2.47 % at lgK 12, 0.47 % at lgK 14 (F8). Time at lgK 14 not measured |
| B3 | Two-stage vs one pass, distributive atoms | **historically recorded** | Loses at 3 M, wins 2x at 100 M (F3, F6). Threshold unknown |
| B4 | Grouping-sets expansion with 5, 6, 8 dimensions | planned | Confirms the cap |
| B5 | Result for a user with a row filter or ABAC policy | planned | Stored rollups must be bypassed (EC-ABAC) |
| B6 | Combined, batched split and per-set exact distinct across row/cardinality/skew/concurrency ranges | planned | Builds a workload-specific selection policy; all runs pin the same sources |
| B7 | Several concurrent requests of the same shape | planned | Contention on one warehouse |

Every new experiment must retain: exact SQL and parameters; pinned source versions and generated-data seed; expected result checksum; engine/runtime and library versions; warehouse/Photon configuration; cold/warm cache procedure; queue/planning/execution timings; repeated-run distribution; query profile and spill; scanned bytes; concurrency; and billed compute if available. Compare identical semantics, including exactness and snapshot consistency.

Add a practical baseline that combines all six KPI aggregates in each of the 12 independent grouping queries. The existing 72-query baseline represents one integration design, not the best available exact alternative. Report end-to-end p50/p95 and cost per successful pivot; elapsed seconds alone do not establish a financial return.

## What would change these decisions

| Observation | Decision |
|---|---|
| Representative B6 measurements consistently favor a candidate | Enable a guarded policy for that workload shape, with fallback and monitoring |
| Two-stage wins repeatedly on representative workloads | Enable only for validated compatible-state cases, with monitored cost and freshness |
| Business requires a hard error ceiling | Keep exact unless an approved probabilistic contract satisfies the requirement; a larger lgK alone does not guarantee a ceiling |
| Native metric views satisfy remaining production contracts at acceptable cost | Use the preferred native semantic backend; retained S4 fixture parity already passes, while production filters/policies and comparative cost remain open ([05](05-first-principles-solution.md), [14](14-test-strategy-and-traceability.md)) |
