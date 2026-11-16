import type { ReactNode } from 'react'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-10 focus:bg-white focus:p-3 focus:text-slate-950">
        Skip to content
      </a>
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5">
          <a href="#overview" className="flex items-center gap-3 font-semibold">
            <span aria-hidden="true" className="h-5 w-5 rotate-12 rounded-sm border-2 border-teal-300" />
            Security Training Platform
          </a>
          <nav aria-label="Main navigation" className="flex flex-wrap gap-5 text-sm text-slate-300">
            <a className="hover:text-teal-200" href="#overview">Overview</a>
            <a className="hover:text-teal-200" href="#recent-events">Recent events</a>
            <a className="hover:text-teal-200" href="#detection-evidence">Detection evidence</a>
            <a className="hover:text-teal-200" href="#connection">API connection</a>
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-6xl px-6 py-14 sm:py-20">
        {children}
      </main>
    </div>
  )
}
