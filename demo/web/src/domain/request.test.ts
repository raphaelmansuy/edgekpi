import { describe, expect, it } from 'vitest'
import type { Catalogue } from '../api/types'
import { addDimension, addKpi, canRun, dateHint, defaultRequest, describeRequest, freeDimensions, publishedProblems, removeDimension, removeKpi, requestKey, setDate, setWhere, toApiRequest } from './request'
import { SCENARIOS, summarise } from './scenarios'

const catalogue = {
  kpis: [
    { id: 'sent', label: 'Message Sent', status: 'confirmed' },
    { id: 'reached', label: 'Reach', status: 'unconfirmed' },
  ],
  dimensions: [{ id: 'typology' }, { id: 'market' }, { id: 'send_year' }],
} as unknown as Catalogue

describe('request', () => {
  it('does not add a KPI twice', () => {
    const r = defaultRequest()
    expect(addKpi(r, 'sent').kpis).toEqual(r.kpis)
    expect(removeKpi(r, 'sent').kpis).not.toContain('sent')
  })
  it('offers only dimensions that are not on an axis yet (EC-D-08)', () => {
    const r = defaultRequest()
    expect(freeDimensions(r, ['typology', 'market', 'tier'])).toEqual(['tier'])
  })
  it('refuses to put a dimension on two axes', () => {
    const r = defaultRequest()
    expect(addDimension(r, 'cols', 'typology')).toBe(r)
    expect(addDimension(r, 'rows', 'tier').rows).toEqual(['typology', 'tier'])
    expect(removeDimension(r, 'rows', 'typology').rows).toEqual([])
  })
  it('will not run without a KPI (EC-D-07)', () => {
    expect(canRun({ ...defaultRequest(), kpis: [] })).toEqual({ ok: false, reason: 'Pick at least one KPI.' })
    expect(canRun(defaultRequest())).toEqual({ ok: true })
  })
  it('warns when the end date is not after the start date (EC-D-20)', () => {
    const r = setDate(setDate(defaultRequest(), 'start_date', '2026-03-01'), 'end_date', '2026-03-01')
    expect(dateHint(r)).toMatch(/selects nothing/)
    expect(dateHint(setDate(r, 'end_date', '2026-04-01'))).toBeNull()
    expect(dateHint(defaultRequest())).toBeNull()
  })
  it('names the KPIs a published report would refuse (EC-D-21)', () => {
    const r = { ...defaultRequest(), kpis: ['sent', 'reached'], published: true }
    expect(publishedProblems(r, catalogue)).toEqual(['reached'])
    expect(publishedProblems({ ...r, published: false }, catalogue)).toEqual([])
  })
  it('drops empty parameters before they reach the service', () => {
    const r = setDate(defaultRequest(), 'start_date', '2026-01-01')
    expect(setDate(r, 'start_date', '').params).toEqual({})
    expect(toApiRequest({ ...r, params: { start_date: '', end_date: '2026-02-01' } }).params).toEqual({ end_date: '2026-02-01' })
  })
  it('a filter with nothing ticked is no filter', () => {
    expect(setWhere(defaultRequest(), 'market', []).where).toEqual([])
    expect(setWhere(defaultRequest(), 'market', ['HK']).where).toEqual([{ dim: 'market', in: ['HK'] }])
    expect(setWhere(defaultRequest(), null, ['HK']).where).toEqual([])
  })
  it('describes a request in words', () => {
    const r = { ...defaultRequest(), kpis: ['sent', 'reached'], rows: ['send_year'], where: [{ dim: 'market', in: ['HK', 'SG'] }] }
    expect(describeRequest(r, catalogue)).toBe('Message Sent, Reach by Send year across Market where Market is HK or SG')
  })
  it('keys two equal requests alike and a changed backend differently', () => {
    expect(requestKey(defaultRequest(), 'sql')).toBe(requestKey(defaultRequest(), 'sql'))
    expect(requestKey(defaultRequest(), 'sql')).not.toBe(requestKey(defaultRequest(), 'malloy'))
  })
})

describe('scenarios', () => {
  it('have unique ids, each tied to an edge case of the library', () => {
    expect(new Set(SCENARIOS.map((s) => s.id)).size).toBe(SCENARIOS.length)
    expect(SCENARIOS.every((s) => /^EC-L-\d\d$/.test(s.ec))).toBe(true)
  })
  it('summarise a request in a line', () => {
    expect(summarise({ kpis: ['sent'], rows: ['market'], where: [{ dim: 'market', in: ['HK', null] }], params: { start_date: '2026-01-01' }, published: true })).toBe(
      'KPIs sent · rows market · market in HK, NULL · start_date = 2026-01-01 · published',
    )
  })
})
