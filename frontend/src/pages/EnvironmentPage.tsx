import { useEffect, useMemo, useState } from 'react'
import '../features/common/features.css'
import { fetchAllScenarios, fetchStoredEnv, HEATING, HEATING_LABEL, ROUTES, type CiFactor, type CiOverrides, type CiResult } from '../api/environment'
import { DataTable, type Column } from '../components/DataTable'
import { SourceBadge, StatusPill, Value } from '../components/ui'
import { useData } from '../data/DataContext'
import { AsyncView, ModeGate, Notice } from '../features/common/Notice'
import { mapAsync, useAsync } from '../features/common/useAsync'
import { BarsChart, ChartFrame, SERIES_COLORS } from '../features/economics/charts'
import { breakdownMismatch, breakdownRowsCi, CI_PARTS, groupedByRoute, needsVerification, uniqueFactors } from '../features/environment/shape'

// Citekeys whose primary document was not opened according to the "checked" text in backend/amcrax/data/environmental.yaml.
const FLAGGED_CITES = ['ema2025ses', 'glec2023v3', 'eu2023_1185']

export default function EnvironmentPage() {
  const { mode, phase, active } = useData()
  const live = mode === 'LIVE' && phase === 'ready' && !!active
  const readable = (mode === 'LIVE' || mode === 'SNAPSHOT') && phase === 'ready' && !!active
  const caseId = active?.case_id ?? ''
  const [dist, setDist] = useState('')
  const [grid, setGrid] = useState('')
  const [q, setQ] = useState<CiOverrides>({})
  useEffect(() => {
    const t = setTimeout(() => {
      const o: CiOverrides = {}
      const d = Number(dist), g = Number(grid)
      if (dist.trim() !== '' && Number.isFinite(d) && d >= 0) o.distance_km = d
      if (grid.trim() !== '' && Number.isFinite(g) && g >= 0) o.grid_ef_kg_per_kWh = g
      setQ(o)
    }, 450)
    return () => clearTimeout(t)
  }, [dist, grid])
  const all = useAsync((s) => fetchAllScenarios(caseId, q, s), [caseId, q], live)
  const stored = useAsync((s) => fetchStoredEnv(caseId, s), [caseId], readable)
  const view = mode === 'SNAPSHOT' ? mapAsync(stored, (d) => ROUTES.flatMap((r) => HEATING.map((h) => d.scenarios?.[`${r}/${h}`]).filter((x): x is CiResult => !!x))) : all
  const overridden = Object.keys(q).length > 0
  return (
    <section className="page">
      <h1>Environment</h1>
      <Notice kind="warn" title="Simplified carbon-intensity accounting - not a life-cycle assessment.">Activity data (from the stored Aspen result) multiplied by literature emission factors, for hydrogen at the cracker/PSA outlet. Results are kg CO2e per kg H2.</Notice>
      <ModeGate what="Re-calculating carbon intensity with overridden emission factors" />
      <div className="card controls" role="group" aria-label="Emission-factor overrides">
        <label className="field">Shipping distance [km]<input type="number" min={0} max={30000} step={500} placeholder="default" value={dist} disabled={!live} onChange={(e) => setDist(e.target.value)} /></label>
        <label className="field">Grid factor [kg CO2e/kWh]<input type="number" min={0} max={2} step={0.01} placeholder="default" value={grid} disabled={!live} onChange={(e) => setGrid(e.target.value)} /></label>
        <button type="button" className="btn" disabled={!live || (!dist && !grid)} onClick={() => { setDist(''); setGrid('') }}>Clear overrides</button>
        <span className="muted">Case <code>{caseId || 'n/a'}</code> {active ? <SourceBadge source={active.source} /> : null}; blank = data-file default. {live ? 'Changes re-query POST /api/environment/carbon-intensity (9 scenarios).' : 'Stored analysis of the 9 scenarios (overrides need the live API).'}</span>
      </div>
      {overridden ? <Notice kind="warn" title="Overrides active.">Overridden factors are recorded as <SourceBadge source="assumption" /> in the factor table.</Notice> : null}
      <AsyncView a={view} what="Carbon intensity">{(rs) => <Body rs={rs} refs={stored.data?.comparison.reference_lines ?? []} />}</AsyncView>
    </section>
  )
}

