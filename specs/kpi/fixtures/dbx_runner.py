"""Databricks adapter for the TIER-DBX tests (../14-test-strategy-and-traceability.md).
Runs ONE statement at a time through the SQL Statement Execution API and returns typed rows.

Opt in with two environment variables (nothing else is read):
  DATABRICKS_CONFIG_PROFILE   profile in ~/.databrickscfg
  EDGEKPI_DBX_WAREHOUSE       SQL warehouse id
Objects are created only in  workspace.edgekpi_spec  (override with EDGEKPI_DBX_CATALOG / EDGEKPI_DBX_SCHEMA).
"""
from __future__ import annotations

import os
import time
from decimal import Decimal

CATALOG = os.environ.get("EDGEKPI_DBX_CATALOG", "workspace")
SCHEMA = os.environ.get("EDGEKPI_DBX_SCHEMA", "edgekpi_spec")
_INT = {"BYTE", "SHORT", "INT", "LONG"}
_FLOAT = {"FLOAT", "DOUBLE", "DECIMAL"}


def enabled() -> bool:
    return bool(os.environ.get("DATABRICKS_CONFIG_PROFILE") and os.environ.get("EDGEKPI_DBX_WAREHOUSE"))


class DatabricksError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


class Dbx:
    def __init__(self):
        from databricks.sdk import WorkspaceClient

        self.w = WorkspaceClient(profile=os.environ["DATABRICKS_CONFIG_PROFILE"])
        self.wh = os.environ["EDGEKPI_DBX_WAREHOUSE"]
        self.statements = 0

    def run(self, sql: str, timeout_s: int = 600) -> list[dict]:
        from databricks.sdk.service.sql import StatementState

        self.statements += 1
        r = self.w.statement_execution.execute_statement(
            statement=sql, warehouse_id=self.wh, catalog=CATALOG, schema=SCHEMA, wait_timeout="30s"
        )
        t0 = time.time()
        while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.time() - t0 > timeout_s:
                self.w.statement_execution.cancel_execution(r.statement_id)
                raise DatabricksError("TIMEOUT", sql[:80])
            time.sleep(1)
            r = self.w.statement_execution.get_statement(r.statement_id)
        if r.status.state != StatementState.SUCCEEDED:
            err = r.status.error
            raise DatabricksError(str(getattr(err, "error_code", "ERROR")), str(getattr(err, "message", "")))
        if r.manifest is None or r.result is None or r.result.data_array is None:
            return []
        cols = [(c.name, str(c.type_name.value if hasattr(c.type_name, "value") else c.type_name)) for c in r.manifest.schema.columns]
        rows = r.result.data_array
        out = []
        for row in rows:
            d = {}
            for (name, typ), v in zip(cols, row):
                if v is None:
                    d[name] = None
                elif typ in _INT:
                    d[name] = int(v)
                elif typ in _FLOAT:
                    d[name] = float(Decimal(v))
                elif typ == "BOOLEAN":
                    d[name] = v == "true"
                else:
                    d[name] = v
            out.append(d)
        return out

    def script(self, text: str) -> None:
        """Run a ';'-separated script of simple statements (no ';' inside literals)."""
        for stmt in [s.strip() for s in text.split(";")]:
            if stmt and not all(line.strip().startswith("--") or not line.strip() for line in stmt.splitlines()):
                self.run(stmt)
