<!-- cites: cechetto2021fpt, iso2019hydrogen, cho2026nickel, hansen2024hysys, richard2024technoeconomic, cechetto2023membrane, mehr2026highcapacity, chopra2026decentralized, ahmad2025gtcc -->

# 28 Hydrogen purification

## 28.1 Scope and boundary

This section tests how the purity demanded of the product hydrogen trades against recovery loss, energy and cost, for the cracked-gas stream of the Aspen Plus V15 baseline (Section 5; PSA feed stream S7, 20 bar). Two reduced-order **independent Python** models are used, one for pressure-swing adsorption (PSA) with a temperature-swing adsorption (TSA) guard bed, and one for a Pd-Ag membrane with and without an NH~3~ polishing bed. They are compared on three end uses: industrial 99.9 % hydrogen, ISO 14687 Grade D hydrogen at 350 bar, and an unpurified cracked-gas blend for a gas turbine. Case compositions at 10 and 30 bar are rebuilt from the KPI mole fractions of the stored pressure sweep (water by difference) and are less certain than the 20 bar stream.

The PSA block of the Aspen baseline is a splitter with an assumed recovery of 0.85 and an assumed NH~3~ removal to zero. It is not an adsorption-cycle simulation, and neither is the model used here. Neither model contains isotherms, bed dynamics or pressure drop.

The term "fuel-cell grade" is not used for any stream in this report. A stream is described as meeting ISO 14687:2019 Grade D **within the modelled scope** only if every modelled contaminant (NH~3~, N~2~, H~2~O) and the hydrogen index pass. The unmodelled contaminants (O~2~, Ar, He, CO, CO~2~, total and non-methane hydrocarbons, sulfur compounds, formaldehyde, formic acid, halogenated compounds, particulates) are always returned as not evaluated, and no claim about them is made.

## 28.2 Method

**Specification check.** Grade D (Table 2 of ISO 14687:2019) requires a hydrogen index of 99.97 %, total non-hydrogen gases 300 µmol/mol, and individual limits of which NH~3~ 0.1, N~2~ 300, H~2~O 5, CO 0.2 and CO~2~ 2 µmol/mol are the ones of concern for cracked ammonia. The "industrial 99.9 %" specification uses only the Grade B index (99.90 %) and total (1000 µmol/mol) of Table 4; the per-species rows of Table 4 could not be assigned reliably from the available text and are not applied. The standard was read from a public standards-body consultation reproduction, not from the ISO store (International Organization for Standardization, 2019).

**PSA recovery at a given purity.** Published PSA operating points are few. The relation used holds the tail-gas H~2~ mole fraction $y_\mathrm{t}$ at the value implied by one published point and solves the component balances for the recovery $R$ at the requested product purity $y_\mathrm{p}$ (H~2~ as a fraction of H~2~ plus N~2~; NH~3~ and H~2~O go entirely to the tail):

$$ R = \frac{F_{\mathrm{H_2}} - k\,F_\mathrm{o}}{F_{\mathrm{H_2}}\,(1 - q\,k)}, \qquad q = \frac{1 - y_\mathrm{p}}{y_\mathrm{p}}, \qquad k = \frac{y_\mathrm{t}}{1 - y_\mathrm{t}} \qquad (28.1) $$

where $F_{\mathrm{H_2}}$ (kmol/h) is the H~2~ in the feed, $F_\mathrm{o}$ (kmol/h) the feed flow of all other components, $y_\mathrm{t}$ (–) the tail-gas H~2~ fraction and $R$ (–) the H~2~ recovery. The anchor is Cho et al. (2026, Table 3): $R = 0.756$ at 99.11 mol % H~2~, which gives $y_\mathrm{t}$ = 0.417 on the 20 bar feed. Because $y_\mathrm{t}$ is held constant, Eq. (28.1) is a mass balance only and gives a **lower bound on the purity penalty**: a real bed that must reach a tighter purity purges more or loads less, so its tail H~2~ fraction rises. The relation is flat by construction and is not evidence that the penalty is small. A second, independent anchor is the lowest published point, 0.71 at 99 % purity (activated carbon, 2.5 bar; Hansen et al., 2024, citing Cha et al., 2021), applied outside its purity range as a pessimistic bound.

