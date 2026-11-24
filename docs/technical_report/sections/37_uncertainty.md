<!-- cites: saltelli2010sobol, jansen1999anova, kennedy2001calibration, haario2001adaptive, vehtari2021rhat, wu2018iuqpart1, lucentini2021nirukinetic, takahashi2016kinetic -->

# 37 Uncertainty quantification

Phase 2 added three published methods that are standard in nuclear-engineering model assessment to the one-at-a-time sensitivity and Monte Carlo analyses of Sections 17 and 27: variance-based global sensitivity analysis, propagation of published kinetic-parameter intervals, and Bayesian calibration used as a model-form diagnostic. None of the three is experimental validation. They show how much of the output uncertainty each input explains and whether a rate law is consistent with its own data; they do not show that the model is correct.

## 37.1 Variance-based global sensitivity (Sobol indices)

First-order (S1) and total-effect (ST) Sobol indices were estimated with the Saltelli sampling scheme (Saltelli et al., 2010) and the Jansen estimator for the total effect (Jansen, 1999), with N = 8192 base samples, d = 10 inputs, seed 20261123 and 1000 bootstrap resamples for the confidence intervals. The ten inputs are the NH~3~ price, electricity price, CAPEX multiplier, CAPEX scaling exponent, catalyst price, catalyst lifetime, discount rate, operating hours, plant life and PSA recovery; their ranges are those of the Monte Carlo and tornado analyses on the unified basis. The carbon tax was added in a separate run as a dummy input.

Table: **Table 37.1.** Total-effect Sobol indices of the LCOH, grey NH~3~, heat integration on. *Source: independent Python calculation, results/research/uq/gsa_sobol.json cases.grey|heat_integration_on.*

| Input or group | ST [95 % CI] |
|---|---|
| NH~3~ price | 0.896 [0.875, 0.917] |
| CAPEX multiplier | 0.063 |
| PSA recovery | 0.033 |
| CAPEX exponent | 0.005 |
| Capital group | 0.069 |
| Operation group | 0.036 |
| Catalyst group | 1e-5 |
| Electricity | about 0 |

<!-- data: results/research/uq/gsa_sobol.json (N 8192, d 10, seed 20261123; LCOH mean 4.017, 90 % range 3.206-4.840; ST values; REC ST capex 0.473, PSA 0.420, NH3 0.059; NPV NH3 ST 0.926) -->

