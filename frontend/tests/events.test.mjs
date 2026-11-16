import assert from 'node:assert/strict'
import test from 'node:test'
import { createApiClient } from '../src/api/client.ts'

test('recent events distinguishes an empty result from an unavailable or invalid response', async () => {
  const client = response => createApiClient('http://localhost:8000', async () => response)
  assert.deepEqual(await client(Response.json([])).recentEvents(20), [])
  await assert.rejects(client(Response.json({}, { status: 503 })).recentEvents(20), /HTTP 503/)
  await assert.rejects(client(Response.json([{ event_id: 'incomplete' }])).recentEvents(20), /unexpected event list/)
})

test('recent events agrees with stored observations on a fresh FastAPI database', async () => {
  const base = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
  const api = createApiClient(base)
  const runId = 'dashboard-fixture'
  const older = '2026-01-01T12:00:00Z'
  const newer = '2026-01-01T12:00:10Z'
  const rawSource = 'fixture.log'
  const run = {
    run_id: runId, scenario: 'benign', expected_label: 'benign',
    start_time: older, end_time: newer, source: 'fixture-client',
    target: 'fixture-server', tool_or_method: 'synthetic dashboard test', log_sources: [rawSource],
  }
  const event = (id, timestamp) => ({
    event_id: id, run_id: runId, timestamp, source_type: 'auth', event_type: 'ssh_password',
    raw_source_file: rawSource, attack_label: 'benign', scenario: 'benign', source_ip: '192.0.2.1',
    username: 'fixture', outcome: 'success',
  })
  const ingested = await fetch(`${base}/ingestion/runs`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_type: 'auth', run, events: [event('older', older), event('newer', newer)] }),
  })
  assert.equal(ingested.status, 201, await ingested.text())
  const rows = (await api.recentEvents(20)).filter(row => row.run_id === runId)
  assert.deepEqual(rows.map(row => row.event_id), ['newer', 'older'])
  const [latest] = rows
  assert.equal((await api.recentEvents(1)).length, 1)
  assert.deepEqual(latest, {
    event_id: 'newer', run_id: runId, source_type: 'auth', timestamp: newer,
    event_type: 'ssh_password', raw_source_file: rawSource,
  })
})
