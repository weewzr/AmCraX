import { useEffect, useMemo, useState } from 'react'
import { GITHUB_DOCS_URL, GITHUB_URL, withBase } from '../../api/url'
import { type ReportItem } from '../../api/reports'
import { fmtBytes, REPRODUCE_STEPS } from '../../features/reports/shape'
import { useJson } from '../data'
import { availableDownloads, downloadUrl, type CopiedFile } from '../downloads'
import { ExtLink, PageHero, Section } from '../ui'

const KIND: Record<string, string> = { report: 'Technical report', paper: 'Paper and summary', deck: 'Pitch deck', validation: 'Validation', research: 'Research note' }
const EXT = (f: string) => f.split('.').pop()?.toUpperCase() ?? ''

const REPO_DOCS: { file: string; title: string; text: string }[] = [
  { file: 'docs/user_guide.md', title: 'User guide', text: 'How to use each dashboard page.' },
  { file: 'docs/installation.md', title: 'Installation', text: 'Set-up on a new machine, with and without Aspen Plus.' },
  { file: 'docs/developer_guide.md', title: 'Developer guide', text: 'Code layout, the Aspen COM driver, tests, adding a model.' },
  { file: 'docs/api.md', title: 'API reference', text: 'Every endpoint of the FastAPI back end.' },
  { file: 'docs/model_assumptions.md', title: 'Model assumptions', text: 'Each assumption with its origin and effect.' },
  { file: 'docs/known_limitations.md', title: 'Known limitations', text: 'What the models cannot do.' },
  { file: 'docs/dependencies.md', title: 'Dependencies', text: 'Software, data and licences used.' },
  { file: 'docs/HANDOVER.md', title: 'Handover', text: 'State of the project, rules learnt, next steps.' },
  { file: 'docs/research/verdict_methodology_v2.md', title: 'Verdict methodology v2', text: 'How row evidence becomes a component and hypothesis verdict.' },
  { file: 'docs/research/unified_baseline.md', title: 'Unified baseline', text: 'The one techno-economic reference scenario of Phase 2.' },
  { file: 'docs/research/uncertainty_quantification.md', title: 'Uncertainty quantification', text: 'Sobol indices and kinetic parameter propagation.' },
  { file: 'docs/research/methodology_transfer_matrix.md', title: 'Methodology transfer matrix', text: 'Published nuclear-engineering methods applied to this plant.' },
]

/** public/downloads/index.json: the files prepare_site.mjs really copied (null while loading or when the index is missing). */
function useCopied(): CopiedFile[] | null {
  const [files, setFiles] = useState<CopiedFile[] | null>(null)
  useEffect(() => {
    let live = true
    fetch(withBase('/downloads/index.json')).then((r) => (r.ok ? r.json() : null)).then((j) => { if (live && j && Array.isArray(j.files)) setFiles(j.files as CopiedFile[]) }).catch(() => undefined)
    return () => { live = false }
  }, [])
  return files
}

export default function Docs() {
  const reports = useJson<{ reports: ReportItem[] }>('/api/reports')
  const bytes = useMemo(() => new Map((reports.phase === 'ready' ? reports.data.reports : []).map((r) => [r.key, r.bytes])), [reports])
  const copied = useCopied()
  const shown = availableDownloads(copied)
  return (
    <>
      <PageHero eyebrow="Section 8 - Documentation and downloads" title="Read, download, reproduce"
        lead="The technical report, the short paper, the executive summary and the pitch deck are generated from the same stored results as this site. The repository holds the rest of the documentation." />
      <Section id="downloads" title="Downloads" intro="Files are copied into the site at build time from the repository, so they are the versions that were committed with the results shown here. A document that did not exist at build time is not listed. The 23 November 2026 release of the report is preserved unchanged; the current report carries the Phase 2 results.">
        <ul className="dl-grid">
          {shown.map((d) => (
            <li key={d.key}>
              <a className="card dl-card" href={downloadUrl(d.file)} download={d.file}>
                <span className="dl-kind">{KIND[d.kind]} <span className="dl-ext">{EXT(d.file)}</span></span>
                <strong>{d.title}</strong>
                <span className="muted">{d.blurb}</span>
                <span className="dl-size muted">{d.file}{(bytes.get(d.key) ?? ('bytes' in d ? d.bytes : undefined)) ? `, ${fmtBytes(bytes.get(d.key) ?? ('bytes' in d ? d.bytes : undefined))}` : ''}</span>
              </a>
            </li>
          ))}
        </ul>
      </Section>
      <Section id="repo" alt title="Documentation in the repository" intro={<>All documents are in <ExtLink href={GITHUB_DOCS_URL}>the docs folder on GitHub</ExtLink>; the <ExtLink href={`${GITHUB_URL}#readme`}>README</ExtLink> has the overview and the repository layout.</>}>
        <ul className="card-grid">
          {REPO_DOCS.map((d) => (
            <li key={d.file}>
              <ExtLink href={`${GITHUB_URL}/blob/main/${d.file}`} className="card link-card"><h3>{d.title}</h3><p>{d.text}</p><span className="link-card-go" aria-hidden="true">Open on GitHub</span></ExtLink>
            </li>
          ))}
        </ul>
      </Section>
      <Section id="reproduce" title="Reproduce it" intro="Everything except the Aspen Plus runs can be regenerated from the repository on a machine without Aspen.">
        <ol className="steps">
          {REPRODUCE_STEPS.map((s) => <li key={s.title}><strong>{s.title}.</strong> <code className="cmd">{s.cmd}</code><div className="muted">{s.note}</div></li>)}
        </ol>
      </Section>
    </>
  )
}