**Membrane.** Hydrogen flux through the Pd-Ag layer follows Sieverts' law with depletion along the retentate:

$$ J_{\mathrm{H_2}} = \frac{P_{e0}\,\exp\!\left(-E_a/RT\right)}{\delta}\left(p_{\mathrm{H_2,ret}}^{\,0.5} - p_{\mathrm{H_2,perm}}^{\,0.5}\right) \qquad (28.2) $$

where $P_{e0}$ = 4.57 × 10^−8^ mol m^−1^ s^−1^ Pa^−0.5^ is the pre-exponential permeability, $E_a$ = 9.23 kJ/mol the activation energy, $\delta$ = 5.2 µm the layer thickness (Richard et al., 2024, Table 2), $R$ the gas constant, $T$ = 673.15 K the membrane temperature (assumption, inside the 350 to 500 °C Pd window), and $p$ the partial pressures (Pa). The retentate is integrated over area; N~2~ leaks with a linear flux set by a finite ideal H~2~/N~2~ selectivity $\alpha$. The maximum recovery is set by the partial-pressure pinch $y_{\mathrm{H_2,ret}} P_\mathrm{feed} = P_\mathrm{perm}$. Area for a target recovery, and the smallest $\alpha$ that keeps permeate N~2~ at or below a limit, are found by root finding. In Phase 1 no numeric selectivity was available, so the base case uses infinite selectivity and the required value is reported separately (Table 28.3). Phase 2 found a sourced ideal H~2~/N~2~ selectivity of 40,541 to 500,000 for a new Pd-Ag membrane measured with single gases (Cechetto et al., 2021), above the requirement; its caveats are given in Section 36.

**NH~3~.** Without a polishing bed the permeate NH~3~ is taken as 2.9 µmol/mol, the measured value in Cechetto et al. (2023, Table 10). With a clinoptilolite bed it is taken as 0.025 µmol/mol (Cechetto et al., 2023, p. 14). For the PSA routes a TSA bed brings NH~3~ to 0.1 µmol/mol, the Cho et al. (2026, Table 3) outlet value, which is exactly at the Grade D limit and is a design target, not a computed result. TSA regeneration energy is not modelled.

**Cost.** Cost per kg of product H~2~ follows the Section 19 method on the cracker (feed NH~3~, heat, capital, fixed and variable operating cost) plus the purification equipment, delivery compression (30 bar for industrial and turbine use, from Richard et al., 2024; 350 bar for Grade D, from Chopra et al., 2026; ideal-gas compression, ±15 % at 350 bar) and, for the membrane, 6000 EUR/m^2^ with a 3-year life converted at 1.099 USD/EUR (Richard et al., 2024, Table 5). In version 2.0 every cost in this section is on the unified reference scenario of Section 32: the base electricity price is 0.1402 USD/kWh, the base ammonia price 450 USD/t, and the cracker and PSA capital, fixed operating cost, hours and exchange rate come from the reference evaluation. Version 1.0 used 0.084 USD/kWh, the membrane price at parity and the legacy CAPEX of Section 19; those values are superseded for research outputs.

## 28.3 Data and assumptions

Table: **Table 28.1.** Principal purification inputs. *Source: results/research/purification/assumptions.json.*

