# Uncertainty quantification

This page summarises three uncertainty studies of the AmCraX models. Each one shows how uncertain a model's output is,
given the stated input ranges. **None of them is experimental validation.** AmCraX has no experimental validation. The
calibration data are few, all at 1 atm, and partly the same data the source papers used to fit their parameters.

The methods follow published sources:
- **Sobol indices:** first-order indices by Saltelli et al. (2010) on centred outputs, total-effect indices by Jansen
  (1999).
- **Grouped cost drivers:** design-for-cost grouping after Stewart and Shirvan (2022).
- **Right-skewed CAPEX case:** shape after Stewart and Shirvan (2023).
- **Sensitivity before calibration:** Che (2022).
- **Bayesian inverse UQ with a model-discrepancy term and a calibration/validation split:** Wu, Kozlowski, Meidani and Shirvan (2018, Parts 1 and 2), and Kennedy and O'Hagan (2001).
- **Sampler:** adaptive Metropolis (Haario et al., 2001).
- **Convergence checks:** Vehtari et al. (2021).

Full entries are in `research/reference_additions/phase2_methodology.json`. The code uses numpy and scipy only, and
every random stream uses seed 20261123.

| Study | Script | Results |
|---|---|---|
| T1 global sensitivity of the cost model | `scripts/research/uq_gsa_sobol.py` | `results/research/uq/gsa_sobol.json`, `gsa_cost_decomposition.json`, figure `uq_gsa_sobol.png` |
| T2a propagation of published kinetic intervals | `scripts/research/uq_kinetic_propagation.py` | `results/research/uq/kinetic_param_propagation.json` (+ samples CSV), figure `uq_kinetic_T_required.png` |
| T2b Bayesian calibration diagnostic of the Takahashi law | `scripts/research/uq_takahashi_calibration.py` | `results/research/uq/takahashi_calibration_{ni,ru}.json`, figure `uq_takahashi_ppc.png` |
| Acceptance checks | `scripts/research/uq_build_validation.py` | `results/research/validation/uq.json` |

## T1. Which input dominates the levelised cost of hydrogen?

**Model and inputs.** The model is `amcrax.economics.singapore.evaluate` on the unified reference scenario. It is
applied to the stored Aspen Plus V15 baseline, with heat integration on and off as separate cases. It uses 10 independent
inputs, with the same distributions as the existing Monte Carlo study:
- NH3 price
- electricity price
- CAPEX multiplier
- CAPEX scaling exponent
- catalyst price
- catalyst lifetime
- discount rate
- operating hours
- plant life
- PSA recovery

**Sampling and checks.**
- Scrambled Sobol sample, N = 8192.
- 95 % bootstrap intervals, from 1000 resamples.
- The estimator reproduces the analytic Ishigami indices within 0.0017, against a tolerance of 0.02. The Ishigami values
  were checked against Marrel et al. (2009) and the closed form of Ishigami and Homma (1990).
- It reproduces a linear test function within 6e-5.
- A dummy input (the carbon tax, which has no effect on ammonia-fired heat) gets indices of exactly 0.
- The top-3 ranking is the same at N = 4096 and N = 8192 in every case.

**Result (grey scenario, 450 USD/t, heat integration on).**
- Mean LCOH is 4.02 USD/kg H2, with a 90 % range of 3.21 to 4.84 USD/kg.
- The NH3 price carries almost all of the variance (table below).
- The CAPEX multiplier (ST 0.063) and PSA recovery (ST 0.033) come next. Every other input has a total index of about
  0.005 or less.
- The order is the same with heat integration off. The NH3 total index ranges from 0.64 (green current) to 0.94 (green 2030).
- A right-skewed lognormal CAPEX distribution does not change the top-3 ranking in any case.

| Input or group | Total index ST (95 % CI) |
|---|---|
| NH3 price (feed group; it also prices the ammonia-fired heat) | 0.896 (0.875 to 0.917) |
| Capital group: CAPEX multiplier, exponent, discount rate, plant life | 0.069 |
| Operation group: hours, electricity, PSA recovery | 0.036 |
| Catalyst group: price and lifetime | below 0.001 |

The reconversion cost is LCOH minus the feed-ammonia cost. Its ranking is different:
- the CAPEX multiplier comes first, with ST 0.47;
- PSA recovery comes second, with ST 0.42;
- the NH3 price has ST 0.06.

At the base point, feed ammonia makes up 76 % of LCOH in the grey case. This figure is cost accounting, not sensitivity.
The CAPEX split into ISBL items and the OSBL, engineering and contingency block is in `gsa_cost_decomposition.json`.

**Threshold.** Above a certain NH3 price, the feed cost is larger than all other LCOH items combined. That threshold is
115 USD/t at the base point, and 174 USD/t when every non-feed input is set to its adverse bound. Every sourced scenario
price (300 to 1052 USD/t) is above it.

The NH3 price at which LCOH equals the 3.06 USD/kg hydrogen benchmark of the reference scenario is:
- 320 USD/t at the base point;
- 379 USD/t with every non-feed input at its favourable bound.

Only the low end of the grey range reaches this price.

**Limits.**
- The indices depend on the stated input ranges.
- The NH3 prices are scenarios, not Singapore transaction prices.
- The CAPEX method has no Singapore location factor.
- Electricity and catalyst have near-zero indices because their cost items are small at the base point: 0.001 and
  0.002 USD/kg. The stored baseline charges electricity for pump power only. This is a property of the model boundary,
  not evidence that these inputs are unimportant in a real plant.
