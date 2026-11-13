# Retained validation: native metric view and generated SQL — 12 November 2026

This evidence supports the preferred native metric-view implementation for the **core synthetic S4 calculation**. It does not establish production readiness or performance.

## What ran

The statements ran on a Databricks serverless SQL warehouse (identifiers withheld). The source table's columns were described before the queries were written. Its intended grain is one sent message per row.

| Check | Result |
|---|---|
| Local fixture suite | 54 passed, 43 skipped, 2 expected failures |
| Generated SQL | 56 groups; one result chunk; not truncated |
| Native temporary metric view | 56 groups; one result chunk; not truncated |
| Integer aggregate parity | Sent, Delivered, Opened, Clicked and Clients all match the local fixture exactly |
| Formula parity | Delivery, Open, Click and CTOR all match within 1e-12 |
| Grouping identity | All five dimensions plus gid match; 12 default grouping shapes |

The native probe defined a **temporary** metric view, referenced its aggregate measures in composed rate measures, and queried all 12 shapes using `MEASURE()` and `GROUPING SETS` inside one non-atomic SQL compound statement. It created no persistent table or view. The generated probe was a SELECT against the existing synthetic fixture.

The warehouse was stopped initially and started for these statements. Raw responses include schema/row manifests; identifiers are replaced by placeholders. They contain aggregated synthetic values, without client identities.

## Files and reproduction

| File | Purpose |
|---|---|
| [review-manifest.json](review-manifest.json) | Warehouse description, scope, limitations and file hashes |
| [generated-s4.sql](generated-s4.sql), [native-s4.sql](native-s4.sql) | Exact executed SQL |
| [generated-request.json](generated-request.json), [native-request.json](native-request.json) | Exact Statement Execution API payloads (warehouse id replaced by a placeholder) |
| [generated-response.json](generated-response.json), [native-response.json](native-response.json) | Complete API responses |
| [parity-summary.json](parity-summary.json) | Successful parity-check output |
| [replay_results.py](replay_results.py) | Offline result/manifest checks against the local fixture |
| [local-tests.txt](local-tests.txt) | Local test output |
| [requirements-test.txt](../../fixtures/requirements-test.txt) | Exact local dependency versions |

From the repository root, in the environment described in [14](../../14-test-strategy-and-traceability.md):

```bash
.venv/bin/python specs/kpi/validation/2026-11-12/replay_results.py
```

This offline replay reads the retained responses, checks completeness, builds the local synthetic fixture, and compares every returned value. It does not contact Databricks.

A fresh target run requires a warehouse you are authorized to use and a compatible, described source. Request files carry a placeholder warehouse id that must be replaced, and they read a scratch table that must exist. This probe is distinct from the existing full Databricks test tier, which creates/replaces scratch tables.

## Limits of this evidence

- Only the nonempty, default S4 fixture and its 12 prefix shapes were tested remotely. Additional NULL/empty populations, optional scopes, production filters, permissions, mixed facts and context operators still need conformance tests.
- These formulas and synthetic clients demonstrate calculation behavior; they are not owner approval for production definitions or Reach.
- The two remote probes did not pin a shared immutable source version. Equal observed results are not proof of multi-query snapshot consistency.
- The compute runtime version was not captured. Warehouse configuration is recorded; it is not a runtime version.
- No comparative timing, query profile, production load or billing measurement was made. Native support makes a smaller custom implementation plausible; it does not prove cheaper compute.
- Benchmark claims elsewhere in the specification are not authenticated by these results.
