<!-- cites: cho2026nickel, kum2026heatintegrated, hansen2024hysys, chopra2026decentralized, mehr2026highcapacity, cechetto2023membrane, yanez2020psa, iso2019hydrogen, richard2024technoeconomic, maccarrone2025comprehensive -->

# 12 Separation and purification

## 12.1 What the PSA block represents

Hydrogen is purified in a block named PSA, an Aspen Plus `Sep` component splitter. It sends a specified fraction of each component to H2PROD and the rest to TAILGAS, then flashes each outlet at its pressure: 19 bar for the product (adsorption pressure minus losses) and 1.3 bar for the tail gas (desorption). It is a **reduced-order material balance**: no isotherms, adsorbent, pressure-swing cycle, bed sizing or purge ratio, and no dependence of recovery on pressure or feed composition. Its 0.73 kW duty is only the enthalpy change of the two outlet flashes. Published flowsheets use the same simplification (lumped PSA in Cho et al., 2026, and Kum et al., 2026; ideal splitters in Hansen et al., 2024), which suffices for a first energy and cost balance but not for purity claims.

<!-- data: aspen/models/baseline.inp BLOCK PSA; results/simulations/baseline.json blocks.PSA -->

## 12.2 Split fractions and their basis

The fractions to H2PROD are H~2~ 0.85, N~2~ 0.001 and 0 for NH~3~, H~2~O and O~2~ (Figure 12.1). The H~2~ recovery of 0.85 is an **engineering assumption** above the 0.71-0.81 range of **published literature**: 75.6 % at 99.11 mol% (Yáñez et al., 2020, as cited in Cho et al., 2026), 80 % (Kum et al., 2026), and 71 % at 99 mol% and 79 % in two studies cited by Hansen et al. (2024). Chopra et al. (2026) give 99 % purity without a recovery; the values in Mehr et al. (2026) are internally inconsistent and are not used. The baseline is therefore optimistic; Section 15.5 varies recovery from 0.70 to 0.95. The N~2~ slip of 0.001 is also an assumption.

<!-- data: aspen/models/baseline.inp BLOCK PSA FRACS; aspen/automation/run_sensitivity.py psa_recovery study; research/notes/cho2026nickel.md, kum2026heatintegrated.md, hansen2024hysys.md, chopra2026decentralized.md, mehr2026highcapacity.md -->

![**Figure 12.1.** PSA (Sep) split fractions to the H2PROD outlet. The H~2~ recovery and N~2~ slip fix the product and tail-gas flows and the product purity; the block is a reduced-order splitter, not a designed PSA. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/08_separation_setup.png){width=95%}

## 12.3 Product and tail gas

Table: **Table 12.1.** PSA inlet and outlet streams of the baseline. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json.*

| Stream | Flow (kmol/h) | P (bar) | H~2~ (mol%) | N~2~ (mol%) | NH~3~ (mol%) | H~2~O (mol%) |
|---|---|---|---|---|---|---|
| S7, PSA feed (40 °C) | 197.88 | 19.5 | 74.20 | 24.73 | 0.968 | 0.101 |
| H2PROD | 124.85 | 19.0 | 99.961 | 0.039 | 0 | 0 |
| TAILGAS | 73.03 | 1.3 | 30.16 | 66.95 | 2.62 | 0.27 |

<!-- data: results/simulations/baseline.json streams.S7, streams.H2PROD, streams.TAILGAS; kpis.h2_product_kmol_h, kpis.h2_product_kg_h, kpis.h2_purity_mole_frac, kpis.h2_yield_overall, kpis.tailgas_lhv_kW -->

The **Aspen Plus V15 simulation** gives 124.80 kmol/h H~2~ (251.6 kg/h) at 99.961 mol% (392 ppm N~2~); recovery is 124.80 / 146.83 = 0.85 by construction and the overall yield relative to 1.5 mol H~2~ per mol NH~3~ fed is 0.834. Purity is not a design result: it follows from the two assumed fractions. The tail gas carries 22.02 kmol/h H~2~ and 1.915 kmol/h NH~3~, an LHV flow of 1647.98 kW or about 4.09 MJ/kg (1647.98 × 3.6 / 1450.29 kg/h); this low-calorific, N~2~-rich gas fires the burner (Section 11.4).

## 12.4 Product specification: nitrogen and residual ammonia

ISO 14687:2019 (International Organization for Standardization, 2019) sets, for PEM fuel-cell vehicles, at least 99.97 % H~2~, at most 300 ppm N~2~ and 0.1 ppm NH~3~; stationary use allows up to 50 % N~2~ (as quoted by Cechetto et al., 2023, who also conclude that an NH~3~ removal unit is always required). The baseline product, 99.961 mol% with 392 ppm N~2~, is **below the fuel-cell limits and must not be called fuel-cell grade**; it meets the stationary N~2~ limit. The purity-driven case is the **Aspen Plus V15 simulation** `scn_fuel_cell_grade` (N~2~ slip 0.0005, recovery 0.80): 99.979 mol% H~2~ with 208 ppm N~2~ and 236.8 kg/h product, at the cost of 14.8 kg/h less H~2~ than the baseline. In a real PSA a lower slip would also lower recovery; the splitter imposes both independently. The scenario is compared with the others in Section 18.

