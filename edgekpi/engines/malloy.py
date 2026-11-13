"""Engine for Malloy: runs the Malloy text on an in-memory DuckDB through node (the Malloy runtime is JavaScript).

The Malloy package bundles its own DuckDB, whose database files are not readable by every Python duckdb version, so the
engine builds the tables from the same SQL script the SQL engine loads. One data script feeds every engine (DRY).
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
from typing import Any

from ..backends.base import Statement
from ..errors import EngineError, UnsupportedError
from .sql import split_script

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "backends" / "malloy_runtime"


def available() -> bool:
    return shutil.which("node") is not None and (RUNTIME / "node_modules" / "@malloydata" / "malloy").exists()


class _NodeEngine:
    """Runs a Malloy program through the Node runtime. Subclasses say where the data is."""

    name = ""

    def __init__(self, timeout: float = 600):
        if not available():
            raise UnsupportedError("ENGINE_UNAVAILABLE", f"needs node and `npm install` in {RUNTIME}")
        self.timeout = timeout
        self.last_sql: str | None = None        # the SQL Malloy generated, for inspection and docs
        self.malloy_version: str | None = None

    def _payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def _environment(self) -> dict[str, str] | None:
        return None

    def execute(self, statement: Statement) -> list[dict[str, Any]]:
        if statement.language != "malloy":
            raise UnsupportedError("ENGINE_LANGUAGE", f"this engine runs Malloy, not {statement.language}")
        done = subprocess.run(
            ["node", str(RUNTIME / "run.js")], input=json.dumps({**self._payload(), "source": statement.text}),
            capture_output=True, text=True, timeout=self.timeout, cwd=RUNTIME, env=self._environment(),
        )
        if done.returncode != 0:
            raise EngineError("ENGINE_FAILED", f"malloy: {done.stderr.strip().splitlines()[0] if done.stderr.strip() else 'exit ' + str(done.returncode)}")
        payload = json.loads(done.stdout)
        self.last_sql, self.malloy_version = payload["sql"], payload["malloy"]
        return payload["rows"]


class MalloyDuckDBEngine(_NodeEngine):
    name = "malloy-duckdb"

    def __init__(self, setup_script: str, timeout: float = 120):
        super().__init__(timeout)
        self.setup = split_script(setup_script)

    def _payload(self) -> dict[str, Any]:
        return {"setup": self.setup}


class MalloyDatabricksEngine(_NodeEngine):
    """Malloy's Databricks connection, on the same warehouse and the same tables as the SQL engine.

    The access token comes from the Databricks SDK session of the given engine and is handed to Node through the
    environment of the child process only: never on the command line, never on stdin, never in the result.
    """

    name = "malloy-databricks"

    def __init__(self, warehouse, timeout: float = 600):
        super().__init__(timeout)
        self.warehouse = warehouse
        info = warehouse.client.warehouses.get(warehouse.warehouse)
        self.http_path = info.odbc_params.path
        self.table_prefix = f"{warehouse.catalog}.{warehouse.schema}."

    def _payload(self) -> dict[str, Any]:
        config = self.warehouse.client.config
        return {"databricks": {"host": config.host.replace("https://", ""), "path": self.http_path,
                               "catalog": self.warehouse.catalog, "schema": self.warehouse.schema}}

    def _environment(self) -> dict[str, str]:
        token = self.warehouse.client.config.authenticate()["Authorization"].removeprefix("Bearer ")
        return {**os.environ, "EDGEKPI_DBX_TOKEN": token}
