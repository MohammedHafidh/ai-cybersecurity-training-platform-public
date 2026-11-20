import { readFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'

test('every displayed evaluation metric matches the frozen report', async ({ page, request }) => {
  const report = JSON.parse(await readFile(new URL('../../data/processed/day32/evaluation.json', import.meta.url)))
  const api = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
  const response = await request.get(`${api}/evaluation/summary`)
  await expect(response).toBeOK()
  expect(await response.json()).toEqual(report)
  await page.goto('/#evaluation')
  const view = page.locator('#evaluation')
  const percent = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 })
  for (const scope of ['overall', 'auth', 'web', 'network']) {
    await view.getByLabel('Lab scenario').selectOption(scope)
    for (const [index, detector] of ['rule', 'ml'].entries()) {
      const row = report.metrics[detector][scope]
      const card = view.locator('article').nth(index)
      const values = card.locator('dl > div > dd:first-of-type')
      await expect(values).toHaveText(['accuracy', 'precision', 'recall', 'f1', 'false_positive_rate']
        .map(key => percent.format(row[key])))
      await expect(card.locator('tbody td')).toHaveText(row.confusion_matrix.flat().map(String))
      await expect(card.locator('caption')).toContainText(`${row.sample_count} runs`)
    }
  }
})
