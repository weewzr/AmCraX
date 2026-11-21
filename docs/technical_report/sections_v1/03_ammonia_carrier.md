<!-- cites: cechetto2023membrane, xu2025review, cho2026nickel, mehr2026highcapacity, chopra2026decentralized, richard2024technoeconomic, ahmad2025gtcc, kum2026heatintegrated, smith_grimech30, goodwin2018cantera, iso2019hydrogen -->

# 3 Ammonia as a hydrogen carrier

## 3.1 Hydrogen content

The hydrogen content of ammonia follows from the stoichiometry NH~3~ → ½ N~2~ + 3/2 H~2~. One mole of NH~3~ releases 1.5 mol of H~2~. The molar masses are those used by the AmCraX thermodynamics package (GRI-Mech 3.0 data loaded through Cantera; Smith et al., n.d.; Goodwin et al., 2018): M(NH~3~) = 17.031 g/mol and M(H~2~) = 2.016 g/mol. The gravimetric hydrogen content is then

$$ w_{\mathrm{H_2}} = \frac{1.5\,M_{\mathrm{H_2}}}{M_{\mathrm{NH_3}}} = \frac{1.5 \times 2.016}{17.031} = \frac{3.024}{17.031} = 0.1776 \qquad (3.1) $$

where $w_{\mathrm{H_2}}$ is the mass of H~2~ released per mass of NH~3~ (kg/kg): ammonia contains **17.8 wt%** hydrogen, as also given by Cechetto et al. (2023, p. 10776) and Xu et al. (2025). The reciprocal, 5.632 kg NH~3~ per kg H~2~, is the theoretical minimum feed (also Cho et al., 2026, pp. 10-11); their cost-optimised plants need 7.639 (Ru, 10 bar) and 8.011 kg/kg (Ni, 24.34 bar) because fuel is burned to heat the cracker and hydrogen is lost in purification.
<!-- data: molar masses from Cantera gri30.yaml (amcrax.thermodynamics data source); research/notes/cechetto2023membrane.md Table 1; research/notes/xu2025review.md p. 3; research/notes/cho2026nickel.md pp. 10-11 and Table 7 -->

## 3.2 Storage and handling

Ammonia boils at −33.4 degC at atmospheric pressure and liquefies at 0.7-0.8 MPa at ambient temperature (Xu et al., 2025, p. 3). It can therefore be stored either refrigerated near atmospheric pressure or pressurised at ambient temperature. Cechetto et al. (2023, p. 10776) give 25 degC and 9.9 bar, a liquid density of 600 kg/m^3^, a lower heating value (LHV) of 18.6 MJ/kg and 12.7 MJ/L. Large import terminals use the refrigerated route. Mehr et al. (2026, p. 4200) design two 27,000 t refrigerated tanks with boil-off-gas re-liquefaction for a 1000 t/d cracker. The AmCraX feed follows the refrigerated route: saturated liquid at 1.013 bar (Section 6).

Ammonia has a narrow flammability range and needs far more ignition energy than hydrogen (Table 3.1). This lowers the fire hazard but makes ammonia-rich tail gas harder to burn, which matters for the tail-gas burner. Sources differ in detail: Cechetto et al. (2023, p. 10777) give an auto-ignition temperature of 650 degC and a flammability range of 15.15-27.35 % in dry air.

Table: **Table 3.1.** Fuel and safety properties of ammonia, hydrogen, methanol and methane. *Source: published literature, Xu et al. (2025, Table 1), who compiled them from earlier sources.*

| Property | NH~3~ | H~2~ | CH~3~OH | CH~4~ |
|---|---|---|---|---|
| Lower heating value (MJ/kg) | 18.6 | 120 | 19.8 | 50 |
| Adiabatic flame temperature (degC) | 1800 | 2100 | 1637 | 1950 |
| Auto-ignition temperature (degC) | 585 | 500-576 | 438 | 650 |
| Flammability limits in air (vol%) | 16-27 | 4.0-75 | 6.7-39 | 5-15 |
| Minimum ignition energy (mJ) | 8 | 0.01 | 0.14 | 0.28 |

<!-- data: research/notes/xu2025review.md "Other property data quoted (Table 1, p. 4)"; research/notes/cechetto2023membrane.md Table 1 and p. 3 -->

## 3.3 Position of the cracker in the supply chain

The cracker sits at the receiving end of the chain, after synthesis, transport and storage. Published scales and end uses:

* **Centralised pipeline-grade hydrogen.** A 1000 t/d NH~3~ cracker produces about 137 t/d H~2~ at more than 100 bar (Mehr et al., 2026).
* **Power generation.** One study needs 2600 kmol/h H~2~ at 30 bar for a 30 vol% H~2~ / 70 % NH~3~ fuel blend in a retrofitted combined-cycle plant (Richard et al., 2024, p. 574). Another heats a partial cracker with gas-turbine exhaust (Ahmad et al., 2025). Partial cracking of 30-40 % is reported to be enough for stable gas-turbine combustion (Xu et al., 2025, p. 5).
* **Decentralised refuelling.** Chopra et al. (2026) size a station for 400 kg H~2~/day delivered at 350 bar.

The NH~3~ feed price dominates cost at every scale. It accounts for 61-65 % of the levelised cost of hydrogen (LCOH) in Cho et al. (2026, p. 14), 65 % (fired tubular reactor) and 70 % (membrane reactor) in Richard et al. (2024, p. 584), and a sensitivity index of 0.988 in Kum et al. (2026, p. 17). This is why hydrogen yield per kg of ammonia is a central performance indicator in AmCraX.
<!-- data: research/notes/mehr2026highcapacity.md; research/notes/richard2024technoeconomic.md (p. 4, p. 14); research/notes/ahmad2025gtcc.md; research/notes/xu2025review.md p. 5; research/notes/chopra2026decentralized.md; research/notes/cho2026nickel.md p. 14; research/notes/kum2026heatintegrated.md p. 17 -->

## 3.4 Product hydrogen quality

Cracked gas at full conversion is 75 mol% H~2~ and 25 mol% N~2~ plus unconverted NH~3~. For proton-exchange-membrane fuel cells ISO 14687:2019 limits NH~3~ to 0.1 ppm, and N~2~ to 300 ppm for vehicles or 50 % for stationary use (ISO, 2019, as cited in Cechetto et al., 2023, p. 10779), so fuel-cell hydrogen always needs NH~3~ removal, for example a zeolite TSA ahead of the PSA (Cho et al., 2026, p. 6), and vehicle grade also needs N~2~ removal. Gas turbines accept N~2~ and some NH~3~ (Ahmad et al., 2025).

The AmCraX separation block is a reduced-order splitter (H~2~ recovery 0.85, an engineering assumption; N~2~ slip 0.001), not designed against a purity specification. The baseline product (392 ppm N~2~) is therefore not fuel-cell grade, and NH~3~ polishing is not modelled (Sections 6.4 and 12).
<!-- data: research/notes/cechetto2023membrane.md p. 5; research/notes/cho2026nickel.md p. 6; backend/amcrax/schemas.py CaseInputs.psa_h2_recovery / psa_n2_slip defaults; results/simulations/baseline.json streams.H2PROD.mole_frac.N2 0.000392 -->
