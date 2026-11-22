import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'

const api = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'

test('a real loopback capture is traceable through the non-LLM dashboard', async ({ page, request }) => {
  const capture = JSON.parse(execFileSync('python', ['../backend/tests/browser_capture.py'], {
    encoding: 'utf8', env: { ...process.env, PYTHONPATH: '../backend' },
  }))
  const { run, events: [event] } = capture
  const ingestion = await request.post(`${api}/ingestion/runs`, { data: capture })
  expect(ingestion.status()).toBe(201)
  const processed = await request.post(`${api}/runs/${run.run_id}/process`)
  await expect(processed).toBeOK()
  const { detection_ids: [ruleId], result: { observations: [observation] } } = await processed.json()

  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/#/evidence')
  await expect(page.getByText('API is reachable')).toBeVisible()
  const nav = page.getByRole('navigation', { name: 'Main navigation' })
  await nav.getByRole('link', { name: 'Recent events' }).click()
  await expect(page).toHaveURL(/#recent-events$/)
  const observed = page.getByRole('row').filter({ hasText: run.run_id })
  await expect(observed).toContainText('TCP connection')
  await expect(observed).toContainText(event.raw_source_file)

  await nav.getByRole('link', { name: 'Detection evidence' }).click()
  await page.getByLabel('Recent stored predictions').selectOption(ruleId)
  await expect(page.getByText(`Run ${run.run_id} · Expected label benign`)).toBeVisible()
  const evidence = page.locator('#detection-evidence')
  await expect(evidence.getByText('Prediction benign', { exact: false }).first()).toBeVisible()
  await expect(evidence.getByText(/observed 1 · trigger threshold ≥ 2/)).toBeVisible()
  await expect(evidence.getByText(new RegExp(`Prediction ${observation.ml.predicted_label} · ${observation.ml.model_version}`))).toBeVisible()
  await expect(evidence.getByText(event.event_id, { exact: true })).toBeVisible()
  await expect(evidence.getByText(event.raw_source_file, { exact: true })).toBeVisible()
  await expect(page.getByRole('complementary', { name: 'Explanation preview' }))
    .toContainText('1 fell below the rule threshold of 2')

  await nav.getByRole('link', { name: 'Evaluation' }).click()
  await expect(page).toHaveURL(/#evaluation$/)
  const matrices = page.getByRole('table').filter({ has: page.getByText('Confusion matrix · 12 runs') })
  await expect(matrices).toHaveCount(2)
  await page.getByLabel('Lab scenario').selectOption('network')
  await expect(page.getByText('Confusion matrix · 4 runs')).toHaveCount(2)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  expect(errors).toEqual([])
})

test('evaluation recovers from an unavailable API response', async ({ page }) => {
  const endpoint = '**/evaluation/summary'
  await page.route(endpoint, route => route.fulfill({
    status: 503, headers: { 'access-control-allow-origin': 'http://localhost:5173' }, body: '{}',
  }))
  await page.goto('/#evaluation')
  await expect(page.getByRole('alert')).toHaveText('Could not load the frozen evaluation.')
  await page.unroute(endpoint)
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(page.getByText('Confusion matrix · 12 runs')).toHaveCount(2)
})
