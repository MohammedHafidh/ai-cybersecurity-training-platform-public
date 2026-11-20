import assert from 'node:assert/strict'
import test from 'node:test'
import { createApiClient } from '../src/api/client.ts'

test('the explanation client rejects malformed passages and references', async () => {
  const source = {
    chunk_id: 'v1:auth:01', source_title: 'Authentication', source_path: 'source.md',
    source_sha256: 'fixture', section: 'Concept', text: 'Trusted background',
    references: [{ title: 'Project reference', location: 'docs/day44-local-explanations.md' }],
  }
  const body = { detection_id: 'test', status: 'grounded', text: 'Stored prediction',
    evidence_ids: ['prediction'], sources: [source] }
  const request = value => createApiClient('http://localhost:8000', async () => Response.json(value))
    .ragExplanation('test', 'what_happened', AbortSignal.timeout(5000))
  assert.deepEqual(await request(body), body)
  for (const sources of [[null], [{ ...source, references: null }],
    [{ ...source, text: 123 }], [{ ...source, references: [{ title: 'missing location' }] }]]) {
    await assert.rejects(request({ ...body, sources }), /unexpected explanation/)
  }
})
