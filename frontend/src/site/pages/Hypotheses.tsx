import { Navigate, useParams } from 'react-router-dom'
import { CatalystView } from '../hyp/CatalystView'
import { EconomicsView } from '../hyp/EconomicsView'
import { EndUseView } from '../hyp/EndUseView'
import { EvidenceMatrix } from '../hyp/EvidenceMatrix'
import { StoredNote, SubNav } from '../hyp/parts'
import { CarbonIntensityTable, CatalystPhase2, EconomicsPhase2, EndUsePhase2, PurificationPhase2, ValidationByKind } from '../hyp/phase2'
import { PlainAnswers } from '../hyp/PlainAnswers'
import { PurificationView } from '../hyp/PurificationView'
import { AspenGallery, ValidationView } from '../hyp/ValidationAspen'
import { OnThisPage } from '../OnThisPage'
import { HYPOTHESIS_PAGES } from '../routes'
import { PageHero, Section } from '../ui'

const LEAD: Record<string, string> = {
  '': 'Four hypotheses from the project essay, tested with Aspen Plus V15 runs and independent Python models for a Singapore setting (Jurong Island as a representative industrial site; no facility is claimed to exist). Each hypothesis starts with a plain answer and its limitations, then the claims inside it one by one; the formal classification under the rule fixed before the analysis is in the evidence matrix further down. Results that go against the essay are reported as such.',
  catalyst: 'Hypothesis H3: catalyst prices derived from metal content, kinetic validity, catalyst cost per kg of hydrogen, break-even prices, heat-exchanger sizing and the net benefit of heat integration.',
  economics: 'Hypothesis H2: the unified baseline, the dominance of the ammonia price, the break-even ammonia price and carbon pricing under the actual Singapore boundary and a hypothetical life-cycle price.',
  purification: 'Hypothesis H4: PSA against Pd-Ag membrane per specification, readiness levels, parity thresholds and the recovery lost for each purity step.',
  'end-use': 'Hypotheses H1 and H2: where cracking is justified against burning ammonia directly, the turbine-efficiency thresholds, and the carbon intensity of each ammonia route.',
  validation: 'The checks each area ran on its own results, kept apart by evidence kind, with every failure named. AmCraX has no independent experimental validation.',
  'aspen-evidence': 'The Aspen Plus V15 windows behind the stored Aspen results.',
}

/** Hypothesis whose plain answers head each topic page (the overview shows all four). */
export const PLAIN_IDS: Record<string, string[]> = { catalyst: ['H3'], economics: ['H2'], purification: ['H4'], 'end-use': ['H1'] }

/** Hypotheses section: evidence matrix at /hypotheses, sub-pages at /hypotheses/<slug>. Everything is read from stored result files. */
export default function Hypotheses() {
  const { page = '' } = useParams()
  const p = HYPOTHESIS_PAGES.find((x) => x.slug === page)
  if (!p) return <Navigate to="/hypotheses" replace />
  return (
    <>
      <PageHero title={p.slug ? p.title : 'Hypothesis testing'} lead={LEAD[p.slug]}>
        <SubNav current={p.slug} />
      </PageHero>
      <div className="wrap hyp-intro">
        <StoredNote extrapolated={p.slug === 'catalyst' || p.slug === ''} />
        <OnThisPage />
      </div>
      {p.slug === '' || PLAIN_IDS[p.slug] ? (
        <Section id="plain-answers" title={p.slug === '' ? 'Plain answers' : `Plain answers for ${PLAIN_IDS[p.slug].join(' and ')}`}>
          <PlainAnswers ids={p.slug === '' ? undefined : PLAIN_IDS[p.slug]} />
        </Section>
      ) : null}
      {p.slug === '' ? <Section id="matrix" title="Evidence matrix"><EvidenceMatrix /></Section> : null}
      {p.slug === 'catalyst' ? <><CatalystPhase2 /><CatalystView /></> : null}
      {p.slug === 'economics' ? <><EconomicsPhase2 /><EconomicsView /></> : null}
      {p.slug === 'purification' ? <><PurificationPhase2 /><PurificationView /></> : null}
      {p.slug === 'end-use' ? <><EndUsePhase2 /><Section id="carbon-intensity" title="Carbon intensity of hydrogen by ammonia route" alt><CarbonIntensityTable /></Section><EndUseView /></> : null}
      {p.slug === 'validation' ? <><ValidationByKind /><ValidationView /></> : null}
      {p.slug === 'aspen-evidence' ? <AspenGallery /> : null}
    </>
  )
}
