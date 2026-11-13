import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Explanation, Member, Plan, RunResult } from '../api/types'
import { Builder } from '../components/Builder'
import { CodeBlock } from '../components/CodeBlock'
import { ErrorBanner } from '../components/ErrorBanner'
import { ExplainPanel } from '../components/Explain'
import { Pivot, type Selection } from '../components/Pivot'
import { Stepper } from '../components/Stepper'
import { Card, EmptyState, PageHead, Pill, Spinner } from '../components/ui'
import { buildPivot } from '../domain/pivot'
import { canRun, describeRequest, requestKey, toApiRequest } from '../domain/request'
import { dataOf } from '../state/asyncState'
import { useApp, useCatalogue } from '../state/AppState'
import { useLatest } from '../state/useLatest'

const DEBOUNCE_MS = 250

export function ReportScreen() {
  const { api, request, setRequest, backend, setBackend } = useApp()
  const catalogue = useCatalogue()
  const runCall = useCallback((...a: Parameters<typeof api.run>) => api.run(...a), [api])
  const planCall = useCallback((...a: Parameters<typeof api.plan>) => api.plan(...a), [api])
  const explainCall = useCallback((...a: Parameters<typeof api.explain>) => api.explain(...a), [api])
  const [result, runReport] = useLatest(runCall)
  const [plan, loadPlan] = useLatest(planCall)
  const [explanation, loadExplanation] = useLatest(explainCall)
  const [tab, setTab] = useState<string | null>(null)
  const [selected, setSelected] = useState<Selection | null>(null)
  const [showSql, setShowSql] = useState(false)
  const startedKey = useRef<string | null>(null)
  const [settledKey, setSettledKey] = useState<string | null>(null)

  const key = requestKey(request, backend)
  const execute = useCallback(() => {
    if (!canRun(request).ok) return
    setSelected(null)
    startedKey.current = key
    void runReport(toApiRequest(request), backend).then(() => {
      if (startedKey.current === key) setSettledKey(key)
    })
    if (showSql) void loadPlan(toApiRequest(request), backend)
  }, [request, backend, runReport, loadPlan, showSql, key])

  // Run when the request or the backend changes, after a short pause; the latest answer wins (EC-D-04, EC-D-19).
  useEffect(() => {
    if (!catalogue) return
    const t = setTimeout(execute, DEBOUNCE_MS)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, catalogue])

  useEffect(() => {
    if (showSql) void loadPlan(toApiRequest(request), backend)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showSql, key])

  // with no KPI there is no report: an older table would answer a question nobody asked any more
  const runnable = canRun(request).ok
  const run: RunResult | undefined = runnable ? dataOf(result) : undefined
  const loading = result.status === 'loading'
  // the table on screen answers an older request until the newest has settled: dim it at once, not after the pause
  const outdated = loading || result.status === 'error' || settledKey !== key
  const kpiId = run && (tab && run.kpis.some((k) => k.id === tab) ? tab : run.kpis[0]?.id)
  const pivot = useMemo(() => (run && kpiId ? buildPivot(run, kpiId) : null), [run, kpiId])

  const select = (scope: string[], members: Member[]) => {
    setSelected({ scope, members })
    if (kpiId) void loadExplanation(toApiRequest(request), kpiId, scope, members, backend)
  }
  const explained: Explanation | undefined = selected ? (explanation.status === 'success' ? explanation.data : undefined) : undefined

  if (!catalogue) return null
  return (
    <>
      <PageHead title="Report" right={<Pill tone="blue">{describeRequest(request, catalogue)}</Pill>}>
        Choose KPIs, rows and columns. Every total is recomputed from its own measures, then checked against the arithmetic of its parts.{' '}
        <a className="tour-link" href="#/tutorial" data-testid="tour-link">New here? Take the guided tutorial.</a>
      </PageHead>
      <div className="report">
        <aside className="builder card">
          <div className="card-body">
            <Builder catalogue={catalogue} request={request} onChange={setRequest} backend={backend} onBackend={setBackend} onRun={execute} running={loading} />
          </div>
        </aside>

        <div className="stack" style={{ minWidth: 0 }}>
          <Card flush testId="result-card">
            <div className="result-top">
              <div className="row">
                <div className={`grow ${loading || settledKey !== key ? 'pending' : ''}`}>
                  {!runnable ? <span className="muted small">No run yet</span> : result.status === 'error' ? <Stepper states={result.error.states} failed /> : run ? <Stepper states={run.states} /> : <span className="muted small">No run yet</span>}
                </div>
                {loading && <span className="row small muted" data-testid="loading"><Spinner /> running…</span>}
                {run && result.status !== 'error' && !loading && (
                  <Pill tone={run.violations.length === 0 ? 'green' : 'pink'}>
                    {run.violations.length === 0 ? '✓ 0 violations' : `✕ ${run.violations.length} violations`}
                  </Pill>
                )}
              </div>
              {run && result.status !== 'error' && <span className="muted small" data-testid="estimate">{run.estimate} · backend {run.backend}</span>}
              {run && result.status === 'error' && <span className="muted small" data-testid="stale-note">Showing the last successful result, dimmed.</span>}
              {runnable && result.status === 'error' && <ErrorBanner error={result.error} onRetry={execute} />}
            </div>

            {run && (
              <>
                <div className="tabs" role="tablist" aria-label="KPI">
                  {run.kpis.map((k) => (
                    <button key={k.id} role="tab" aria-selected={k.id === kpiId} onClick={() => { setTab(k.id); setSelected(null) }}>
                      {k.label}
                    </button>
                  ))}
                </div>
                <div className={outdated ? 'stale' : ''} data-testid="result-body" data-stale={outdated}>
                  {run.nodes.length === 0 ? (
                    <EmptyState title="No rows match">Nothing satisfies the filters, so there is nothing to total. This is the correct answer, not a failure.</EmptyState>
                  ) : (
                    pivot && <Pivot pivot={pivot} selected={selected} onSelect={(c) => select(c.scope, c.members)} />
                  )}
                  {selected && explanation.status === 'loading' && <div className="empty"><Spinner label="Explaining" /></div>}
                  {selected && explanation.status === 'error' && <div style={{ padding: '0 18px 18px' }}><ErrorBanner error={explanation.error} /></div>}
                  {explained && <ExplainPanel e={explained} onClose={() => setSelected(null)} />}
                </div>
                {run.violations.length > 0 && (
                  <div style={{ padding: '0 18px 18px' }} data-testid="violations">
                    {run.violations.map((v, i) => (
                      <div key={i} className="banner error"><span className="code">{v.code}</span><p>{v.message}</p></div>
                    ))}
                  </div>
                )}
              </>
            )}
            {!runnable && <EmptyState title="No report yet">Pick at least one KPI on the left.</EmptyState>}
            {runnable && !run && result.status === 'loading' && <div className="empty"><Spinner /></div>}
            {runnable && !run && result.status === 'idle' && <EmptyState title="Ready">Pick KPIs on the left. The report runs as you change it.</EmptyState>}
          </Card>

          <Card title="Statement" sub="What the chosen backend runs for this report" actions={<button type="button" className="btn small" aria-expanded={showSql} onClick={() => setShowSql((s) => !s)} data-testid="toggle-sql">{showSql ? 'Hide' : 'Show'}</button>}>
            {showSql ? <StatementView plan={dataOf(plan)} error={plan.status === 'error' ? plan.error : null} /> : <span className="muted small">Hidden. Parameters stay bound: they never appear in the text.</span>}
          </Card>
        </div>
      </div>
    </>
  )
}

function StatementView({ plan, error }: { plan: Plan | undefined; error: { code: string; message: string; states: string[] } | null }) {
  if (error) return <ErrorBanner error={error} />
  if (!plan) return <Spinner />
  return (
    <div className="stack" data-testid="statements">
      {plan.statements.map((s, i) => (
        <CodeBlock key={i} label={`${s.kind === 'ddl' ? 'Definition (once per model version)' : 'Query'} · ${s.language}`} text={s.text} testId={`statement-${i}`} />
      ))}
      {plan.bindings.length > 0 && <p className="small muted">Bound: {plan.bindings.map((b) => `${b.name} = ${String(b.value)}`).join(', ')}</p>}
    </div>
  )
}
