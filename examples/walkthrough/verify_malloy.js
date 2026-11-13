// Option 2: runs 2-engagement.malloy on DuckDB against message.sql and checks all nine member groups.
// See README.md for the install and run commands. Local only; no Databricks connection.
const fs = require('fs');
const path = require('path');
const {SingleConnectionRuntime} = require('@malloydata/malloy');
const {DuckDBConnection} = require('@malloydata/db-duckdb');

// "typology|market" -> [sent, unique_clients, delivery rate in %]; "*" means rolled up.
const EXPECTED = {
  'New|HK': [3, 2, 66.7], 'New|SG': [1, 1, 100.0], 'VIP|HK': [1, 1, 100.0], 'VIP|SG': [3, 2, 66.7],
  'New|*': [4, 3, 75.0], 'VIP|*': [4, 2, 75.0], '*|HK': [4, 3, 75.0], '*|SG': [4, 3, 75.0], '*|*': [8, 5, 75.0],
};
const cell = n => [Number(n.sent), Number(n.unique_clients), Math.round(Number(n.delivery_rate) * 1000) / 10];

(async () => {
  const connection = new DuckDBConnection('duckdb', ':memory:');
  await connection.runSQL(fs.readFileSync(path.join(__dirname, 'message.sql'), 'utf8').replace(/;\s*$/, ''));
  const runtime = new SingleConnectionRuntime({connection});
  const query = runtime.loadModel(fs.readFileSync(path.join(__dirname, '2-engagement.malloy'), 'utf8')).loadQueryByName('pivot');
  const total = (await query.run()).data.toObject()[0];

  const got = {'*|*': cell(total)};                       // the tree, flattened to member groups
  for (const m of total.by_market) got[`*|${m.market}`] = cell(m);
  for (const t of total.by_typology) {
    got[`${t.typology}|*`] = cell(t);
    for (const m of t.by_market) got[`${t.typology}|${m.market}`] = cell(m);
  }
  const ok = JSON.stringify(Object.entries(got).sort()) === JSON.stringify(Object.entries(EXPECTED).sort());
  if (!ok) console.error(JSON.stringify(got));
  const version = require('@malloydata/malloy/package.json').version;
  console.log(`2-engagement.malloy: ${Object.keys(got).length} member groups ${ok ? 'match' : 'DO NOT match'} on DuckDB, Malloy ${version}`);
  await connection.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FAILED:', e.message || e); process.exit(2); });
