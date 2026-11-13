"""Grain checks: a join must keep exactly one row per fact row, and the key must be unique (docs: EC-L-09, EC-L-25).

The check reads the data once and states what it saw. It proves the join on today's data; it does not prove it
for tomorrow's, which is why the result keeps the counts for the audit trail.
"""
from __future__ import annotations

from .backends.base import Engine, Statement
from .errors import GrainError
from .model import SemanticModel


def check_joins(engine: Engine, source: str, key: str, joins: list[tuple[str, str, str]]) -> dict[str, int]:
    """`joins` are (table, alias, on) in Databricks SQL, `on` written with `source.` for the fact."""
    relation = f"{source} AS source" + "".join(f" LEFT JOIN {table} AS {alias} ON {on}" for table, alias, on in joins)
    fact = engine.execute(Statement(f"SELECT COUNT(*) AS n, COUNT(DISTINCT {key}) AS k FROM {source}"))[0]
    if fact["n"] != fact["k"]:
        raise GrainError("GRAIN_KEY_NOT_UNIQUE", f"{source}.{key} is not unique: {fact['n']} rows, {fact['k']} distinct keys", rows=fact["n"], keys=fact["k"])
    joined = engine.execute(Statement(f"SELECT COUNT(*) AS n, COUNT(DISTINCT source.{key}) AS k FROM {relation}"))[0]
    if not joined["n"] == joined["k"] == fact["n"]:
        raise GrainError(
            "GRAIN_JOIN_FANOUT",
            f"a join changes the grain: {fact['n']} messages become {joined['n']} rows covering {joined['k']} messages",
            fact_rows=fact["n"], joined_rows=joined["n"], distinct_keys=joined["k"],
        )
    return {"fact_rows": fact["n"], "joined_rows": joined["n"], "distinct_keys": joined["k"]}


def check_grain(engine: Engine, model: SemanticModel) -> dict[str, int]:
    from .backends.sqlparts import qualify, render

    joins = [(j.table, j.name, render(qualify(j.tree))) for j in model.joins]
    return check_joins(engine, model.source, model.key, joins)
