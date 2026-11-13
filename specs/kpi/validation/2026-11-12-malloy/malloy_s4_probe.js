// Probe: does one Malloy nested query reproduce the 56 scenario-4 reference groups of the synthetic fixture?
// Local DuckDB only. No Databricks connection, no writes outside this folder. See README.md to run it.
const fs = require('fs');
const path = require('path');
const {SingleConnectionRuntime} = require('@malloydata/malloy');
const {DuckDBConnection} = require('@malloydata/db-duckdb');

const HERE = __dirname;
const SPEC = path.resolve(HERE, '..', '..');
const ATOMS = ['sent', 'delivered', 'opened', 'clicked', 'clients'];
const RATES = ['delivery_rate', 'open_rate', 'click_rate', 'ctor'];
const ROW_LEVELS = [['by_typology', 'typology'], ['by_tier', 'tier'], ['by_campaign', 'campaign']];
const keyOf = r => JSON.stringify([r.typology, r.tier, r.campaign, r.yr, r.market]);
const num = v => (v === null || v === undefined ? null : Number(v));

// Nested Malloy result -> one flat record per member node, keyed like the SQL reference.
function flatten(node, rowKey, depth, out) {
  const emit = (n, yr, market) => {
    const rec = {typology: null, tier: null, campaign: null, ...rowKey, yr, market};
    for (const k of [...ATOMS, ...RATES]) rec[k] = num(n[k]);
    out.push(rec);
  };
  emit(node, null, null);
  for (const y of node.by_year || []) {
    emit(y, num(y.yr), null);
    for (const m of y.by_market || []) emit(m, num(y.yr), m.market);
  }
  if (depth < ROW_LEVELS.length) {
    const [nest, dim] = ROW_LEVELS[depth];
    for (const child of node[nest] || []) flatten(child, {...rowKey, [dim]: child[dim]}, depth + 1, out);
  }
}

async function zeroDenominator(runtime) {
  const model = `
    source: z is duckdb.sql("""SELECT * FROM (VALUES ('B', FALSE, FALSE)) AS t(campaign, is_delivered, is_opened)""") extend {
      measure:
        delivered is count() { where: is_delivered }
        opened is count() { where: is_opened }
        plain is opened / delivered
        guarded is opened / nullif(delivered, 0)
    }
    run: z -> { group_by: campaign; aggregate: delivered, plain, guarded }`;
  const query = runtime.loadQuery(model);
  const sql = await query.getSQL();
  const row = (await query.run()).data.toObject()[0];
  return {
    delivered: num(row.delivered),
    unguarded_division_value: String(row.plain),
    guarded_division_value: String(row.guarded),
    malloy_adds_nullif_itself: /NULLIF/i.test(sql.split('\n').find(l => /"plain"/.test(l)) || ''),
  };
}

(async () => {
  const connection = new DuckDBConnection('duckdb', ':memory:');
  const fixture = fs.readFileSync(path.join(SPEC, 'fixtures', 's4_messages.sql'), 'utf8');
  for (const statement of fixture.split(';').map(s => s.trim()).filter(s => s.replace(/--.*$/gm, '').trim())) {
    await connection.runSQL(statement);
  }
  const grain = (await connection.runSQL('SELECT COUNT(*) AS n, COUNT(DISTINCT message_id) AS k FROM message')).rows[0];
  const referenceSql = fs.readFileSync(path.join(SPEC, 'validation', '2026-11-12', 'generated-s4.sql'), 'utf8')
    .replace(/workspace\.edgekpi_spec\.message/g, 'message').replace(/;\s*$/, '');
  const reference = (await connection.runSQL(referenceSql, {rowLimit: 100000})).rows;

  const runtime = new SingleConnectionRuntime({connection});
  const query = runtime.loadModel(fs.readFileSync(path.join(HERE, 's4.malloy'), 'utf8')).loadQueryByName('s4');
  const sql = await query.getSQL();
  if (process.argv.includes('--write-sql')) fs.writeFileSync(path.join(HERE, 'malloy-generated-s4.sql'), sql + '\n');
  const out = [];
  flatten((await query.run({rowLimit: 100000})).data.toObject()[0], {}, 0, out);

  const want = new Map(reference.map(r => [keyOf({...r, yr: num(r.yr)}), r]));
  const got = new Map(out.map(r => [keyOf(r), r]));
  const mismatches = [];
  for (const [key, r] of want) {
    const g = got.get(key);
    if (!g) { mismatches.push(['missing', key]); continue; }
    for (const a of ATOMS) if (g[a] !== num(r[a])) mismatches.push(['atom', key, a, g[a], num(r[a])]);
    for (const a of RATES) {
      const x = g[a], y = num(r[a]);
      if ((x === null) !== (y === null) || (x !== null && Math.abs(x - y) > 1e-12)) mismatches.push(['rate', key, a, x, y]);
    }
  }
  for (const key of got.keys()) if (!want.has(key)) mismatches.push(['extra', key]);

  const versions = name => require(`${name}/package.json`).version;
  const summary = {
    fixture: {rows: num(grain.n), distinct_message_ids: num(grain.k)},
    reference_groups: want.size,
    malloy_groups: out.length,
    malloy_distinct_keys: got.size,
    mismatches: mismatches.length,
    compared: {integer_atoms: ATOMS, exact: true, ratios: RATES, ratios_tolerance: '1e-12'},
    generated_sql: {
      statements: 1,
      characters: sql.length,
      base_table_references: (sql.match(/\bFROM message\b/g) || []).length,
      group_set_series: (sql.match(/GENERATE_SERIES\(\d+,\d+,\d+\)/g) || []),
      uses_grouping_sets_clause: /GROUPING SETS/i.test(sql),
      count_distinct_expressions: (sql.match(/count\(distinct/gi) || []).length,
    },
    zero_denominator: await zeroDenominator(runtime),
    versions: {
      node: process.version,
      malloy: versions('@malloydata/malloy'),
      db_duckdb: versions('@malloydata/db-duckdb'),
      duckdb: String((await connection.runSQL('SELECT version() AS v')).rows[0].v),
    },
  };
  console.log(JSON.stringify(summary, null, 2));
  if (mismatches.length) console.error(JSON.stringify(mismatches.slice(0, 20)));
  await connection.close();
  process.exit(mismatches.length || out.length !== 56 ? 1 : 0);
})().catch(e => { console.error('PROBE FAILED:', e.message || e); process.exit(2); });
