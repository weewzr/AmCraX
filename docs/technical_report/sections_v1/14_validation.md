<!-- cites: nist_janaf, cechetto2023membrane, xu2025review, maccarrone2025comprehensive, kum2026heatintegrated, hansen2024hysys, farokhi2025costoptimization, takahashi2016kinetic, dicarlo2014ammonia -->

# 14 Model validation

## 14.1 Strategy and validation matrix

AmCraX has two independent models: the **Aspen Plus V15 simulation** and the **independent Python calculation**. Each is checked against the other, against reference data and literature, and for internal consistency. Every check is one item in a validation matrix. An item passes only with a computed metric and a tolerance stated as an engineering assumption. Failing items are kept and never relaxed. The matrix holds 130 items: 103 pass, 22 fail, 0 not run and 5 informational (Table 14.1). All 22 failures come from two documented root causes. The full list is in the appendix.
<!-- data: results/validation/validation_matrix.json summary (n_items, pass, fail, not_run, informational, by_family, failure_root_causes) -->

Table: **Table 14.1.** Validation items by family and status. *Source: results/validation/validation_matrix.json.*

| Family | Items | Pass | Fail | Info. |
|---|---|---|---|---|
| Thermochemistry and equilibrium (THERMO, EQ) | 13 | 12 | 0 | 1 |
| Aspen internal consistency (BAL-ASPEN, SENS, STEMP, FEED-PROP) | 31 | 31 | 0 | 0 |
| Flowsheet, all key KPIs (FS) | 20 | 0 | 20 | 0 |
| Flowsheet, primary quantities (FS-PRIMARY) | 20 | 20 | 0 | 0 |
| Literature (LIT) | 14 | 11 | 0 | 3 |
| Kinetics (KIN) | 4 | 1 | 2 | 1 |
| Optimisation, economics, environment, Python balances, test suite | 28 | 28 | 0 | 0 |

<!-- data: results/validation/validation_matrix.json summary.by_family -->

## 14.2 Thermochemistry and equilibrium

Python thermochemistry was compared with **NIST-JANAF** (National Institute of Standards and Technology, n.d.). Over 250–900 °C, the reaction Gibbs energy deviates by at most 14.9 J/mol NH~3~ and the reaction enthalpy by at most 0.039 kJ/mol.
<!-- data: results/validation/validation_matrix.json items EQ-DG-JANAF, EQ-DH-JANAF -->

Equilibrium was compared like for like over 84 temperature–pressure points: Aspen IDEAL with Python ideal gas, Aspen PENG-ROB with Python Peng–Robinson (Table 14.2, Figure 14.1). The 1.48 pp of a mixed comparison is the fugacity effect, not a data error. The ideal-gas deviations come from a pressure-independent Gibbs offset between the Aspen and Python standard-state data, which runs from −10.3 to +11.6 J/mol. Conversion responds to it through

$$ \frac{dX}{d\ln K} = \frac{X(1-X^2)}{2} \qquad (14.1) $$

where *X* is the NH~3~ conversion (–) and *K* the equilibrium constant (–). This sensitivity ranges from 1.4 × 10^−4^ to 0.19. The first-order prediction reproduces every ideal-gas deviation to within 1.7 × 10^−5^ pp. At 250 °C and 40 bar the equation-of-state effect is −1.51 pp in Aspen and −1.29 pp in Python. A different α-function explains 0.04 pp of the gap, and 0.18 pp remains unexplained. Aspen's databank binary parameters are a likely cause, but this is not verified: the Aspen input forms do not expose these k~ij~ values.
<!-- data: results/validation/equilibrium_discrepancy_summary.json; results/validation/aspen_binary_parameters.json; docs/validation/discrepancy_analysis.md -->

Table: **Table 14.2.** Equilibrium conversion, Aspen Plus V15 vs independent Python calculation (84 points, 250–900 °C, 1–40 bar, pure NH~3~). *Source: results/validation/equilibrium_discrepancy_summary.json.*

| Comparison | Max abs(ΔX), pp | Mean abs(ΔX), pp | Tolerance, pp |
|---|---|---|---|
| Aspen IDEAL vs Python ideal | 0.045 | 0.005 | 0.1 |
| Aspen PENG-ROB vs Python PR | 0.185 | 0.023 | 0.5 |
| Aspen PENG-ROB vs Python ideal (not like for like) | 1.476 | 0.098 | – |

![**Figure 14.1.** Equilibrium conversion parity and deviations, Aspen Plus V15 vs independent Python calculation. Panel (b) shows the deviations predicted by Eq. (14.1) as dotted lines. *Source: Aspen Plus V15 simulation; independent Python calculation.*](../../results/figures/validation_parity_by_method.png){width=100%}

![**Figure 14.2.** Equation-of-state effect X(PR) − X(ideal) in each code, and the difference between the two. *Source: Aspen Plus V15 simulation; independent Python calculation.*](../../results/figures/validation_eos_effect.png){width=95%}

## 14.3 A defect found by validation

