<!-- cites: cho2026nickel, hansen2024hysys, chopra2026decentralized -->

# 20 Optimisation

## 20.1 Formulation

The optimiser evaluates the **independent Python process model** with the LCOH and carbon-intensity modules (CI; simplified accounting, not an LCA). Aspen Plus V15 re-solves the candidates afterwards (Section 20.4). The heat deficit is covered by burning grey NH~3~ at 450 USD/t. Below the 7 bar PSA feed pressure required by Cho et al. (2026), compression electricity is charged, but not compressor CAPEX.

The bounds are the ranges of the Aspen Plus V15 sweeps (Section 17): reactor temperature $T$ 400–800 °C, pressure $P$ 5–40 bar, PSA H~2~ recovery $R$ 0.70–0.95 (**engineering assumption**; literature PSA points span 0.71–0.81) and exchanger hot-end approach $\Delta T_\mathrm{app}$ 20–150 K. The objectives are minimum LCOH, maximum LHV efficiency, minimum external heating per kg H~2~, maximum H~2~ production and maximum NH~3~ conversion. The constraints are satisfied when $g \ge 0$:

$$ g_1 = \Delta T_\mathrm{min,FEHE} - 0\ \mathrm{K}, \qquad g_2 = X - 0.95, \qquad g_3 = y_\mathrm{H_2} - 0.99 \qquad (20.1) $$

where $\Delta T_\mathrm{min,FEHE}$ (K) is the smallest internal exchanger temperature difference (a cross or model failure is infeasible), $X$ (–) the equilibrium NH~3~ conversion and $y_\mathrm{H_2}$ (–) the product H~2~ mole fraction (Chopra et al., 2026). The 0.95 conversion limit is a design assumption that limits the NH~3~ sent to the burner; a 0.99 variant follows the 99.42 % and 99.6 % reported by Hansen et al. (2024). An optional $g_4 = -\dot Q_\mathrm{deficit}$ (kW) imposes thermal self-sufficiency. A kinetic-feasibility constraint is **not implemented**.
<!-- data: results/optimisation/single_objective.json assumptions (evaluator, variables, default_constraints, constraint_definitions) -->

The solver is differential evolution (SciPy; population 10, 30 generations, seed 12345) on scaled variables, followed by an SLSQP polish. Each objective is solved with all four variables and with $T$ and $P$ only ($R$ = 0.85, $\Delta T_\mathrm{app}$ = 50 K), because the model does not cost PSA size or exchanger area. The 13 runs used 1073–2310 model evaluations without a model failure. Differential evolution stopped at the generation limit in all runs but one; the polish converged except in the $X \ge 0.99$ variant (iteration limit) and the self-sufficient $T$, $P$ variant, which found no feasible point.
<!-- data: results/optimisation/single_objective.json results[*].solver (popsize 10, maxiter 30, seed 12345, model_runs, model_failures, de_message, polish) -->

## 20.2 Single-objective results

Table: **Table 20.1.** Single-objective optima on the Python process model ($T$ °C / $P$ bar / $R$ / $\Delta T_\mathrm{app}$ K; then $T$ and $P$ only). Baseline values come from the same model at 600 °C and 20 bar. *Source: independent Python calculation.*

| Objective | Optimum, 4 variables | Value (baseline) | Optimum, $T$, $P$ only | Value | What sets the optimum |
|---|---|---|---|---|---|
| Min LCOH (USD/kg) | 529.1 / 7.5 / 0.95 / 20 | 3.805 (3.909) | 527.2 / 7.5 | 3.896 | $R$ upper, $\Delta T_\mathrm{app}$ lower bound; $P$ at the PSA-feed kink; $T$ interior, flat |
| Max LHV efficiency (–) | 462.3 / 5.0 / 0.95 / 20 | 0.903 (0.880) | 458.3 / 5.0 | 0.885 | $P$, $R$, $\Delta T_\mathrm{app}$ bounds; flat in $T$ over 400–800 °C |
| Min external heating (kWh/kg) | 418.2 / 5.0 / 0.95 / 20 | 7.72 (9.00) | 416.4 / 5.0 | 8.79 | $P$, $R$, $\Delta T_\mathrm{app}$ bounds; $T$ interior |
| Max H~2~ (kg/h) | 800 / 5.0 / 0.95 / 122.5 | 286.3 (251.6) | 800 / 5.0 | 256.2 | $T$ upper, $P$ lower, $R$ upper; flat in $P$, $\Delta T_\mathrm{app}$ |
| Max conversion (–) | 800 / 5.0 / 0.876 / 99.5 | 0.9988 (0.9809) | 800 / 5.0 | 0.9988 | $T$ upper, $P$ lower (equilibrium) |

