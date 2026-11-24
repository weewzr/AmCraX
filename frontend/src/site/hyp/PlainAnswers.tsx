import { Link } from 'react-router-dom'
import { AsyncView } from '../../features/common/Notice'
import { useMatrix2, type Matrix } from './EvidenceMatrix'
import { list, show } from './shape'

type Obj = Record<string, unknown>
export interface PlainAnswer { claim?: unknown; answer?: unknown; qualifier?: unknown; limitation?: unknown; basis?: { rows?: unknown[]; half?: unknown; mode?: unknown }; formal_verdict?: unknown; note?: unknown; basis_outcome?: unknown; assumption?: unknown }
export interface FigureCheck { figure?: unknown; result?: unknown; finding?: unknown; row?: unknown; row_verdict?: unknown }

/** The stored value of the conditional answer and the short word its chip prints. */
export const CONDITIONAL_YES = 'Yes, under the stated assumption'
/** The four plain answers the matrix may hold; anything else is shown as stored, never coloured as an answer. */
export const PLAIN = ['Yes', CONDITIONAL_YES, 'No', 'Not established'] as const
export function answerKind(a: unknown): 'yes' | 'ya' | 'no' | 'ne' | 'other' {
  const s = show(a)
  return s === 'Yes' ? 'yes' : s === CONDITIONAL_YES ? 'ya' : s === 'No' ? 'no' : s === 'Not established' ? 'ne' : 'other'
}
/** The word a chip prints: "Yes (assumption)" for the conditional answer, the stored word otherwise. */
export function chipWord(a: unknown): string {
  const k = answerKind(a)
  return k === 'ya' ? 'Yes (assumption)' : show(a)
}
/** Kind of a headline answer sentence ("Yes, under ...: ...", "Yes: ...", "No ...", "Not established."). */
export function headlineKind(s: unknown): 'yes' | 'ya' | 'no' | 'ne' | 'other' {
  const t = show(s)
  if (/^Yes, under/.test(t)) return 'ya'
  if (/^Yes\b/.test(t)) return 'yes'
  if (/^No\b/.test(t)) return 'no'
  if (/^Not established/.test(t)) return 'ne'
  return 'other'
}

const HALF: Record<string, string> = { cracking_psa: 'cracking + PSA half', fired_cracking: 'fired-cracking half', energy: 'energy half', cost: 'cost half' }
const MODE: Record<string, string> = { actual_sg: 'actual Singapore boundary', hypothetical_lca: 'hypothetical price, not Singapore law' }

/** Basis of a plain answer as text: row ids, then the half or the carbon-pricing mode it rests on. */
export function basisText(b: PlainAnswer['basis']): string {
  if (!b) return ''
  const rows = list(b.rows).join(', ')
  const half = show(b.half), mode = show(b.mode)
  return rows + (half ? ` (${HALF[half] ?? half})` : '') + (mode ? ` (${MODE[mode] ?? mode})` : '')
}

/** The matrix writes temperatures as "degC"; the page prints the degree sign. */
export const degC = (s: string): string => s.replace(/\s?degC\b/g, ' °C')

/** The sentence that explains the two layers (shown once, near the top of the hypotheses overview). */
export const TWO_LAYERS = 'Plain answers state what the model computes and under which assumptions; the formal classification applies a stricter rule fixed before the analysis, under which a result that rests on an untested assumption is not counted as supported; both are published.'

/** Answer chip: prints its word (colour is not the only carrier). The conditional answer prints "Yes (assumption)". */
export function AnswerChip({ a, kind }: { a: unknown; kind?: ReturnType<typeof answerKind> }) {
  const k = kind ?? answerKind(a)
  const icon = k === 'yes' ? '✓' : k === 'ya' ? '✓*' : k === 'no' ? '✗' : '?'
  const word = kind ? ({ yes: 'Yes', ya: 'Yes (assumption)', no: 'No', ne: 'Not established', other: show(a) } as const)[k] : chipWord(a)
  return <span className={`pill answer-chip answer-${k}`} data-answer={show(a)}><span aria-hidden="true">{icon}</span> {word || 'no answer'}</span>
}

interface Hyp extends Obj { id?: string; statement?: string; primary_hypothesis?: unknown; plain_answers?: PlainAnswer[]; published_figures_checked?: FigureCheck[]; headline_answer?: unknown; headline_limitations?: unknown[] }

/** Headline answer of a hypothesis, then its limitations, always visible (no click). Formal classification is not shown here. */
export function Headline({ h, compact = false }: { h: Hyp; compact?: boolean }) {
  const head = show(h.headline_answer)
  const lims = list(h.headline_limitations)
  if (!head) return null
  const k = headlineKind(head)
  return (
    <div className={`plain-headline headline-${k}`} data-testid={`headline-${show(h.id)}`}>
      <p className="plain-headline-answer"><AnswerChip a={head} kind={k} /> <strong data-testid={`headline-answer-${show(h.id)}`}>{head}</strong></p>
      {lims.length ? (
        <div className="plain-limits" data-testid={`headline-limitations-${show(h.id)}`}>
          <p className="small plain-limits-h"><strong>Limitations</strong></p>
          <ul className={`hyp-list${compact ? ' small' : ''}`}>{lims.map((x, i) => <li key={i}>{degC(x)}</li>)}</ul>
        </div>
      ) : null}
    </div>
  )
}

