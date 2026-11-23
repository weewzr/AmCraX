import { Navigate, useParams } from 'react-router-dom'
import { CatalystView } from '../hyp/CatalystView'
import { EconomicsView } from '../hyp/EconomicsView'
import { EndUseView } from '../hyp/EndUseView'
import { EvidenceMatrix } from '../hyp/EvidenceMatrix'
import { StoredNote, SubNav } from '../hyp/parts'
import { PurificationView } from '../hyp/PurificationView'
import { AspenGallery, ValidationView } from '../hyp/ValidationAspen'
import { HYPOTHESIS_PAGES } from '../routes'
import { PageHero, Section } from '../ui'

const LEAD: Record<string, string> = {
  '': 'Four hypotheses from the project essay, tested with Aspen Plus V15 runs and independent Python models for a Singapore setting (Jurong Island as a representative industrial site; no facility is claimed to exist). Each verdict is SUPPORTED, CONTRADICTED or INCONCLUSIVE, and results that contradict the essay are reported as such.',
  catalyst: 'Hypothesis H3: how much catalyst each rate law needs, what the heat duty and cost are with and without heat integration, and at what catalyst price a low-temperature catalyst stops paying.',
  economics: 'Hypothesis H2: the cost of hydrogen from cracked ammonia under grey, blue and green ammonia price scenarios, with sensitivity, break-even and uncertainty.',
  purification: 'Hypothesis H4: PSA against Pd-Ag membrane, the recovery lost for each purity step, and the cost per kg of hydrogen that meets the end-use specification.',
  'end-use': 'Hypotheses H1 and H2: where cracking is justified against burning ammonia directly, and the life-cycle carbon of each ammonia route against Singapore alternatives.',
  validation: 'The checks each area ran on its own results, with pass, fail and informational counts and every failure named.',
  'aspen-evidence': 'The Aspen Plus V15 windows behind the stored Aspen results.',
}

/** Hypotheses section: evidence matrix at /hypotheses, sub-pages at /hypotheses/<slug>. Everything is read from stored result files. */
export default function Hypotheses() {
  const { page = '' } = useParams()
  const p = HYPOTHESIS_PAGES.find((x) => x.slug === page)
  if (!p) return <Navigate to="/hypotheses" replace />
  return (
    <>
      <PageHero eyebrow="Section 10: hypothesis testing" title={p.slug ? p.title : 'Hypothesis testing'} lead={LEAD[p.slug]}>
        <SubNav current={p.slug} />
      </PageHero>
      <div className="wrap" style={{ paddingTop: 'var(--s5, 24px)' }}><StoredNote extrapolated={p.slug === 'catalyst' || p.slug === ''} /></div>
      {p.slug === '' ? <Section id="matrix" title="Evidence matrix"><EvidenceMatrix /></Section> : null}
      {p.slug === 'catalyst' ? <CatalystView /> : null}
      {p.slug === 'economics' ? <EconomicsView /> : null}
      {p.slug === 'purification' ? <PurificationView /> : null}
      {p.slug === 'end-use' ? <EndUseView /> : null}
      {p.slug === 'validation' ? <ValidationView /> : null}
      {p.slug === 'aspen-evidence' ? <AspenGallery /> : null}
    </>
  )
}
