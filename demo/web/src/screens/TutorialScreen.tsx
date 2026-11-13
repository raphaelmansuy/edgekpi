import { useEffect, useState, type ComponentType } from 'react'
import { PageHead } from '../components/ui'
import { STEPS, parseStep } from '../domain/tutorial'
import type { ReportRequest } from '../api/types'
import { go } from '../state/route'
import { useApp, useCatalogue } from '../state/AppState'
import { LayoutStep, DefineStep, OldStep, VerifyStep, WaysStep, YoursStep } from './tutorial/fix'
import { ReachStep } from './tutorial/reach'
import { MoveStep, SqlStep } from './tutorial/sql'
import type { StepProps } from './tutorial/shared'
import { DataStep, InsideStep, PredictStep } from './tutorial/story'

const BODIES: Record<string, ComponentType<StepProps>> = {
  data: DataStep, predict: PredictStep, inside: InsideStep, reach: ReachStep, old: OldStep,
  define: DefineStep, ways: WaysStep, sqlhow: SqlStep, moveover: MoveStep, layout: LayoutStep, verify: VerifyStep, yours: YoursStep,
}

/** A guided path through the problem and its fix. Every number on it is computed live by the library. */
export function TutorialScreen({ param }: { param: string | null }) {
  const { api, answers, answer, setRequest } = useApp()
  const catalogue = useCatalogue()
  const { step, adjusted } = parseStep(param, STEPS.length)
  const [visited, setVisited] = useState<Set<number>>(() => new Set([step]))
  useEffect(() => {
    setVisited((v) => (v.has(step) ? v : new Set(v).add(step)))
    window.scrollTo({ top: 0 })
  }, [step])
  if (!catalogue) return null
  const info = STEPS[step - 1]!
  const Body = BODIES[info.id]!
  const props: StepProps = {
    api, catalogue, answers, answer,
    goTo: (n) => go('tutorial', n),
    openReport: (request: ReportRequest) => {
      setRequest(request)
      go('report')
    },
  }
  const percent = Math.round((step / STEPS.length) * 100)
  return (
    <>
      <PageHead title="Tutorial">
        Why totals break, and how to fix them. {STEPS.length} short steps, about fifteen minutes. Nothing here is a picture: every number is
        computed live by the library on thirteen example messages.
      </PageHead>
      {adjusted && <div className="notice" role="note" data-testid="step-notice">There is no step “{param}”. Showing step {step}.</div>}
      <div className="tutorial">
        <nav className="outline" aria-label="Tutorial steps" data-testid="outline">
          <ol>
            {STEPS.map((s, i) => {
              const n = i + 1
              const state = n === step ? 'current' : visited.has(n) ? 'done' : 'todo'
              return (
                <li key={s.id}>
                  <a href={`#/tutorial/${n}`} aria-current={n === step ? 'step' : undefined} data-step={n} data-state={state}>
                    <span className="num">{state === 'done' ? '✓' : n}</span>
                    <span>{s.title}</span>
                  </a>
                </li>
              )
            })}
          </ol>
        </nav>
        <section className="lesson card" data-testid="lesson" data-step={info.id}>
          <header className="lesson-head">
            <div className="row">
              <span className="small muted" data-testid="step-count">Step {step} of {STEPS.length}</span>
              <span className="grow" />
              <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={STEPS.length} aria-valuenow={step} aria-label="Progress"><i style={{ width: `${percent}%` }} /></div>
            </div>
            <h2 data-testid="step-title">{info.title}</h2>
            <p className="learn"><span aria-hidden>🎯</span> <strong>You will see that:</strong> {info.learn}</p>
          </header>
          <div className="lesson-body" key={info.id}>
            <Body {...props} />
          </div>
          <footer className="lesson-foot">
            {step > 1 ? <a className="btn" href={`#/tutorial/${step - 1}`} data-testid="back">← Back</a> : <span />}
            {step < STEPS.length ? (
              <a className="btn primary" href={`#/tutorial/${step + 1}`} data-testid="next">Next: {STEPS[step]?.title} →</a>
            ) : (
              <a className="btn primary" href="#/report" data-testid="finish">Finish: open the Report →</a>
            )}
          </footer>
        </section>
      </div>
    </>
  )
}
