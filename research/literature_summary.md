# Literature review: ammonia cracking for hydrogen supply

*All numbers are literature values taken from research/notes and research/model_parameters.yaml. They are not AmCraX results. References are listed in research/references_apa.md.*

## Thermodynamics

Ammonia decomposition, NH3 ⇌ ½N2 + 1.5H2, is endothermic. The reviewed papers report a standard reaction enthalpy of 45.6 to 46.2 kJ per mol NH3 (Cechetto et al., 2023; Cho et al., 2026; Kum et al., 2026; Xu et al., 2025). The reaction produces more moles than it consumes, so conversion rises with temperature and falls with pressure. Cechetto et al. (2023) used Aspen Plus RGibbs to calculate equilibrium conversion for pure NH3. They report more than 99% above 400 °C at 1 bar and more than 95% above 500 °C at 1-20 bar. At 5 bar, conversion is 95.9% at 400 °C and 98.7% at 500 °C. Xu et al. (2025) show about 80% at 400 °C and 92% at 500 °C at 3 MPa (read from their figure). The equilibrium-constant correlations reprinted by Maccarrone et al. (2025) contain typographical errors. Before using them, they must be checked against the originals, for example Wang et al. (1999). Kum et al. (2026) give a Gibbs-energy polynomial that is consistent with standard thermochemical data (Goodwin et al., 2018; Linstrom & Mallard, n.d.).

## Ni and Ru catalysts and kinetics

Ruthenium is the most active metal. Nickel is cheaper but needs higher temperatures. Su et al. (2023) collect apparent activation energies of 41.55-98.2 kJ/mol for supported Ru and turnover frequencies of 0.04-11.4 s⁻¹. Which step limits the rate is still debated. The candidates are N2 recombinative desorption and N-H bond scission (Maccarrone et al., 2025; Su et al., 2023). Takahashi and Fujitani (2016) fitted a four-step microkinetic model to Ni/MgO and Ru/MgO at 1 atm. In their model, NH3 dehydrogenation controls the rate on Ni and N2 desorption controls it on Ru. Their parameters are given per gram of catalyst, which makes them directly usable in a plug-flow model. However, the rate depends only on mole fractions, and the reverse reactions are left out. Use at elevated pressure is therefore an extrapolation and needs an equilibrium constraint.

Kum et al. (2026) fitted a reversible Temkin-Pyzhev law (activation energy 114.2 kJ/mol, β = 0.27) for a commercial Ru/Al2O3 catalyst. The fit used data measured by Di Carlo et al. (2014) at 1-10 bar, which makes it the only usable pressure-dependent rate law in the library. Pressure suppresses conversion strongly. On Ru-K/CaO at 500 °C, conversion falls from 98% at 1 bar to 65% at 20 bar (Sayas et al., 2020, as tabulated by Maccarrone et al., 2025). Other rate laws in the corpus cannot be reproduced: parameters are missing (Chopra et al., 2026; Mehr et al., 2026), units are ambiguous (Su et al., 2023), or values are only in unavailable supplementary files (Cho et al., 2026; Richard et al., 2024).

Long-term tests show slow deactivation. An industrial Ni catalyst lost about 1.5 percentage points between 250 and 800 h at 534 °C. A coprecipitated Ni/Al2O3 deactivated faster, with Ni crystallites growing from 3.5 to 5.0 nm (Purcel et al., 2025). Ru/MgO deactivated linearly over more than 1000 h (Yamazaki et al., 2022).

## Reactor models

Process studies use three levels of reactor model:
- **Equilibrium (Gibbs) reactors.** These are optimistic about conversion (Farokhi et al., 2025; Hansen et al., 2024).
- **Isothermal multitubular plug-flow reactors with kinetics.** Cho et al. (2026) imposed a minimum conversion of 97%.
- **Detailed fired-tube models.** Kum et al. (2026) solved two-dimensional mass and energy balances for 336 tubes with Ergun pressure drop and radiative flue-gas heating. They report 96.3% conversion at a GHSV of 1800 h⁻¹ and more than 2 bar pressure drop.

## Heat integration

The endothermic duty and the hot product gas make heat recovery central. Kum et al. (2026) applied pinch targeting with a 10 K minimum temperature approach, following the method of Linnhoff and Hindmarsh (1983). A designed heat-exchanger network recovered 5750 kW of a 6081 kW maximum, compared with 1108 kW in a conventional layout. Xu et al. (2025) quote an increase in process efficiency from 65.7% to 75.3% when feed/effluent heat exchange and an adiabatic pre-cracker are added. Furnace firing with PSA tail gas is common practice. Chopra et al. (2026) burn 18% of the product gas. Cho et al. (2026) find that their Ru case needs no NH3 make-up fuel, while their Ni case at 24 bar does, and Cechetto et al. (2023) state that off-gas alone is generally insufficient.