In the first Aspen grid, one IDEAL point (600 °C, 30 bar) gave a duty-to-conversion ratio 1.24 kJ/mol off. For an ideal gas this ratio cannot depend on pressure. The point had carried the previous point's duty: the automation ran the engine asynchronously and read the duty while Aspen was still loading results. The fix: synchronous engine runs, re-initialisation at every grid point, and two guards (repeatability and pressure independence). In the regenerated grid, the pressure spread of the ratio is 3.2 × 10^−7^ kJ/mol. Flowsheet runs always re-initialise and were unaffected. The validation worked as intended.
<!-- data: results/validation/validation_matrix.json items EQ-GRID-STALE, EQ-DH-ASPEN; docs/validation/discrepancy_analysis.md section 6 -->

## 14.4 Aspen internal consistency

All 20 stored Aspen cases close mass, element and energy balances to 4.5 × 10^−9^ or better. The 91 sensitivity runs all converged, with closures below 4.5 × 10^−9^. Aspen's native Sensitivity block and the COM-driven study agree to 4.8 × 10^−10^ at nine temperatures. Specific outputs are independent of feed rate to within 2.9 × 10^−9^.
<!-- data: results/validation/validation_matrix.json items BAL-ASPEN-*, SENS-*, STEMP-*, FEED-PROP; results/validation/aspen_internal_consistency.csv -->

## 14.5 Flowsheet cross-check

Each Aspen case was re-run with the Python model using identical inputs. All 20 FS items fail the 2 % tolerance on key KPIs, for one reason. The Python vaporiser dew point (ideal-liquid model) is about 5.8 K below Aspen PENG-ROB, and liquid-ammonia enthalpy comes from a different equation of state. The vaporiser duty therefore differs by about 3.5 %, recovered heat by up to 5.6 % and cooler duty by up to 10.8 %. The FS-PRIMARY family excludes the feed section and checks conversion, composition, product flow, purity, yield, reactor duty, tail gas and flame temperature. All 20 FS-PRIMARY items pass, at no more than 12 % of their tolerance.
<!-- data: results/validation/validation_matrix.json items FS-*, FS-PRIMARY-*; results/validation/aspen_vs_python_flowsheet.csv -->

## 14.6 Literature benchmarks

**Published literature** is comparable where conditions are fully stated. Fourteen tabulated equilibrium conversions (Cechetto et al., 2023) agree within 0.15 pp. Nine printed reaction enthalpies agree within 0.32 kJ/mol, and 16 values read from figures (Cechetto et al., 2023; Xu et al., 2025) agree within 1.5 pp. The temperature at which ΔG = 0 is 455.9 K, against the approximately 450 K stated by Maccarrone et al. (2025). The Gibbs correlation of Kum et al. (2026) agrees within 0.53 kJ. Three items are not comparable: the sources omit the pressure or use another reactor boundary (Hansen et al., 2024; Farokhi et al., 2025; Kum et al., 2026), or the correlations are misprinted.
<!-- data: results/validation/literature_benchmarks.csv; validation_matrix.json items LIT-* -->

## 14.7 Kinetics

Rate constants from the published Arrhenius parameters match the tabulated values within 6.8 % (Takahashi & Fujitani, 2016). Reactor predictions do worse (Figure 14.3); W/F was inferred from one anchor point per catalyst because the catalyst mass is not reported. Six of 12 Ni points and six of 11 Ru points fall outside the 0.05 tolerance, with a maximum of 0.11. All of these are under-predictions, at diluted NH~3~ or with H~2~ co-feed. Both items fail. The Di Carlo et al. (2014) data agree within 0.004, but the rate law was fitted to them, so this result is informational only.
<!-- data: results/validation/kinetics_validation.csv; validation_matrix.json items KIN-* -->

![**Figure 14.3.** Microkinetic PFR conversion vs values read from the figures of Takahashi and Fujitani (2016). *Source: independent Python calculation; published literature.*](../../results/figures/kinetics_validation.png){width=95%}

## 14.8 Optimisation candidates

Ten optimisation candidates, at exactly the reported optima, were re-solved in Aspen. Judged by the criterion stated in the verification file, all converged and all 11 primary metrics agree within 1.24 % (tolerance 2 %). LCOH agrees within 0.25 %. Secondary metrics such as recovered heat and cooling-water cost deviate by up to 10.4 %, for the feed-section reason above. Of 13 reported optima, the 12 flagged feasible respect all bounds and constraints. The one remaining optimum is labelled infeasible.
<!-- data: results/optimisation/aspen_verification.json; results/optimisation/single_objective.json; validation_matrix.json items OPT-ASPEN, OPT-FEAS -->

## 14.9 Not validated

The following were not validated: the reduced-order PSA and membrane models, the cost estimates, the carbon-intensity accounting (not an LCA) and the kinetics at 20 bar (the data are at 1 atm, or up to 10 bar for Di Carlo et al.). No plant data were available.
<!-- data: results/validation/validation_matrix.json (no items for these components); results/validation/kinetics_validation.csv conditions -->
