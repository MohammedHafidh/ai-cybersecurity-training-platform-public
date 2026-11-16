import { ApiConnection } from './components/ApiConnection'
import { AppShell } from './components/AppShell'
import { RecentEvents } from './components/RecentEvents'
import { DetectionEvidence } from './components/DetectionEvidence'
import { scenarioNames } from './api/evidence'

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function App() {
  return (
    <AppShell>
      <div className="grid items-start gap-10 lg:grid-cols-[1.3fr_1fr]">
        <section id="overview" aria-labelledby="overview-title">
          <h1 id="overview-title" className="max-w-xl text-4xl font-semibold tracking-tight sm:text-6xl">
            Security activity dashboard
          </h1>
          <p className="mt-5 max-w-lg text-lg leading-8 text-slate-300">
            Learn to distinguish observed evidence from rule and machine learning predictions across authentication, web, and network activity.
          </p>
          <ul aria-label="Training scenarios" className="mt-7 flex flex-wrap gap-2">
            {[scenarioNames.brute_force, scenarioNames.sql_injection, scenarioNames.reconnaissance].map(scenario => (
              <li key={scenario} className="rounded-full border border-white/10 px-3 py-1.5 text-sm text-slate-300">{scenario}</li>
            ))}
          </ul>
        </section>
        <ApiConnection baseUrl={apiBase} />
      </div>
      <RecentEvents baseUrl={apiBase} />
      <DetectionEvidence baseUrl={apiBase} />
    </AppShell>
  )
}
