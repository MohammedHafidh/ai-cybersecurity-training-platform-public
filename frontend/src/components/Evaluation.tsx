import { useEffect, useState } from 'react'
import { createApiClient, type EvaluationSummary } from '../api/client'
import { scenarioNames } from '../api/evidence'

const scopes = {
  overall: 'All lab runs',
  auth: scenarioNames.brute_force,
  web: scenarioNames.sql_injection,
  network: scenarioNames.reconnaissance,
}
type Scope = keyof typeof scopes
type Metrics = EvaluationSummary['metrics']['rule']['overall']

const definitions = [
  ['accuracy', 'Accuracy', 'Share of all runs classified correctly.'],
  ['precision', 'Precision', 'Share of flagged runs that were labeled malicious.'],
  ['recall', 'Recall', 'Share of malicious runs that were flagged.'],
  ['f1', 'F1', 'Harmonic mean of precision and recall.'],
  ['false_positive_rate', 'False positive rate', 'Share of benign runs that were flagged.'],
] as const

const percent = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 })

function DetectorMetrics({ detector, version, result }: { detector: string; version: string; result: Metrics }) {
  const labels = result.label_order
  return <article className="min-w-0 rounded-2xl border border-white/10 bg-slate-900/80 p-5 sm:p-6">
    <h3 className="text-lg font-semibold">{detector}</h3>
    <p className="mt-1 text-sm text-slate-300">{version}</p>
    <dl className="mt-4 grid gap-4 sm:grid-cols-2">
      {definitions.map(([key, name, meaning]) => <div key={key}>
        <dt className="text-sm text-slate-300">{name}</dt>
        <dd className="text-xl font-semibold tabular-nums">{percent.format(result[key])}</dd>
        <dd className="text-xs text-slate-300">{meaning}</dd>
      </div>)}
    </dl>
    <div className="mt-5 overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="pb-2 text-left font-semibold">Confusion matrix · {result.sample_count} runs</caption>
        <thead>
          <tr>
            <th scope="col" className="py-2 pr-2">Actual label</th>
            {labels.map(label => <th scope="col" key={label} className="p-2">Predicted {label}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10 border-t border-white/10">
          {labels.map((actual, row) => <tr key={actual}>
            <th scope="row" className="py-2 pr-2 capitalize">{actual}</th>
            {labels.map((predicted, column) => <td key={predicted} className="p-2 tabular-nums">
              {result.confusion_matrix[row][column]}
            </td>)}
          </tr>)}
        </tbody>
      </table>
    </div>
  </article>
}

export function Evaluation({ baseUrl }: { baseUrl: string }) {
  const [result, setResult] = useState<EvaluationSummary | 'error' | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(5000)])
    async function load() {
      try {
        const report = await createApiClient(baseUrl).evaluation(signal)
        if (!controller.signal.aborted) setResult(report)
      } catch {
        if (!controller.signal.aborted) setResult('error')
      }
    }
    void load()
    return () => controller.abort()
  }, [baseUrl, attempt])
  return <section id="evaluation" aria-labelledby="evaluation-title" className="mt-14 scroll-mt-6">
    <h2 id="evaluation-title" className="text-2xl font-semibold tracking-tight">Held-out evaluation</h2>
    {!result && <p role="status" className="mt-4">Loading evaluation…</p>}
    {result === 'error' && <div className="mt-4">
      <p role="alert" className="text-amber-200">Could not load the frozen evaluation.</p>
      <button type="button" className="mt-3 rounded-lg border border-white/15 px-4 py-2 text-sm hover:bg-white/10"
        onClick={() => { setResult(null); setAttempt(value => value + 1) }}>Try again</button>
    </div>}
    {result && result !== 'error' && <EvaluationResults report={result} />}
  </section>
}

export function EvaluationResults({ report }: { report: EvaluationSummary }) {
  const [scope, setScope] = useState<Scope>('overall')
  const { metrics, model_version, rule_version } = report
  return <>
    <div className="flex flex-wrap items-end justify-between gap-4">
      <p className="mt-2 text-sm text-slate-300">Frozen Day 32 results. A run is flagged when any observation is predicted malicious.</p>
      <label className="text-sm">
        <span className="mr-2">Lab scenario</span>
        <select value={scope} onChange={event => setScope(event.target.value as Scope)}
          className="rounded-lg border border-white/15 bg-slate-900 p-2">
          {Object.entries(scopes).map(([key, name]) => <option key={key} value={key}>{name}</option>)}
        </select>
      </label>
    </div>
    <div className="mt-5 grid gap-4 lg:grid-cols-2">
      <DetectorMetrics detector="Rule engine" version={rule_version} result={metrics.rule[scope]} />
      <DetectorMetrics detector="Machine learning" version={model_version} result={metrics.ml[scope]} />
    </div>
    <p className="mt-4 rounded-lg border border-amber-200/20 bg-amber-200/5 p-4 text-sm text-amber-100">
      These results cover {metrics.rule.overall.sample_count} scripted lab runs across three scenarios, four per scenario.
      They describe performance on this lab dataset. Production performance and generalization are unknown.
      A rate of 0% can occur when its denominator is zero, such as precision when a detector flags no runs.
    </p>
  </>
}
