import { withBase } from '../api/url'

/**
 * Files copied into public/downloads/ by scripts/prepare_site.mjs (keep the two lists identical).
 * `key` is the key used by /api/reports, so the dashboard's Reports page can map its entries to these copies.
 */
export interface DownloadFile { key: string; file: string; title: string; kind: 'report' | 'deck' | 'validation'; blurb: string; source: string }

export const DOWNLOADS: DownloadFile[] = [
  { key: 'technical_report_pdf', file: 'AmCraX_Technical_Report.pdf', title: 'Technical report (PDF)', kind: 'report', blurb: '21 sections with equations, 43 figures (including the 16 Aspen Plus screenshots) and APA references.', source: 'docs/technical_report/AmCraX_Technical_Report.pdf' },
  { key: 'technical_report_2026_11_23_pdf', file: 'AmCraX_Technical_Report_2026-11-23.pdf', title: 'Technical report, 23 November 2026 release (PDF)', kind: 'report', blurb: 'The preserved Phase 1 research-expansion release of the report, unchanged. Later Phase 2 results are not in it.', source: 'docs/technical_report/releases/2026-11-23/AmCraX_Technical_Report_2026-11-23.pdf' },
  { key: 'technical_report_docx', file: 'AmCraX_Technical_Report.docx', title: 'Technical report (Word)', kind: 'report', blurb: 'Editable version of the same report.', source: 'docs/technical_report/AmCraX_Technical_Report.docx' },
  { key: 'pitch_deck_pdf', file: 'AmCraX_Pitch_Deck.pdf', title: 'Pitch deck (PDF)', kind: 'deck', blurb: '15 slides with a provenance tag on every number and a "what AmCraX does not claim" strip.', source: 'docs/pitch_deck/AmCraX_Pitch_Deck.pdf' },
  { key: 'pitch_deck_pptx', file: 'AmCraX_Pitch_Deck.pptx', title: 'Pitch deck (PowerPoint)', kind: 'deck', blurb: 'Editable slides with speaker notes.', source: 'docs/pitch_deck/AmCraX_Pitch_Deck.pptx' },
  { key: 'speaker_script', file: 'speaker_script.md', title: 'Pitch deck speaker script', kind: 'deck', blurb: 'The spoken text for each slide.', source: 'docs/pitch_deck/speaker_script.md' },
  { key: 'validation_matrix', file: 'validation_matrix.md', title: 'Validation matrix', kind: 'validation', blurb: 'Every check with method, reference, tolerance, result and limitation.', source: 'docs/validation/validation_matrix.md' },
  { key: 'discrepancy_analysis', file: 'discrepancy_analysis.md', title: 'Discrepancy analysis', kind: 'validation', blurb: 'Why Aspen Plus and the independent Python models differ where they do.', source: 'docs/validation/discrepancy_analysis.md' },
]

/** URL of a copied file under the active base ("/AmCraX/downloads/..." on GitHub Pages). */
export const downloadUrl = (file: string): string => withBase(`/downloads/${file}`)

export const downloadByKey = (key: string): DownloadFile | undefined => DOWNLOADS.find((d) => d.key === key)
export const downloadByFile = (file: string): DownloadFile | undefined => DOWNLOADS.find((d) => d.file === file)

export const REPORT_PDF = DOWNLOADS[0]
