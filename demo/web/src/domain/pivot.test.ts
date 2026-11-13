import { describe, expect, it } from 'vitest'
import type { RunResult } from '../api/types'
import { formatValue, memberLabel, plural, titleCase } from './format'
import { buildPivot, compareKeys, listRows } from './pivot'

const run = (over: Partial<RunResult> = {}): RunResult => ({
  backend: 'sql', states: [], dims: ['typology', 'market'], rows: ['typology'], cols: ['market'],
  kpis: [{ id: 'sent', label: 'Message Sent', format: 'number', status: 'confirmed', measures: ['n_sent'] }, { id: 'rate', label: 'Rate', format: 'percent', status: 'confirmed', measures: [] }],
  measures: [], violations: [], scopes: [], estimate: '',
  nodes: [
    { scope: ['typology', 'market'], members: ['New', 'HK'], values: { sent: 3, rate: 0.5 } },
    { scope: ['typology', 'market'], members: [null, 'HK'], values: { sent: 1, rate: null } },
    { scope: ['typology'], members: ['New'], values: { sent: 3, rate: 0.5 } },
    { scope: ['typology'], members: [null], values: { sent: 1, rate: null } },
    { scope: ['market'], members: ['HK'], values: { sent: 4, rate: 0.4 } },
    { scope: [], members: [], values: { sent: 4, rate: 0.4 } },
  ],
  ...over,
})

describe('format', () => {
  it('writes a NULL member as (none), never blank (EC-D-05)', () => {
    expect(memberLabel(null)).toBe('(none)')
    expect(memberLabel(2026)).toBe('2026')
  })
  it('writes a missing or NaN value as a dash, never "null" or "NaN" (EC-D-10)', () => {
    expect(formatValue(null, 'number')).toBe('–')
    expect(formatValue(Number.NaN, 'percent')).toBe('–')
    expect(formatValue(undefined, 'percent')).toBe('–')
  })
  it('formats percentages with one decimal and counts with separators', () => {
    expect(formatValue(0.8333333, 'percent')).toBe('83.3%')
    expect(formatValue(0, 'percent')).toBe('0.0%')
    expect(formatValue(1234567, 'number')).toBe('1,234,567')
    expect(formatValue(2.5, 'number')).toBe('2.5')
  })
  it('makes ids readable', () => {
    expect(titleCase('send_year')).toBe('Send year')
    expect(plural(1, 'message')).toBe('1 message')
    expect(plural(13, 'message')).toBe('13 messages')
  })
})

describe('pivot', () => {
  it('orders children first, then the subtotal, the grand total last', () => {
    const p = buildPivot(run(), 'sent')
    expect(p.rows.map((r) => r.label)).toEqual(['(none)', 'New', 'Total'])
    expect(p.rows.map((r) => r.kind)).toEqual(['detail', 'detail', 'total'])
    expect(p.cols.map((c) => c.label)).toEqual(['HK', 'All'])
  })
  it('keeps the NULL member and the grand total as different rows (EC-D-05)', () => {
    const p = buildPivot(run(), 'sent')
    const none = p.rows.find((r) => r.label === '(none)')!
    const total = p.rows.find((r) => r.kind === 'total')!
    const hk = p.cols[0]!
    expect(p.cell(none, hk)?.text).toBe('1')
    expect(p.cell(total, hk)?.text).toBe('4')
  })
  it('shows a blank value as a dash and gives it no data bar (EC-D-10)', () => {
    const p = buildPivot(run(), 'rate')
    const none = p.rows.find((r) => r.label === '(none)')!
    const cell = p.cell(none, p.cols[0]!)!
    expect(cell.text).toBe('–')
    expect(cell.bar).toBeNull()
    expect(p.cell(p.rows.find((r) => r.kind === 'total')!, p.cols[0]!)?.bar).toBeCloseTo(0.4, 5)
  })
  it('labels a subtotal with its path when there are two row dimensions', () => {
    const r = run({
      rows: ['typology', 'tier'], dims: ['typology', 'tier', 'market'], cols: [],
      nodes: [
        { scope: ['typology', 'tier'], members: ['New', 'Gold'], values: { sent: 2 } },
        { scope: ['typology'], members: ['New'], values: { sent: 2 } },
        { scope: [], members: [], values: { sent: 2 } },
      ],
    })
    const p = buildPivot(r, 'sent')
    expect(p.rows.map((x) => [x.label, x.kind])).toEqual([['New / Gold', 'detail'], ['New / total', 'subtotal'], ['Total', 'total']])
    expect(p.cols.map((c) => c.label)).toEqual(['Message Sent'])
  })
  it('refuses a KPI that is not in the result', () => {
    expect(() => buildPivot(run(), 'ghost')).toThrow(/not in this result/)
  })
  it('compares keys so that numbers sort numerically and NULL sorts first', () => {
    expect(compareKeys([2025], [2026], 1)).toBeLessThan(0)
    expect(compareKeys([null], ['A'], 1)).toBeLessThan(0)
    expect(compareKeys([9], [10], 1)).toBeLessThan(0)
    expect(compareKeys(['A'], [], 1)).toBeLessThan(0)
  })
  it('is empty, not broken, for a result with no nodes (EC-D-09)', () => {
    const p = buildPivot(run({ nodes: [] }), 'sent')
    expect(p.rows).toEqual([])
    expect(p.cols).toEqual([])
  })
})

describe('listRows', () => {
  it('lists each group in order, NULL first, then the grand total, with the service values untouched', () => {
    const rows = listRows(run({ rows: ['typology'], cols: [] }))
    expect(rows.map((r) => [r.label, r.kind])).toEqual([['(none)', 'detail'], ['New', 'detail'], ['Total', 'total']])
    expect(rows[2]?.values.sent).toBe(4)
  })
  it('is empty for an empty result', () => {
    expect(listRows(run({ nodes: [] }))).toEqual([])
  })
})
