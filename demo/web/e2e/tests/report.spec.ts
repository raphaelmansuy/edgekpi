import { expect, test } from '@playwright/test'
import { openRun, pivotCell, reportReady, rowLabels, shot } from '../helpers'

test.describe('Report: the main flow', () => {
  test('a default report is computed, checked and shown with every total', async ({ page }) => {
    await openRun(page)
    await expect(page.getByRole('tab')).toHaveText(['Message Sent', 'Delivery Rate', 'Reach'])
    await expect(page.locator('[data-testid="stepper"] .step.done')).toHaveCount(5)
    await expect(page.getByText('✓ 0 violations')).toBeVisible()
    await expect(page.getByTestId('estimate')).toContainText('4 scopes x 3 measures = 12 aggregate states, 1 of them distinct counts')
    await expect(await pivotCell(page, 'Total', 'All')).toHaveText('13')
    await shot(page, '01-report-default')
  })

  test('EC-D-05: a NULL member is its own row and is not the Total', async ({ page }) => {
    await openRun(page)
    expect(await rowLabels(page)).toEqual(['(none)', 'New', 'VIP', 'Total'])
    await expect(await pivotCell(page, '(none)', 'All')).toHaveText('1')
    await expect(await pivotCell(page, 'Total', 'All')).toHaveText('13')
    await expect(page.locator('.none-member')).toHaveText('(none)')
  })

  test('EC-D-10: a rate with a zero denominator is a dash, never NaN or null', async ({ page }) => {
    await openRun(page)
    await page.getByRole('tab', { name: 'Delivery Rate' }).click()
    await expect(await pivotCell(page, 'Total', 'JP')).toHaveText('0.0%')
    await page.getByLabel('Add a KPI').selectOption('open_rate')
    await reportReady(page)
    await page.getByRole('tab', { name: 'Open Rate' }).click()
    await expect(await pivotCell(page, 'VIP', 'JP')).toHaveText('–')
    await expect(page.locator('table.pivot')).not.toContainText('NaN')
    await expect(page.locator('table.pivot')).not.toContainText('null')
    await shot(page, '02-report-blank-rate')
  })

  test('two row dimensions give subtotals, labelled with their path', async ({ page }) => {
    await openRun(page)
    await page.getByLabel('Add to rows').selectOption('tier')
    await reportReady(page)
    const labels = await rowLabels(page)
    expect(labels).toContain('New / Gold')
    expect(labels).toContain('New / total')
    expect(labels.at(-1)).toBe('Total')
    expect(labels.indexOf('New / Gold')).toBeLessThan(labels.indexOf('New / total'))
    await expect(page.locator('tr.subtotal').first()).toBeVisible()
    await shot(page, '03-report-two-row-levels')
  })

  test('EC-D-08: a dimension already on an axis is not offered again', async ({ page }) => {
    await openRun(page)
    const options = await page.getByLabel('Add to columns').locator('option').allTextContents()
    expect(options).not.toContain('Typology')
    expect(options).not.toContain('Market')
    expect(options).toContain('Tier')
  })

  test('EC-D-07: with no KPI the report cannot run and says why', async ({ page }) => {
    await openRun(page)
    for (const name of ['Message Sent', 'Delivery Rate', 'Reach']) await page.getByRole('button', { name: `Remove ${name}` }).click()
    await expect(page.getByTestId('run')).toBeDisabled()
    await expect(page.getByText('Pick at least one KPI.')).toBeVisible()
    await expect(page.getByTestId('empty-state')).toContainText('No report yet')
    await expect(page.locator('table.pivot')).toHaveCount(0)
    await shot(page, '04-report-no-kpi')
  })

  test('removing and adding a KPI changes the tabs', async ({ page }) => {
    await openRun(page)
    await page.getByRole('button', { name: 'Remove Reach' }).click()
    await expect(page.getByRole('tab')).toHaveText(['Message Sent', 'Delivery Rate'])
    await page.getByLabel('Add a KPI').selectOption('ctor')
    await expect(page.getByRole('tab')).toHaveText(['Message Sent', 'Delivery Rate', 'Click-to-Open'])
  })
})

test.describe('Report: explaining a number', () => {
  test('a rate total is its own counts divided, not the mean of the cells', async ({ page }) => {
    await openRun(page)
    await page.getByRole('tab', { name: 'Delivery Rate' }).click()
    const cell = await pivotCell(page, 'Total', 'All')
    await expect(cell).toHaveText('76.9%')
    await cell.click()
    const explain = page.getByTestId('explain')
    await expect(explain).toContainText('Why is Delivery Rate 76.9%?')
    await expect(page.getByTestId('explain-terms')).toContainText('n_delivered')
    await expect(page.getByTestId('explain-terms')).toContainText('10')
    await expect(page.getByTestId('explain-terms')).toContainText('13')
    await expect(page.getByTestId('explain-value')).toHaveText('76.9%')
    await expect(page.getByTestId('explain-naive')).toHaveText('81.9%')
    await expect(explain).toContainText('Averaging the cells weights every cell equally')
    await shot(page, '05-explain-rate-total')
  })

  test('a distinct count total is below the sum of its cells', async ({ page }) => {
    await openRun(page)
    await page.getByRole('tab', { name: 'Reach' }).click()
    await (await pivotCell(page, 'Total', 'All')).click()
    await expect(page.getByTestId('explain')).toContainText('Why is Reach 6?')
    await expect(page.getByTestId('explain-terms')).toContainText('distinct')
    await expect(page.getByTestId('explain-naive')).toHaveText('9')
    await expect(page.getByTestId('explain-compare')).toContainText('Sum of the 3 cells by Market')
    await expect(page.getByTestId('explain')).toContainText('counted once in the total')
    await shot(page, '06-explain-distinct')
  })

  test('EC-D-11: a detail cell says there is nothing finer to compare', async ({ page }) => {
    await openRun(page)
    await (await pivotCell(page, 'New', 'HK')).click()
    await expect(page.getByTestId('explain-leaf')).toContainText('nothing finer')
  })

  test('EC-D-12: a cell is reachable and operable by keyboard', async ({ page }) => {
    await openRun(page)
    const cell = await pivotCell(page, 'VIP', 'All')
    await cell.focus()
    await expect(cell).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByTestId('explain')).toBeVisible()
    await page.getByRole('button', { name: 'Close' }).click()
    await expect(page.getByTestId('explain')).toHaveCount(0)
  })
})

