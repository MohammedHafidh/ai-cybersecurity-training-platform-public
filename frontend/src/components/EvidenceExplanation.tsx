import { evidenceObject, featureName } from '../api/evidence'

function ruleFinding(value: unknown): string | undefined {
  const { feature, observed, threshold, operator } = evidenceObject(value)
  if (typeof feature !== 'string' || typeof observed !== 'number' || typeof threshold !== 'number'
    || !Number.isFinite(observed) || !Number.isFinite(threshold) || operator !== '>=') return
  const outcome = observed >= threshold ? 'met' : 'fell below'
  return `${featureName(feature)}: ${observed} ${outcome} the rule threshold of ${threshold}.`
}

export function EvidenceExplanation({ rules }: { rules: { detection_id: string; evidence: Record<string, unknown> }[] }) {
  const findings = rules.flatMap(row => {
    const finding = ruleFinding(row.evidence.rule)
    return finding ? [{ id: row.detection_id, finding }] : []
  })
  return <aside aria-labelledby="explanation-title" className="border-t border-white/10 pt-5">
    <h3 id="explanation-title" className="font-semibold">Explanation preview</h3>
    {findings.length ? <ul className="mt-2 space-y-1 text-sm text-slate-200">
      {findings.map(({ id, finding }) => <li key={id}>{finding}</li>)}
    </ul> : <p className="mt-2 text-sm text-slate-200">No supported rule threshold is stored for this observation.</p>}
    <p className="mt-2 text-sm text-slate-300">
      This summary uses stored rule evidence. The ML panel shows the model prediction and its available probability.
      LLM explanations are unavailable.
    </p>
  </aside>
}
