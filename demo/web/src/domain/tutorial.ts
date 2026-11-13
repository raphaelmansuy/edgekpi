import type { Evidence, MessageRow, ReportRequest } from '../api/types'
import { makeRequest } from './request'

export interface StepInfo {
  id: string
  title: string
  /** one sentence: what the learner will be able to say after the step */
  learn: string
}

export const STEPS: StepInfo[] = [
  { id: 'data', title: 'The rows behind a report', learn: 'A report is a summary of 13 messages; every number can be traced back to them.' },
  { id: 'predict', title: 'Predict the total', learn: 'The tempting way to total a percentage gives a different answer from the right way.' },
  { id: 'inside', title: 'Look inside the percentage', learn: 'A rate forgets how big its group was; the counts behind it do not.' },
  { id: 'reach', title: 'A second trap: unique clients', learn: 'Counting people cannot be done by adding the cells.' },
  { id: 'old', title: 'Why a query per KPI fails', learn: 'A saved query returns one finished number; nothing in it says how to total.' },
  { id: 'define', title: 'The fix: define it once', learn: 'Describe a KPI by its counts and its formula; every total follows.' },
  { id: 'ways', title: 'Three ways to write it', learn: 'A Databricks metric view, Malloy and generated SQL each hold the same definition; here is how each one works.' },
  { id: 'sqlhow', title: 'Generated SQL, piece by piece', learn: 'How a KPI is expressed as a definition, and how each part of it becomes a part of the SQL.' },
  { id: 'moveover', title: 'Moving from your queries', learn: 'Move the saved queries once, or keep writing templates and let a tool infer and check the definition.' },
  { id: 'layout', title: 'Change the layout, keep the total', learn: 'With the definition as data, the grand total is the same under any layout.' },
  { id: 'verify', title: 'Trust, but check', learn: 'Three backends and an independent reference must agree, and every result is checked.' },
  { id: 'yours', title: 'Your turn', learn: 'Where to go next, and the three rules to remember.' },
]

/** Reports the tutorial runs. They are fixed so every learner sees the same numbers. */
export const RATE_BY_TYPOLOGY: ReportRequest = makeRequest({ kpis: ['delivery_rate', 'sent'], rows: ['typology'] })
export const REACH_BY_MARKET: ReportRequest = makeRequest({ kpis: ['reached', 'sent'], rows: ['market'] })
export const WAYS_REQUEST: ReportRequest = makeRequest({ kpis: ['delivery_rate'], rows: ['typology'], cols: ['market'] })
export const YOUR_TURN: ReportRequest = makeRequest({ kpis: ['sent', 'delivery_rate', 'reached'], rows: ['typology'], cols: ['market'] })

export interface Layout {
  id: string
  label: string
  request: ReportRequest
}

export const LAYOUTS: Layout[] = [
  { id: 'none', label: 'Nothing: one number', request: makeRequest({ kpis: ['delivery_rate'] }) },
  { id: 'typology', label: 'By typology', request: makeRequest({ kpis: ['delivery_rate'], rows: ['typology'] }) },
  { id: 'market', label: 'By market', request: makeRequest({ kpis: ['delivery_rate'], rows: ['market'] }) },
  { id: 'both', label: 'Typology and market', request: makeRequest({ kpis: ['delivery_rate'], rows: ['typology'], cols: ['market'] }) },
]

/** Step in the hash (`#/tutorial/4`): missing or not a number means the first step; out of range is clamped. */
export function parseStep(param: string | null, total: number): { step: number; adjusted: boolean } {
  if (param === null) return { step: 1, adjusted: false }
  const n = Number(param)
  if (!Number.isInteger(n)) return { step: 1, adjusted: true }
  const step = Math.min(Math.max(n, 1), total)
  return { step, adjusted: step !== n }
}

/**
 * Clients that were delivered a message in more than one market. They are the reason the Reach of the whole is below the
 * sum of its parts. Read straight from the rows; no KPI is computed.
 */
