import type { Member } from '../api/types'

/** A NULL member is a member, not a blank: it reads "(none)" and never collides with a Total. */
export function memberLabel(member: Member): string {
  return member === null ? '(none)' : String(member)
}

export function formatValue(value: number | null | undefined, format: 'number' | 'percent'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–'
  if (format === 'percent') return `${(value * 100).toFixed(1)}%`
  return Number.isInteger(value) ? value.toLocaleString('en-US') : value.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

/** 'send_year' reads 'Send year'. Labels of dimensions are ids in the model; the screen makes them readable. */
export function titleCase(id: string): string {
  const text = id.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`
}
