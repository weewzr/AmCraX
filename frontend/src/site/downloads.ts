import { withBase } from '../api/url'

/**
 * Files copied into public/downloads/ by scripts/prepare_site.mjs (keep the two lists identical).
 * `key` is the key used by /api/reports, so the dashboard's Reports page can map its entries to these copies.
 * prepare_site.mjs writes public/downloads/index.json with the files it really copied; the Docs page shows only those,
 * so an entry whose source does not exist at build time is skipped cleanly. PDFs of docs/paper/build/ are listed there as kind "paper".
 */
export type DownloadKind = 'report' | 'paper' | 'deck' | 'validation' | 'research'
export interface DownloadFile { key: string; file: string; title: string; kind: DownloadKind; blurb: string; source: string }

export const DOWNLOADS: DownloadFile[] = [
  { key: 'technical_report_pdf', file: 'AmCraX_Technical_Report.pdf', title: 'Technical report (PDF)', kind: 'report', blurb: 'The current technical report with equations, figures, the Aspen Plus screenshots and APA references.', source: 'docs/technical_report/AmCraX_Technical_Report.pdf' },
  { key: 'technical_report_2026_11_23_pdf', file: 'AmCraX_Technical_Report_2026-11-23.pdf', title: 'Technical report, 23 November 2026 release (PDF)', kind: 'report', blurb: 'The preserved Phase 1 research-expansion release of the report, unchanged. Later Phase 2 results are not in it.', source: 'docs/technical_report/releases/2026-11-23/AmCraX_Technical_Report_2026-11-23.pdf' },
  { key: 'technical_report_docx', file: 'AmCraX_Technical_Report.docx', title: 'Technical report (Word)', kind: 'report', blurb: 'Editable version of the current report.', source: 'docs/technical_report/AmCraX_Technical_Report.docx' },
  { key: 'paper_pdf', file: 'AmCraX_Paper.pdf', title: 'Research paper (PDF)', kind: 'paper', blurb: 'Concise research paper on the Phase 2 results: methods, the four hypotheses, thresholds, limitations.', source: 'docs/paper/build/AmCraX_Paper.pdf' },
  { key: 'executive_summary_pdf', file: 'AmCraX_Executive_Summary.pdf', title: 'Executive summary (PDF)', kind: 'paper', blurb: 'Two-page summary of the Phase 2 results and verdicts.', source: 'docs/paper/build/AmCraX_Executive_Summary.pdf' },
  { key: 'pitch_deck_pdf', file: 'AmCraX_Pitch_Deck.pdf', title: 'Pitch deck (PDF)', kind: 'deck', blurb: 'Slides with a provenance tag on every number and a "what AmCraX does not claim" strip.', source: 'docs/pitch_deck/AmCraX_Pitch_Deck.pdf' },
  { key: 'pitch_deck_pptx', file: 'AmCraX_Pitch_Deck.pptx', title: 'Pitch deck (PowerPoint)', kind: 'deck', blurb: 'Editable slides with speaker notes.', source: 'docs/pitch_deck/AmCraX_Pitch_Deck.pptx' },
  { key: 'speaker_script', file: 'speaker_script.md', title: 'Pitch deck speaker script', kind: 'deck', blurb: 'The spoken text for each slide.', source: 'docs/pitch_deck/speaker_script.md' },
  { key: 'validation_matrix', file: 'validation_matrix.md', title: 'Validation matrix', kind: 'validation', blurb: 'Every check with method, reference, tolerance, result and limitation.', source: 'docs/validation/validation_matrix.md' },
  { key: 'discrepancy_analysis', file: 'discrepancy_analysis.md', title: 'Discrepancy analysis', kind: 'validation', blurb: 'Why Aspen Plus and the independent Python models differ where they do.', source: 'docs/validation/discrepancy_analysis.md' },
  { key: 'verdict_methodology_v2', file: 'verdict_methodology_v2.md', title: 'Verdict methodology, version 2', kind: 'research', blurb: 'The rule that turns row evidence into component and hypothesis verdicts. The roles, components and aggregation rule were fixed before the Phase 2 analyses; the row-by-row rules were written afterwards.', source: 'docs/research/verdict_methodology_v2.md' },
  { key: 'unified_baseline', file: 'unified_baseline.md', title: 'Unified baseline note', kind: 'research', blurb: 'The single techno-economic reference scenario and why the two earlier baselines are superseded for research outputs.', source: 'docs/research/unified_baseline.md' },
  { key: 'uncertainty_quantification', file: 'uncertainty_quantification.md', title: 'Uncertainty quantification note', kind: 'research', blurb: 'Global sensitivity (Sobol indices) and kinetic parameter propagation. Numerical verification, not experimental validation.', source: 'docs/research/uncertainty_quantification.md' },
  { key: 'methodology_transfer_matrix', file: 'methodology_transfer_matrix.md', title: 'Methodology transfer matrix', kind: 'research', blurb: 'Published methods from the nuclear-engineering literature and how each was applied here.', source: 'docs/research/methodology_transfer_matrix.md' },
  { key: 'findings_that_changed', file: 'phase2_findings_changed.md', title: 'Findings that changed', kind: 'research', blurb: 'Every headline finding of the 23 November 2026 release set against its Phase 2 value, with the reason.', source: 'docs/research/phase2_findings_changed.md' },
  { key: 'limitations_and_future_work', file: 'limitations_and_future_work.md', title: 'Limitations and future work', kind: 'research', blurb: 'Open items: missing sources, unvalidated models and what would close them.', source: 'docs/research/limitations_and_future_work.md' },
]

/** URL of a copied file under the active base ("/AmCraX/downloads/..." on GitHub Pages). */
export const downloadUrl = (file: string): string => withBase(`/downloads/${file}`)

export const downloadByKey = (key: string): DownloadFile | undefined => DOWNLOADS.find((d) => d.key === key)
export const downloadByFile = (file: string): DownloadFile | undefined => DOWNLOADS.find((d) => d.file === file)

export const REPORT_PDF = DOWNLOADS[0]

/** One entry of public/downloads/index.json (written by prepare_site.mjs). */
export interface CopiedFile { file: string; source?: string; bytes?: number; kind?: string }

/**
 * The downloads to show: fixed entries whose file was copied, then paper PDFs found by pattern.
 * `copied === null` (index not readable) keeps the fixed list unchanged, as before the index existed.
 */
export function availableDownloads(copied: CopiedFile[] | null): (DownloadFile & { bytes?: number })[] {
  if (copied === null) return DOWNLOADS
  const by = new Map(copied.map((c) => [c.file, c]))
  const fixed = DOWNLOADS.filter((d) => by.has(d.file)).map((d) => ({ ...d, bytes: by.get(d.file)?.bytes }))
  const papers = copied.filter((c) => c.kind === 'paper' && !DOWNLOADS.some((d) => d.file === c.file))
    .map((c) => ({ key: `paper_${c.file}`, file: c.file, title: `Short paper (${c.file})`, kind: 'paper' as const, blurb: 'Short paper on the Phase 2 results, built from docs/paper.', source: c.source ?? `docs/paper/build/${c.file}`, bytes: c.bytes }))
  return [...fixed, ...papers]
}
