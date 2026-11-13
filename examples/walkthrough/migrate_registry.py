"""Migration by inference, harder cases: joins, date parameters, optional filters, Databricks functions,
and the six KPI ids of the registry. Evidence for the briefing note; a prototype, not product code.

For every template of examples/registry/templates.sql (Databricks SQL) it
  1. parses the template and refuses shapes it cannot rewrite, with a reason;
  2. checks every join against the data: the joined rows must still be exactly one per message;
  3. infers the source, the joins, the parameters, the optional and fixed row filters, the measures
     (three spellings of a conditional count become one measure) and the expression of each KPI;
  4. writes one Databricks statement for all accepted KPIs, with every total;
  5. proves it: each legacy template is run at every grouping and under several parameter bindings,
     and every value is compared with the migrated statement.

Engines
  DuckDB (default): the Databricks SQL is transpiled with sqlglot and run in memory.
  Databricks (--databricks): the same SQL runs natively, with named parameter markers, on the warehouse
  named by DATABRICKS_CONFIG_PROFILE and EDGEKPI_DBX_WAREHOUSE. It creates or replaces three small
  synthetic tables in workspace.edgekpi_migration (override with EDGEKPI_DBX_MIGRATION_SCHEMA).

Run from the repository root, in the environment of ../../specs/kpi/fixtures/requirements-test.txt:
    python migrate_registry.py                  # check on DuckDB
    python migrate_registry.py --write          # rewrite the generated files
    python migrate_registry.py --databricks     # also run natively (needs databricks-sdk)
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time

import duckdb
import sqlglot
from sqlglot import exp

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = ROOT / "specs" / "kpi" / "validation" / "2026-11-12-migration" / "databricks-run.json"
SLOT, SENTINEL = "{{ group_by_list }}", "__group_by_list__"
FACT_KEY = "message_id"                       # in production: the grain declared for the fact
DIMS = {"typology": "D.typology", "market": "C.market"}
SETS = [("typology", "market"), ("typology",), ("market",), ()]
BINDINGS = [
    {"start_date": None, "end_date": None},
    {"start_date": "2026-01-01", "end_date": None},
    {"start_date": "2025-06-01", "end_date": "2026-03-01"},
]
DATA = [s for s in (ROOT / "examples" / "registry" / "data.sql").read_text().split(";") if re.sub(r"--.*", "", s).strip()]


def dbx(node):
    return node.sql(dialect="databricks")


class DuckDB:
    name = "duckdb"

    def __init__(self):
        self.con = duckdb.connect()
        for statement in DATA:
            self.con.execute(statement)

    def run(self, sql, binding=None):
        local = sqlglot.transpile(sql, read="databricks", write="duckdb")[0]
        cursor = self.con.execute(local, {k: v for k, v in (binding or {}).items() if f"${k}" in local})
        names = [d[0] for d in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


class Databricks:
    name = "databricks"

    def __init__(self):
        from databricks.sdk import WorkspaceClient

        self.client = WorkspaceClient(profile=os.environ["DATABRICKS_CONFIG_PROFILE"])
        self.warehouse = os.environ["EDGEKPI_DBX_WAREHOUSE"]
        self.catalog = "workspace"
        self.schema = os.environ.get("EDGEKPI_DBX_MIGRATION_SCHEMA", "edgekpi_migration")
        self.statements = 0
        self.last_id = None
        self.run(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema}", in_schema=False)
        for statement in DATA:
            self.run(statement)

    def run(self, sql, binding=None, in_schema=True):
        from databricks.sdk.service.sql import StatementParameterListItem, StatementState

        parameters = [StatementParameterListItem(name=k, value=v, type="STRING") for k, v in (binding or {}).items() if f":{k}" in sql]
        response = self.client.statement_execution.execute_statement(
            statement=sql, warehouse_id=self.warehouse, catalog=self.catalog,
            schema=self.schema if in_schema else None, parameters=parameters or None, wait_timeout="30s",
        )
        started = time.time()
        while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.time() - started > 600:
                raise RuntimeError(f"timeout: {sql[:80]}")
            time.sleep(1)
            response = self.client.statement_execution.get_statement(response.statement_id)
        if response.status.state != StatementState.SUCCEEDED:
            raise RuntimeError(f"{response.status.error.error_code}: {response.status.error.message}\n{sql}")
        self.statements += 1
        self.last_id = response.statement_id
        if response.manifest is None or response.result is None or response.result.data_array is None:
            return []
        assert not response.manifest.truncated and (response.manifest.total_chunk_count or 1) == 1, "incomplete result"
        columns = [(c.name, str(getattr(c.type_name, "value", c.type_name))) for c in response.manifest.schema.columns]
        out = []
        for row in response.result.data_array:
            record = {}
            for (name, kind), value in zip(columns, row):
                if value is not None and kind in ("BYTE", "SHORT", "INT", "LONG"):
                    value = int(value)
                elif value is not None and kind in ("FLOAT", "DOUBLE", "DECIMAL"):
                    value = float(value)
                record[name] = value
            out.append(record)
        return out


def read_templates():
    text = (ROOT / "examples" / "registry" / "templates.sql").read_text()
    found = re.findall(r"-- kpi: (\S+) \| (\w+)\n(.*?;)", text, flags=re.S)
    return {kpi_id: (alias, body.strip().rstrip(";")) for kpi_id, alias, body in found}


def conjuncts(node):
    if node is None:
        return []
    if isinstance(node, exp.And):
        return conjuncts(node.this) + conjuncts(node.expression)
    return [] if node.sql() == "1 = 1" else [node]


def classify_filter(node):
    """Optional filter (`:p IS NULL OR ...`), required parameter filter, or fixed row filter."""
    inner = node.this if isinstance(node, exp.Paren) else node
    parameters = sorted({p.name for p in node.find_all(exp.Placeholder)})
    if (isinstance(inner, exp.Or) and isinstance(inner.this, exp.Is) and isinstance(inner.this.expression, exp.Null)
            and len(parameters) == 1 and list(inner.this.this.find_all(exp.Placeholder))):
        return {"kind": "optional", "parameter": parameters[0], "applies": dbx(inner.expression)}
    if parameters:
        return {"kind": "required", "parameters": parameters, "applies": dbx(node)}
    return {"kind": "fixed", "applies": dbx(node)}


def one_spelling(expr):
    """COUNT_IF(p) and SUM(CASE WHEN p THEN 1 ELSE 0 END) count the rows where p holds, as does
    COUNT(*) FILTER (WHERE p). They agree on every non-empty group, which is all the statement returns."""
    def visit(node):
        predicate = None
        if isinstance(node, exp.CountIf):
            predicate = node.this
        elif isinstance(node, exp.Sum) and isinstance(node.this, exp.Case) and not node.this.this:
            ifs, default = node.this.args.get("ifs") or [], node.this.args.get("default")
            if len(ifs) == 1 and ifs[0].args["true"].sql() == "1" and default is not None and default.sql() == "0":
                predicate = ifs[0].this
        if predicate is None:
            return node
        return exp.Filter(this=exp.Count(this=exp.Star()), expression=exp.Where(this=predicate.copy()))
    return expr.copy().transform(visit)


def with_row_filter(expr, predicate):
    def visit(node):
        if isinstance(node, exp.Filter):
            node.set("expression", exp.Where(this=exp.and_(node.expression.this, predicate.copy())))
            return node
        if isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Filter):
            return exp.Filter(this=node, expression=exp.Where(this=predicate.copy()))
        return node
    return expr.copy().transform(visit)


def check_grain(engine, source, joins):
    """A join is accepted only if the joined relation still has exactly one row per fact row."""
    relation = dbx(source) + "".join(" " + dbx(j) for j in joins)
    joined = engine.run(f"SELECT COUNT(*) AS n, COUNT(DISTINCT {source.alias_or_name}.{FACT_KEY}) AS k FROM {relation}")[0]
    fact_rows = engine.run(f"SELECT COUNT(*) AS n FROM {source.name}")[0]["n"]
    if not joined["n"] == joined["k"] == fact_rows:
        raise ValueError(f"a join changes the grain: {fact_rows} messages become {joined['n']} rows covering {joined['k']} messages")
    return {"fact_rows": fact_rows, "joined_rows": joined["n"], "distinct_keys": joined["k"]}


def decompose(engine, template):
    tree = sqlglot.parse_one(template.replace(SLOT, SENTINEL), dialect="databricks")
    if list(tree.find_all(exp.Subquery)):
        raise ValueError("more than one aggregation")
    for clause in ("having", "limit", "distinct", "qualify"):
        if tree.args.get(clause):
            raise ValueError(f"{clause.upper()} is not supported")
    if list(tree.find_all(exp.Window)):
        raise ValueError("window function")
    if [g.sql() for g in tree.args["group"].expressions] != [SENTINEL]:
        raise ValueError("GROUP BY is not exactly the grouping slot")
    slot, kpi = tree.expressions
    if slot.sql() != SENTINEL or kpi.alias != "kpi_value" or not list(kpi.find_all(exp.AggFunc)):
        raise ValueError("SELECT is not the slot plus one aggregate expression")
    source, joins = tree.args["from_"].this, tree.args.get("joins") or []
    where = tree.args.get("where")
    seen = {type(n).__name__ for n in tree.walk()}
    return {
        "source": source, "joins": joins, "grain": check_grain(engine, source, joins),
        "filters": conjuncts(where.this if where else None),
        "expression": one_spelling(kpi.this),
        "constructs": sorted(seen & {"TryCast", "SafeDivide", "CountIf", "Filter", "Placeholder", "Case", "Nullif", "Distinct"}),
    }


def migrate(engine, templates):
    parts, refused = {}, {}
    for kpi_id, (alias, template) in templates.items():
        try:
            parts[kpi_id] = dict(decompose(engine, template), alias=alias)
        except ValueError as error:
            refused[kpi_id] = str(error)

    relation = lambda p: dbx(p["source"]) + "".join("\n  " + dbx(j) for j in p["joins"])  # noqa: E731
    relations = {relation(p) for p in parts.values()}
    assert len(relations) == 1, f"KPIs over different sources need one statement each: {relations}"
    first = next(iter(parts.values()))
    shared_text = set.intersection(*[{dbx(f) for f in p["filters"]} for p in parts.values()])
    shared = [f for f in first["filters"] if dbx(f) in shared_text]

    measures, kpis = {}, {}
    for kpi_id, p in parts.items():
        expr, own = p["expression"], [f for f in p["filters"] if dbx(f) not in shared_text]
        for predicate in own:
            expr = with_row_filter(expr, predicate)

        def name_measure(node, kpi_id=kpi_id):
            top = isinstance(node, exp.Filter) or (isinstance(node, exp.AggFunc) and not isinstance(node.parent, exp.Filter))
            if not top:
                return node
            entry = measures.setdefault(dbx(node), {"name": f"m{len(measures) + 1}", "used_by": []})
            if kpi_id not in entry["used_by"]:
                entry["used_by"].append(kpi_id)
            return exp.column(entry["name"])
        kpis[kpi_id] = {"alias": p["alias"], "expression": dbx(expr.transform(name_measure)),
                        "own_row_filters": [dbx(f) for f in own]}

    sets = ", ".join("(" + ", ".join(DIMS[d] for d in s) + ")" for s in SETS)
    sql = (
        "WITH agg AS (\n  SELECT "
        + ", ".join(f"{expr} AS {name}" for name, expr in DIMS.items())
        + f",\n    GROUPING_ID({', '.join(DIMS.values())}) AS gid,\n    "
        + ",\n    ".join(f"{aggregate} AS {m['name']}" for aggregate, m in measures.items())
        + f"\n  FROM {relations.pop()}\n  WHERE "
        + ("\n    AND ".join(dbx(f) for f in shared) or "TRUE")
        + f"\n  GROUP BY GROUPING SETS ({sets})\n  HAVING COUNT(*) > 0\n)\n"
        + f"SELECT {', '.join(DIMS)}, gid,\n  "
        + ",\n  ".join(f"{k['expression']} AS {k['alias']}" for k in kpis.values())
        + "\nFROM agg\n"
    )
    inferred = {
        "source": {"fact": dbx(first["source"]), "key": f"{first['source'].alias_or_name}.{FACT_KEY}",
                   "joins": [{"join": dbx(j), "grain": "one row per message kept", **first["grain"]} for j in first["joins"]]},
        "parameters": sorted({p.name for f in shared for p in f.find_all(exp.Placeholder)}),
        "shared_row_filters": [classify_filter(f) for f in shared],
        "measures": {m["name"]: {"expression": aggregate, "used_by": m["used_by"]} for aggregate, m in measures.items()},
        "kpis": kpis,
        "refused": refused,
        "databricks_constructs_read": sorted({c for p in parts.values() for c in p["constructs"]}),
    }
    return sql, inferred


def legacy_sql(template, group):
    """The registry's way: paste a column list into the text. The grand total has no valid form with the
    slot, so that reference is obtained by removing the slot and the GROUP BY from the parsed tree."""
    if group:
        return template.replace(SLOT, ", ".join(DIMS[g] for g in group))
    tree = sqlglot.parse_one(template.replace(SLOT, SENTINEL), dialect="databricks")
    tree.set("group", None)
    tree.set("expressions", [tree.expressions[1]])
    return dbx(tree)


def same(a, b):
    return (a is None and b is None) or (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-12)


def prove(engine, templates, sql, inferred):
    """Run the legacy templates and the migrated statement on one engine and compare every value."""
    result = {"bindings": len(BINDINGS), "groups": 0, "compared": 0, "nulls": 0, "different": 0, "only_after": [], "migrated_ids": []}
    for index, binding in enumerate(BINDINGS):
        migrated = {(r["typology"], r["market"], r["gid"]): r for r in engine.run(sql, binding)}
        result["migrated_ids"].append(getattr(engine, "last_id", None))
        result["groups"] += len(migrated)
        for kpi_id, kpi in inferred["kpis"].items():
            for group in SETS:
                gid = sum(1 << (len(DIMS) - 1 - i) for i, d in enumerate(DIMS) if d not in group)
                seen = set()
                for r in engine.run(legacy_sql(templates[kpi_id][1], group), binding):
                    key = (r.get("typology"), r.get("market"), gid)
                    seen.add(key)
                    result["compared"] += 1
                    result["nulls"] += r["kpi_value"] is None
                    result["different"] += not same(migrated[key][kpi["alias"]], r["kpi_value"])
                result["only_after"] += [(index, kpi["alias"], migrated[key][kpi["alias"]]) for key in migrated if key[2] == gid and key not in seen]
    return result


def main():
    templates = read_templates()
    engines = [DuckDB()] + ([Databricks()] if "--databricks" in sys.argv else [])
    outputs = None
    for engine in engines:
        sql, inferred = migrate(engine, templates)
        reparsed = dbx(sqlglot.parse_one(sql, dialect="databricks"))
        assert dbx(sqlglot.parse_one(reparsed, dialect="databricks")) == reparsed, "Databricks text does not round-trip"
        produced = {"5-migrated-databricks.sql": sql, "5-inferred.json": json.dumps(inferred, indent=2) + "\n"}
        assert outputs is None or outputs == produced, "the two engines led to different inferences"
        outputs = produced
        for name, content in produced.items():
            if "--write" in sys.argv and engine.name == "duckdb":
                (HERE / name).write_text(content)
            assert (HERE / name).read_text() == content, f"{name} is not what the migration produces"

        proof = prove(engine, templates, sql, inferred)
        if engine.name == "duckdb":
            print("accepted  :", {k: v["expression"] for k, v in inferred["kpis"].items()})
            print("measures  :", {k: v["expression"] for k, v in inferred["measures"].items()})
            print("refused   :", inferred["refused"])
            print("filters   :", [(f["kind"], f.get("parameter")) for f in inferred["shared_row_filters"]], "| parameters", inferred["parameters"])
            print("joins     :", inferred["source"]["joins"])
            print("constructs:", inferred["databricks_constructs_read"])
        print(f"{engine.name:10}: {proof['bindings']} parameter bindings, {proof['groups']} groups, {proof['compared']} legacy values "
              f"compared ({proof['nulls']} NULL for a zero denominator), {proof['different']} different; "
              f"{len(proof['only_after'])} values exist only after migration, for {sorted({p[1] for p in proof['only_after']})} = {sorted({p[2] for p in proof['only_after']})}")

        assert len(inferred["kpis"]) == 6 and len(inferred["measures"]) == 5
        assert sorted(inferred["refused"]) == ["messages-per-client", "open-events"]
        assert [f["kind"] for f in inferred["shared_row_filters"]] == ["optional", "optional"] and inferred["parameters"] == ["end_date", "start_date"]
        assert (proof["bindings"], proof["groups"], proof["compared"], proof["nulls"], proof["different"]) == (3, 34, 200, 18, 0)
        assert {p[1] for p in proof["only_after"]} == {"reached"} and {p[2] for p in proof["only_after"]} == {0} and len(proof["only_after"]) == 4

        if engine.name == "databricks":
            warehouse = engine.client.warehouses.get(engine.warehouse)
            record = {
                "date": datetime.date.today().isoformat(),
                "warehouse": {"name": warehouse.name, "size": warehouse.cluster_size},     # no host, user or id: the record is published
                "schema": f"{engine.catalog}.{engine.schema}",
                "tables_created_or_replaced": ["client", "message", "message_event"],
                "statements_executed": engine.statements,
                "parameter_bindings": BINDINGS,
                "parity": {k: proof[k] for k in ("bindings", "groups", "compared", "nulls", "different")},
                "values_only_after_migration": len(proof["only_after"]),
                "same_inference_as_duckdb": True,
                "databricks_constructs_executed_natively": inferred["databricks_constructs_read"],
            }
            EVIDENCE.write_text(json.dumps(record, indent=2) + "\n")
            print(f"evidence  : {EVIDENCE.relative_to(ROOT)} ({engine.statements} statements)")
    print("OK")


main()
