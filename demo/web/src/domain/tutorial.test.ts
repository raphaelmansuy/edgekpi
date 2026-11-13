import { describe, expect, it } from 'vitest'
import type { MessageRow } from '../api/types'
import { CONTRACT, IDIOMS, LAYOUTS, SQL_LADDER, STAGES, STEPS, advice, clientsInSeveralMarkets, excerpt, lineMatching, measureUse, measuresOf, pairSummary, parseStep } from './tutorial'

const row = (client_id: string, market: string, is_delivered: boolean): MessageRow => ({
  message_id: 1, client_id, typology: 'New', market, send_date: '2026-01-01', is_delivered, is_opened: false, is_clicked: false,
})

describe('parseStep', () => {
  it('starts at the first step with no parameter', () => {
    expect(parseStep(null, 10)).toEqual({ step: 1, adjusted: false })
  })
  it('reads a step in range', () => {
    expect(parseStep('4', 10)).toEqual({ step: 4, adjusted: false })
  })
  it('clamps a step out of range and says it adjusted (EC-D-25)', () => {
    expect(parseStep('99', 10)).toEqual({ step: 10, adjusted: true })
    expect(parseStep('0', 10)).toEqual({ step: 1, adjusted: true })
    expect(parseStep('-3', 10)).toEqual({ step: 1, adjusted: true })
  })
  it('treats anything that is not a whole number as the first step (EC-D-25)', () => {
    for (const bad of ['abc', '2.5', '', 'NaN', '<script>']) expect(parseStep(bad, 10)).toEqual({ step: 1, adjusted: true })
  })
})

describe('clientsInSeveralMarkets', () => {
  it('lists a client delivered in two markets, with the markets sorted', () => {
    const rows = [row('c1', 'SG', true), row('c1', 'HK', true), row('c2', 'HK', true), row('c2', 'HK', true)]
    expect(clientsInSeveralMarkets(rows)).toEqual([{ client: 'c1', markets: ['HK', 'SG'] }])
  })
  it('ignores messages that were not delivered, because Reach counts delivered clients', () => {
    expect(clientsInSeveralMarkets([row('c1', 'HK', true), row('c1', 'SG', false)])).toEqual([])
  })
})

describe('tutorial content', () => {
  it('has twelve steps with unique ids and a learning sentence each', () => {
    expect(STEPS).toHaveLength(12)
    expect(new Set(STEPS.map((s) => s.id)).size).toBe(12)
    expect(STEPS.every((s) => s.learn.length > 20)).toBe(true)
  })
  it('offers four layouts of one KPI, from nothing to two dimensions', () => {
    expect(LAYOUTS.map((l) => [l.request.rows.length, l.request.cols.length])).toEqual([[0, 0], [1, 0], [1, 0], [1, 1]])
    expect(new Set(LAYOUTS.map((l) => l.request.kpis.join())).size).toBe(1)
  })
})

describe('SQL ladder and helpers', () => {
  it('grows one idea at a time: one KPI and nothing, then a condition, then one dimension, then two', () => {
    expect(SQL_LADDER.map((r) => [r.request.kpis.length, r.request.rows.length + r.request.cols.length])).toEqual([[1, 0], [1, 0], [1, 1], [2, 2]])
    expect(SQL_LADDER.every((r) => r.marks.length > 0 && r.adds.length > 20)).toBe(true)
  })
  it('quotes the first matching line of a statement, trimmed, and nothing when there is none', () => {
    const sql = 'SELECT a,\n    COUNT(*) AS n_sent,\n    COUNT(*) FILTER(WHERE x) AS n_x,\nFROM t'
    expect(lineMatching(sql, /FILTER/)).toBe('COUNT(*) FILTER(WHERE x) AS n_x')
    expect(lineMatching(sql, /GROUPING/)).toBeNull()
  })
  it('excerpts the capture group, or the whole match, or nothing', () => {
    expect(excerpt('a / b AS r, c', /(\w \/ \w AS \w)/)).toBe('a / b AS r')
    expect(excerpt('SELECT 1', /SELECT/)).toBe('SELECT')
    expect(excerpt('SELECT 1', /FROM/)).toBeNull()
  })
  it('lists the measures of a formula once each, in order', () => {
    expect(measuresOf('m3 / m1')).toEqual(['m3', 'm1'])
    expect(measuresOf('m2 / m2')).toEqual(['m2'])
    expect(measuresOf('n_delivered / n_sent')).toEqual([])
  })
  it('walks five stages and six idioms, each with the three sentences a reader needs', () => {
    expect(STAGES.map((x) => x.id)).toEqual(['inventory', 'read', 'review', 'prove', 'switch'])
    expect(IDIOMS).toHaveLength(6)
    expect([...STAGES, ...IDIOMS].every((x) => Object.values(x).every((v) => v.length > 3))).toBe(true)
  })
})

describe('advice for a refused template', () => {
  it('says what to do for each family of refusal, and never leaves the reader without a next move', () => {
    expect(advice('GRAIN_JOIN_FANOUT: a join changes the grain')).toMatch(/multiplies the rows/)
    expect(advice('INFER_MORE_THAN_ONE_AGGREGATION: more than one aggregation')).toMatch(/Split it/)
    expect(advice('SOMETHING_NEW: whatever')).toMatch(/Keep this query/)
    expect(advice(null)).toMatch(/Keep this query/)
  })
})

describe('pairSummary', () => {
  const ev = { available: true, results: { a: { 'malloy on databricks': { nodes: 4, diffs: 0, violations: 0, error: null } }, b: { 'malloy on databricks': { nodes: 6, diffs: 1, violations: 0, error: null }, 'sql on duckdb': { nodes: 6, diffs: 0, violations: 0, error: null } } } }
  it('adds up the requests of one pair, and says nothing about a pair that was not run', () => {
    expect(pairSummary(ev, 'malloy on databricks')).toEqual({ requests: 2, nodes: 10, differences: 1 })
    expect(pairSummary(ev, 'sql on duckdb')).toEqual({ requests: 1, nodes: 6, differences: 0 })
    expect(pairSummary(ev, 'metric view on databricks')).toBeNull()
  })
  it('says nothing when no run is recorded', () => {
    expect(pairSummary({ available: false }, 'sql on duckdb')).toBeNull()
  })
})

describe('route B: infer from templates', () => {
  it('shows which KPIs share a measure, and a measure nobody uses as unused', () => {
    const kpis = [{ id: 'sent', formula: 'm1' }, { id: 'rate', formula: 'm3 / m1' }]
    const measures = [{ id: 'm1', expr: 'COUNT(*)' }, { id: 'm3', expr: 'COUNT(*) FILTER(WHERE x)' }, { id: 'm9', expr: 'SUM(y)' }]
    expect(measureUse(kpis, measures).map((m) => [m.id, m.usedBy])).toEqual([['m1', ['sent', 'rate']], ['m3', ['rate']], ['m9', []]])
  })
  it('lists five rules, each naming the refusal a breach causes', () => {
    expect(CONTRACT).toHaveLength(5)
    expect(CONTRACT.every((r) => /^(INFER|GRAIN)_[A-Z_]+(, (INFER|GRAIN)_[A-Z_]+)*$/.test(r.refused))).toBe(true)
  })
})
