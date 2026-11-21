<!-- cites: smith_grimech30, goodwin2018cantera, nist_janaf, peng1976new, bell2014coolprop, cechetto2023membrane -->

# 13 Equilibrium modelling

## 13.1 The independent Python model

AmCraX contains its own equilibrium model, `amcrax.thermodynamics`, so that Aspen RGibbs can be checked against a calculation that shares no code with it. Species properties come from the NASA 7-coefficient polynomials of GRI-Mech 3.0 (Smith et al., n.d.), copied once from Cantera's `gri30.yaml` (Goodwin et al., 2018) into a data file; Cantera is not called at run time. The entropies reproduce the NIST-JANAF 1 bar values (National Institute of Standards and Technology, n.d.) and are used with a 1 bar standard state. The solver finds $z = \ln n_\mathrm{NH_3}$ with a bracketed Brent method and checks the N and H balances to 10^-9^. Two gas models are available: ideal gas, and Peng-Robinson (Peng & Robinson, 1976) with CoolProp critical constants (Bell et al., 2014), $k_{ij}$ = 0 by default and an optional Boston-Mathias α-function. The model is gas-phase only, for 250-900 °C.

<!-- data: backend/amcrax/thermodynamics/nasa7.py (DATA_FILE nasa7.json, POLY_PREF_BAR = 1.0, R = 8.314462618), equilibrium.py solve_equilibrium (brentq on ln n_NH3, element check 1e-9), peng_robinson.py (critical_properties.json from CoolProp, kij None = 0, alpha "boston-mathias") -->

## 13.2 Derivation of the equilibrium conversion

Per mole of ammonia the reaction is

$$ \mathrm{NH_3} \rightleftharpoons \tfrac{1}{2}\,\mathrm{N_2} + \tfrac{3}{2}\,\mathrm{H_2} \qquad (13.1) $$

For a feed of $n_0$ mol NH~3~ and conversion $X = \xi/n_0$, with $\xi$ the extent of reaction (mol), the mole numbers and the total are

$$ n_{\mathrm{NH_3}} = n_0(1-X), \quad n_{\mathrm{N_2}} = \tfrac{1}{2}n_0X, \quad n_{\mathrm{H_2}} = \tfrac{3}{2}n_0X, \quad n_{\mathrm{tot}} = n_0(1+X) \qquad (13.2) $$

so the mole fractions are

$$ y_{\mathrm{NH_3}} = \frac{1-X}{1+X}, \quad y_{\mathrm{N_2}} = \frac{X}{2(1+X)}, \quad y_{\mathrm{H_2}} = \frac{3X}{2(1+X)} \qquad (13.3) $$

At equilibrium the activities satisfy

$$ K(T) = \exp\!\left(-\frac{\Delta G_r^\circ(T)}{RT}\right) = \frac{(\hat\varphi_{\mathrm{N_2}} y_{\mathrm{N_2}}P/p^\circ)^{1/2}\,(\hat\varphi_{\mathrm{H_2}} y_{\mathrm{H_2}}P/p^\circ)^{3/2}}{\hat\varphi_{\mathrm{NH_3}} y_{\mathrm{NH_3}}P/p^\circ} \qquad (13.4) $$

where $K$ is the equilibrium constant (-), $\Delta G_r^\circ = \tfrac{1}{2}g^\circ_\mathrm{N_2} + \tfrac{3}{2}g^\circ_\mathrm{H_2} - g^\circ_\mathrm{NH_3}$ the standard Gibbs energy of reaction (J/mol NH~3~) with $g^\circ = h^\circ - Ts^\circ$ from the NASA-7 polynomials, $R$ = 8.314 J/(mol K), $T$ the temperature (K), $P$ the total pressure (bar), $p^\circ$ = 1 bar and $\hat\varphi_i$ the fugacity coefficients (-). For an ideal gas ($\hat\varphi_i$ = 1) the net exponent of $P$ is $\Delta\nu$ = +1. Substituting Eq. (13.3), with $(1/2)^{1/2}(3/2)^{3/2} = 3\sqrt{3}/4 \approx 1.299$ and $(1-X)(1+X) = 1-X^2$:

