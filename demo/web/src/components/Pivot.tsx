import type { Member } from '../api/types'
import { memberLabel, titleCase } from '../domain/format'
import type { AxisKey, Pivot as PivotModel, PivotCell } from '../domain/pivot'

export interface Selection {
  scope: string[]
  members: Member[]
}

const same = (a: Selection | null, c: PivotCell) => a !== null && JSON.stringify([a.scope, a.members]) === JSON.stringify([c.scope, c.members])

function RowLabel({ row }: { row: AxisKey }) {
  if (row.kind === 'total') return <>{row.label}</>
  return (
    <>
      {row.key.map((m, i) => (
        <span key={i}>
          {i > 0 && ' / '}
          {m === null ? <span className="none-member">{memberLabel(m)}</span> : memberLabel(m)}
        </span>
      ))}
      {row.kind === 'subtotal' && ' / total'}
    </>
  )
}

/** The reader-facing table of one KPI. A cell is a button in all but name: it opens the explanation. */
export function Pivot({ pivot, selected, onSelect, readOnly = false }: { pivot: PivotModel; selected: Selection | null; onSelect: (cell: PivotCell) => void; readOnly?: boolean }) {
  return (
    <div className="pivot-wrap">
      <table className="pivot" data-testid="pivot" aria-label={`${pivot.kpi.label} by ${pivot.rowDims.join(', ') || 'nothing'}`}>
        <thead>
          <tr>
            <th scope="col">{pivot.rowDims.map(titleCase).join(' / ') || 'All rows'}</th>
            {pivot.cols.map((c) => (
              <th key={c.id} scope="col" className={c.kind !== 'detail' ? 'colhead-total' : ''}>
                {c.key.map((m, i) => (
                  <span key={i}>
                    {i > 0 && ' / '}
                    {memberLabel(m)}
                  </span>
                ))}
                {c.kind === 'total' ? c.label : c.kind === 'subtotal' ? ' / total' : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pivot.rows.map((r) => (
            <tr key={r.id} className={r.kind} data-row-kind={r.kind}>
              <th scope="row" className="rowhead">
                <RowLabel row={r} />
              </th>
              {pivot.cols.map((c) => {
                const cell = pivot.cell(r, c)
                if (!cell) return <td key={c.id} className={`coltotal-${c.kind}`} aria-label="no data" />
                const open = () => onSelect(cell)
                if (readOnly)
                  return (
                    <td key={c.id} className={c.kind !== 'detail' ? 'coltotal' : ''} data-value={cell.value ?? ''}>
                      <span className={cell.value === null ? 'null-value' : ''}>{cell.text}</span>
                      {cell.bar !== null && <span className="bar" style={{ width: `${Math.round(cell.bar * 100)}%` }} />}
                    </td>
                  )
                return (
                  <td
                    key={c.id}
                    className={`cell ${c.kind !== 'detail' ? 'coltotal' : ''}`}
                    tabIndex={0}
                    role="gridcell"
                    aria-selected={same(selected, cell)}
                    aria-label={`${pivot.kpi.label}: ${cell.text}. Press Enter to explain.`}
                    data-value={cell.value ?? ''}
                    onClick={open}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        open()
                      }
                    }}
                  >
                    <span className={cell.value === null ? 'null-value' : ''}>{cell.text}</span>
                    {cell.bar !== null && <span className="bar" style={{ width: `${Math.round(cell.bar * 100)}%` }} />}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
