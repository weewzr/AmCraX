<!-- cites: cho2026nickel, kum2026heatintegrated, hansen2024hysys, chopra2026decentralized, mehr2026highcapacity, cechetto2023membrane, yanez2020psa, iso2019hydrogen, richard2024technoeconomic, maccarrone2025comprehensive -->

# 11 Separation and purification

## 11.1 What the PSA block is and is not

Hydrogen is purified in a block named PSA, an Aspen Plus `Sep` component splitter. It sends a specified fraction of each component to H2PROD and the rest to TAILGAS, then flashes each outlet at its pressure: 19.0 bar for the product and 1.3 bar for the tail gas. It is a **reduced-order material balance**: no isotherms, adsorbent, cycle, bed size or purge, and a recovery independent of pressure and feed composition. Its 0.73 kW duty is only the enthalpy change of the outlet flashes. Published flowsheets use the same simplification (Cho et al., 2026; Hansen et al., 2024; Kum et al., 2026); it suffices for a first energy and cost balance but cannot predict purity.

<!-- data: aspen/models/baseline.inp BLOCK PSA (FRAC, FLASH-SPECS); results/simulations/baseline.json blocks.PSA.duty_kW 0.7259 -->

## 11.2 Split fractions and their basis

The fractions to H2PROD are 0.85 for H~2~, 0.001 for N~2~ and 0 for NH~3~, H~2~O and O~2~ (Figure 11.1). The H~2~ recovery of 0.85 is an **engineering assumption** above the 0.71-0.81 range of **published literature**: 75.6 % at 99.11 mol% (Yáñez et al., 2020, as cited in Cho et al., 2026), 80 % (Kum et al., 2026), 71 % at 99 mol% and 79 % in two studies cited by Hansen et al. (2024), and about 81 % from Mehr et al. (2026), whose PSA figures are internally inconsistent. Chopra et al. (2026) give 99 % purity without a recovery. The baseline is therefore optimistic; Section 17 varies the recovery from 0.70 to 0.95. The N~2~ slip of 0.001 is also an assumption.

<!-- data: aspen/models/baseline.inp BLOCK PSA FRACS; research/notes/cho2026nickel, kum2026heatintegrated, hansen2024hysys, chopra2026decentralized, mehr2026highcapacity (reliability_warning: 81 % vs 25 % recovery); aspen/automation/run_sensitivity.py psa_recovery [0.70 ... 0.95] -->

![**Figure 11.1.** PSA (Sep) split fractions to H2PROD: NH~3~ 0, H~2~ 0.85, N~2~ 0.001, H~2~O 0, O~2~ 0. These five numbers fix the product flow, the product purity and the tail-gas fuel; the block is a component splitter, not a designed adsorption unit. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/08_separation_setup.png){width=95%}

## 11.3 Product and tail gas

Table: **Table 11.1.** PSA inlet and outlet streams of the baseline. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json.*

| Stream | Flow (kmol/h) | P (bar) | H~2~ (mol%) | N~2~ (mol%) | NH~3~ (mol%) | H~2~O (mol%) |
|---|---|---|---|---|---|---|
| S7, PSA feed (40 °C) | 197.88 | 19.5 | 74.20 | 24.73 | 0.968 | 0.101 |
| H2PROD | 124.85 | 19.0 | 99.961 | 0.039 | 0 | 0 |
| TAILGAS | 73.03 | 1.3 | 30.16 | 66.95 | 2.62 | 0.27 |

<!-- data: results/simulations/baseline.json streams.S7, streams.H2PROD, streams.TAILGAS (mole_flow_kmol_h, pressure_bar, mole_frac) -->

For the **Aspen Plus V15 simulation** (Table 11.1) the product is 124.80 kmol/h H~2~ (251.6 kg/h) at 99.961 mol% H~2~ with 392 ppm N~2~. The recovery, 124.80 / 146.83 = 0.85, holds by construction, and the overall yield relative to 1.5 mol H~2~ per mol NH~3~ fed is 0.834. **The purity is set by the assumed split, it is not a prediction**: with all NH~3~ and H~2~O sent to the tail gas, the product N~2~ content follows directly from the two fractions. The tail gas carries 22.02 kmol/h H~2~ and 1.915 kmol/h NH~3~, an LHV flow of 1647.98 kW or 4.09 MJ/kg; this low-calorific, N~2~-rich gas fires the burner (Section 10).

<!-- data: results/simulations/baseline.json kpis.h2_product_kmol_h 124.8032, h2_product_kg_h 251.588, h2_purity_mole_frac 0.999608, h2_yield_overall 0.83369, tailgas_lhv_kW 1647.975; streams.H2PROD.mole_frac.N2 3.92e-4; streams.TAILGAS.component_mole_flow_kmol_h; 1647.975 x 3.6 / 1450.29 = 4.09 MJ/kg -->

## 11.4 Product specification

ISO 14687:2019 requires at least 99.97 mol% H~2~, at most 300 ppm N~2~ and at most 0.1 ppm NH~3~ for PEM fuel-cell road vehicles (grade D); stationary applications allow far more N~2~ (ISO, 2019; Cechetto et al., 2023). The baseline product, 99.961 mol% with 392 ppm N~2~, misses both vehicle limits and **is not fuel-cell grade**. The purity-driven case is the **Aspen Plus V15 simulation** `scn_fuel_cell_grade` (N~2~ slip 0.0005, recovery 0.80): 99.979 mol% H~2~ with 208 ppm N~2~ and 236.8 kg/h, 14.8 kg/h less than the baseline. Its purity is again an input consequence; a real PSA would trade slip against recovery.

