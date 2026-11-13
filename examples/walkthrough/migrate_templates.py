"""Migration by rewriting: legacy KPI templates -> syntax tree -> measures and formulas -> one statement
with totals. Evidence for the migration section of the briefing note; a prototype, not product code.

What it does
  1. Parse each template of 4-legacy-templates.sql and keep only the supported shape:
     one aggregation over one source, grouped by the grouping slot alone.
  2. Decompose it into a source, row filters, aggregates (measures) and the expression applied after
     aggregation (formula). An aggregate used by several KPIs becomes one shared measure.
  3. Rewrite: the grouping slot becomes grouping sets; a row filter that not every KPI shares moves into
     the aggregates that need it.
  4. Prove: run every template the legacy way, at every grouping, and compare each value.

Run from the repository root, in the environment of ../../specs/kpi/fixtures/requirements-test.txt:
    python migrate_templates.py            # check
    python migrate_templates.py --write    # rewrite 4-migrated.sql
"""
import pathlib
import re
import sys

import duckdb
import sqlglot
from sqlglot import exp

HERE = pathlib.Path(__file__).resolve().parent
SLOT, SENTINEL = "{{ group_by_list }}", "__group_by_list__"
DIMS = ["typology", "market"]
SETS = [("typology", "market"), ("typology",), ("market",), ()]


def read_templates():
    text = (HERE / "4-legacy-templates.sql").read_text()
    return {name: body.strip().rstrip(";") for name, body in re.findall(r"-- kpi: (\w+)\n(.*?;)", text, flags=re.S)}


def conjuncts(node):
    """Row filters of a WHERE clause, without the registry's `1 = 1` padding."""
    if node is None:
        return []
    if isinstance(node, exp.And):
        return conjuncts(node.this) + conjuncts(node.expression)
    return [] if node.sql() == "1 = 1" else [node]


def decompose(name, template):
    """Template -> (source, row filters, expression over aggregates). Any other shape is refused."""
    tree = sqlglot.parse_one(template.replace(SLOT, SENTINEL), dialect="databricks")
    if list(tree.find_all(exp.Subquery)) or tree.args.get("joins"):
        raise ValueError(f"{name}: more than one aggregation or source")
    for clause in ("having", "limit", "distinct", "qualify"):
        if tree.args.get(clause):
            raise ValueError(f"{name}: {clause.upper()} is not supported")
    if list(tree.find_all(exp.Window)):
        raise ValueError(f"{name}: window function")
    if [g.sql() for g in tree.args["group"].expressions] != [SENTINEL]:
        raise ValueError(f"{name}: GROUP BY is not exactly the grouping slot")
    slot, kpi = tree.expressions
    if slot.sql() != SENTINEL or kpi.alias != "kpi_value" or not list(kpi.find_all(exp.AggFunc)):
        raise ValueError(f"{name}: SELECT is not the slot plus one aggregate expression")
    where = tree.args.get("where")
    return tree.args["from_"].this, conjuncts(where.this if where else None), kpi.this


def with_row_filter(expr, predicate):
    """Move a row filter into every aggregate, so KPIs with different WHERE clauses can share one pass."""
    def visit(node):
        if isinstance(node, exp.Filter):
            node.set("expression", exp.Where(this=exp.and_(node.expression.this, predicate.copy())))
            return node
        if isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Filter):
            return exp.Filter(this=node, expression=exp.Where(this=predicate.copy()))
        return node
    return expr.copy().transform(visit)


