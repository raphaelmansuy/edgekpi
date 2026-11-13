import type { BackendId, ReportRequest, RunResult } from '../api/types'

/** One edge case of the library, runnable from the Edge-case lab. `expect` says what a correct service answers. */
export interface Scenario {
  id: string
  ec: string
  title: string
  why: string
  request: Record<string, unknown>
  backend: BackendId
  expect: { error: string } | { ok: (run: RunResult) => boolean; describe: string }
}

const base = (over: Record<string, unknown>) => ({ kpis: ['sent', 'delivery_rate'], rows: [], cols: [], totals: { rows: true, cols: true }, params: {}, where: [], published: false, ...over })

export const SCENARIOS: Scenario[] = [
  {
    id: 'unknown-kpi', ec: 'EC-L-05', title: 'A KPI that does not exist', why: 'A typo must not become an empty column.',
    request: base({ kpis: ['ghost'] }), backend: 'sql', expect: { error: 'REQ_UNKNOWN_KPI' },
  },
  {
    id: 'duplicate-dimension', ec: 'EC-L-04', title: 'The same dimension on both axes', why: 'One dimension on one axis, once.',
    request: base({ rows: ['market'], cols: ['market'] }), backend: 'sql', expect: { error: 'REQ_DUPLICATE_DIMENSION' },
  },
  {
    id: 'impossible-date', ec: 'EC-L-08', title: 'A date that does not exist', why: '30 February is refused before it reaches the data.',
    request: base({ params: { start_date: '2026-02-30' } }), backend: 'sql', expect: { error: 'REQ_BAD_PARAM' },
  },
  {
    id: 'sql-in-a-date', ec: 'EC-L-07', title: 'SQL typed into a date', why: 'Parameters are typed before they travel.',
    request: base({ params: { start_date: "2026-01-01'; DROP TABLE message; --" } }), backend: 'sql', expect: { error: 'REQ_BAD_PARAM' },
  },
  {
    id: 'unconfirmed-published', ec: 'EC-L-16', title: 'An unconfirmed KPI on a published report', why: 'Reach is not approved by its owner yet.',
    request: base({ kpis: ['reached'], published: true }), backend: 'sql', expect: { error: 'REQ_UNCONFIRMED_KPI' },
  },
  {
    id: 'null-in-filter', ec: 'EC-L-22', title: 'A filter on NULL', why: 'NULL never equals anything, so the filter would silently match nothing.',
    request: base({ rows: ['market'], where: [{ dim: 'market', in: ['HK', null] }] }), backend: 'sql', expect: { error: 'REQ_NULL_IN_FILTER' },
  },
  {
    id: 'no-warehouse', ec: 'EC-L-11', title: 'A metric view without a warehouse', why: 'Refused honestly, not faked on another engine.',
    request: base({}), backend: 'metric-view', expect: { error: 'ENGINE_UNAVAILABLE' },
  },
  {
    id: 'injection-in-filter', ec: 'EC-L-07', title: 'SQL typed into a filter value', why: 'Bound as data: it matches no market, and the table is intact.',
    request: base({ rows: ['market'], where: [{ dim: 'market', in: ["HK'; DROP TABLE message; --"] }] }), backend: 'sql',
    expect: { ok: (r) => r.nodes.length === 0, describe: 'no node, no error, nothing dropped' },
  },
  {
    id: 'empty-input', ec: 'EC-L-01', title: 'No rows match', why: 'No input rows means no node, not a zero grand total.',
    request: base({ rows: ['market'], where: [{ dim: 'market', in: ['XX'] }] }), backend: 'sql',
    expect: { ok: (r) => r.nodes.length === 0, describe: 'an empty result' },
  },
  {
    id: 'null-member', ec: 'EC-L-03', title: 'A client missing from the dimension', why: 'Its group reads (none) and is not the Total.',
    request: base({ rows: ['typology'] }), backend: 'sql',
    expect: { ok: (r) => r.nodes.some((n) => n.scope.length === 1 && n.members[0] === null) && r.nodes.some((n) => n.scope.length === 0), describe: 'a (none) node and a Total node' },
  },
  {
    id: 'zero-denominator', ec: 'EC-L-02', title: 'A group with no delivered message', why: 'Open rate divides by delivered: blank, not an error and not NaN.',
    request: base({ kpis: ['open_rate'], rows: ['market'], where: [{ dim: 'market', in: ['JP'] }] }), backend: 'sql',
    expect: { ok: (r) => r.nodes.some((n) => n.values.open_rate === null), describe: 'a blank open rate' },
  },
  {
    id: 'totals-off', ec: 'EC-L-19', title: 'Totals switched off', why: 'Only the detail cells are computed.',
    request: base({ rows: ['typology'], cols: ['market'], totals: { rows: false, cols: false } }), backend: 'sql',
    expect: { ok: (r) => r.nodes.every((n) => n.scope.length === 2), describe: 'detail nodes only' },
  },
]

type Loose = { kpis?: string[]; rows?: string[]; cols?: string[]; params?: Record<string, string>; where?: { dim: string; in: unknown[] }[]; published?: boolean; totals?: { rows: boolean; cols: boolean } }

/** The request in a line a reader can check against the title, instead of raw JSON. */
export function summarise(request: Record<string, unknown>): string {
  const r = request as Loose
  const parts = [`KPIs ${(r.kpis ?? []).join(', ')}`]
  if (r.rows?.length) parts.push(`rows ${r.rows.join(', ')}`)
  if (r.cols?.length) parts.push(`columns ${r.cols.join(', ')}`)
  for (const w of r.where ?? []) parts.push(`${w.dim} in ${w.in.map((v) => (v === null ? 'NULL' : String(v))).join(', ')}`)
  for (const [k, v] of Object.entries(r.params ?? {})) parts.push(`${k} = ${v}`)
  if (r.published) parts.push('published')
  if (r.totals && !r.totals.rows && !r.totals.cols) parts.push('no totals')
  return parts.join(' · ')
}

export const scenarioRequest = (s: Scenario) => s.request as unknown as ReportRequest
