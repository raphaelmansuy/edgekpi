import { useEffect, useState } from 'react'

export const ROUTES = [
  { id: 'tutorial', label: 'Tutorial', hint: 'Learn the problem and the fix in nine short steps' },
  { id: 'report', label: 'Report', hint: 'Build a report and check it' },
  { id: 'catalogue', label: 'Catalogue', hint: 'What a definition says' },
  { id: 'backends', label: 'Backends', hint: 'One definition, three statements' },
  { id: 'migration', label: 'Migration', hint: 'From legacy SQL templates' },
  { id: 'assistant', label: 'Assistant', hint: 'A request from loose words' },
  { id: 'lab', label: 'Edge-case lab', hint: 'Things that go wrong, on purpose' },
] as const

export type RouteId = (typeof ROUTES)[number]['id']

/** `#/lab` gives 'lab'. An unknown or empty hash falls back to the report and says so (EC-D-13). */
export function parseHash(hash: string): { route: RouteId; unknown: string | null; param: string | null } {
  const parts = hash.replace(/^#\/?/, '').split('?')[0]?.split('/') ?? []
  const name = parts[0] ?? ''
  const param = parts[1] ? parts[1] : null
  const found = ROUTES.find((r) => r.id === name)
  if (found) return { route: found.id, unknown: null, param }
  return { route: 'report', unknown: name === '' ? null : name, param: null }
}

export function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash)
  useEffect(() => {
    const on = () => setHash(window.location.hash)
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return parseHash(hash)
}

export const go = (route: RouteId, param?: string | number) => {
  window.location.hash = param === undefined ? `#/${route}` : `#/${route}/${param}`
}
