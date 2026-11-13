"""B1-B3 on Databricks (../08-complexity-and-performance.md PERF-DBX). Needs the opt-in variables of dbx_runner.py.
Run: python bench_dbx.py [rows] [baseline_reps]
Honest limits: ONE serverless 2X-Small warehouse, synthetic data, warm file cache. The query result cache is defeated by a
unique harmless predicate per run. Each number includes the Statement Execution API round trip, which is part of the real cost
of 72 statements versus 1. Medians are over the stated number of runs; with few runs read them as orders of magnitude.
"""
import itertools, statistics, sys, time

import dbx_runner
from mini_planner import Atom, Kpi, Part, grouping_sets, oracle_sql, plan_sql

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3_000_000
BASE_REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 1
d = dbx_runner.Dbx()
d.run(f"CREATE SCHEMA IF NOT EXISTS {dbx_runner.CATALOG}.{dbx_runner.SCHEMA}")
T = f"bench_message_{N}"
t0 = time.time()
d.run(f"""
CREATE OR REPLACE TABLE {T} AS
SELECT id AS message_id,
       CONCAT('C', CAST(pmod(hash(id), 400000) AS STRING)) AS client_id,
       element_at(array('New','Existing','VIP'), CAST(pmod(hash(id*3), 3) AS INT) + 1) AS typology,
       element_at(array('Gold','Silver','Bronze'), CAST(pmod(hash(id*5), 3) AS INT) + 1) AS tier,
       CONCAT('CMP', CAST(pmod(hash(id*7), 40) AS STRING)) AS campaign,
       2024 + CAST(pmod(hash(id*11), 3) AS INT) AS yr,
       element_at(array('HK','SG','CN','JP'), CAST(pmod(hash(id*13), 4) AS INT) + 1) AS market,
       pmod(hash(id*17), 100) < 92 AS is_delivered,
       pmod(hash(id*19), 100) < 40 AS is_opened,
       pmod(hash(id*23), 100) < 12 AS is_clicked
FROM range({N})""")
print(f"table {T}: {d.run(f'SELECT COUNT(*) AS n FROM {T}')[0]['n']:,} rows, built in {time.time()-t0:.0f}s")

ATOMS = [Atom("sent", "COUNT(*)"), Atom("delivered", "COUNT(*) FILTER (WHERE is_delivered)"),
         Atom("opened", "COUNT(*) FILTER (WHERE is_opened)"), Atom("clicked", "COUNT(*) FILTER (WHERE is_clicked)"),
         Atom("clients", "COUNT(DISTINCT client_id)")]
HLL = [a for a in ATOMS if a.name != "clients"] + [Atom("clients", "hll_sketch_estimate(hll_sketch_agg(client_id, 12))")]
DIST = [a for a in ATOMS if a.name != "clients"]
BY = {a.name: a for a in ATOMS}
KPI_ATOMS = {"message_sent": ["sent"], "message_reached": ["clients"], "delivery_rate": ["delivered", "sent"],
             "open_rate": ["opened", "delivered"], "click_rate": ["clicked", "delivered"], "ctor": ["clicked", "opened"]}
KPIS = [Kpi.ratio("delivery_rate", "delivered", "sent"), Kpi.ratio("open_rate", "opened", "delivered"),
        Kpi.ratio("click_rate", "clicked", "delivered"), Kpi.ratio("ctor", "clicked", "opened")]
ROWS, COLS = ["typology", "tier", "campaign"], ["yr", "market"]
DIMS = ROWS + COLS
nodes = grouping_sets(ROWS, COLS)
tok = itertools.count(1)
fresh = lambda: f"message_id >= -{next(tok)}"          # defeats the query result cache, keeps every row


def timed(label, fn, reps, warm=True):
    if warm:
        fn()  # warm-up (file cache, warehouse)
    ts = []
    for _ in range(reps):
        s = time.time(); fn(); ts.append(time.time() - s)
    print(f"{label:58s} median {statistics.median(ts):7.2f}s  min {min(ts):6.2f}  max {max(ts):6.2f}  (n={reps})", flush=True)
    return statistics.median(ts)


def baseline():
    for atoms in KPI_ATOMS.values():
        for node in nodes:
            d.run(oracle_sql(T, [BY[a] for a in atoms], node, where=fresh()))

one = lambda atoms: (lambda: d.run(plan_sql(T, atoms, [], ROWS, COLS, where=fresh())))
print(f"\nrows={N:,}  KPIs=6  nodes={len(nodes)}  baseline statements={6*len(nodes)}")
b = timed("baseline: 72 statements (6 KPIs x 12 nodes), sequential", baseline, BASE_REPS, warm=False)
o = timed("one pass, 5 atoms (exact COUNT(DISTINCT client_id))", one(ATOMS), 3)
timed("one pass, 4 distributive atoms only", one(DIST), 3)
timed("one pass, 4 distributive + HLL lgK 12 for clients", one(HLL), 3)

def two_stage():
    d.run(f"CREATE OR REPLACE TABLE {T}_cells AS SELECT {', '.join(DIMS)}, " + ", ".join(f"{a.expr} AS {a.name}" for a in DIST)
          + f" FROM {T} WHERE {fresh()} GROUP BY {', '.join(DIMS)}")
    sets = ", ".join("(" + ", ".join(s) + ")" for s in nodes)
    d.run(f"SELECT {', '.join(DIMS)}, GROUPING_ID({', '.join(DIMS)}) AS gid, " + ", ".join(f"SUM({a.name}) AS {a.name}" for a in DIST)
          + f" FROM {T}_cells GROUP BY GROUPING SETS ({sets})")
timed("two stage, 4 distributive atoms (cells table + rollup)", two_stage, 3)
print(f"\nstatements: baseline 72 vs one pass 1.   time ratio baseline / one pass = {b/o:.1f}x")
