import { Callout } from '../../components/Callout'
import { ExplainPanel } from '../../components/Explain'
import { Pivot } from '../../components/Pivot'
import { Predict } from '../../components/Predict'
import { Remote } from '../../components/Remote'
import { formatValue, memberLabel } from '../../domain/format'
import { buildPivot, listRows } from '../../domain/pivot'
import { RATE_BY_TYPOLOGY } from '../../domain/tutorial'
import { noop, useMessages, useRunAndExplain, type StepProps } from './shared'

const yesNo = (v: boolean) => (v ? '✓' : '·')

/** Step 1: the rows. Everything later is a summary of these thirteen lines. */
export function DataStep({ api }: StepProps) {
  const [state, retry] = useMessages(api)
  return (
    <>
      <p className="lead">
        Imagine you run the CRM of a shop. Every time you send a promotional message, one line is written. Here are all thirteen messages of the
        year, and nothing else. Every number you will see in this demo is a summary of <strong>these lines</strong>.
      </p>
      <Remote state={state} retry={retry}>
        {({ rows }) => (
          <div className="table-wrap" data-testid="messages">
            <table className="table compact">
              <thead>
                <tr><th>#</th><th>Client</th><th>Typology</th><th>Market</th><th>Sent on</th><th>Delivered</th><th>Opened</th><th>Clicked</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.message_id} className={r.typology === null ? 'unknown' : ''} data-message={r.message_id}>
                    <td className="mono">{r.message_id}</td>
                    <td className="mono">{r.client_id}</td>
                    <td>{r.typology === null ? <span className="none-member">{memberLabel(null)}</span> : r.typology}</td>
                    <td>{r.market}</td>
                    <td className="mono">{r.send_date}</td>
                    <td>{yesNo(r.is_delivered)}</td>
                    <td>{yesNo(r.is_opened)}</td>
                    <td>{yesNo(r.is_clicked)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Remote>
      <div className="two">
        <Callout kind="idea">
          A <strong>report</strong> groups these lines (by typology, by market…) and counts them. A <strong>KPI</strong> is a number computed
          from the counts, such as <em>Delivery Rate = delivered ÷ sent</em>.
        </Callout>
        <Callout kind="watch" title="One line is odd">
          Message 13 went to client <code>c9</code>, who is missing from the client list, so its typology is unknown. It is a real group,
          shown as <span className="none-member">(none)</span>. It will matter later.
        </Callout>
      </div>
    </>
  )
}

/** Step 2: commit to an answer, then see it. */
export function PredictStep({ api, answers, answer }: StepProps) {
  const [state, retry] = useRunAndExplain(api, RATE_BY_TYPOLOGY, 'delivery_rate')
  const choice = answers.rate
  return (
    <>
      <p className="lead">
        Below is the <strong>Delivery Rate</strong> of each group: the share of messages that reached the client. Your manager asks:
        <em> “and for everyone together?”</em>
      </p>
      <Remote state={state} retry={retry}>
        {({ run, explain }) => {
          const pivot = buildPivot(run, 'delivery_rate')
          const shown = { ...pivot, rows: choice === undefined ? pivot.rows.filter((r) => r.kind !== 'total') : pivot.rows }
          const total = run.nodes.find((n) => n.scope.length === 0)?.values.delivery_rate ?? null
          const naive = explain.naive?.value ?? null
          return (
            <div className="stack">
              <Pivot pivot={shown} selected={null} onSelect={noop} readOnly />
              <Predict
                id="rate"
                question="What is the Delivery Rate for everyone?"
                correct="ratio"
                answer={choice}
                onAnswer={(c) => answer('rate', c)}
                choices={[
                  { id: 'average', label: <strong>{formatValue(naive, 'percent')}</strong>, detail: 'Take the average of the rates above.' },
                  { id: 'ratio', label: <strong>{formatValue(total, 'percent')}</strong>, detail: 'Divide all delivered messages by all sent messages.' },
                ]}
              >
                <p>
                  The right answer is <strong>{formatValue(total, 'percent')}</strong>. The average gives {formatValue(naive, 'percent')}: a
                  difference of {explain.naive ? Math.abs(Math.round((naive! - total!) * 1000) / 10).toFixed(1) : '?'} points, for a number that
                  looks perfectly reasonable.
                </p>
                <ExplainPanel e={explain} />
              </Predict>
            </div>
          )
        }}
      </Remote>
      {choice === undefined && <Callout kind="try">Pick an answer. Nothing is hidden: the service will compute both and show you.</Callout>}
    </>
  )
}

/** Step 3: why. The counts behind each rate. */
export function InsideStep({ api }: StepProps) {
  const [state, retry] = useRunAndExplain(api, RATE_BY_TYPOLOGY, 'delivery_rate')
  return (
    <>
      <p className="lead">
        A percentage is a <strong>ratio</strong>: a count on top of a count. Once the division is done, the sizes are lost. Open the percentages
        and look at what they were made of.
      </p>
      <Remote state={state} retry={retry}>
        {({ run }) => {
          const rows = listRows(run)
          const total = rows.find((r) => r.kind === 'total')
          return (
            <div className="stack">
              <table className="table counts" data-testid="counts">
                <thead>
                  <tr><th>Typology</th><th className="num">Delivered</th><th className="num">Sent</th><th className="num">Delivery Rate</th></tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.label} className={r.kind === 'total' ? 'total' : ''} data-row={r.label}>
                      <td>{r.label === '(none)' ? <span className="none-member">(none)</span> : r.label}</td>
                      <td className="num">{formatValue(r.values.n_delivered ?? null, 'number')}</td>
                      <td className="num">{formatValue(r.values.n_sent ?? null, 'number')}</td>
                      <td className="num"><strong>{formatValue(r.values.delivery_rate ?? null, 'percent')}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="equations">
                <div className="eq right">
                  <span className="small">The right way: add the counts, then divide once</span>
                  <b data-testid="eq-right">{formatValue(total?.values.n_delivered ?? null, 'number')} ÷ {formatValue(total?.values.n_sent ?? null, 'number')} = {formatValue(total?.values.delivery_rate ?? null, 'percent')}</b>
                </div>
                <div className="eq wrong">
                  <span className="small">The tempting way: average the percentages</span>
                  <b>(rate₁ + rate₂ + rate₃) ÷ 3</b>
                  <span className="small">every group counts the same, big or small</span>
                </div>
              </div>
            </div>
          )
        }}
      </Remote>
      <div className="two">
        <Callout kind="idea">
          <strong>(none)</strong> delivered 1 of 1 message: a perfect 100%. <strong>VIP</strong> delivered 3 of 5: 60%. Averaging treats
          “1 out of 1” as important as “3 out of 5”. A rate has <em>forgotten its size</em>; the counts have not.
        </Callout>
        <Callout kind="remember">To total a rate, go back to the counts: add the numerators, add the denominators, divide once.</Callout>
      </div>
    </>
  )
}

