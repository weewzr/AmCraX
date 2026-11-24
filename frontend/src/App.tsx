import { lazy, Suspense, type ReactNode } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { SiteLayout } from './site/SiteLayout'
import { REDIRECTS } from './site/routes'
import { PageHero } from './site/ui'

// Every page is its own chunk: the landing page (the simulator) loads only the frame and the simulator; the chart library,
// the research pages and the engineering dashboard (React Flow, eleven pages) load when they are opened.
const PlatformApp = lazy(() => import('./platform/PlatformApp'))
const PfdSite = lazy(() => import('./site/pages/PfdSite'))
const Home = lazy(() => import('./site/pages/Home'))
const Why = lazy(() => import('./site/pages/Why'))
const Methodology = lazy(() => import('./site/pages/Methodology'))
const Architecture = lazy(() => import('./site/pages/Architecture'))
const Docs = lazy(() => import('./site/pages/Docs'))
const About = lazy(() => import('./site/pages/About'))
const Results = lazy(() => import('./site/pages/Results'))
const Research = lazy(() => import('./site/pages/Research'))
const Hypotheses = lazy(() => import('./site/pages/Hypotheses'))
// The process simulator is the landing page ("/"); its graphs load as a further chunk when they come into view.
const SimulatorPage = lazy(() => import('./simulator/SimulatorPage'))

const Loading = ({ what }: { what: string }) => <div className="wrap" style={{ padding: '48px 24px' }} role="status">Loading {what} ...</div>
const L = ({ what, children }: { what: string; children: ReactNode }) => <Suspense fallback={<Loading what={what} />}>{children}</Suspense>

function NotFound() {
  return (
    <PageHero eyebrow="404" title="Page not found" lead={<>This page does not exist. <Link to="/">Back to the simulator</Link> or <Link to="/overview">the overview</Link>; <kbd>Ctrl</kbd> + <kbd>K</kbd> lists every page.</>} />
  )
}

/** Public site at "/", engineering dashboard under "/platform" (all dashboard links are built with site/routes.platformPath). */
export default function App() {
  return (
    <Routes>
      <Route element={<SiteLayout />}>
        <Route index element={<L what="the simulator"><SimulatorPage /></L>} />
        <Route path="overview" element={<L what="the overview"><Home /></L>} />
        <Route path="why" element={<L what="the page"><Why /></L>} />
        <Route path="pfd" element={<L what="the diagram"><PfdSite /></L>} />
        <Route path="methodology" element={<L what="the methodology"><Methodology /></L>} />
        <Route path="results" element={<L what="the results"><Results /></L>} />
        <Route path="architecture" element={<L what="the architecture"><Architecture /></L>} />
        <Route path="research" element={<L what="the validation record"><Research /></L>} />
        <Route path="hypotheses" element={<L what="the hypothesis evidence"><Hypotheses /></L>} />
        <Route path="hypotheses/:page" element={<L what="the hypothesis evidence"><Hypotheses /></L>} />
        <Route path="docs" element={<L what="the documentation"><Docs /></L>} />
        <Route path="about" element={<L what="the page"><About /></L>} />
        {REDIRECTS.map((r) => <Route key={r.from} path={r.from.slice(1)} element={<Navigate to={r.to} replace />} />)}
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="platform/*" element={<L what="the platform"><PlatformApp /></L>} />
    </Routes>
  )
}
