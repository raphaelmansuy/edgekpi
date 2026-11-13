import { expect, test } from '@playwright/test'
import { openRun, pivotCell, reportReady, shot } from '../helpers'

test.describe('Resilience of the Report screen', () => {
  test('EC-D-01: an unreachable service is said so, with a retry that recovers', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort())
    await page.goto('/')
    await expect(page.getByTestId('error-code')).toHaveText('SERVICE_UNREACHABLE')
    await expect(page.getByTestId('service-status')).toContainText('service unreachable')
    await shot(page, '12-service-down')
    await page.unroute('**/api/**')
    await page.getByRole('button', { name: 'Retry' }).click()
    await reportReady(page)
    await expect(page.getByTestId('service-status')).toContainText('service ok')
  })

  test('EC-D-03: while a run is slow the last good result stays, dimmed, with a spinner', async ({ page }) => {
    await openRun(page)
    await page.route('**/api/run', async (route) => {
      await new Promise((r) => setTimeout(r, 1800))
      await route.continue()
    })
    await page.getByRole('button', { name: 'Remove Reach' }).click()
    await expect(page.getByTestId('loading')).toBeVisible()
    await expect(page.locator('[data-testid="result-body"]')).toHaveAttribute('data-stale', 'true')
    await expect(page.getByTestId('run')).toBeDisabled()
    await expect(page.getByRole('tab', { name: 'Reach' })).toBeVisible()
    await shot(page, '13-report-loading')
    await page.unroute('**/api/run')
    await reportReady(page)
    await expect(page.getByRole('tab', { name: 'Reach' })).toHaveCount(0)
  })

  test('EC-D-04, EC-D-19: a slow answer to an older request never overwrites a newer one', async ({ page }) => {
    let calls = 0
    await page.route('**/api/run', async (route) => {
      calls += 1
      if (calls === 1) await new Promise((r) => setTimeout(r, 2500))
      await route.continue()
    })
    await page.goto('/')
    await expect(page.getByTestId('loading')).toBeVisible()
    await page.getByRole('button', { name: 'Remove Reach' }).click()
    await expect(page.getByRole('tab')).toHaveText(['Message Sent', 'Delivery Rate'])
    await page.waitForTimeout(3200)
    expect(calls).toBeGreaterThanOrEqual(2)
    await expect(page.getByRole('tab')).toHaveText(['Message Sent', 'Delivery Rate'])
  })

  test('EC-D-02: a malformed answer from the service is shown as an error, not a blank page', async ({ page }) => {
    await openRun(page)
    await page.route('**/api/run', (route) => route.fulfill({ status: 200, contentType: 'text/html', body: '<html>proxy error</html>' }))
    await page.getByRole('button', { name: 'Remove Reach' }).click()
    await expect(page.getByTestId('error-code')).toHaveText('BAD_RESPONSE')
    await expect(page.getByTestId('result-body')).toHaveAttribute('data-stale', 'true')
  })

  test('EC-D-14: the request survives moving between screens', async ({ page }) => {
    await openRun(page)
    await page.getByLabel('Add to rows').selectOption('tier')
    await reportReady(page)
    await page.getByRole('link', { name: 'Catalogue' }).click()
    await expect(page.getByRole('heading', { name: 'Catalogue' })).toBeVisible()
    await page.getByRole('link', { name: 'Report' }).click()
    await expect(page.getByTestId('axis-rows')).toContainText('Tier')
    await reportReady(page)
  })

  test('EC-D-13: a deep link opens its screen; an unknown one falls back and says so', async ({ page }) => {
    await page.goto('/#/lab')
    await expect(page.getByRole('heading', { name: 'Edge-case lab' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Edge-case lab' })).toHaveAttribute('aria-current', 'page')
    await page.goto('/#/nowhere')
    await expect(page.getByTestId('route-notice')).toContainText('nowhere')
    await reportReady(page)
  })

  test('EC-D-16: a narrow window scrolls the table, not the page', async ({ page }) => {
    await page.setViewportSize({ width: 760, height: 900 })
    await openRun(page)
    await page.getByLabel('Add to rows').selectOption('tier')
    await page.getByLabel('Add to columns').selectOption('send_year')
    await reportReady(page)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
    await expect(await pivotCell(page, 'Total', 'All')).toBeVisible()
    await shot(page, '14-report-narrow')
  })
})
