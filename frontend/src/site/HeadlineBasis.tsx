import { Link } from 'react-router-dom'
import { SourceBadge } from '../components/ui'
import { fmt } from '../data/format'
import { useJson } from './data'
import { srcOf } from './hyp/shape'
import { basisSentence } from './siteHelpers'

/**
 * Headline basis strip, shown on every page (public site and platform). It states the one cost basis and the one
 * carbon-intensity basis that headline numbers refer to, with the value read from the snapshot files:
 *   results/research/reference_scenario/baseline.json      (unified reference LCOH, USD first, SGD in brackets)
 *   results/research/carbon_pricing/carbon_intensity.json  (carbon intensity of the route of that scenario)
 * Nothing numeric is typed here. Legacy values appear only on pages that carry the legacy label. The full basis sentence
 * of each file is in the title of its line and on the linked page.
 */
type O = Record<string, unknown>
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)
const at = (o: unknown, path: string[]): unknown => path.reduce<unknown>((v, k) => (v && typeof v === 'object' ? (v as O)[k] : undefined), o)

export function HeadlineBasis({ compact = false }: { compact?: boolean }) {
  const b = useJson<O>('/api/research/reference_scenario/baseline.json')
  const ci = useJson<O>('/api/research/carbon_pricing/carbon_intensity.json')
  if (b.phase !== 'ready') return null
  const d = b.data
  const usd = num(d.lcoh_USD_per_kg), sgd = num(d.lcoh_SGD_per_kg)
  const scenario = typeof d.scenario === 'string' ? d.scenario : null
  const route = ci.phase === 'ready' && scenario ? (at(ci.data, ['routes', scenario]) as O | undefined) : undefined
  const ciCentral = num(at(route, ['ci_kgCO2e_per_kgH2', 'central']))
  const ciLow = num(at(route, ['ci_kgCO2e_per_kgH2', 'low'])), ciHigh = num(at(route, ['ci_kgCO2e_per_kgH2', 'high']))
  const costSrc = srcOf(at(d, ['provenance', 'source_type']))
  const ciSrc = ci.phase === 'ready' ? srcOf(at(ci.data, ['provenance', 'source_type'])) : null
  const routeLabel = typeof route?.label === 'string' ? route.label : `${scenario ?? ''} NH3`
  return (
    <section className={`basis-strip${compact ? ' basis-compact' : ''}`} aria-label="Headline basis of this site">
      <div className="wrap basis-row">
        <p className="basis-item" data-testid="headline-cost" title={`Unified reference: ${basisSentence(d.description, scenario)}.`}>
          <span className="basis-k">Hydrogen cost</span>{' '}
          <span className="basis-v"><span className="num">{usd === null ? 'n/a' : fmt(usd, 3)}</span> USD/kg H<sub>2</sub>{sgd === null ? null : <span className="basis-alt"> ({fmt(sgd, 3)} SGD/kg)</span>}</span>{' '}
          <span className="basis-b"><Link to="/hypotheses/economics#baseline">unified reference</Link>, {scenario ?? 'reference'} NH3</span>{' '}
          <SourceBadge source={costSrc} />
        </p>
        {ciCentral !== null ? (
          <p className="basis-item" data-testid="headline-ci" title={`${routeLabel}, cradle to PSA outlet, central value${ciLow !== null && ciHigh !== null ? ` (range ${fmt(ciLow, 2)} to ${fmt(ciHigh, 2)})` : ''}; simplified accounting, not a full LCA.`}>
            <span className="basis-k">Carbon intensity</span>{' '}
            <span className="basis-v"><span className="num">{fmt(ciCentral, 2)}</span> kg CO<sub>2</sub>e/kg H<sub>2</sub></span>{' '}
            <span className="basis-b"><Link to="/hypotheses/end-use#carbon-intensity">{scenario ?? ''} NH3 route</Link>, central, not a full LCA</span>{' '}
            <SourceBadge source={ciSrc} />
          </p>
        ) : null}
      </div>
    </section>
  )
}
