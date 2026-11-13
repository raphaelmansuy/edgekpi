import { useCallback, useEffect } from 'react'
import { CodeBlock } from '../components/CodeBlock'
import { ErrorBanner } from '../components/ErrorBanner'
import { Card, EmptyState, PageHead, Pill, Spinner } from '../components/ui'
import { canRun, describeRequest, toApiRequest } from '../domain/request'
import { dataOf } from '../state/asyncState'
import { useApp, useCatalogue } from '../state/AppState'
import { useLatest } from '../state/useLatest'
import type { BackendId } from '../api/types'

const APPROACHES: { id: BackendId; title: string; tone: 'peach' | 'lav' | 'blue'; blurb: string }[] = [
  { id: 'metric-view', title: 'Databricks metric view', tone: 'peach', blurb: 'Defined once in Unity Catalog; the report is a MEASURE() query.' },
  { id: 'malloy', title: 'Malloy', tone: 'lav', blurb: 'A source plus one query with a nest per grouping.' },
  { id: 'sql', title: 'Generated SQL', tone: 'blue', blurb: 'One statement, one scan, every grouping set.' },
]

export function BackendsScreen() {
  const { api, request, backend, setBackend } = useApp()
  const c = useCatalogue()
  const planCall = useCallback((...a: Parameters<typeof api.plan>) => api.plan(...a), [api])
  const verifyCall = useCallback((r: Parameters<typeof api.verify>[0]) => api.verify(r), [api])
  const evidenceCall = useCallback(() => api.evidence(), [api])
  const [sql, loadSql] = useLatest(planCall)
  const [malloy, loadMalloy] = useLatest(planCall)
  const [view, loadView] = useLatest(planCall)
  const [verify, runVerify] = useLatest(verifyCall)
  const [evidence, loadEvidence] = useLatest(evidenceCall)
  const ok = canRun(request).ok
  const api_request = toApiRequest(request)

  useEffect(() => {
    void loadEvidence()
  }, [loadEvidence])
  useEffect(() => {
    if (!ok) return
    void loadSql(api_request, 'sql')
    void loadMalloy(api_request, 'malloy')
    void loadView(api_request, 'metric-view')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(api_request), ok])

  if (!c) return null
  const plans = { sql, malloy, 'metric-view': view }
  const ev = dataOf(evidence)

  return (
    <>
      <PageHead title="Backends" right={<Pill tone="blue">{describeRequest(request, c)}</Pill>}>
        The same report, written three ways. The statements differ; the numbers do not. Change the report on the Report screen and come back.
      </PageHead>
      {!ok ? (
        <Card><EmptyState title="No report to compile">Pick at least one KPI on the Report screen.</EmptyState></Card>
      ) : (
        <div className="stack">
          <div className="three" data-testid="statements-three">
            {APPROACHES.map((a) => {
              const state = plans[a.id]
              const plan = dataOf(state)
              const available = c.backends.find((b) => b.id === a.id)?.available
              return (
                <Card key={a.id} title={a.title} sub={a.blurb} testId={`approach-${a.id}`} actions={<Pill tone={a.tone}>{plan ? `${plan.statements.length} statement${plan.statements.length > 1 ? 's' : ''}` : '…'}</Pill>}>
                  <div className="stack">
                    <div className="row">
                      <Pill tone={available ? 'green' : 'gray'}>{available ? 'runs here' : 'not connected here'}</Pill>
                      {plan && <span className="small muted">{plan.statements.reduce((n, s) => n + s.text.length, 0).toLocaleString('en-US')} characters</span>}
                      <span className="grow" />
                      <button type="button" className="btn small" disabled={!available} aria-pressed={backend === a.id} onClick={() => setBackend(a.id)} title={available ? 'Use this backend on the Report screen' : 'Not available here'}>
                        {backend === a.id ? 'In use' : 'Use'}
                      </button>
                    </div>
                    {state.status === 'error' && <ErrorBanner error={state.error} />}
                    {!plan && state.status === 'loading' && <Spinner />}
                    {plan?.statements.map((s, i) => (
                      <CodeBlock key={i} label={`${s.kind === 'ddl' ? 'Definition' : 'Query'} · ${s.language}`} text={s.text} testId={`code-${a.id}-${i}`} />
                    ))}
                  </div>
                </Card>
              )
            })}
          </div>

          <div className="two">
            <Card title="Do they agree?" sub="Each backend against an independent reference: one plain GROUP BY per node" testId="verify-card"
              actions={<button type="button" className="btn primary small" onClick={() => void runVerify(api_request)} disabled={verify.status === 'loading'} data-testid="verify">{verify.status === 'loading' ? 'Verifying…' : 'Verify now'}</button>}>
              {verify.status === 'idle' && <span className="muted small">Runs the report on every backend connected here and compares every value.</span>}
              {verify.status === 'loading' && <div className="row"><Spinner /> <span className="small muted">Comparing…</span></div>}
              {verify.status === 'error' && <ErrorBanner error={verify.error} />}
              {verify.status === 'success' && (
                <div className="stack" data-testid="verify-result">
                  {verify.data.outcomes.map((o) => (
                    <div key={o.label} className={`banner ${o.ok ? 'ok' : 'error'}`}>
                      <div style={{ flex: 1 }}><strong>{o.label}</strong>
                        <p>{o.ok ? `matches the reference on all ${o.nodes} nodes` : (o.error ?? `${o.diffs} differences, ${o.violations} violations`)}</p></div>
                      <Pill tone={o.ok ? 'green' : 'pink'}>{o.ok ? '✓ match' : '✕ differ'}</Pill>
                    </div>
                  ))}
                  {verify.data.skipped.map((s) => <div key={s.id} className="banner info"><div><strong>{s.label}</strong><p>Skipped: {s.reason}</p></div></div>)}
                </div>
              )}
            </Card>

            <Card title="Recorded warehouse run" sub="Not run live in this demo" testId="evidence-card">
              {!ev || !ev.available ? <EmptyState title="No recorded run">Run <code>scripts/record_evidence.py --databricks</code> to create one.</EmptyState> : (
                <div className="stack">
                  <div className="row">
                    <Pill tone={ev.failed === 0 ? 'green' : 'pink'}>{ev.comparisons} comparisons · {ev.failed} differences</Pill>
                    <span className="small muted">{ev.date} · {ev.warehouse?.name} ({ev.warehouse?.size})</span>
                  </div>
                  <div className="evidence-grid" style={{ gridTemplateColumns: `1.6fr repeat(${ev.pairs?.length ?? 0}, 1fr)` }} data-testid="evidence-grid">
                    <div className="h">request</div>
                    {ev.pairs?.map((p) => <div key={p} className="h">{p.replace(' on ', ' · ').replace('metric view', 'view')}</div>)}
                    {ev.requests?.map((r) => (
                      <Row key={r} name={r} pairs={ev.pairs ?? []} results={ev.results?.[r] ?? {}} />
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}
    </>
  )
}

function Row({ name, pairs, results }: { name: string; pairs: string[]; results: Record<string, { diffs: number; violations: number; error: string | null }> }) {
  return (
    <>
      <div className="mono">{name}</div>
      {pairs.map((p) => {
        const r = results[p]
        const ok = r && !r.error && r.diffs === 0 && r.violations === 0
        return <div key={p} className={ok ? 'ok' : ''}>{ok ? '✓' : '✕'}</div>
      })}
    </>
  )
}
