import type { StoredPurification as SP } from '../sim'

const CONF_LABEL: Record<string, string> = {
  PSA_low_recovery: 'PSA, low recovery', PSA_central_recovery: 'PSA, central recovery', PSA_high_recovery: 'PSA, high recovery',
  MEM_cost_low: 'Membrane, low cost', MEM_central: 'Membrane, central', MEM_cost_high: 'Membrane, high cost',
}

/**
 * Stored Python comparison of PSA and Pd-Ag membrane at the reference conditions (results/research/purification/phase2_comparison.json
 * through the exporter). The browser has no membrane model: these numbers do not respond to the controls, and the table says so.
 */
export function StoredPurification({ sp }: { sp: SP | null | undefined }) {
  if (!sp) return <p className="sim-nm-block-l">Stored purification comparison: not in this data export.</p>
  const pct = (v: number) => `${(v * 100).toFixed(1)} %`
  return (
    <section className="sim-stored" aria-labelledby="sim-stored-h" data-testid="stored-purification">
      <h3 id="sim-stored-h" className="sim-stored-h">Stored comparison: PSA against Pd-Ag membrane</h3>
      <p className="sim-stored-warn"><strong>Stored Python results at the reference conditions.</strong> They do not respond to the controls on this page; the browser has no membrane model.
        {' '}Source: <code>{sp.file}</code>{sp.script ? <> (<code>{sp.script}</code>)</> : null}. Comparison of models, not experimental validation.</p>
      {Object.entries(sp.specs).map(([sid, spec]) => (
        <div key={sid} className="sim-stored-spec">
          <h4>{spec.label}</h4>
          <div className="sim-cmp-wrap">
            <table className="sim-ptable" data-spec={sid}>
              <thead><tr><th scope="col">Configuration</th><th scope="col">H2 recovery</th><th scope="col">N2 (ppm)</th><th scope="col">Cost, USD/kg usable H2</th><th scope="col">SGD/kg</th><th scope="col">Readiness (TRL)</th></tr></thead>
              <tbody>{Object.entries(spec.configurations).map(([cid, r]) => (
                <tr key={cid} data-conf={cid}>
                  <th scope="row">{CONF_LABEL[cid] ?? cid}{r.recovery_source?.source_type ? <span className="sim-stored-src"> recovery: {r.recovery_source.source_type}</span> : null}</th>
                  <td className="sim-num">{pct(r.h2_recovery)}</td>
                  <td className="sim-num">{r.n2_ppm.toFixed(r.n2_ppm < 100 ? 1 : 0)}</td>
                  <td className="sim-num">{r.lcoh_usd_per_kg_usable.toFixed(3)}</td>
                  <td className="sim-num">{r.lcoh_sgd_per_kg_usable.toFixed(3)}</td>
                  <td>{r.readiness.trl ?? 'not given'}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      ))}
      <p className="sim-stored-note">Costs include delivery compression to the stated pressure, so they are higher than the plant-gate baseline
        {sp.basis.baseline_lcoh_usd !== undefined ? <> ({sp.basis.baseline_lcoh_usd.toFixed(3)} USD/kg)</> : null}. The source type of each PSA
        recovery is shown in its row; the low PSA recovery comes from a different feed (ammonia-plant purge gas). The membrane rows use the Python Sieverts model.
        {sp.basis.baseline_note ? <> Basis: {sp.basis.baseline_note.replace(/\.?\s*$/, '.')}</> : null} Readiness levels from <code>research/data/membrane_trl.json</code>.</p>
    </section>
  )
}
