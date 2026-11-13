"""Replay retained synthetic-fixture results; no Databricks connection or writes."""
import hashlib
import json
import math
import platform
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
SPEC = HERE.parents[1]

def complete_rows(path):
    response = json.loads(path.read_text())
    assert response["status"]["state"] == "SUCCEEDED", response["status"]
    manifest = response["manifest"]
    assert manifest["truncated"] is False
    assert manifest["total_chunk_count"] == 1
    result = response["result"]
    assert not result.get("next_chunk_index") and not result.get("next_chunk_internal_link")
    assert len(result["data_array"]) == manifest["total_row_count"] == result["row_count"]
    columns = manifest["schema"]["columns"]
    assert len(columns) == 15
    normalized = {}
    for raw in result["data_array"]:
        assert len(raw) == len(columns)
        row = []
        for value, column in zip(raw, columns):
            kind = column["type_name"]
            if value is not None and kind in {"INT", "LONG", "BIGINT"}:
                value = int(value)
            elif value is not None and kind in {"DOUBLE", "FLOAT", "DECIMAL"}:
                value = float(value)
            row.append(value)
        key = tuple(row[:6])
        assert key not in normalized, key
        normalized[key] = tuple(row[6:])
    return response["statement_id"], normalized

connection = duckdb.connect()
fixture = SPEC / "fixtures/s4_messages.sql"
connection.execute(fixture.read_text())
assert connection.execute("SELECT COUNT(*), COUNT(DISTINCT message_id) FROM message").fetchone() == (1050, 1050)
sql = HERE.joinpath("generated-s4.sql").read_text()
local_rows = connection.execute(sql.replace("workspace.edgekpi_spec.message", "message")).fetchall()
expected = {tuple(row[:6]): tuple(row[6:]) for row in local_rows}
assert len(expected) == 56

summary = {}
for label, name in (("generated_sql", "generated-response.json"), ("native_metric_view", "native-response.json")):
    statement_id, actual = complete_rows(HERE / name)
    assert actual.keys() == expected.keys(), label
    for key, values in expected.items():
        for index, (observed, wanted) in enumerate(zip(actual[key], values)):
            if observed is None or wanted is None:
                assert observed is wanted, (label, key, index, observed, wanted)
            elif index < 5:
                assert observed == wanted, (label, key, index, observed, wanted)
            else:
                assert math.isclose(observed, float(wanted), rel_tol=1e-12, abs_tol=1e-12), (label, key, index, observed, wanted)
    summary[label] = {"statement_id": statement_id, "rows": len(actual), "integer_atoms": "exact", "ratios_tolerance": "1e-12", "truncated": False}

summary["local"] = {"python": platform.python_version(), "duckdb": duckdb.__version__, "source_grain": "1050 rows, 1050 distinct message ids"}
summary["fixture_sha256"] = hashlib.sha256(fixture.read_bytes()).hexdigest()
print(json.dumps(summary, indent=2))
