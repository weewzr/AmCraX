<!-- cites: cho2026nickel, hansen2024hysys, chopra2026decentralized -->

# 18 Process optimisation

## 18.1 Formulation

The evaluator is the **independent Python process model** with the LCOH and carbon-intensity (CI; simplified accounting, not an LCA) modules; Aspen Plus V15 re-solves the candidates afterwards (Section 18.4). The heat deficit is covered by burning grey NH~3~ (450 USD/t). Below the 7 bar PSA feed requirement (Cho et al., 2026), compression electricity is charged, but not compressor CAPEX.

The bounds are the ranges of the Aspen Plus V15 sweeps: reactor temperature $T$ 400-800 degC, pressure $P$ 5-40 bar, PSA H~2~ recovery $R$ 0.70-0.95 (**engineering assumption**; literature PSA points span 0.71-0.81) and FEHE hot-end approach $\Delta T_\mathrm{app}$ 20-150 K. Objectives: minimum LCOH, maximum LHV efficiency, minimum external heating per kg H~2~, maximum H~2~ production, maximum NH~3~ conversion. Constraints ($g \ge 0$ satisfied):

$$ g_1 = \Delta T_\mathrm{min,FEHE} - 0\ \mathrm{K} \ge 0, \qquad g_2 = X - 0.95 \ge 0, \qquad g_3 = y_\mathrm{H_2} - 0.99 \ge 0 \qquad (18.1) $$

where $\Delta T_\mathrm{min,FEHE}$ (K) is the smallest internal FEHE temperature difference (a cross or model failure is infeasible), $X$ (-) the equilibrium NH~3~ conversion (0.95 is a design assumption limiting NH~3~ to the burner; a 0.99 variant follows the 99.42 % and 99.6 % of Hansen et al., 2024) and $y_\mathrm{H_2}$ (-) the product H~2~ mole fraction (Chopra et al., 2026). An optional $g_4 = -\dot Q_\mathrm{deficit}$ (kW) $\ge 0$ imposes thermal self-sufficiency. A kinetic-feasibility constraint is **not implemented**.

The solver is differential evolution (scipy; Sobol start, population 10, 30 generations, seed 12345) on scaled variables, then an SLSQP polish. Each objective is solved with all four variables and with $T$ and $P$ only ($R$ = 0.85, $\Delta T_\mathrm{app}$ = 50 K), because the model does not cost PSA size or FEHE area. Runs used 1020-2405 model evaluations without failures. Differential evolution stopped at the generation limit in all runs but one. SLSQP converged except in the $X \ge 0.99$ and self-sufficiency variants.
<!-- data: results/optimisation/single_objective.json assumptions, results[*].solver; backend/amcrax/optimisation/problems.py VARIABLES, CONSTRAINT_DOCS -->

## 18.2 Single-objective results

Table: **Table 18.1.** Single-objective optima on the Python process model (four variables, $T$ / $P$ / $R$ / $\Delta T_\mathrm{app}$; then $T$ and $P$ only). Baseline values are from the same model at 600 degC and 20 bar. *Source: independent Python calculation.*

| Objective | Optimum, 4 variables | Value (baseline) | Optimum, $T$, $P$ only | Value | What sets the optimum |
|---|---|---|---|---|---|
| Min LCOH (USD/kg) | 532.6 / 7.5 / 0.95 / 20 | 3.810 (3.914) | 526.1 / 7.5 | 3.902 | $R$ upper, $\Delta T_\mathrm{app}$ lower bound; $P$ at 7 bar PSA-feed kink; $T$ interior, flat |
| Max LHV efficiency (-) | 460.8 / 5.0 / 0.95 / 20 | 0.903 (0.880) | 456.7 / 5.0 | 0.885 | $P$ lower bound; flat in $T$ over 400-800 degC |
| Min external heating (kWh/kg) | 416.6 / 5.0 / 0.95 / 20 | 7.72 (8.99) | 414.6 / 5.0 | 8.78 | $P$, $R$, $\Delta T_\mathrm{app}$ bounds; $T$ interior |
| Max H~2~ (kg/h) | 800 / 5.0 / 0.95 / 122.5 | 286.3 (251.6) | 800 / 5.0 | 256.2 | $T$ upper, $P$ lower, $R$ upper; flat in $P$, $\Delta T_\mathrm{app}$ |
| Max conversion (-) | 800 / 5.0 / 0.876 / 99.5 | 0.9988 (0.9809) | 800 / 5.0 | 0.9988 | $T$ upper, $P$ lower (equilibrium) |

<!-- data: results/optimisation/single_objective.json results[id=*].decision_variables, improvement, driver, flatness -->