| Input | Value | Origin | Source |
|---|---|---|---|
| Cracked gas at PSA feed, 20 bar | H~2~ 146.83, N~2~ 48.94, NH~3~ 1.915, H~2~O 0.2 kmol/h | Aspen Plus V15 | stored baseline stream S7 |
| PSA anchor | R 0.756 at 99.11 mol % H~2~ | literature | Cho et al. (2026), Table 3 |
| PSA low-recovery bound | R 0.71 at 99 % | literature | Hansen et al. (2024) |
| TSA NH~3~ outlet | 0.1 µmol/mol | literature (design target) | Cho et al. (2026), Table 3 |
| Pd-Ag permeability | P~e0~, E~a~, δ as in Eq. (28.2) | literature | Richard et al. (2024), Table 2 |
| Selectivity H~2~/N~2~ | infinite (base); sourced ideal 40,541 to 500,000 (Section 36) | assumption; literature | Richard et al. (2024) assume infinite; Cechetto et al. (2021) |
| Permeate NH~3~, raw / polished | 2.9 / 0.025 µmol/mol | literature | Cechetto et al. (2023), Table 10 and p. 14 |
| Membrane cost, life | 6000 EUR/m^2^ (6594 USD/m^2^ at 1.099 USD/EUR), 3 yr; Phase 2 range 7,473 to 15,000 USD/m^2^ and 2 to 5 yr in Section 36 | literature | Richard et al. (2024), Table 5 |
| Delivery pressure | 30 bar (industrial, turbine), 350 bar (Grade D) | literature | Richard et al. (2024); Chopra et al. (2026) |
| Compressor | efficiency 0.75, ratio 3.5 per stage | literature | Cho et al. (2026), Table 2 |
| Operating hours | 8000 h/yr | literature | Cho et al. (2026), Table 4 |

## 28.4 Results

### Specification status at 20 bar

Table: **Table 28.2.** Product quality and cost of the purification configurations on the 20 bar baseline gas. "Grade D, in scope" means the hydrogen index and the modelled contaminants (NH~3~, N~2~, H~2~O) pass; unmodelled contaminants are not evaluated. Cost is per kg of product H~2~ at 450 USD/t NH~3~ and 0.1402 USD/kWh on the unified basis of Section 32, at the delivery pressure of the end use named. *Source: independent Python calculation on Aspen Plus V15 gas; results/research/purification/purification_configurations.csv (case 20bar_baseline).*

