import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { EdgeKpiApi } from '../api/client'
import type { BackendId, Catalogue, ReportRequest } from '../api/types'
import { DEFAULT_BACKEND, defaultRequest } from '../domain/request'
import type { AsyncState } from './asyncState'
import { useLatest } from './useLatest'

interface AppValue {
  api: EdgeKpiApi
  catalogue: AsyncState<Catalogue>
  reloadCatalogue: () => void
  request: ReportRequest
  setRequest: (next: ReportRequest | ((current: ReportRequest) => ReportRequest)) => void
  backend: BackendId
  setBackend: (b: BackendId) => void
  /** what the learner chose in the tutorial's predictions; survives leaving the tutorial and coming back */
  answers: Record<string, string>
  answer: (id: string, choice: string | null) => void
}

const AppContext = createContext<AppValue | null>(null)

/** The request and the backend live above the screens, so they survive navigation (EC-D-14). */
export function AppProvider({ api, children }: { api: EdgeKpiApi; children: ReactNode }) {
  const [request, setRequest] = useState<ReportRequest>(defaultRequest)
  const [backend, setBackend] = useState<BackendId>(DEFAULT_BACKEND)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const answer = useCallback((id: string, choice: string | null) => {
    setAnswers((current) => {
      const next = { ...current }
      if (choice === null) delete next[id]
      else next[id] = choice
      return next
    })
  }, [])
  const load = useCallback(() => api.catalogue(), [api])
  const [catalogue, loadCatalogue] = useLatest(load)
  useEffect(() => {
    void loadCatalogue()
  }, [loadCatalogue])
  const value = useMemo<AppValue>(
    () => ({ api, catalogue, reloadCatalogue: () => void loadCatalogue(), request, setRequest, backend, setBackend, answers, answer }),
    [api, catalogue, loadCatalogue, request, backend, answers, answer],
  )
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp(): AppValue {
  const value = useContext(AppContext)
  if (!value) throw new Error('useApp must be used inside AppProvider')
  return value
}

/** The catalogue, for screens that cannot render without it. */
export function useCatalogue(): Catalogue | undefined {
  const { catalogue } = useApp()
  return catalogue.status === 'success' ? catalogue.data : undefined
}