$$ K = \frac{3\sqrt{3}}{4}\,\frac{X^2}{1-X^2}\,\frac{P}{p^\circ} \qquad (13.5) $$

Solving for $X$ gives the closed form

$$ X_{\mathrm{eq}} = \left(1 + \frac{3\sqrt{3}}{4}\,\frac{P/p^\circ}{K(T)}\right)^{-1/2} \qquad (13.6) $$

At the baseline, 600 °C and 20 bar, $K$ = 658.4, so 1.299 × 20 / 658.4 = 0.0395 and $X_\mathrm{eq}$ = 1.0395^-1/2^ = 0.9808, identical to the numerical solver (0.98084). With non-ideal fugacity coefficients Eq. (13.6) no longer holds and the solver finds the root of the logarithm of Eq. (13.4) numerically. Taking logarithms of Eq. (13.5) and differentiating gives the sensitivity of the conversion to the equilibrium constant, used in Section 13.4:

$$ \frac{\mathrm{d}X}{\mathrm{d}\ln K} = \frac{X(1-X^2)}{2} \qquad (13.7) $$

It is 0.019 at the baseline and 0.19 at 250 °C and 10 bar, so data differences matter most where conversion is far from one.

<!-- data: results/validation/equilibrium_python_grid.csv T_C=600 P_bar=20 eos=ideal: K_eq 658.4463, nh3_conversion 0.9808364; amcrax.thermodynamics.equilibrium_constant(873.15) = 658.446; 0.980836 x (1 - 0.980836^2)/2 = 0.0186; results/validation/equilibrium_discrepancy_summary.json dXdlnK_range [1.42e-4, 0.192] -->

## 13.3 Results

The **independent Python calculation** gives $\Delta H_r^\circ$(298.15 K) = +45.899 kJ/mol NH~3~ and $\Delta G_r^\circ$(298.15 K) = +16.381 kJ/mol. Because the heat-capacity change of reaction is positive, $\Delta H_r$ rises from 50.27 kJ/mol at 250 °C to 54.22 kJ/mol at 600 °C and 55.70 kJ/mol at 900 °C, while $K$ rises from 5.387 to 658.4 and 4572 (Figure 13.1).

<!-- data: amcrax.thermodynamics.reaction_enthalpy_kJ_mol(298.15) = 45.8989, reaction_gibbs_kJ_mol(298.15) = 16.3811; results/validation/equilibrium_python_grid.csv K_eq, dH_rxn_kJ_per_mol_NH3 at T_C = 250, 600, 900 -->

![**Figure 13.1.** Equilibrium constant $K$ (left axis, logarithmic, standard state 1 bar) and reaction enthalpy $\Delta H_r$ (right axis, kJ/mol NH~3~) from 250 to 900 °C. Higher temperature favours conversion but raises the heat needed per mole cracked. *Source: independent Python calculation (NASA-7 / GRI-Mech 3.0 data).*](../../results/figures/equilibrium_K_and_dH_vs_T.png){width=80%}

Eq. (13.6) contains both trends of Le Chatelier's principle: conversion rises with temperature and falls with pressure (Table 13.1, Figure 13.2). At 1 bar it exceeds 99 % from 400 °C; at 20 bar 600 °C is needed to exceed 98 %. The pressure penalty is large below about 500 °C: at 400 °C conversion falls from 99.14 % at 1 bar to 81.02 % at 30 bar. At 20 bar the equilibrium NH~3~ mole fraction is 7.5 % at 400 °C, 2.4 % at 500 °C and 0.97 % at 600 °C (Figure 13.3), which sets the load on downstream NH~3~ removal.

<!-- data: results/validation/equilibrium_python_grid.csv eos=ideal nh3_conversion, y_NH3 at P_bar=20 (0.07468, 0.02448, 0.00967) -->

Table: **Table 13.1.** Equilibrium NH~3~ conversion (%) for a pure NH~3~ feed, ideal gas. *Source: independent Python calculation, results/validation/equilibrium_python_grid.csv.*

