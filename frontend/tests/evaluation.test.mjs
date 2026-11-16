import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'
import { createApiClient } from '../src/api/client.ts'

test('the dashboard renders the frozen evaluation and separates the evidence explanation', async () => {
  const server = await createServer({
    server: { middlewareMode: true, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] },
    appType: 'custom',
  })
  try {
    const { EvaluationResults } = await server.ssrLoadModule('/src/components/Evaluation.tsx')
    const { EvidenceExplanation } = await server.ssrLoadModule('/src/components/EvidenceExplanation.tsx')
    const frozen = JSON.parse(await readFile(new URL('../../data/processed/day32/evaluation.json', import.meta.url)))
    const base = process.env.API_SMOKE_URL ?? 'http://127.0.0.1:8765'
    const report = await createApiClient(base).evaluation(AbortSignal.timeout(5000))
    assert.deepEqual(report, frozen)
    const { metrics } = frozen
    const html = renderToStaticMarkup(createElement(EvaluationResults, { report }))
    const matrices = [...html.matchAll(/<table\b.*?<\/table>/g)].map(([table]) =>
      [...table.matchAll(/<td[^>]*>(\d+)<\/td>/g)].map(([, count]) => Number(count)))
    assert.deepEqual(matrices, [metrics.rule.overall.confusion_matrix.flat(), metrics.ml.overall.confusion_matrix.flat()])
    assert.match(html, /Actual label/)
    assert.match(html, /Predicted benign/)
    assert.match(html, /Predicted malicious/)
    for (const title of ['Accuracy', 'Precision', 'Recall', 'F1', 'False positive rate']) {
      assert.equal(html.split(`>${title}</dt>`).length - 1, 2)
    }
    assert.match(html, /12 scripted lab runs/)
    assert.match(html, /Production performance and generalization are unknown/)
    for (const scenario of ['Brute force', 'SQL injection', 'Network reconnaissance']) {
      assert.ok(html.includes(scenario))
    }

    const known = { feature: 'failed_login_count', observed: 3, threshold: 3, operator: '>=' }
    const explain = (...findings) => renderToStaticMarkup(createElement(EvidenceExplanation, {
      rules: findings.map((rule, id) => ({ detection_id: String(id), evidence: { rule } })),
    }))
    const explanation = explain(known, { ...known, observed: 2 })
    assert.match(explanation, /<aside aria-labelledby="explanation-title"/)
    assert.match(explanation, /Failed SSH password events: 3 met the rule threshold of 3/)
    assert.match(explanation, /Failed SSH password events: 2 fell below the rule threshold of 3/)
    assert.match(explanation, /This summary uses stored rule evidence/)
    assert.match(explain({ ...known, observed: null }), /No supported rule threshold/)
  } finally {
    await server.close()
  }
})