export function clientsInSeveralMarkets(rows: MessageRow[]): { client: string; markets: string[] }[] {
  const seen = new Map<string, Set<string>>()
  for (const r of rows) {
    if (!r.is_delivered) continue
    seen.set(r.client_id, (seen.get(r.client_id) ?? new Set()).add(r.market))
  }
  return [...seen.entries()]
    .filter(([, markets]) => markets.size > 1)
    .map(([client, markets]) => ({ client, markets: [...markets].sort() }))
    .sort((a, b) => a.client.localeCompare(b.client))
}

export interface Rung {
  id: string
  label: string
  /** what this rung adds to the previous one, in one sentence */
  adds: string
  request: ReportRequest
  /** fragments that identify the new lines in the generated statement */
  marks: string[]
}

/** Four reports, each adding one idea to the last, so the SQL is learned by growing it. */
export const SQL_LADDER: Rung[] = [
  { id: 'count', label: '1. Count', adds: 'A measure is an aggregate. One KPI, no grouping: one row.', request: makeRequest({ kpis: ['sent'] }), marks: ['COUNT(*) AS n_sent'] },
  { id: 'rate', label: '2. Condition and formula', adds: 'A second measure with a condition (FILTER), and a formula in the outer SELECT, applied after the counts.', request: makeRequest({ kpis: ['delivery_rate'] }), marks: ['FILTER', 'NULLIF'] },
  { id: 'group', label: '3. Group', adds: 'A dimension: the grouping columns, and GROUPING SETS to also get the total in the same pass.', request: makeRequest({ kpis: ['delivery_rate'], rows: ['typology'] }), marks: ['GROUPING', 'GROUP BY'] },
  { id: 'unique', label: '4. Two dimensions, unique count', adds: 'Two dimensions give four levels. A unique count is its own aggregate, recounted at every level.', request: makeRequest({ kpis: ['delivery_rate', 'reached'], rows: ['typology'], cols: ['market'] }), marks: ['DISTINCT', 'GROUPING SETS'] },
]

/** The first line of a statement that matches, trimmed: used to quote the real SQL next to a definition. */
export function lineMatching(text: string, pattern: RegExp): string | null {
  const line = text.split('\n').find((l) => pattern.test(l))
  return line ? line.trim().replace(/,$/, '') : null
}

/** The part of a statement that matches (its first capture group when there is one), or null: quotes the real SQL. */
export function excerpt(text: string, pattern: RegExp): string | null {
  const m = pattern.exec(text)
  return m ? (m[1] ?? m[0]).trim() : null
}

/** The measures a legacy-inferred formula such as `m3 / m1` refers to, in order and without repeats. */
export function measuresOf(formula: string): string[] {
  return [...new Set(formula.match(/\bm\d+\b/g) ?? [])]
}

export interface Idiom {
  legacy: string
  becomes: string
  why: string
}

/** What each habit of the saved queries turns into. Each legacy fragment appears in the registry templates. */
export const IDIOMS: Idiom[] = [
  { legacy: '{{ group_by_list }}', becomes: 'The report’s rows and columns', why: 'The grouping stops being pasted text and becomes a choice made per report.' },
  { legacy: 'try_divide(COUNT_IF(x), COUNT(*))', becomes: 'ratio(n_x, n_sent)', why: 'The two counts become measures; the division is written once, with its zero guard.' },
  { legacy: 'COUNT_IF(C.is_delivered)', becomes: 'COUNT(*) FILTER (WHERE is_delivered)', why: 'One spelling for a conditional count, so equal counts are recognised as equal.' },
  { legacy: 'AND C.is_delivered (in WHERE)', becomes: 'the same condition, inside the measure', why: 'A condition that belongs to one KPI must not filter the others.' },
  { legacy: 'try_cast(:start_date AS DATE) IS NULL OR …', becomes: 'an optional filter with a typed parameter', why: 'Declared once; a missing date means “no limit”, never an error.' },
  { legacy: 'LEFT JOIN client D ON …', becomes: 'a join, declared once', why: 'The library checks that it does not multiply the rows.' },
]

