<!-- cites: nist_janaf, smith_grimech30, goodwin2018cantera, bell2014coolprop, cechetto2023membrane, xu2025review, maccarrone2025comprehensive, kum2026heatintegrated, hansen2024hysys, farokhi2025costoptimization, takahashi2016kinetic, dicarlo2014ammonia -->

# 16 Model validation

## 16.1 Strategy and validation matrix

AmCraX contains two process models that share inputs but no code: the **Aspen Plus V15 simulation** and the **independent Python calculation**. Each is checked against the other, against reference data and for internal consistency, and every check is one item of a validation matrix rebuilt from the stored results. An item passes only when a computed metric lies within a tolerance fixed beforehand, usually an **engineering assumption**. Failing items keep their tolerance; items that cannot fail are informational. The matrix holds 137 items: 105 pass, 22 fail, 0 not run and 10 informational (Table 16.1). The failures have two root causes (Sections 16.4 and 16.7).
<!-- data: results/validation/validation_matrix.json summary (n_items, pass, fail, not_run, informational), summary.failure_root_causes -->

Table: **Table 16.1.** Validation items by family and status. *Source: results/validation/validation_matrix.json, summary.by_family.*

| Family | What is compared | Items | Pass | Fail | Info. |
|---|---|---|---|---|---|
| THERMO | Stoichiometry, NASA-7 consistency | 3 | 2 | 0 | 1 |
| EQ | Aspen vs Python equilibrium, Python vs NIST-JANAF | 11 | 8 | 0 | 3 |
| FS | Aspen vs Python flowsheet, all key KPIs (2 %) | 20 | 0 | 20 | 0 |
| FS-PRIMARY | Aspen vs Python, independent reaction-section quantities | 20 | 20 | 0 | 0 |
| FEEDSEC | Feed-section analysis at identical states | 1 | 0 | 0 | 1 |
| BAL-ASPEN, BAL-PY | Mass, element and energy bookkeeping | 24 | 24 | 0 | 0 |
| SENS, STEMP, FEED-PROP | Sensitivity runs, native Sensitivity block, feed scaling | 11 | 11 | 0 | 0 |
| PHYS | Independent physics recalculations | 5 | 4 | 0 | 1 |
| LIT | Published values | 14 | 11 | 0 | 3 |
| KIN | Published kinetic data | 4 | 1 | 2 | 1 |
| OPT | Aspen re-solution and feasibility of optima | 2 | 2 | 0 | 0 |
| ECON, ENV | Cost and carbon arithmetic | 9 | 9 | 0 | 0 |
| PYTEST | Python test suite, one item per test file | 13 | 13 | 0 | 0 |
| **Total** | | **137** | **105** | **22** | **10** |

<!-- data: results/validation/validation_matrix.json summary.by_family (families merged where marked) -->

## 16.2 Thermochemistry and equilibrium

The Python thermochemistry (GRI-Mech 3.0 NASA-7 data via Cantera; Smith et al., n.d.; Goodwin et al., 2018) matches **NIST-JANAF** (National Institute of Standards and Technology, n.d.) within 14.9 J/mol NH~3~ in reaction Gibbs energy and 0.039 kJ/mol in reaction enthalpy over 250–900 °C. Like for like over 84 temperature–pressure points, Aspen IDEAL and Python ideal gas differ by at most 0.045 pp in conversion, and Aspen PENG-ROB and Python Peng–Robinson by at most 0.185 pp. Section 13 gives the detailed comparison and the unexplained 0.18 pp, for which binary interaction parameters are an unlikely cause.
<!-- data: results/validation/validation_matrix.json items EQ-DG-JANAF (14.94), EQ-DH-JANAF (0.03856), EQ-IDEAL (0.04547), EQ-PR (0.1853), EQ-MIXED (1.476), EQ-KIJ-SENS -->

## 16.3 Aspen internal consistency

All 20 stored Aspen cases close mass, element and energy balances to 3.9 × 10^−9^, and the 91 sensitivity runs converged with closures below 4.5 × 10^−9^. These items test extraction and bookkeeping, not physics, because Aspen closes its own balances (Section 15). Aspen's native Sensitivity block and the COM-driven study agree to 4.8 × 10^−10^.
<!-- data: results/validation/validation_matrix.json items BAL-ASPEN-* (max 3.943e-09, opt_opt_lcoh_tp), SENS-* (max energy 4.47e-09), STEMP-baseline (4.822e-10), FEED-PROP (2.912e-09) -->

## 16.4 Flowsheet cross-check

Each of the 20 stored Aspen cases was re-run with the Python model at identical inputs. The FS items apply 2 % to all key KPIs, including feed-section duties, and all 20 fail. The largest deviation per case is 3.5–11.8 %, in the cooler duty (17 cases) or trim-heater duty (3 cases).
<!-- data: results/validation/validation_matrix.json items FS-* (value min 0.03537 FS-baseline_no_hi, max 0.1180 FS-scn_tight_fehe; worst metric cooling_duty_kW 17x, preheat_duty_kW 3x) -->

