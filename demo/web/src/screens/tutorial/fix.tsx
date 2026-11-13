import { useCallback, useState } from 'react'
import type { BackendId, Catalogue, MalloyEngine, Plan } from '../../api/types'
import { Callout } from '../../components/Callout'
import { CodeBlock } from '../../components/CodeBlock'
import { ErrorBanner } from '../../components/ErrorBanner'
import { Pivot } from '../../components/Pivot'
import { Remote } from '../../components/Remote'
import { Stepper } from '../../components/Stepper'
import { Pill, Segmented, Spinner } from '../../components/ui'
import { formatValue } from '../../domain/format'
import { buildPivot } from '../../domain/pivot'
import { LAYOUTS, RATE_BY_TYPOLOGY, WAYS_REQUEST, YOUR_TURN, pairSummary } from '../../domain/tutorial'
import { dataOf } from '../../state/asyncState'
import { useAutoLatest, useLatest } from '../../state/useLatest'
import { noop, useRunAndExplain, type StepProps } from './shared'

/** Step 5: the registry's way. A saved query that returns one finished number. */
export function OldStep({ api }: StepProps) {
  const call = useCallback(() => api.inference(), [api])
  const [state, retry] = useAutoLatest(call, 'inference')
  return (
    <>
      <p className="lead">
        Today a KPI is stored as a <strong>query with a hole in it</strong>. The hole, <code>{'{{ group_by_list }}'}</code>, is filled with whatever
        columns the report needs. This is the saved query for Delivery Rate:
      </p>
      <Remote state={state} retry={retry}>
        {(inf) => {
          const template = inf.templates?.find((t) => t.kpi === 'delivery_rate')
          const kpi = inf.kpis?.find((k) => k.id === 'delivery_rate')
          if (!inf.available || !template)
            return <Callout kind="watch" title="No templates here">This service was started without the legacy templates, so the example cannot be shown. The explanation below still applies.</Callout>
          return (
            <div className="stack">
              <CodeBlock label={`Registry template ${template.id}`} text={template.sql} marks={['try_divide', 'group_by_list']} testId="legacy-sql" />
              <div className="read-guide">
                <div><b>1</b><span><code>{'{{ group_by_list }}'}</code> is <em>pasted</em> into the text. Each layout is a different query.</span></div>
                <div><b>2</b><span><code>try_divide(...)</code> does the division <em>inside</em> the query. What comes out is one finished percentage.</span></div>
                <div><b>3</b><span>The result is a column of percentages. The counts it was made of are gone, and nothing says “this is a ratio”.</span></div>
              </div>
              {kpi && (
                <div className="banner info">
                  <div>
                    <strong>What the library finds when it reads this query</strong>
                    <p>It is a ratio of two counts: <code className="mono">{kpi.formula}</code> (m3 = delivered, m1 = sent). That is exactly the information the saved query was hiding. <a href="#/migration">See the whole migration</a>.</p>
                  </div>
                </div>
              )}
            </div>
          )
        }}
      </Remote>
      <div className="two">
        <Callout kind="idea">
          Run the query once with no grouping and you do get the right total. The problem is a <em>report</em> that holds many cells and has to produce
          totals from them. All it holds are percentages.
        </Callout>
        <Callout kind="watch">Nothing is broken in the query. The weakness is the <strong>shape</strong> of what is stored: an answer, not a definition.</Callout>
      </div>
    </>
  )
}

function definitionText(c: Catalogue): string {
  const measures = c.measures.filter((m) => ['n_delivered', 'n_sent', 'n_reached'].includes(m.id))
  const kpis = c.kpis.filter((k) => ['delivery_rate', 'reached'].includes(k.id))
  return ['measures:', ...measures.map((m) => `  ${m.id}: ${m.expr}`), 'kpis:', ...kpis.map((k) => `  ${k.id}: ${k.formula}`)].join('\n')
}