<!-- data: results/optimisation/single_objective.json results[id=min_lcoh, min_lcoh_TP, max_lhv_efficiency(_TP), min_specific_heat(_TP), max_h2_production(_TP), max_conversion(_TP)].decision_variables, improvement, driver, flatness -->

Most optima are set by bounds. Maximum H~2~ and conversion follow Le Chatelier's principle to high $T$ and low $P$. $R$ = 0.95 and $\Delta T_\mathrm{app}$ = 20 K win only because PSA size and exchanger area are not costed; they are not discovered optima. The minimum-LCOH pressure of 7.5 bar is the lowest that delivers 7 bar to the PSA without compression, so it moves with that literature requirement. The minimum-LCOH temperature is interior but flat: the LCOH stays within 1 % of the optimum from 420 to 800 °C and from 5 to 27.75 bar (Figures 20.1 and 20.2), whereas only recoveries of 0.90–0.95 stay within 1 %. The gain over the baseline is 2.7 % with four variables and 0.3 % with $T$ and $P$ only. With $X \ge 0.99$ the optimum moves to 564.3 °C at 3.897 USD/kg. Thermal self-sufficiency has no feasible $T$, $P$ point; with $R$ free it gives 414.0 °C, 7.5 bar, $R$ = 0.803 and 3.953 USD/kg, worse than the baseline.
<!-- data: results/optimisation/single_objective.json results[id=min_lcoh].flatness (T 420-800, P 5-27.75, R 0.90-0.95), improvement.delta_rel (-0.0267, -0.0033), optimum_metrics.psa_feed_pressure_bar (7.0); results[id=min_lcoh_TP_X99], [id=min_lcoh_TP_selfsuff] (feasible false), [id=min_lcoh_selfsuff] -->

![**Figure 20.1.** LCOH over reactor temperature and pressure ($R$ = 0.85, 50 K approach), with infeasible grid points (crosses) and the $T$, $P$ optimum (star). The wide valley shows how flat the LCOH optimum is. *Source: independent Python calculation.*](../../results/figures/opt_lcoh_landscape.png){width=75%}

![**Figure 20.2.** One-dimensional scans through the four-variable minimum-LCOH point (dashed line = +1 %). Only the PSA recovery changes the LCOH strongly, and it sits on its upper bound. *Source: independent Python calculation.*](../../results/figures/opt_objective_flatness.png){width=100%}

## 20.3 Objective conflicts

Over the 4752 feasible points of the 6120-point design grid, the objectives largely do not conflict, because all of them follow the NH~3~ use per kg H~2~. Spearman rank correlations, in minimisation sense with positive values meaning aligned objectives, are 0.997 for LCOH–CI, 0.991 for LCOH–efficiency, 0.964 for LCOH–H~2~ yield and 0.994 for efficiency–CI. Conversion correlates weakly with every other objective (0.032–0.167). The non-dominated sets are narrow: 2 LCOH–CI points (3.8046–3.8051 USD/kg) and 15 LCOH–conversion points (LCOH 3.805–3.838 USD/kg, conversion 0.9855–0.9988).
<!-- data: results/optimisation/objective_conflicts.json pairs[*].spearman_rho_min_sense, n_non_dominated, front_ranges; results/optimisation/pareto.json n_grid_points, n_feasible -->

A real trade-off appears only when the heat source and the NH~3~ origin change. With green NH~3~, priced at the sourced 1000 USD/t for current renewable NH~3~ (Cho et al., 2026), and natural-gas heat, the non-dominated set has 104 points, from 6.621 USD/kg at 1.62 kg CO~2~e/kg (800 °C) to 7.991 USD/kg at 0.41 kg CO~2~e/kg (425 °C). Fired natural gas is cheaper than burning NH~3~ but adds fossil CO~2~ (Figure 20.3). With grey NH~3~, natural-gas heat gives a single point at 3.355 USD/kg and 17.06 kg CO~2~e/kg.
<!-- data: results/optimisation/pareto.json fronts[overlay='green NH3, heat source natural_gas'] (104 points, ranges), fronts[overlay='grey NH3, heat source natural_gas'] (1 point); backend/amcrax/optimisation/pareto.py nh3_price_for_route; backend/amcrax/data/economics.yaml nh3_price alternatives 'renewable NH3 current' 1000 USD/t -->

