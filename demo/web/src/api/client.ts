import type {
  ApiResult, BackendId, Catalogue, Evidence, Explanation, Inference, MalloyEngine, Member, MessageRow, Plan, ReportRequest, Resolution, RunResult, Verification,
} from './types'

/** Everything the screens need from the service. Screens depend on this interface, never on `fetch` (Dependency Inversion). */
export interface EdgeKpiApi {
  catalogue(): Promise<ApiResult<Catalogue>>
  run(request: ReportRequest, backend: BackendId): Promise<ApiResult<RunResult>>
  plan(request: ReportRequest, backend: BackendId, engine?: MalloyEngine): Promise<ApiResult<Plan>>
  explain(request: ReportRequest, kpi: string, scope: string[], members: Member[], backend: BackendId): Promise<ApiResult<Explanation>>
  verify(request: ReportRequest): Promise<ApiResult<Verification>>
  resolve(proposal: Record<string, unknown>): Promise<ApiResult<Resolution>>
  evidence(): Promise<ApiResult<Evidence>>
  inference(): Promise<ApiResult<Inference>>
  messages(): Promise<ApiResult<{ rows: MessageRow[] }>>
}

type Fetch = typeof fetch

const UNREACHABLE = {
  code: 'SERVICE_UNREACHABLE',
  message: 'The edgekpi service did not answer. Start it with `python -m edgekpi.server` and retry.',
  states: [],
}

export function createHttpApi(fetchImpl: Fetch = (...args) => fetch(...args), base = '/api'): EdgeKpiApi {
  async function call<T>(path: string, body?: unknown): Promise<ApiResult<T>> {
    let response: Response
    try {
      response = await fetchImpl(`${base}${path}`, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    } catch {
      return { ok: false, error: UNREACHABLE }
    }
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      return { ok: false, error: { code: 'BAD_RESPONSE', message: `The service answered with something that is not JSON (HTTP ${response.status}).`, states: [] } }
    }
    const data = payload as { ok?: boolean; error?: { code: string; message: string; states?: string[] } }
    if (data.ok === false && data.error) return { ok: false, error: { code: data.error.code, message: data.error.message, states: data.error.states ?? [] } }
    if (!response.ok) return { ok: false, error: { code: 'HTTP_' + response.status, message: `Unexpected HTTP status ${response.status}.`, states: [] } }
    return { ok: true, data: payload as T }
  }

  return {
    catalogue: () => call('/catalogue'),
    run: (request, backend) => call('/run', { request, backend }),
    plan: (request, backend, engine) => call('/plan', { request, backend, ...(engine ? { engine } : {}) }),
    explain: (request, kpi, scope, members, backend) => call('/explain', { request, kpi, scope, members, backend }),
    verify: (request) => call('/verify', { request }),
    resolve: (proposal) => call('/resolve', { proposal }),
    evidence: () => call('/evidence'),
    inference: () => call('/inference'),
    messages: () => call('/messages'),
  }
}