/** Step 6: the definition as data, and what it says about totals. */
export function DefineStep({ catalogue }: StepProps) {
  return (
    <>
      <p className="lead">
        The fix is to store what the saved query was hiding. Instead of an answer, store a <strong>definition</strong> in two parts: the
        <em> counts</em> (called <strong>measures</strong>) and the <em>formula</em> that combines them (the <strong>KPI</strong>).
      </p>
      <CodeBlock label="The definition, as the library reads it" text={definitionText(catalogue)} marks={['ratio(', 'DISTINCT']} testId="definition" />
      <table className="table kinds" data-testid="kinds">
        <thead><tr><th>Kind of number</th><th>Example here</th><th>How a total is made</th></tr></thead>
        <tbody>
          <tr><td><Pill tone="blue">count</Pill></td><td className="mono">n_sent</td><td>Add the parts.</td></tr>
          <tr><td><Pill tone="green">rate</Pill></td><td className="mono">ratio(n_delivered, n_sent)</td><td>Add the numerators, add the denominators, divide once.</td></tr>
          <tr><td><Pill tone="peach">unique count</Pill></td><td className="mono">n_reached</td><td>Count the people again at that level. Never add.</td></tr>
        </tbody>
      </table>
      <div className="two">
        <Callout kind="idea">
          Because the library knows <em>which kind</em> each number is, it can total any layout correctly. And <code>ratio(n, d)</code> writes the
          “divide by zero” guard in one place, so nobody can forget it.
        </Callout>
        <Callout kind="remember">The definition says nothing about <strong>how</strong> or <strong>where</strong> to compute. That is the next step.</Callout>
      </div>
    </>
  )
}

const WAYS: {
  id: BackendId
  title: string
  tone: 'peach' | 'lav' | 'blue'
  idea: string
  analogy: string
  marks: string[]
  guide: { part: string; where: string }[]
  good: string
  limit: string
}[] = [
  {
    id: 'metric-view',
    title: 'Databricks metric view',
    tone: 'peach',
    idea: 'The database itself stores the measures. A metric view is an object in Databricks (Unity Catalog) that holds measures and formulas once. A query then says MEASURE(name) and chooses the grouping; the engine evaluates the measure at every level.',
    analogy: 'Like a calculated field owned by the warehouse, so every tool that queries it gets the same number.',
    marks: ['MEASURE(', 'GROUPING SETS', 'NULLIF'],
    guide: [
      { part: 'Measures', where: 'the measures: list of the CREATE VIEW … WITH METRICS statement' },
      { part: 'Formula', where: 'the delivery_rate measure: MEASURE(n_delivered) * 1.0 / NULLIF(MEASURE(n_sent), 0)' },
      { part: 'Grouping', where: 'the GROUP BY GROUPING SETS of the query: one set per layout level' },
    ],
    good: 'Governed in one place; shared with dashboards and notebooks; the engine optimises it.',
    limit: 'Databricks only, and not connected in this demo: its statements are compiled and shown, and a recorded warehouse run matched.',
  },
  {
    id: 'malloy',
    title: 'Malloy',
    tone: 'lav',
    idea: 'A modelling language for analytics. You declare measures inside a source, then a query lists what to group by and aggregate. Each nest: is a sub-table for one grouping level, and Malloy writes the SQL for the engine.',
    analogy: 'Like a small report designer: the structure of the report is the structure of the query.',
    marks: ['measure:', 'nullif', 'nest:', 'aggregate:', '.table('],
    guide: [
      { part: 'Measures', where: 'the measure: block of the source' },
      { part: 'Formula', where: 'delivery_rate is n_delivered / nullif(n_sent, 0)' },
      { part: 'Grouping', where: 'one nest: per level; the top-level aggregate: is the grand total' },
      { part: 'Engine', where: 'the .table(…) lines name the connection (duckdb or databricks) and the table; nothing else changes between engines' },
    ],
    good: 'Several engines; results come nested, which suits drill-down.',
    limit: 'A separate runtime (Node); no automatic zero guard, so the library writes nullif; fewer SQL functions are expressible.',
  },
  {
    id: 'sql',
    title: 'Generated SQL',
    tone: 'blue',
    idea: 'The library writes one ordinary SQL statement. GROUPING SETS computes every level in a single pass over the data, and the formula is applied in an outer SELECT, after the counts are added.',
    analogy: 'Like writing the query by hand, but the part people get wrong is produced by one function.',
    marks: ['GROUPING SETS', 'FILTER', 'NULLIF', 'HAVING'],
    guide: [
      { part: 'Measures', where: 'the aggregates of the inner query, such as COUNT(*) FILTER (WHERE …)' },
      { part: 'Formula', where: 'the outer SELECT: n_delivered * 1.0 / NULLIF(n_sent, 0)' },
      { part: 'Grouping', where: 'GROUP BY GROUPING SETS (...); HAVING COUNT(*) > 0 drops an empty total' },
    ],
    good: 'Runs on any SQL engine: DuckDB in this demo, a Databricks warehouse in the recorded run. Nothing new to install; one statement, one scan.',
    limit: 'The library owns the planner, so it must be tested: see the checks in the next steps.',
  },
]

