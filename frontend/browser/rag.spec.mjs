import { randomUUID } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'

const api = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
const endpoint = '**/rag-explanation?*'
const { chunks } = JSON.parse(await readFile(new URL('../../data/knowledge/day45/chunks.json', import.meta.url)))
const timestamp = '2026-01-01T12:00:00Z'
const scenarios = [
  ['auth', 'brute_force', 'ssh_password', Array.from({ length: 3 }, () => ({ username: 'fixture', outcome: 'failure' })), 3],
  ['web', 'sql_injection', 'http_request', [{ method: 'GET', status_code: 400, request_data: 'select a category' }], 1],
  ['network', 'reconnaissance', 'tcp_connection', [8080, 8081].map(destination_port => ({ destination_port, protocol: 'tcp' })), 2],
]

async function store(request, [source, scenario, event_type, attributes]) {
  const run_id = `day48-${randomUUID()}`
  const run = {
    run_id, scenario, expected_label: 'malicious', start_time: timestamp, end_time: timestamp,
    source: 'fixture-client', target: 'fixture-server', tool_or_method: 'synthetic training evidence',
    log_sources: ['fixture.log'],
  }
  const events = attributes.map((fields, index) => ({
    ...fields, event_id: `${run_id}-${index}`, run_id, timestamp, event_type, scenario, attack_label: 'malicious',
    raw_source_file: 'fixture.log', source_type: source, source_ip: '192.0.2.48',
  }))
  const ingest = await request.post(`${api}/ingestion/runs`, { data: { source_type: source, run, events } })
  expect(ingest.status()).toBe(201)
  const scored = await request.post(`${api}/runs/${run_id}/process`)
  await expect(scored).toBeOK()
  return (await scored.json()).detection_ids
}

async function select(page, id) {
  await page.getByLabel('Recent stored predictions').selectOption(id)
  const panel = page.getByRole('region', { name: 'Grounded explanation' })
  await expect(panel).toBeVisible()
  return panel
}

test('the learner sees a grounded answer and citations for each scenario', async ({ page, request }) => {
  test.setTimeout(120_000)
  const trials = []
  for (const fixture of scenarios) {
    const [rule] = await store(request, fixture)
    trials.push({ rule, scenario: fixture[1], threshold: fixture[4] })
  }
  if (process.env.CAPSTONE_TEST_LIVE_RAG !== '1') {
    await page.route(endpoint, route => {
      const url = new URL(route.request().url())
      const trial = trials.find(({ rule }) => url.pathname.endsWith(`/${rule}/rag-explanation`))
      expect(url.searchParams.get('question')).toBe('why_suspicious')
      const source = chunks.find(chunk => chunk.scenario === trial.scenario)
      return route.fulfill({ json: {
        detection_id: trial.rule, status: 'grounded', question: 'why_suspicious', model: 'gemma3:1b',
        text: `The count met its threshold of ${trial.threshold}.`, evidence_ids: ['threshold'], sources: [source],
      } })
    })
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  for (const { rule, scenario, threshold } of trials) {
    const panel = await select(page, rule)
    await expect(panel.getByText('Trusted sources')).toHaveCount(0)
    await panel.getByLabel('Training question').selectOption('why_suspicious')
    await panel.getByRole('button', { name: 'Get explanation' }).click()
    await expect(panel.getByRole('status')).toContainText(`met its threshold of ${threshold}`, { timeout: 55_000 })
    const source = chunks.find(chunk => chunk.scenario === scenario)
    for (const reference of source.references) {
      const href = reference.location.startsWith('https://') ? reference.location : new URL(reference.location,
        'https://github.com/MohammedHafidh/ai-cybersecurity-training-platform-public/blob/main/').href
      await expect(panel.getByRole('link', { name: reference.title }).first()).toHaveAttribute('href', href)
    }
    await expect(page.getByRole('heading', { name: 'Rule output' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'ML output' })).toBeVisible()
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
})

test('loading, retry, empty results, and unsupported questions keep the stored evidence visible', async ({ page, request }) => {
  const [, ml] = await store(request, scenarios[0])
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route(endpoint, async route => {
    await pending
    await route.fulfill({ status: 503, body: '{}' })
  })
  await page.goto('/')
  const panel = await select(page, ml)
  await panel.getByRole('button', { name: 'Get explanation' }).click()
  await expect(panel.getByRole('status')).toHaveText('Preparing the local explanation…')
  await expect(panel.getByRole('button', { name: 'Get explanation' })).toBeDisabled()
  release()
  await expect(panel.getByRole('alert')).toContainText('The local explanation is unavailable')

  await page.unroute(endpoint)
  await page.route(endpoint, route => route.fulfill({ json: {
    detection_id: ml, status: 'grounded', text: '', sources: [],
  } }))
  await panel.getByRole('button', { name: 'Retry explanation' }).click()
  await expect(panel.getByText('No explanation text was returned.')).toBeVisible()
  await expect(panel.getByText('No source references were returned.')).toBeVisible()

  await page.unroute(endpoint)
  await panel.getByLabel('Training question').selectOption('why_suspicious')
  await panel.getByRole('button', { name: 'Get explanation' }).click()
  await expect(panel.getByRole('status')).toContainText('do not support that question')
  await expect(panel.getByText('Trusted sources')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'ML output' })).toBeVisible()
})
