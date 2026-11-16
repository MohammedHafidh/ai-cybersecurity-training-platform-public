import type { paths } from './schema'

export type Health = paths['/health']['get']['responses'][200]['content']['application/json']

export function createApiClient(baseUrl: string, request: typeof fetch = fetch) {
  const url = new URL(baseUrl)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('Set VITE_API_BASE_URL to an HTTP or HTTPS API address.')
  }
  const base = url.toString().replace(/\/+$/, '')

  return {
    docsUrl: `${base}/docs`,
    async health(signal?: AbortSignal): Promise<Health> {
      const response = await request(`${base}/health`, {
        headers: { Accept: 'application/json' }, signal,
      })
      if (!response.ok) throw new Error(`Health check failed (HTTP ${response.status}).`)
      const body: unknown = await response.json()
      if (!body || typeof body !== 'object' || !('status' in body) || body.status !== 'ok') {
        throw new Error('The API returned an unexpected health response.')
      }
      return { status: body.status }
    },
  }
}
