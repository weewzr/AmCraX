import { useEffect, useMemo, useState } from 'react'
import { fetchCatalysts, runPfr } from '../../api/reactor'
import { SourceBadge } from '../../components/ui'
import { DataTable, type Column } from '../../components/DataTable'
import { Notice } from '../common/Notice'
import { useAsync } from '../common/useAsync'
import { XYChart } from '../common/XYChart'
import { extractProfile, normaliseCatalysts, type CatalystRow, type PfrProfile } from './shape'

const cols: Column<CatalystRow>[] = [
  { key: 'catalyst', label: 'Catalyst' },
  { key: 'rate_law', label: 'Rate law', render: (r) => <span className="wrap-cell">{r.rate_law}</span> },
  { key: 'parameters', label: 'Parameters', render: (r) => <span className="wrap-cell">{r.parameters}</span> },
  { key: 'validity', label: 'Validity range', render: (r) => <span className="wrap-cell">{r.validity}</span> },
  { key: 'source', label: 'Source', render: (r) => <span className="wrap-cell">{r.source}</span> },
  { key: 'limitations', label: 'Limitations', render: (r) => <span className="wrap-cell">{r.limitations}</span> },
]

export function KineticsSection({ live, readable }: { live: boolean; readable: boolean }) {
  const cat = useAsync((s) => fetchCatalysts(s), [], readable)
  const catalysts = useMemo(() => (cat.phase === 'ready' ? normaliseCatalysts(cat.data) : []), [cat])
  const [id, setId] = useState('')
  const [T, setT] = useState('500')
  const [P, setP] = useState('1')
  const [feed, setFeed] = useState('100')
  const [mass, setMass] = useState('10')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [profile, setProfile] = useState<PfrProfile | null>(null)
  const [raw, setRaw] = useState<unknown>(null)

  useEffect(() => { if (!id && catalysts[0]) setId(catalysts[0].id || catalysts[0].catalyst) }, [catalysts, id])

  const unavailable = cat.phase === 'error' && (cat.status === 503 || cat.status === 404)
  const run = async () => {
    setBusy(true); setErr(null); setProfile(null)
    try {
      const body = await runPfr({ catalyst_id: id || null, T_C: Number(T), P_bar: Number(P), feed_nh3_kmol_h: Number(feed), catalyst_mass_kg: mass === '' ? null : Number(mass), n_points: 60 })
      setRaw(body)
      const p = extractProfile(body)
      if (!p) setErr('The PFR run returned, but no axial profile could be recognised in the response; raw response shown below.')
      setProfile(p)
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); setRaw(null) } finally { setBusy(false) }
  }

  if (!readable) return <Notice kind="warn" title="Kinetics are not available in this mode.">Catalyst table and PFR runs need the API or a snapshot.</Notice>
  if (cat.phase === 'loading') return <Notice>Loading catalyst models ...</Notice>
  if (unavailable) return <Notice kind="warn" title="Kinetic module not available from the API.">GET /api/kinetics/catalysts answered HTTP {cat.status}. No kinetic curves are shown; nothing is substituted. Reload when the module is deployed.</Notice>
  if (cat.phase === 'error') return <Notice kind="error" title="Could not load catalysts.">{cat.error}</Notice>

  const data = profile ? profile.rows.map((r) => ({
    ...r,
    ...(profile.conv ? { [profile.conv]: r[profile.conv] === null ? null : (r[profile.conv] as number) * 100 } : {}),
    ...(profile.eq ? { [profile.eq]: r[profile.eq] === null ? null : (r[profile.eq] as number) * 100 } : {}),
  })) : []

  return (
    <div className="page-block">
      <DataTable<CatalystRow> columns={cols} rows={catalysts} caption="Catalyst kinetic models (literature rate laws; see source and limitations)" filename="catalyst_models.csv" />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Plug-flow reactor run <SourceBadge source="python_model" /></h3>
        <form className="controls" onSubmit={(e) => { e.preventDefault(); void run() }}>
          <label className="field">Catalyst
            <select value={id} onChange={(e) => setId(e.target.value)}>{catalysts.map((c) => <option key={c.id || c.catalyst} value={c.id || c.catalyst}>{c.catalyst}</option>)}</select></label>
          <label className="field">T [degC]<input type="number" value={T} onChange={(e) => setT(e.target.value)} /></label>
          <label className="field">P [bar]<input type="number" value={P} onChange={(e) => setP(e.target.value)} /></label>
          <label className="field">NH3 feed [kmol/h]<input type="number" value={feed} onChange={(e) => setFeed(e.target.value)} /></label>
          <label className="field">Catalyst mass [kg]<input type="number" required min="0.001" step="any" value={mass} onChange={(e) => setMass(e.target.value)} /></label>
          <button type="submit" className="btn" disabled={busy || !live} title={live ? undefined : 'Needs the live API'}>{busy ? 'Running ...' : 'Run PFR'}</button>
        </form>
        {!live ? <p className="muted">SNAPSHOT mode: running a new plug-flow calculation needs the live API; the catalyst table above is the stored model metadata.</p> : null}
        {err ? <Notice kind="error">{err}</Notice> : null}
      </div>
      {profile ? (
        <div className="grid-2">
          <XYChart title="Conversion along the reactor" xKey={profile.xKey} xLabel={profile.xKey} yLabel="NH3 conversion [%]" data={data}
            description="Axial NH3 conversion from the plug-flow model with the equilibrium limit when provided."
            series={[
              ...(profile.conv ? [{ key: profile.conv, label: 'Kinetic conversion', color: '#38bdf8', kind: 'line' as const, source: 'python_model' as const }] : []),
              ...(profile.eq ? [{ key: profile.eq, label: 'Equilibrium limit', color: '#ff7a3d', kind: 'line' as const, dashed: true, source: 'python_model' as const }] : []),
            ]} />
          {profile.temp ? <XYChart title="Temperature profile" xKey={profile.xKey} xLabel={profile.xKey} yLabel={profile.temp} data={data} description="Axial temperature." series={[{ key: profile.temp, label: 'Temperature', color: '#f472b6', kind: 'line', source: 'python_model' }]} /> : null}
          {profile.press ? <XYChart title="Pressure profile" xKey={profile.xKey} xLabel={profile.xKey} yLabel={profile.press} data={data} description="Axial pressure." series={[{ key: profile.press, label: 'Pressure', color: '#4ade80', kind: 'line', source: 'python_model' }]} /> : null}
        </div>
      ) : null}
      {raw && !profile ? <pre className="card" style={{ overflow: 'auto', maxHeight: 240 }}>{JSON.stringify(raw, null, 2).slice(0, 4000)}</pre> : null}
    </div>
  )
}

