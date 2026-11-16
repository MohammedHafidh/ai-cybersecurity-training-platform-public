import assert from 'node:assert/strict'
import test from 'node:test'
import { createApiClient } from '../src/api/client.ts'

test('the health client handles HTTP errors and invalid responses', async () => {
  assert.throws(() => createApiClient('file:///tmp/api'))
  const bad = createApiClient('http://localhost:8000', async () => new Response('', { status: 503 }))
  await assert.rejects(bad.health(), /HTTP 503/)
  const unexpected = createApiClient('http://localhost:8000', async () => Response.json({ status: 'wrong' }))
  await assert.rejects(unexpected.health(), /unexpected health response/)
})

test('the frontend health client reaches FastAPI with the configured browser origin', async () => {
  const base = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
  const origin = 'http://localhost:5173'
  const api = createApiClient(base + '/', async (url, init) => {
    const headers = new Headers(init?.headers)
    headers.set('Origin', origin)
    const response = await fetch(url, { ...init, headers })
    assert.equal(response.headers.get('access-control-allow-origin'), origin)
    return response
  })
  assert.deepEqual(await api.health(AbortSignal.timeout(5_000)), { status: 'ok' })
})