![**Figure 20.3.** LCOH–CI non-dominated sets for each NH~3~ origin and heat source. Only green NH~3~ with natural-gas heat gives an extended front. Grey NH~3~ is priced at 450 USD/t and green NH~3~ at 1000 USD/t; the footer of the image, which states a fixed 450 USD/t, applies to grey NH~3~ only. *Source: independent Python calculation; CI simplified accounting, not an LCA.*](../../results/figures/opt_pareto_lcoh_ci_overlays.png){width=75%}

## 20.4 Verification in Aspen Plus V15

The ten candidates are the six single-objective optima of Table 20.1 (the five four-variable optima and the $T$, $P$ minimum-LCOH point) and four LCOH–H~2~-yield Pareto points. They were sent to Aspen with the reported decision variables, rounded to 0.1 K in temperature and approach and to 0.001 in recovery; no variable was reset to a baseline value. The verification file states the criterion: "pass = Aspen Plus converged AND every primary metric agrees with the Python surrogate within the tolerance. Secondary metrics (individual duties, minor cost items) are reported, not judged." The tolerance is 0.02 relative.
<!-- data: results/optimisation/candidates_for_aspen.json; results/optimisation/aspen_verification.json criterion, tolerance_relative, primary_metrics (11) -->

Table: **Table 20.2.** Re-solution of the optimisation candidates ($T$ °C / $P$ bar / $R$ / $\Delta T_\mathrm{app}$ K). Deviations are relative, (Python − Aspen)/Aspen; the largest primary deviation is always the specific external heating. *Source: Aspen Plus V15 simulation; independent Python calculation.*

| Candidate | Inputs | Converged | Max primary dev. | LCOH Aspen / Python (USD/kg) | Max secondary dev. |
|---|---|---|---|---|---|
| opt_lcoh | 529.1 / 7.5 / 0.95 / 20 | yes | 1.15 % | 3.812 / 3.805 | 8.5 % |
| opt_eff | 462.3 / 5.0 / 0.95 / 20 | yes | 1.10 % | 3.835 / 3.828 | 8.9 % |
| opt_heat | 418.2 / 5.0 / 0.95 / 20 | yes | 1.11 % | 3.839 / 3.832 | 9.4 % |
| opt_h2 | 800 / 5.0 / 0.95 / 122.5 | yes | 0.97 % | 3.895 / 3.887 | 4.1 % |
| opt_conv | 800 / 5.0 / 0.876 / 99.5 | yes | 0.98 % | 3.946 / 3.938 | 4.4 % |
| opt_lcoh_tp | 527.2 / 7.5 / 0.85 / 50 | yes | 1.13 % | 3.905 / 3.896 | 7.2 % |
| par_1 | 525 / 7.5 / 0.95 / 20 | yes | 1.15 % | 3.813 / 3.805 | 8.6 % |
| par_2 | 650 / 7.5 / 0.95 / 20 | yes | 1.11 % | 3.815 / 3.807 | 7.4 % |
| par_3 | 750 / 7.5 / 0.95 / 20 | yes | 1.08 % | 3.819 / 3.811 | 6.8 % |
| par_4 | 800 / 5.0 / 0.95 / 20 | yes | 1.03 % | 3.845 / 3.838 | 6.3 % |

<!-- data: results/optimisation/aspen_verification.json candidates[*].aspen_converged, max_relative_deviation_primary(_metric), metrics.lcoh_USD_per_kg.aspen/python, max_relative_deviation_secondary -->

All ten candidates converged and pass: the largest primary deviation is 1.15 % (par_1), and the LCOH agrees within 0.23 %, with Aspen 0.19–0.23 % above Python in every case, so the ranking holds in Aspen. Relative closures are at most 3.3 × 10^−9^ in magnitude. The largest secondary deviation is always the cooling-water cost item (up to 9.4 %); it and the recovered-heat difference (1.8–4.3 %) arise from the different feed-section property models (Section 16.4), which also make the ten FS items of these candidates fail while their FS-PRIMARY items pass.
<!-- data: results/optimisation/aspen_verification.json candidates[*] (max primary 0.011517 par_1; |lcoh relative| 0.00186-0.00226; secondary max 0.09437 opt_heat lcoh_cooling_water_USD_per_kg; recovered_heat_kW relative 0.0183-0.0426; aspen_mass_closure_rel, aspen_energy_closure_rel max |3.26e-09|); validation_matrix.json items FS-opt_*, FS-PRIMARY-opt_* -->