<!-- data: results/simulations/scn_fuel_cell_grade.json inputs.psa_n2_slip 0.0005, inputs.psa_h2_recovery 0.8, kpis.h2_purity_mole_frac 0.99979171, streams.H2PROD.mole_frac.N2 2.0829e-4, kpis.h2_product_kg_h 236.789; 251.588 - 236.789 = 14.80; research/notes/cechetto2023membrane (ISO 14687:2019 limits) -->

The cracked gas contains 0.968 mol% NH~3~ (9678 ppm); reaching 0.1 ppm requires removing a fraction 0.9999923 of it. The Sep block meets the NH~3~ limit only because its NH~3~ fraction to product is set to zero. **NH~3~ polishing is required and not modelled**: published options are a temperature-swing adsorber on zeolite 4A reaching below 0.1 ppm (Cho et al., 2026; Kum et al., 2026) or adsorption on clinoptilolite (Cechetto et al., 2023). Its regeneration heat and NH~3~ recovery are outside the AmCraX balances.

<!-- data: results/simulations/separation_baseline.json ammonia_slip (nh3_cracked_gas_ppm 9677.98, required_nh3_removal_factor 0.99999233, removal_evidence) -->

## 11.5 Reduced-order PSA and membrane comparison

The **independent Python calculation** `amcrax.separation` applies alternative options to the Aspen PSA feed S7 (146.83 kmol/h H~2~, 19.5 bar); all are reduced-order models and **none is validated** (Table 11.2). The PSA rows apply published operating points as fixed splits; S7 exceeds every reported PSA feed pressure, and each lower recovery sends 493-1381 kW more H~2~ LHV to the tail gas than the baseline. The Pd-Ag membrane follows Sieverts' law, $J = (Pe/\delta)(p_\mathrm{H_2,ret}^{0.5} - p_\mathrm{H_2,perm}^{0.5})$, with $J$ the H~2~ flux (mol/(m^2^ s)), $p$ partial pressures (Pa), $Pe$ = 4.57 × 10^-8^ exp(-9.23 kJ mol^-1^/RT) mol/(m s Pa^0.5^) and $\delta$ = 5.2 µm (Richard et al., 2024, Table 2). It runs at 400 °C (engineering assumption inside the 350-500 °C Pd window; Maccarrone et al., 2025) with 1 bar permeate and infinite selectivity; recompressing the permeate to 19 bar costs 1.63 kWh/kg H~2~ (Cho et al., 2026). At a 5 bar feed the membrane would need about 80 m^2^ for the recovery that 23.6 m^2^ gives at 19.5 bar (Figure 11.2).

<!-- data: results/simulations/separation_baseline.json rows[*], membrane.R0.756.max_recovery_at_pinch 0.9812, psa.*.required_feed_pressure_bar; backend/amcrax/data/separation.yaml (richard_ref53, compression); H2 LHV to tail gas vs amcrax_baseline 1479.44 kW: 1972.59 - 1479.44 = 493.15, 2860.26 - 1479.44 = 1380.82; results/sensitivity/membrane_recovery_vs_area.csv -->

Table: **Table 11.2.** Reduced-order purification options on the baseline cracked gas. *Source: independent Python calculation (results/simulations/separation_baseline.json) with published operating points and permeability as cited; not validated.*

| Option | Basis | H~2~ recovery | H~2~ purity (mol frac.) | Area (m^2^) | Electricity (kWh/kg H~2~) | H~2~ LHV to tail gas or retentate (kW) |
|---|---|---|---|---|---|---|
| PSA, zeolite 5A | Yáñez et al. (2020) via Cho et al. (2026), Table 3 | 0.756 | 0.9911 | - | 0 | 2406.6 |
| PSA, activated carbon | Hansen et al. (2024), Sec. 2 | 0.71 | 0.99 | - | 0 | 2860.3 |
| PSA, lumped | Kum et al. (2026), Sec. 2; purity set to 0.99 | 0.80 | 0.99 | - | 0 | 1972.6 |
| PSA, AmCraX baseline | engineering assumption | 0.85 | 0.99961 | - | 0 | 1479.4 |
| Pd-Ag membrane | Richard et al. (2024), Table 2 | 0.756 | 1 (assumed) | 23.6 | 1.63 | 2406.6 |
| Pd-Ag membrane | as above; pinch-limited maximum 0.981 | 0.90 | 1 (assumed) | 31.1 | 1.63 | 986.3 |

![**Figure 11.2.** Pd-Ag membrane H~2~ recovery versus area for the baseline cracked gas at 400 °C: left, feed pressure 5-30 bar at 1 bar permeate; right, permeate 0.5-4 bar at 19.5 bar feed. The high cracker pressure keeps the membrane small, while a higher permeate pressure lowers the attainable recovery. *Source: independent Python calculation, reduced-order ideal Sieverts model.*](../../results/figures/sep_membrane_recovery_vs_area.png){width=100%}