function Body({ rs, refs }: { rs: CiResult[]; refs: { label: string; value_kgCO2e_per_kgH2: number; source: string; note?: string }[] }) {
  const first = rs[0]
  const src = first?.source ?? 'python_model'
  const grouped = useMemo(() => groupedByRoute(rs), [rs])
  const stack = useMemo(() => breakdownRowsCi(rs, (h) => HEATING_LABEL[h] ?? h), [rs])
  const factors = useMemo(() => uniqueFactors(rs), [rs])
  const mism = breakdownMismatch(rs)
  const fCols: Column<CiFactor>[] = [
    { key: 'name', label: 'Factor' },
    { key: 'value', label: 'Value', align: 'right', render: (f) => <Value v={f.value} unit={f.unit} digits={4} source={null} showSource={false} />, csv: (f) => `${f.value} ${f.unit}` },
    { key: 'provenance', label: 'Provenance', render: (f) => <SourceBadge source={f.provenance === 'literature' ? 'literature' : 'assumption'} />, csv: (f) => f.provenance },
    { key: 'source', label: 'Source', render: (f) => <span className="wrap-cell">{f.source}</span> },
    { key: 'verify', label: 'Status', render: (f) => needsVerification(f, FLAGGED_CITES) ? <StatusPill kind="warn">to be verified against primary source</StatusPill> : <StatusPill kind="ok">as recorded</StatusPill>, csv: (f) => (needsVerification(f, FLAGGED_CITES) ? 'to be verified' : 'recorded') },
    { key: 'note', label: 'Note', render: (f) => <span className="wrap-cell muted">{f.note ?? ''}</span> },
  ]
  const sRows = rs.map((r) => ({ scenario: r.scenario, total: r.total_kgCO2e_per_kgH2, ...r.breakdown_kgCO2e_per_kgH2 }))
  return (
    <>
      {mism > 1e-6 ? <Notice kind="error" title="Internal check failed.">Breakdown parts do not sum to the total (max mismatch {mism}).</Notice> : null}
      <div className="grid-2">
        <ChartFrame title="Carbon intensity by ammonia route and heating option" sources={[src]} height={340}
          description="Grouped bars of kg CO2e per kg H2 for green, blue and grey ammonia, one bar per heating option, with regulatory reference lines."
          note="Dashed lines are regulatory or policy yardsticks quoted for orientation, not AmCraX results; their system boundaries differ from this simplified accounting.">
          <BarsChart data={grouped} xKey="route" xLabel="Ammonia production route" yLabel="kg CO2e / kg H2"
            series={HEATING.map((h, i) => ({ key: h, label: HEATING_LABEL[h], color: SERIES_COLORS[i] }))}
            refs={refs.map((r) => ({ y: r.value_kgCO2e_per_kgH2, label: `reference: ${r.label}` }))} />
        </ChartFrame>
        <ChartFrame title="Breakdown by contribution" sources={[src]} height={340}
          description="Stacked bars per route and heating option of upstream ammonia, transport, electricity and external heat contributions in kg CO2e per kg H2.">
          <BarsChart data={stack} xKey="name" stacked xLabel="Route / heating" yLabel="kg CO2e / kg H2"
            series={CI_PARTS.map(([key, label], i) => ({ key, label, color: SERIES_COLORS[i] }))} />
        </ChartFrame>
      </div>
      <div className="grid-2">
        <DataTable columns={[
          { key: 'scenario', label: 'Scenario' },
          { key: 'total', label: 'Total', unit: 'kg CO2e/kg H2', align: 'right', render: (x) => <Value v={x.total} digits={2} source={src} showSource={false} /> },
          ...CI_PARTS.map(([k, l]): Column<Record<string, number | string | null>> => ({ key: k, label: l, align: 'right', render: (x) => <Value v={(x[k] as number | null) ?? null} digits={3} source={src} showSource={false} /> })),
        ] as Column<(typeof sRows)[number]>[]} rows={sRows} caption="Carbon intensity of the nine scenarios" filename="carbon_intensity.csv" />
        <div className="card">
          <h2>System boundary and references</h2>
          <p><strong>Boundary.</strong> {first?.system_boundary}</p>
          <p className="muted">Method: {first?.method} Grid: <code>{first?.grid}</code>; shipping distance <Value v={first?.transport_distance_km ?? null} unit="km" digits={0} source="assumption" />.</p>
          {refs.length ? <ul>{refs.map((r) => <li key={r.label}><strong>{r.label}:</strong> <Value v={r.value_kgCO2e_per_kgH2} unit="kg CO2e/kg H2" digits={2} source="literature" /> <span className="muted">reference line - {r.source}. {r.note}</span></li>)}</ul> : <p className="muted">Reference lines not available (stored analysis file missing).</p>}
        </div>
      </div>
      <div className="card">
        <h2>Emission factors used</h2>
        <p className="muted">Factors flagged "to be verified against primary source" were taken from secondary extracts according to the data file (backend/amcrax/data/environmental.yaml); re-check them before external use.</p>
        <DataTable columns={fCols} rows={factors} caption="Emission factors with sources" filename="emission_factors.csv" />
      </div>
    </>
  )
}
