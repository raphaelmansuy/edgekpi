import { Callout } from '../../components/Callout'
import { ExplainPanel } from '../../components/Explain'
import { Pivot } from '../../components/Pivot'
import { Predict } from '../../components/Predict'
import { Remote } from '../../components/Remote'
import { formatValue } from '../../domain/format'
import { buildPivot } from '../../domain/pivot'
import { REACH_BY_MARKET, clientsInSeveralMarkets } from '../../domain/tutorial'
import { noop, useMessages, useRunAndExplain, type StepProps } from './shared'

/** Step 4: a count of people. The second trap, and the one a percentage lesson does not prepare you for. */
export function ReachStep({ api, answers, answer }: StepProps) {
  const [state, retry] = useRunAndExplain(api, REACH_BY_MARKET, 'reached')
  const [messages] = useMessages(api)
  const choice = answers.reach
  const overlap = messages.status === 'success' ? clientsInSeveralMarkets(messages.data.rows) : []
  return (
    <>
      <p className="lead">
        <strong>Reach</strong> is the number of different clients who received at least one message. This time there is no division, only
        counting. Surely counts can simply be added?
      </p>
      <Remote state={state} retry={retry}>
        {({ run, explain }) => {
          const pivot = buildPivot(run, 'reached')
          const shown = { ...pivot, rows: choice === undefined ? pivot.rows.filter((r) => r.kind !== 'total') : pivot.rows }
          const total = run.nodes.find((n) => n.scope.length === 0)?.values.reached ?? null
          const sum = explain.naive?.value ?? null
          return (
            <div className="stack">
              <Pivot pivot={shown} selected={null} onSelect={noop} readOnly />
              <Predict
                id="reach"
                question="How many different clients did we reach in total?"
                correct="distinct"
                answer={choice}
                onAnswer={(c) => answer('reach', c)}
                choices={[
                  { id: 'sum', label: <strong>{formatValue(sum, 'number')}</strong>, detail: 'Add up the cells above.' },
                  { id: 'distinct', label: <strong>{formatValue(total, 'number')}</strong>, detail: 'Count each client once, wherever they were reached.' },
                ]}
              >
                <p>
                  Adding the cells gives {formatValue(sum, 'number')}, but only <strong>{formatValue(total, 'number')}</strong> different people were
                  reached: some clients appear in more than one cell.
                </p>
                {overlap.length > 0 && (
                  <ul className="overlap" data-testid="overlap">
                    {overlap.map((o) => (
                      <li key={o.client}>
                        Client <code>{o.client}</code> was reached in <strong>{o.markets.join(' and ')}</strong>: counted in each of those cells, once in the total.
                      </li>
                    ))}
                  </ul>
                )}
                <ExplainPanel e={explain} />
              </Predict>
            </div>
          )
        }}
      </Remote>
      {choice === undefined && <Callout kind="try">Look at the three cells, then decide before you reveal.</Callout>}
      <div className="two">
        <Callout kind="idea">
          A count of <em>messages</em> adds up, because a message sits in exactly one cell. A count of <em>people</em> does not, because a person can
          sit in several. The total has to <strong>look at the people again</strong>.
        </Callout>
        <Callout kind="remember">Three kinds of number, three ways to total: counts add; rates add their counts then divide; unique counts recount the people.</Callout>
      </div>
    </>
  )
}
