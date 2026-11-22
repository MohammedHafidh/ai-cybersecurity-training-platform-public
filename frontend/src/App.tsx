import { useEffect, useState } from 'react'
import { Evaluation } from './components/Evaluation'
import { ApiConnection } from './components/ApiConnection'
import { RecentEvents } from './components/RecentEvents'
import { api, base, progress, type Exercise, type Lesson } from './training'
import { StartExercise, ExercisePage } from './ExercisePage'
import { DetectionEvidence } from './components/DetectionEvidence'
import { AppShell } from './components/AppShell'

export default function App() {
  const [route, setRoute] = useState(location.hash.slice(1) || '/')
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [error, setError] = useState('')
  const [states,setStates] = useState<Record<string,Exercise>>({})
  useEffect(()=>{if(route==='/')Promise.all(Object.entries(progress()).map(async ([key,id])=>[key,await api<Exercise>('/training/exercises/'+id)] as const)).then(rows=>setStates(Object.fromEntries(rows))).catch(()=>{})},[route])
  useEffect(() => { const change = () => { setRoute(location.hash.slice(1) || '/'); window.scrollTo(0, 0) }; window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change) }, [])
  useEffect(() => { api<Lesson[]>('/training/scenarios').then(setLessons).catch(e => setError(e.message)) }, [])
  useEffect(() => { document.getElementById('main')?.focus({ preventScroll: true }) }, [route])
  const exerciseRoute = route.match(/^\/exercises\/([a-f0-9]{32})(?:\/(analysis|quiz|complete))?(?:\?focus=ai)?$/)
  const selected = lessons.find(l => route === '/scenarios/' + l.id)
  return <>
    <a href="#main" onClick={e=>{e.preventDefault();document.getElementById('main')?.focus()}} className="skip-link">Skip to content</a>
    <header className="site-header"><a className="brand" href="#/">FIELDNOTES<span>Cybersecurity learning lab</span></a><nav aria-label="Main navigation">
      <a href="#/" aria-current={route === '/' ? 'page' : undefined}>Learn</a><a href="#/results" aria-current={route === '/results' ? 'page' : undefined}>Results & limitations</a><a href="#/help" aria-current={route === '/help' ? 'page' : undefined}>Help</a>
    </nav><span className="local-label"><i /> Local learning environment</span></header>
    <main id="main" tabIndex={-1} className="platform-main">
      {error && <div role="alert" className="notice">The learning service is unavailable. {error} <button onClick={() => location.reload()}>Try again</button></div>}
      {!lessons.length && !error && <p role="status">Preparing your learning space…</p>}
      {route === '/' && <><section className="hero"><p className="eyebrow">Observe. Understand. Defend.</p><h1>Learn cybersecurity<br />through <em>real evidence.</em></h1><p className="hero-copy">Practice safely. Follow the logs. Discover how rules and machine learning interpret the same activity—and learn where they can be wrong.</p><a className="button" href="#scenarios" onClick={e=>{e.preventDefault();document.getElementById('scenarios')?.scrollIntoView()}}>Explore the scenarios <span aria-hidden="true">↗</span></a><div className="hero-note"><strong>Three scenarios. One connected story.</strong><span>Controlled activity → evidence → detection → understanding</span></div></section>
        <section id="scenarios" className="scenario-section"><div className="section-heading"><div><p className="eyebrow">Your learning path</p><h2>Start with a question.<br />Leave with understanding.</h2></div><p>Choose a scenario. Each lesson connects an exercise to the evidence it leaves behind.</p></div><div className="scenario-grid">{lessons.map(l => <article className="scenario-card" key={l.id}><p className="eyebrow">{l.eyebrow}</p><span className="progress-label">{states[l.id]?.completed ? 'Completed' : states[l.id] ? 'In Progress' : 'Not Started'}</span><h3>{l.title}</h3><p>{l.objective}</p><div className="card-bottom"><span>Guided / Beginner</span><a className="text-link" href={states[l.id] ? '#/exercises/'+states[l.id].id+(states[l.id].completed?'/complete':'') : '#/scenarios/' + l.id}>{states[l.id] ? 'Continue learning' : 'Start learning'} <span aria-hidden="true">↗</span></a></div></article>)}</div></section>
        <section className="learning-promise"><span className="step-number">01—06</span><h2>Learn the story behind the alert.</h2><p>Read a guide, practice in an isolated lab, inspect the evidence, compare detectors, ask a grounded question and test your understanding.</p></section></>}
      {selected && <Guide lesson={selected} />}{exerciseRoute && <ExercisePage key={exerciseRoute[1]} id={exerciseRoute[1]} view={exerciseRoute[2] || 'exercise'} lessons={lessons} />}
      {route === '/evidence' && <div className="legacy"><AppShell><h1>Security activity dashboard</h1><ApiConnection baseUrl={base}/><RecentEvents baseUrl={base}/><DetectionEvidence baseUrl={base}/><Evaluation baseUrl={base}/></AppShell></div>}
      {route === '/results' && <div className="legacy"><p className="eyebrow">Honest measurement</p><h1>Results & limitations</h1><p>These frozen results describe a small controlled dataset, not production detection performance.</p><Evaluation baseUrl={base} /><RecentEvents baseUrl={base} /></div>}
      {route === '/help' && <><p className="eyebrow">A safe place to learn</p><h1>Help & readiness</h1><p>The operator starts the platform once. Students perform training entirely in this browser. Live exercises need the approved private local lab; demonstrations will always be labeled separately.</p><div className="legacy"><ApiConnection baseUrl={base} /></div><p>No external targets or custom commands are accepted. If a service is unavailable, your stored results remain available.</p></>}
      {lessons.length > 0 && route !== '/' && route !== '/results' && route !== '/help' && route !== '/evidence' && !selected && !exerciseRoute && <section><h1>Page not found</h1><a href="#/">Return to learning</a></section>}
    </main><footer className="site-footer"><span>FIELDNOTES / A controlled cybersecurity learning platform</span><span>Rules and ML detect. Local AI explains.</span></footer>
  </>
}

