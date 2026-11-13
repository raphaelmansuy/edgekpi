import type { ReactNode } from 'react'

/** `marks` are fragments: every line that contains one is highlighted, so a reader is told where to look. */
export function CodeBlock({ text, label, right, testId, marks = [] }: { text: string; label?: string; right?: ReactNode; testId?: string; marks?: string[] }) {
  const lines = text.split('\n')
  return (
    <div>
      {(label || right) && (
        <div className="code-label">
          <span>{label}</span>
          {right}
        </div>
      )}
      <pre className="code" data-testid={testId} tabIndex={0}>
        {marks.length === 0
          ? text
          : lines.map((line, i) => {
              const hit = marks.some((m) => line.includes(m))
              return (
                <span key={i} className={hit ? 'hl' : undefined} data-hl={hit || undefined}>
                  {line}
                  {'\n'}
                </span>
              )
            })}
      </pre>
    </div>
  )
}
