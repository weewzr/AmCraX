# Research expansion: validation and limitations

> **Phase 2 update (23 November 2026; fix pass 24 November 2026).** This report describes the research expansion of the Phase 1 release. Phase 2 changes the following, and the Phase 2 documents win where they differ:
>
> - Economics use one reference scenario (4.015 USD/kg, 5.174 SGD/kg). The stored LCOH of 3.918842 USD/kg in section 3.4 is the legacy correlation of the core model and is superseded for research outputs. The Phase 1 equipment-method value of 3.61 USD/kg is also superseded.
> - Verdicts follow the rule of [verdict_methodology_v2.md](verdict_methodology_v2.md): H1 INCONCLUSIVE, H2 MIXED, H3 PARTIALLY SUPPORTED (resting only on H3-T; H3-H and H3-K INCONCLUSIVE), H4 INCONCLUSIVE, each shown with the version 1 verdict (all INCONCLUSIVE, rule v1). An independent adversarial review moved rows H2-b, H3-d and H4-e to INCONCLUSIVE. The evidence matrix has the rows.
> - Validation is described by four evidence kinds: numerical verification, Python against Aspen comparison, comparison with published literature, and independent experimental validation, of which AmCraX has none. Every Phase 2 validation item carries its kind. No single percentage summarises them. Counts below are counts of items in files, not measures of accuracy. The table in section 1 gives the Phase 1 counts. The current counts (24 November 2026, `results/research/validation/summary.json`) are 705 items: 609 pass, 12 fail, 83 informational, 1 not available; by kind, numerical verification 466 (442 pass, 5 fail, 19 informational), Python against Aspen comparison 183 (156, 5, 22), comparison with published literature 55 (11, 2, 42), and independent experimental validation none (one placeholder item, not available).
> - Changed findings: the five feed-effluent exchanger failures are traced to the vaporiser dew-point state (8.8 kW) and the ammonia residual enthalpy (12.1 kW) and still fail with the tolerance unchanged; the above-equilibrium Aspen failures are quantified and the 20 bar cases now pass in the partial-pressure form (40 bar still fails); the Phase 1 "17 % lower fired duty" is withdrawn (at most 25 kW at equal conversion, 4.9 % of the fired duty and 1.1 % of total external heating); catalyst prices are derived from metal content.
> - Section 3.4 keeps the Phase 1 economics (REC 0.573 USD/kg, FX 1.290, scale effect 3.90 to 3.46 USD/kg); the unified values are REC 0.975 USD/kg and FX 1.288444.
> - Limitations by area and the ranked next steps: [limitations_and_future_work.md](limitations_and_future_work.md).

This report covers the Singapore-specific hypothesis tests added to AmCraX (hypotheses H1 to H4; see [README.md](README.md)). It states, for each workstream, what was validated and against what, what is preliminary, what is assumed, what failed and why, the effect on the conclusions, and the corrective action. Verdicts are not repeated here: they are held in [evidence_matrix.md](evidence_matrix.md) (generated from `results/research/evidence_matrix.json`), which is the only place they should be read from.

Counts are read from `results/research/validation/summary.json`, produced by `scripts/research/build_research_validation.py` from the per-workstream files in `results/research/validation/`. This is separate from the core validation matrix (`results/validation/validation_matrix.json`), which is unchanged. The full list of failures, with observed value, expected value, tolerance and recorded cause, is in [../validation/research_validation.md](../validation/research_validation.md).

## 1. Summary of validation status (Phase 1 release, 23 November 2026)

| Workstream | File | Pass | Fail | Informational |
|---|---|---|---|---|
| Kinetics | `kinetics.json` | 8 | 2 | 3 |
| Aspen kinetic RPlug | `aspen_kinetic.json` | 161 | 3 | 19 |
| Catalyst comparison and heat integration | `catalyst_comparison.json` | 66 | 5 | 4 |
| Singapore techno-economics | `economics.json` | 9 | 0 | 6 |
| Purification | `purification.json` | 4 | 0 | 4 |
| End use | `enduse.json` | 40 | 0 | 5 |
| Life-cycle assessment | `lca.json` | 7 | 0 | 4 |
| **Total** | `summary.json` | 295 | 10 | 45 |

