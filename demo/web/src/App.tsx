import type { EdgeKpiApi } from './api/client'
import { ErrorBanner } from './components/ErrorBanner'
import { CodeBlock } from './components/CodeBlock'
import { Card, Spinner } from './components/ui'
import { AppProvider, useApp } from './state/AppState'
import { ROUTES, useHashRoute, type RouteId } from './state/route'
import { TutorialScreen } from './screens/TutorialScreen'
import { AssistantScreen } from './screens/AssistantScreen'
import { BackendsScreen } from './screens/BackendsScreen'
import { CatalogueScreen } from './screens/CatalogueScreen'
import { LabScreen } from './screens/LabScreen'
import { MigrationScreen } from './screens/MigrationScreen'
import { ReportScreen } from './screens/ReportScreen'

const SCREENS: Record<RouteId, (props: { param: string | null }) => JSX.Element | null> = {
  tutorial: TutorialScreen,
  report: ReportScreen,
  catalogue: CatalogueScreen,
  backends: BackendsScreen,
  migration: MigrationScreen,
  assistant: AssistantScreen,
  lab: LabScreen,
}

function Shell() {
  const { route, unknown, param } = useHashRoute()
  const { catalogue, reloadCatalogue } = useApp()
  const Screen = SCREENS[route]
  const tone = catalogue.status === 'success' ? '' : catalogue.status === 'error' ? 'bad' : 'wait'
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden>Σ</span>
          edgekpi <small>one definition · three backends</small>
        </div>
        <nav className="nav" aria-label="Screens">
          {ROUTES.map((r) => (
            <a key={r.id} href={`#/${r.id}`} aria-current={r.id === route ? 'page' : undefined} title={r.hint}>
              {r.label}
            </a>
          ))}
        </nav>
        <span className="service-pill" data-testid="service-status">
          <span className={`dot ${tone}`} />
          {catalogue.status === 'success' ? `service ok · ${catalogue.data.model} ${catalogue.data.version}` : catalogue.status === 'error' ? 'service unreachable' : 'connecting…'}
        </span>
      </header>
      <main className="main">
        {unknown && <div className="notice" role="note" data-testid="route-notice">There is no screen called “{unknown}”. Showing the report.</div>}
        {catalogue.status === 'error' && (
          <div className="stack" data-testid="service-down">
            <ErrorBanner error={catalogue.error} onRetry={reloadCatalogue} />
            <Card title="Start the service">
              <div className="stack">
                <span className="small muted">The demo reads everything from the edgekpi library through a small local service. From the repository root:</span>
                <CodeBlock text={'pip install -e ".[dev]"\npython -m edgekpi.server --port 8765'} />
                <span className="small muted">Then press Retry. Nothing here is mocked: the numbers come from the library running on DuckDB and Malloy.</span>
              </div>
            </Card>
          </div>
        )}
        {(catalogue.status === 'idle' || catalogue.status === 'loading') && <div className="empty"><Spinner label="Connecting" /><p>Connecting to the service…</p></div>}
        {catalogue.status === 'success' && <Screen param={param} />}
      </main>
    </div>
  )
}

export function App({ api }: { api: EdgeKpiApi }) {
  return (
    <AppProvider api={api}>
      <Shell />
    </AppProvider>
  )
}
