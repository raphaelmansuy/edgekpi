import { expect, test } from '@playwright/test'
import { shot } from '../helpers'

test.describe('Catalogue', () => {
  test('EC-D-15: every KPI shows its status as a word, and what does not add up is flagged', async ({ page }) => {
    await page.goto('/#/catalogue')
    const rows = page.locator('[data-testid="kpi-table"] tbody tr')
    await expect(rows).toHaveCount(6)
    await expect(page.locator('[data-kpi="reached"]')).toContainText('unconfirmed')
    await expect(page.locator('[data-kpi="reached"]')).toContainText('distinct')
    await expect(page.locator('[data-kpi="delivery_rate"]')).toContainText('ratio(n_delivered, n_sent)')
    await expect(page.locator('[data-kpi="sent"]')).toContainText('confirmed')
    await expect(page.getByTestId('measure-table')).toContainText('⚠ unique')
    await shot(page, '20-catalogue')
  })

  test('proves the grain from the data', async ({ page }) => {
    await page.goto('/#/catalogue')
    const grain = page.getByTestId('grain')
    await expect(grain).toContainText('13')
    await expect(grain).toContainText('rows after LEFT JOIN client')
    await expect(grain).toContainText('exactly one row per message')
  })
})

test.describe('Backends', () => {
  test('one report, three statements, each in its own language', async ({ page }) => {
    await page.goto('/#/backends')
    await expect(page.getByTestId('code-sql-0')).toContainText('GROUP BY GROUPING SETS')
    await expect(page.getByTestId('code-malloy-0')).toContainText('nest: s0')
    await expect(page.getByTestId('code-malloy-0')).toContainText('nullif(n_sent, 0)')
    await expect(page.getByTestId('code-metric-view-0')).toContainText('WITH METRICS LANGUAGE YAML')
    await expect(page.getByTestId('code-metric-view-1')).toContainText('MEASURE(delivery_rate)')
    await expect(page.getByTestId('approach-metric-view')).toContainText('2 statements')
    await expect(page.getByTestId('approach-metric-view')).toContainText('not connected here')
    await expect(page.getByTestId('approach-metric-view').getByRole('button', { name: 'Use' })).toBeDisabled()
    await shot(page, '21-backends')
  })

  test('verify compares each connected backend with the independent reference', async ({ page }) => {
    await page.goto('/#/backends')
    await page.getByTestId('verify').click()
    const result = page.getByTestId('verify-result')
    await expect(result).toContainText('DuckDB')
    await expect(result).toContainText('Malloy on DuckDB')
    await expect(result.locator('.banner.ok')).toHaveCount(2)
    await expect(result).toContainText('Skipped: needs a Databricks SQL warehouse')
    await expect(result).not.toContainText('differ')
    await shot(page, '22-backends-verified')
  })

  test('the recorded warehouse run is shown as recorded, not as live', async ({ page }) => {
    await page.goto('/#/backends')
    const card = page.getByTestId('evidence-card')
    await expect(card).toContainText('Not run live in this demo')
    await expect(card).toContainText('45 comparisons · 0 differences')
    await expect(card.locator('.evidence-grid .ok')).toHaveCount(45)
    await expect(card.locator('.evidence-grid .ok').first()).toHaveText('✓')
  })

  test('EC-D-23: with no recorded run the panel says so instead of showing an empty grid', async ({ page }) => {
    await page.route('**/api/evidence', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, available: false }) }))
    await page.goto('/#/backends')
    await expect(page.getByTestId('evidence-card')).toContainText('No recorded run')
    await expect(page.locator('.evidence-grid')).toHaveCount(0)
  })

  test('the report chosen on the Report screen is the one compiled here', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Remove Reach' }).click()
    await page.getByLabel('Add a KPI').selectOption('ctor')
    await page.getByRole('link', { name: 'Backends' }).click()
    await expect(page.getByTestId('code-sql-0')).toContainText('n_clicked * 1.0 / NULLIF(n_opened, 0) AS ctor')
    await expect(page.getByTestId('code-sql-0')).not.toContainText('n_reached')
  })
})

