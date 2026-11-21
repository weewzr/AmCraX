import { Link } from 'react-router-dom'
import { equilibriumAt } from '../../calc/equilibrium'
import { platformPath } from '../routes'
import { Callout, Cite, ExecLabel, PageHero, Section } from '../ui'

const M_NH3 = 17.031
const M_H2 = 2.016
const W_H2 = (1.5 * M_H2) / M_NH3

export default function Why() {
  const rows = [250, 600, 900].map((T) => equilibriumAt(T, 1))
  const rows20 = [250, 600, 900].map((T) => equilibriumAt(T, 20))
  const dH298 = equilibriumAt(25, 1).dH_kJ_per_mol_NH3
  return (
    <>
      <PageHero
        eyebrow="Section 2 - Background"
        title="Why ammonia cracking"
        lead={<>Hydrogen is a carbon-free energy vector that is hard to store and move. Ammonia carries it chemically. At the destination the hydrogen has to be released again: that step is ammonia cracking, and its heat demand, yield and purification decide whether the carrier is competitive.</>}
      />

      <Section id="transport" title="The hydrogen transport problem" intro="Low volumetric energy density, plus the cost of compressing or liquefying hydrogen, makes bound hydrogen attractive.">
        <div className="prose">
          <p>
            Liquid ammonia holds 121 kg of H<sub>2</sub> per m<sup>3</sup> and can be stored at 25 {'°C'} and 9.9 bar <Cite k="cechetto2023membrane" p="10776" />, or refrigerated at about
            {' '}-33 {'°C'} near atmospheric pressure <Cite k="xu2025review" p="3" />. For pipeline transport over 1610 km, a cost of about 0.194 USD per kg H<sub>2</sub> has been reported for
            ammonia, against 0.51 to 3.22 USD per kg H<sub>2</sub> for gaseous hydrogen <Cite k={['bartels2008feasibility', 'xu2025review']} />.
          </p>
          <p>
            The ammonia chain is also more mature than the cracking step that ends it. Technology readiness levels are reported as 7 for fired tubular crackers and 4 to 5 for membrane
            reactors <Cite k="richard2024technoeconomic" />, and 4 to 6 overall <Cite k="ahmad2025gtcc" />. Vendor single-train capacities are 1000 to 1200 t/d of NH<sub>3</sub> <Cite k="mehr2026highcapacity" p="4203" />.
          </p>
        </div>
      </Section>

      <Section id="carrier" alt title="Ammonia as a hydrogen carrier" intro="The hydrogen content follows directly from the stoichiometry.">
        <div className="two-col">
          <div className="prose">
            <p>
              One mole of NH<sub>3</sub> releases 1.5 mol of H<sub>2</sub>. With M(NH<sub>3</sub>) = {M_NH3} g/mol and M(H<sub>2</sub>) = {M_H2} g/mol, the gravimetric hydrogen content is
              {' '}<strong>{(W_H2 * 100).toFixed(1)} wt%</strong>, as also given by <Cite k="cechetto2023membrane" p="10776" /> and <Cite k="xu2025review" />. The reciprocal, {(1 / W_H2).toFixed(3)} kg NH<sub>3</sub> per kg H<sub>2</sub>, is the theoretical minimum feed;
              the cracker cases of that study need about 7.6 (Ru) to 8.05 (Ni) kg/kg because fuel is burned to heat the cracker and hydrogen is lost in purification <Cite k="cho2026nickel" p="10-11" />.
            </p>
            <p>
              The feed price dominates the cost at every scale: ammonia is 61 to 65 % of the levelised cost of hydrogen in <Cite k="cho2026nickel" p="14" /> and 65 % (fired tubular) to 70 % (membrane reactor) in <Cite k="richard2024technoeconomic" p="584" />.
              Hydrogen yield per kg of ammonia is therefore a central performance indicator in AmCraX.
            </p>
          </div>
          <figure className="eq-card">
            <div className="eq" role="math" aria-label="NH3 reacts to one half N2 plus three halves H2">
              NH<sub>3</sub> {'⇄'} {'½'} N<sub>2</sub> + {'¾'}{'×'}2 H<sub>2</sub>
            </div>
            <figcaption className="muted">Cracking reaction per mole of ammonia (1.5 mol H<sub>2</sub>, 0.5 mol N<sub>2</sub>). Gas moles rise from 1 to 2 per mole converted, so pressure works against conversion.</figcaption>
          </figure>
        </div>
      </Section>

      <Section id="heat" title="The cracking reaction and its heat demand" intro="Cracking is endothermic and needs temperatures of several hundred degrees Celsius.">
        <div className="prose">
          <p>
            Releasing the hydrogen takes 30.6 kJ per mol H<sub>2</sub>, against 0.907 kJ per mol H<sub>2</sub> for regasifying liquid hydrogen <Cite k="cechetto2023membrane" p="10777" />.
            Published reaction enthalpies are 45.6 to 46.2 kJ per mol NH<sub>3</sub> <Cite k={['cho2026nickel', 'richard2024technoeconomic', 'maccarrone2025comprehensive', 'mehr2026highcapacity']} />; the AmCraX thermodynamics package, built on the
            GRI-Mech 3.0 NASA-7 data <Cite k={['smith_grimech30', 'goodwin2018cantera']} />, gives +{dH298.toFixed(2)} kJ/mol NH<sub>3</sub> at 298 K. Typical catalysts need about 600 {'°C'} for complete conversion; the research target is 400 to 500 {'°C'} <Cite k="xu2025review" p="4" />.
          </p>
          <p>
            The reaction enthalpy rises with temperature and the equilibrium constant rises much faster, which is why a hot, low-pressure cracker converts almost everything but a pressurised one needs more heat per mole of ammonia.
          </p>
        </div>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Reaction enthalpy and equilibrium constant versus temperature">
          <table className="data simple">
            <caption>Reaction enthalpy and equilibrium conversion of pure NH<sub>3</sub> <ExecLabel kind="browser" /></caption>
            <thead><tr><th scope="col">Temperature</th><th scope="col" className="r">{'Δ'}H<sub>r</sub> [kJ/mol NH<sub>3</sub>]</th><th scope="col" className="r">K [-]</th><th scope="col" className="r">X<sub>eq</sub> at 1 bar</th><th scope="col" className="r">X<sub>eq</sub> at 20 bar</th></tr></thead>
            <tbody>
              {rows.map((e, i) => (
                <tr key={e.T_C}>
                  <th scope="row">{e.T_C} {'°C'}</th>
                  <td className="r">{e.dH_kJ_per_mol_NH3.toFixed(2)}</td>
                  <td className="r">{e.K < 100 ? e.K.toFixed(2) : e.K.toFixed(1)}</td>
                  <td className="r">{(e.conversion * 100).toFixed(2)} %</td>
                  <td className="r">{(rows20[i].conversion * 100).toFixed(2)} %</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">Ideal gas, closed form of the equilibrium; see the <Link to="/methodology#equilibrium">methodology</Link> and the <Link to="/#try">calculator</Link>.</p>
      </Section>

      <Section id="purification" alt title="Purification" intro="Cracked gas is hydrogen and nitrogen with unconverted ammonia. What can be done with it depends on the specification.">
        <div className="prose">
          <p>
            At full conversion the gas is 75 mol% H<sub>2</sub> and 25 mol% N<sub>2</sub>. For proton-exchange-membrane fuel cells ISO 14687:2019 limits NH<sub>3</sub> to 0.1 ppm and N<sub>2</sub> to 300 ppm for vehicles
            {' '}<Cite k={['iso2019hydrogen', 'cechetto2023membrane']} p="10779" />, so fuel-cell hydrogen always needs NH<sub>3</sub> removal, for example a zeolite temperature-swing adsorber ahead of the pressure-swing adsorber (PSA) <Cite k="cho2026nickel" p="6" />.
            Gas-turbine use does not need this purification: <Cite k="ahmad2025gtcc" /> fire partly or fully cracked NH<sub>3</sub>/H<sub>2</sub>-N<sub>2</sub> blends, nitrogen included, in a combined-cycle plant.
          </p>
          <p>
            PSA is described as the most developed separation technology for this duty <Cite k="cechetto2023membrane" p="10778" />. A published PSA recovery is 75.6 % at 99.11 mol% purity <Cite k="cho2026nickel" p="6" />;
            palladium membrane reactors reach more than 99 % conversion with 90 to 97.5 % hydrogen recovery at 400 to 500 {'°C'} and 4 to 7 bar <Cite k="cechetto2023membrane" />, and in one techno-economic study a membrane reactor outperforms a conventional one only from about 5 to 6 bar <Cite k="richard2024technoeconomic" p="581" />.
            Heat integration is a major efficiency lever in the literature: preheating the cracker feed with product heat raised the hydrogen yield from 0.131 to 0.141 kg H<sub>2</sub> per kg NH<sub>3</sub> <Cite k="hansen2024hysys" p="83" />, and a pinch-based network recovered 94.56 % of the waste-heat potential against 18.22 % in a conventional plant <Cite k="kum2026heatintegrated" />.
          </p>
        </div>
        <Callout kind="warn" title="Where AmCraX stands.">
          Its separator is a reduced-order splitter with an assumed recovery, and the baseline product is not fuel-cell grade. See <Link to="/about#limits">what AmCraX does not claim</Link>.
          The flowsheet and its heat integration are explored on the <Link to={platformPath('/pfd')}>interactive platform</Link>.
        </Callout>
      </Section>
    </>
  )
}
