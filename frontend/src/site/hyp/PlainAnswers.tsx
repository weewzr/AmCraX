import { Link } from 'react-router-dom'
import { AsyncView } from '../../features/common/Notice'
import { useMatrix2, type Matrix } from './EvidenceMatrix'
import { VerdictChip } from './phase2'
import { list, show } from './shape'

type Obj = Record<string, unknown>
export interface PlainAnswer { claim?: unknown; answer?: unknown; qualifier?: unknown; limitation?: unknown; basis?: { rows?: unknown[]; half?: unknown; mode?: unknown }; formal_verdict?: unknown; note?: unknown; basis_outcome?: unknown }
export interface FigureCheck { figure?: unknown; result?: unknown; finding?: unknown; row?: unknown; row_verdict?: unknown }

/** The three plain answers the matrix may hold; anything else is shown as stored, never coloured as an answer. */
export const PLAIN = ['Yes', 'No', 'Not established'] as const
export function answerKind(a: unknown): 'yes' | 'no' | 'ne' | 'other' {
  const s = show(a)
  return s === 'Yes' ? 'yes' : s === 'No' ? 'no' : s === 'Not established' ? 'ne' : 'other'
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

/** Answer chip: prints its word (colour is not the only carrier). */
export function AnswerChip({ a }: { a: unknown }) {
  const k = answerKind(a)
  const icon = k === 'yes' ? '✓' : k === 'no' ? '✗' : '?'
  return <span className={`pill answer-chip answer-${k}`} data-answer={show(a)}><span aria-hidden="true">{icon}</span> {show(a) || 'no answer'}</span>
}

interface Hyp extends Obj { id?: string; statement?: string; primary_hypothesis?: unknown; verdict?: string; components?: { id?: string; verdict?: string }[]; plain_answers?: PlainAnswer[]; published_figures_checked?: FigureCheck[]; plain_answers_note?: unknown }

/** One hypothesis: its formal verdict and components first, then the plain answers with their limitations. */
export function PlainAnswersFor({ h }: { h: Hyp }) {
  const pa = Array.isArray(h.plain_answers) ? h.plain_answers : []
  const figs = Array.isArray(h.published_figures_checked) ? h.published_figures_checked : []
  const cs = Array.isArray(h.components) ? h.components : []
  if (!pa.length) return null
  return (
    <div className="plain-block" data-testid={`plain-answers-${show(h.id)}`}>
      <h3 className="plain-h">{show(h.id)}: {show(h.primary_hypothesis ?? h.statement)}</h3>
      <p className="small plain-formal">Formal verdict: <VerdictChip v={h.verdict} small />{cs.length ? <> Components:{' '}
        {cs.map((c, i) => <span key={`${show(c.id)}${i}`}>{i > 0 ? '; ' : ''}<strong>{show(c.id)}</strong> <VerdictChip v={c.verdict} small /></span>)}</> : null}
      </p>
      {/* own markup (not DTable): on a phone each row stacks into a labelled card instead of scrolling sideways */}
      <div className="plain-table" role="region" aria-label={`Plain answers for ${show(h.id)}`}>
        <table className="data simple">
          <caption>Plain answers for {show(h.id)} (reading aid; the formal verdict above is unchanged)</caption>
          <thead><tr>{['Claim', 'Answer', 'Qualifier', 'Limitation', 'Basis and formal verdict'].map((x) => <th key={x} scope="col">{x}</th>)}</tr></thead>
          <tbody>
            {pa.map((a, i) => (
              <tr key={`${show(a.claim)}${i}`}>
                <th scope="row" data-label="Claim">{show(a.claim)}</th>
                <td data-label="Answer"><AnswerChip a={a.answer} /></td>
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
          <ul className="hyp-list">{figs.map((x, i) => <li key={i}><span className="pill answer-chip answer-ne" data-figure={show(x.result)}>{show(x.result)}</span> {show(x.figure)}. {degC(show(x.finding))} <span className="muted">({show(x.row)} {show(x.row_verdict)})</span></li>)}</ul>
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
      const rule = show((d.provenance as Obj | undefined)?.plain_answers_rule)
      return (
        <div className="plain-answers" data-testid="plain-answers">
          <p className="prose-p" data-testid="plain-answers-lead">
            These yes or no answers are a reading aid derived in code from the formal rows of the evidence matrix; they are not verdicts and change none.
            An answer that rests on half of a row is a finding: that row's formal verdict stays INCONCLUSIVE because the row needs both halves.
            The formal verdict and its components are printed with each table, and the limitation of each answer follows it.
          </p>
          {rule ? <details className="hyp-details"><summary>How the plain answers are derived</summary><p className="small" style={{ padding: '0 16px' }}>{rule}</p></details> : null}
          {withPa.map((h) => <PlainAnswersFor key={String(h.id)} h={h} />)}
        </div>
      )
    }}</AsyncView>
  )
}
