# 07. CLI and UX

> What a person sees and does. The command line is implemented and tested; the report-builder screens are wireframes of what a graphical interface would need from the library, marked as proposed.

Related: [README](README.md) · [01 UX lens](01-lenses.md#4-ux-and-ui-designer) · [04 result](04-domain-model-and-definitions.md#the-result) · [08 assistant](08-ai-and-integration.md) · [kpi/12 UX and wireframes](../kpi/12-ux-and-wireframes.md)

Code: [cli.py](../../edgekpi/cli.py), [render.py](../../edgekpi/render.py). Tests: [test_cli_and_scaling.py](../../tests/test_cli_and_scaling.py).

## Design rules

| Rule | How it shows |
|---|---|
| Show what was asked, including what was left out | a rolled-up total is labelled `Total` or `All`; a missing node is blank; a zero denominator is `-` |
| A NULL member is a member | the unknown group reads `(none)`, never merged into `Total` |
| An error is a sentence with a code | `REQ_UNKNOWN_KPI: unknown KPI 'ghost'; known: [...]`, exit status 1 |
| Say what was checked | every run prints its lifecycle states and the reconciliation result |
| One screen, one decision | five commands, each doing one thing |

## Navigation of the command line (implemented)

```
                                  edgekpi
        ┌──────────┬───────────┬─────────┴───┬───────────┬──────────────┐
     validate    compile       run          verify      check-grain     infer
        │           │           │             │             │             │
   model.yaml   model.yaml   model.yaml    model.yaml    model.yaml    templates.sql
                request.json request.json  request.json   --data        --name --key
                --backend    --data        --data                      --dim name=expr
                (sql |       --backend     [--databricks]              [--data]
                metric-view  [--databricks]
                | malloy)
        │           │           │             │             │             │
   what is in    the exact   a pivot per    every backend  keys unique,  model draft
   the model     statements  KPI, states,   against the    joins keep    + refusals
                 per backend reconciliation reference     one row/key   + notes
```

ASCII-only variant of the same map, for terminals without box drawing:

```
edgekpi --+-- validate MODEL
          +-- compile  MODEL REQUEST [--backend sql|metric-view|malloy]
          +-- run      MODEL REQUEST --data SCRIPT [--backend ...] [--databricks]
          +-- verify   MODEL REQUEST --data SCRIPT [--databricks]
          +-- check-grain MODEL --data SCRIPT
          +-- infer    TEMPLATES --name N --key K --dim NAME=EXPR... [--data SCRIPT]
```

## Commands

```
pip install -e .[dev]                                    # Python 3.10+
(cd edgekpi/backends/malloy_runtime && npm install)      # only for the Malloy backend

export DATABRICKS_CONFIG_PROFILE=<profile> EDGEKPI_DBX_WAREHOUSE=<warehouse id>   # only for --databricks

python -m edgekpi validate examples/registry/model.yaml
python -m edgekpi compile  examples/registry/model.yaml examples/registry/request-small.json --backend malloy
python -m edgekpi run      examples/registry/model.yaml examples/registry/request-pivot.json \
                           --data ../../examples/registry/data.sql
python -m edgekpi verify   examples/registry/model.yaml examples/registry/request-pivot.json \
                           --data ../../examples/registry/data.sql --databricks
```

## Screens (implemented, real output)

### Validate screen

```
$ python -m edgekpi validate examples/registry/model.yaml
model engagement v1 [d1480738f4b1] over message (key message_id)
  joins      : client->client
  dimensions : typology, tier, market, send_year
  measures   : n_sent[count], n_delivered[count], n_opened[count], n_clicked[count], n_reached[unique]
  kpis       : sent[confirmed], reached[unconfirmed], delivery_rate[confirmed], open_rate[confirmed], click_rate[confirmed], ctor[confirmed]
  filters    : from_date?, to_date?
```

`[unique]` warns the reader that Reach does not add up; `?` marks an optional filter.

### Run screen

```
$ python -m edgekpi run examples/registry/model.yaml examples/registry/request-small.json --data ...data.sql
Message Sent
+----------+----+----+----+-----+
| typology | HK | JP | SG | All |
+----------+----+----+----+-----+
| (none)   |  1 |    |    |   1 |      <- a NULL member: the client is missing from the dimension
| New      |  3 |    |    |   3 |
| VIP      |  1 |  1 |  2 |   4 |
| Total    |  5 |  1 |  2 |   8 |      <- the grand total, a different node from (none)
+----------+----+----+----+-----+

Delivery Rate
+----------+--------+------+-------+--------+
| typology |     HK |   JP |    SG |    All |
+----------+--------+------+-------+--------+
| (none)   | 100.0% |      |       | 100.0% |
| New      |  66.7% |      |       |  66.7% |
| VIP      | 100.0% | 0.0% | 50.0% |  50.0% |
| Total    |  80.0% | 0.0% | 50.0% |  62.5% |      <- 5/8, not the mean of the cells above
+----------+--------+------+-------+--------+

Reach
+----------+----+----+----+-----+
| typology | HK | JP | SG | All |
+----------+----+----+----+-----+
| VIP      |  1 |  0 |  1 |   1 |      <- 1 + 0 + 1 = 2 across markets, but 1 client: distinct counts do not add
| Total    |  4 |  0 |  1 |   4 |      <- 4 + 0 + 1 = 5 across markets, but 4 clients
+----------+----+----+----+-----+

states: VALIDATED > COMPILED > EXECUTED > ASSEMBLED > RECONCILED
reconciliation: all checks pass
```

Annotations are added here; the program prints none. Rows for `(none)` and `New` of Reach are omitted for width. The values are those of the registry-style example data with `start_date = 2026-01-01`.

### Verify screen

```
$ python -m edgekpi verify examples/registry/model.yaml examples/registry/request-pivot.json --data ... --databricks
sql on duckdb                match   9 nodes  0 diffs, 0 violations
malloy on duckdb             match   9 nodes  0 diffs, 0 violations
sql on databricks            match   9 nodes  0 diffs, 0 violations
metric view on databricks    match   9 nodes  0 diffs, 0 violations
malloy on databricks         match   9 nodes  0 diffs, 0 violations
```

Exit status is 0 only if every line says `match`. A backend that fails is reported on its own line with its error code, so one cannot hide another ([conformance.py](../../edgekpi/conformance.py)).

### Error screen

```
$ python -m edgekpi compile examples/registry/model.yaml bad.json
REQ_UNKNOWN_KPI: unknown KPI 'ghost'; known: ['sent', 'reached', 'delivery_rate', 'open_rate', 'click_rate', 'ctor']

REQ_UNCONFIRMED_KPI: KPI reached is unconfirmed; a published report accepts confirmed KPIs only

REQ_BAD_PARAM: parameter start_date: day is out of range for month
```

Each is a different invocation; they appear together here. Messages go to standard error, the exit status is 1.

## Wireframes for a graphical interface (proposed, not built)

These show what each screen needs from the library, so a future interface is a thin layer.

### Screen map

```
  ┌──────────────┐    ┌───────────────┐    ┌────────────────┐    ┌───────────────┐
  │ 1 KPI        │───▶│ 2 Report      │───▶│ 3 Result       │───▶│ 4 Export /    │
  │   catalogue  │    │   builder     │    │   + checks     │    │   publish     │
  └──────┬───────┘    └───────────────┘    └────────────────┘    └───────────────┘
         │ owner path                                │ explain a number
         ▼                                           ▼
  ┌──────────────┐                           ┌────────────────┐
  │ 5 Definition │                           │ 6 Why is this  │
  │   review     │                           │   total this?  │
  └──────────────┘                           └────────────────┘
```

### 1. KPI catalogue (needs `catalog(model)`)

```
┌ KPI catalogue ──────────────────────────────────────────────────────────┐
│ Search [____________]   Status [all ▾]                                  │
├─────────────────────┬───────────────┬──────────────┬────────────────────┤
│ KPI                 │ Status        │ Owner        │ Unit               │
├─────────────────────┼───────────────┼──────────────┼────────────────────┤
│ Message Sent        │ ● confirmed   │ CRM owner    │ count              │
│ Delivery Rate       │ ● confirmed   │ CRM owner    │ percent            │
│ Reach               │ ◌ unconfirmed │ CRM owner    │ count  ⚠ distinct  │
└─────────────────────┴───────────────┴──────────────┴────────────────────┘
 ⚠ distinct: totals are not the sum of the parts            [Open definition]
```

### 2. Report builder (needs `request_json_schema`, `validate`)

```
┌ New report ─────────────────────────────────────────────────────────────┐
│ KPIs      [Message Sent ✕] [Delivery Rate ✕] [+ add]                    │
│ Rows      [Typology ✕] [+ add]        Totals [x] subtotals              │
│ Columns   [Market ✕]   [+ add]        Totals [x] grand total            │
│ Filters   Market is any of [HK ✕] [SG ✕]                                │
│ Dates     From [2026-01-01]  To [        ]   (end excluded)             │
│ Backend   (•) generated SQL  ( ) metric view  ( ) Malloy               │
│                                                                         │
│ 4 scopes × 3 measures = 12 aggregate states         [Preview SQL] [Run] │
└─────────────────────────────────────────────────────────────────────────┘
   errors appear under the field, with the code:  Dates  ⚠ REQ_BAD_PARAM
```

The cost line is `estimate(report).description`.

### 3 and 6. Result and explanation (needs `Grid`, `reconcile.check`)

```
┌ Delivery Rate ──────────────────────────────────────── ✔ 0 violations ┐
│              HK        SG        All                                  │
│ New         66.7%    100.0%     83.3%                                 │
│ VIP        100.0%     66.7%     75.0%                                 │
│ Total       75.0%     83.3%     80.0%  ◀ click                        │
└───────────────────────────────────────────────────────────────────────┘
┌ Why is Total / All 80.0%? ────────────────────────────────────────────┐
│ Delivered 8 ÷ Sent 10 = 80.0%        (scope: all rows, filters kept)  │
│ Not the average of 83.3% and 75.0%, which would be 79.2%              │
└───────────────────────────────────────────────────────────────────────┘
```

The explanation is two measures from the same node (`grid.get(...)`) and the formula (`Kpi.formula`); no extra query.

### 5. Definition review (needs `loader.dumps`, `fingerprint`)

```
┌ Review: Open Rate  (draft, inferred from open-rate) ───────────────┐
│ Formula      opened ÷ delivered        ratio(n_opened, n_delivered)     │
│ Measures     n_opened      COUNT(*) FILTER(WHERE is_opened)             │
│              n_delivered   COUNT(*) FILTER(WHERE is_delivered)          │
│ Legacy       try_divide(COUNT_IF(C.is_opened), COUNT_IF(C.is_delivered))│
│ Parity       200 values compared, 0 different                           │
│ Note         division is now guarded: zero denominator gives blank      │
│                                         [Reject] [Mark unconfirmed]     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Accessibility and language

The CLI prints plain text with fixed-width columns and no colour, so it works in any terminal, a log or a screen reader. Percentages are written with one decimal and a sign, counts with thousands separators. Labels come from the model (`label` field), not from the code, so a host can localise them.
