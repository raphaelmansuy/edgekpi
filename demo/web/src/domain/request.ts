import type { BackendId, Catalogue, ReportRequest } from '../api/types'
import { titleCase } from './format'

export const DEFAULT_BACKEND: BackendId = 'sql'

export function defaultRequest(): ReportRequest {
  return {
    kpis: ['sent', 'delivery_rate', 'reached'],
    rows: ['typology'],
    cols: ['market'],
    totals: { rows: true, cols: true },
    params: {},
    where: [],
    published: false,
  }
}

/** A request with nothing chosen but the defaults; the tutorial and the lab build theirs from it. */
export function makeRequest(over: Partial<ReportRequest>): ReportRequest {
  return { ...defaultRequest(), kpis: [], rows: [], cols: [], ...over }
}

const without = <T,>(list: T[], item: T) => list.filter((x) => x !== item)

export function addKpi(r: ReportRequest, id: string): ReportRequest {
  return r.kpis.includes(id) ? r : { ...r, kpis: [...r.kpis, id] }
}
export function removeKpi(r: ReportRequest, id: string): ReportRequest {
  return { ...r, kpis: without(r.kpis, id) }
}

/** A dimension may sit on one axis once: the picker offers only what is not used (EC-D-08). */
export function freeDimensions(r: ReportRequest, all: string[]): string[] {
  const used = new Set([...r.rows, ...r.cols])
  return all.filter((d) => !used.has(d))
}

export function addDimension(r: ReportRequest, axis: 'rows' | 'cols', id: string): ReportRequest {
  if ([...r.rows, ...r.cols].includes(id)) return r
  return { ...r, [axis]: [...r[axis], id] }
}
export function removeDimension(r: ReportRequest, axis: 'rows' | 'cols', id: string): ReportRequest {
  return { ...r, [axis]: without(r[axis], id) }
}

export function setDate(r: ReportRequest, name: 'start_date' | 'end_date', value: string): ReportRequest {
  const params = { ...r.params }
  if (value === '') delete params[name]
  else params[name] = value
  return { ...r, params }
}

export function setWhere(r: ReportRequest, dim: string | null, selected: (string | number)[]): ReportRequest {
  return { ...r, where: dim === null || selected.length === 0 ? [] : [{ dim, in: selected }] }
}

export function canRun(r: ReportRequest): { ok: true } | { ok: false; reason: string } {
  if (r.kpis.length === 0) return { ok: false, reason: 'Pick at least one KPI.' }
  return { ok: true }
}

/** A hint before the server is asked: an end date on or before the start date selects nothing (EC-D-20). */
export function dateHint(r: ReportRequest): string | null {
  const { start_date: from, end_date: to } = r.params
  if (from && to && to <= from) return 'The end date is excluded, so this range selects nothing.'
  return null
}

/** With "published" on, only confirmed KPIs pass; say which ones will be refused (EC-D-21). */
export function publishedProblems(r: ReportRequest, c: Catalogue): string[] {
  if (!r.published) return []
  return r.kpis.filter((id) => c.kpis.find((k) => k.id === id)?.status !== 'confirmed')
}

export function toApiRequest(r: ReportRequest): ReportRequest {
  return { ...r, params: Object.fromEntries(Object.entries(r.params).filter(([, v]) => v !== '')) }
}

export function describeRequest(r: ReportRequest, c: Catalogue): string {
  const label = (id: string) => c.kpis.find((k) => k.id === id)?.label ?? id
  const dim = (id: string) => titleCase(id)
  const parts = [r.kpis.map(label).join(', ') || 'no KPI']
  if (r.rows.length) parts.push(`by ${r.rows.map(dim).join(' then ')}`)
  if (r.cols.length) parts.push(`across ${r.cols.map(dim).join(' then ')}`)
  if (r.where.length) parts.push(`where ${r.where.map((w) => `${dim(w.dim)} is ${w.in.join(' or ')}`).join(' and ')}`)
  return parts.join(' ')
}

export function requestKey(r: ReportRequest, backend: BackendId): string {
  return JSON.stringify([backend, toApiRequest(r)])
}
