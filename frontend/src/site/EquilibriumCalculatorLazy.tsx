import { lazy, Suspense, useEffect, useRef, useState } from 'react'

// The calculator draws a Recharts chart: its chunk is requested when the placeholder comes near the viewport or shortly after first paint,
// so the landing page's first paint does not wait for the chart library.
const Calc = lazy(() => import('./EquilibriumCalculator').then((m) => ({ default: m.EquilibriumCalculator })))

export function EquilibriumCalculatorLazy() {
  const ref = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(typeof IntersectionObserver === 'undefined')
  useEffect(() => {
    const el = ref.current
    if (near || !el) return
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setNear(true); io.disconnect() } }, { rootMargin: '800px 0px' })
    io.observe(el)
    const t = window.setTimeout(() => setNear(true), 800)
    return () => { io.disconnect(); window.clearTimeout(t) }
  }, [near])
  return (
    <div ref={ref} style={{ minHeight: near ? undefined : 520 }}>
      {near ? <Suspense fallback={<div className="card calc" role="status">Loading the calculator ...</div>}><Calc /></Suspense> : null}
    </div>
  )
}
