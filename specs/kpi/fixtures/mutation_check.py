"""Manual mutation check for ../14-test-strategy-and-traceability.md (TIER-MUT).
Each mutant edits mini_planner.py in a temp copy of this folder and runs the tests. A mutant must be KILLED (tests fail).
Run: uv run --with duckdb --with pytest --with edgesql python specs/kpi/fixtures/mutation_check.py
"""
import os, pathlib, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).parent
MUTANTS = [
    ("M1 drop NULLIF guard", "mini_planner.py", "NULLIF({{{denominator}}}, 0)", "{{{denominator}}}"),
    ("M2 GROUPING_ID with reversed dims", "mini_planner.py", "GROUPING_ID({dim_list}) AS gid,\n    {atom_sql}", "GROUPING_ID({', '.join(reversed(dims))}) AS gid,\n    {atom_sql}"),
    ("M3 no grand total node", "mini_planner.py", "return [tuple(dims[:k]) for k in range(len(dims), -1, -1)]", "return [tuple(dims[:k]) for k in range(len(dims), 0, -1)]"),
    ("M4 drill-across joins on dims only (no gid)", "mini_planner.py", "ON {p.name}.gid = node.gid AND ", "ON TRUE AND "),
    ("M5 drill-across uses = instead of IS NOT DISTINCT FROM", "mini_planner.py", "IS NOT DISTINCT FROM node.{d}", "= node.{d}"),
    ("M6 cap on dimensions removed", "mini_planner.py", "if len(dims) > MAX_DIMS:", "if False:"),
    ("M7 unknown atoms ignored", "mini_planner.py", "if missing:", "if False:"),
]
# DuckDB only by default: a mutant run must be fast and free. Pass --dbx to keep the Databricks variables.
ENV = dict(os.environ) if "--dbx" in sys.argv else {k: v for k, v in os.environ.items() if k not in ("DATABRICKS_CONFIG_PROFILE", "EDGEKPI_DBX_WAREHOUSE")}
killed = survived = 0
for name, fname, old, new in MUTANTS:
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(HERE, tmp + "/f", ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "mutation_check.py"))
        p = pathlib.Path(tmp, "f", fname)
        src = p.read_text()
        assert old in src, f"mutant pattern not found: {name}"
        p.write_text(src.replace(old, new, 1))
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=tmp + "/f", capture_output=True, text=True, env=ENV)
        status = "KILLED" if r.returncode != 0 else "SURVIVED"
        killed += status == "KILLED"; survived += status == "SURVIVED"
        first = next((l for l in r.stdout.splitlines() if l.startswith("FAILED")), "")
        print(f"{status:9} {name}  {first[:110]}")
print(f"killed {killed}, survived {survived}")
sys.exit(1 if survived else 0)
