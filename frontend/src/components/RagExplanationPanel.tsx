import { useEffect, useRef, useState } from 'react'
import { createApiClient, type ExplanationQuestion, type RagExplanation } from '../api/client'

const questions: Record<ExplanationQuestion, string> = {
  what_happened: 'What happened?',
  why_suspicious: 'Why was this suspicious?',
  what_evidence: 'What evidence is available?',
}
type State = { status: 'idle' | 'loading' | 'error' } | { status: 'ready'; result: RagExplanation }
const repository = 'https://github.com/MohammedHafidh/ai-cybersecurity-training-platform-public/blob/main/'

function referenceLink(location: string): string | undefined {
  if (/^docs\/[a-z0-9-]+\.md$/.test(location)) return repository + location
  try {
    const url = new URL(location)
    if (url.protocol === 'https:' && !url.username && !url.password) return url.href
  } catch {
    return
  }
}

export function RagExplanationPanel({ baseUrl, detectionId }: { baseUrl: string; detectionId: string }) {
  const [question, setQuestion] = useState<ExplanationQuestion>('what_happened')
  const [state, setState] = useState<State>({ status: 'idle' })
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])

  async function requestExplanation() {
    const controller = new AbortController()
    active.current?.abort()
    active.current = controller
    setState({ status: 'loading' })
    try {
      const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(50_000)])
      const result = await createApiClient(baseUrl).ragExplanation(detectionId, question, signal)
      if (result.detection_id !== detectionId || !['grounded', 'unsupported'].includes(result.status)
        || typeof result.text !== 'string' || !Array.isArray(result.sources)) {
        throw new Error('Unexpected explanation response')
      }
      if (!controller.signal.aborted) setState({ status: 'ready', result })
    } catch {
      if (!controller.signal.aborted) setState({ status: 'error' })
    }
  }

  const result = state.status === 'ready' ? state.result : null
  return <section aria-labelledby="rag-title" className="border-t border-white/10 pt-5">
    <h3 id="rag-title" className="font-semibold">Grounded explanation</h3>
    <form className="mt-3 flex flex-wrap items-end gap-3" onSubmit={event => {
      event.preventDefault()
      void requestExplanation()
    }}>
      <label className="min-w-0 max-w-full text-sm">
        <span className="block text-slate-300">Training question</span>
        <select value={question} disabled={state.status === 'loading'} onChange={event => {
          setQuestion(event.target.value as ExplanationQuestion)
          setState({ status: 'idle' })
        }} className="mt-1 max-w-full rounded-lg border border-white/15 bg-slate-950 p-2">
          {Object.entries(questions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <button type="submit" disabled={state.status === 'loading'}
        className="rounded-lg border border-teal-300/40 px-4 py-2 text-sm text-teal-200 hover:bg-teal-300/10 disabled:opacity-50">
        {state.status === 'error' ? 'Retry explanation' : 'Get explanation'}
      </button>
    </form>
    {state.status === 'loading' && <p role="status" className="mt-3 text-sm">Preparing the local explanation…</p>}
    {state.status === 'error' && <p role="alert" className="mt-3 text-sm text-amber-200">The local explanation is unavailable. Check that Ollama and retrieval are ready, then try again.</p>}
    {result && <div className="mt-4 space-y-3 text-sm">
      <p role="status" className={result.status === 'unsupported' ? 'text-amber-200' : 'text-slate-200'}>
        {result.text.trim() || (result.status === 'unsupported' ? 'This question is unsupported.' : 'No explanation text was returned.')}
      </p>
      {result.status === 'grounded' && <div className="rounded-xl border border-white/10 p-4">
        <h4 className="font-medium">Trusted sources</h4>
        {result.sources.length ? <ul className="mt-3 space-y-4">
          {result.sources.map(source => <li key={source.chunk_id} className="break-words">
            <p className="font-medium text-teal-200">{source.source_title} · {source.section}</p>
            <p className="mt-1 text-slate-300">{source.text}</p>
            <ul className="mt-2 space-y-1">
              {source.references.map(reference => {
                const href = referenceLink(reference.location)
                return <li key={reference.location}>
                  {href ? <a href={href} className="underline underline-offset-4 hover:text-teal-200">{reference.title}</a> : reference.title}
                </li>
              })}
            </ul>
          </li>)}
        </ul> : <p className="mt-2 text-slate-300">No source references were returned.</p>}
      </div>}
    </div>}
  </section>
}