| Configuration | Recovery | H~2~ (mol %) | N~2~ (ppm) | NH~3~ (ppm) | Grade D in scope | Industrial 99.9 % cost (USD/kg, 30 bar) | Grade D cost (USD/kg, 350 bar) |
|---|---|---|---|---|---|---|---|
| None (cooled cracked gas) | 1.000 | 74.20 | 247 328 | 9678 | no | 3.784 (turbine blend) | not applicable |
| PSA at the Cho point | 0.756 | 99.11 | 8900 | 0.1 | no | 4.245 | not applicable |
| PSA, 99.91 % (mass balance) | 0.752 | 99.91 | 900 | 0.1 | no | 4.269 | not applicable |
| PSA, 99.975 % (mass balance) | 0.751 | 99.975 | 250 | 0.1 | yes | 4.271 | 4.463 |
| PSA, 99.975 % (R = 0.71) | 0.710 | 99.975 | 250 | 0.1 | yes | 4.518 | 4.710 |
| PSA, AmCraX assumed R = 0.85 | 0.850 | 99.96 | 400 | 0.1 | no | 4.046 | not applicable |
| Pd-Ag, 1 bar permeate, no bed | 0.900 | 99.9997 | 0 | 2.9 | no | {{VAL:purification/purification_study.json#cases/20bar_baseline/configs/[MEM_1bar_raw]/costs/industrial_99.9/usd_per_kg_usable_h2|.3f}} | not applicable |
| Pd-Ag, 1 bar permeate, polishing bed | 0.900 | 99.99999 | 0 | 0.025 | yes (conditional) | {{VAL:purification/purification_study.json#cases/20bar_baseline/configs/[MEM_1bar_polish]/costs/industrial_99.9/usd_per_kg_usable_h2|.3f}} | {{VAL:purification/purification_study.json#cases/20bar_baseline/configs/[MEM_1bar_polish]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2|.3f}} |
| Pd-Ag, 0.1 bar vacuum, polishing bed | 0.900 | 99.99999 | 0 | 0.025 | yes (conditional) | {{VAL:purification/purification_study.json#cases/20bar_baseline/configs/[MEM_vac0.1bar_polish]/costs/industrial_99.9/usd_per_kg_usable_h2|.3f}} | {{VAL:purification/purification_study.json#cases/20bar_baseline/configs/[MEM_vac0.1bar_polish]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2|.3f}} |

<!-- data: results/research/purification/purification_configurations.csv rows case 20bar_baseline, columns h2_recovery, purity_h2, N2_ppm, NH3_ppm, meets_gradeD_in_scope, usd_per_kg_product_h2 for end_use industrial_99.9 and fuel_cell_grade_D (PSA_AMCRAX at Grade D end use is 4.239 and does not pass) -->

The raw cracked gas (74.2 mol % H~2~, 24.7 mol % N~2~, 0.97 mol % NH~3~) fails every grade. It is the only option for the turbine blend, which has no purity specification (3.784 USD/kg at 20 bar, 3.776 at 30 bar and 3.832 at 10 bar). The published PSA point of Cho et al. (2026) reaches 99.11 mol %, which fails both the 99.9 % and Grade D specifications because its N~2~ content is 8900 µmol/mol. The Aspen baseline H~2~PROD stream is not Grade D either: its N~2~ is 392 µmol/mol against the 300 limit (validation item P-ISO-2); it passes the 99.9 % industrial index. Its NH~3~ content is exactly zero because of the splitter assumption.

The conditional rows in Table 28.2 depend on selectivity. An ideal H~2~/N~2~ selectivity of at least 12 919 is needed to keep permeate N~2~ at or below 300 µmol/mol at 90 % recovery and 1 bar permeate pressure, and 3871 for the 1000 µmol/mol total of the 99.9 % specification (Table 28.3). Phase 2 found a sourced ideal selectivity of 40,541 to 500,000 (Cechetto et al., 2021; single gas, new membrane), which exceeds the grade D requirement by 3.1 times at the low value (Section 36). The Pd-Ag reactor measurement of Cechetto et al. (2023) could not be compared, because it is a reactor result with no module area or permeability parameters.

Table: **Table 28.3.** Membrane area and the H~2~/N~2~ selectivity required by the N~2~ limits, 100 kmol/h NH~3~ cracked-gas feed, 20 bar. *Source: independent Python calculation; results/research/purification/membrane_required_selectivity.csv.*

| Permeate (bar) | Recovery | Area (m^2^) | Selectivity for N~2~ 300 ppm | Selectivity for total 1000 ppm |
|---|---|---|---|---|
| 1.0 | 0.80 | 25.6 | 10 575 | 3169 |
| 1.0 | 0.90 | 31.1 | 12 919 | 3871 |
| 1.0 | 0.95 | 35.7 | 15 549 | 4660 |
| 0.1 | 0.80 | 19.8 | 8125 | 2434 |
| 0.1 | 0.90 | 23.5 | 9566 | 2866 |
| 0.1 | 0.95 | 26.0 | 10 848 | 3251 |

### Recovery, purity and cost

The cost of Grade D hydrogen through PSA and TSA rises steeply as the recovery falls (Table 28.4, Figure 28.1), because the feed ammonia dominates and each lost kmol of H~2~ must be made up with more feed. The recovery at 99.975 % is not known: the two anchors differ by 0.04, equal to 0.25 USD/kg.

Table: **Table 28.4.** Cost of Grade D hydrogen (350 bar) against assumed PSA recovery at 99.975 % purity, and against membrane recovery with a polishing bed. *Source: results/research/purification/recovery_vs_cost.csv and sensitivity.csv.*

| Route | Recovery | Cost (USD/kg) |
|---|---|---|
| PSA and TSA | 0.60 | 5.533 |
| PSA and TSA | 0.65 | 5.124 |
| PSA and TSA | 0.70 | 4.774 |
| PSA and TSA | 0.75 | 4.471 |
| PSA and TSA | 0.80 | 4.322 |
| Pd-Ag with bed, 1 bar permeate | 0.80 | 4.474 |
| Pd-Ag with bed, 1 bar permeate | 0.90 | 4.333 |
| Pd-Ag with bed, 1 bar permeate | 0.95 | 4.276 |

<!-- data: results/research/purification/recovery_vs_cost.csv config "PSA+TSA grade D purity 99.975 %" recovery 0.6, 0.65, 0.7, 0.75, 0.8 (5.53259, 5.12416, 4.77408, 4.47067, 4.32213); sensitivity.csv rows "membrane recovery" 0.8 (4.47414), 0.95 (4.27604), base MEM_D 4.33316 (fix pass 24 Nov 2026: membrane annualised with the CRF at its life) -->


![**Figure 28.1.** Hydrogen recovery against product purity for the PSA relation and the Hansen anchor. The mass-balance relation is flat by construction and understates the penalty of tighter purity. *Source: independent Python calculation (results/research/purification/psa_recovery_vs_purity.csv).*](../../results/figures/research/purification_recovery_purity.png){width=85%}

![**Figure 28.2.** Cost of Grade D hydrogen against recovery, PSA and TSA compared with the Pd-Ag membrane with polishing bed. *Source: independent Python calculation (results/research/purification/recovery_vs_cost.csv).*](../../results/figures/research/purification_recovery_cost.png){width=85%}

![**Figure 28.3.** Cost, recovery and specification status of all configurations at 20 bar. *Source: independent Python calculation (results/research/purification/purification_configurations.csv).*](../../results/figures/research/purification_config_comparison.png){width=90%}

### Energy and heat effects

Delivery compression to 30 bar costs 0.22 kWh/kg H~2~ for PSA product and 1.92 kWh/kg for the 1 bar membrane permeate (3.23 kWh/kg at 0.1 bar vacuum); to 350 bar the values are 1.59, 3.33 and 4.63 kWh/kg. Recovery also changes the furnace heat balance. The PSA tail gas returns 1520 kW to the furnace at recovery 0.85 (net heat deficit 773 kW) and 2376 to 2418 kW at recovery 0.75 (no deficit; the surplus is not credited). The membrane retentate returns 1065 kW and leaves a deficit of 1228 kW that must be met with imported fuel. A higher-recovery route therefore saves feed ammonia and loses tail-gas heat. Both effects are in the cost figures above.
<!-- data: results/research/purification/purification_configurations.csv case 20bar_baseline, columns compression_kWh_per_kg, tail_heat_to_furnace_kW, net_heat_deficit_kW (rows PSA_AMCRAX, PSA_D_MB, PSA_CHO, MEM_1bar_*, MEM_vac0.1bar_*; delivery 30 and 350 bar rows) -->

### Sensitivity and Singapore prices

The ammonia price dominates: moving it from 300 to 610 USD/t changes the Grade D cost from 3.317 to 5.686 USD/kg for PSA and TSA, and from 3.376 to 5.354 USD/kg for the membrane with bed, so the order of the two routes reverses within the price range. Recovery assumptions come next. A membrane cost multiplier of 0.5 or 2 changes the membrane route by less than 0.04 USD/kg (4.314 and 4.372 USD/kg); a flux multiplier of 0.15 (concentration polarisation) raises it from 4.333 to 4.552 USD/kg. The membrane is annualised with the capital recovery factor at its life, as the PSA is (corrected on 24 November 2026, Section 31.4). The PSA and TSA capital basis (Cho et al. unit cost instead of the reference items) moves the PSA route from 4.463 to 4.386 USD/kg.
<!-- data: results/research/purification/sensitivity.csv rows "NH3 price (USD/t)" 300 / 610, "membrane cost multiplier", "flux multiplier", "PSA/TSA CAPEX basis" -->

On the unified basis the Singapore electricity price is already the base case, so the separate Singapore price table of version 1.0 is not repeated; the costs at the blue and green ammonia prices are in `results/research/purification/singapore_price_scenario.csv`. Section 36 compares PSA with the membrane over the full factorial of sourced inputs and finds that neither ranking is robust. Hybrids were screened but are not recommended: a membrane on the PSA tail gas could recover up to 0.87 of the tail H~2~ only at 0.1 bar vacuum and would need recompression of the product; a membrane followed by a small PSA is not quantified because no published PSA recovery exists for a ppm-level polishing duty.
<!-- data: results/research/purification/hybrids.json hybrid_psa_tail_membrane.rows[*].pinch_recovery_of_tail_H2 (0.0019, 0.8730, 0.9883 at 0.5, 0.1, 0.01 bar); hybrid_membrane_plus_psa_polish.status -->

## 28.5 Validation status and failures

`results/research/validation/purification.json` had 8 items in Phase 1 (4 pass, 0 fail, 4 informational); Phase 2 added 9 items (Section 36), for 17 items and no failure. The Phase 1 passes are: component and mass closure for all 33 configuration and case combinations (maximum relative error below 10^-9); the Sieverts flux against a hand calculation (1.4646 mol m^-2^ s^-1^ at 673.15 K, 14 bar retentate, 1 bar permeate, relative error below 10^-9); the pinch limit approached at large area (0.98120); and transcription of the ISO limits. The informational items record that the PSA point is reproduced by construction, that the required selectivity can be compared with Cechetto et al. (2023)'s measured 99.995 % permeate purity but not validated against it, that the Cechetto et al. 4 bar, 400 °C membrane-reactor result (99.3 % conversion, 93.5 % recovery) was not reproduced, and that the Aspen baseline stream fails Grade D on N~2~. Nothing here validates the PSA recovery-purity trade-off, which has no independent data in the library beyond the two anchor points; the Mehr et al. (2026) points available are mutually inconsistent and are not used.

## 28.6 Comparison with literature

The PSA recovery of 0.756 at 99.11 mol % (Cho et al., 2026) and 0.71 at 99 % (Hansen et al., 2024) are the only usable literature points. The reported 81 % recovery at 96 % conversion in Deka et al. (2025), quoted in the project brief, could not be checked because the paper is not in the library. The membrane result that Pd-Ag permeates reach very high purity is in line with Cechetto et al. (2023), who report NH~3~ in the permeate from 0.01 to 2.9 µmol/mol; AmCraX agrees on the NH~3~ range because it takes the upper value from that table, so this is an input and not a validation.

## 28.7 Limitations

* The PSA model is a mass-balance relation anchored on two points, not an adsorption simulation; recovery at 99.975 % purity is unknown within 0.71 to 0.751.
* The membrane results are lower bounds: housing, skid, compression CAPEX, TSA regeneration, pressure drop, real-gas behaviour at 350 bar and NH~3~ inhibition of Pd permeation are not modelled.
* The membrane results are conditional on selectivity of order 10^4^; the only sourced value (Cechetto et al., 2021) is an ideal single-gas value for a new membrane.
* Only NH~3~, N~2~ and H~2~O are evaluated; Grade D status is not established for the other contaminants listed in Section 28.1.
* The 10 and 30 bar cases are rebuilt from KPIs, with PSA feed pressure taken as reactor pressure minus 0.5 bar.
* Costs use the unified reference scenario (Section 32); version 1.0 used the legacy CAPEX basis.

## 28.8 Implication for hypothesis H4

Purity and recovery are linked through the NH~3~ and N~2~ limits: the 99.11 mol % PSA point of Cho et al. (2026) fails both 99.9 % and Grade D by N~2~, and meeting Grade D adds a TSA step and, for the membrane, a polishing bed and a selectivity requirement. Each 0.05 step of PSA recovery at 99.975 % moves the Grade D cost by 0.15 to 0.41 USD/kg in the range 0.60 to 0.80 (Table 28.4). What is not established is the size of the recovery penalty for tighter purity, because the library holds two PSA points and the relation used cannot resolve it. The membrane advantage over the Grade D PSA routes ({{VAL:purification/purification_study.json#cases/20bar_baseline/configs/[MEM_1bar_polish]/costs/fuel_cell_grade_D/usd_per_kg_usable_h2|.3f}} against 4.463 and 4.710 USD/kg, Table 28.2) is driven by the assumed recovery (0.90 against 0.71 to 0.85), not by a demonstrated purity advantage; Section 36 shows that the ranking reverses inside the sourced ranges, with parity at a PSA recovery of {{VAL:purification/phase2_comparison.json#specs/fuel_cell_grade_D/thresholds/psa_recovery_at_parity_with_central_membrane|.3f}} (grade D) and {{VAL:purification/phase2_comparison.json#specs/industrial_99.9/thresholds/psa_recovery_at_parity_with_central_membrane|.3f}} (industrial). The verdict on H4 is given in Section 40.