| T (°C) | 1 bar | 10 bar | 20 bar | 30 bar |
|---|---|---|---|---|
| 300 | 95.90 | 73.06 | 60.34 | 52.56 |
| 400 | 99.14 | 92.28 | 86.10 | 81.02 |
| 500 | 99.74 | 97.52 | 95.22 | 93.08 |
| 600 | 99.90 | 99.03 | 98.08 | 97.17 |
| 700 | 99.95 | 99.55 | 99.10 | 98.66 |

![**Figure 13.2.** Equilibrium NH~3~ conversion versus temperature at 1-40 bar, pure NH~3~ feed (solid: ideal gas; dashed: Peng-Robinson, $k_{ij}$ = 0). The curves converge above about 700 °C, so pressure costs conversion mainly in low-temperature designs. *Source: independent Python calculation.*](../../results/figures/equilibrium_conversion_vs_T.png){width=85%}

![**Figure 13.3.** Equilibrium mole fractions of NH~3~, H~2~ and N~2~ at 1 bar (left) and 20 bar (right). The gas tends to 75 % H~2~ and 25 % N~2~; at 20 bar appreciable NH~3~ remains below about 500 °C. *Source: independent Python calculation (solid: ideal gas; dashed: Peng-Robinson).*](../../results/figures/equilibrium_composition_vs_T.png){width=95%}

Non-ideality is small at the baseline: Peng-Robinson gives 98.07 % against 98.08 % for the ideal gas at 600 °C and 20 bar. The largest effect in the grid is at 250 °C and 40 bar, 29.36 % against 30.65 %. **Published literature** at 5 bar gives 91.9, 95.9, 97.8 and 98.7 % at 350, 400, 450 and 500 °C (Cechetto et al., 2023, Table 3); the Python model gives 91.91, 95.91, 97.80 and 98.74 %.

<!-- data: results/validation/equilibrium_python_grid.csv (600/20 pr 0.980720, ideal 0.980836; 250/40 pr 0.293576, ideal 0.306481; P_bar=5 ideal 0.919075, 0.959052, 0.977979, 0.987383); results/validation/literature_benchmarks.csv LIT-CECH-5-* -->

## 13.4 Comparison with Aspen RGibbs

The Aspen side is a single isothermal RGibbs block fed with pure NH~3~ at reactor conditions, run for 14 temperatures (250-900 °C) and 6 pressures (1-40 bar) with PENG-ROB and with IDEAL: 168 **Aspen Plus V15** points, each re-initialised (Section 12). The comparison is made like for like, ideal against IDEAL and Peng-Robinson against PENG-ROB (Tables 13.2 and 13.3, Figure 13.4). The 1.48 pp of a mixed comparison (Aspen PENG-ROB against Python ideal gas) is the fugacity effect itself, not a data error.

Table: **Table 13.2.** Equilibrium conversion, Aspen Plus V15 against the independent Python calculation (84 points per method, 250-900 °C, 1-40 bar, pure NH~3~). *Source: results/validation/equilibrium_discrepancy_summary.json; tolerances are engineering assumptions (validation_matrix.json EQ-IDEAL, EQ-PR).*

| Comparison | Max abs(ΔX) (pp) | Where | Mean abs(ΔX) (pp) | Tolerance (pp) |
|---|---|---|---|---|
| Aspen IDEAL vs Python ideal | 0.045 | 250 °C, 10 bar | 0.005 | 0.1 |
| Aspen PENG-ROB vs Python PR ($k_{ij}$ = 0) | 0.185 | 250 °C, 40 bar | 0.023 | 0.5 |
| Aspen PENG-ROB vs Python ideal (not like for like) | 1.476 | 250 °C, 40 bar | 0.098 | - |

Table: **Table 13.3.** Selected equilibrium conversions for a pure NH~3~ feed. *Source: Aspen Plus V15 simulation (results/validation/equilibrium_aspen_grid.csv); independent Python calculation (results/validation/equilibrium_python_grid.csv).*