/** One hypothesis: (a) the headline answer, (b) its limitations, (c) the claim table. */
export function PlainAnswersFor({ h }: { h: Hyp }) {
  const pa = Array.isArray(h.plain_answers) ? h.plain_answers : []
  const figs = Array.isArray(h.published_figures_checked) ? h.published_figures_checked : []
  if (!pa.length) return null
  return (
    <div className="plain-block" data-testid={`plain-answers-${show(h.id)}`}>
      <h3 className="plain-h">{show(h.id)}: {show(h.primary_hypothesis ?? h.statement)}</h3>
      <Headline h={h} />
      {/* own markup (not DTable): on a phone each row stacks into a labelled card instead of scrolling sideways */}
      <div className="plain-table" role="region" aria-label={`Claims of ${show(h.id)}`}>
        <table className="data simple">
          <caption>Claims of {show(h.id)}, answered one by one (reading aid)</caption>
          <thead><tr>{['Claim', 'Answer', 'Qualifier', 'Limitation', 'Basis (formal classification, rule fixed before the analysis)'].map((x) => <th key={x} scope="col">{x}</th>)}</tr></thead>
          <tbody>
            {pa.map((a, i) => (
              <tr key={`${show(a.claim)}${i}`} data-answer-kind={answerKind(a.answer)}>
                <th scope="row" data-label="Claim">{show(a.claim)}</th>
                <td data-label="Answer"><AnswerChip a={a.answer} />{answerKind(a.answer) === 'ya' && show(a.assumption) ? <div className="small answer-assumption" data-testid="answer-assumption">Assumption: {show(a.assumption)}</div> : null}</td>
                <td data-label="Qualifier">{show(a.qualifier) || <span className="muted">none</span>}</td>
                <td data-label="Limitation" className="wide"><span className="small">{degC(show(a.limitation))}{show(a.note) ? <> <em>{show(a.note)}</em></> : null}</span></td>
                <td data-label="Basis"><span className="small"><Link to={{ pathname: '/hypotheses', hash: `#row-${list(a.basis?.rows)[0] ?? ''}` }}>{basisText(a.basis)}</Link><span className="muted">: {show(a.formal_verdict)}</span></span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {figs.length ? (
        <div className="small plain-figs" data-testid={`figures-checked-${show(h.id)}`}>
          <strong>Published figures checked</strong> (secondary rows; they do not vote):
          <ul className="hyp-list">{figs.map((x, i) => <li key={i}><span className="pill answer-chip answer-ne" data-figure={show(x.result)}>{show(x.result)}</span> {show(x.figure)}. {degC(show(x.finding))} <span className="muted">({show(x.row)})</span></li>)}</ul>
        </div>
      ) : null}
    </div>
  )
}

/** "Plain answers" block read from the evidence matrix. `ids` limits it to some hypotheses (topic pages). */
export function PlainAnswers({ ids }: { ids?: string[] }) {
  const m = useMatrix2()
  return (
    <AsyncView a={m} what="The plain answers (results/research/evidence_matrix.json)">{(d: Matrix) => {
      const hs = (Array.isArray(d.hypotheses) ? d.hypotheses : []).filter((h) => !ids || ids.includes(String(h.id))) as Hyp[]
      const withPa = hs.filter((h) => Array.isArray(h.plain_answers) && h.plain_answers.length)
      if (!withPa.length) return <p className="prose-p muted">The evidence matrix file holds no plain answers.</p>
      const prov = d.provenance as Obj | undefined
      const rule = show(prov?.plain_answers_rule), hrule = show(prov?.headline_rule).replace(/\s*Plain answers state what.*$/, '')
      return (
        <div className="plain-answers" data-testid="plain-answers">
          {!ids ? <p className="prose-p" data-testid="two-layers">{TWO_LAYERS}</p> : null}
          <p className="prose-p" data-testid="plain-answers-lead">
            Each hypothesis starts with its headline answer and the limitations that go with it, then the claims inside it answered one by one.
            {ids ? <> The formal classification under the rule fixed before the analysis is in the <Link to={{ pathname: '/hypotheses', hash: '#matrix' }}>evidence matrix</Link>.</> : <> The formal classification under the rule fixed before the analysis is in the evidence matrix below.</>}
          </p>
          {rule || hrule ? <details className="hyp-details"><summary>How the headline and plain answers are derived</summary><p className="small" style={{ padding: '0 16px' }}>{hrule}</p><p className="small" style={{ padding: '0 16px' }}>{rule}</p></details> : null}
          {withPa.map((h) => <PlainAnswersFor key={String(h.id)} h={h} />)}
        </div>
      )
    }}</AsyncView>
  )
}
