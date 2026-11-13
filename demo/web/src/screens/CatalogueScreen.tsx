import { Card, PageHead, Pill, StatusPill } from '../components/ui'
import { plural, titleCase } from '../domain/format'
import { useCatalogue } from '../state/AppState'

export function CatalogueScreen() {
  const c = useCatalogue()
  if (!c) return null
  return (
    <>
      <PageHead title="Catalogue" right={<Pill tone="lav">model {c.model} · {c.version}</Pill>}>
        One definition, read by every backend. A measure is one aggregate; a KPI is a formula over measures, so a total is recomputed, never averaged.
      </PageHead>
      <div className="stack">
        <Card title="KPIs" sub="Only confirmed KPIs pass a published report" testId="kpi-table" flush>
          <table className="table">
            <thead>
              <tr><th>KPI</th><th>Status</th><th>Formula</th><th>Built from</th><th>Owner</th></tr>
            </thead>
            <tbody>
              {c.kpis.map((k) => (
                <tr key={k.id} data-kpi={k.id}>
                  <td><strong>{k.label}</strong><div className="muted small mono">{k.id}</div></td>
                  <td><StatusPill status={k.status} /></td>
                  <td><code className="mono">{k.formula}</code></td>
                  <td>
                    <div className="row" style={{ gap: 6 }}>
                      {k.measures.map((m) => {
                        const measure = c.measures.find((x) => x.id === m)
                        return <Pill key={m} tone={measure?.kind === 'unique' ? 'peach' : 'blue'} title={measure?.expr}>{m}{measure?.kind === 'unique' ? ' · distinct' : ''}</Pill>
                      })}
                    </div>
                  </td>
                  <td className="muted">{k.owner ?? '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div className="two">
          <Card title="Measures" sub="One aggregate each; the kind is read from the expression" flush testId="measure-table">
            <table className="table">
              <thead><tr><th>Measure</th><th>Expression</th><th>Parts add up?</th></tr></thead>
              <tbody>
                {c.measures.map((m) => (
                  <tr key={m.id}>
                    <td className="mono">{m.id}</td>
                    <td><code className="mono">{m.expr}</code></td>
                    <td>{m.additive ? <Pill tone="green">✓ additive</Pill> : <Pill tone="peach" title="Counted once in a total: the parts need not add up">⚠ {m.kind}</Pill>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="stack">
            <Card title="Dimensions">
              <div className="stack" style={{ gap: 10 }}>
                {c.dimensions.map((d) => (
                  <div key={d.id} className="row">
                    <strong style={{ minWidth: 90 }}>{titleCase(d.id)}</strong>
                    <code className="mono muted">{d.expr}</code>
                    <span className="grow" />
                    <span className="small muted">{d.members.map((m) => (m === null ? '(none)' : String(m))).join(', ')}</span>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="Filters and parameters" sub="Bound, never interpolated">
              <div className="stack" style={{ gap: 10 }}>
                {c.filters.map((f) => (
                  <div key={f.id}>
                    <div className="row"><strong>{f.id}</strong>{f.optional && <Pill tone="gray">optional</Pill>}{Object.entries(f.params).map(([n, t]) => <Pill key={n} tone="lav">:{n} · {t}</Pill>)}</div>
                    <code className="mono muted">{f.predicate}</code>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>

        <Card title="Grain" sub="Proved by reading the data, not assumed" testId="grain">
          <div className="stats">
            <div className="stat" style={{ background: 'var(--blue)', borderColor: 'var(--blue-line)', color: 'var(--blue-ink)' }}><b>{c.grain.fact_rows}</b><span>rows in {c.source}</span></div>
            <div className="stat" style={{ background: 'var(--blue)', borderColor: 'var(--blue-line)', color: 'var(--blue-ink)' }}><b>{c.grain.joined_rows}</b><span>rows after {c.joins.map((j) => `LEFT JOIN ${j.table}`).join(', ') || 'no joins'}</span></div>
            <div className="stat" style={{ background: 'var(--green)', borderColor: 'var(--green-line)', color: 'var(--green-ink)' }}><b>{c.grain.distinct_keys}</b><span>distinct {c.key}</span></div>
          </div>
          <p className="small muted" style={{ marginTop: 10 }}>
            {c.grain.fact_rows === c.grain.joined_rows && c.grain.joined_rows === c.grain.distinct_keys
              ? `The join keeps exactly one row per message (${plural(c.grain.fact_rows, 'message')}), so no count is inflated. This proves today's data only.`
              : 'The join changes the grain.'}
          </p>
        </Card>
      </div>
    </>
  )
}
