import { useEffect, useState } from 'react'
import type { BackendId, Catalogue, ReportRequest } from '../api/types'
import { addDimension, addKpi, canRun, dateHint, freeDimensions, publishedProblems, removeDimension, removeKpi, setDate, setWhere } from '../domain/request'
import { titleCase } from '../domain/format'
import { Check, Chip, Segmented } from './ui'

interface Props {
  catalogue: Catalogue
  request: ReportRequest
  onChange: (next: ReportRequest) => void
  backend: BackendId
  onBackend: (b: BackendId) => void
  onRun: () => void
  running: boolean
}

function DimensionAxis({ axis, title, catalogue, request, onChange }: { axis: 'rows' | 'cols'; title: string; catalogue: Catalogue; request: ReportRequest; onChange: (r: ReportRequest) => void }) {
  const free = freeDimensions(request, catalogue.dimensions.map((d) => d.id))
  const label = (id: string) => titleCase(id)
  return (
    <div className="field">
      <span className="label">{title}</span>
      <div className="chips" data-testid={`axis-${axis}`}>
        {request[axis].length === 0 && <span className="hint">None: one {axis === 'rows' ? 'row' : 'column'}</span>}
        {request[axis].map((d) => (
          <Chip key={d} label={label(d)} onRemove={() => onChange(removeDimension(request, axis, d))} />
        ))}
        {free.length > 0 && (
          <select className="select" aria-label={`Add to ${title.toLowerCase()}`} value="" onChange={(e) => e.target.value && onChange(addDimension(request, axis, e.target.value))}>
            <option value="">+ add</option>
            {free.map((d) => (
              <option key={d} value={d}>
                {label(d)}
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  )
}

export function Builder({ catalogue, request, onChange, backend, onBackend, onRun, running }: Props) {
  const remaining = catalogue.kpis.filter((k) => !request.kpis.includes(k.id))
  const run = canRun(request)
  const hint = dateHint(request)
  const refused = publishedProblems(request, catalogue)
  const [chosen, setChosen] = useState(request.where[0]?.dim ?? '')
  const external = request.where[0]?.dim
  useEffect(() => {
    if (external) setChosen(external)
  }, [external])
  const filterDim = chosen
  const filterMembers = catalogue.dimensions.find((d) => d.id === filterDim)?.members ?? []
  const selected = request.where[0]?.in ?? []

  return (
    <form className="stack" onSubmit={(e) => { e.preventDefault(); onRun() }} aria-label="Report builder" data-testid="builder">
      <div className="field">
        <span className="label">KPIs</span>
        <div className="chips" data-testid="kpi-chips">
          {request.kpis.map((id) => {
            const k = catalogue.kpis.find((x) => x.id === id)
            const warn = refused.includes(id)
            return <Chip key={id} label={`${k?.label ?? id}${warn ? ' ⚠' : ''}`} tone={warn ? 'peach' : undefined} title={warn ? 'Not confirmed: a published report would refuse it' : undefined} onRemove={() => onChange(removeKpi(request, id))} />
          })}
          {remaining.length > 0 && (
            <select className="select" aria-label="Add a KPI" value="" onChange={(e) => e.target.value && onChange(addKpi(request, e.target.value))}>
              <option value="">+ add</option>
              {remaining.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.label}
                  {k.status !== 'confirmed' ? ` (${k.status})` : ''}
                </option>
              ))}
            </select>
          )}
        </div>
        {!run.ok && <span className="hint warn" role="note">{run.reason}</span>}
      </div>

      <div className="divider" />
      <DimensionAxis axis="rows" title="Rows" catalogue={catalogue} request={request} onChange={onChange} />
      <DimensionAxis axis="cols" title="Columns" catalogue={catalogue} request={request} onChange={onChange} />
      <div className="row">
        <Check checked={request.totals.rows} onChange={(v) => onChange({ ...request, totals: { ...request.totals, rows: v } })}>Row totals</Check>
        <Check checked={request.totals.cols} onChange={(v) => onChange({ ...request, totals: { ...request.totals, cols: v } })}>Column totals</Check>
      </div>

      <div className="divider" />
      <div className="field">
        <span className="label">Dates</span>
        <div className="dates">
          <label>
            From
            <input className="input" type="date" aria-label="From date" value={request.params.start_date ?? ''} onChange={(e) => onChange(setDate(request, 'start_date', e.target.value))} />
          </label>
          <label>
            To
            <input className="input" type="date" aria-label="To date" value={request.params.end_date ?? ''} onChange={(e) => onChange(setDate(request, 'end_date', e.target.value))} />
          </label>
        </div>
        <span className="hint">The end date is excluded. Empty means no limit.</span>
        {hint && <span className="hint warn" role="note" data-testid="date-hint">{hint}</span>}
      </div>

      <div className="field">
        <span className="label">Filter</span>
        <select className="select" aria-label="Filter by" value={filterDim} onChange={(e) => { setChosen(e.target.value); onChange(setWhere(request, e.target.value || null, [])) }}>
          <option value="">No filter</option>
          {catalogue.dimensions.map((d) => (
            <option key={d.id} value={d.id}>
              {titleCase(d.id)}
            </option>
          ))}
        </select>
        {filterDim && (
          <div className="members" data-testid="filter-members">
            {filterMembers.map((m) => {
              const text = m === null ? '(none)' : String(m)
              return (
                <Check key={text} checked={m !== null && selected.includes(m as string | number)} disabled={m === null} onChange={(v) => onChange(setWhere(request, filterDim, v ? [...selected, m as string | number] : selected.filter((s) => s !== m)))}>
                  {text}
                </Check>
              )
            })}
          </div>
        )}
        {filterDim && selected.length === 0 && <span className="hint">Tick at least one member, or choose “No filter”.</span>}
      </div>

      <div className="divider" />
      <Check checked={request.published} onChange={(v) => onChange({ ...request, published: v })}>
        Published report <span className="muted small">(confirmed KPIs only)</span>
      </Check>
      {refused.length > 0 && <span className="hint warn" role="note" data-testid="published-hint">The service will refuse: {refused.join(', ')}.</span>}

      <div className="field">
        <span className="label">Backend</span>
        <Segmented
          label="Backend"
          value={backend}
          onChange={onBackend}
          options={catalogue.backends.map((b) => ({ id: b.id, label: b.id === 'sql' ? 'SQL' : b.id === 'malloy' ? 'Malloy' : 'Metric view', disabled: !b.available, title: b.available ? b.label : (b.reason ?? 'unavailable') }))}
        />
        {catalogue.backends.filter((b) => !b.available).map((b) => (
          <span key={b.id} className="hint" data-testid={`backend-off-${b.id}`}>
            {b.id === 'metric-view' ? 'Metric view' : b.id}: {b.reason}
          </span>
        ))}
      </div>

      <button type="submit" className="btn primary" disabled={!run.ok || running} data-testid="run">
        {running ? 'Running…' : 'Run report'}
      </button>
    </form>
  )
}