Two of the 10 failures (`EXISTING-KIN-NI-PRED`, `EXISTING-KIN-RU-PRED`) are copies of core-matrix rows (`KIN-NI-PRED`, `KIN-RU-PRED`) listed for context by the kinetics workstream and not re-run. Excluding the four mirrored rows (two fail, one pass, one informational), the research items number 346: 294 pass, 8 fail, 44 informational (`totals_excluding_items_mirrored_from_core_matrix`).

A pass here means the stated check was met. It does not mean the underlying physical claim is established: several passes are consistency checks against the data used to fit the model (flagged below), and informational items are not passes.

## 2. Aspen Plus runs

`results/research/aspen_kinetic/run_status.json` lists 162 new Aspen Plus V15 runs, all with status `ok` (kv 12, kl 2, ki 2, cv 34, cs 102, ci 10 by case-id prefix): 12 integrated-flowsheet runs (`ki_`, `ci_`) and 150 standalone RPLUG runs. No run failed. The existing results (`results/simulations`, `results/sensitivity`, `results/optimisation`, `results/validation`) were not regenerated.

Aspen Plus was not run during integration and documentation; all Aspen numbers are read from the stored files.

## 3. Per workstream

### 3.1 Kinetics (`results/research/kinetics`, validation `kinetics.json`)

Validated:
- Two Lucentini et al. (2021) Ni-Ru/CeO2 LHHW laws reproduce the paper's Table 1 conversions (5Ni1Ru/CeO2 RMSE 0.0228, 2.5Ni0.5Ru/CeO2 RMSE 0.0183; items `KINR-LUC-*`). These points are part of the data the law was fitted to, so this is a consistency check and not independent validation.
- The Aspen-form expressions (native LHHW and power law) reproduce the Python rates (`KINR-ASPENFORM-*`, all pass).

Preliminary:
- The Takahashi Ni/MgO and Ru/MgO laws cannot be written as a native Aspen reaction (they need a coverage solve). A fitted LHHW approximation is used instead (`KINR-ASPENAPPROX-*`, pass as "approximation fitted by AmCraX", max relative rate error 0.48 and 0.53). It is a Python fit, not a literature law, and is valid at 20 bar only. Results for these two catalysts carry that label.

Failed:
- `EXISTING-KIN-NI-PRED` (observed 0.1096 against tolerance 0.05) and `EXISTING-KIN-RU-PRED` (0.1113 against 0.05). Recorded cause: catalyst mass and W/F are not reported by Takahashi and Fujitani (inferred from one anchor point), and the published curves were read from figures. Not resolved.

Not modelled and not verifiable here (stated plainly because these were the priority catalysts):
- **Ni/CeO2 and Ru/CeO2 (Lucentini et al., 2019)**: the paper reports conversions only (Ru/CeO2 98 % and Ni/CeO2 63 % at 450 degC are confirmed in the text, `KINR-LIT-LUC2019`) and gives no rate law, activation energy, orders or pre-exponential factor. No rate law is available, so these catalysts are NOT modelled. No parameter was derived from the conversion points.
- **Ru-K/CaO (Sayas et al., 2020)**: the main text was read in full on 24 November 2026. The essay values (Ea 96 to 75 kJ/mol, H2 order -1.9 against -1.2, about 80 % at 40 bar) are confirmed at 350 degC and 1 atm (Table 4); the 111 kJ/mol carried from a review is not in the main text, and the claimed 40-fold productivity at pressure comes from multiplying rates by pressure. The rate constant and equilibrium term are in the supplementary information, not obtained, so no law is implemented or fitted (`KINR-LIT-SAYAS2020`, informational). The 15 measured conversions at 10 to 40 bar are stored as unused comparison points (`K1P2-SAYAS-POINTS`); at 20 bar and 500 degC the catalyst reaches about 68 % where the Ru/Al2O3 law gives about 95 % at equal Ru per mol NH3, a cross-catalyst context, not a test (`K1P2-SAYAS-RUAL2O3-CONTEXT`).
- Ni/Al2O3 (Collins 1993, used by Cho et al.) sits in an unavailable supplement; Co-based catalysts were not searched.
- The combined consequence is that the catalyst set actually modelled is: Ru/Al2O3 (Kum), 5Ni1Ru/CeO2 and 2.5Ni0.5Ru/CeO2 (Lucentini 2021), and Ni/MgO and Ru/MgO (Takahashi approximation).