Most optima are set by bounds. Maximum H~2~ and conversion follow Le Chatelier's principle to high $T$ and low $P$. $R$ = 0.95 and $\Delta T_\mathrm{app}$ = 20 K win only because PSA size and FEHE area are not costed. The minimum-LCOH pressure (7.5 bar) is the lowest that gives a 7 bar PSA feed without compression, so it moves with that literature requirement. The minimum-LCOH temperature is a genuine interior optimum but flat: LCOH stays within 1 % from 420 to 800 degC and from 5 to 28.6 bar (Figures 18.1 and 18.2). The gain is -2.7 % (four variables) and -0.3 % ($T$, $P$). With $X \ge 0.99$ the optimum moves to 564.3 degC (3.902 USD/kg). Self-sufficiency has no feasible $T$, $P$ point; with $R$ free it gives 414.0 degC, 7.5 bar, $R$ = 0.803 and 3.959 USD/kg, worse than the baseline.
<!-- data: results/optimisation/single_objective.json results[id=min_lcoh].flatness, results[id=min_lcoh_TP_X99], results[id=min_lcoh_TP_selfsuff], results[id=min_lcoh_selfsuff] -->

![**Figure 18.1.** LCOH over reactor temperature and pressure ($R$ = 0.85, 50 K approach), with infeasible grid points and the $T$, $P$ optimum. The wide yellow valley shows how flat the LCOH optimum is. *Source: independent Python calculation.*](../../results/figures/opt_lcoh_landscape.png){width=75%}

![**Figure 18.2.** One-dimensional scans through the four-variable minimum-LCOH point (dashed line = +1 %). Only $R$ changes LCOH strongly. *Source: independent Python calculation.*](../../results/figures/opt_objective_flatness.png){width=100%}

## 18.3 Multi-objective analysis

Over the 4752 feasible points of the 6120-point design grid, the objectives mostly agree because all follow NH~3~ use per kg H~2~. Spearman correlations (minimisation sense, positive = aligned) are 0.997 for LCOH-CI, 0.991 for LCOH-efficiency, 0.964 for LCOH-H~2~ yield and 0.994 for efficiency-CI; conversion correlates weakly with all (0.027-0.167). The non-dominated sets are narrow: 2 LCOH-CI points (3.8097-3.8102 USD/kg) and 15 LCOH-conversion points (LCOH 3.810-3.843 USD/kg, conversion 0.9855-0.9988). A real trade-off appears only in an overlay. Green NH~3~ with natural-gas heat gives 99 points, from 3.360 USD/kg at 1.62 kg CO~2~e/kg (800 degC) to 3.949 USD/kg at 0.41 kg CO~2~e/kg (425 degC): fired heat is cheaper than burning NH~3~ but adds fossil CO~2~ (Figure 18.3). The NH~3~ price stays at 450 USD/t in these overlays.
<!-- data: results/optimisation/objective_conflicts.json pairs; results/optimisation/pareto.json fronts (overlays) -->

![**Figure 18.3.** LCOH-CI non-dominated sets for each NH~3~ origin and heat source. Only green NH~3~ with natural-gas heat gives an extended front. *Source: independent Python calculation; CI simplified accounting, not an LCA.*](../../results/figures/opt_pareto_lcoh_ci_overlays.png){width=75%}

## 18.4 Verification in Aspen Plus V15

The ten candidates are the six single-objective optima and four LCOH-H~2~-yield Pareto points, sent to Aspen with exactly the reported decision variables (an earlier verification had reset variables in which an objective was flat to their baseline values; it was replaced). All ten candidates were re-solved in **Aspen Plus V15** (relative mass and energy closures at most 3.3 × 10^−9^ in magnitude). The criterion is quoted from the file: "pass = Aspen Plus converged AND every primary metric agrees with the Python surrogate within the tolerance. Secondary metrics (individual duties, minor cost items) are reported, not judged." The tolerance is 0.02.
<!-- data: results/optimisation/aspen_verification.json criterion, tolerance_relative, candidates[*] -->

Table: **Table 18.2.** Re-solution of the optimisation candidates ($T$ degC / $P$ bar / $R$ / $\Delta T_\mathrm{app}$ K). Deviations are relative (Python vs Aspen). *Source: Aspen Plus V15 simulation; independent Python calculation.*

| Candidate | Inputs | Converged | Primary max dev. | LCOH Aspen / Python (USD/kg) | Secondary max dev. |
|---|---|---|---|---|---|
| opt_lcoh | 532.6/7.5/0.95/20 | yes | 1.23 % | 3.818 / 3.810 | 9.3 % |
| opt_eff | 460.8/5/0.95/20 | yes | 1.17 % | 3.841 / 3.833 | 9.6 % |
| opt_heat | 416.6/5/0.95/20 | yes | 1.19 % | 3.846 / 3.837 | 10.4 % |
| opt_h2 | 800/5/0.95/122.5 | yes | 1.00 % | 3.900 / 3.893 | 4.2 % |
| opt_conv | 800/5/0.876/99.5 | yes | 1.01 % | 3.952 / 3.944 | 4.6 % |
| opt_lcoh_tp | 526.1/7.5/0.85/50 | yes | 1.22 % | 3.911 / 3.902 | 8.0 % |
| par_1 to par_4 | 525-800/5-7.5/0.95/20 | yes | 1.05-1.24 % | 3.818-3.851 / 3.810-3.843 | 6.6-9.4 % |

