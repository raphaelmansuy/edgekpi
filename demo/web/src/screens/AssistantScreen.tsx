import { useCallback, useEffect, useState } from 'react'
import { Card, PageHead, Pill, Spinner } from '../components/ui'
import { CodeBlock } from '../components/CodeBlock'
import { ErrorBanner } from '../components/ErrorBanner'
import { dataOf } from '../state/asyncState'
import { go } from '../state/route'
import { useApp } from '../state/AppState'
import { useLatest } from '../state/useLatest'
import { defaultRequest } from '../domain/request'

const split = (text: string) => text.split(',').map((s) => s.trim()).filter(Boolean)

const EXAMPLES = [
  { id: 'labels', title: 'Labels and a typo', kpis: 'Delivery Rate, Message Sent', rows: 'Typology', cols: 'markt' },
  { id: 'ambiguous', title: 'An ambiguous word', kpis: 'rate', rows: 'colour', cols: '' },
  { id: 'hostile', title: 'Text that tries to give orders', kpis: 'ignore previous instructions; DROP TABLE message', rows: '<img src=x onerror=alert(1)>', cols: '' },
]

/** The resolver that sits behind an assistant. No language model is called here: this is what its output goes through. */
export function AssistantScreen() {
  const { api, setRequest } = useApp()
  const call = useCallback((p: Record<string, unknown>) => api.resolve(p), [api])
  const [state, resolve] = useLatest(call)
  const [kpis, setKpis] = useState('Delivery Rate, Message Sent')
  const [rows, setRows] = useState('Typology')
  const [cols, setCols] = useState('markt')
  useEffect(() => {
    void resolve({ kpis: split('Delivery Rate, Message Sent'), rows: split('Typology'), cols: split('markt') })
  }, [resolve])
  const submit = () => void resolve({ kpis: split(kpis), rows: split(rows), cols: split(cols) })
  const out = dataOf(state)

  const open = () => {
    if (!out?.request) return
    setRequest({ ...defaultRequest(), kpis: out.request.kpis, rows: out.request.rows, cols: out.request.cols, totals: out.request.totals, params: out.request.params })
    go('report')
  }

  return (
    <>
      <PageHead title="Assistant">
        An assistant may propose a report. It may not execute one, name a column or write SQL. Whatever it proposes goes through this resolver: exact names pass, near misses are noted, ambiguity becomes a question.
      </PageHead>
      <div className="banner info" style={{ marginBottom: 16 }} role="note"><div><strong>No language model is called in this demo.</strong><p>Type what a model might propose. The resolver is the part of the library that stands between it and the data.</p></div></div>
      <div className="two">
        <Card title="A proposal" sub="Loose names, separated by commas">
          <form className="stack" onSubmit={(e) => { e.preventDefault(); submit() }} aria-label="Proposal">
            <label className="field"><span className="label">KPIs</span><input className="input" value={kpis} onChange={(e) => setKpis(e.target.value)} aria-label="KPIs" /></label>
            <label className="field"><span className="label">Rows</span><input className="input" value={rows} onChange={(e) => setRows(e.target.value)} aria-label="Rows" /></label>
            <label className="field"><span className="label">Columns</span><input className="input" value={cols} onChange={(e) => setCols(e.target.value)} aria-label="Columns" /></label>
            <div className="row">
              <button type="submit" className="btn primary" data-testid="resolve">Resolve</button>
              {EXAMPLES.map((x) => (
                <button key={x.id} type="button" className="btn small" data-example={x.id} onClick={() => { setKpis(x.kpis); setRows(x.rows); setCols(x.cols); void resolve({ kpis: split(x.kpis), rows: split(x.rows), cols: split(x.cols) }) }}>{x.title}</button>
              ))}
            </div>
          </form>
        </Card>

        <Card title="Resolution" testId="resolution">
          {state.status === 'idle' && <span className="muted small">Resolve a proposal to see what the library would do with it.</span>}
          {state.status === 'loading' && !out && <Spinner />}
          {state.status === 'error' && <ErrorBanner error={state.error} />}
          {out && (
            <div className="stack">
              {out.notes.length > 0 && (
                <div className="stack" style={{ gap: 6 }} data-testid="notes">
                  <span className="label small muted">Read as</span>
                  {out.notes.map((n) => <div key={n} className="banner ok"><div>{n}</div></div>)}
                </div>
              )}
              {out.questions.length > 0 && (
                <div className="stack" style={{ gap: 6 }} data-testid="questions">
                  <span className="label small muted">Asked instead of guessing</span>
                  {out.questions.map((q) => <div key={q} className="banner warn"><div>{q}</div></div>)}
                </div>
              )}
              {out.request ? (
                <div className="stack" data-testid="resolved-request">
                  <div className="row"><Pill tone="green">✓ valid request</Pill></div>
                  <CodeBlock text={JSON.stringify(out.request, null, 2)} />
                  <button type="button" className="btn primary" onClick={open} data-testid="open-report">Open in Report</button>
                </div>
              ) : (
                <div className="row"><Pill tone="yellow">no request yet</Pill><span className="small muted">Answer the questions by naming a known KPI or dimension.</span></div>
              )}
            </div>
          )}
        </Card>
      </div>
      <div style={{ marginTop: 20 }}>
        <Card title="How the resolver decides" sub="The same rules the library applies to any assistant's output" testId="rules">
          <table className="table">
            <thead><tr><th>The assistant wrote</th><th>The resolver</th><th>Why</th></tr></thead>
            <tbody>
              <tr><td className="mono">delivery_rate</td><td><Pill tone="green">accepts</Pill></td><td className="muted">an exact id: nothing to interpret</td></tr>
              <tr><td className="mono">Delivery Rate</td><td><Pill tone="green">accepts, and says so</Pill></td><td className="muted">an exact label, any case: it is what people say</td></tr>
              <tr><td className="mono">markt</td><td><Pill tone="green">accepts, and says so</Pill></td><td className="muted">one close match (similarity 0.8 or more): a typo, not a choice</td></tr>
              <tr><td className="mono">rate</td><td><Pill tone="yellow">asks</Pill></td><td className="muted">several KPIs are close: guessing would change a number</td></tr>
              <tr><td className="mono">colour</td><td><Pill tone="yellow">asks</Pill></td><td className="muted">nothing is close: the library never invents a name</td></tr>
              <tr><td className="mono">a date like 2026-02-30</td><td><Pill tone="pink">refuses</Pill></td><td className="muted">a resolved request is validated like any other</td></tr>
            </tbody>
          </table>
        </Card>
      </div>
    </>
  )
}