export interface Stage {
  id: string
  title: string
  you: string
  tool: string
  done: string
}

export const STAGES: Stage[] = [
  { id: 'inventory', title: 'Inventory', you: 'Export the saved queries.', tool: 'Keeps each one apart: one bad query never blocks the others.', done: 'Every query has an id.' },
  { id: 'read', title: 'Read', you: 'Nothing.', tool: 'Parses each query and splits it into source, joins, filters and the one aggregate.', done: 'Each query is accepted or refused, with a reason.' },
  { id: 'review', title: 'Review', you: 'Read the proposed definitions and name an owner.', tool: 'Marks every KPI as draft until someone confirms it.', done: 'Each KPI has an owner and a status.' },
  { id: 'prove', title: 'Prove', you: 'Look at the count of differences.', tool: 'Runs the old query and the new definition on the same data and compares every value.', done: 'Zero values differ.' },
  { id: 'switch', title: 'Switch', you: 'Point one report at the definition, then retire the old query.', tool: 'Serves the same report, plus the totals the old queries could not give.', done: 'The old query is deleted, one KPI at a time.' },
]

/** What to do about a refused template, by the code at the start of its reason. */
export function advice(reason: string | null): string {
  const code = (reason ?? '').split(':')[0] ?? ''
  if (code.startsWith('GRAIN_')) return 'The join multiplies the rows, so a count would be inflated. Count at the right level (for example distinct messages), or aggregate the many side first, then migrate.'
  if (code === 'INFER_MORE_THAN_ONE_AGGREGATION') return 'One query returns two numbers, so it is two KPIs in one text. Split it into one query per number, then migrate each.'
  return 'Keep this query running as it is for now, and ask its owner to simplify it. Nothing else is blocked.'
}

/** What the recorded warehouse run says about one backend-and-engine pair, e.g. `malloy on databricks`. */
export function pairSummary(evidence: Evidence, pair: string): { requests: number; nodes: number; differences: number } | null {
  const rows = Object.values(evidence.results ?? {}).map((r) => r[pair]).filter((r) => r !== undefined)
  if (!evidence.available || rows.length === 0) return null
  return { requests: rows.length, nodes: rows.reduce((n, r) => n + r.nodes, 0), differences: rows.reduce((n, r) => n + r.diffs, 0) }
}

export interface ContractRule {
  write: string
  because: string
  /** what the tool says when the rule is broken */
  refused: string
}

/** What a template must look like for its definition to be inferred. Each rule is a refusal code of the library. */
export const CONTRACT: ContractRule[] = [
  { write: 'One SELECT: the grouping slot and one aggregate named kpi_value', because: 'The aggregate is what becomes a measure; a second one is a second KPI.', refused: 'INFER_SELECT, INFER_MORE_THAN_ONE_AGGREGATION' },
  { write: 'GROUP BY exactly the slot', because: 'The slot is replaced by the report’s grouping; anything else would be lost.', refused: 'INFER_GROUP_BY' },
  { write: 'Only LEFT JOINs, every column qualified', because: 'An inner join would drop fact rows; an unqualified column could belong to either table.', refused: 'INFER_NOT_A_LEFT_JOIN, INFER_UNQUALIFIED_COLUMN' },
  { write: 'No HAVING, LIMIT, DISTINCT or window function', because: 'They change the rows after the grouping, which a total cannot repeat.', refused: 'INFER_UNSUPPORTED_CLAUSE, INFER_WINDOW' },
  { write: 'Joins that keep one row per message', because: 'A join that multiplies rows inflates every count, silently.', refused: 'GRAIN_JOIN_FANOUT, GRAIN_KEY_NOT_UNIQUE' },
]

/** For each measure, the KPIs whose formula uses it: how six templates end up on five measures. */
export function measureUse(kpis: { id: string; formula: string }[], measures: { id: string; expr: string }[]): { id: string; expr: string; usedBy: string[] }[] {
  return measures.map((m) => ({ ...m, usedBy: kpis.filter((k) => measuresOf(k.formula).includes(m.id)).map((k) => k.id) }))
}
