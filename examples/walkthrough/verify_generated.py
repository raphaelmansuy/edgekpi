"""Option 3: generated SQL. Regenerates 3-generated.sql with the prototype planner, runs it on DuckDB
against message.sql and checks all nine member groups of the Typology x Market pivot.

Run from the repository root, in the environment of ../../specs/kpi/fixtures/requirements-test.txt:
    python verify_generated.py            # check
    python verify_generated.py --write    # rewrite 3-generated.sql
"""
import pathlib
import sys

import duckdb

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "specs" / "kpi" / "fixtures"))
from mini_planner import Atom, Kpi, plan_sql  # noqa: E402

# The catalogue entries of 3-definitions.yaml, in the prototype's form.
MEASURES = [
    Atom("sent", "COUNT(*)"),
    Atom("delivered", "COUNT(*) FILTER (WHERE is_delivered)"),
    Atom("unique_clients", "COUNT(DISTINCT client_id)"),
]
KPIS = [Kpi.ratio("delivery_rate", "delivered", "sent")]
# The request of 3-request.json: rows, columns, totals on both axes.
SQL = plan_sql("message", MEASURES, KPIS, row_dims=["typology"], col_dims=["market"]) + "\n"

# (typology, market) -> (gid, sent, delivered, unique_clients, delivery rate in %)
EXPECTED = {
    ("New", "HK"): (0, 3, 2, 2, 66.7), ("New", "SG"): (0, 1, 1, 1, 100.0),
    ("VIP", "HK"): (0, 1, 1, 1, 100.0), ("VIP", "SG"): (0, 3, 2, 2, 66.7),
    ("New", None): (1, 4, 3, 3, 75.0), ("VIP", None): (1, 4, 3, 2, 75.0),
    (None, "HK"): (2, 4, 3, 3, 75.0), (None, "SG"): (2, 4, 3, 3, 75.0),
    (None, None): (3, 8, 6, 5, 75.0),
}

target = HERE / "3-generated.sql"
if "--write" in sys.argv:
    target.write_text(SQL)
assert target.read_text() == SQL, "3-generated.sql is not what the planner generates"

con = duckdb.connect()
con.execute((HERE / "message.sql").read_text())
cur = con.execute(SQL)
names = [d[0] for d in cur.description]
got = {}
for row in cur.fetchall():
    r = dict(zip(names, row))
    got[(r["typology"], r["market"])] = (r["gid"], r["sent"], r["delivered"], r["unique_clients"], round(r["delivery_rate"] * 100, 1))
assert got == EXPECTED, got
print(f"3-generated.sql: {len(got)} member groups match on DuckDB {duckdb.__version__}")