The two models use different property models in the feed section: Aspen applies PENG-ROB to the liquid, the vaporisation and the NH~3~–H~2~O dew point; the Python model uses the reference equation of state for ammonia through CoolProp (Bell et al., 2014) and an ideal-liquid dew point. At identical states, Aspen's vaporiser duty is 2.4 % above the reference equation of state (739.5 vs 721.8 kW). The dew point at 20.8 bar is 60.1 °C with the ideal-liquid model and 65.9 °C in Aspen; no reference mixture model was available to arbitrate. Of the 20.8 kW baseline exchanger-duty gap, 8.7 kW come from the dew point and 11.6 kW from the vapour residual enthalpy; with Aspen's own states and the same property model the Python correlations give 612.0 kW against Aspen's 612.2 kW. The FS items therefore measure a model-form difference in both directions; they are not evidence that the Python model is the weaker one.
<!-- data: results/validation/feed_section_analysis.json vaporiser_at_aspen_states (721.82, 739.46, 0.02444), dew_point (50.88, 60.09, 65.90), fehe_gap_split_kW (20.82, 8.67, 11.62, 0.74, -0.21, NASA_PR_kij0_between_aspen_S2_S3_kW 611.99) -->

The FS-PRIMARY family compares Aspen PENG-ROB with Python Peng–Robinson on independent quantities only: conversion and cracked-gas mole fractions (0.5 pp) and reactor duty (1 %). H~2~ purity, product flow, yield, tail gas and flame temperature follow from the conversion and the PSA split fractions, which are inputs; they are reported, not judged. All 20 items pass; the largest normalised deviation is 0.118 (reactor duty −0.118 % at 40 bar).
<!-- data: results/validation/validation_matrix.json items FS-PRIMARY-* (max 0.1182, FS-PRIMARY-scn_high_pressure) -->

## 16.5 Independent physics checks

Four Aspen quantities were recalculated outside Aspen for all stored cases (Table 16.2): flame temperature and flue-gas cooler duty with Cantera, pump power by hand with the CoolProp liquid volume, and exchanger UA from the terminal temperatures. The UA item checks output consistency, not heat transfer; it showed that Aspen's "cal" here is the International Table calorie.
<!-- data: results/validation/independent_physics_checks.csv; validation_matrix.json items PHYS-* -->

Table: **Table 16.2.** Independent physics checks over the stored Aspen cases. Tolerances are engineering assumptions. *Source: results/validation/independent_physics_checks.csv; independent Python calculation (Cantera, CoolProp) against Aspen Plus V15 simulation.*

| Item | Recalculation | Worst deviation | Tolerance | Status |
|---|---|---|---|---|
| PHYS-FLAME | Complete-combustion flame temperature, Cantera | 0.58 K (baseline 1368.80 vs 1368.90 °C) | 2 K | pass |
| PHYS-FLAME-DISSOC | Equilibrium flame with dissociation | −2.25 K at baseline (−0.04 to −6.33 K) | none | informational |
| PHYS-FLUEHX | Flue-gas cooler duty, Cantera | 3.5 × 10^−4^ relative | 0.5 % | pass |
| PHYS-PUMP | $\dot n\, v_\mathrm{L}\, \Delta P / 0.75$ | +0.29 % (baseline 1.851 vs 1.845 kW) | 1 % | pass |
| PHYS-FEHE-UA | $Q/\Delta T_\mathrm{lm}$ from terminal temperatures | 4.9 × 10^−9^ relative | 10^−4^ | pass |

<!-- data: results/validation/validation_matrix.json items PHYS-FLAME (0.5758 K, scn_low_recovery), PHYS-FLAME-DISSOC (-2.251), PHYS-FLUEHX (3.482e-04), PHYS-PUMP (2.939e-03), PHYS-FEHE-UA (4.892e-09) -->

## 16.6 Literature benchmarks

Where conditions are fully stated, **published literature** agrees: fourteen tabulated equilibrium conversions within 0.15 pp (Cechetto et al., 2023), nine reaction enthalpies within 0.32 kJ/mol, sixteen figure readings within 1.5 pp (Cechetto et al., 2023; Xu et al., 2025) and the Gibbs correlation of Kum et al. (2026) within 0.53 kJ. Zero reaction Gibbs energy falls at 455.9 K against about 450 K (Maccarrone et al., 2025). Three items are informational because the sources omit the pressure or reactor boundary (Hansen et al., 2024; Farokhi et al., 2025) or misprint correlations.
<!-- data: results/validation/validation_matrix.json items LIT-CECHETTO-T3 (0.1523), LIT-DH298 (0.3211), LIT-FIGREAD (1.511), LIT-KUM-DG (0.5253), LIT-MACC-T0 (455.9 K), LIT-HANSEN, LIT-PROCESS, LIT-MACC-KP; results/validation/literature_benchmarks.csv -->

