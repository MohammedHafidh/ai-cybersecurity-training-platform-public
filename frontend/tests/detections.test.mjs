import assert from 'node:assert/strict'
import test from 'node:test'
import { createApiClient } from '../src/api/client.ts'
import { featureName, maliciousProbability, scenarioNames } from '../src/api/evidence.ts'

test('evidence labels describe measured features and only show valid ML probabilities', () => {
  assert.equal(featureName('suspicious_token_count'), 'SQL-like token matches')
  assert.equal(featureName('unique_destination_port_count'), 'Distinct observed destination ports')
  assert.equal(featureName('failed_login_count'), 'Failed SSH password events')
  assert.equal(maliciousProbability(0), '0%')
  assert.equal(maliciousProbability(0.625), '62.5%')
  assert.equal(maliciousProbability(1), '100%')
  for (const invalid of [undefined, null, '0.6', NaN, Infinity, -0.1, 1.01]) {
    assert.equal(maliciousProbability(invalid), undefined)
  }
})

test('real API pairs stored rule and ML evidence for each scenario', async () => {
  const base = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
  const api = createApiClient(base)
  const signal = AbortSignal.timeout(30000)
  const timestamp = '2026-01-01T12:00:00Z'
  const fixtures = [
    ['auth', 'brute_force', 'Brute force', 'ssh_password', 'failed_login_count',
      Array.from({ length: 3 }, () => ({ outcome: 'failure', username: 'fixture' })), 3, 3],
    ['web', 'sql_injection', 'SQL injection', 'http_request', 'suspicious_token_count',
      [{ method: 'GET', status_code: 400, request_data: 'select a category' }], 1, 1],
    ['network', 'reconnaissance', 'Network reconnaissance', 'tcp_connection', 'unique_destination_port_count',
      [8080, 8081].map(destination_port => ({ destination_port, protocol: 'tcp' })), 2, 2],
  ]
  assert.deepEqual(await api.recentDetections(signal), [])
  for (const [source, scenario, title, event_type, feature, fields, observed, threshold] of fixtures) {
    const run_id = `day41-${source}`
    const events = fields.map((attributes, index) => ({
      ...attributes, run_id, event_id: `${run_id}-${index}`, timestamp, event_type, scenario,
      raw_source_file: 'fixture.log', attack_label: 'malicious', source_type: source, source_ip: '192.0.2.5',
    }))
    const run = {
      run_id, scenario, expected_label: 'malicious', start_time: timestamp, end_time: timestamp,
      source: 'fixture-client', target: 'fixture-server', tool_or_method: 'synthetic evidence test',
      log_sources: ['fixture.log'],
    }
    const ingestion = await fetch(`${base}/ingestion/runs`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: source, run, events }), signal,
    })
    assert.equal(ingestion.status, 201, await ingestion.text())
    const processed = await fetch(`${base}/runs/${run_id}/process`, { method: 'POST', signal })
    assert.equal(processed.status, 200, processed.status === 200 ? undefined : await processed.text())
    const { detection_ids } = await processed.json()
    const listed = (await api.recentDetections(signal)).filter(row => row.run_id === run_id)
    assert.deepEqual(new Set(listed.map(row => row.detection_id)), new Set(detection_ids))
    const [rule, ml] = await Promise.all(['rule', 'ml'].map(detector =>
      api.detectionDetail(listed.find(row => row.detector === detector).detection_id, signal)))
    assert.equal(scenarioNames[rule.run.scenario], title)
    assert.equal(rule.run.expected_label, 'malicious')
    assert.equal(rule.run.start_time, timestamp)
    assert.equal(rule.run.source_type, source)
    assert.equal(rule.predicted_label, observed >= threshold ? 'malicious' : 'benign')
    assert.equal(rule.evidence.rule.feature, feature)
    assert.equal(rule.evidence.rule.observed, observed)
    assert.equal(rule.evidence.rule.threshold, threshold)
    assert.equal(rule.evidence.observed_features[feature], observed)
    assert.deepEqual(new Set(rule.evidence.event_ids), new Set(events.map(event => event.event_id)))
    assert.deepEqual(rule.evidence.raw_source_files, ['fixture.log'])
    assert.equal(rule.evidence.row_id, ml.evidence.row_id)
    assert.equal(rule.counterparts.length, 1)
    assert.equal(rule.counterparts[0].detection_id, ml.detection_id)
    assert.equal(ml.counterparts.length, 1)
    assert.equal(ml.counterparts[0].detection_id, rule.detection_id)
    assert.equal(rule.evidence.malicious_probability, undefined)
    assert.ok(maliciousProbability(ml.evidence.malicious_probability))
  }
  await assert.rejects(api.detectionDetail('missing', signal), /HTTP 404/)
})
