import type { Member, RunKpi, RunResult } from '../api/types'
import { formatValue, memberLabel } from './format'

export type AxisKind = 'detail' | 'subtotal' | 'total'

export interface AxisKey {
  id: string
  key: Member[]
  kind: AxisKind
  label: string
}

export interface PivotCell {
  value: number | null
  text: string
  scope: string[]
  members: Member[]
  /** a percent KPI's value as 0..1, for the data bar */
  bar: number | null
}

export interface Pivot {
  kpi: RunKpi
  rowDims: string[]
  colDims: string[]
  rows: AxisKey[]
  cols: AxisKey[]
  cell(row: AxisKey, col: AxisKey): PivotCell | undefined
}

const rank = (m: Member): [number, string] => (m === null ? [0, ''] : typeof m === 'number' ? [1, String(m).padStart(12, '0')] : [1, String(m)])

/** Children first, then their subtotal, the grand total last: shorter keys are padded with a high sentinel. */
export function compareKeys(a: Member[], b: Member[], depth: number): number {
  for (let i = 0; i < depth; i++) {
    const [ra, ta] = i < a.length ? rank(a[i] as Member) : ([2, ''] as [number, string])
    const [rb, tb] = i < b.length ? rank(b[i] as Member) : ([2, ''] as [number, string])
    if (ra !== rb) return ra - rb
    if (ta !== tb) return ta < tb ? -1 : 1
  }
  return 0
}

function axisKey(key: Member[], depth: number, totalWord: string): AxisKey {
  const kind: AxisKind = key.length === 0 ? 'total' : key.length === depth ? 'detail' : 'subtotal'
  const path = key.map(memberLabel).join(' / ')
  const label = kind === 'total' ? totalWord : kind === 'subtotal' ? `${path} / total` : path
  return { id: JSON.stringify(key), key, kind, label }
}

/** One table for one KPI: row dimensions down, column dimensions across, every requested total. Pure: no I/O. */
export function buildPivot(run: RunResult, kpiId: string): Pivot {
  const kpi = run.kpis.find((k) => k.id === kpiId)
  if (!kpi) throw new Error(`KPI ${kpiId} is not in this result`)
  const cells = new Map<string, PivotCell>()
  const rowKeys = new Map<string, Member[]>()
  const colKeys = new Map<string, Member[]>()
  for (const node of run.nodes) {
    const at = new Map(node.scope.map((d, i) => [d, node.members[i] as Member]))
    const rowKey = run.rows.filter((d) => at.has(d)).map((d) => at.get(d) as Member)
    const colKey = run.cols.filter((d) => at.has(d)).map((d) => at.get(d) as Member)
    const value = node.values[kpiId] ?? null
    cells.set(JSON.stringify([rowKey, colKey]), { value, text: formatValue(value, kpi.format), scope: node.scope, members: node.members, bar: null })
    rowKeys.set(JSON.stringify(rowKey), rowKey)
    colKeys.set(JSON.stringify(colKey), colKey)
  }
  // a rate's bar is its own share of 100%, so bars compare across cells honestly
  if (kpi.format === 'percent') for (const c of cells.values()) c.bar = c.value === null ? null : Math.min(1, Math.abs(c.value))
  const rows = [...rowKeys.values()].sort((a, b) => compareKeys(a, b, run.rows.length)).map((k) => axisKey(k, run.rows.length, 'Total'))
  const cols = [...colKeys.values()].sort((a, b) => compareKeys(a, b, run.cols.length)).map((k) => axisKey(k, run.cols.length, run.cols.length ? 'All' : kpi.label))
  return { kpi, rowDims: run.rows, colDims: run.cols, rows, cols, cell: (r, c) => cells.get(JSON.stringify([r.key, c.key])) }
}

export interface ListRow {
  label: string
  kind: AxisKind
  values: Record<string, number | null>
}

/**
 * The rows of a result with at most one row dimension and no columns: each group, then the grand total.
 * The tutorial shows the measures behind each rate; every value is the service's, none is computed here.
 */
export function listRows(run: RunResult): ListRow[] {
  const dim = run.rows[0]
  const groups = run.nodes.filter((n) => n.scope.length === 1 && n.scope[0] === dim).sort((a, b) => compareKeys(a.members, b.members, 1))
  const total = run.nodes.find((n) => n.scope.length === 0)
  const rows: ListRow[] = groups.map((n) => ({ label: memberLabel(n.members[0] ?? null), kind: 'detail' as const, values: n.values }))
  if (total) rows.push({ label: 'Total', kind: 'total', values: total.values })
  return rows
}
