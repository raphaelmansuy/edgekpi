"""SQL fragments shared by the generated-SQL and metric-view backends (DRY: one rendering of joins, filters, sets)."""
from __future__ import annotations

from typing import Callable

from sqlglot import exp

from .. import expr
from ..model import PARAM_TYPES, SemanticModel
from ..request import Report
from ..scopes import Scope

ColumnMap = Callable[[exp.Column], exp.Expression]


def qualify(tree: exp.Expression) -> exp.Expression:
    """Bare columns belong to the fact: write them as source.<column>."""
    def visit(node):
        if isinstance(node, exp.Column) and not node.table:
            return exp.column(node.name, table=expr.FACT)
        return node
    return tree.transform(visit)


def render(tree: exp.Expression) -> str:
    return tree.sql(dialect=expr.DIALECT)


def dimension_sql(model: SemanticModel) -> dict[str, str]:
    """Every dimension of the model as a SQL expression over the fact and its joins."""
    return {d.name: render(qualify(d.tree)) for d in model.dimensions}


def qualified_column(column: exp.Column) -> exp.Expression:
    return qualify(column)


def relation(model: SemanticModel) -> str:
    parts = [f"{model.source} AS {expr.FACT}"]
    parts += [f"LEFT JOIN {j.table} AS {j.name} ON {render(qualify(j.tree))}" for j in model.joins]
    return "\n  ".join(parts)


def _typed(param_type: str, name: str) -> exp.Expression:
    return exp.Cast(this=exp.Placeholder(this=name), to=exp.DataType.build(PARAM_TYPES[param_type]))


def predicate_sql(report: Report, column_map: ColumnMap, dimension_ref: Callable[[str], str]) -> list[str]:
    """Every row filter of the model plus the request's `where`, each as one parenthesised conjunct.
    Parameters stay as named markers, so the statement text does not change with the bound values."""
    out = []
    types = report.model.params
    for active in report.filters:
        flt = active.filter
        tree = flt.tree.transform(lambda n: _typed(types[n.name].type, n.name) if isinstance(n, exp.Placeholder) else n)
        tree = tree.transform(lambda n: column_map(n) if isinstance(n, exp.Column) else n)
        text = render(tree)
        if flt.optional:
            first = flt.params[0]
            text = f"{render(_typed(first.type, first.name))} IS NULL OR {text}"
        out.append(f"({text})")
    for w, bindings in report.where:
        markers = ", ".join(f":{b.name}" for b in bindings)
        out.append(f"({dimension_ref(w.dimension)} = :{bindings[0].name})" if w.op == "eq" else f"({dimension_ref(w.dimension)} IN ({markers}))")
    return out


def sets_sql(scopes: tuple[Scope, ...], ref: Callable[[str], str]) -> str:
    return ", ".join("(" + ", ".join(ref(d) for d in scope) + ")" for scope in scopes)