<!-- data: research/notes/cechetto2023membrane.md (ISO 14687:2019, p. 5: N2 300 ppm vehicle, 50 % stationary; NH3 0.1 ppm); results/simulations/baseline.json streams.H2PROD.mole_frac.N2; results/simulations/scn_fuel_cell_grade.json streams.H2PROD.mole_frac (H2 0.99979171, N2 0.00020829), kpis.h2_product_kg_h 236.789; 251.6 - 236.8 = 14.8 -->

The cracked gas contains 0.968 mol% NH~3~ (about 9678 ppm); reaching 0.1 ppm requires removing a fraction 0.9999923 of it. The Sep block meets the NH~3~ limit only because its NH~3~ fraction to product is set to zero. A real plant needs a polishing step, e.g. a temperature-swing adsorber on zeolite 4A reaching below 0.1 ppm (Cho et al., 2026; Kum et al., 2026) or water absorption (Cechetto et al., 2023). This step, its regeneration heat and its NH~3~ recovery are **not modelled**.

<!-- data: results/simulations/baseline.json streams.S7.mole_frac.NH3; results/simulations/separation_baseline.json ammonia_slip; research/notes/cho2026nickel.md (TSA) -->

## 12.5 Reduced-order PSA and membrane comparison

The **independent Python calculation** `amcrax.separation` applies alternative purification options to the Aspen PSA feed (S7: 146.83 kmol/h H~2~, 19.5 bar). All are **reduced-order models, none validated** against a designed unit (Table 12.2).

*PSA.* **Published literature** operating points are applied as fixed splits: 75.6 % at 99.11 mol% and 7 bar on zeolite 5A (Yáñez et al., 2020, as cited in Cho et al., 2026), 71 % at 99 mol% and 2.5 bar on activated carbon (Hansen et al., 2024) and 80 % (Kum et al., 2026). S7 exceeds all reported feed pressures, so no compression is needed; each lower recovery sends 493-1381 kW more H~2~ LHV to the tail gas than the baseline.

*Pd-Ag membrane.* Hydrogen flux follows Sieverts' law, $J = (Pe/\delta)(p_\mathrm{H_2,ret}^{0.5} - p_\mathrm{H_2,perm}^{0.5})$, where $J$ is the H~2~ flux (mol/(m^2^ s)), $p$ partial pressures (Pa), $Pe$ = 4.57 × 10^−8^ exp(−9.23 kJ mol^−1^/RT) mol/(m s Pa^0.5^) and $\delta$ = 5.2 µm (Richard et al., 2024, Table 2); isothermal at 400 °C (**engineering assumption** within the 350-500 °C Pd window; Maccarrone et al., 2025), 19.5 bar feed, 1 bar permeate, infinite selectivity. Matching 0.756 recovery needs 23.6 m^2^ and 0.90 needs 31.1 m^2^ (Figure 12.2), with a pinch-limited maximum of 0.981. Recompressing the 1 bar permeate to 19 bar costs 1.63 kWh/kg H~2~ (isentropic efficiency 0.75, pressure ratio at most 3.5 per stage; Cho et al., 2026, Table 2).

<!-- data: results/simulations/separation_baseline.json rows[*] (h2_recovery, h2_purity_mole_frac, membrane_area_m2, energy_kWh_per_kgH2_incl_product_recompression, h2_loss_lhv_kW), psa.*.required_feed_pressure_bar, membrane.R0.9.max_recovery_at_pinch, ammonia_slip; backend/amcrax/data/separation.yaml; H2 LHV differences vs amcrax_baseline 1479.44 kW: 1972.59-1479.44 = 493.15, 2860.26-1479.44 = 1380.82 -->

Table: **Table 12.2.** Reduced-order purification options on the baseline cracked gas. *Source: independent Python calculation (results/simulations/separation_baseline.json) with published operating points and permeability as cited; not validated.*

| Option | Basis | H~2~ recovery | H~2~ purity (mol frac.) | Membrane area (m^2^) | Electricity (kWh/kg H~2~) | H~2~ LHV to tail gas / retentate (kW) |
|---|---|---|---|---|---|---|
| PSA, zeolite 5A | Yáñez et al. (2020) via Cho et al. (2026), Table 3 | 0.756 | 0.9911 | - | 0 | 2406.6 |
| PSA, activated carbon | Hansen et al. (2024), Sec. 2 | 0.71 | 0.99 | - | 0 | 2860.3 |
| PSA, lumped | Kum et al. (2026), Sec. 2; purity set to 0.99 spec | 0.80 | 0.99 | - | 0 | 1972.6 |
| PSA, AmCraX baseline | engineering assumption | 0.85 | 0.99961 | - | 0 | 1479.4 |
| Pd-Ag membrane | Richard et al. (2024), Table 2 | 0.756 | 1 (assumed) | 23.6 | 1.63 | 2406.6 |
| Pd-Ag membrane | as above | 0.90 | 1 (assumed) | 31.1 | 1.63 | 986.3 |

![**Figure 12.2.** Pd-Ag membrane H~2~ recovery versus area for the baseline cracked gas at 400 °C: left, feed pressure 5-30 bar at 1 bar permeate; right, permeate 0.5-4 bar at 19.5 bar feed. The 19.5 bar S7 pressure keeps the area near 30 m^2^ for 0.9 recovery, whereas a 5 bar feed would need about 80 m^2^ for 0.76. *Source: independent Python calculation, reduced-order ideal Sieverts model.*](../../results/figures/sep_membrane_recovery_vs_area.png){width=100%}