- The first-order estimator is applied to centred outputs (the mean of f(A) and f(B) is subtracted). Before the fix
  pass of 24 November 2026 it used uncentred outputs, which has the same expectation but a larger variance: the 95 %
  interval of the first-order index of the NH3 price (grey, heat integration on) was 0.662 to 1.134 and is now 0.870 to
  0.921 (point estimate 0.8956 before and after). The total-effect indices use differences only and are unchanged.
- The indices, and every probability quoted from the Monte Carlo sample, are conditional on the assumed input
  distributions.

## T2a. Effect of the published kinetic-parameter intervals

**Data.** Lucentini et al. (2021) report k0, Ek, K1 and K4 with intervals but no covariance. Two assumptions are made
and labelled as such:
- The intervals are treated as 95 % marginal intervals.
- Three correlation cases are propagated:
  - C1, independent;
  - C2, centred at 475 degC;
  - C3, draws whose predicted Table 1 conversions fall inside the paper's ±10 % parity band. Of the C1 draws, 15 % and
    13 % are accepted for the two catalysts.

**Model.** The existing isothermal PFR is used without change. The parameters are passed in through an optional
override keyword. With nominal parameters, the model reproduces the stored studies to within 0.1 K and 0.1 %.

**Sample size.** 4000 Latin-hypercube draws per case. The rank correlation between k0 and the required temperature is
only -0.13 in C1: in the independent case, the Ek interval dominates the spread.

| Output (5Ni1Ru/CeO2) | C1 independent, p5 to p95 | C2 centred, p5 to p95 |
|---|---|---|
| T for X = 0.99, W = 1000 kg per 100 kmol/h, 1 atm | 417 to 492 degC | 447 to 460 degC |
| T for X = 0.95, W = 100 kg, 20 bar (extrapolation) | 529 to 615 degC | 563 to 581 degC |
| Catalyst mass for 99 % of equilibrium, 600 degC, 20 bar (extrapolation) | 24 to 158 kg | 49 to 76 kg |
| LCOH, grey, Ru price as upper proxy | 4.017 to 4.035 USD/kg | 4.020 to 4.024 USD/kg |

**Findings.**
- The spread is dominated by how k0 and Ek are assumed to be correlated. The independent case is an upper bound.
- At 20 bar the 99 % target is limited by equilibrium, not by kinetics: every draw needs 684.8 degC.
- An absolute conversion of 0.99 cannot be reached at 600 degC and 20 bar, because equilibrium conversion there is 0.981.
- Catalyst inventory affects LCOH only through the catalyst replacement cost. The effect is below 0.05 USD/kg even at
  the Ru price proxy. No sourced Ni-Ru/CeO2 price exists, so the Ni (33.4 USD/kg) and Ru (542 USD/kg) prices are used
  as bounds.
- Every result above 1 atm is an extrapolation of a 1 atm laboratory fit.

## T2b. Is the Takahashi temperature dependence consistent with the paper's own extrapolation data?

**Data.** About 60 conversions from Takahashi and Fujitani (2016) were read from the published figures, with an
accuracy of about ±2 percentage points, all at 1 atm. They are split into:
- calibration data (the temperature series and one space-velocity series);
- held-out data (the other space-velocity rows, the NH3 dilution series and the H2 co-feed series);
- the paper's own fitting data, which are reported separately.

**Model.** Three quantities are calibrated:
- a scale factor s, which absorbs the unreported catalyst mass;
- a shift dE of one activation energy;
- an iid discrepancy term sigma_d.

A local screening step chose which activation energy to shift: the rate constant with the largest effect on the
calibration data. For Ni this is k2, the rate-determining step. For Ru it is also k2, while the rate-determining step is
k3. The k3 result is reported as well.

The PFR is tabulated on a grid of (ln s, dE) values and interpolated. Against direct solves, the interpolation is
accurate to better than 0.001 in conversion.

**Checks.**
- R-hat is below 1.01 and the bulk ESS is above 1000 for every parameter.
- Synthetic recovery covers the true value in 18 of 20 data sets for ln s, and in 20 of 20 for dE.

| | Ni (k2) | Ru (k2) |
|---|---|---|
| dE posterior median (90 % interval) | +12 kJ/mol (-3 to +27) | +2 kJ/mol (-26 to +34) |
| Posterior sd of dE, against a prior sd of 20 | 8.9 | 18.3 |
| sigma_d median | 0.018 | 0.031 |
| Held-out points inside the 90 % predictive band | 11 of 19 | 16 of 19 |

**Findings.**
- For both catalysts the interval contains 0, so the published temperature dependence is consistent with the data
  within reading error.
- For Ru this statement is weak. The posterior is barely narrower than the prior, and widening the prior to sd 40 moves
  the mean by 11 kJ/mol.
- The held-out checks find a model-form problem that a temperature shift cannot remove. The model under-predicts every
  point of the H2 co-feed series (by 0.07 to 0.09 on average) and the Ni NH3-dilution series (by 0.06).
- This agrees with the existing prediction failures KIN-NI-PRED and KIN-RU-PRED.
- No parameter in `kinetics.yaml` was changed.
- The result is not carried over to plant catalyst mass or cost, because the catalyst mass used in the experiments is
  not reported.

## Limits common to all three studies

- These studies quantify uncertainty under stated assumptions. They are not experimental validation of AmCraX.
- The kinetic calibration data are few, all at 1 atm, read from figures, and partly the fitting data of the source
  papers.
- Every kinetic result above 1 atm is an extrapolation.
- The cost study shows only the variance that the chosen input ranges create. It cannot detect inputs or model-structure
  errors that lie outside those ranges.