The LCOH has a mean of 4.017 USD/kg and a 90 % range of 3.206 to 4.840 USD/kg in the Sobol sample (3.25 to 4.88 in the separate Monte Carlo of Section 27); both are conditional on the assumed input distributions. The NH~3~ price explains about 90 % of its variance; its first-order index is also {{VAL:uq/gsa_sobol.json#cases/grey|heat_integration_on/outputs/lcoh_USD_per_kg/indices/nh3_price_USD_per_t/S1|.3f}} [{{VAL:uq/gsa_sobol.json#cases/grey|heat_integration_on/outputs/lcoh_USD_per_kg/indices/nh3_price_USD_per_t/S1_ci/0|.3f}}, {{VAL:uq/gsa_sobol.json#cases/grey|heat_integration_on/outputs/lcoh_USD_per_kg/indices/nh3_price_USD_per_t/S1_ci/1|.3f}}]. The first-order estimator centres the outputs (the mean of the two base samples is subtracted); an earlier uncentred estimator gave the same index with a much wider interval, [0.66, 1.13], and was corrected after the independent review (Section 31.4). The total-effect indices did not change. The NH~3~-price total effect is 0.726 for blue, 0.636 for green at current prices, 0.944 for green 2030 and 0.899 for grey without heat integration. For the NPV it is 0.926. The reconversion cost (all items except feed) behaves differently: CAPEX multiplier ST 0.473, PSA recovery 0.420, NH~3~ price 0.059. Electricity has almost no index because the cost boundary includes pump power only (Section 32.4). The ranking of the top three inputs is unchanged when the CAPEX distribution is changed from triangular to lognormal and between N = 2^12^ and 2^13^.

![**Figure 37.1.** First-order and total-effect Sobol indices of the LCOH and the reconversion cost. *Source: independent Python calculation, results/figures/research/uq_gsa_sobol.png.*](../../results/figures/research/uq_gsa_sobol.png){width=85%}

The method was checked on test functions with known indices: the Ishigami function (maximum error 0.0017 against a tolerance of 0.02) and a linear function (error 5e-5 against 0.01); a dummy input (the carbon tax, which is zero in Mode A) gives S1 = ST = 0 exactly. The mean LCOH agrees with the Monte Carlo analysis within 0.27 % in all four scenarios.

## 37.2 Propagation of published kinetic-parameter intervals

The Lucentini et al. (2021) rate laws for the two NiRu/CeO~2~ catalysts were propagated with 4000 Latin-hypercube draws per case, under three treatments of the published intervals (C1 independent, C2 correlated, C3 constrained to reproduce the published points; acceptance rates 15.3 % and 12.5 %). The intervals are treated as 95 % intervals (an assumption).

For 5Ni1Ru/CeO~2~ the temperature needed for 99 % conversion with 1000 kg at 1 atm spans 417 to 492 °C (p5 to p95) under C1 and 447 to 460 °C under C2. At 20 bar, the temperature for 95 % conversion with 100 kg spans 529 to 615 °C (C1), an extrapolation in pressure. At 20 bar and 99 % conversion every draw needs 684.77 °C: the result is limited by equilibrium, so the kinetic parameters do not matter there. The effect on the LCOH is small: 4.017 to 4.035 USD/kg (C1) for 5Ni1Ru, up to 4.049 for 2.5Ni0.5Ru, less than 0.035 USD/kg in every case. This effect acts only through the catalyst replacement cost and was computed at the published TEA ruthenium price as a proxy.

![**Figure 37.2.** Temperature needed for a target conversion under the propagated kinetic-parameter uncertainty, at 1 atm (inside the fitted range) and 20 bar (extrapolation). *Source: independent Python calculation, results/figures/research/uq_kinetic_T_required.png.*](../../results/figures/research/uq_kinetic_T_required.png){width=85%}

## 37.3 Bayesian calibration as a model-form diagnostic

The Takahashi and Fujitani (2016) microkinetic laws for Ni/MgO and Ru/MgO were calibrated against digitised points from the same paper, in the spirit of the Bayesian calibration of computer models (Kennedy & O'Hagan, 2001) as applied to inverse uncertainty quantification in nuclear thermal-hydraulics (Wu et al., 2018a). Two parameters were calibrated per catalyst (a scale factor s and an activation-energy shift dE of the most sensitive step) with an adaptive Metropolis sampler (Haario et al., 2001); convergence was checked with the rank-normalised R-hat and effective sample size (Vehtari et al., 2021): R-hat at most 1.009 and bulk ESS at least 1190. The forward model was tabulated on a grid and interpolated; the surrogate error is at most 9.7e-4 against a tolerance of 0.002.

Table: **Table 37.2.** Calibration of the Takahashi laws: posterior of the activation-energy shift and coverage of held-out data by the 90 % predictive band. *Source: independent Python calculation, results/research/uq/takahashi_calibration_ni.json and takahashi_calibration_ru.json.*

| | Ni/MgO | Ru/MgO |
|---|---|---|
| dE p50 (90 % interval), kJ/mol | +12.0 (-2.6 to +26.5) | +1.8 (-25.6 to +34.1) |
| Posterior sd of dE (prior sd 20) | 8.9 | 18.3 |
| Coverage of held-out points | 11/19 | 16/19 |
| Coverage of calibration points | 8/8 | 6/6 |

By the rule set before the calibration, both laws are "consistent within reading error" in their temperature dependence. For Ru this is weak, because the posterior is close to the prior. The held-out data show a model-form error: the H~2~ co-feed and NH~3~-dilution series are under-predicted, with mean residuals of +0.087 and +0.063 (Ni) and +0.075 (Ru, H~2~ co-feed), all of one sign. This agrees with the failing prediction checks KIN-NI-PRED and KIN-RU-PRED (Section 38). No calibrated value was propagated to plant results, and the stored kinetic parameters are unchanged.

![**Figure 37.3.** Posterior predictive check of the calibrated Takahashi laws against calibration and held-out data. *Source: independent Python calculation, results/figures/research/uq_takahashi_ppc.png.*](../../results/figures/research/uq_takahashi_ppc.png){width=85%}

## 37.4 Checks

The uncertainty workstream has 84 checks: 78 numerical verifications pass, 4 are informational, and 2 comparisons with published literature (the posterior predictive checks) are informational. None is experimental validation.
<!-- data: results/research/validation/uq.json -->
