import { useCallback, useEffect, useState } from 'react'
import { CodeBlock } from '../components/CodeBlock'
import { ErrorBanner } from '../components/ErrorBanner'
import { Card, EmptyState, PageHead, Pill, Spinner, StatusPill } from '../components/ui'
import { dataOf } from '../state/asyncState'
import { useApp } from '../state/AppState'
import { useLatest } from '../state/useLatest'

export function MigrationScreen() {
  const { api } = useApp()
  const call = useCallback(() => api.inference(), [api])
  const [state, load] = useLatest(call)
  const [selected, setSelected] = useState<string | null>(null)
  const [showYaml, setShowYaml] = useState(false)
  useEffect(() => {
    void load()
  }, [load])

  const data = dataOf(state)
  const current = data?.templates?.find((t) => t.id === selected) ?? data?.templates?.[0]

  return (
    <>
      <PageHead title="Migration">
        Legacy KPIs are SQL templates with a grouping slot. Each is read as relational algebra, rewritten inside its aggregation, and proved against the legacy numbers. What cannot be proved is refused, with a reason.
      </PageHead>
      {state.status === 'loading' && !data && <Card><div className="empty"><Spinner /> <p>Reading templates and comparing 200 values…</p></div></Card>}
      {state.status === 'error' && <ErrorBanner error={state.error} onRetry={() => void load()} />}
      {data && !data.available && <Card><EmptyState title="No templates configured">Start the service with a templates file to see the migration.</EmptyState></Card>}
      {data?.available && data.templates && current && (
        <div className="stack">
          <div className="stats" data-testid="parity">
            <div className="stat" style={{ background: 'var(--green)', borderColor: 'var(--green-line)', color: 'var(--green-ink)' }}><b>{data.templates.filter((t) => t.accepted).length}</b><span>of {data.templates.length} templates accepted</span></div>
            <div className="stat" style={{ background: 'var(--pink)', borderColor: 'var(--pink-line)', color: 'var(--pink-ink)' }}><b>{data.templates.filter((t) => !t.accepted).length}</b><span>refused, with a reason</span></div>
            <div className="stat" style={{ background: 'var(--blue)', borderColor: 'var(--blue-line)', color: 'var(--blue-ink)' }}><b data-testid="compared">{data.parity?.compared}</b><span>legacy values compared</span></div>
            <div className="stat" style={{ background: data.parity?.different === 0 ? 'var(--green)' : 'var(--pink)', borderColor: 'var(--green-line)', color: 'var(--green-ink)' }}><b data-testid="different">{data.parity?.different}</b><span>values that differ</span></div>
            <div className="stat" style={{ background: 'var(--yellow)', borderColor: 'var(--yellow-line)', color: 'var(--yellow-ink)' }}><b>{data.parity?.only_after}</b><span>values only after migration</span></div>
          </div>

          <div className="master-detail">
            <Card flush title="Registry templates" testId="templates">
              <div className="list">
                {data.templates.map((t) => (
                  <button key={t.id} type="button" aria-pressed={t.id === current.id} onClick={() => setSelected(t.id)} data-template={t.id}>
                    <div className="row"><strong className="mono">{t.id}</strong><span className="grow" /><Pill tone={t.accepted ? 'green' : 'pink'}>{t.accepted ? '✓ accepted' : '✕ refused'}</Pill></div>
                    <span className="small muted">{t.accepted ? `becomes KPI ${t.kpi}` : t.reason?.split(':')[0]}</span>
                  </button>
                ))}
              </div>
            </Card>

            <div className="stack" data-testid="template-detail">
              <Card title="Legacy template" sub={current.id}><CodeBlock text={current.sql} /></Card>
              {current.accepted ? (
                <Card title="Inferred" sub="Measures named, formula written, status draft until an owner confirms">
                  {(() => {
                    const kpi = data.kpis?.find((k) => k.id === current.kpi)
                    return kpi && (
                      <div className="stack">
                        <div className="row"><strong>{kpi.id}</strong><StatusPill status={kpi.status} /><code className="mono">{kpi.formula}</code></div>
                        <table className="table">
                          <tbody>
                            {data.measures?.filter((m) => new RegExp(`\\b${m.id}\\b`).test(kpi.formula)).map((m) => (
                              <tr key={m.id}><td className="mono">{m.id}</td><td><code className="mono">{m.expr}</code></td><td><Pill tone={m.kind === 'unique' ? 'peach' : 'blue'}>{m.kind}</Pill></td></tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )
                  })()}
                </Card>
              ) : (
                <div className="stack">
                  <div className="banner error" data-testid="refusal"><div><span className="code">{current.reason?.split(':')[0]}</span><p>{current.reason?.split(': ').slice(1).join(': ')}</p></div></div>
                  <Card title="What happens next" testId="refusal-next">
                    <ul className="small" style={{ margin: 0, paddingLeft: 18, lineHeight: 1.7 }}>
                      <li>The other templates are not affected: each one is judged alone.</li>
                      <li>This KPI stays a legacy query until it is rewritten, for example over a second fact table.</li>
                      <li>Nothing was guessed: a number that cannot be proved equal is not migrated.</li>
                    </ul>
                  </Card>
                </div>
              )}
            </div>
          </div>

          <div className="two">
            <Card title="Proof" sub="Legacy templates and the migrated model, value by value">
              <p>
                {data.parity?.bindings} parameter bindings, {data.parity?.nodes} nodes. {data.parity?.compared} legacy values compared ({data.parity?.nulls} blank where a denominator is zero): <strong>{data.parity?.different} differ</strong>.
              </p>
              <p className="small muted" style={{ marginTop: 8 }}>
                The {data.parity?.only_after} extra values are the one deliberate difference: moving <code>WHERE is_delivered</code> into the measure turns “no row” into 0.
              </p>
              {data.grain && <p className="small muted" style={{ marginTop: 8 }}>Joins keep the grain: {data.grain.fact_rows} messages stay {data.grain.joined_rows} rows.</p>}
              {data.notes && data.notes.length > 0 && <ul className="small" style={{ marginTop: 8, paddingLeft: 18 }}>{data.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
            </Card>
            <Card title="Inferred model" actions={<button type="button" className="btn small" aria-expanded={showYaml} onClick={() => setShowYaml((s) => !s)}>{showYaml ? 'Hide YAML' : 'Show YAML'}</button>}>
              {showYaml && data.yaml ? <CodeBlock text={data.yaml} testId="yaml" /> : (
                <div className="stack" style={{ gap: 6 }}>
                  {data.measures?.map((m) => <div key={m.id} className="row"><span className="mono" style={{ minWidth: 28 }}>{m.id}</span><code className="mono muted">{m.expr}</code></div>)}
                  <p className="small muted">Three spellings of a conditional count, <code>COUNT_IF</code>, <code>FILTER</code> and <code>SUM(CASE…)</code>, are one measure.</p>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}
    </>
  )
}
