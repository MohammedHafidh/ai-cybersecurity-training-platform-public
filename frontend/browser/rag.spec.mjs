import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { readFile, writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'

const api = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
const endpoint = '**/rag-explanation?*'
const { chunks } = JSON.parse(await readFile(new URL('../../data/knowledge/day45/chunks.json', import.meta.url)))
const timestamp = '2026-01-01T12:00:00Z'
const scenarios = [
  ['auth', 'brute_force', 'ssh_password', Array.from({ length: 3 }, () => ({ username: 'fixture', outcome: 'failure' })), 3],
]

async function store(request, [source, scenario, event_type, attributes], expectedLabel = 'malicious') {
  const run_id = `day48-${randomUUID()}`
  const run = {
    run_id, scenario, expected_label: expectedLabel, start_time: timestamp, end_time: timestamp,
    source: 'fixture-client', target: 'fixture-server', tool_or_method: 'synthetic training evidence',
    log_sources: ['fixture.log'],
  }
  const events = attributes.map((fields, index) => ({
    ...fields, event_id: `${run_id}-${index}`, run_id, timestamp, event_type, scenario, attack_label: expectedLabel,
    raw_source_file: 'fixture.log', source_type: source, source_ip: '192.0.2.48',
  }))
  return processCapture(request, { source_type: source, run, events }).then(result => result.detection_ids)
}

async function processCapture(request, capture) {
  const ingest = await request.post(`${api}/ingestion/runs`, { data: capture })
  expect(ingest.status()).toBe(201)
  expect(await ingest.json()).toEqual({ run_id: capture.run.run_id, event_count: capture.events.length })
  const scored = await request.post(`${api}/runs/${encodeURIComponent(capture.run.run_id)}/process`)
  await expect(scored).toBeOK()
  return scored.json()
}

async function select(page, id) {
  await page.getByLabel('Recent stored predictions').selectOption(id)
  const panel = page.getByRole('region', { name: 'Grounded explanation' })
  await expect(panel).toBeVisible()
  return panel
}

function timestampMicros(timestamp) {
  // Date.parse retains only milliseconds. The raw log can carry six fractional digits.
  const fraction = timestamp.match(/\.(\d+)(?:Z|[+-]\d\d:\d\d)$/)?.[1] ?? ''
  return Date.parse(timestamp) * 1000 + Number(fraction.padEnd(6, '0').slice(3, 6))
}

async function traceCapture(request, script, countFeature, eventLabel) {
  const capture = JSON.parse(execFileSync('python', [`../backend/tests/${script}`], {
    encoding: 'utf8', env: { ...process.env, PYTHONPATH: '../backend' },
  }))
  const processed = await processCapture(request, capture)
  const [rule, ml] = processed.detection_ids
  const [observation] = processed.result.observations
  const eventIds = capture.events.map(event => event.event_id).sort()
  expect(processed.result.run_id).toBe(capture.run.run_id)
  expect(processed.result.observations).toHaveLength(1)
  expect([...observation.event_ids].sort()).toEqual(eventIds)
  expect(observation.observed_features[countFeature]).toBe(eventIds.length)
  expect(observation.rule.predicted_label).toBe('malicious')
  let visibleFeatures = []
  if (capture.source_type === 'network') {
    const times = capture.events.map(event => timestampMicros(event.timestamp))
    const ports = new Set(capture.events.map(event => event.destination_port)).size
    const span = (Math.max(...times) - Math.min(...times)) / 1_000_000
    const rate = eventIds.length / 60
    expect(observation.rule.evidence.observed).toBe(ports)
    expect(observation.observed_features.unique_destination_port_count).toBe(ports)
    expect(observation.observed_features.connections_per_second).toBeCloseTo(rate)
    expect(observation.observed_features.observed_span_seconds).toBe(span)
    visibleFeatures = [
      ['Distinct observed destination ports', ports],
      ['connection count', eventIds.length],
      ['connections per second', rate],
      ['observed span seconds', span],
    ]
  }
  const details = async () => Promise.all([rule, ml].map(async id => {
    const response = await request.get(`${api}/detections/${id}`)
    await expect(response).toBeOK()
    return response.json()
  }))
  const before = await details()
  for (const row of before) {
    expect(row.run_id).toBe(capture.run.run_id)
    expect([...row.evidence.event_ids].sort()).toEqual(eventIds)
    expect(row.predicted_label).toBe(observation[row.detector].predicted_label)
    expect(row.evidence.observed_features).toEqual(observation.observed_features)
  }
  expect(before[1].evidence.malicious_probability).toBe(observation.ml.malicious_probability)
  const { observed, threshold } = observation.rule.evidence
  return { rule, scenario: capture.run.scenario, threshold, observed, capture, eventIds, eventLabel, before, details, visibleFeatures }
}

test('the learner sees a grounded answer and citations for each scenario', async ({ page, request }, testInfo) => {
  test.setTimeout(120_000)
  const auth = await traceCapture(request, 'auth_browser_capture.py', 'failed_login_count', 'SSH password event')
  const web = await traceCapture(request, 'web_browser_capture.py', 'request_count', 'HTTP request')
  const network = await traceCapture(request, 'network_browser_capture.py', 'connection_count', 'TCP connection')
  const trials = [auth, web, network]
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
  await page.goto('/#/evidence')
  for (const { rule, scenario, threshold, observed, capture, eventIds, eventLabel, before, details, visibleFeatures } of trials) {
    if (capture) {
      const rows = page.getByRole('row').filter({ hasText: capture.run.run_id })
      await expect(rows).toHaveCount(eventIds.length)
      for (const row of await rows.all()) await expect(row).toContainText(eventLabel)
    }
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
    if (capture) {
      await expect(page.getByText(`Run ${capture.run.run_id} · Expected label malicious`)).toBeVisible()
      await expect(page.locator('#detection-evidence')).toContainText(`observed ${observed} · trigger threshold ≥ ${threshold}`)
      for (const id of eventIds) await expect(page.locator('#detection-evidence')).toContainText(id)
      await expect(page.locator('#detection-evidence')).toContainText(capture.events[0].raw_source_file)
      for (const [label, value] of visibleFeatures) {
        const displayed = page.locator('dt').filter({ hasText: new RegExp(`^${label}$`) }).locator('..').locator('dd')
        await expect(displayed).toHaveText(String(value))
      }
      expect(await details()).toEqual(before)
    }
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  if (process.env.CAPSTONE_DEMO_BACKUP === '1') {
    for (const source of ['AUTH', 'WEB', 'NETWORK']) {
      expect(process.env[`CAPSTONE_${source}_LOG`], 'backup requires public fixtures').toBeUndefined()
    }
    expect(auth.capture.run.run_id).toMatch(/^day49-auth-/)
    await page.unroute(endpoint)
    const panel = await select(page, auth.rule)
    const unavailable = page.waitForResponse(response => response.url().includes('/rag-explanation?'))
    await panel.getByRole('button', { name: 'Get explanation' }).click()
    expect((await unavailable).status()).toBe(503)
    await expect(panel.getByRole('alert')).toContainText('The local explanation is unavailable')
    await expect(page.getByRole('complementary', { name: 'Explanation preview' })).toContainText('3 met the rule threshold of 3')
    expect(await auth.details()).toEqual(auth.before)

    const screenshot = 'demo-evidence.png'
    await page.locator('#detection-evidence').screenshot({ path: testInfo.outputPath(screenshot) })
    await writeFile(testInfo.outputPath('demo-evidence.json'), JSON.stringify({
      evidence_kind: 'synthetic raw authentication fixture',
      screenshot,
      run_id: auth.capture.run.run_id,
      expected_label: auth.capture.run.expected_label,
      event_ids: auth.eventIds,
      threshold: auth.threshold,
      observed: auth.observed,
      predictions: auth.before.map(({ detector, detection_id, predicted_label }) => ({
        detector, detection_id, predicted_label,
      })),
      rag_http_status: 503,
    }, null, 2) + '\n')
  }
})

test('the dashboard keeps a benign expected label visible when both detectors flag the request', async ({ page, request }) => {
  const [rule, ml] = await store(request, [
    'web', 'benign', 'http_request',
    [{ method: 'GET', status_code: 200, request_data: 'select a category' }],
  ], 'benign')
  await page.goto('/#/evidence')
  for (const id of [rule, ml]) {
    await select(page, id)
    const detail = page.locator('#detection-evidence')
    await expect(detail.getByText('Expected label benign', { exact: false })).toBeVisible()
    await expect(detail.getByText('fixture-client → fixture-server')).toBeVisible()
    await expect(detail.getByText(/Prediction malicious/)).toHaveCount(2)
  }
})

test('loading, retry, empty results, and unsupported questions keep the stored evidence visible', async ({ page, request }) => {
  const [, ml] = await store(request, scenarios[0])
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route(endpoint, async route => {
    await pending
    await route.fulfill({ status: 503, body: '{}' })
  })
  await page.goto('/#/evidence')
  const panel = await select(page, ml)
  await panel.getByRole('button', { name: 'Get explanation' }).click()
  await expect(panel.getByRole('status')).toHaveText('Preparing the local explanation…')
  await expect(panel.getByRole('button', { name: 'Get explanation' })).toBeDisabled()
  release()
  await expect(panel.getByRole('alert')).toContainText('The local explanation is unavailable')

  await page.unroute(endpoint)
  await page.route(endpoint, route => route.fulfill({ json: {
    detection_id: ml, status: 'grounded', text: '', sources: [], evidence_ids: [],
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

test('slow inference times out with retry while the saved prediction stays visible', async ({ page, request }) => {
  test.setTimeout(70_000)
  const [rule] = await store(request, scenarios[0])
  let started
  let release
  const intercepted = new Promise(resolve => { started = resolve })
  const pending = new Promise(resolve => { release = resolve })
  await page.route(endpoint, async route => {
    started()
    await pending
    await route.abort().catch(() => {})
  })
  await page.goto('/#/evidence')
  const panel = await select(page, rule)
  await panel.getByRole('button', { name: 'Get explanation' }).click()
  await intercepted
  await expect(panel.getByRole('status')).toHaveText('Preparing the local explanation…')
  await expect(panel.getByRole('alert')).toContainText('The local explanation is unavailable', { timeout: 55_000 })
  await expect(panel.getByRole('button', { name: 'Retry explanation' })).toBeEnabled()
  await expect(page.getByRole('complementary', { name: 'Explanation preview' })).toContainText('3 met the rule threshold of 3')
  release()
})

test('database read errors leave evaluation available and explain the missing evidence', async ({ page }) => {
  for (const path of ['events', 'detections']) {
    await page.route(`**/${path}?limit=20`, route => route.fulfill({ status: 503, body: '{}' }))
  }
  await page.goto('/#/evidence')
  await expect(page.locator('#recent-events').getByRole('alert')).toContainText('Could not load recent events')
  await expect(page.locator('#detection-evidence').getByRole('alert')).toContainText('Could not load detections')
  await expect(page.getByText('Confusion matrix · 12 runs')).toHaveCount(2)
  await expect(page.getByRole('button', { name: 'Refresh detections' })).toBeEnabled()
})

test('malformed citation data produces retry instead of breaking the evidence view', async ({ page, request }) => {
  const [rule] = await store(request, scenarios[0])
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route(endpoint, route => route.fulfill({ json: {
    detection_id: rule, status: 'grounded', text: 'Invalid citation response',
    evidence_ids: ['prediction'], sources: [null],
  } }))
  await page.goto('/#/evidence')
  const panel = await select(page, rule)
  await panel.getByRole('button', { name: 'Get explanation' }).click()
  await expect(panel.getByRole('alert')).toContainText('The local explanation is unavailable')
  await expect(panel.getByRole('button', { name: 'Retry explanation' })).toBeEnabled()
  await expect(page.getByRole('heading', { name: 'Rule output' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'ML output' })).toBeVisible()
  expect(errors).toEqual([])
})
