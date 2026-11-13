"""Local microbenchmark for ../08-complexity-and-performance.md (PERF-MEASURED).
DuckDB on one laptop, synthetic data. It validates SCALING SHAPE (statements and scans), not Databricks latency.
Run: uv run --with duckdb python specs/kpi/fixtures/bench.py [rows]
"""
import statistics, sys, time
import duckdb
from mini_planner import Atom, Kpi, grouping_sets, oracle_sql, plan_sql

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3_000_000
con = duckdb.connect()
con.execute(f"""
CREATE TABLE message AS
SELECT i AS message_id,
       'C' || CAST((hash(i) % 400000) AS VARCHAR) AS client_id,
       (ARRAY['New','Existing','VIP'])[CAST(1 + (hash(i*3) % 3) AS BIGINT)] AS typology,
       (ARRAY['Gold','Silver','Bronze'])[CAST(1 + (hash(i*5) % 3) AS BIGINT)] AS tier,
       'CMP' || CAST(hash(i*7) % 40 AS VARCHAR) AS campaign,
       2024 + (hash(i*11) % 3) AS yr,
       (ARRAY['HK','SG','CN','JP'])[CAST(1 + (hash(i*13) % 4) AS BIGINT)] AS market,
       (hash(i*17) % 100) < 92 AS is_delivered,
       (hash(i*19) % 100) < 40 AS is_opened,
       (hash(i*23) % 100) < 12 AS is_clicked
FROM range({N}) t(i)""")
ATOMS = [Atom("sent","COUNT(*)"),Atom("delivered","COUNT(*) FILTER (WHERE is_delivered)"),
         Atom("opened","COUNT(*) FILTER (WHERE is_opened)"),Atom("clicked","COUNT(*) FILTER (WHERE is_clicked)"),
         Atom("clients","COUNT(DISTINCT client_id)")]
BY = {a.name:a for a in ATOMS}
KPI_ATOMS = {"message_sent":["sent"],"message_reached":["clients"],"delivery_rate":["delivered","sent"],
             "open_rate":["opened","delivered"],"click_rate":["clicked","delivered"],"ctor":["clicked","opened"]}
KPIS = [Kpi.ratio("delivery_rate","delivered","sent"),Kpi.ratio("open_rate","opened","delivered"),
        Kpi.ratio("click_rate","clicked","delivered"),Kpi.ratio("ctor","clicked","opened")]
ROWS, COLS = ["typology","tier","campaign"], ["yr","market"]

def timed(fn, reps=5):
    ts=[]
    for _ in range(reps):
        t=time.perf_counter(); fn(); ts.append(time.perf_counter()-t)
    return statistics.median(ts)

def baseline():
    nodes = grouping_sets(ROWS, COLS)
    for atoms in KPI_ATOMS.values():
        for node in nodes:
            con.execute(oracle_sql("message",[BY[a] for a in atoms],node)).fetchall()
def one_pass():
    con.execute(plan_sql("message",ATOMS,KPIS,ROWS,COLS)).fetchall()

nodes = len(grouping_sets(ROWS, COLS))
print(f"rows={N:,}  KPIs=6  nodes={nodes}")
print(f"baseline  statements={6*nodes:3d}  scans={6*nodes:3d}  median={timed(baseline):6.2f}s")
print(f"one pass  statements=  1  scans=  1  median={timed(one_pass):6.2f}s")
# scale in K at fixed nodes: add synthetic atoms
for k in (6, 12, 24, 48):
    extra=[Atom(f"x{i}", f"COUNT(*) FILTER (WHERE hash(message_id + {i}) % 7 = 0)") for i in range(k)]
    f=lambda: con.execute(plan_sql("message", ATOMS+extra, KPIS, ROWS, COLS)).fetchall()
    print(f"one pass, atoms={len(ATOMS)+k:3d}: median={timed(f):6.2f}s")

# ---- two-stage plan (PLAN-TWOSTAGE): distributive atoms only, then roll up from cells ----------------
DIST = [a for a in ATOMS if a.name != "clients"]
DIMS = ROWS + COLS
SETS = ", ".join("(" + ", ".join(s) + ")" for s in grouping_sets(ROWS, COLS))
DIM_LIST = ", ".join(DIMS)

def two_stage():
    con.execute(f"CREATE OR REPLACE TEMP TABLE cells AS SELECT {DIM_LIST}, " +
                ", ".join(f"{a.expr} AS {a.name}" for a in DIST) + f" FROM message GROUP BY {DIM_LIST}")
    return con.execute(f"SELECT {DIM_LIST}, GROUPING_ID({DIM_LIST}) AS gid, " +
                ", ".join(f"SUM({a.name}) AS {a.name}" for a in DIST) +
                f" FROM cells GROUP BY GROUPING SETS ({SETS})").fetchall()

def one_pass_dist():
    return con.execute(plan_sql("message", DIST, [], ROWS, COLS)).fetchall()

a, b = two_stage(), one_pass_dist()
norm = lambda rows: sorted((tuple(map(str, r[:6])) + tuple(int(x) for x in r[6:])) for r in rows)
assert norm(a) == norm(b), "two-stage differs from one-pass"
cells = con.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
print(f"two-stage parity OK, cells={cells:,} (N/cells = {N/cells:,.0f}x)")
print(f"one pass, distributive atoms only: median={timed(one_pass_dist):6.2f}s")
print(f"two stage, distributive atoms only: median={timed(two_stage):6.2f}s")
