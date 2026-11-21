<!-- cites: cechetto2023membrane, xu2025review, bartels2008feasibility, cho2026nickel, mehr2026highcapacity, richard2024technoeconomic, ahmad2025gtcc, chopra2026decentralized, kum2026heatintegrated, iso2019hydrogen, hansen2024hysys, farokhi2025costoptimization -->

# 2 Motivation and background

## 2.1 The hydrogen transport problem

Hydrogen is a carbon-free energy vector, but its low volumetric energy density makes it costly to store and move. A chemical carrier binds it in a denser liquid that is cracked near the point of use. Ammonia is the leading candidate: the liquid holds 121 kg H~2~ per m^3^ and can be stored at 25 degC and 9.9 bar (Cechetto et al., 2023, p. 10776), and pipeline transport over 1610 km has been costed at about 0.194 USD/kg H~2~ as ammonia against 0.51-3.22 USD/kg H~2~ as gaseous hydrogen (Bartels, 2008, as cited in Xu et al., 2025, p. 3).
<!-- data: research/notes/cechetto2023membrane.md (Table 1, PDF p. 2 = journal p. 10776); research/notes/xu2025review.md ("Other property data quoted", p. 3) -->

## 2.2 Ammonia as a hydrogen carrier

One mole of NH~3~ releases 1.5 mol of H~2~ (Section 3.1), so the gravimetric hydrogen content is

$$ w_{\mathrm{H_2}} = \frac{3\,M_{\mathrm{H}}}{M_{\mathrm{NH_3}}} = \frac{3 \times 1.008}{17.031} = 0.1776 \qquad (2.1) $$

where $w_{\mathrm{H_2}}$ is the mass of hydrogen per mass of ammonia (kg/kg), $M_{\mathrm{H}}$ = 1.008 g/mol and $M_{\mathrm{NH_3}}$ = 17.031 g/mol: 17.8 wt%, as also given by Cechetto et al. (2023, p. 10776). The reciprocal, 5.632 kg NH~3~/kg H~2~, is the stoichiometric minimum; cost-optimised plants need 7.639-8.011 kg/kg because ammonia is also burned as fuel and hydrogen is lost in purification (Cho et al., 2026, p. 13).
<!-- data: fact sheet F1 (3 x 1.008 / 17.031); research/notes/cechetto2023membrane.md Table 1; research/notes/cho2026nickel.md pp. 10-11 and Table 7 (p. 13) -->

Ammonia boils at -33.4 degC and liquefies at 0.7-0.8 MPa at ambient temperature (Xu et al., 2025, p. 3), so it is stored either pressurised or refrigerated near 1 bar, the route of large designs (Mehr et al., 2026, p. 4200) and of AmCraX. Its high ignition energy (Table 2.1) lowers the fire hazard but makes an ammonia-bearing tail gas harder to burn.
<!-- data: research/notes/xu2025review.md p. 3; research/notes/mehr2026highcapacity.md (PDF p. 4 = journal p. 4200, two 27,000 t refrigerated tanks) -->

Table: **Table 2.1.** Fuel and safety properties of ammonia, hydrogen, methanol and methane. *Source: published literature, Xu et al. (2025, Table 1, p. 4), compiled by those authors from earlier sources; Cechetto et al. (2023, p. 10777) give 650 degC and 15.15-27.35 vol% for ammonia.*

| Property | NH~3~ | H~2~ | CH~3~OH | CH~4~ |
|---|---|---|---|---|
| Lower heating value (MJ/kg) | 18.6 | 120 | 19.8 | 50 |
| Adiabatic flame temperature (degC) | 1800 | 2100 | 1637 | 1950 |
| Auto-ignition temperature (degC) | 585 | 500-576 | 438 | 650 |
| Flammability limits in air (vol%) | 16-27 | 4.0-75 | 6.7-39 | 5-15 |
| Minimum ignition energy (mJ) | 8 | 0.01 | 0.14 | 0.28 |

<!-- data: research/notes/xu2025review.md "Other property data quoted (Table 1, p. 4)"; research/notes/cechetto2023membrane.md p. 3 -->

