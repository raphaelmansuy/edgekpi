import type { ReactNode } from 'react'

const KINDS = {
  idea: { icon: '💡', title: 'The idea' },
  try: { icon: '👆', title: 'Try it' },
  remember: { icon: '📌', title: 'Remember' },
  watch: { icon: '⚠', title: 'Watch out' },
} as const

/** A short box with a fixed role: the same four roles in every step, so a learner learns to read them. */
export function Callout({ kind, title, children }: { kind: keyof typeof KINDS; title?: string; children: ReactNode }) {
  const k = KINDS[kind]
  return (
    <aside className={`callout ${kind}`} data-callout={kind}>
      <div className="callout-icon" aria-hidden>
        {k.icon}
      </div>
      <div>
        <strong>{title ?? k.title}</strong>
        <div className="callout-body">{children}</div>
      </div>
    </aside>
  )
}
