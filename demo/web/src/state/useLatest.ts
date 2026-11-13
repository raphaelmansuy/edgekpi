import { useCallback, useEffect, useReducer, useRef } from 'react'
import type { ApiResult } from '../api/types'
import { asyncReducer, initialAsync, type AsyncState } from './asyncState'

/** Runs `call` on demand and keeps only the latest answer. `run` returns the result so callers can chain on it. */
export function useLatest<A extends unknown[], T>(call: (...args: A) => Promise<ApiResult<T>>) {
  const [state, dispatch] = useReducer(asyncReducer<T>, undefined, initialAsync<T>)
  const seq = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const run = useCallback(
    async (...args: A): Promise<ApiResult<T>> => {
      const mine = ++seq.current
      dispatch({ type: 'start', seq: mine })
      const result = await call(...args)
      if (mounted.current) dispatch({ type: 'finish', seq: mine, result })
      return result
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [call],
  )
  return [state as AsyncState<T>, run] as const
}

/** Runs `call` when `key` changes (and on mount), keeping only the latest answer. `again` re-runs it, for a Retry. */
export function useAutoLatest<T>(call: () => Promise<ApiResult<T>>, key: string) {
  const latest = useRef(call)
  latest.current = call
  const stable = useCallback(() => latest.current(), [])
  const [state, run] = useLatest(stable)
  useEffect(() => {
    void run()
  }, [run, key])
  return [state as AsyncState<T>, run] as const
}
