import type { ReactNode } from 'react'
import type { AsyncState } from '../state/asyncState'
import { dataOf } from '../state/asyncState'
import { ErrorBanner } from './ErrorBanner'
import { Spinner } from './ui'

/**
 * Shows the three states of a call in one place: a spinner, the error with its Retry, or the data.
 * While a newer call runs, the last good data stays on screen, dimmed (EC-D-03).
 */
export function Remote<T>({ state, retry, children }: { state: AsyncState<T>; retry?: () => void; children: (data: T) => ReactNode }) {
  const data = dataOf(state)
  return (
    <div data-remote={state.status}>
      {state.status === 'error' && <ErrorBanner error={state.error} onRetry={retry} />}
      {data === undefined && (state.status === 'loading' || state.status === 'idle') && (
        <div className="empty"><Spinner /></div>
      )}
      {data !== undefined && <div className={state.status === 'loading' || state.status === 'error' ? 'stale' : ''}>{children(data)}</div>}
    </div>
  )
}