| T (°C) | P (bar) | Aspen PENG-ROB | Aspen IDEAL | Python PR | Python ideal |
|---|---|---|---|---|---|
| 600 | 1 | 0.99901 | 0.99901 | 0.99901 | 0.99902 |
| 600 | 20 | 0.98079 | 0.98083 | 0.98072 | 0.98084 |
| 600 | 40 | 0.96256 | 0.96272 | 0.96229 | 0.96273 |
| 400 | 20 | 0.86025 | 0.86104 | 0.85967 | 0.86102 |
| 400 | 40 | 0.76460 | 0.76749 | 0.76330 | 0.76748 |
| 250 | 40 | 0.29172 | 0.30681 | 0.29358 | 0.30648 |

<!-- data: results/validation/equilibrium_discrepancy_summary.json max_abs_dX_ideal_vs_ideal_pp 0.04547, max_abs_dX_pr_vs_pr_pp -0.18534, max_abs_dX_aspenPR_vs_pythonIdeal_pp -1.4758, mean values; results/validation/equilibrium_aspen_grid.csv and equilibrium_python_grid.csv rows listed; results/validation/equilibrium_comparison.csv -->

![**Figure 13.4.** Equilibrium conversion, Aspen Plus V15 against the independent Python calculation: (a) parity of all 252 pairs; (b) ideal-gas deviation with the first-order prediction of Eq. (13.7) dotted; (c) Peng-Robinson deviation. Both like-for-like deviations vanish above about 600 °C and peak at 250 °C. *Source: Aspen Plus V15 simulation; independent Python calculation.*](../../results/figures/validation_parity_by_method.png){width=100%}

**Ideal gas: thermochemical data.** For every Aspen IDEAL point the equilibrium constant was back-calculated from the Aspen composition with Eq. (13.4) and compared with the Python $K(T)$ as an equivalent Gibbs-energy offset:

$$ \delta G = -RT\,(\ln K_\mathrm{Aspen} - \ln K_\mathrm{Python}) \qquad (13.8) $$

where $\delta G$ is in J/mol NH~3~. The offset runs smoothly from -10.3 J/mol at 250 °C through zero near 420 °C to +11.6 J/mol at 900 °C and changes by less than 0.001 J/mol over 1-40 bar at fixed temperature (Figure 13.5), so it belongs to the standard-state data (Aspen PURE41 against GRI-Mech 3.0), not to the solver. The ideal-gas conversion difference is **equivalent to an offset of at most 11.6 J/mol** (75 points with X < 0.999), magnified by Eq. (13.7) where conversion is far from one. This is a restatement, not an explanation: the offset is back-calculated from Aspen's composition, so Eq. (13.7) reproduces the deviations by construction (EQ-AMPLIFY is informational).

<!-- data: results/validation/equilibrium_discrepancy_summary.json dG_offset_aspen_minus_python_J_mol (min -10.334, max 11.642, n_resolved 75), dG_offset_max_spread_over_P_at_fixed_T_J_mol 9.38e-4, dG_offset_max_abs_resolved_J_mol 11.642; validation_matrix.json EQ-DG-ASPEN, EQ-AMPLIFY (informational) -->

**Comparison with NIST-JANAF.** JANAF minus Python is -9.7 to -14.9 J/mol and Aspen minus JANAF +4.6 to +23.7 J/mol over 250-900 °C. The mean absolute offset from JANAF is 13.3 J/mol for Aspen and 12.0 J/mol for Python, so both are about equally close: Aspen below about 400 °C, Python above about 450 °C. All three data sets agree within 25 J/mol, about 0.15 % of $\Delta G_r^\circ$(298 K). For the reaction enthalpy, the Aspen IDEAL duty per mole converted lies 0.001-0.050 kJ/mol below the Python $\Delta H_r(T)$, the Python value differs from JANAF by at most 0.039 kJ/mol, and $\Delta H_r^\circ$(298 K) is 45.899 kJ/mol (Python) against 45.898 kJ/mol (JANAF).

<!-- data: results/validation/equilibrium_discrepancy_summary.json dG_offset_janaf_minus_python_J_mol, dG_offset_aspen_minus_janaf_J_mol, mean_abs_dG_vs_janaf_J_mol (13.30, 11.96), dH_aspen_minus_python_kJ_mol (min -0.0501, max -0.0011); validation_matrix.json EQ-DG-JANAF, EQ-DH-JANAF (0.0386 kJ/mol), EQ-DH-ASPEN; docs/validation/discrepancy_analysis.md section 2 -->