Extrapolation: Takahashi and Lucentini laws were fitted at 1 atm and Kum below 10 bar and 723 K. Every result at 20 bar (and at 600 degC for Kum) is an extrapolation (`within_fitted_range` flag in the study files). Lucentini's H2 inhibition is concentration based, so its rate falls strongly at 20 bar. The reported Ek confidence interval moves X at 450 degC from 0.42 to 0.995 (`kinetics.md` hand-back; per-catalyst validation JSON), which overstates the uncertainty because k0 and Ek are correlated and no covariance is published, but shows the rate level is poorly constrained. A flow reference at 25 degC instead of 0 degC changes X by up to 0.03.

Effectiveness factor is taken as 1 and pressure drop is neglected in the study files, so catalyst masses are lower bounds.

Recommended action: obtain the Sayas 2020 supplementary information and the Cho 2026 supplement; measure or find rate data at 10 to 20 bar; supply W/F for Takahashi from the original data.

### 3.2 Aspen RPlug (`results/research/aspen_kinetic`, validation `aspen_kinetic.json`)

Validated: native laws agree with the Python PFR (largest |dX| 0.0007 for Kum and 0.0003 for Lucentini in isothermal runs), duties agree within 2 %, adiabatic outlet temperatures within 2 K, and all 10 integrated catalyst cases converge. The integrated 600 degC case reproduces the stored RGibbs baseline conversion within 0.0004.

Failed (3): `cat_nire_ceo2_5ni1ru_lucentini_lhhw_below_equilibrium` (observed 4.87e-4), `cat_nire_ceo2_2p5ni0p5ru_lucentini_lhhw_below_equilibrium` (4.87e-4) and `cat_ru_takahashi_microkinetic_below_equilibrium` (1.60e-4), each against a tolerance of 1e-4. Some LHHW runs sit slightly above the PENG-ROB RGibbs equilibrium of the same model. Recorded cause: the LHHW reverse term uses the ideal-gas equilibrium constant of the kinetics spec on a concentration basis, whereas RGibbs uses fugacities; the excess is largest at 40 bar. Nothing was tuned. The Python PFR at the same conditions agrees within the conversion tolerance. Impact: conversions at 40 bar are slightly optimistic by up to about 5e-4, negligible against the other uncertainties, but the strict check fails and is kept as a failure. Action: use a fugacity-based equilibrium constant in the LHHW reverse term.

Preliminary and assumed:
- A small H2 seed (1e-3 of the NH3 in standalone cases; 1e-4 in integrated cases through a separate `H2SEED` stream) is needed because the rate is infinite at zero H2. This is a numerical device.
- In integrated cases the RPLUG cracker outlet sits at the heater outlet pressure (20.2 bar) instead of exactly 20 bar as in the RGibbs baseline, and the Takahashi approximation assumes 20 bar.
- The Kum equilibrium constant polynomial has a T^3 term that the native form cannot hold exactly; Aspen computes Keq from Gibbs energies.
- A native Aspen sensitivity block is not available with the kinetic cracker; temperature and mass studies are individual runs.
- The adiabatic case still reports a phase-stability warning at block level.
- The 500 degC and 600 degC cases are above the Kum fitted range; they verify the tooling and are not catalyst evidence.

Screenshots: see section 5.

### 3.3 Catalyst comparison and heat integration (`results/research/catalyst_comparison`, validation `catalyst_comparison.json`)

Validated: pinch baseline 752.63 kW against 752.6 kW (`HCAT-PINCH-BASELINE`); mass and energy closure for every configuration; analytic catalyst-cost addition against the full economics evaluation to 1e-9; Python against Aspen within 3 % for total external heating and tail-gas heat.

Failed (5): `HCAT-ASPY-{Ru/Al2O3, 5Ni1Ru/CeO2, 2.5Ni0.5Ru/CeO2, Ni/MgO, Ru/MgO}-HI-heat`. The Python recovered heat in the FEHE exceeds the Aspen value by 20.8 to 20.9 kW (3.45 to 4.44 %) against a tolerance of 3 %. Recorded cause: a systematic property-basis difference in the FEHE, the same offset for every catalyst (the same class of difference as the core `FS-<case>` items, which are 3 to 10 %). Because it is the same offset for every catalyst, comparisons between catalysts are affected less than absolute duties. Action: replace the Python FEHE property basis with the Aspen PENG-ROB basis, or report Aspen duties only.

