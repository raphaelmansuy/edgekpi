import type { Locator, Page } from '@playwright/test'
import path from 'node:path'

/** Screenshots are evidence: they live with the specification, not in a build folder. */
export const SHOTS = path.resolve(import.meta.dirname, '../../../specs/ux-demo/e2e/screenshots')

export async function shot(page: Page, name: string, options: { fullPage?: boolean } = {}) {
  await page.waitForTimeout(150)
  // a sticky header would be stitched into the middle of a full-page capture
  const style = await page.addStyleTag({ content: '.topbar { position: static !important; } .builder, .outline { position: static !important; }' })
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: options.fullPage ?? true, animations: 'disabled' })
  await style.evaluate((el) => el.remove())
}

/** Wait until the report on screen is a finished one: no spinner and a lifecycle that reached its end. */
export async function reportReady(page: Page) {
  await page.getByTestId('result-card').waitFor()
  await page.locator('[data-testid="result-body"][data-stale="false"]').waitFor()
  await page.locator('[data-testid="stepper"] [data-state="RECONCILED"][data-reached="true"]').waitFor()
}

const exact = (text: string) => new RegExp(`^\\s*${text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`)

/** The cell at a row label and a column label of the pivot on screen. */
export async function pivotCell(page: Page, row: string, col: string): Promise<Locator> {
  const heads = await page.locator('table.pivot thead th').allTextContents()
  const index = heads.findIndex((h) => exact(col).test(h))
  if (index < 1) throw new Error(`no column "${col}" among ${JSON.stringify(heads)}`)
  const line = page.locator('table.pivot tbody tr').filter({ has: page.locator('th.rowhead', { hasText: exact(row) }) })
  return line.locator('td').nth(index - 1)
}

export async function rowLabels(page: Page): Promise<string[]> {
  return (await page.locator('table.pivot tbody th.rowhead').allTextContents()).map((t) => t.trim())
}

export async function openRun(page: Page, hash = '') {
  await page.goto(`/${hash}`)
  await reportReady(page)
}
