import type { ReactNode } from 'react'

export interface Choice {
  id: string
  label: ReactNode
  detail?: string
}

/**
 * Asks before it tells. The learner commits to a choice, then the answer is revealed with a verdict.
 * Whatever is chosen stays chosen until "Try again", so moving between steps does not lose it.
 */
export function Predict({
  id, question, choices, correct, answer, onAnswer, children,
}: {
  id: string
  question: string
  choices: Choice[]
  correct: string
  answer: string | undefined
  onAnswer: (choice: string | null) => void
  children?: ReactNode
}) {
  const done = answer !== undefined
  return (
    <section className="predict" data-testid={`predict-${id}`} aria-labelledby={`${id}-q`}>
      <h3 id={`${id}-q`}>{question}</h3>
      <div className="choices" role="radiogroup" aria-labelledby={`${id}-q`}>
        {choices.map((c) => {
          const chosen = answer === c.id
          const state = !done ? '' : c.id === correct ? 'right' : chosen ? 'wrong' : 'dim'
          return (
            <button
              key={c.id}
              type="button"
              role="radio"
              aria-checked={chosen}
              disabled={done}
              className={`choice ${state}`}
              data-choice={c.id}
              data-state={state || undefined}
              onClick={() => onAnswer(c.id)}
            >
              <span className="choice-mark" aria-hidden>
                {!done ? '○' : c.id === correct ? '✓' : chosen ? '✕' : '○'}
              </span>
              <span>
                {c.label}
                {c.detail && <small>{c.detail}</small>}
              </span>
            </button>
          )
        })}
      </div>
      {done && (
        <div className="verdict" data-testid={`verdict-${id}`} data-correct={answer === correct} aria-live="polite">
          <div className="row">
            <strong>{answer === correct ? 'Right.' : 'Not quite. That is the tempting answer.'}</strong>
            <span className="grow" />
            <button type="button" className="btn small" onClick={() => onAnswer(null)}>
              Try again
            </button>
          </div>
          {children}
        </div>
      )}
    </section>
  )
}
