import type { components, paths } from './schema'

export type Health = paths['/health']['get']['responses'][200]['content']['application/json']
export type RecentEvent = components['schemas']['EventSummary']
export type DetectionSummary = components['schemas']['DetectionSummary']
export type DetectionDetail = components['schemas']['DetectionDetail']
export type EvaluationSummary = components['schemas']['EvaluationSummary']
export type RagExplanation = components['schemas']['RagExplanation']
export type ExplanationQuestion = components['schemas']['Question']

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function hasStrings(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every(field => typeof value[field] === 'string')
}

function isRagExplanation(value: unknown): value is RagExplanation {
  if (!isRecord(value) || !hasStrings(value, ['detection_id', 'text'])
    || !['grounded', 'unsupported'].includes(String(value.status))
    || !Array.isArray(value.evidence_ids) || !value.evidence_ids.every(id => typeof id === 'string')
    || !Array.isArray(value.sources)) return false
  return value.sources.every(source => isRecord(source)
    && hasStrings(source, ['chunk_id', 'source_title', 'source_path', 'source_sha256', 'section', 'text'])
    && Array.isArray(source.references) && source.references.every(reference =>
      isRecord(reference) && hasStrings(reference, ['title', 'location'])))
}

function isRecentEvent(value: unknown): value is RecentEvent {
  if (!value || typeof value !== 'object') return false
  const row = value as Record<string, unknown>
  return ['event_id', 'run_id', 'event_type', 'raw_source_file'].every(key => typeof row[key] === 'string')
    && (row.source_type === 'auth' || row.source_type === 'web' || row.source_type === 'network')
    && typeof row.timestamp === 'string' && Number.isFinite(Date.parse(row.timestamp))
}

export function createApiClient(baseUrl: string, request: typeof fetch = fetch) {
  const url = new URL(baseUrl)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('Set VITE_API_BASE_URL to an HTTP or HTTPS API address.')
  }
  const base = url.toString().replace(/\/+$/, '')

  return {
    docsUrl: `${base}/docs`,
    async ragExplanation(id: string, question: ExplanationQuestion, signal: AbortSignal): Promise<RagExplanation> {
      const query = new URLSearchParams({ question })
      const response = await request(`${base}/detections/${encodeURIComponent(id)}/rag-explanation?${query}`, {
        headers: { Accept: 'application/json' }, signal,
      })
      if (!response.ok) throw new Error(`Explanation request failed (HTTP ${response.status}).`)
      const body: unknown = await response.json()
      if (!isRagExplanation(body)) throw new Error('The API returned an unexpected explanation.')
      return body
    },
    async evaluation(signal: AbortSignal): Promise<EvaluationSummary> {
      const response = await request(`${base}/evaluation/summary`, {
        headers: { Accept: 'application/json' }, signal,
      })
      if (!response.ok) throw new Error(`Evaluation request failed (HTTP ${response.status}).`)
      return response.json()
    },
    async recentDetections(signal: AbortSignal): Promise<DetectionSummary[]> {
      const response = await request(`${base}/detections?limit=20`, { signal })
      if (!response.ok) throw new Error(`Detection list failed (HTTP ${response.status}).`)
      return response.json()
    },
    async detectionDetail(id: string, signal: AbortSignal): Promise<DetectionDetail> {
      const response = await request(`${base}/detections/${encodeURIComponent(id)}`, { signal })
      if (!response.ok) throw new Error(`Detection detail failed (HTTP ${response.status}).`)
      return response.json()
    },
    async recentEvents(limit: number, signal?: AbortSignal): Promise<RecentEvent[]> {
      const response = await request(`${base}/events?limit=${limit}`, {
        headers: { Accept: 'application/json' }, signal,
      })
      if (!response.ok) throw new Error(`Recent events request failed (HTTP ${response.status}).`)
      const body: unknown = await response.json()
      if (!Array.isArray(body) || !body.every(isRecentEvent)) {
        throw new Error('The API returned an unexpected event list.')
      }
      return body
    },
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
