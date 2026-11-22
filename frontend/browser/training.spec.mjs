import { expect, test } from '@playwright/test'

const live = process.env.CAPSTONE_LIVE_ACCEPTANCE === '1'
const sample = process.env.CAPSTONE_SAMPLE_ACCEPTANCE === '1'
const api = process.env.API_SMOKE_URL || process.env.CAPSTONE_PLATFORM_URL || 'http://127.0.0.1:8765'
const cases = [
  ['brute-force', 'Brute Force', [0, 2, 1, 3]],
  ['sql-injection', 'SQL Injection', [1, 3, 0, 2]],
  ['reconnaissance', 'Reconnaissance', [2, 0, 1, 3]],
]

test('learning home and three complete guides are usable without AI', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Learn cybersecurity/ })).toBeVisible()
  await expect(page.locator('.scenario-card')).toHaveCount(3)
  await page.getByRole('link', { name: 'Skip to content' }).focus()
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main')).toBeFocused()
  const firstGuide = page.locator('.scenario-card').first().getByRole('link')
  await firstGuide.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Brute Force', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'API connection', exact: true })).toHaveCount(0)
  await page.setViewportSize({ width: 375, height: 850 })
  for (const [id, title] of cases) {
    await page.goto('/#/scenarios/' + id)
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Learning objectives', exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Trusted references', exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375)
  }
})

// Serial because the product intentionally permits one lab exercise at a time.
test.describe('complete student journeys', () => {
  test.describe.configure({ mode: 'serial' })
  for (const [id, title, answers] of cases) test(`${title}: guide to evidence, AI, quiz and completion`, async ({ page, request }, testInfo) => {
    test.skip(!live && !sample, 'Dedicated acceptance step selects explicit live lab or sample mode')
    test.setTimeout(240_000)
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    await page.goto('/')
    await page.locator('.scenario-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) }).getByRole('link').click()
    await expect(page.getByRole('heading', { name: 'Learning objectives', exact: true })).toBeVisible()
    const start = page.getByRole('button', { name: live ? 'Start Controlled Exercise' : 'Sample / Demonstration Mode', exact: true })
    await expect(start).toBeEnabled({ timeout: 20_000 })
    const started = Date.now()
    await start.click()
    await page.waitForURL(/\/analysis$/, { timeout: 120_000 })
    await expect(page.getByText(live ? 'Live Controlled Exercise' : 'Sample / Demonstration Mode', { exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Read the evidence.', exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Normalized event', exact: true }).first()).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Understand the features.', exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Rule output', exact: true }).first()).toBeVisible()
    await expect(page.getByRole('heading', { name: 'ML output', exact: true }).first()).toBeVisible()
    const exercise = page.url().match(/exercises\/([a-f0-9]{32})/)[1]
    const before = await (await request.get(`${api}/training/exercises/${exercise}`)).json()
    expect(before.mode).toBe(live ? 'live' : 'sample')
    expect(before.result.records.length).toBeGreaterThan(0)
    if (live) {
      expect(new Date(before.history[0].at).getTime()).toBeGreaterThanOrEqual(started - 2000)
      expect(before.history.map(e => e.stage)).toEqual(['preparing', 'starting', 'activity', 'capturing', 'normalizing', 'rules', 'ml', 'saving', 'ready'])
    } else {
      await expect(page.getByText(/At least one detector differs from ground truth/).first()).toBeVisible()
    }
    const stored = await (await request.get(`${api}/detections`)).json()
    await page.getByLabel('Ask AI about this evidence…').fill('Why did the rule and ML model reach these results?')
    const response = page.waitForResponse(r => r.url().endsWith('/question') && r.request().method() === 'POST', { timeout: 70_000 })
    await page.getByRole('button', { name: 'Ask AI', exact: true }).click()
    const answer = await (await response).json()
    expect(['grounded', 'fallback']).toContain(answer.status)
    expect(answer.sources.length).toBeGreaterThan(0)
    await expect(page.getByRole('heading', { name: 'Trusted sources', exact: true })).toBeVisible()
    expect(await (await request.get(`${api}/detections`)).json()).toEqual(stored)
    await page.getByLabel('Ask AI about this evidence…').fill('What is the weather today?')
    await page.getByRole('button', { name: 'Ask AI', exact: true }).click()
    await expect(page.getByText('Outside this lesson', { exact: true })).toBeVisible()
    await page.getByRole('link', { name: 'Continue to knowledge check', exact: false }).click()
    for (let i = 0; i < 4; i++) await page.getByRole('radio').nth(i * 4 + answers[i]).check()
    await page.getByRole('button', { name: 'Submit knowledge check' }).click()
    await expect(page.getByRole('heading', { name: 'Your score: 4/4', exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Mark Scenario Complete' }).click()
    await expect(page.getByRole('heading', { name: 'Scenario Complete', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Review AI Explanation', exact: true })).toBeVisible()
    const end = await (await request.get(`${api}/training/exercises/${exercise}`)).json()
    expect(end.completed).toBe(true)
    expect(end.quiz_attempts.at(-1).answers).toEqual(answers)
    await page.screenshot({ path: testInfo.outputPath('completion.png'), fullPage: true })
    await testInfo.attach('safe-acceptance-record', { body: JSON.stringify({ scenario:id, mode:end.mode, exercise, run_id:end.result.run_id, hashes:end.result.hashes, event_count:end.result.total_records, stages:end.history, answer_mode:answer.mode, citations:answer.sources.map(s=>s.chunk_id), score:end.quiz_attempts.at(-1).score, completed:end.completed, seconds:(Date.now()-started)/1000 }), contentType:'application/json' })
    await page.getByRole('link', { name: 'Return Home', exact: true }).click()
    await expect(page.locator('.scenario-card').filter({ has: page.getByRole('heading', { name:title,exact:true }) }).getByText('Completed', { exact:true })).toBeVisible()
    expect(errors).toEqual([])
  })
})

