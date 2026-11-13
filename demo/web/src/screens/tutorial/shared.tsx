import { useCallback } from 'react'
import type { EdgeKpiApi } from '../../api/client'
import type { ApiResult, Catalogue, Explanation, MessageRow, ReportRequest, RunResult } from '../../api/types'
import { useAutoLatest } from '../../state/useLatest'

/** What every step receives. A step never reaches for the app state itself (Interface Segregation). */
export interface StepProps {
  api: EdgeKpiApi
  catalogue: Catalogue
  answers: Record<string, string>
  answer: (id: string, choice: string | null) => void
  goTo: (step: number) => void
  openReport: (request: ReportRequest) => void
}

export interface RunAndExplain {
  run: RunResult
  explain: Explanation
}

/** A report and the explanation of its grand total, fetched together so a step shows both or an error. */
export async function runAndExplain(api: EdgeKpiApi, request: ReportRequest, kpi: string): Promise<ApiResult<RunAndExplain>> {
  const [run, explain] = await Promise.all([api.run(request, 'sql'), api.explain(request, kpi, [], [], 'sql')])
  if (!run.ok) return run
  if (!explain.ok) return explain
  return { ok: true, data: { run: run.data, explain: explain.data } }
}

export function useRunAndExplain(api: EdgeKpiApi, request: ReportRequest, kpi: string) {
  const call = useCallback(() => runAndExplain(api, request, kpi), [api, request, kpi])
  return useAutoLatest(call, JSON.stringify([request, kpi]))
}

export function useMessages(api: EdgeKpiApi) {
  const call = useCallback((): Promise<ApiResult<{ rows: MessageRow[] }>> => api.messages(), [api])
  return useAutoLatest(call, 'messages')
}

export const noop = () => undefined