/** Step 7: how each way of writing the definition works, with its live statements and a reading guide. */
export function WaysStep({ api, catalogue }: StepProps) {
  const [which, setWhich] = useState<BackendId>('metric-view')
  const way = WAYS.find((w) => w.id === which) ?? WAYS[0]!
  const [engine, setEngine] = useState<MalloyEngine>('duckdb')
  const engineOf = which === 'malloy' ? engine : undefined
  const planCall = useCallback(() => api.plan(WAYS_REQUEST, which, engineOf), [api, which, engineOf])
  const [plan, retry] = useAutoLatest(planCall, `${which}-${engineOf ?? ''}`)
  const runCall = useCallback(async () => {
    const [sql, malloy, evidence] = await Promise.all([api.run(WAYS_REQUEST, 'sql'), api.run(WAYS_REQUEST, 'malloy'), api.evidence()])
    return { ok: true as const, data: { sql, malloy, evidence } }
  }, [api])
  const [answers] = useAutoLatest(runCall, 'ways-answers')
  const totalOf = (r: Awaited<ReturnType<typeof api.run>>) => (r.ok ? (r.data.nodes.find((n) => n.scope.length === 0)?.values.delivery_rate ?? null) : null)
  const p: Plan | undefined = dataOf(plan)
  const available = catalogue.backends.find((b) => b.id === which)?.available && (which !== 'malloy' || engine === 'duckdb')
  return (
    <>
      <p className="lead">
        The definition is the same; there are <strong>three ways to make a database answer it</strong>. Each has the same three pieces: where the
        measures live, where the formula lives, and how the grouping is asked. The statements below are the real ones, generated now for “Delivery
        Rate by Typology across Market”.
      </p>
      <Segmented
        label="Way of writing the definition"
        value={which}
        onChange={setWhich}
        options={WAYS.map((w) => ({ id: w.id, label: w.title }))}
      />
      <div className="way" data-testid={`way-${way.id}`}>
        <div className="way-text">
          <div className="row"><h3>{way.title}</h3><Pill tone={available ? 'green' : 'gray'}>{available ? 'runs in this demo' : 'compiled only, not connected'}</Pill></div>
          <p>{way.idea}</p>
          <p className="muted">{way.analogy}</p>
          <div className="read-guide">
            {way.guide.map((g, i) => (
              <div key={g.part}><b>{i + 1}</b><span><strong>{g.part}:</strong> {g.where}.</span></div>
            ))}
          </div>
          <div className="gl">
            {which === 'malloy' && (
              <div className="engines" data-testid="malloy-engines">
                <strong>Same model, two engines</strong>
                <span>Only the <code>.table(…)</code> lines and the connection change. Malloy then writes each engine’s own SQL, so the model never contains engine SQL.</span>
              </div>
            )}
            <div className="good"><strong>Good at</strong><span>{way.good}</span></div>
            <div className="limit"><strong>Limits</strong><span>{way.limit}</span></div>
          </div>
        </div>
        <div className="way-code">
          {plan.status === 'error' && <ErrorBanner error={plan.error} onRetry={retry} />}
          {!p && plan.status === 'loading' && <Spinner />}
          {which === 'malloy' && (
            <Segmented label="Engine Malloy runs on" value={engine} onChange={setEngine} options={[{ id: 'duckdb', label: 'On DuckDB' }, { id: 'databricks', label: 'On Databricks' }]} />
          )}
          {p && (
            <div className={`stack ${plan.status === 'loading' ? 'stale' : ''}`}>
              {p.connection && <CodeBlock label={`Connection, set up outside the model · ${p.connection.label}`} text={p.connection.text} testId="malloy-connection" />}
              {p.statements.map((s, i) => (
                <CodeBlock key={`${which}-${engineOf ?? ''}-${i}`} label={`${s.kind === 'ddl' ? 'Definition, stored once' : 'Query, asked per report'} · ${s.language}`} text={s.text} marks={way.marks} testId={`way-code-${i}`} />
              ))}
              <span className="small muted">Yellow lines are the ones the reading guide points at.</span>
            </div>
          )}
        </div>
      </div>
      <Remote state={answers}>
        {({ sql, malloy, evidence }) => (
          <div className="answers" data-testid="same-answer">
            <strong>Same question, same grand total</strong>
            <div className="row">
              <Pill tone="blue">SQL on DuckDB · {formatValue(totalOf(sql), 'percent')}</Pill>
              {(() => {
                const m = evidence.ok ? pairSummary(evidence.data, 'sql on databricks') : null
                return <Pill tone="blue">{m ? `SQL on Databricks · matched in the recorded run (${m.requests} reports, ${m.differences} differences)` : 'SQL on Databricks · not run here'}</Pill>
              })()}
              <Pill tone="lav">Malloy on DuckDB · {formatValue(totalOf(malloy), 'percent')}</Pill>
              {(() => {
                const m = evidence.ok ? pairSummary(evidence.data, 'malloy on databricks') : null
                return <Pill tone="lav">{m ? `Malloy on Databricks · matched in the recorded run (${m.requests} reports, ${m.differences} differences)` : 'Malloy on Databricks · not run here'}</Pill>
              })()}
              <Pill tone="peach">
                Metric view · {evidence.ok && evidence.data.available ? `matched in the recorded warehouse run (${evidence.data.comparisons} comparisons, ${evidence.data.failed} differences)` : 'not run here'}
              </Pill>
            </div>
          </div>
        )}
      </Remote>
      <div className="two">
        <Callout kind="idea">All three are <em>renderings</em> of one definition, not three definitions. Change a formula once and all three change.</Callout>
        <Callout kind="remember">Choosing one is an operational decision (where do you run, who consumes it), not a different answer.</Callout>
      </div>
    </>
  )
}