![**Figure 13.5.** (a) Equivalent Gibbs-energy offset of the Aspen IDEAL data from the Python NASA-7 data at six pressures, and NIST-JANAF minus Python; (b) reaction enthalpy from Aspen IDEAL duty per mole converted, Python and NIST-JANAF. The pressure-independent offset identifies a standard-state data difference of the order of 10 J/mol. *Source: Aspen Plus V15 simulation; independent Python calculation; NIST-JANAF tables.*](../../results/figures/validation_lnK_offset.png){width=100%}

**Equation of state.** Non-ideality lowers the conversion in both codes, because the fugacity coefficient of NH~3~ falls below one at high pressure and low temperature. The effect grows with pressure, falls with temperature and is below 0.05 pp above 600 °C (Figure 13.6). At 250 °C and 40 bar it is -1.509 pp in Aspen and -1.291 pp in Python: Aspen's effect is about 17 % stronger. Using the Boston-Mathias α-function, which Aspen applies to supercritical components, changes the Python effect to -1.332 pp and explains 0.04 pp. **About 0.18 pp of the PENG-ROB gap (0.185 pp in total) remains unexplained.** Aspen retrieves binary parameters (PRKBV, EOS-LIT databank) at run time but does not expose them in its input forms, while Python uses $k_{ij}$ = 0. A sensitivity study, not a calibration, shows that this is an unlikely explanation: one $k_{ij}$ of +1.26 (NH~3~-H~2~) or +2.69 (NH~3~-N~2~) would be needed to close the gap, no value in [-2, 3] closes it for H~2~-N~2~, and all three pairs at +0.3 together close only 0.081 pp. Differences in critical constants, acentric factors or Aspen's α treatment are more plausible, but not verified. The gap passes the 0.5 pp tolerance.

<!-- data: results/validation/equilibrium_discrepancy_summary.json max_abs_eos_effect_aspen_pp -1.5089, max_abs_eos_effect_python_pp -1.2905, max_abs_eos_effect_diff_pp -0.2183, max_abs_eos_effect_diff_with_boston_mathias_pp -0.1769, kij_sensitivity_250C_40bar (1.2569, 2.6934, null, max_gap_reduction_within_range_pp 0.0811); results/validation/aspen_binary_parameters.json; validation_matrix.json EQ-PR, EQ-KIJ-SENS -->

![**Figure 13.6.** (a) Equation-of-state effect on conversion, X(Peng-Robinson) minus X(ideal), in Aspen (solid) and Python with $k_{ij}$ = 0 (dashed); (b) difference of the two effects. Both codes agree on sign and trend; the residual difference is largest at 250 °C and 40 bar. *Source: Aspen Plus V15 simulation; independent Python calculation.*](../../results/figures/validation_eos_effect.png){width=100%}

The baseline flowsheet gives 0.98081, slightly above the 0.98079 of the pure-NH~3~ PENG-ROB grid point, because the 0.2 mol% feed water dilutes the reacting gas.

<!-- data: results/simulations/baseline.json kpis.nh3_conversion 0.980810; results/validation/equilibrium_aspen_grid.csv 600/20 PENG-ROB 0.980792 -->

## 13.5 A third implementation in the browser

The public website (Section 23) has an in-browser calculator, `frontend/src/calc/equilibrium.ts`: a TypeScript port of the ideal-gas case using the same NASA-7 data and the closed form of Eq. (13.6), labelled as an ideal-gas calculation, not an Aspen result. Its unit tests compare it with nine rows of the Python grid (250-900 °C, 1-40 bar; conversion and mole fractions within 10^-4^, $K$ within 10^-5^ relative, $\Delta H_r$ within 0.005 kJ/mol) and check Eq. (13.5) to 10^-12^. The ideal-gas equilibrium is thus computed by three separate implementations: the closed form in the browser and the Python solver agree to within the test tolerances, and both agree with Aspen RGibbs IDEAL to within 0.045 pp.

<!-- data: frontend/src/calc/equilibrium.ts; frontend/src/calc/equilibrium.test.ts (REF rows copied from results/validation/equilibrium_python_grid.csv, tolerances) -->