test.describe('Migration', () => {
  test('six templates accepted, two refused, every legacy value equal', async ({ page }) => {
    await page.goto('/#/migration')
    await expect(page.getByTestId('compared')).toHaveText('200')
    await expect(page.getByTestId('different')).toHaveText('0')
    await expect(page.locator('[data-testid="templates"] button')).toHaveCount(8)
    await expect(page.locator('[data-testid="templates"] .pill.green')).toHaveCount(6)
    await expect(page.locator('[data-testid="templates"] .pill.pink')).toHaveCount(2)
    await expect(page.getByTestId('template-detail')).toContainText('{{ group_by_list }}')
    await shot(page, '23-migration')
  })

  test('EC-D-24: with no templates configured the screen says so', async ({ page }) => {
    await page.route('**/api/inference', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, available: false }) }))
    await page.goto('/#/migration')
    await expect(page.getByText('No templates configured')).toBeVisible()
  })

  test('a refused template shows its reason, a joined one that multiplies rows', async ({ page }) => {
    await page.goto('/#/migration')
    await page.locator('[data-template="open-events"]').click()
    await expect(page.getByTestId('refusal')).toContainText('GRAIN_JOIN_FANOUT')
    await expect(page.getByTestId('refusal')).toContainText('13 messages become 20 rows')
    await shot(page, '24-migration-refused')
  })

  test('an accepted template shows its inferred measures and a draft status', async ({ page }) => {
    await page.goto('/#/migration')
    await page.locator('[data-template="click-to-open-rate"]').click()
    const detail = page.getByTestId('template-detail')
    await expect(detail).toContainText('ctor')
    await expect(detail).toContainText('draft')
    await expect(detail).toContainText('m5 / m4')
    await expect(detail).toContainText('COUNT(*) FILTER(WHERE is_clicked)')
    await page.getByRole('button', { name: 'Show YAML' }).click()
    await expect(page.getByTestId('yaml')).toContainText('name: registry')
    await shot(page, '25-migration-inferred')
  })
})

test.describe('Assistant', () => {
  test('a label and a typo are read and said so; the request is valid', async ({ page }) => {
    await page.goto('/#/assistant')
    await expect(page.getByTestId('notes')).toContainText("'Delivery Rate' read as 'delivery_rate'")
    await expect(page.getByTestId('notes')).toContainText("'markt' read as 'market'")
    await expect(page.getByTestId('resolved-request')).toContainText('"cols"')
    await shot(page, '26-assistant-resolved')
  })

  test('an ambiguous word becomes a question, never a guess', async ({ page }) => {
    await page.goto('/#/assistant')
    await page.locator('[data-example="ambiguous"]').click()
    await expect(page.getByTestId('questions')).toContainText("which KPI is 'rate'?")
    await expect(page.getByTestId('questions')).toContainText('click_rate')
    await expect(page.getByTestId('resolved-request')).toHaveCount(0)
    await shot(page, '27-assistant-question')
  })

  test('EC-D-17: hostile text is shown as text and does nothing', async ({ page }) => {
    let dialogs = 0
    page.on('dialog', (d) => { dialogs += 1; void d.dismiss() })
    await page.goto('/#/assistant')
    await page.locator('[data-example="hostile"]').click()
    await expect(page.getByTestId('questions')).toContainText('DROP TABLE message')
    await expect(page.getByTestId('questions')).toContainText('<img src=x onerror=alert(1)>')
    await expect(page.locator('img[src="x"]')).toHaveCount(0)
    expect(dialogs).toBe(0)
    await shot(page, '28-assistant-hostile')
  })

  test('a resolved proposal opens in the Report screen', async ({ page }) => {
    await page.goto('/#/assistant')
    await page.getByTestId('open-report').click()
    await expect(page.getByRole('heading', { name: 'Report' })).toBeVisible()
    const chips = page.locator('[data-testid="kpi-chips"] .chip')
    await expect(chips).toHaveText(['Delivery Rate✕', 'Message Sent✕'])
    await expect(page.getByTestId('axis-cols')).toContainText('Market')
  })
})

test.describe('Edge-case lab', () => {
  test('every case is answered as a correct service should', async ({ page }) => {
    await page.goto('/#/lab')
    await expect(page.locator('[data-testid^="scenario-"]')).toHaveCount(12)
    await page.getByTestId('run-all').click()
    await expect(page.locator('[data-outcome="pass"]')).toHaveCount(12, { timeout: 60_000 })
    await expect(page.locator('[data-outcome="fail"]')).toHaveCount(0)
    await expect(page.getByText('12/12 as expected')).toBeVisible()
    await shot(page, '29-lab-all-pass')
  })

  test('SQL typed into a filter value is data: no rows, no error, nothing dropped', async ({ page }) => {
    await page.goto('/#/lab')
    await page.getByTestId('scenario-injection-in-filter').getByRole('button', { name: 'Run' }).click()
    await expect(page.getByTestId('scenario-injection-in-filter')).toContainText('no node, no error, nothing dropped')
    await page.goto('/')
    await expect(page.getByTestId('result-card')).toBeVisible()
    await page.locator('[data-testid="result-body"][data-stale="false"]').waitFor()
    await expect(page.locator('table.pivot')).toContainText('13')
  })
})
