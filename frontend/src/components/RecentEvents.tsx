import { useEffect, useState } from 'react'
import { createApiClient, type RecentEvent } from '../api/client'

const limit = 20
const sourceLabels = { auth: 'Authentication', web: 'Web', network: 'Network' }
const eventLabels: Record<string, string> = {
  ssh_password: 'SSH password event',
  http_request: 'HTTP request',
  tcp_connection: 'TCP connection',
}
const utc = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium', timeStyle: 'medium', timeZone: 'UTC',
})

type State =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; rows: RecentEvent[] }

export function RecentEvents({ baseUrl }: { baseUrl: string }) {
  const [state, setState] = useState<State>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      controller.abort()
      setState({ status: 'error' })
    }, 5000)
    async function load() {
      try {
        const rows = await createApiClient(baseUrl).recentEvents(limit, controller.signal)
        if (!controller.signal.aborted) setState({ status: 'ready', rows })
      } catch {
        if (!controller.signal.aborted) setState({ status: 'error' })
      } finally {
        window.clearTimeout(timer)
      }
    }
    void load()
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [baseUrl, attempt])

  function refresh() {
    setState({ status: 'loading' })
    setAttempt(value => value + 1)
  }

  return (
    <section id="recent-events" aria-labelledby="events-title" className="mt-14">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="events-title" className="text-2xl font-semibold tracking-tight">Recent events</h2>
          <p className="mt-2 text-sm text-slate-400">Observed activity from ingested runs, newest first.</p>
        </div>
        <button type="button" onClick={refresh} disabled={state.status === 'loading'}
          className="rounded-lg border border-white/15 px-4 py-2 text-sm hover:bg-white/10 disabled:opacity-50">
          {state.status === 'error' ? 'Try again' : 'Refresh'}
        </button>
      </div>
      <div className="mt-5 rounded-2xl border border-white/10 bg-slate-900/80" aria-busy={state.status === 'loading'}>
        {state.status === 'loading' && <p role="status" className="p-6 text-slate-300">Loading recent events…</p>}
        {state.status === 'error' && <p role="alert" className="p-6 text-amber-200">Could not load recent events. Check the API and database connection, then try again.</p>}
        {state.status === 'ready' && (state.rows.length === 0
          ? <p role="status" className="p-6 text-slate-300">No events have been ingested yet.</p>
          : <>
              <p role="status" className="border-b border-white/10 px-6 py-3 text-sm text-slate-300">
                Showing {state.rows.length} {state.rows.length === 1 ? 'event' : 'events'} (up to {limit})
              </p>
              <div className="overflow-x-auto" role="region" aria-label="Recent events table" tabIndex={0}>
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      {['Time (UTC)', 'Source', 'Event', 'Run ID', 'Log reference'].map(heading => (
                        <th key={heading} scope="col" className="whitespace-nowrap px-6 py-3 font-medium">{heading}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {state.rows.map(row => (
                      <tr key={row.event_id}>
                        <td className="whitespace-nowrap px-6 py-4"><time dateTime={row.timestamp}>{utc.format(new Date(row.timestamp))}</time></td>
                        <td className="px-6 py-4 text-teal-200">{sourceLabels[row.source_type]}</td>
                        <td className="whitespace-nowrap px-6 py-4">{Object.hasOwn(eventLabels, row.event_type) ? eventLabels[row.event_type] : row.event_type}</td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-300">{row.run_id}</td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-300">{row.raw_source_file}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>)}
      </div>
    </section>
  )
}
