import { useEffect, useState } from 'react'
import { createApiClient, type DetectionDetail, type DetectionSummary } from '../api/client'
import { evidenceList, evidenceObject, featureName, maliciousProbability, scenarioNames } from '../api/evidence'

type Result<T> = { data: T } | { error: true }
const utc = new Intl.DateTimeFormat('en-GB', {
  dateStyle: 'medium', timeStyle: 'medium', timeZone: 'UTC',
})

function EvidenceReferences({ label, values }: { label: string; values: unknown }) {
  const entries = evidenceList(values)
  return <div className="min-w-0">
    <h4 className="font-medium">{label}</h4>
    <p className="mt-1 break-all text-sm text-slate-300">{entries.join(', ') || 'Unavailable'}</p>
  </div>
}

export function DetectionEvidence({ baseUrl }: { baseUrl: string }) {
  const [list, setList] = useState<Result<DetectionSummary[]> | null>(null)
  const [selected, setSelected] = useState('')
  const [detail, setDetail] = useState<Result<DetectionDetail> | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(5000)])
    async function load() {
      try {
        const data = await createApiClient(baseUrl).recentDetections(signal)
        if (!controller.signal.aborted) setList({ data })
      } catch {
        if (!controller.signal.aborted) setList({ error: true })
      }
    }
    void load()
    return () => controller.abort()
  }, [baseUrl, attempt])

  useEffect(() => {
    if (!selected) return
    const controller = new AbortController()
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(5000)])
    async function load() {
      try {
        const data = await createApiClient(baseUrl).detectionDetail(selected, signal)
        if (!controller.signal.aborted) setDetail({ data })
      } catch {
        if (!controller.signal.aborted) setDetail({ error: true })
      }
    }
    void load()
    return () => controller.abort()
  }, [baseUrl, selected, attempt])

  function refresh() {
    setList(null)
    setDetail(null)
    setAttempt(value => value + 1)
  }

  return <section id="detection-evidence" aria-labelledby="detection-title" className="mt-14">
    <div className="flex flex-wrap items-center justify-between gap-4">
      <h2 id="detection-title" className="text-2xl font-semibold tracking-tight">Detection evidence</h2>
      <button type="button" onClick={refresh} disabled={!list}
        className="rounded-lg border border-white/15 px-4 py-2 text-sm hover:bg-white/10 disabled:opacity-50">Refresh detections</button>
    </div>
    {!list && <p role="status" className="mt-4">Loading detections…</p>}
    {list && 'error' in list && <p role="alert" className="mt-4 text-amber-200">Could not load detections. Refresh to try again.</p>}
    {list && 'data' in list && (list.data.length ? <div className="mt-5">
      <label htmlFor="detection-select" className="block text-sm">Recent stored predictions</label>
      <select id="detection-select" value={selected} onChange={event => {
        setDetail(null)
        setSelected(event.target.value)
      }} className="mt-2 w-full rounded-lg border border-white/15 bg-slate-900 p-3 text-sm">
        <option value="">Choose a prediction to inspect its evidence</option>
        {selected && !list.data.some(row => row.detection_id === selected) &&
          <option value={selected}>Previously selected prediction</option>}
        {list.data.map(row => <option key={row.detection_id} value={row.detection_id}>
          {row.run_id} · {row.detector === 'rule' ? 'Rule' : 'ML'} · {row.predicted_label} · {row.detection_id.slice(4, 12)}
        </option>)}
      </select>
    </div> : <p role="status" className="mt-4">No stored detections yet.</p>)}
    {selected && !detail && <p role="status" className="mt-4">Loading evidence…</p>}
    {detail && 'error' in detail && <p role="alert" className="mt-4 text-amber-200">Could not load this prediction. Refresh to try again.</p>}
    {detail && 'data' in detail && <Observation detail={detail.data} />}
  </section>
}

function Observation({ detail }: { detail: DetectionDetail }) {
  const { run, evidence } = detail
  const predictions = [detail, ...detail.counterparts]
  const rule = predictions.filter(row => row.detector === 'rule')
  const ml = predictions.filter(row => row.detector === 'ml')
  const features = Object.entries(evidenceObject(evidence.observed_features))
    .filter(([, value]) => typeof value === 'boolean' || typeof value === 'number')

  return <div className="mt-5 space-y-6 rounded-2xl border border-white/10 bg-slate-900/80 p-5 sm:p-6">
    <div>
      <h3 className="font-semibold">{scenarioNames[run.scenario]}</h3>
      <p className="mt-1 break-words text-sm text-slate-300">Run {detail.run_id} · Expected label {run.expected_label}</p>
      <p className="mt-1 break-words text-sm text-slate-300">{run.source} → {run.target}</p>
      <p className="mt-1 text-sm text-slate-300">{utc.format(new Date(run.start_time))} to {utc.format(new Date(run.end_time))} UTC</p>
    </div>
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-xl border border-white/10 p-4">
        <h3 className="font-semibold text-teal-200">Rule output</h3>
        {!rule.length && <p className="mt-2 text-sm">No stored rule output for this observation.</p>}
        {rule.map(row => {
          const matched = evidenceObject(row.evidence.rule)
          const scenario = row.evidence.predicted_scenario
          return <div key={row.detection_id} className="mt-3 space-y-1 text-sm">
            <p>Prediction <strong>{row.predicted_label}</strong> · {row.detector_version}</p>
            {typeof scenario === 'string' && scenario !== 'benign' && Object.hasOwn(scenarioNames, scenario) &&
              <p>Rule scenario · {scenarioNames[scenario as keyof typeof scenarioNames]}</p>}
            {typeof matched.feature === 'string' && typeof matched.observed === 'number' && typeof matched.threshold === 'number' &&
              <p>{featureName(matched.feature)} · observed {matched.observed} · trigger threshold ≥ {matched.threshold}</p>}
            {matched.window_seconds === 60 && <p>Measured in a 60-second window.</p>}
            {matched.aggregation_unit === 'web run' && <p>Measured across the web run. Token matches alone cannot establish that an injection succeeded.</p>}
          </div>
        })}
      </div>
      <div className="rounded-xl border border-white/10 p-4">
        <h3 className="font-semibold text-teal-200">ML output</h3>
        {!ml.length && <p className="mt-2 text-sm">No stored ML output for this observation.</p>}
        {ml.map(row => {
          const probability = maliciousProbability(row.evidence.malicious_probability)
          return <div key={row.detection_id} className="mt-3 space-y-1 text-sm">
            <p>Prediction <strong>{row.predicted_label}</strong> · {row.detector_version}</p>
            {probability !== undefined && <p>Model probability of malicious class · {probability}</p>}
          </div>
        })}
      </div>
    </div>
    <div>
      <h3 className="font-semibold">Observed features</h3>
      <dl className="mt-2 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        {features.map(([key, value]) => <div key={key}>
          <dt className="text-slate-300">{featureName(key)}</dt>
          <dd>{typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}</dd>
        </div>)}
      </dl>
      {!features.length && <p className="mt-2 text-sm">No stored features for this observation.</p>}
    </div>
    <div className="grid gap-3 sm:grid-cols-2">
      <EvidenceReferences label="Event IDs" values={evidence.event_ids} />
      <EvidenceReferences label="Log references" values={evidence.raw_source_files} />
    </div>
  </div>
}
