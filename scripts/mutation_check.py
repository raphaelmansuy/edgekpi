"""Mutation check: does the suite notice when a rule is broken? Each mutant changes one line of a COPY of the library
and the local tests must fail. A surviving mutant means a rule has no test.

    python scripts/mutation_check.py
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

MUTANTS = [
    ([("expr.py", "expression=exp.Literal.number(0))", "expression=exp.Literal.number(1))")], "zero denominator no longer guarded (EC-L-02/23)"),
    ([("scopes.py", "1 << (len(dims) - 1 - i)", "1 << i")], "GROUPING_ID bit order reversed (EC-L-03)"),
    ([("reconcile.py", "return abs(float(a) - float(b)) <= REL_TOL", "return True or abs(float(a) - float(b)) <= REL_TOL")], "reconciliation compares nothing (EC-L-15)"),
    ([("request.py", "not _DATE.match(text)", "False")], "dates are not checked before they travel (EC-L-08)"),
    ([("backends/sqlparts.py", 'text = f"{render(_typed(first.type, first.name))} IS NULL OR {text}"', "pass")], "optional filters become required (EC-L-08)"),
    ([("backends/sql.py", "HAVING COUNT(*) > 0", "HAVING COUNT(*) >= 0"), ("backends/base.py", "if ROW_COUNT in row and not row[ROW_COUNT]:", "if False:")],
     "empty input yields a zero node: both defences removed (EC-L-01)"),
    ([("grain.py", 'if fact["n"] != fact["k"]:', "if False:")], "duplicate keys accepted (EC-L-25)"),
    ([("grain.py", 'if not joined["n"] == joined["k"] == fact["n"]:', "if False:")], "join fan-out accepted (EC-L-09)"),
    ([("inference.py", "predicate = node.this\n        elif isinstance(node, exp.Sum)", "predicate = None\n        elif isinstance(node, exp.Sum)")], "COUNT_IF spelling not unified (EC-L-18)"),
    ([("scopes.py", "return [tuple(dims[:k]) for k in range(len(dims), -1, -1)]", "return [tuple(dims)]")], "totals dropped (EC-L-19)"),
    ([("request.py", 'if request.published and kpi.status != "confirmed":', "if False:")], "unconfirmed KPI published (EC-L-16)"),
    ([("model.py", 'if join.cardinality != "one":', "if False:")], "to-many join declared (EC-L-09)"),
    ([("runner.py", "if engine.name not in backend.engines:", "if False:")], "backend runs on the wrong engine (EC-L-11)"),
    ([("backends/malloy.py", 'return f"{t(node.this)} and {t(node.expression)}"', 'return f"{t(node.this)} or {t(node.expression)}"')], "AND translated as OR in Malloy (EC-L-07)"),
    ([("backends/malloy.py", 'return "\'" + str(value).replace("\\\\", "\\\\\\\\")', 'return "\'" + str(value).replace("\\\\", "\\\\")')], "Malloy literal does not escape backslashes (EC-L-07)"),
    ([("intent.py", "cutoff=0.8", "cutoff=0.3")], "the assistant guesses on weak matches (EC-L-28)"),
    ([("explain.py", 'if best is None or (found["differs"] and not best["differs"]):', "if best is None:")], "the explanation picks a split where the tempting answer is right (EC-D-11)"),
    ([("server.py", "if length > MAX_BODY:", "if False:")], "an oversized body is read (EC-D-22)"),
    ([("service.py", "(UnsupportedError, 501), (EngineError, 502), ", "")], "an unavailable backend is reported as a client error (EC-D-06)"),
]


def main() -> int:
    survived, skipped = [], 0
    for index, (changes, why) in enumerate(MUTANTS, 1):
        with tempfile.TemporaryDirectory() as tmp:
            work = pathlib.Path(tmp)
            shutil.copytree(ROOT / "edgekpi", work / "edgekpi", ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
            os.symlink(ROOT / "examples", work / "examples")
            os.symlink(ROOT / "specs", work / "specs")
            missing = False
            for path, old, new in changes:
                target = work / "edgekpi" / path
                text = target.read_text()
                if old not in text:
                    missing = True
                    print(f"{index:2} SKIP     {path}: pattern not found ({why})")
                    break
                target.write_text(text.replace(old, new, 1))
            if missing:
                skipped += 1
                continue
            env = {**os.environ, "PYTHONPATH": str(work), "PYTHONDONTWRITEBYTECODE": "1"}
            env.pop("EDGEKPI_DBX_WAREHOUSE", None)
            try:
                done = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-x", "-m", "not databricks and not malloy"],
                                      cwd=work, env=env, capture_output=True, text=True, timeout=180)
                killed = done.returncode != 0
            except subprocess.TimeoutExpired:
                killed = True                                   # a mutant that makes the suite hang is noticed, not survived
            print(f"{index:2} {'killed  ' if killed else 'SURVIVED'} {changes[0][0]}: {why}")
            if not killed:
                survived.append(why)
    total = len(MUTANTS) - skipped
    print(f"{total - len(survived)}/{total} mutants killed")
    return 1 if survived or skipped else 0


if __name__ == "__main__":
    sys.exit(main())
