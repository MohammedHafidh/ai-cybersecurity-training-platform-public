import { useEffect, useState } from 'react'
import { createApiClient } from '../api/client'

type State = 'checking' | 'connected' | 'unavailable'

export function ApiConnection({ baseUrl }: { baseUrl: string }) {
  const [state, setState] = useState<State>('checking')
  const [attempt, setAttempt] = useState(0)
  const [docs, setDocs] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      controller.abort()
      setState('unavailable')
    }, 5000)
    async function check() {
      try {
        const api = createApiClient(baseUrl)
        setDocs(api.docsUrl)
        await api.health(controller.signal)
        if (!controller.signal.aborted) setState('connected')
      } catch {
        if (!controller.signal.aborted) setState('unavailable')
      } finally {
        window.clearTimeout(timeout)
      }
    }
    void check()
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [baseUrl, attempt])

  const status = { checking: 'Checking connection…', connected: 'API is reachable', unavailable: 'API unavailable' }[state]

  return (
    <section id="connection" aria-labelledby="connection-title" className="rounded-2xl border border-white/10 bg-slate-900/80 p-6 sm:p-8">
      <h2 id="connection-title" className="text-xl font-semibold">API connection</h2>
      <p role="status" className={`mt-4 font-medium ${state === 'connected' ? 'text-teal-300' : state === 'unavailable' ? 'text-amber-200' : 'text-slate-300'}`}>
        {status}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        {state === 'unavailable' ? 'Check that the backend is running and the frontend origin is allowed.' : 'Checks whether the backend responds to its health endpoint.'}
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-4 text-sm">
        <button type="button" disabled={state === 'checking'} onClick={() => {
          setState('checking')
          setAttempt(value => value + 1)
        }} className="rounded-lg border border-teal-300/40 px-4 py-2 font-medium text-teal-200 hover:bg-teal-300/10 disabled:opacity-50">
          Check again
        </button>
        {docs && <a className="text-slate-200 underline underline-offset-4 hover:text-teal-200" href={docs}>Open API docs</a>}
      </div>
    </section>
  )
}
