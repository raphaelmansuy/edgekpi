import type { ReactNode } from 'react'
import type { Status } from '../api/types'

export type Tone = 'blue' | 'green' | 'peach' | 'pink' | 'yellow' | 'lav' | 'mint' | 'gray'

export function Card({ title, sub, actions, children, flush = false, testId }: { title?: string; sub?: ReactNode; actions?: ReactNode; children: ReactNode; flush?: boolean; testId?: string }) {
  return (
    <section className="card" data-testid={testId}>
      {(title || actions) && (
        <header className="card-head">
          <div>
            {title && <h2>{title}</h2>}
            {sub && <div className="sub">{sub}</div>}
          </div>
          {actions}
        </header>
      )}
      <div className={flush ? '' : 'card-body'}>{children}</div>
    </section>
  )
}

export function Pill({ tone = 'gray', children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`pill ${tone}`} title={title}>
      {children}
    </span>
  )
}

const STATUS_TONE: Record<Status, Tone> = { confirmed: 'green', unconfirmed: 'yellow', draft: 'peach' }
const STATUS_MARK: Record<Status, string> = { confirmed: '●', unconfirmed: '◌', draft: '✎' }

/** The status is the word, never only a colour (EC-D-15). */
export function StatusPill({ status }: { status: Status }) {
  return (
    <Pill tone={STATUS_TONE[status]} title={`Status: ${status}`}>
      <span aria-hidden>{STATUS_MARK[status]}</span> {status}
    </Pill>
  )
}

export function Chip({ label, onRemove, tone, title }: { label: string; onRemove?: () => void; tone?: 'peach'; title?: string }) {
  return (
    <span className={`chip ${tone ?? ''}`} title={title}>
      {label}
      {onRemove && (
        <button type="button" aria-label={`Remove ${label}`} onClick={onRemove}>
          ✕
        </button>
      )}
    </span>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return <span className="spinner" role="status" aria-label={label} />
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty" data-testid="empty-state">
      <div className="empty-glyph" aria-hidden>∅</div>
      <strong>{title}</strong>
      {children}
    </div>
  )
}

export function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: { id: T; label: string; disabled?: boolean; title?: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={value === o.id}
          aria-disabled={o.disabled || undefined}
          title={o.title}
          onClick={() => !o.disabled && onChange(o.id)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Check({ checked, onChange, children, disabled }: { checked: boolean; onChange: (v: boolean) => void; children: ReactNode; disabled?: boolean }) {
  return (
    <label className="check">
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  )
}

export function PageHead({ title, children, right }: { title: string; children?: ReactNode; right?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {right}
    </div>
  )
}