The carrier is paid for at the receiving end: endothermic catalytic decomposition ("cracking") takes 30.6 kJ/mol H~2~ at several hundred degC, against 0.907 kJ/mol H~2~ for regasifying liquid hydrogen (Cechetto et al., 2023, p. 10777), and it is less mature than the rest of the chain: technology readiness level 7 for fired tubular crackers and 4-5 for membrane reactors (Richard et al., 2024), or 4-6 overall (Ahmad et al., 2025, p. 7).
<!-- data: research/notes/cechetto2023membrane.md p. 3; research/notes/richard2024technoeconomic.md (uncertainty-analysis paragraph); research/notes/ahmad2025gtcc.md p. 7 -->

## 2.3 Where the cracker sits

The cracker is the last step of the chain. Published designs range from pipeline-grade hydrogen at 137 t/d (Mehr et al., 2026) and 2600 kmol/h H~2~ for a gas-turbine fuel blend (Richard et al., 2024, p. 574) to 400 kg/d for a refuelling station (Chopra et al., 2026). At every scale the ammonia price dominates: it is 61-65 % of the levelised cost of hydrogen (LCOH) in Cho et al. (2026, p. 14) and 65-70 % in Richard et al. (2024, p. 584). Hydrogen delivered per kilogram of ammonia bought is therefore a central AmCraX performance indicator.
<!-- data: research/notes/mehr2026highcapacity.md (137.42 t/d); research/notes/richard2024technoeconomic.md (p. 4 = 574; p. 14 = 584); research/notes/chopra2026decentralized.md; research/notes/cho2026nickel.md p. 14 -->

## 2.4 Product-quality requirements

For fuel-cell vehicles ISO 14687:2019 limits NH~3~ to 0.1 ppm and N~2~ to 300 ppm (ISO, 2019, as cited in Cechetto et al., 2023, p. 10779), so fuel-cell hydrogen needs both NH~3~ and N~2~ removal.

The AmCraX separation block is a reduced-order splitter with an assumed H~2~ recovery of 0.85 and N~2~ slip of 0.001. The baseline purity of 99.961 mol% H~2~ (392 ppm N~2~) follows from these assumed split fractions; it is not a prediction. It is below the 300 ppm N~2~ limit and the 99.97 mol% quoted for fuel-cell hydrogen, so the baseline product is not fuel-cell grade, and NH~3~ polishing is not modelled (Section 11). The assumed recovery is above the published PSA range of 0.71-0.81 (Section 4.3).
<!-- data: results/simulations/baseline.json inputs.psa_h2_recovery 0.85, inputs.psa_n2_slip 0.001, streams.H2PROD.mole_frac (H2 0.999607997, N2 0.000392003); research/notes/cechetto2023membrane.md p. 5 (ISO limits); 99.97 mol% from config/scenarios.json scn_fuel_cell_grade rationale (no library source) -->

## 2.5 What AmCraX is and what this report covers

AmCraX (Ammonia Cracking Simulation and Optimisation Platform) models a complete ammonia-to-hydrogen plant in four layers: an **Aspen Plus V15 flowsheet** with an equilibrium cracker, generated as an input file and run through the COM interface; **independent Python models** of the same plant and its economics that cross-check it; a **FastAPI back end** that runs Aspen jobs in an isolated worker process and labels every value with its provenance; and a **React dashboard**. The baseline cracks 100 kmol/h of liquid ammonia at 600 degC and 20 bar. As in comparable studies (Cho et al., 2026; Farokhi et al., 2025; Hansen et al., 2024; Kum et al., 2026), the questions are how much heat the cracker needs, how much the tail gas and heat recovery supply, and what that means for yield and cost.
<!-- data: results/simulations/baseline.json inputs (feed_total_kmol_h 100, reactor_temperature_C 600, reactor_pressure_bar 20) -->

The claims are limited on purpose: the equilibrium reactor shows the thermodynamic limit, not a reactor design; the separation block is not a designed PSA unit; costs are preliminary; the carbon accounting is not a life-cycle assessment; and the steady-state model is not a validated digital twin. Sections 3 to 12 cover fundamentals, literature, process design, the Aspen model and automation; Sections 13 to 16 equilibrium, kinetics, balances and validation; Sections 17 to 21 the results; Sections 22 to 25 the dashboard, website, limitations and conclusions.