## 16.7 Kinetics

Rate constants from the published Arrhenius parameters match the tabulated values within 6.8 % (Takahashi & Fujitani, 2016). The plug-flow predictions of the published conversion curves do worse (Figure 16.1); W/F was inferred from one anchor point per catalyst because the catalyst mass is not reported. Six of 12 Ni points and six of 11 Ru points miss the 0.05 tolerance (maxima 0.110 and 0.111), all under-predictions at diluted NH~3~ or with H~2~ co-feed. Both items fail; nothing was tuned. The fit to Di Carlo et al. (2014) is informational because the rate law was fitted to those data (Section 14).
<!-- data: results/validation/validation_matrix.json items KIN-TABLE2 (0.06828), KIN-NI-PRED (0.1096, 6 of 12), KIN-RU-PRED (0.1113, 6 of 11), KIN-DICARLO (0.003857); results/validation/kinetics_validation.csv -->

![**Figure 16.1.** Microkinetic plug-flow conversion against values read from Figs. 3–5 of Takahashi and Fujitani (2016), Ni/MgO (top) and Ru/MgO (bottom). The pure-NH~3~ temperature series agree, while the diluted and H~2~-co-feed series are under-predicted, which is why KIN-NI-PRED and KIN-RU-PRED fail. *Source: independent Python calculation; published literature.*](../../results/figures/kinetics_validation.png){width=100%}

## 16.8 Aspen verification of the optimisation candidates

The ten optimisation candidates were re-solved in **Aspen Plus V15** with the reported decision variables (Section 20.4). Under the file's criterion (converged, and every primary metric within 0.02 of the Python value), all ten pass; the 11 primary metrics agree within 1.15 %, while secondary metrics, which are not judged, deviate by up to 9.4 % for the feed-section reason above. The item formerly took the maximum over every field; it now reads the file by its own criterion, a correction of the reading, not a relaxed tolerance. The 12 optima flagged feasible respect all bounds and constraints within 3.2 × 10^−9^.
<!-- data: results/optimisation/aspen_verification.json criterion, tolerance_relative, candidates[*].max_relative_deviation_primary (max 0.01152, par_1) and _secondary (max 0.09437, opt_heat); validation_matrix.json items OPT-ASPEN, OPT-FEAS (3.179e-09) -->

## 16.9 A defect found by validation

In the first Aspen equilibrium grid, one IDEAL point (600 °C, 30 bar) gave a duty-to-conversion ratio 1.24 kJ/mol off, although for an ideal gas this ratio cannot depend on pressure. The automation had run the engine asynchronously and read the previous point's duty while Aspen was still loading results. The fix was synchronous runs, re-initialisation at every point and guards for repeatability and pressure independence (Section 12). In the regenerated grid the pressure spread of the ratio is 3.2 × 10^−7^ kJ/mol. Flowsheet runs always re-initialise and were not affected.
<!-- data: results/validation/validation_matrix.json items EQ-GRID-STALE (3.247e-07), EQ-DH-ASPEN (0.05008, limitations text) -->

## 16.10 Informational items

Two items were reclassified as informational in the independent review because they cannot fail: THERMO-VANTHOFF tests the Gibbs–Helmholtz relation, which NASA-7 polynomials obey exactly, and EQ-AMPLIFY recovers Aspen's conversion from a ln K back-calculated from Aspen's own composition. Four lack a judging reference: EQ-MIXED (not like for like), FEEDSEC-ANALYSIS (no NH~3~–H~2~O arbiter), PHYS-FLAME-DISSOC (no dissociation in either model) and EQ-KIJ-SENS (a sensitivity study). The other four are LIT-HANSEN, LIT-PROCESS, LIT-MACC-KP and KIN-DICARLO. The Python energy closure is zero by construction and is not judged. The 13 test-suite items (391 tests pass, one opt-in live-Aspen test skipped) show that the code behaves as specified, not that the physics is right.
<!-- data: results/validation/validation_matrix.json items with status informational (10), BAL-PY-* limitations, PYTEST-* (sum 392 tests, 1 skipped); docs/validation/discrepancy_analysis.md section 7(d) -->

## 16.11 What is not validated

Not validated are the reduced-order PSA and membrane models, the costs, the carbon-intensity accounting, the kinetics at 20 bar (data at 1 atm, or up to 10 bar), the NH~3~–H~2~O dew point and the remaining 0.18 pp Peng–Robinson gap. No plant data were available; AmCraX is not a validated digital twin (Section 24).
<!-- data: results/validation/validation_matrix.json (no items for these components); results/validation/kinetics_validation.csv conditions -->