export function Guide({ lesson: l }: { lesson: Lesson }) {
  return <><a className="text-link" href="#/">← All scenarios</a><section className="guide-hero"><p className="eyebrow">{l.eyebrow}</p><h1>{l.title}</h1><p className="lead">{l.objective}</p></section><div className="guide-layout"><aside className="guide-index"><p className="eyebrow">In this lesson</p>{['Understand', 'Practice safely', 'Read the evidence', 'Compare detectors', 'Learn to defend'].map((s, i) => <a key={s} href={'#guide-' + i} onClick={e => { e.preventDefault(); document.getElementById('guide-' + i)?.scrollIntoView() }}>{String(i + 1).padStart(2, '0')} / {s}</a>)}</aside><div className="lesson-body">
    <section id="guide-0"><h2>What is {l.title.toLowerCase()}?</h2><p>{l.definition}</p><h3>Why it matters</h3><p>{l.importance}</p><h3>Learning objectives</h3><ul>{l.objectives.map(o => <li key={o}>{o}</li>)}</ul></section>
    <section id="guide-1"><p className="eyebrow">Your controlled exercise</p><h2>Practice inside the boundary.</h2><p>{l.activity}</p><div className="notice"><strong>Safety first.</strong> {l.safety}</div><ol>{l.steps.map(s => <li key={s}>{s}</li>)}</ol><StartExercise lesson={l} /></section>
    <section id="guide-2"><h2>Know what to look for.</h2><p>{l.observe}</p><h3>Log concepts</h3><p>{l.logs}</p><dl className="feature-dictionary">{Object.entries(l.features).map(([name, text]) => <div key={name}><dt>{name}</dt><dd>{text}</dd></div>)}</dl></section>
    <section id="guide-3"><h2>Two detectors. Independent judgments.</h2><h3>Rule-based detection</h3><p>{l.rule}</p><h3>Machine learning</h3><p>{l.ml}</p><div className="notice"><strong>Look for uncertainty.</strong> {l.limitations}</div></section>
    <section id="guide-4"><h2>From observation to defense.</h2><p>{l.mitigation}</p><h3>Trusted references</h3><ul>{l.references.map(r => <li key={r.url}><a href={r.url} target="_blank" rel="noreferrer">{r.title} ↗</a></li>)}</ul></section>
  </div></div></>
}
