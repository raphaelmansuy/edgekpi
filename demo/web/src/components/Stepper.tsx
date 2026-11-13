const PIPELINE = ['VALIDATED', 'COMPILED', 'EXECUTED', 'ASSEMBLED', 'RECONCILED'] as const

/** The lifecycle of one run (library docs 10, "Request lifecycle"). A failure marks the first step not reached. */
export function Stepper({ states, failed = false }: { states: string[]; failed?: boolean }) {
  const reached = new Set(states)
  const firstMissing = PIPELINE.find((s) => !reached.has(s))
  return (
    <div className="stepper" data-testid="stepper" aria-label="Run lifecycle">
      {PIPELINE.map((s, i) => {
        const done = reached.has(s)
        const bad = failed && s === firstMissing
        return (
          <span key={s} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            {i > 0 && <span className="step-sep">›</span>}
            <span className={`step ${done ? 'done' : ''} ${bad ? 'failed' : ''}`} data-state={s} data-reached={done}>
              {done ? '✓' : bad ? '✕' : '·'} {s.toLowerCase()}
            </span>
          </span>
        )
      })}
    </div>
  )
}
