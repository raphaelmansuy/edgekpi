import { useCallback, useState } from 'react'
import { Callout } from '../../components/Callout'
import { CodeBlock } from '../../components/CodeBlock'
import { ErrorBanner } from '../../components/ErrorBanner'
import { Remote } from '../../components/Remote'
import { Pill, Segmented, Spinner } from '../../components/ui'
import type { Inference } from '../../api/types'
import { formatValue } from '../../domain/format'
import { CONTRACT, IDIOMS, SQL_LADDER, STAGES, YOUR_TURN, advice, excerpt, lineMatching, measureUse, measuresOf } from '../../domain/tutorial'
import { dataOf } from '../../state/asyncState'
import { useAutoLatest } from '../../state/useLatest'
import type { StepProps } from './shared'

const quote = (text: string | null) => (text ? <code className="mono">{text}</code> : <span className="muted">–</span>)

/** Step 8: how a KPI is written as a definition, and how each part of it becomes SQL. Every statement shown is generated now. */
export function SqlStep({ api, catalogue }: StepProps) {
  const [rungId, setRungId] = useState(SQL_LADDER[0]!.id)
  const rung = SQL_LADDER.find((r) => r.id === rungId) ?? SQL_LADDER[0]!
  const rungCall = useCallback(() => api.plan(rung.request, 'sql'), [api, rung])
  const [plan, retry] = useAutoLatest(rungCall, rungId)
  const fullCall = useCallback(() => api.plan(YOUR_TURN, 'sql'), [api])
  const [full] = useAutoLatest(fullCall, 'sql-recipes')
  const sql = dataOf(full)?.statements[0]?.text ?? ''
  const measure = (id: string) => catalogue.measures.find((m) => m.id === id)
  const kpi = (id: string) => catalogue.kpis.find((k) => k.id === id)
  const dimension = catalogue.dimensions.find((d) => d.id === 'typology')
  const join = catalogue.joins[0]
  const from = catalogue.filters.find((f) => f.optional)
  const ctor = kpi('ctor')
  const recipes = [
    { id: 'count', want: 'Count the rows', kind: <Pill tone="blue">count</Pill>, write: `n_sent: ${measure('n_sent')?.expr ?? ''}`, sql: lineMatching(sql, /\bCOUNT\(\*\) AS n_sent/) },
    { id: 'condition', want: 'Count only some rows', kind: <Pill tone="blue">count</Pill>, write: `n_delivered: ${measure('n_delivered')?.expr ?? ''}`, sql: lineMatching(sql, /AS n_delivered/) },
    { id: 'unique', want: 'Count people, not rows', kind: <Pill tone="peach">unique</Pill>, write: `n_reached: ${measure('n_reached')?.expr ?? ''}`, sql: lineMatching(sql, /DISTINCT/) },
    { id: 'rate', want: 'Divide one count by another', kind: <Pill tone="green">rate</Pill>, write: `delivery_rate: ${kpi('delivery_rate')?.formula ?? ''}`, sql: excerpt(sql, /(\w+ \* 1\.0 \/ NULLIF\(\w+, 0\) AS \w+)/) },
    { id: 'dimension', want: 'Group by a column of another table', kind: <Pill tone="gray">dimension</Pill>, write: `typology: ${dimension?.expr ?? ''}\njoin ${join?.id ?? ''}: ${join?.on ?? ''}`, sql: lineMatching(sql, /LEFT JOIN/) },
    { id: 'date', want: 'Limit to dates, when given', kind: <Pill tone="gray">filter</Pill>, write: `${from?.id ?? ''}: ${from?.predicate ?? ''}`, sql: lineMatching(sql, /start_date AS DATE\) IS NULL/) },
  ]
  const p = dataOf(plan)
  return (
    <>
      <p className="lead">
        With this approach <strong>nobody writes the big query</strong>. You write a short definition, and one function turns it into one ordinary
        SQL statement. This step shows the recipe for writing a KPI, then grows a real statement one idea at a time, so you can read any generated
        query yourself.
      </p>

      <h3 className="section">A. Write a KPI: six recipes</h3>
      <div className="table-wrap">
        <table className="table compact" data-testid="recipes">
          <thead><tr><th>You want to…</th><th>Kind</th><th>You write</th><th>The SQL contains</th></tr></thead>
          <tbody>
            {recipes.map((r) => (
              <tr key={r.id} data-recipe={r.id}>
                <td>{r.want}</td>
                <td>{r.kind}</td>
                <td><code className="mono pre">{r.write}</code></td>
                <td>{quote(r.sql)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted">The left side comes from the catalogue; the right side is quoted from the statement generated for a report that uses them all.</p>

      <h3 className="section">B. Read the SQL: grow it in four steps</h3>
      <Segmented label="Step of the build-up" value={rungId} onChange={setRungId} options={SQL_LADDER.map((r) => ({ id: r.id, label: r.label }))} />
      <div className="way" data-testid={`rung-${rung.id}`}>
        <div className="way-text">
          <p><strong>What is new:</strong> {rung.adds}</p>
          <div className="read-guide" data-testid="read-order">
            <div><b>1</b><span><strong>FROM / LEFT JOIN</strong>: the rows, and the other tables they need. One row stays one row.</span></div>
            <div><b>2</b><span><strong>WHERE</strong>: the filters. A date that is not given means “no limit”.</span></div>
            <div><b>3</b><span><strong>Aggregates</strong>: the measures. Every cell and every total is built from these counts.</span></div>
            <div><b>4</b><span><strong>GROUP BY GROUPING SETS</strong>: one set per level, so cells and totals come from one scan. <code>gid</code> says which level a row is.</span></div>
            <div><b>5</b><span><strong>Outer SELECT</strong>: the formulas, applied <em>after</em> the counts are added. This is where totals become right.</span></div>
          </div>
        </div>
        <div className="way-code">
          {plan.status === 'error' && <ErrorBanner error={plan.error} onRetry={retry} />}
          {!p && plan.status === 'loading' && <Spinner />}
          {p && (
            <div className={`stack ${plan.status === 'loading' ? 'stale' : ''}`}>
              <CodeBlock label={`Generated for: ${rung.request.kpis.join(', ')}${rung.request.rows.length + rung.request.cols.length ? ` by ${[...rung.request.rows, ...rung.request.cols].join(' × ')}` : ''}`} text={p.statements[0]?.text ?? ''} marks={rung.marks} testId="rung-sql" />
              <span className="small muted">Yellow lines are what this step added.</span>
            </div>
          )}
        </div>
      </div>

      <h3 className="section">C. Add a KPI: two lines</h3>
      <div className="two">
        <div className="stack">
          {ctor ? (
            <CodeBlock label="Already in the catalogue: Click-to-open Rate" text={`kpis:\n  ${ctor.id}: ${ctor.formula}`} marks={['ratio(']} testId="new-kpi" />
          ) : (
            <Callout kind="watch" title="Not in this catalogue">The example KPI is missing here, the recipe above still applies.</Callout>
          )}
          <p className="small muted">The counts it needs already exist as measures. No query is written, and every layout, total and backend gets it at once.</p>
        </div>
        <div className="stack">
          <Callout kind="idea" title="Divide last">
            The generated statement adds the counts first and divides in the outer SELECT. Doing it the other way round, dividing in each cell and then
            combining, is the mistake from step 2.
          </Callout>
          <Callout kind="watch">
            Three things are handled for you: a group whose label is unknown (shown as <code>(none)</code>), an empty total (dropped by{' '}
            <code>HAVING COUNT(*) &gt; 0</code>) and a zero denominator (<code>NULLIF</code> gives “–”, not an error).
          </Callout>
        </div>
      </div>
    </>
  )
}

const INFER_COMMAND = [
  'python -m edgekpi infer registry-templates.sql \\',
  '       --name registry --key message_id \\',
  '       --dim typology=client.typology --dim market=market \\',
  '       --data registry-data.sql',
].join('\n')

type Route = 'once' | 'infer'

/** Step 9: two ways to get the saved queries onto definitions, and how to know it worked. */
export function MoveStep({ api }: StepProps) {
  const call = useCallback(() => api.inference(), [api])
  const [state, retry] = useAutoLatest(call, 'inference-move')
  const [route, setRoute] = useState<Route>('once')
  return (
    <>
      <p className="lead">
        You do not rewrite the saved queries by hand, and you do not switch everything on one day. There are <strong>two routes</strong>, and they can
        be combined: move once and then edit definitions, or keep writing the SQL templates you know and let a tool <strong>infer the definition</strong>.
      </p>
      <Segmented
        label="Route"
        value={route}
        onChange={setRoute}
        options={[{ id: 'once', label: 'A. Migrate once' }, { id: 'infer', label: 'B. Keep writing templates, infer the definition' }]}
      />
      {route === 'once' ? <MigrateOnce state={state} retry={retry} /> : <InferFromTemplates state={state} retry={retry} />}

      <h3 className="section">How each habit of the old queries is translated</h3>
      <div className="table-wrap">
        <table className="table compact" data-testid="idioms">
          <thead><tr><th>In the saved query</th><th>In the definition</th><th>Why</th></tr></thead>
          <tbody>
            {IDIOMS.map((i) => (
              <tr key={i.legacy}><td><code className="mono">{i.legacy}</code></td><td>{i.becomes}</td><td>{i.why}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="two">
        <Callout kind="idea" title="Proof, not trust">
          “Only exist after migration” are values the old queries could not give: the totals. Every value the old queries <em>could</em> give is compared,
          and the count of differences has to be zero before anything is switched.
        </Callout>
        <Callout kind="try">
          See all eight templates, the inferred model and the comparison on the <a href="#/migration">Migration screen</a>.
        </Callout>
      </div>
    </>
  )
}

type InferenceState = ReturnType<typeof useAutoLatest<Inference>>[0]

/** Route A: five stages, then the saved query beside the definition proposed for it. */
function MigrateOnce({ state, retry }: { state: InferenceState; retry: () => void }) {
  const [picked, setPicked] = useState<string | null>(null)
  return (
    <>
      <ol className="stages" data-testid="stages">
        {STAGES.map((s, i) => (
          <li key={s.id} data-stage={s.id}>
            <span className="num">{i + 1}</span>
            <strong>{s.title}</strong>
            <span><em>You:</em> {s.you}</span>
            <span><em>Tool:</em> {s.tool}</span>
            <span className="done"><em>Done when:</em> {s.done}</span>
          </li>
        ))}
      </ol>
      <Callout kind="idea" title="Route A in one line">
        Run the tool <strong>once</strong>, review what it proposes, and from then on <strong>the definition is what people edit</strong>. The templates are
        retired one KPI at a time.
      </Callout>

      <h3 className="section">What it looks like on the example registry</h3>
      <Remote state={state} retry={retry}>
        {(inf) => {
          const templates = inf.templates ?? []
          const accepted = templates.filter((t) => t.accepted)
          const refused = templates.filter((t) => !t.accepted)
          const options = [
            ...['delivery_rate', 'reached'].map((k) => accepted.find((t) => t.kpi === k)).filter((t) => t !== undefined),
            ...refused.slice(0, 2),
          ]
          if (!inf.available || options.length === 0)
            return <Callout kind="watch" title="No templates here">This service was started without the legacy templates, so the example cannot be shown. The stages above still apply.</Callout>
          const current = options.find((t) => t.id === picked) ?? options[0]!
          const kpi = inf.kpis?.find((k) => k.id === current.kpi)
          const used = (kpi ? measuresOf(kpi.formula) : []).map((id) => inf.measures?.find((m) => m.id === id)).filter((m) => m !== undefined)
          const note = inf.notes?.find((n) => current.kpi && n.startsWith(`${current.kpi}:`))
          return (
            <div className="stack" data-testid="move-live">
              <Segmented
                label="Template"
                value={current.id}
                onChange={setPicked}
                options={options.map((t) => ({ id: t.id, label: t.accepted ? `✓ ${t.kpi}` : `✕ ${(t.reason ?? '').split(':')[0]}` }))}
              />
              <div className="way" data-testid={`move-${current.accepted ? 'accepted' : 'refused'}`}>
                <CodeBlock label={`Before: saved query ${current.id}`} text={current.sql} marks={['group_by_list', 'try_divide', 'COUNT_IF', 'AND C.is_delivered']} testId="move-before" />
                {current.accepted && kpi ? (
                  <div className="stack">
                    <CodeBlock
                      label="After: the definition the library proposes"
                      text={['measures:', ...used.map((m) => `  ${m.id}: ${m.expr}`), 'kpis:', `  ${kpi.id}: ${kpi.formula}   # status: ${kpi.status}`].join('\n')}
                      marks={[`  ${kpi.id}:`]}
                      testId="move-after"
                    />
                    {note && <Callout kind="idea" title="What changed in the maths">{note}.</Callout>}
                    <Callout kind="remember">
                      The status is <strong>{kpi.status}</strong> until its owner confirms. The library proposes; a person decides.
                    </Callout>
                  </div>
                ) : (
                  <div className="stack" data-testid="move-refusal">
                    <Callout kind="watch" title="Refused, with its reason">{current.reason}</Callout>
                    <Callout kind="idea" title="What to do">{advice(current.reason)}</Callout>
                  </div>
                )}
              </div>
              <ParityLine inf={inf} />
            </div>
          )
        }}
      </Remote>
    </>
  )
}

function ParityLine({ inf }: { inf: Inference }) {
  const templates = inf.templates ?? []
  const accepted = templates.filter((t) => t.accepted).length
  return (
    <div className="row wrap" data-testid="parity-line">
      <Pill tone="green">{accepted} of {templates.length} templates accepted</Pill>
      <Pill tone="pink">{templates.length - accepted} refused, with a reason</Pill>
      {inf.parity && <Pill tone="blue">{formatValue(inf.parity.compared, 'number')} old values compared</Pill>}
      {inf.parity && <Pill tone={inf.parity.different === 0 ? 'green' : 'pink'}>{inf.parity.different} differ</Pill>}
      {inf.parity && <Pill tone="yellow">{inf.parity.only_after} only exist after migration</Pill>}
    </div>
  )
}

const LOOP = [
  { id: 'write', title: 'Write', text: 'An author edits a SQL template, the way it is done today.' },
  { id: 'infer', title: 'Infer', text: 'The tool reads it and names the counts (measures), the formula and the filters.' },
  { id: 'check', title: 'Check', text: 'It accepts the template, or refuses it with a code that says which rule was broken.' },
  { id: 'prove', title: 'Prove', text: 'It runs the template and the definition on the same data and compares every value.' },
  { id: 'use', title: 'Use', text: 'Reports are built from the generated definition; an owner confirms each KPI.' },
]

/** Route B: templates stay the thing people write; the definition is generated and checked from them. */
function InferFromTemplates({ state, retry }: { state: InferenceState; retry: () => void }) {
  return (
    <div className="stack" data-testid="route-infer">
      <ol className="stages loop" data-testid="infer-loop">
        {LOOP.map((s, i) => (
          <li key={s.id} data-stage={s.id}>
            <span className="num">{i + 1}</span>
            <strong>{s.title}</strong>
            <span>{s.text}</span>
          </li>
        ))}
      </ol>
      <Callout kind="idea" title="Route B in one line">
        <strong>Nothing changes for the author on day one.</strong> The template stays the source; the definition is a generated, checked copy. The refusals
        act as a linter for templates.
      </Callout>

      <h3 className="section">The template contract: five rules, each with its refusal</h3>
      <div className="table-wrap">
        <table className="table compact" data-testid="contract">
          <thead><tr><th>Write the template so that…</th><th>Because</th><th>If not, the tool says</th></tr></thead>
          <tbody>
            {CONTRACT.map((r) => (
              <tr key={r.write}><td>{r.write}</td><td>{r.because}</td><td><code className="mono">{r.refused}</code></td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="section">What the tool makes of the example templates</h3>
      <Remote state={state} retry={retry}>
        {(inf) => {
          if (!inf.available || !inf.kpis || !inf.measures)
            return <Callout kind="watch" title="No templates here">This service was started without the legacy templates, so the example cannot be shown. The contract above still applies.</Callout>
          const uses = measureUse(inf.kpis, inf.measures)
          const refused = (inf.templates ?? []).filter((t) => !t.accepted)
          return (
            <div className="stack" data-testid="infer-live">
              <p>
                <strong>{inf.kpis.length} templates</strong> became <strong>{inf.measures.length} measures</strong>: templates that count the same thing share one
                measure, even when they spell it differently.
              </p>
              <div className="table-wrap">
                <table className="table compact" data-testid="shared-measures">
                  <thead><tr><th>Measure</th><th>What it counts</th><th>Used by</th></tr></thead>
                  <tbody>
                    {uses.map((m) => (
                      <tr key={m.id} data-measure={m.id}>
                        <td className="mono">{m.id}</td>
                        <td><code className="mono">{m.expr}</code></td>
                        <td>{m.usedBy.map((k) => <Pill key={k} tone={m.usedBy.length > 1 ? 'yellow' : 'gray'}>{k}</Pill>)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="stack" data-testid="infer-refusals">
                {refused.map((t) => (
                  <Callout key={t.id} kind="watch" title={`Refused: ${t.id}`}>
                    <code className="mono">{t.reason}</code>. {advice(t.reason)}
                  </Callout>
                ))}
              </div>
              <ParityLine inf={inf} />
            </div>
          )
        }}
      </Remote>

      <h3 className="section">Run it</h3>
      <CodeBlock label="The command that reads the templates and prints the definition" text={INFER_COMMAND} testId="infer-command" />
      <p className="small muted">
        It prints the model, then <code>accepted N, refused M</code> and one line per refusal. The comparison with the old numbers is the library’s
        <code> parity.verify</code>, which this demo’s service runs. A gate that fails a change on a refusal or a difference is a few lines on top of these
        functions; it is not built here.
      </p>

      <h3 className="section">Which route?</h3>
      <div className="table-wrap">
        <table className="table compact" data-testid="routes">
          <thead><tr><th /><th>A. Migrate once</th><th>B. Keep templates, infer</th></tr></thead>
          <tbody>
            <tr><td>People edit</td><td>the definition</td><td>the SQL template</td></tr>
            <tr><td>The definition is</td><td>the source of truth</td><td>generated; hand edits would be overwritten</td></tr>
            <tr><td>Day-one effort</td><td>learn the definition format</td><td>none for authors</td></tr>
            <tr><td>What can be expressed</td><td>anything the model allows</td><td>only what the template contract allows</td></tr>
            <tr><td>Risk</td><td>a one-time review of every KPI</td><td>two sources live side by side for as long as it lasts</td></tr>
          </tbody>
        </table>
      </div>
      <Callout kind="remember" title="Use B as a bridge, A as the destination">
        Start with B so nothing stops and every KPI gets a checked definition. When a KPI needs to evolve, promote its generated definition to be the
        source (route A) and retire its template.
      </Callout>
    </div>
  )
}
