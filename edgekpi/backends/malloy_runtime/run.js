// Runs one Malloy program and prints the top-level result row as JSON.
// Input (stdin), either
//   {"setup": ["<SQL statement that creates a table>", ...], "source": "<Malloy text ending in run:>"}        in-memory DuckDB
//   {"databricks": {"host", "path", "catalog", "schema"}, "source": "..."}                                    SQL warehouse; the
//                                                       access token is read from EDGEKPI_DBX_TOKEN, never from stdin
// Output (stdout): {"rows": [ ...nested rows... ], "sql": "<SQL Malloy generated>", "malloy": "<version>"}
const fs = require('fs');
const {SingleConnectionRuntime} = require('@malloydata/malloy');
const {DuckDBConnection} = require('@malloydata/db-duckdb');
const {DatabricksConnection} = require('@malloydata/db-databricks');

const plain = value => {
  if (typeof value === 'bigint') return Number(value);
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (value && typeof value === 'object' && 'value' in value && Object.keys(value).length <= 2) return String(value.value);
  return value;
};
const clean = row => Object.fromEntries(Object.entries(row).map(([k, v]) =>
  [k, Array.isArray(v) ? v.map(clean) : plain(v)]));

(async () => {
  const input = JSON.parse(fs.readFileSync(0, 'utf8'));
  let connection;
  if (input.databricks) {
    const d = input.databricks;
    if (!process.env.EDGEKPI_DBX_TOKEN) throw new Error('EDGEKPI_DBX_TOKEN is not set');
    connection = new DatabricksConnection('databricks', {
      host: d.host, path: d.path, token: process.env.EDGEKPI_DBX_TOKEN, defaultCatalog: d.catalog, defaultSchema: d.schema,
    });
  } else {
    connection = new DuckDBConnection('duckdb', ':memory:');
    for (const statement of input.setup) await connection.runSQL(statement);
  }
  const runtime = new SingleConnectionRuntime({connection});
  const query = runtime.loadQuery(input.source);
  const sql = await query.getSQL();
  const result = await query.run();
  const rows = result.data.toObject().map(clean);
  process.stdout.write(JSON.stringify({rows, sql, malloy: require('@malloydata/malloy/package.json').version}));
  await connection.close();
})().catch(error => { process.stderr.write(String((error && error.message) || error)); process.exit(2); });