Preliminary and assumed:
- Furnace efficiency (0.85) and a 2 % thermal-loss allowance are assumptions.
- Catalyst prices are proxies: Cho et al. (2026) Ni 33.4 and Ru 542 USD/kg with a 2-year life. No sourced price exists for NiRu/CeO2, so 542 is an upper bound and a break-even price is reported instead. Ru price multipliers of 4 and 8 are stress values, not prices.
- The CAPEX module does not respond to reactor volume, exchanger area or temperature. Volume scaling is a sensitivity only. The economics model therefore cannot show a CAPEX advantage or penalty of operating temperature, which is where Cho et al. place the Ru advantage (boiler, exchangers, NOx treatment). This is the CAPEX insensitivity limitation.
- Python optimum-temperature rows have no Aspen run at the optimum; only the `ci_*` operating points are Aspen results.
- Effectiveness factor 1, no pressure drop; N2O not quantified; exchanger U of 50 W/(m2 K) is an assumption.
- The cost-optimal temperature is flat (within 0.001 USD/kg over a 40 to 65 K band), and the ranking of catalysts changes in 11 of 32 sensitivity cases (`catalyst_ranking_robustness.json`). Differences between catalyst LCOH values are below the resolution of the model.
- At 99 % conversion and 20 bar every catalyst is equilibrium-limited (about 685 degC or higher, `study_temperature_for_target_conversion.json`), so catalyst activity cannot lower the temperature for that target.
- The comparison with Cho et al. is a rebuild on AmCraX boundaries, not a reproduction: Cho includes 180 bar compression, H2 recycle, TSA and an expander that AmCraX does not have.

### 3.4 Singapore techno-economics (`results/research/singapore`, validation `economics.json`)

Validated: the stored LCOH 3.918842 USD/kg is reproduced exactly in the legacy CAPEX mode (to 1e-9); cost-share closure, unit consistency, REC definition and break-even consistency pass; NH3 feed per kg H2 stays above the stoichiometric floor; the Cho Ru REC difference (7.0 % lower) is recomputed from Cho's own numbers as a check on the input data (E09; informational since the final verification, because it is a literature consistency check, not validation).

Preliminary: the equipment-level CAPEX is a screening estimate scaled from one published purchased-equipment-cost point (Farokhi) with Chopra shares and a TCI/PEC factor, not built from per-equipment correlations. AmCraX REC (0.975 USD/kg on the unified basis; 0.573 in Phase 1, `baseline.json`) is far below Cho's 1.86 to 2.00; the difference is a boundary difference (Cho includes compression, TSA, SCR, OSBL, contingency and a smaller plant) and the AmCraX figure is probably optimistic. In Phase 1, the scale effect (3.90 to 3.46 USD/kg from 25 to 1000 kmol/h) is much weaker than the 5.21 to 3.58 quoted from Deka et al.; the Deka primary paper was not found, so this is informational.

Assumed or secondary: electricity (0.140 USD/kWh) is derived, not an official industrial price; the blue ammonia price and several hydrogen benchmarks come from search-result text because the source pages returned HTTP 403 or no text (`source_type secondary_web`); the exchange rate is 1.288444 SGD per USD, the cross rate of the ECB reference rates of 20 November 2026, read at the source, and the Phase 1 value 1.290 (ADB) is kept only as a cross-check; no Singapore gas price, WACC, labour rate or location factor was found; N2O is a covered gas under the carbon tax but not quantified. Cost base is mixed 2024 to 2026 nominal USD with no escalation. Landed cost is not computed (no sourced transport cost). Product compression and storage and NOx treatment are excluded. Heat-exchanger capital does not respond to heat integration, so heat integration acts only through fuel and cooling.

Halim, Zain and Khoo (2025): read in full on 24 November 2026; the 60.1 MW, 15.1 and 10.1 USD/kg values are in the paper (pp. 3, 9, 11) and are not used as inputs.

Impact: feed ammonia dominates the LCOH in this model (`scenario_results.json`, breakdown), so conclusions about the price of ammonia are robust to the CAPEX uncertainty, while conclusions that depend on CAPEX (catalyst, purification equipment, scale) are not.