/** Step 8: the payoff. Four layouts, one grand total. */
export function LayoutStep({ api }: StepProps) {
  const [layoutId, setLayoutId] = useState('typology')
  const layout = LAYOUTS.find((l) => l.id === layoutId) ?? LAYOUTS[0]!
  const [state, retry] = useRunAndExplain(api, layout.request, 'delivery_rate')
  const planCall = useCallback(() => api.plan(layout.request, 'sql'), [api, layout])
  const [plan] = useAutoLatest(planCall, layoutId)
  const sets = dataOf(plan)?.statements[0]?.text.match(/GROUP BY GROUPING SETS \(.*\)/)?.[0]
  return (
    <>
      <p className="lead">
        Now the experiment the old way could not survive. Change the layout of the report and watch two numbers: the real grand total, and the
        average of the cells that you would have computed by hand.
      </p>
      <Segmented label="Layout" value={layoutId} onChange={setLayoutId} options={LAYOUTS.map((l) => ({ id: l.id, label: l.label }))} />
      <Remote state={state} retry={retry}>
        {({ run, explain }) => {
          const pivot = buildPivot(run, 'delivery_rate')
          const total = run.nodes.find((n) => n.scope.length === 0)?.values.delivery_rate ?? null
          return (
            <div className="stack" data-testid="layout-result">
              <Pivot pivot={pivot} selected={null} onSelect={noop} readOnly />
              <div className="compare">
                <div className="right"><span className="small">Grand total, from the definition</span><b data-testid="layout-total">{formatValue(total, 'percent')}</b></div>
                <div className={explain.naive?.differs ? 'wrong' : 'right'}>
                  <span className="small">{explain.naive ? `Average of the cells by ${explain.naive.dimension}` : 'Average of the cells'}</span>
                  <b data-testid="layout-naive">{explain.naive ? formatValue(explain.naive.value, 'percent') : 'nothing to average'}</b>
                </div>
              </div>
            </div>
          )
        }}
      </Remote>
      {sets && <CodeBlock label="What the library asked the database for, in one pass" text={sets} marks={['GROUPING SETS']} testId="grouping-sets" />}
      <div className="two">
        <Callout kind="idea">The grand total never moves, whatever the layout. The hand-made average moves each time, because it depends on how the cells were cut.</Callout>
        <Callout kind="try">Switch layouts and compare the two numbers. This is the business problem, reproduced and solved live.</Callout>
      </div>
    </>
  )
}