## Purification

Fuel-cell hydrogen must meet ISO 14687:2019: at most 0.1 ppm NH3 and, for vehicles, at most 300 ppm N2 (as quoted by Cechetto et al., 2023). Residual NH3 is removed by TSA on zeolite 4A. Kum et al. (2026) recover 98.57% of the H2 in their TSA unit, and Cho et al. (2026) reach an NH3 outlet of 0.1 ppm or less. H2 is then purified by PSA. Reported PSA H2 recoveries are 0.71-0.81 (Cho et al., 2026, based on Yáñez et al., 2020; Hansen et al., 2024; Kum et al., 2026), with a purity of about 0.99. No local source supports a recovery of 0.85. Pd-based membrane reactors reach more than 99% conversion with 90-97.5% H2 recovery at 400-450 °C and 4-7 bar. However, Pd membranes embrittle below 300 °C and form defects above 550 °C (Cechetto et al., 2023; Maccarrone et al., 2025).

## Process simulation practice

Aspen Plus is used with the Peng-Robinson equation of state (Peng & Robinson, 1976) by Cho et al. (2026) and Richard et al. (2024), and with RKS-BM by Chopra et al. (2026). HYSYS with Peng-Robinson is used by Hansen et al. (2024) and Mehr et al. (2026). Common simplifications are black-box PSA units, ideal component splitters and Gibbs-reactor furnaces (Farokhi et al., 2025; Hansen et al., 2024). Reported H2 yields lie between 0.128 and 0.141 kg H2 per kg NH3 once the NH3 burned as fuel is included (Farokhi et al., 2025; Hansen et al., 2024).

## Techno-economics

The NH3 feedstock dominates the levelised cost of hydrogen (LCOH). Using 2024 USD and NH3 at 450 USD/t, Cho et al. (2026) report 5.44 USD/kg for Ni and 5.29 USD/kg for Ru. The cost of reconversion alone (LCOH minus NH3 feed) is 2.00 and 1.86 USD/kg. Their assumptions are an 8.5% discount rate, a 25-year life, 8000 h/yr and catalyst prices of 33.4 USD/kg for Ni and 542 USD/kg for Ru. Kum et al. (2026) report a most-probable LCOH of 6.44 USD/kg. Farokhi et al. (2025) report 5.1-5.5 USD/kg. Richard et al. (2024) report 5.1 EUR/kg for a fired tubular reactor and 4.45 EUR/kg for a membrane reactor. At refuelling-station scale, Chopra et al. (2026) find 6.84 USD/kg for grey NH3 and up to 17.12 USD/kg for electrolytic NH3, including supply and compression to 350 bar. Ahmad et al. (2025) give a cracker CAPEX correlation, 18.171·(t H2/h)^0.7451 MUSD, derived from data of Cesaro et al. (2021). Several inputs in the corpus trace back to Devkota et al. (2024). Mehr et al. (2026) is internally inconsistent and serves only as context.

## Environmental assessment

Life-cycle results depend mainly on where the NH3 comes from. In a cradle-to-gate assessment for India, Chopra et al. (2026) report 17.91 kg CO2-eq/kg H2 for cracking grey NH3. Solar-PV-based NH3 gives 3.214 and grid-electrolytic NH3 gives 112.79, against 13.48 for SMR. Haber-Bosch synthesis emits 2.0-4.6 t CO2 per t NH3 (Cechetto et al., 2023). With a 0.207 kg CO2/kWh grid factor, the cracker's electricity adds only 0.38 kg CO2/kg H2 (Kum et al., 2026). NOx from burning NH3-rich fuel ranges from 863 to 1517 mg/Nm³ in boiler flue gas (Cho et al., 2026). Cho et al. (2026) cost NOx treatment by selective catalytic reduction (SCR) at 4 USD/kg.

## Commercial technologies

Topsoe offers commercial crackers of 500 t H2/day, and the technology readiness level of NH3 cracking is quoted as 4-6 (Ahmad et al., 2025). Commercial catalysts in the corpus are Ru/Al2O3 (Hypermec 10010; Di Carlo et al., 2014; Kum et al., 2026) and an industrial Ni catalyst of undisclosed composition (Purcel et al., 2025).
