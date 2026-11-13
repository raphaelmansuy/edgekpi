import { describe, expect, it, vi } from 'vitest'
import { createHttpApi } from '../api/client'
import type { ApiResult } from '../api/types'
import { asyncReducer, dataOf, initialAsync, type AsyncState } from './asyncState'
import { parseHash } from './route'

const ok = <T,>(data: T): ApiResult<T> => ({ ok: true, data })
const bad = (code: string): ApiResult<number> => ({ ok: false, error: { code, message: code, states: [] } })

describe('asyncReducer', () => {
  it('goes idle, loading, success', () => {
    let s: AsyncState<number> = initialAsync()
    s = asyncReducer(s, { type: 'start', seq: 1 })
    expect(s.status).toBe('loading')
    s = asyncReducer(s, { type: 'finish', seq: 1, result: ok(7) })
    expect(s).toMatchObject({ status: 'success', data: 7 })
  })
  it('ignores the answer of an older call: latest wins (EC-D-04, EC-D-19)', () => {
    let s: AsyncState<number> = initialAsync()
    s = asyncReducer(s, { type: 'start', seq: 1 })
    s = asyncReducer(s, { type: 'start', seq: 2 })
    s = asyncReducer(s, { type: 'finish', seq: 2, result: ok(2) })
    s = asyncReducer(s, { type: 'finish', seq: 1, result: ok(1) })
    expect(dataOf(s)).toBe(2)
  })
  it('keeps the last good data while a newer call runs or fails (EC-D-03)', () => {
    let s: AsyncState<number> = asyncReducer(asyncReducer(initialAsync<number>(), { type: 'start', seq: 1 }), { type: 'finish', seq: 1, result: ok(5) })
    s = asyncReducer(s, { type: 'start', seq: 2 })
    expect(s).toMatchObject({ status: 'loading', previous: 5 })
    s = asyncReducer(s, { type: 'finish', seq: 2, result: bad('X') })
    expect(s).toMatchObject({ status: 'error', previous: 5 })
    expect(dataOf(s)).toBe(5)
  })
  it('an error with nothing before it has no data', () => {
    const s = asyncReducer(asyncReducer(initialAsync<number>(), { type: 'start', seq: 1 }), { type: 'finish', seq: 1, result: bad('X') })
    expect(dataOf(s)).toBeUndefined()
  })
})

describe('route', () => {
  it('reads a known screen', () => {
    expect(parseHash('#/lab')).toEqual({ route: 'lab', unknown: null, param: null })
    expect(parseHash('#/migration?x=1')).toEqual({ route: 'migration', unknown: null, param: null })
    expect(parseHash('#/tutorial/4')).toEqual({ route: 'tutorial', unknown: null, param: '4' })
  })
  it('falls back to the report and names an unknown one (EC-D-13)', () => {
    expect(parseHash('#/nowhere')).toEqual({ route: 'report', unknown: 'nowhere', param: null })
    expect(parseHash('')).toEqual({ route: 'report', unknown: null, param: null })
  })
})

describe('http api', () => {
  const answer = (status: number, body: unknown, asText = false) =>
    vi.fn().mockResolvedValue({ status, ok: status < 400, json: asText ? () => Promise.reject(new Error('not json')) : () => Promise.resolve(body) })

  it('turns a network failure into SERVICE_UNREACHABLE (EC-D-01)', async () => {
    const api = createHttpApi(vi.fn().mockRejectedValue(new TypeError('failed to fetch')) as unknown as typeof fetch)
    const r = await api.catalogue()
    expect(r).toMatchObject({ ok: false, error: { code: 'SERVICE_UNREACHABLE' } })
  })
  it('keeps the code and the message of a domain error (EC-D-02)', async () => {
    const api = createHttpApi(answer(422, { ok: false, error: { code: 'REQ_UNKNOWN_KPI', message: 'unknown KPI', states: ['FAILED'] } }) as unknown as typeof fetch)
    expect(await api.run({} as never, 'sql')).toEqual({ ok: false, error: { code: 'REQ_UNKNOWN_KPI', message: 'unknown KPI', states: ['FAILED'] } })
  })
  it('says so when the answer is not JSON', async () => {
    const api = createHttpApi(answer(502, null, true) as unknown as typeof fetch)
    expect(await api.catalogue()).toMatchObject({ ok: false, error: { code: 'BAD_RESPONSE' } })
  })
  it('does not trust a bare HTTP failure', async () => {
    const api = createHttpApi(answer(500, { something: 'else' }) as unknown as typeof fetch)
    expect(await api.catalogue()).toMatchObject({ ok: false, error: { code: 'HTTP_500' } })
  })
  it('posts JSON to the right path', async () => {
    const fetchMock = answer(200, { ok: true, nodes: [] })
    const api = createHttpApi(fetchMock as unknown as typeof fetch, '/api')
    await api.plan({ kpis: ['sent'] } as never, 'malloy')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/plan')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ request: { kpis: ['sent'] }, backend: 'malloy' })
  })
})
