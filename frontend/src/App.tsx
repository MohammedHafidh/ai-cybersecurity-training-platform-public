function App() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-16">
        <section className="space-y-6">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
            Capstone Project
          </p>
          <h1 className="max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
            AI-Assisted Cybersecurity Training Platform
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-slate-300">
            Controlled attacks generate real logs that will be processed, detected by rules and machine learning, and explained by a local LLM with RAG.
          </p>
          <div className="inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
            Frontend skeleton is running
          </div>
        </section>
      </div>
    </main>
  )
}

export default App