test.describe('Report: filters, dates and publishing', () => {
  test('a date range narrows every total and filters stay on at the grand total', async ({ page }) => {
    await openRun(page)
    await page.getByLabel('From date').fill('2026-01-01')
    await reportReady(page)
    await expect(await pivotCell(page, 'Total', 'All')).toHaveText('8')
    await page.getByLabel('Filter by').selectOption('market')
    await page.getByLabel('HK').check()
    await reportReady(page)
    await expect(await pivotCell(page, 'Total', 'All')).toHaveText('5')
    await expect(page.locator('table.pivot thead th')).toHaveText(['Typology', 'HK', 'All'])
    await shot(page, '07-report-filtered')
  })

  test('EC-D-20: an end date on or before the start date is flagged before the service is asked', async ({ page }) => {
    await openRun(page)
    await page.getByLabel('From date').fill('2026-03-01')
    await page.getByLabel('To date').fill('2026-03-01')
    await expect(page.getByTestId('date-hint')).toContainText('selects nothing')
  })

  test('EC-D-09: nothing matching is an empty answer, not an error', async ({ page }) => {
    await page.goto('/')
    await reportReady(page)
    await page.getByLabel('From date').fill('2030-01-01')
    await expect(page.getByTestId('empty-state')).toContainText('No rows match')
    await expect(page.getByTestId('error-banner')).toHaveCount(0)
    await expect(page.getByText('✓ 0 violations')).toBeVisible()
    await shot(page, '08-report-empty')
  })

  test('EC-D-21: publishing with an unconfirmed KPI is flagged, refused by the service, and recoverable', async ({ page }) => {
    await openRun(page)
    await page.getByLabel(/Published report/).check()
    await expect(page.getByTestId('published-hint')).toContainText('reached')
    await expect(page.getByTestId('error-code')).toHaveText('REQ_UNCONFIRMED_KPI')
    await expect(page.locator('[data-testid="stepper"] .step.failed')).toHaveCount(1)
    await expect(page.getByTestId('error-banner')).not.toContainText('Traceback')
    await expect(page.getByTestId('error-banner').getByRole('button', { name: 'Retry' })).toHaveCount(0)
    await expect(page.getByTestId('error-banner')).toContainText('Change the report and it runs again.')
    await expect(page.getByTestId('stale-note')).toBeVisible()
    await expect(page.getByTestId('estimate')).toHaveCount(0)
    await shot(page, '09-report-published-refused')
    await page.getByRole('button', { name: /Remove Reach/ }).click()
    await reportReady(page)
    await expect(page.getByTestId('error-banner')).toHaveCount(0)
  })
})

test.describe('Report: backends', () => {
  test('EC-D-06: the metric view is offered but disabled, with the reason', async ({ page }) => {
    await openRun(page)
    const metric = page.getByRole('radio', { name: 'Metric view' })
    await expect(metric).toHaveAttribute('aria-disabled', 'true')
    await expect(page.getByTestId('backend-off-metric-view')).toContainText('needs a Databricks SQL warehouse')
    await metric.click({ force: true })
    await expect(page.getByRole('radio', { name: 'SQL' })).toHaveAttribute('aria-checked', 'true')
  })

  test('EC-D-18: Malloy, the slower backend, gives the same totals as SQL', async ({ page }) => {
    await openRun(page)
    const before = await (await pivotCell(page, 'Total', 'All')).textContent()
    await page.getByRole('radio', { name: 'Malloy' }).click()
    await expect(page.getByTestId('estimate')).toContainText('backend malloy')
    await reportReady(page)
    expect(await (await pivotCell(page, 'Total', 'All')).textContent()).toBe(before)
    await shot(page, '10-report-malloy')
  })

  test('EC-L-07: the statement shows bound parameters, never their values', async ({ page }) => {
    await openRun(page)
    await page.getByLabel('From date').fill('2026-01-01')
    await reportReady(page)
    await page.getByTestId('toggle-sql').click()
    const sql = page.getByTestId('statement-0')
    await expect(sql).toContainText('GROUP BY GROUPING SETS')
    await expect(sql).toContainText(':start_date')
    await expect(sql).not.toContainText('2026-01-01')
    await expect(page.getByTestId('statements')).toContainText('Bound: start_date = 2026-01-01')
    await shot(page, '11-report-statement')
  })
})