### 3.5 Purification (`results/research/purification`, validation `purification.json`)

Validated: component and mass closure for all 33 configuration and case combinations (relative error below 1e-9); the Sieverts hand calculation; the membrane pinch limit; transcription of the ISO 14687:2019 limits (read from a standards-body reproduction, not the ISO store).

Preliminary:
- Only two usable PSA recovery-purity points exist (Cho 0.756 at 99.11 %, Hansen 0.71 at 99 %); the Mehr 2026 points are mutually inconsistent. The mass-balance relation is flat by construction and is not evidence of a small penalty. No adsorption-cycle simulation was done.
- Recovery at Grade D purity is bounded (0.751 optimistic, 0.71 lowest published point applied outside its range), not computed.
- Membrane results use Sieverts parameters from one source (Richard 2024), in Phase 1 an infinite H2/N2 selectivity in the base case and an EUR membrane cost applied as USD at parity (Phase 2: ideal selectivity 40,541 to 500,000 sourced against a requirement of 12,919, and 7,473 USD/m2, that is 6,800 EUR at 1.099 USD/EUR, annualised with the capital recovery factor over the membrane life), and no NH3 inhibition. Housing, skid, compression CAPEX, TSA regeneration energy and pressure drop are not modelled, so membrane costs are lower bounds.
- The 10 and 30 bar compositions are rebuilt from KPI mole fractions, not stored stream tables.
- TSA NH3 removal to 0.1 ppm is a design target at the limit, not a computed result.

Informational findings recorded in `purification.json`: the Aspen baseline H2PROD stream contains about 392 ppm N2, above the Grade D limit of 300 ppm (`P-ISO-2`); the baseline is therefore not called fuel-cell grade anywhere. The Aspen splitter sets NH3 to exactly zero by assumption. Only the index, the total, NH3, N2 and H2O are evaluated; other ISO 14687 contaminants are listed as not evaluated, so no purity claim covers every contaminant.

The Cechetto et al. (2023) membrane reactor comparison (4 bar, 400 degC) was not done: it is a reactor result and the library has no module area or Sieverts parameters for that membrane.

Failed: none.

### 3.6 End use (`results/research/enduse`, validation `enduse.json`)

Validated: the Ahmad bypass table is matched by stoichiometry; atom balances and blend round trip; energy balance for every power pathway; the Aspen LHV efficiency 0.877 within 0.005; the stored LCOH; Ahmad Case 2a LCOE (0.2798 USD/kWh) within 1 %.

Preliminary and assumed: turbine efficiencies are literature calibrated from Ahmad (direct 49.6 %, exhaust-heated full cracking 54.6 %); the efficiency of intermediate blends is a linear interpolation between those end points; the fired-variant efficiency applies the direct-NH3 turbine efficiency to H2-rich fuel; the natural gas CCGT comparator efficiency (0.55) is an assumption. No combustion was simulated and the 30 to 60 vol% blend range is labelled unverified. NOx abatement cost is not included. Partial-cracking heat is the stored Aspen duty scaled linearly with cracked share at 600 degC and 20 bar. The new package is not wired into the API or frontend.