## 20.5 Scenario analysis

Table: **Table 20.3.** Named Aspen Plus V15 scenarios (grey NH~3~ at 450 USD/t, heat deficit covered by burning NH~3~). The last column is Aspen minus Python at the same inputs, a model-form difference, not an error bar. LCOH values are on the legacy cost basis of Section 19 (legacy core result, superseded for research outputs; the unified baseline is 4.015 USD/kg, Section 32). *Source: Aspen Plus V15 simulation; LCOH and CI by independent Python calculation.*

| Scenario | X (–) | H~2~ (kg/h) | LHV eff. (–) | LCOH (USD/kg) | CI (kg CO~2~e/kg) | Aspen − Python LCOH |
|---|---|---|---|---|---|---|
| Baseline, 600 °C, 20 bar | 0.9808 | 251.6 | 0.877 | 3.919 | 19.52 | +0.010 |
| 500 °C | 0.9521 | 244.2 | 0.876 | 3.931 | 19.55 | +0.010 |
| 700 °C | 0.9910 | 254.2 | 0.877 | 3.919 | 19.53 | +0.009 |
| 5 bar (90.5 kW compression) | 0.9951 | 255.3 | 0.881 | 3.933 | 19.59 | +0.008 |
| 40 bar | 0.9626 | 246.9 | 0.875 | 3.933 | 19.57 | +0.011 |
| No heat integration | 0.9808 | 251.6 | 0.824 | 4.133 | 20.77 | +0.003 |
| 20 K exchanger approach | 0.9808 | 251.6 | 0.881 | 3.903 | 19.43 | +0.010 |
| Recovery 0.92 | 0.9808 | 272.3 | 0.888 | 3.861 | 19.27 | +0.009 |
| Recovery 0.75 | 0.9808 | 222.0 | 0.842 | 4.084 | 20.33 | +0.000 |
| Purity-driven (N~2~ slip 0.0005, $R$ 0.80) | 0.9808 | 236.8 | 0.868 | 3.966 | 19.72 | +0.010 |

<!-- data: results/simulations/scenario_comparison.json rows[*].metrics (nh3_conversion, h2_product_kg_h, lhv_efficiency, lcoh_USD_per_kg, carbon_intensity_kgCO2e_per_kgH2, compression_power_kW), aspen_minus_python.lcoh_USD_per_kg -->

Temperature and pressure move the LCOH by less than 0.4 %, because conversion stays between 0.95 and 0.995 and the burner returns unconverted NH~3~ as heat. Heat integration (+5.5 % LCOH without the exchanger) and PSA recovery (−1.5 % at 0.92, +4.2 % at 0.75) matter (Figure 20.4). The baseline product, 99.961 mol% H~2~, is set by the assumed PSA split and is not fuel-cell grade. The purity-driven case reaches 99.979 mol% for +1.2 % LCOH; NH~3~ polishing is not modelled. The Aspen-minus-Python LCOH (0.000–0.011 USD/kg) is small against the scenario differences.
<!-- data: results/simulations/scenario_comparison.json rows[*].delta_rel_vs_baseline.lcoh_USD_per_kg (max |.| 0.0036 for T/P rows; baseline_no_hi 0.0546; scn_high_recovery -0.0149; scn_low_recovery 0.0422; scn_fuel_cell_grade 0.0121), metrics.h2_purity_mole_frac (0.999608, 0.999792), aspen_minus_python -->

![**Figure 20.4.** LCOH breakdown of the ten Aspen scenarios with the Aspen-minus-Python difference above each bar. Only heat integration and PSA recovery move the LCOH by more than a few tenths of a percent. *Source: Aspen Plus V15 simulation; LCOH by independent Python calculation.*](../../results/figures/scenario_lcoh.png){width=95%}

## 20.6 Limits

The optima come from the Python surrogate; only the ten re-solved candidates are confirmed in Aspen. The equilibrium reactor carries no catalyst-volume penalty and the kinetic-feasibility constraint is not implemented, so low temperatures are not checked kinetically (Section 14). The plant-level CAPEX correlation does not cost exchanger area, PSA size or compressors, which puts $R$ and $\Delta T_\mathrm{app}$ on their bounds; $R$ = 0.95 lies outside the demonstrated PSA range (Section 11).
