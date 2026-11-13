import { useCallback, useState } from 'react'
import type { ApiResult, RunResult } from '../api/types'
import { Card, PageHead, Pill, Spinner } from '../components/ui'
import { SCENARIOS, scenarioRequest, summarise, type Scenario } from '../domain/scenarios'
import { useApp } from '../state/AppState'

type Outcome = { status: 'pass' | 'fail'; text: string }

function judge(s: Scenario, result: ApiResult<RunResult>): Outcome {
  if ('error' in s.expect) {
    if (result.ok) return { status: 'fail', text: `expected ${s.expect.error}, got a result` }
    return result.error.code === s.expect.error ? { status: 'pass', text: `${result.error.code}: ${result.error.message}` } : { status: 'fail', text: `expected ${s.expect.error}, got ${result.error.code}` }
  }
  if (!result.ok) return { status: 'fail', text: `${result.error.code}: ${result.error.message}` }
  return s.expect.ok(result.data) ? { status: 'pass', text: `${s.expect.describe} (${result.data.nodes.length} nodes)` } : { status: 'fail', text: `expected ${s.expect.describe}` }
}

/** Each case below is an edge case of the library, run for real. The card turns green when the service answers as it should. */
export function LabScreen() {
  const { api } = useApp()
  const [outcomes, setOutcomes] = useState<Record<string, Outcome | 'running'>>({})
  const runOne = useCallback(async (s: Scenario) => {
    setOutcomes((o) => ({ ...o, [s.id]: 'running' }))
    const result = await api.run(scenarioRequest(s), s.backend)
    setOutcomes((o) => ({ ...o, [s.id]: judge(s, result) }))
  }, [api])
  const runAll = async () => {
    for (const s of SCENARIOS) await runOne(s)
  }
  const done = Object.values(outcomes).filter((o) => o !== 'running')
  const passed = done.filter((o) => o.status === 'pass').length

  return (
    <>
      <PageHead title="Edge-case lab" right={<div className="row">{done.length > 0 && <Pill tone={passed === done.length ? 'green' : 'pink'} title="Cases answered as expected">{passed}/{done.length} as expected</Pill>}<button type="button" className="btn primary" onClick={() => void runAll()} data-testid="run-all">Run all {SCENARIOS.length}</button></div>}>
        Things that go wrong on purpose. A correct service refuses, or answers honestly, and always says which.
      </PageHead>
      <div className="scenarios" data-testid="scenarios">
        {SCENARIOS.map((s) => {
          const o = outcomes[s.id]
          return (
            <Card key={s.id} testId={`scenario-${s.id}`}>
              <div className="scenario" style={{ padding: 0 }}>
                <div className="row"><Pill tone="lav">{s.ec}</Pill><span className="grow" /><span className="small muted">{s.backend}</span></div>
                <strong>{s.title}</strong>
                <span className="small muted">{s.why}</span>
                <code className="mono small" style={{ color: 'var(--ink-2)', overflowWrap: 'anywhere' }} data-testid="request-line">{summarise(s.request)}</code>
                {o === 'running' ? <div className="result"><Spinner /> running…</div> : o ? <div className={`result ${o.status}`} data-outcome={o.status}>{o.status === 'pass' ? '✓ ' : '✕ '}{o.text}</div> : null}
                <div><button type="button" className="btn small" onClick={() => void runOne(s)}>Run</button></div>
              </div>
            </Card>
          )
        })}
      </div>
    </>
  )
}