def migrate(templates):
    parts, refused = {}, {}
    for name, template in templates.items():
        try:
            parts[name] = decompose(name, template)
        except ValueError as error:
            refused[name] = str(error).split(": ", 1)[1]
    sources = {source.sql(dialect="duckdb") for source, _, _ in parts.values()}
    assert len(sources) == 1, f"different sources cannot be fused: {sources}"
    shared = set.intersection(*[{p.sql() for p in filters} for _, filters, _ in parts.values()])

    measures, formulas = {}, {}                      # aggregate SQL -> measure name; KPI -> formula SQL
    for name, (_, filters, expr) in parts.items():
        for predicate in filters:
            if predicate.sql() not in shared:
                expr = with_row_filter(expr, predicate)

        def name_measure(node):
            top = isinstance(node, exp.Filter) or (isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Filter))
            if not top:
                return node
            key = node.sql(dialect="duckdb")
            return exp.column(measures.setdefault(key, f"m{len(measures) + 1}"))
        formulas[name] = expr.transform(name_measure).sql(dialect="duckdb")

    dims = ", ".join(DIMS)
    sets = ", ".join("(" + ", ".join(s) + ")" for s in SETS)
    sql = (
        "WITH agg AS (\n"
        f"  SELECT {dims},\n    GROUPING_ID({dims}) AS gid,\n    "
        + ",\n    ".join(f"{aggregate} AS {measure}" for aggregate, measure in measures.items())
        + f"\n  FROM {sources.pop()}\n  WHERE {' AND '.join(sorted(shared)) or 'TRUE'}\n"
        f"  GROUP BY GROUPING SETS ({sets})\n  HAVING COUNT(*) > 0\n)\n"
        f"SELECT {dims}, gid,\n  "
        + ",\n  ".join(f"{formula} AS {name}" for name, formula in formulas.items())
        + "\nFROM agg\n"
    )
    return sql, measures, formulas, refused


def legacy_sql(template, group):
    """The registry's way: paste a column list into the text. An empty list has no valid form, so the
    grand total is obtained here by removing the slot and the GROUP BY from the tree."""
    if group:
        return sqlglot.transpile(template.replace(SLOT, ", ".join(f"C.{g}" for g in group)), read="databricks", write="duckdb")[0]
    tree = sqlglot.parse_one(template.replace(SLOT, SENTINEL), dialect="databricks")
    tree.set("group", None)
    tree.set("expressions", [tree.expressions[1]])
    return tree.sql(dialect="duckdb")


def rows(connection, sql):
    cursor = connection.execute(sql)
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


templates = read_templates()
sql, measures, formulas, refused = migrate(templates)
target = HERE / "4-migrated.sql"
if "--write" in sys.argv:
    target.write_text(sql)
assert target.read_text() == sql, "4-migrated.sql is not what the rewrite produces"

con = duckdb.connect()
con.execute((HERE / "message.sql").read_text())
# A ninth message, sent and not delivered, in a market of its own: it shows the empty-group question.
con.execute("INSERT INTO message VALUES (9, 'c6', 'VIP', 'JP', FALSE, FALSE, FALSE)")
migrated = {(r["typology"], r["market"], r["gid"]): r for r in rows(con, sql)}

compared = different = 0
only_migrated = []
for name in formulas:
    for group in SETS:
        gid = sum(1 << (len(DIMS) - 1 - i) for i, d in enumerate(DIMS) if d not in group)
        seen = set()
        for r in rows(con, legacy_sql(templates[name], group)):
            key = (r.get("typology"), r.get("market"), gid)
            seen.add(key)
            compared += 1
            different += abs(float(migrated[key][name]) - float(r["kpi_value"])) > 1e-12
        only_migrated += [(name, key, migrated[key][name]) for key in migrated if key[2] == gid and key not in seen]

print("measures :", {v: k for k, v in measures.items()})
print("formulas :", formulas)
print("refused  :", refused)
print(f"parity   : {len(migrated)} groups, {compared} legacy values compared, {different} different")
for name, key, value in only_migrated:
    print(f"presence : {name} {key} is {value} after migration; the legacy query returns no row")

assert sorted(formulas) == ["delivery_rate", "reached_clients", "sent"] and list(refused) == ["messages_per_client"]
assert len(measures) == 3 and (len(migrated), compared, different) == (11, 31, 0)
assert {key for _, key, _ in only_migrated} == {("VIP", "JP", 0), (None, "JP", 2)}
print("OK")
