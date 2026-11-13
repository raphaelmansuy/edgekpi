import type { ApiError, ApiResult } from '../api/types'

/** Four states of any call. `previous` keeps the last good data visible, dimmed, while a newer call runs or fails. */
export type AsyncState<T> =
  | { status: 'idle'; seq: number }
  | { status: 'loading'; seq: number; previous?: T }
  | { status: 'success'; seq: number; data: T }
  | { status: 'error'; seq: number; error: ApiError; previous?: T }

export type AsyncAction<T> = { type: 'start'; seq: number } | { type: 'finish'; seq: number; result: ApiResult<T> }

export const initialAsync = <T,>(): AsyncState<T> => ({ status: 'idle', seq: 0 })

const dataOf = <T,>(s: AsyncState<T>): T | undefined => (s.status === 'success' ? s.data : s.status === 'idle' ? undefined : s.previous)

/**
 * Latest wins. A `finish` whose seq is not the current one belongs to an older call and is ignored, so a slow answer
 * can never overwrite a newer one (EC-D-04, EC-D-19).
 */
export function asyncReducer<T>(state: AsyncState<T>, action: AsyncAction<T>): AsyncState<T> {
  if (action.type === 'start') return { status: 'loading', seq: action.seq, previous: dataOf(state) }
  if (action.seq !== state.seq) return state
  if (action.result.ok) return { status: 'success', seq: state.seq, data: action.result.data }
  return { status: 'error', seq: state.seq, error: action.result.error, previous: dataOf(state) }
}

export { dataOf }