Informational: the Halim 40 % claim (not reproduced in the cost of electricity; the paper's own 39 to 44 % is a fuel-cost comparison, on which AmCraX gives 20 to 33 %, item `EU-P2-halim-fuel-basis`; the reconciliation passes, `EU-P2-halim-reconcile`), Halim plant numbers, ISO purity, Ahmad full-crack TCI (212 against 230 MUSD).

### 3.7 Life-cycle assessment (`results/research/lca`, validation `lca.json`)

Validated: the Lee et al. blue-ammonia intensities (1.16 and 0.77 kg CO2e/kg NH3) are reproduced exactly; the existing environmental baseline carbon intensity is reproduced for grey, blue and green; cost breakdown sums; NH3 per kg H2.

Weak or secondary sources (flagged low confidence in `assumptions.json`): coal ammonia (abstract-level extract), SMR with CCS (search extracts), methane leakage scenario values (0.2, 1.5, 3 %), the CH4 GWP of 29.8 (the IPCC PDF returned HTTP 403), IEA highlights only. Route distances are scenario parameters (5000 km baseline, 2000 to 12000 km range) because no sea-distance source was reachable; boil-off is a parameter defaulting to zero; NOx and N2O factors come from simulated ppmv in Ahmad with an assumed exhaust-basis conversion; N2O is the only direct in-scope emission and is reported but small. The Monte Carlo draws are uniform over stated ranges and are not probability statements about the real world.

## 4. Cross-cutting limitations

- **Inaccessible sources**: Sayas et al. (2020) supplementary information (the main text and Halim, Zain and Khoo (2025) and Abdoos et al. (2025) were read in full on 24 November 2026); Deka et al. (2025) primary paper; Cho et al. (2026) supplementary information (Collins and Sayas kinetics); several S&P Global and EMA pages. Values in the essay that depend on them are marked unverified in the workstream files and the evidence matrix, not confirmed.
- **Extrapolation from 1 atm to 20 bar**: all three kinetic families are used outside their fitted pressure. Conversions at 20 bar for catalysts other than Kum are therefore less certain than the agreement between Aspen and Python (which share the same rate law) suggests. Aspen agreeing with Python verifies the implementation, not the rate law.
- **CAPEX insensitivity**: the CAPEX module does not respond to temperature, pressure, reactor volume or heat-exchanger area. Any conclusion that depends on those capital effects is untested by this model.
- **Proxies**: catalyst prices (Cho Ni and Ru used for all catalysts), Takahashi approximation for Ni/MgO and Ru/MgO, the 5000 km shipping distance, the 0.85 furnace efficiency and the Cho-based catalyst lifetime.
- **Boundary differences with the literature**: AmCraX has no 180 bar compression, H2 recycle, TSA, NOx SCR or expander, so absolute comparison with Cho et al. is not like for like.
- **Separate validation scopes**: the research items verify implementation and internal consistency; few are comparisons against independent experimental data at 20 bar. The core matrix (105 pass, 22 fail, 10 informational of 137, read from `results/validation/validation_matrix.json`) is a different set of checks.

## 5. Screenshot inspection

All 31 PNGs in `docs/images/aspen_evidence` were opened and inspected on 23 November 2026. Each is a capture of the Aspen Plus V15 window only; the title bar shows only the model file name; no user name, host name, e-mail, licence owner or user-folder path is visible (the run-status forms show the user name and host computer fields masked and the site ID blank). 30 passed at the first inspection and one failed. The failed capture was recaptured in Aspen Plus the same day and then passed, so all 31 are now marked `publish: true` in `manifest.json`:

- `ci_luc5_T572_P20_W100_hi__08_reactor_results.png`: the first capture showed the CRACKER Setup > Catalyst tab instead of the results (the Results node was selected in the tree but the Catalyst tab stayed displayed). The capture script now selects the Summary tab explicitly. The recapture shows CRACKER (RPlug) Results > Summary with a heat duty of 1430.87 kW at 572 degC, which matches `results/research/aspen_kinetic/ci_luc5_T572_P20_W100_hi.json` (1430.865 kW). No image was edited.

Two captions describe the reaction stoichiometry as 2 NH3 -> N2 + 3 H2 for LHHW cases, while Aspen displays it per mole of NH3 (NH3 -> 0.5 N2 + 1.5 H2); the reaction is the same and both are marked verified with a note in the manifest. Per-file notes are in `inspection_note` in the manifest. Not every form was captured for every case (for example the LHHW driving-force and adsorption pop-ups, and any native sensitivity block, which is unavailable with the kinetic cracker).

## 6. Corrective actions in priority order

1. Obtain the Sayas 2020 supplementary information and the Cho 2026 supplement so that Ru-K/CaO and Ni/Al2O3 can be modelled; until then those catalysts stay out.
2. Obtain high-pressure (10 to 20 bar) rate data for the modelled catalysts, or flag all 20 bar conversions as extrapolations in any publication.
3. Make CAPEX respond to temperature, reactor volume and exchanger area, then repeat the catalyst comparison.
4. Add PSA purity-recovery data or an adsorption-cycle model for the purification trade-off.
5. Replace the Python FEHE property basis (or publish Aspen duties only) to clear the five catalyst-comparison failures.
6. Use a fugacity-based equilibrium constant in the LHHW reverse term to clear the three below-equilibrium failures.