/** Step 9: three backends and an independent reference. Every result is checked. */
export function VerifyStep({ api }: StepProps) {
  const [state] = useRunAndExplain(api, RATE_BY_TYPOLOGY, 'delivery_rate')
  const call = useCallback(() => api.verify(YOUR_TURN), [api])
  const [verify, check] = useLatest(call)
  const run = dataOf(state)?.run
  return (
    <>
      <p className="lead">
        A definition that is computed by a program needs a way to be <strong>doubted</strong>. Two safeguards run on every report.
      </p>
      <div className="two">
        <div className="card"><div className="card-body stack">
          <h3>1. The arithmetic check</h3>
          <p>Every result is checked against three rules before you see it:</p>
          <ul className="rules">
            <li><strong>Parts add up.</strong> A count equals the sum of the groups under it.</li>
            <li><strong>Unique counts stay in bounds.</strong> Between the biggest group and the sum of the groups, never above.</li>
            <li><strong>A rate is its own division.</strong> Each rate equals its counts divided, in every cell.</li>
          </ul>
          {run && (
            <div className="row" data-testid="checks">
              <Stepper states={run.states} />
              <Pill tone={run.violations.length === 0 ? 'green' : 'pink'}>{run.violations.length === 0 ? '✓ 0 violations' : `✕ ${run.violations.length} violations`}</Pill>
            </div>
          )}
        </div></div>
        <div className="card"><div className="card-body stack">
          <h3>2. The independent reference</h3>
          <p>
            A deliberately naive program asks the database for every cell with a separate plain <code>GROUP BY</code> and compares. If a backend
            disagrees on a single value, it is reported.
          </p>
          <button type="button" className="btn primary" onClick={() => void check()} disabled={verify.status === 'loading'} data-testid="tutorial-verify">
            {verify.status === 'loading' ? 'Comparing…' : 'Check all backends now'}
          </button>
          {verify.status === 'error' && <ErrorBanner error={verify.error} onRetry={() => void check()} />}
          {verify.status === 'success' && (
            <div className="stack" data-testid="tutorial-verify-result">
              {verify.data.outcomes.map((o) => (
                <div key={o.label} className={`banner ${o.ok ? 'ok' : 'error'}`}><div><strong>{o.label}</strong><p>{o.ok ? `matches the reference on all ${o.nodes} nodes` : (o.error ?? `${o.diffs} differences`)}</p></div></div>
              ))}
              {verify.data.skipped.map((s) => <div key={s.id} className="banner info"><div><strong>{s.label}</strong><p>Not connected here. The recorded warehouse run matched all 45 comparisons.</p></div></div>)}
            </div>
          )}
        </div></div>
      </div>
      <Callout kind="remember">Trust comes from being able to check. That is why the edge-case lab exists: it tries to break these rules on purpose.</Callout>
    </>
  )
}

/** Step 10: what to do next, and the three rules. */
export function YoursStep({ openReport }: StepProps) {
  return (
    <>
      <p className="lead">You now know the problem, the three kinds of number, and how one definition serves three backends. Go and try it yourself.</p>
      <div className="three next-cards">
        <div className="card"><div className="card-body stack">
          <h3>Build and break a report</h3>
          <p className="small">Opens the Report with Typology down and Market across. Click the <strong>Total</strong> cells to see the explanation, and try the filters and dates.</p>
          <button type="button" className="btn primary" onClick={() => openReport(YOUR_TURN)} data-testid="open-yours">Open the Report</button>
        </div></div>
        <div className="card"><div className="card-body stack">
          <h3>Compare the backends</h3>
          <p className="small">The same report as a metric view, Malloy and SQL, side by side, with the recorded warehouse run.</p>
          <a className="btn" href="#/backends">Go to Backends</a>
        </div></div>
        <div className="card"><div className="card-body stack">
          <h3>Try to break it</h3>
          <p className="small">Twelve things that go wrong on purpose. A correct service refuses or answers honestly, and says which.</p>
          <a className="btn" href="#/lab">Go to the Edge-case lab</a>
        </div></div>
      </div>
      <div className="three rules3" data-testid="rules">
        <Callout kind="remember" title="Rule 1: rates"><span>Add the numerators, add the denominators, divide once. Never average percentages.</span></Callout>
        <Callout kind="remember" title="Rule 2: unique counts"><span>Count the people again at the level of the total. Never add the cells.</span></Callout>
        <Callout kind="remember" title="Rule 3: totals"><span>Compute a total from the definition over all the rows, with the filters kept. Never from the cells.</span></Callout>
      </div>
      <p className="small muted">Also see <a href="#/catalogue">the Catalogue</a> for the definitions, and <a href="#/migration">Migration</a> to turn old saved queries into definitions.</p>
    </>
  )
}