<!-- data: results/optimisation/aspen_verification.json candidates[*].max_relative_deviation_primary, metrics.lcoh_USD_per_kg, max_relative_deviation_secondary -->

All ten pass. The largest primary deviation is always the specific external heating (at most 1.24 %); LCOH agrees within 0.25 %, so the ranking holds in Aspen. The largest secondary deviation is always the cooling-water cost item. It comes, like the recovered-heat difference (3.7 % for opt_lcoh), from the feed-section model: the Python vaporiser dew point (Raoult) is about 5.8 K below Aspen PENG-ROB and liquid-NH~3~ enthalpy comes from CoolProp. The validation matrix therefore fails the full-duty items `FS-opt_*` (20 FS failures; 22 failures of 130 items in total), while all `FS-PRIMARY` and both `OPT` items pass.
<!-- data: results/optimisation/aspen_verification.json candidates[*]; results/validation/validation_matrix.json summary (generated 2026-11-21T12:41:51Z: 130 items, 103 pass, 22 fail, 5 informational) -->

## 18.5 Scenario analysis

Table: **Table 18.3.** Named Aspen Plus V15 scenarios (grey NH~3~ at 450 USD/t, heat deficit by burning NH~3~). The last column is Aspen minus Python at the same inputs, a model-form difference, not an error bar. *Source: Aspen Plus V15 simulation; LCOH and CI by independent Python calculation.*

| Scenario | X (-) | H~2~ (kg/h) | LHV eff. (-) | LCOH (USD/kg) | CI (kg CO~2~e/kg) | Aspen-Python LCOH |
|---|---|---|---|---|---|---|
| Baseline 600 degC, 20 bar | 0.9808 | 251.6 | 0.877 | 3.925 | 19.52 | +0.011 |
| 500 degC | 0.9521 | 244.2 | 0.876 | 3.937 | 19.55 | +0.012 |
| 700 degC | 0.9910 | 254.2 | 0.877 | 3.925 | 19.53 | +0.011 |
| 5 bar (90.5 kW compression) | 0.9951 | 255.3 | 0.881 | 3.939 | 19.59 | +0.009 |
| 40 bar | 0.9626 | 246.9 | 0.875 | 3.939 | 19.57 | +0.014 |
| No heat integration | 0.9808 | 251.6 | 0.824 | 4.139 | 20.77 | +0.003 |
| 20 K FEHE approach | 0.9808 | 251.6 | 0.881 | 3.910 | 19.43 | +0.011 |
| Recovery 0.92 | 0.9808 | 272.3 | 0.888 | 3.867 | 19.27 | +0.011 |
| Recovery 0.75 | 0.9808 | 222.0 | 0.842 | 4.091 | 20.33 | +0.000 |
| Purity-driven, `scn_fuel_cell_grade` (slip 0.0005, $R$ 0.80) | 0.9808 | 236.8 | 0.868 | 3.973 | 19.72 | +0.012 |

<!-- data: results/simulations/scenario_comparison.json rows[*].metrics, aspen_minus_python -->

Temperature and pressure move LCOH by less than 0.4 %, because conversion stays at 0.95-0.995 and the burner returns unconverted NH~3~ as heat. Heat integration (+5.4 % LCOH without the FEHE) and PSA recovery (-1.5 % at 0.92, +4.2 % at 0.75) matter. The baseline product (99.961 mol% H~2~) is not fuel-cell grade; the purity-driven case `scn_fuel_cell_grade` (99.979 mol%) costs +1.2 % LCOH, and NH~3~ polishing is not modelled. The Aspen-minus-Python LCOH (0.000-0.014 USD/kg) is small against the scenario differences.
<!-- data: results/simulations/scenario_comparison.json rows[*] -->

## 18.6 Limits

The optima come from a surrogate; only the ten re-solved candidates are Aspen-confirmed. The equilibrium reactor has no catalyst-volume penalty and the kinetic-feasibility constraint is not implemented, so low temperatures are not checked kinetically. The plant-level CAPEX correlation does not cost exchanger area, PSA size or compressors, which puts $R$ and $\Delta T_\mathrm{app}$ on bounds; $R$ = 0.95 is outside the demonstrated PSA range.
