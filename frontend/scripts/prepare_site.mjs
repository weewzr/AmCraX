// Copy the downloadable deliverables from the repository into frontend/public/downloads/ so that Vite ships them with the static site.
//
//   node scripts/prepare_site.mjs          (also run by `npm run prebuild:pages` and `npm run predev`)
//
// Missing sources are skipped with a message (never an error), so a checkout without the generated PDFs still builds.
// Every copied file is listed in public/downloads/index.json; the Docs page shows only the files listed there, so a
// missing file is skipped cleanly on the site as well. Keep the fixed file list identical to src/site/downloads.ts.
// PDFs in docs/paper/build/ are copied by pattern (their names are set by the paper build) and listed as kind "paper".
// Portable: path.join only, no shell, works on Linux in GitHub Actions.
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(here, '..')
const repo = path.resolve(frontend, '..')
const outDir = path.join(frontend, 'public', 'downloads')

export const FILES = [
  ['docs', 'technical_report', 'AmCraX_Technical_Report.pdf'],
  ['docs', 'technical_report', 'releases', '2026-11-23', 'AmCraX_Technical_Report_2026-11-23.pdf'],
  ['docs', 'technical_report', 'AmCraX_Technical_Report.docx'],
  ['docs', 'pitch_deck', 'AmCraX_Pitch_Deck.pdf'],
  ['docs', 'pitch_deck', 'AmCraX_Pitch_Deck.pptx'],
  ['docs', 'pitch_deck', 'speaker_script.md'],
  ['docs', 'validation', 'validation_matrix.md'],
  ['docs', 'validation', 'discrepancy_analysis.md'],
  ['docs', 'research', 'verdict_methodology_v2.md'],
  ['docs', 'research', 'unified_baseline.md'],
  ['docs', 'research', 'uncertainty_quantification.md'],
  ['docs', 'research', 'methodology_transfer_matrix.md'],
  ['docs', 'research', 'phase2_findings_changed.md'],
  ['docs', 'research', 'limitations_and_future_work.md'],
]

/** Directory whose PDFs are copied by pattern (short paper). */
export const PAPER_DIR = ['docs', 'paper', 'build']

export function prepareSite() {
  mkdirSync(outDir, { recursive: true })
  const listed = []
  const take = (parts, kind) => {
    const src = path.join(repo, ...parts)
    const name = parts[parts.length - 1]
    if (!existsSync(src)) { console.log(`prepare_site: skipped (not found) ${parts.join('/')}`); return }
    const dst = path.join(outDir, name)
    copyFileSync(src, dst)
    const bytes = statSync(dst).size
    listed.push({ file: name, source: parts.join('/'), bytes, ...(kind ? { kind } : {}) })
    console.log(`prepare_site: ${parts.join('/')} -> public/downloads/${name} (${(bytes / 1024).toFixed(0)} kB)`)
  }
  for (const parts of FILES) take(parts)
  const paperDir = path.join(repo, ...PAPER_DIR)
  if (existsSync(paperDir)) {
    for (const f of readdirSync(paperDir).filter((x) => x.toLowerCase().endsWith('.pdf')).sort()) take([...PAPER_DIR, f], 'paper')
  } else console.log(`prepare_site: skipped (not found) ${PAPER_DIR.join('/')}/*.pdf`)
  writeFileSync(path.join(outDir, 'index.json'), JSON.stringify({ note: 'Files copied by scripts/prepare_site.mjs; missing sources are not listed.', files: listed }, null, 1))
  console.log(`prepare_site: ${listed.length} files copied (${FILES.length} fixed entries + paper PDFs)`)
  return listed.length
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) prepareSite()
