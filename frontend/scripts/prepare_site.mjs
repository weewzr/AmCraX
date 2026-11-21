// Copy the downloadable deliverables from the repository into frontend/public/downloads/ so that Vite ships them with the static site.
//
//   node scripts/prepare_site.mjs          (also run by `npm run prebuild:pages` and `npm run predev`)
//
// Missing sources are skipped with a message (never an error), so a checkout without the generated PDFs still builds.
// Keep the file list identical to src/site/downloads.ts. Portable: path.join only, no shell, works on Linux in GitHub Actions.
import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(here, '..')
const repo = path.resolve(frontend, '..')
const outDir = path.join(frontend, 'public', 'downloads')

export const FILES = [
  ['docs', 'technical_report', 'AmCraX_Technical_Report.pdf'],
  ['docs', 'technical_report', 'AmCraX_Technical_Report.docx'],
  ['docs', 'pitch_deck', 'AmCraX_Pitch_Deck.pdf'],
  ['docs', 'pitch_deck', 'AmCraX_Pitch_Deck.pptx'],
  ['docs', 'pitch_deck', 'speaker_script.md'],
  ['docs', 'validation', 'validation_matrix.md'],
  ['docs', 'validation', 'discrepancy_analysis.md'],
]

export function prepareSite() {
  mkdirSync(outDir, { recursive: true })
  let copied = 0
  for (const parts of FILES) {
    const src = path.join(repo, ...parts)
    const dst = path.join(outDir, parts[parts.length - 1])
    if (!existsSync(src)) { console.log(`prepare_site: skipped (not found) ${parts.join('/')}`); continue }
    copyFileSync(src, dst)
    copied++
    console.log(`prepare_site: ${parts.join('/')} -> public/downloads/${parts[parts.length - 1]} (${(statSync(dst).size / 1024).toFixed(0)} kB)`)
  }
  console.log(`prepare_site: ${copied} of ${FILES.length} files copied`)
  return copied
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) prepareSite()
