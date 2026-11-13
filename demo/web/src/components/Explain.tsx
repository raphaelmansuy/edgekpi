import type { Explanation } from '../api/types'
import { formatValue, memberLabel, titleCase } from '../domain/format'

function where(e: Explanation): string {
  if (e.scope.length === 0) return 'all rows, with the report filters kept'
  return e.scope.map((d, i) => `${titleCase(d)} = ${memberLabel(e.members[i] ?? null)}`).join(', ')
}

/** Why a number is what it is: its own measures, its formula, and the tempting wrong answer beside it. */
export function ExplainPanel({ e, onClose }: { e: Explanation; onClose?: () => void }) {
  const f = (v: number | null) => formatValue(v, e.format)
  const single = e.terms.length === 1 && e.formula.trim() === e.terms[0]?.measure
  return (
    <section className="explain" data-testid="explain" aria-live="polite">
      <div className="row">
        <h3 className="grow">
          Why is {e.label} {f(e.value)}?
        </h3>
        {onClose && (
          <button type="button" className="btn small" onClick={onClose}>
            Close
          </button>
        )}
      </div>
      <p className="muted small">Scope: {where(e)}</p>
      <div className="equation" data-testid="explain-terms">
        {e.terms.map((t, i) => (
          <span key={t.measure} className="row" style={{ gap: 8 }}>
            {i > 0 && <span className="arrow">{e.is_ratio ? '÷' : ','}</span>}
            <span className="term">
              <small>
                {t.measure}
                {t.kind === 'unique' ? ' · distinct' : ''}
              </small>
              <b>{formatValue(t.value, 'number')}</b>
            </span>
          </span>
        ))}
        {single ? (
          <b className="sr-only" data-testid="explain-value">{f(e.value)}</b>
        ) : (
          <>
            <span className="arrow">=</span>
            <span className="term">
              <small>{e.formula}</small>
              <b data-testid="explain-value">{f(e.value)}</b>
            </span>
          </>
        )}
      </div>
      {e.naive ? (
        <div className="compare" data-testid="explain-compare">
          <div className="right">
            <span className="small">Computed at this scope</span>
            <b>{f(e.value)}</b>
          </div>
          <div className={e.naive.differs ? 'wrong' : 'right'}>
            <span className="small">
              {e.naive.method === 'mean' ? 'Mean' : 'Sum'} of the {e.naive.children} cells by {titleCase(e.naive.dimension)}
            </span>
            <b data-testid="explain-naive">{f(e.naive.value)}</b>
          </div>
        </div>
      ) : (
        <p className="muted small" data-testid="explain-leaf">
          This is a detail cell: there is nothing finer to compare it with.
        </p>
      )}
      {e.naive?.differs && (
        <p className="small">
          {e.naive.method === 'mean'
            ? 'A rate must be recomputed from its own counts. Averaging the cells weights every cell equally, whatever its size.'
            : 'A distinct count cannot be added: one client can sit in several cells, and is counted once in the total.'}
        </p>
      )}
    </section>
  )
}
