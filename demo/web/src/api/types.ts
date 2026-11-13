// The contract with the edgekpi service (edgekpi/service.py). One place; every other module imports from here.

export type Status = 'draft' | 'unconfirmed' | 'confirmed'
export type BackendId = 'sql' | 'malloy' | 'metric-view'
export type Member = string | number | boolean | null

export interface ApiError {
  code: string
  message: string
  states: string[]
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError }

export interface WhereClause {
  dim: string
  in: (string | number)[]
}

/** What the reader asks for. Dates are 'YYYY-MM-DD' or absent. */
export interface ReportRequest {
  kpis: string[]
  rows: string[]
  cols: string[]
  totals: { rows: boolean; cols: boolean }
  params: Record<string, string>
  where: WhereClause[]
  published: boolean
}

export interface KpiInfo {
  id: string
  label: string
  formula: string
  status: Status
  owner: string | null
  format: 'number' | 'percent'
  measures: string[]
}

export interface MeasureInfo {
  id: string
  expr: string
  kind: 'count' | 'sum' | 'unique' | 'avg' | 'min' | 'max'
  additive: boolean
}

export interface DimensionInfo {
  id: string
  label: string
  expr: string
  members: Member[]
}

export interface BackendStatus {
  id: BackendId
  label: string
  available: boolean
  reason: string | null
}

export interface Catalogue {
  model: string
  version: string
  source: string
  key: string
  grain: { fact_rows: number; joined_rows: number; distinct_keys: number }
  joins: { id: string; table: string; on: string }[]
  dimensions: DimensionInfo[]
  measures: MeasureInfo[]
  kpis: KpiInfo[]
  filters: { id: string; predicate: string; optional: boolean; params: Record<string, string> }[]
  parameters: Record<string, string>
  backends: BackendStatus[]
}

export interface Node {
  scope: string[]
  members: Member[]
  values: Record<string, number | null>
}

export interface RunKpi {
  id: string
  label: string
  format: 'number' | 'percent'
  status: Status
  measures: string[]
}

export interface Violation {
  code: string
  node: Record<string, Member>
  message: string
}

export interface RunResult {
  backend: BackendId
  states: string[]
  dims: string[]
  rows: string[]
  cols: string[]
  kpis: RunKpi[]
  measures: string[]
  nodes: Node[]
  violations: Violation[]
  scopes: string[][]
  estimate: string
}

export interface Statement {
  kind: 'ddl' | 'query'
  language: 'sql' | 'malloy'
  text: string
}

export type MalloyEngine = 'duckdb' | 'databricks'

/** How Malloy reaches an engine. Placeholders only: a secret never appears in it. */
export interface Connection {
  engine: MalloyEngine
  label: string
  language: string
  text: string
}

export interface Plan {
  backend: BackendId
  connection: Connection | null
  notes: string[]
  estimate: { scopes: number; measures: number; distinct_measures: number; aggregate_states: number; description: string }
  statements: Statement[]
  bindings: { name: string; value: string | number | boolean; type: string }[]
  scopes: string[][]
}

export interface Explanation {
  kpi: string
  label: string
  format: 'number' | 'percent'
  formula: string
  scope: string[]
  members: Member[]
  value: number | null
  terms: { measure: string; kind: string; value: number | null }[]
  is_ratio: boolean
  naive: { method: 'mean' | 'sum'; dimension: string; children: number; value: number; differs: boolean } | null
}

export interface VerifyOutcome {
  label: string
  ok: boolean
  nodes: number
  diffs: number
  violations: number
  error: string | null
}

export interface Verification {
  outcomes: VerifyOutcome[]
  skipped: BackendStatus[]
}

export interface Resolution {
  request: { kpis: string[]; rows: string[]; cols: string[]; totals: { rows: boolean; cols: boolean }; params: Record<string, string> } | null
  questions: string[]
  notes: string[]
}

export interface Evidence {
  available: boolean
  date?: string
  pairs?: string[]
  comparisons?: number
  failed?: number
  requests?: string[]
  results?: Record<string, Record<string, { nodes: number; diffs: number; violations: number; error: string | null }>>
  warehouse?: { id: string; name: string; size: string } | null
  statements?: number
  versions?: Record<string, string>
}

export interface MessageRow {
  message_id: number
  client_id: string
  typology: string | null
  market: string
  send_date: string
  is_delivered: boolean
  is_opened: boolean
  is_clicked: boolean
}

export interface InferenceTemplate {
  id: string
  alias: string
  sql: string
  accepted: boolean
  kpi: string | null
  reason: string | null
}

export interface Inference {
  available: boolean
  templates?: InferenceTemplate[]
  measures?: { id: string; expr: string; kind: string }[]
  kpis?: { id: string; formula: string; status: Status; legacy: string }[]
  filters?: { id: string; predicate: string; optional: boolean; params: Record<string, string> }[]
  grain?: { fact_rows: number; joined_rows: number; distinct_keys: number } | null
  notes?: string[]
  parity?: { bindings: number; nodes: number; compared: number; nulls: number; different: number; only_after: number }
  yaml?: string
}
