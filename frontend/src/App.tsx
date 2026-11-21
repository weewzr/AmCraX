import { lazy, Suspense } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { SiteLayout } from './site/SiteLayout'
import { PageHero } from './site/ui'
import Home from './site/pages/Home'
import Why from './site/pages/Why'
import Methodology from './site/pages/Methodology'
import Architecture from './site/pages/Architecture'
import Docs from './site/pages/Docs'
import About from './site/pages/About'

// The engineering dashboard (React Flow, eleven pages) is a separate chunk: visitors of the public site do not download it until they open /platform.
const PlatformApp = lazy(() => import('./platform/PlatformApp'))
const PfdSite = lazy(() => import('./site/pages/PfdSite'))
// Recharts-heavy site pages are separate chunks, so the landing page loads without the chart library.
const Results = lazy(() => import('./site/pages/Results'))
const Research = lazy(() => import('./site/pages/Research'))

const Loading = ({ what }: { what: string }) => <div className="wrap" style={{ padding: '48px 24px' }} role="status">Loading {what} ...</div>

function NotFound() {
  return (
    <PageHero eyebrow="404" title="Page not found" lead={<>This page does not exist. <Link to="/">Back to the overview</Link>.</>} />
  )
}

/** Public site at "/", engineering dashboard under "/platform" (all dashboard links are built with site/routes.platformPath). */
export default function App() {
  return (
    <Routes>
      <Route element={<SiteLayout />}>
        <Route index element={<Home />} />
        <Route path="why" element={<Why />} />
        <Route path="pfd" element={<Suspense fallback={<Loading what="the diagram" />}><PfdSite /></Suspense>} />
        <Route path="methodology" element={<Methodology />} />
        <Route path="results" element={<Suspense fallback={<Loading what="the results" />}><Results /></Suspense>} />
        <Route path="architecture" element={<Architecture />} />
        <Route path="research" element={<Suspense fallback={<Loading what="the validation record" />}><Research /></Suspense>} />
        <Route path="docs" element={<Docs />} />
        <Route path="about" element={<About />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="platform/*" element={<Suspense fallback={<Loading what="the platform" />}><PlatformApp /></Suspense>} />
    </Routes>
  )
}
