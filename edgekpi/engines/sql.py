"""Engines that run SQL: DuckDB (local oracle and test engine) and Databricks SQL warehouses."""
from __future__ import annotations

import os
import time
from typing import Any

import sqlglot

from ..backends.base import Statement
from ..errors import EngineError, UnsupportedError


def split_script(script: str) -> list[str]:
    """Statements of a SQL script, comments and empty parts dropped."""
    return [part for part in script.split(";") if "".join(line.split("--")[0] for line in part.splitlines()).strip()]


class DuckDBEngine:
    """Runs generated SQL locally. Databricks-dialect text is transpiled with sqlglot (one dialect to author)."""

    name = "duckdb"

    def __init__(self, connection=None):
        import duckdb

        self.con = connection or duckdb.connect()
        self.statements = 0

    def load(self, script: str) -> None:
        for part in split_script(script):
            self.con.execute(part)

    def execute(self, statement: Statement) -> list[dict[str, Any]]:
        if statement.language != "sql":
            raise UnsupportedError("ENGINE_LANGUAGE", f"duckdb runs SQL, not {statement.language}")
        try:
            local = sqlglot.transpile(statement.text, read="databricks", write="duckdb")[0]
            bound = {b.name: b.value for b in statement.params if f"${b.name}" in local}
            cursor = self.con.execute(local, bound)
            names = [d[0] for d in cursor.description or []]
            self.statements += 1
            return [dict(zip(names, row)) for row in cursor.fetchall()]
        except Exception as error:  # duckdb raises several unrelated types
            raise EngineError("ENGINE_FAILED", f"duckdb: {str(error).splitlines()[0]}") from error


class DatabricksEngine:
    """Runs statements on a SQL warehouse through the Statement Execution API. Named markers are bound natively."""

    name = "databricks"

    def __init__(self, warehouse_id: str | None = None, profile: str | None = None, catalog: str = "workspace", schema: str = "edgekpi_lib"):
        from databricks.sdk import WorkspaceClient

        self.client = WorkspaceClient(profile=profile or os.environ.get("DATABRICKS_CONFIG_PROFILE"))
        self.warehouse = warehouse_id or os.environ["EDGEKPI_DBX_WAREHOUSE"]
        self.catalog, self.schema = catalog, schema
        self.statements = 0
        self.statement_ids: list[str] = []

    def load(self, script: str) -> None:
        """Create the schema and load a data script (CREATE OR REPLACE TABLE ...) into it."""
        self.execute(Statement(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema}"))
        for part in split_script(script):
            self.execute(Statement(part))

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value).lower() if isinstance(value, bool) else str(value)

    def execute(self, statement: Statement) -> list[dict[str, Any]]:
        from databricks.sdk.service.sql import StatementParameterListItem, StatementState

        if statement.language != "sql":
            raise UnsupportedError("ENGINE_LANGUAGE", f"databricks runs SQL, not {statement.language}")
        parameters = [
            StatementParameterListItem(name=b.name, value=self._text(b.value), type=b.type)
            for b in statement.params if f":{b.name}" in statement.text
        ]
        response = self.client.statement_execution.execute_statement(
            statement=statement.text, warehouse_id=self.warehouse, catalog=self.catalog, schema=self.schema,
            parameters=parameters or None, wait_timeout="30s",
        )
        started = time.time()
        while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.time() - started > 600:
                raise EngineError("ENGINE_TIMEOUT", f"databricks statement still running after 600 s: {statement.text[:80]}")
            time.sleep(1)
            response = self.client.statement_execution.get_statement(response.statement_id)
        if response.status.state != StatementState.SUCCEEDED:
            error = response.status.error
            raise EngineError("ENGINE_FAILED", f"databricks {error.error_code}: {error.message}")
        self.statements += 1
        self.statement_ids.append(response.statement_id)
        if response.manifest is None or response.result is None or response.result.data_array is None:
            return []
        if response.manifest.truncated or (response.manifest.total_chunk_count or 1) != 1:
            raise EngineError("ENGINE_INCOMPLETE_RESULT", "the result is truncated or chunked; refusing a partial grid")
        columns = [(c.name, str(getattr(c.type_name, "value", c.type_name))) for c in response.manifest.schema.columns]
        out = []
        for row in response.result.data_array:
            record = {}
            for (name, kind), value in zip(columns, row):
                if value is not None and kind in ("BYTE", "SHORT", "INT", "LONG"):
                    value = int(value)
                elif value is not None and kind in ("FLOAT", "DOUBLE", "DECIMAL"):
                    value = float(value)
                elif value is not None and kind == "BOOLEAN":
                    value = value in (True, "true")
                record[name] = value
            out.append(record)
        return out
