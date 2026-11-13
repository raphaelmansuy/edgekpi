import type { ApiError } from '../api/types'

/** An error is a sentence with its code, never a stack trace (EC-D-02). */
const DOMAIN = /^(REQ|DEF|GRAIN|INFER|MALLOY)_/

export function ErrorBanner({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  // Asking again cannot fix a refused request: only the service being down, slow or confused can be retried (EC-D-02).
  const retriable = !DOMAIN.test(error.code) && error.code !== 'ENGINE_UNAVAILABLE'
  return (
    <div className="banner error" role="alert" data-testid="error-banner">
      <div style={{ flex: 1 }}>
        <span className="code" data-testid="error-code">
          {error.code}
        </span>
        <p>{error.message}</p>
        {!retriable && <p className="small muted">Change the report and it runs again.</p>}
      </div>
      {onRetry && retriable && (
        <button type="button" className="btn small" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
