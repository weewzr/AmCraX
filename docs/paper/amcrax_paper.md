---
title: "Ammonia cracking for hydrogen supply in Singapore: a threshold-based test of four hypotheses with an Aspen Plus flowsheet, Python models and uncertainty quantification"
author: "AmCraX project"
date: "23 November 2026"
---

# Abstract

Ammonia is proposed as a hydrogen carrier for Singapore, but it is not settled when the ammonia should be cracked back to hydrogen and what decides the cost. This paper tests four hypotheses from an earlier essay: end-use suitability (H1), feedstock (H2), catalyst and heat integration (H3) and purification (H4). The methods are an Aspen Plus V15 flowsheet (600 °C, 20 bar) with RPlug reactors for five published rate laws, Python models, one frozen cost scenario and Sobol uncertainty analysis. The verdict rule was written down before the analysis. A row that rests on an assumption can only be supported by a threshold analysis against sourced values. The reference levelised cost of hydrogen is 4.015 USD/kg (5.174 SGD/kg), of which ammonia feed is 76 %. The ammonia price explains about 90 % of its variance (total-effect index 0.896). H1 is INCONCLUSIVE: direct ammonia combustion is 8 to 17 % cheaper than standalone cracking at equal turbine efficiency. Cracking with pressure-swing adsorption would need a turbine 12.6 percentage points more efficient, above the only sourced bound of 7.3. Against the essay, exhaust-heated cracking is 1.3 % cheaper than direct use on the reference basis. H2 is MIXED: affordable and low-carbon ammonia are necessary, but under the actual Singapore carbon tax low-carbon ammonia earns no cost advantage. H3 is PARTIALLY SUPPORTED: heat integration pays after the exchanger cost, but at ruthenium prices derived from metal content the low-temperature catalysts do not pay. H4 is PARTIALLY SUPPORTED. AmCraX has no independent experimental validation.

# 1 Introduction

## 1.1 Context

Singapore is studying ammonia as a low-carbon fuel for power generation and bunkering (Maritime and Port Authority of Singapore, 2025). Ammonia carries 17.8 % hydrogen by mass, liquefies at modest pressure and is traded at scale. To deliver molecular hydrogen, the ammonia must be decomposed (cracked) over a catalyst at high temperature and the product purified. Each step costs energy and capital, and the ammonia itself is not cheap. Recent process and techno-economic studies cover parts of this chain (Chopra et al., 2026; Cho et al., 2026; Farokhi et al., 2025; Kum et al., 2026; Mehr et al., 2026; Richard et al., 2024), and turbine studies compare direct ammonia combustion with cracked fuel (Ahmad et al., 2025; Halim et al., 2025). The studies differ in plant size, cost basis, catalyst, purity target and end use, so their conclusions cannot be compared directly.

An earlier essay by the project author argued four positions on this question. This paper tests them with one consistent model chain and one cost basis, and reports where the evidence does not support the essay.

## 1.2 The four hypotheses

- **H1, end-use suitability.** Cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly.
- **H2, feedstock.** Affordable, low-carbon ammonia is essential to economic and environmental competitiveness.
- **H3, catalyst and heat integration.** Low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh a higher catalyst cost.
- **H4, purification.** Purification must balance purity requirements against recovery losses, energy and equipment cost.

Each hypothesis joins several claims. H2, for example, makes an economic claim and an environmental claim, and can also be read as saying that low carbon intensity is rewarded economically. Section 2.5 describes how the hypotheses were split into components and rows before any Phase 2 result was computed.

## 1.3 Contribution

The paper makes three contributions. First, it costs every pathway on one frozen reference scenario, so that differences between pathways are not differences between cost bases. Second, where a conclusion depends on an assumed quantity (for example, the efficiency of a turbine on hydrogen-rich fuel), it computes the value at which the conclusion reverses and compares that threshold with sourced values. Third, it states for every number which of four kinds of evidence supports it: numerical verification, Python against Aspen comparison, comparison with published literature, or independent experimental validation. AmCraX has none of the last kind.

# 2 Methods

## 2.1 Aspen Plus V15 flowsheet

The baseline flowsheet converts saturated liquid ammonia (99.8 mol% NH~3~, 0.2 mol% H~2~O, 100 kmol/h, 1.013 bar) into hydrogen in a single train without recycle. A pump raises the liquid to 21 bar. A vaporiser heats it to 10 K above the dew point. A feed/effluent heat exchanger (FEHE) heats the vapour to 550 °C against the reactor effluent, and a trim heater closes the last 50 K. The baseline cracker is an isothermal RGibbs equilibrium reactor at 600 °C and 20 bar, which reaches an NH~3~ conversion of 0.9808. The cracked gas is cooled to 40 °C and sent to a pressure-swing adsorption (PSA) unit, modelled as a reduced-order splitter with an assumed hydrogen recovery of 0.85. The tail gas is burned with 15 % excess air, and its heat is credited against the process heat demand. The property method is PENG-ROB (Peng & Robinson, 1976). The baseline produces 251.6 kg/h of hydrogen at 99.96 mol%. This purity follows from the assumed PSA split fractions; it is not a prediction.

The recovery of 0.85 is above the published range of about 0.71 to 0.81 for comparable PSA units. Its effect is tested in Sections 2.6, 3.4 and 3.5.

## 2.2 Kinetic reactors in Aspen RPlug

The equilibrium reactor carries no catalyst, so H3 needs a reactor in which the catalyst sets the conversion. Published rate laws were implemented in Aspen RPlug reactors when a complete law (form, pre-exponential factor, activation energy and every adsorption or inhibition constant, with units) was found in a primary source. Five laws met this condition: a Temkin-Pyzhev law for Ru/Al~2~O~3~ (Kum et al., 2026), fitted to data of Di Carlo et al. (2014); Langmuir-Hinshelwood-Hougen-Watson laws for 5Ni1Ru/CeO~2~ and 2.5Ni0.5Ru/CeO~2~ (Lucentini et al., 2021); and microkinetic laws for Ni/MgO and Ru/MgO (Takahashi & Fujitani, 2016), represented in Aspen by a fitted approximation. No rate law was found for Ni/CeO~2~ or Ru/CeO~2~, and the full text for Ru-K/CaO (Sayas et al., 2020) could not be retrieved. These three catalysts are not modelled and no parameter was invented for them.

Each law was classified by the range of temperature and pressure in which it was fitted. Three laws are validated against literature, in the sense that they reproduce their own published fitting data. Two are extrapolated. None is validated at 20 bar, the operating pressure of the plant. Every kinetic result at 20 bar is therefore an extrapolation. Figure 1 shows the Aspen RPlug conversion against temperature at 20 bar.

![**Figure 1.** Aspen RPlug NH~3~ conversion against reactor temperature for the five modelled rate laws at 20 bar, 100 kg of catalyst and 100 kmol/h NH~3~, with the RGibbs equilibrium for comparison. Open markers denote a law used outside its fitted range; dashed lines denote the fitted approximation of the Takahashi laws. All points at 20 bar are extrapolations. *Source: Aspen Plus V15 stored runs, results/research/aspen_kinetic/.*](../../results/figures/research/aspen_kinetic_conversion_vs_T.png){width=82%}

Aspen and the independent Python plug-flow model agree within 4.0 × 10^-4^ in conversion against a tolerance of 0.005. Three RPlug runs (Lucentini laws at 600 °C and 40 bar, and a Takahashi Ru case) end slightly above the RGibbs equilibrium, by up to 4.9 × 10^-4^ against a tolerance of 10^-4^. The excess was traced to how Aspen evaluates the reverse-rate term: a compressibility part (Z = 1.0087 at 600 °C and 40 bar) and a fugacity part. Recasting the Lucentini law exactly on a partial-pressure basis removes the compressibility part; the 20 bar runs then pass, and the 40 bar run still fails at 1.69 × 10^-4^. The original items stay recorded as failures.

## 2.3 Independent Python models

The Python package reproduces the flowsheet with its own thermodynamics (CoolProp reference equations for ammonia; Bell et al., 2014), equilibrium and plug-flow models, heat-integration analysis, purification models, end-use pathways and cost models. It is used for studies that Aspen cannot run in bulk, and as an independent check on Aspen. Where the two differ by model form rather than by error, the difference is kept and quantified. The main example is the FEHE duty: Python is 20.8 kW above Aspen in every case. Of this, 8.76 kW comes from a different vaporiser outlet state (dew point 60.09 °C under Raoult's law against 65.90 °C in Aspen) and 12.1 kW from the residual-enthalpy model of ammonia (reference equation against Peng-Robinson). On the Peng-Robinson basis Python reproduces the Aspen duty within 0.12 %. The five affected checks remain failing at an unchanged tolerance of 3 %.

## 2.4 Unified reference scenario

All Phase 2 economic results use one reference scenario (version 1.0.0). Its main entries are: 8000 operating hours per year, a 10 % discount rate, a 25-year life, grey ammonia at 450 USD/t, and electricity at 0.1402 USD/kWh. Capital cost follows the itemised installed cost of the Cho et al. (2026) nickel plant in 2024 USD, with the product compressor removed, each item scaled by the size ratio to the power 0.8 (Chopra et al., 2026), and outside battery limits, engineering and contingency added as in Cho et al. (2026). Calculations are in USD. Every output is also reported in SGD at one rate, 1.288444 SGD/USD, the cross rate of the European Central Bank reference rates of 20 November 2026 (European Central Bank, 2026).

Two earlier baselines exist and are superseded for research outputs: 3.919 USD/kg (a legacy plant-level correlation, kept in the core stored results) and 3.613 USD/kg (the Phase 1 equipment method). The independent published capital range of 3.1 to 6.5 MUSD, normalised to the AmCraX plant, would give 3.64 to 3.92 USD/kg. The reference capital cost of 7.67 MUSD is at or above the top of that range, so the reference is at the conservative end and does not favour cracking.

Catalyst prices are derived from metal content plus a non-metal part, because no supplier quotation was found. The derived central prices are 4791 USD/kg for Ru/Al~2~O~3~, 3006 for Ru/MgO, 628 for 5Ni1Ru/CeO~2~, 330 for 2.5Ni0.5Ru/CeO~2~ and 37 for Ni/MgO. The ruthenium values used in earlier techno-economic studies (for example 542 USD/kg in Cho et al., 2026) are below the ruthenium metal value today (U.S. Geological Survey, 2026) and appear only as a labelled historical case.

Table 1 gives the reference breakdown.

Table: **Table 1.** Reference levelised cost of hydrogen (LCOH), grey NH~3~ at 450 USD/t, heat integration on, plant gate. *Source: results/research/reference_scenario/baseline.json.*

| Item | USD/kg H~2~ | SGD/kg H~2~ |
|---|---:|---:|
| Ammonia feed | 3.040 | 3.917 |
| Capital charge | 0.420 | 0.541 |
| Fixed operating cost | 0.284 | 0.366 |
| Supplementary NH~3~ for heat | 0.268 | 0.345 |
| Catalyst, electricity, cooling water | 0.004 | 0.005 |
| Carbon tax (actual boundary) | 0 | 0 |
| **LCOH** | **4.015** | **5.174** |
| Reconversion cost (LCOH excluding feed) | 0.975 | 1.257 |
| LCOH with heat integration off | 4.229 | 5.449 |

The capital cost is 7.67 MUSD (9.88 MSGD). The net present value at a selling price of 3.06 USD/kg, the north-east Asia steam-reforming marker (Argus Media, 2026), is -17.46 MUSD, and no internal rate of return exists at that price.

## 2.5 Verdict methodology fixed before analysis

The verdict rule (version 2) was written and committed before any Phase 2 analysis was run, so that it could not be shaped by the results. Version 1 called a hypothesis SUPPORTED only if every row was SUPPORTED; under it all four hypotheses were INCONCLUSIVE. Version 2 keeps the row standard and changes only the aggregation.

Each hypothesis is split into components, the separable claims inside the statement. Each component has primary rows, which test it directly, and may have secondary rows, which test whether a specific number quoted in the essay can be reproduced. Secondary rows are reported in full but do not vote.

A row is SUPPORTED only if its result is computed, does not follow from an assumption built into the model, holds across its sensitivity or uncertainty range, and has a stated envelope. A row whose direction follows from an assumption can become SUPPORTED only through evidence independent of that assumption. The accepted form is a threshold analysis: compute the value of the assumed quantity at which the conclusion reverses, and compare it with sourced values. If sourced values lie clearly on one side, the row is SUPPORTED inside the envelope they define. If no source exists, or sourced values straddle the threshold, the row is INCONCLUSIVE and the threshold is the finding. A result smaller than the numerical resolution of the model cannot decide a row. A hypothetical scenario can only support a row that is explicitly conditional on it.

Components are SUPPORTED when every primary row is SUPPORTED, MIXED when at least one is SUPPORTED and one CONTRADICTED, PARTIALLY SUPPORTED when at least one is SUPPORTED and none CONTRADICTED, CONTRADICTED when none is SUPPORTED and at least half are CONTRADICTED, and INCONCLUSIVE otherwise. The hypothesis verdict follows from the components by the same pattern. The version 1 verdict is shown alongside every version 2 verdict.

## 2.6 Uncertainty quantification

Global sensitivity of the LCOH, the reconversion cost and the net present value was computed with variance-based Sobol indices (Saltelli et al., 2010; Jansen, 1999). Ten inputs were varied over their sourced ranges: ammonia price, capital multiplier, capital scaling exponent, PSA recovery, operating hours, discount rate, plant life, electricity price, catalyst price and catalyst lifetime. The design used N = 8192 base samples and 1000 bootstrap resamples. The estimator was checked on the Ishigami function (maximum error 0.0017 against a tolerance of 0.02) and on a linear test function, and a dummy input gave indices of exactly zero.

Kinetic parameter uncertainty was propagated by Latin-hypercube sampling of the published parameter intervals of the Lucentini laws. The Takahashi laws were recalibrated with an adaptive Metropolis sampler (Haario et al., 2001) against digitised data, following the Bayesian calibration framework of Kennedy and O'Hagan (2001), and convergence was checked with the rank-normalised R-hat (Vehtari et al., 2021). These methods are taken from the published uncertainty-quantification literature, including work transferred from nuclear engineering; the project's methodology-transfer matrix lists the sources. The result describes the uncertainty of a model given its stated input ranges. It is not experimental validation.

## 2.7 Interactive simulator

The project website opens with an interactive process simulator. It is a static page and cannot run Aspen or Python. Its numbers come from stored Aspen and Python results, interpolation of stored grids, or browser code tested against the Python model. On the reference scenario the browser LCOH matches the Python model with a maximum relative difference of 2.1 × 10^-16^ (tolerance 0.5 %). The simulator uses an ideal-gas equilibrium and has no membrane model. Its animation shows flow paths only and does not represent a transient simulation.

# 3 Results

## 3.1 H1: end use

Table 2 compares the levelised cost of electricity (LCOE) of the power pathways on the reference basis. The cracker in each pathway is the stored Aspen plant scaled to the turbine. The turbine performance is calibrated to Ahmad et al. (2025).

Table: **Table 2.** LCOE of power pathways and the turbine-efficiency thresholds at which cracking would match direct NH~3~ combustion. Thresholds are given at the reference basis, with the range over 11 bases of capital cost, NH~3~ price and operating hours. *Source: results/research/enduse/turbine_threshold.json.*

| Pathway | LCOE (USD/MWh) | Against direct use | Threshold (percentage points) | Sourced value |
|---|---:|---|---|---|
| Direct NH~3~ combustion | 258.9 | - | - | - |
| Fired standalone cracking | 280.1 | direct 7.6 % cheaper | +5.16 (3.29 to 8.79) | none for H~2~/N~2~ fuel |
| Cracking + PSA, pure H~2~ fuel | 310.2 | direct 16.5 % cheaper | +12.55 (9.68 to 18.10) | +7.3 at most (NETL) |
| Exhaust-heated full cracking | 255.6 | direct 1.3 % dearer | +4.04 (1.97 to 8.04) | +4.9 to +5.5 |
| Exhaust-heated partial cracking, 40 vol% H~2~ | 258.9 | equal | - | - |

Under the modelled operating conditions, direct ammonia combustion produces electricity at a lower cost than the standalone cracking pathways, with a calculated cost advantage of approximately 8 to 17 % (5 to 15 % on the earlier cost basis). This comparison assumes that the hydrogen-rich turbine operates at the same 49.64 % efficiency as the direct-ammonia turbine. The actual economic advantage depends on fuel-specific turbine performance.

Because the direction of row H1-a follows from that assumption, the threshold test decides it (Figure 2). For cracking with PSA, the turbine on pure hydrogen would need an efficiency 12.55 percentage points above the ammonia turbine to match direct use. The only sourced comparison is the difference between two National Energy Technology Laboratory studies, pure hydrogen (steam-diluted) against pure ammonia, which gives +7.3 points (National Energy Technology Laboratory, 2023, 2024). Steam dilution inflates the hydrogen figure, so this is an upper bound. It lies below the threshold on every one of the 11 bases, and the threshold stays above 7.3 even at a quarter of the reference cracker capital cost (+8.36). For fired cracking without purification the threshold is +5.16 points, and no source gives a turbine efficiency on the H~2~/N~2~ fuel of a fired cracker. An indirect bracket of -1.86 to +7.3 points contains the threshold. Row H1-a claims both halves, so it is INCONCLUSIVE. The purified half alone passes the test on every basis and is reported as a finding.

![**Figure 2.** Turbine-efficiency thresholds for H1. Left: the efficiency gain on H~2~-rich fuel, relative to 49.64 %, at which fired and purified cracking pathways would match direct NH~3~ combustion; dots at the reference basis, bars over 11 bases; dashed line the NETL upper bound of +7.3 points. Right: the system efficiency gain needed by exhaust-heated cracking; shaded band the sourced 4.9 to 5.5 points. *Source: results/research/enduse/turbine_threshold.json; cracker from stored Aspen Plus V15 runs; turbine calibrated to Ahmad et al. (2025).*](../../results/figures/research/enduse_turbine_threshold.png){width=100%}

Row H1-c asks whether cracking in front of a turbine pays where ammonia could be burned directly. Exhaust-heated full cracking uses turbine exhaust heat for the cracker and raises the system efficiency by a sourced 4.9 to 5.5 points (Ahmad et al., 2025, rescaled to the AmCraX heating-value basis; Karpilov et al., 2025, maximum values). The threshold is +4.04 points. On the reference basis the sourced values lie above it, so exhaust-heated cracking is about 1.3 % cheaper than direct use. This goes against the essay. The outcome is not robust: a cracker capital cost 1.22 times the reference removes the advantage, and an ammonia price of 300 USD/t, 6000 operating hours or less, or a doubled cracker capital cost favour direct use. Row H1-c is INCONCLUSIVE.

Row H1-d tests the second half of the hypothesis: cracking is justified where hydrogen is the product. Cracked hydrogen from grey ammonia costs 4.015 USD/kg, above the 3.06 USD/kg north-east Asia steam-reforming marker. The energy side depends again on the turbine assumption: per kg of ammonia, direct combustion yields 2.565 kWh, cracking with PSA 2.251 kWh at equal efficiency and 2.582 kWh at the NETL upper bound. Row H1-d is INCONCLUSIVE.

Row H1-b is secondary. It tests the figure of about 40 % quoted in the essay from Halim et al. (2025). The largest computed gap across the stored bases is 16.6 %. Reaching 40 % would need a cracker capital cost 6.3 times (cracking with PSA) or 11.1 times (fired cracking) the reference. The full text of Halim et al. could not be obtained, so the basis of the 40 % figure could not be checked. Row H1-b is CONTRADICTED as a reproduction of that number and does not vote.

**H1 verdict: INCONCLUSIVE** (version 1: INCONCLUSIVE). Both components, H1-P (direct use is preferable where ammonia can be burned) and H1-Q (cracking is justified where hydrogen is the product), are INCONCLUSIVE.

## 3.2 H2: feedstock

**Economic component (H2-E).** Ammonia feed is 3.040 of 4.015 USD/kg, a share of 75.7 %. With the ammonia burned for process heat the share is 82.4 %. The Sobol analysis (Figure 3) gives the ammonia price a total-effect index of 0.896 (95 % interval 0.875 to 0.917) on the LCOH. The capital multiplier follows at 0.063 and the PSA recovery at 0.033. Feed is the largest cost item in every one of 5000 Monte Carlo draws.

![**Figure 3.** First-order (S1) and total-effect (ST) Sobol indices of the LCOH, grey scenario, heat integration on, N = 8192, with 95 % bootstrap intervals. The S1 intervals are wide because of estimator variance; the ST intervals are narrow. *Source: results/research/uq/gsa_sobol.json; Python cost model on the stored Aspen Plus V15 baseline.*](../../results/figures/research/uq_gsa_sobol.png){width=80%}

Feed dominance follows from assumed prices, so the threshold test was applied (Figure 4). The feed share falls to 50 % only below 114.9 USD/t of ammonia. Capital plus fixed operating cost overtakes feed only at a capital multiplier of 4.70 at 450 USD/t (3.09 at 300 USD/t). The sourced ammonia prices run from 300 to 1052 USD/t and the sourced capital multipliers from 0.41 to 1.5, all clearly on the dominant side. Row H2-a is SUPPORTED, inside the envelope of capacity scale 1, both heat-integration cases and PSA recovery down to 0.756. One caveat applies: the reconversion cost, the cost excluding feed, is driven by the capital multiplier (total-effect index 0.473) and PSA recovery (0.420), not by the ammonia price.

![**Figure 4.** Capital charge plus fixed operating cost against the capital multiplier on the reference capital cost of 7.67 MUSD, compared with the ammonia feed cost at 300, 450 and 610 USD/t. The shaded band is the sourced range of multipliers, 0.41 to 1.5. *Source: results/research/carbon_pricing/feed_dominance.json; stored Aspen Plus V15 baseline costed on the reference scenario.*](../../results/figures/research/carbon_feed_dominance.png){width=85%}

Row H2-b states that only affordable ammonia keeps cracked hydrogen competitive. The break-even ammonia price against the 3.06 USD/kg benchmark is 320 USD/t, and 277 to 371 USD/t over the sourced capital range (multipliers 1.5 to 0.41). Competitiveness therefore requires cheap ammonia, and this holds across the sourced capital range. The row is SUPPORTED as a necessity statement. It must be read with the adverse finding: grey ammonia at 450 USD/t is not cheap enough. The Monte Carlo probability of an LCOH below 3.06 USD/kg is 1.4 %, and the net present value at that price is negative. Only one benchmark was used.

**Environmental component (H2-C).** The life-cycle carbon intensity of cracked hydrogen, in kg CO~2~e per kg H~2~, is 19.52 for grey ammonia (range 15.11 to 34.22), 8.93 for blue ammonia (6.07 to 14.53), and 2.43 for green ammonia including embedded emissions (0.93 to 3.93) (Lee et al., 2022, with AmCraX accounting). For cracked hydrogen to have a lower carbon intensity than unabated steam reforming, the ammonia must be produced at 1.31 to 1.58 kg CO~2~e/kg NH~3~ or less; against steam reforming with capture, at 0.41 to 0.67. For direct ammonia power to beat a natural-gas combined cycle, the break-even is 0.81 to 1.33. The lowest sourced value for grey ammonia, 2.0, is above every break-even. Rows H2-c and H2-d are SUPPORTED as necessity statements: low-carbon ammonia is needed. They are not sufficiency statements, because blue ammonia at its central value fails some of the comparisons.

**Cross-claim (H2-X): is low carbon intensity rewarded economically?** This was evaluated in two modes, kept apart. Mode A is the actual Singapore boundary under the Carbon Pricing Act 2018: SGD 45 per tCO~2~e for 2026 and any later year, applied only to direct facility emissions at or above 25,000 tCO~2~e per year, with a global warming potential of 265 for N~2~O. A further rise to 50 to 80 SGD/t by 2030 is a stated aim, not law. The self-fired reference plant burns ammonia for heat, emits no direct CO~2~ and is far below the threshold. Upstream emissions of imported ammonia are outside the Act. The tax is zero for every ammonia route, so low-carbon ammonia earns no cost advantage. Blue ammonia raises the LCOH by 0.272 USD/kg and green ammonia at current prices by 4.04 USD/kg. Row H2-e is CONTRADICTED under Mode A. This follows from the statute, not from a model assumption.

Mode B applies a hypothetical life-cycle carbon price to the embodied emissions of each route. It is hypothetical and is not Singapore law. Table 3 gives the carbon prices at which one route overtakes another (Figure 5).

Table: **Table 3.** Mode B, hypothetical life-cycle carbon price (not Singapore law): crossover prices between ammonia routes, SGD/tCO~2~e. *Source: results/research/carbon_pricing/thresholds.json.*

| Crossover | Central | Range from carbon-intensity ranges |
|---|---:|---|
| Blue overtakes grey | 33 | 12 to 605 |
| Green (current price) overtakes grey | 305 | 156 to 466 |
| Green (2030 projection) overtakes grey | 144 | 74 to 219 |
| Green (current price) overtakes blue | 747 | 357 to 2275 |

![**Figure 5.** Mode B: LCOH by ammonia route against a hypothetical life-cycle carbon price, which is not Singapore law. Bands show the carbon-intensity ranges. Vertical lines mark the legislated SGD 45, the stated 2030 aim of 50 to 80, and an EU emissions-trading level for context. Under Mode A, the actual Singapore boundary, the carbon cost is zero for every route. *Source: results/research/carbon_pricing/scenarios.json and price_sweep.csv.*](../../results/figures/research/carbon_price_sweep.png){width=90%}

At current prices, grey ammonia is cheapest up to about 35 SGD/t and blue ammonia above that; green ammonia at current prices is never cheapest up to 500 SGD/t. The blue-over-grey range of 12 to 605 straddles every reference price, so H2-e under Mode B is INCONCLUSIVE. It is reported beside the verdict and does not change the row about actual policy.

**H2 verdict: MIXED** (version 1: INCONCLUSIVE). H2-E is SUPPORTED, H2-C is SUPPORTED, and the cross-claim H2-X is CONTRADICTED under the actual Singapore carbon tax.

## 3.3 H3: catalyst and heat integration

**Lower-temperature operation (H3-T).** Phase 1 reported a 17 % reduction of fired process duty for Ru/Al~2~O~3~ at 499 °C against Ni/MgO at 594 °C, from Aspen runs with 100 kg of catalyst. Those runs reached unequal conversion (Ni 0.9589, Ru 0.9496). With less unconverted ammonia in the tail gas, the Ni case needs more fired heat, so most of the 17 % is an artefact. At equal conversion of 0.95 and 20 bar, the fired duty is 485.1 kW for Ru/Al~2~O~3~ against 510.3 kW for Ni/MgO with heat integration, a saving of 25 kW or about 5 %. Without heat integration the saving is 163 kW. With heat integration the saving exceeds the 15 kW Python against Aspen offset only for a temperature difference of about 60 K or more. For the Ni-Ru catalysts the saving is 4 to 5 kW, below that resolution. Row H3-a is SUPPORTED inside a narrow envelope: equal conversion 0.95, 20 bar, 499 to 594 °C. The Phase 1 figure of 17 % is withdrawn.

Row H3-b states that the active catalysts allow a lower temperature for the same duty. The temperature ordering rests on rate laws extrapolated to 20 bar, and no law is validated there. Kinetic uncertainty is large: for 5Ni1Ru/CeO~2~, the temperature needed for a conversion of 0.95 at 20 bar spans 529 to 615 °C (5th to 95th percentile) over the published parameter intervals. Row H3-b is INCONCLUSIVE. Component H3-T is PARTIALLY SUPPORTED.

**Heat integration (H3-H).** In Aspen, the FEHE reduces the first-law heat deficit of the plant from 1385.1 to 772.9 kW, by 44 %, and the total external heating from 2905.3 to 2293.1 kW, by 21 %. The cost side was tested by sizing and costing the exchanger. Because of a temperature cross, the FEHE needs five 1-2 shells in series. At overall heat-transfer coefficients of 35, 72.5 and 150 W/(m^2^ K) the area is 249, 120 and 58 m^2^, and the capital cost, on the same total-investment basis as the reference, is 1.78, 1.54 and 1.44 MUSD (Turton et al., 2018). The heat-integration saving of 0.214 USD/kg leaves a net benefit of +0.067 to +0.095 USD/kg after the annualised exchanger cost (Figure 6). The net benefit turns negative only for a coefficient below about 12 W/(m^2^ K), an ammonia price below about 310 USD/t, or a capital recovery factor above about 0.15. No sourced coefficient at 20 bar was found; typical ranges are 5 to 35 W/(m^2^ K) for gas at about 1 bar and 150 to 500 at 200 to 300 bar (VDI e. V., 2010). Row H3-d is SUPPORTED for the energy claim, which is computed. The cost side is threshold-dependent and is stated in the envelope rather than voted. The exchanger cost is added on top of the reference heat-exchanger item, which may count part of it twice; this makes the net benefit conservative. Component H3-H is SUPPORTED.

![**Figure 6.** Heat-integration fuel saving against the annualised FEHE cost at three overall heat-transfer coefficients, for the baseline and for ten catalyst cases. The saving exceeds the exchanger cost in every case shown. *Source: results/research/heat_exchanger/heat_exchanger_study.json.*](../../results/figures/research/heat_exchanger_net_benefit.png){width=95%}

**Catalyst cost (H3-K).** Table 4 summarises the catalyst economics, and Figure 7 shows the break-even prices.

Table: **Table 4.** Low-temperature catalysts against Ni/MgO at 594 °C, equal conversion 0.95, 20 bar, exchanger costed, catalyst lifetime 2 years. A positive LCOH difference means the low-temperature catalyst is dearer. All results rest on laws extrapolated to 20 bar. *Source: results/research/catalyst_economics/catalyst_economics.json and catalyst_breakeven.csv.*

| Catalyst | Derived central price (USD/kg) | Metal-content floor (USD/kg) | LCOH difference (USD/kg H~2~) | Break-even price (USD/kg) | Ni temperature at which it wins, kinetics-free (°C) |
|---|---:|---:|---:|---:|---:|
| Ru/Al~2~O~3~ | 4791 | 1775 | +0.081 | 1506 | 670 |
| Ru/MgO | 3006 | 1109 | +0.043 | 1297 | 676 |
| 5Ni1Ru/CeO~2~ | 628 | 223 | +0.011 | 177 | 640 |
| 2.5Ni0.5Ru/CeO~2~ | 330 | 111 | +0.005 | 151 | 540 |

At the derived prices, every low-temperature catalyst is dearer than Ni/MgO at equal conversion, by 0.005 to 0.081 USD/kg. Each break-even price is below the derived central price, and for the two ruthenium catalysts it is also below the ruthenium metal value alone. When temperature and catalyst mass are optimised for cost, the optimum for an expensive catalyst is a small charge at a high temperature (Ru/Al~2~O~3~ at 614 °C with 7.5 kg). The low-temperature operation the hypothesis needs is then not chosen. In 100 sensitivity cases, a low-temperature catalyst wins by more than the 0.006 USD/kg resolution in only one. This goes against the essay.

![**Figure 7.** Break-even catalyst price against the Ni/MgO reference (exchanger costed, lifetime 2 years), at the kinetic operating temperature and at the re-optimised cost-optimal design, compared with the derived central price, the metal-content floor and the historical price used in a published techno-economic study. All laws are extrapolated to 20 bar. *Source: results/research/catalyst_economics/catalyst_economics.json; prices from research/data/catalyst_prices.json (derived, no quotation).*](../../results/figures/research/catalyst_econ_breakeven.png){width=95%}

The result is not a contradiction, because it depends on the temperature at which nickel must run. Sourced nickel design temperatures of 736 °C (Cho et al., 2026) and 760 °C (Mehr et al., 2026) are above the kinetics-free thresholds of 540 to 676 °C in Table 4, so against those designs the low-temperature catalysts win. The AmCraX Ni/MgO law, which is extrapolated, places the nickel cost optimum at 537 to 549 °C, below most thresholds. The sourced values and the model straddle the threshold. Row H3-c is INCONCLUSIVE, and so is component H3-K.

Two secondary rows test reproductions of Cho et al. (2026). Their pattern, in which the Ru process needs no supplementary fuel and the Ni process does, appears in the AmCraX model only for PSA recoveries between 0.7564 and 0.7813 (H3-e). Their 7.0 % lower relative economic cost for Ru becomes -16.2 to +1.6 % depending on the price and inventory basis (H3-f). Both rows are INCONCLUSIVE and do not vote.

**H3 verdict: PARTIALLY SUPPORTED** (version 1: INCONCLUSIVE). H3-T is PARTIALLY SUPPORTED, H3-H is SUPPORTED, and H3-K is INCONCLUSIVE.

## 3.4 H4: purification

H4 has one component, H4-B: purity must be balanced against recovery, energy and cost.

Row H4-a asks whether higher PSA purity costs recovery. No PSA purity-recovery relation is computed in AmCraX; the PSA is a splitter with an assumed recovery. The only sourced slope (recovery falling from 75.3 to 55.5 % between 99.25 and 99.97 % purity) is for a different feed (Yáñez et al., 2020). Row H4-a is INCONCLUSIVE.

Row H4-b asks whether stricter purity raises the cost per kg of usable hydrogen. The order raw product < industrial 99.9 % < fuel-cell Grade D (International Organization for Standardization, 2019) holds in every sourced combination: 3.784, 3.984 and 4.237 USD/kg at the cheapest configuration of each. However, raw below industrial is structural, and most of the Grade D increment is the 350 bar delivery pressure. The increment from purity alone, at equal 30 bar delivery, is 0.002 to 0.17 USD/kg and rests on a proxy. Under the strict row rule H4-b stays INCONCLUSIVE.

Row H4-e asks whether recovery losses trade against energy. The computed energy balance shows that hydrogen not recovered returns as fuel for the cracker. At a recovery of 0.7651 the tail-gas heat equals the furnace demand of 2293 kW, for both PSA and membrane. Above that recovery, supplementary ammonia must be burned (a 773 kW deficit at the assumed 0.85); below it, the lost hydrogen has no use in this flowsheet. Row H4-e is SUPPORTED, with a threshold recovery of 0.765.

Row H4-d, secondary, compares PSA with a Pd-Ag membrane (Figure 8). For industrial purity the PSA LCOH is 5.605, 4.269 or 4.046 USD/kg at recoveries of 0.5715 (Yáñez et al., 2020, different feed), 0.7516 (mass-balance relation) and 0.85 (assumption). The membrane gives 4.102 to 4.262 USD/kg over sourced costs. Over the full factorial of sourced inputs the membrane is cheaper in 59 % of pairs for industrial purity and 60 % for Grade D. The ranking reverses at a PSA recovery of 0.801 (industrial) or 0.788 (Grade D) against the central membrane, and sourced PSA values straddle these. Membrane cost, life and selectivity do not decide the ranking. The required ideal H~2~/N~2~ selectivity for Grade D is 12,919. Cechetto et al. (2021) report 40,541 (from the printed permeances) to 500,000 (stated) for a new membrane in single-gas tests; the paper is internally inconsistent and both values are carried. Technology readiness favours PSA (unit level 9 against 4 to 5 for the membrane), and a recent membrane demonstration missed its recovery target (Gemserv Ltd et al., 2025). Row H4-d is INCONCLUSIVE.

![**Figure 8.** LCOH of usable hydrogen against PSA recovery for industrial 99.9 % hydrogen at 30 bar (left) and ISO 14687:2019 Grade D at 350 bar (right), with the central Pd-Ag membrane case. Marked points are published or assumed recoveries; recovery is an input, as no adsorption-cycle model exists. *Source: results/research/purification/phase2_comparison.json; Python reduced-order models on Aspen Plus V15 cracked gas.*](../../results/figures/research/purification_phase2_psa_recovery.png){width=100%}

Row H4-c, secondary, is unchanged from Phase 1 and CONTRADICTED: the published PSA point of Cho et al. (2026), 75.6 % recovery at 99.11 % H~2~, leaves about 8900 ppm N~2~ and does not meet ISO 14687 grades for fuel cells.

**H4 verdict: PARTIALLY SUPPORTED** (version 1: INCONCLUSIVE).

## 3.5 Summary of verdicts

Table 5 collects the verdicts.

Table: **Table 5.** Hypothesis verdicts under the version 2 rule, with component verdicts and the version 1 verdict. Secondary rows are listed but do not vote. *Source: docs/research/verdict_methodology_v2.md; row evidence in the result files named in Section 3.*

| Hypothesis | Components (primary rows) | Secondary rows | Version 2 | Version 1 |
|---|---|---|---|---|
| H1 end use | H1-P INCONCLUSIVE (H1-a, H1-c INCONCLUSIVE); H1-Q INCONCLUSIVE (H1-d) | H1-b CONTRADICTED | INCONCLUSIVE | INCONCLUSIVE |
| H2 feedstock | H2-E SUPPORTED (H2-a, H2-b); H2-C SUPPORTED (H2-c, H2-d); H2-X CONTRADICTED under the actual Singapore boundary (H2-e), INCONCLUSIVE under the hypothetical price | - | MIXED | INCONCLUSIVE |
| H3 catalyst and heat integration | H3-T PARTIALLY SUPPORTED (H3-a SUPPORTED, H3-b INCONCLUSIVE); H3-H SUPPORTED (H3-d); H3-K INCONCLUSIVE (H3-c) | H3-e, H3-f INCONCLUSIVE | PARTIALLY SUPPORTED | INCONCLUSIVE |
| H4 purification | H4-B PARTIALLY SUPPORTED (H4-e SUPPORTED; H4-a, H4-b INCONCLUSIVE) | H4-c CONTRADICTED; H4-d INCONCLUSIVE | PARTIALLY SUPPORTED | INCONCLUSIVE |

# 4 Discussion

## 4.1 What the evidence supports

The strongest result of this work is about cost structure, not technology choice. On a conservative capital basis, ammonia feed is three quarters of the cost of cracked hydrogen, and its price explains about 90 % of the variance of the LCOH. The capital cost would have to rise almost fivefold before it rivalled feed. No plausible improvement of the cracker, the catalyst or the purification changes this picture. The reconversion cost is a different matter: there, capital cost and PSA recovery dominate, and these are the quantities that engineering can change.

The second robust result is that cracking ammonia to pure hydrogen in order to burn it in a turbine does not pay against burning ammonia directly, unless a hydrogen turbine is more than 12 percentage points more efficient than an ammonia turbine. The only sourced comparison suggests a gain of at most 7.3 points.

The third is that heat integration is worth its exchanger. The FEHE cuts the external heating by about one fifth and pays back its cost with a net margin of about 0.07 to 0.10 USD/kg, unless the heat-transfer coefficient is very low.

## 4.2 Findings against the original essay

Four findings go against the essay, and they are stated plainly.

1. **Exhaust-heated cracking is slightly cheaper than direct use.** The essay held that cracking is not justified where ammonia can be burned directly. On the reference basis, cracking with turbine exhaust heat is about 1.3 % cheaper than direct combustion, and partial cracking to 40 vol% hydrogen costs the same. The margin is small and reverses with plausible changes of capital cost, ammonia price or operating hours, so the row is INCONCLUSIVE rather than CONTRADICTED. It does not support the essay.
2. **At realistic ruthenium prices, the low-temperature catalysts do not pay.** The essay held that energy savings can outweigh a higher catalyst cost. At catalyst prices derived from today's metal values, every low-temperature catalyst is dearer than nickel at equal conversion, and the cost optimum for ruthenium is a small charge at high temperature. The essay's position is only recovered against the high nickel design temperatures of published plants.
3. **The energy saving of low-temperature operation is about 5 %, not 17 %.** The larger Phase 1 figure came from comparing runs at unequal conversion and is withdrawn.
4. **Low-carbon ammonia is not rewarded by the actual Singapore carbon tax.** The tax covers direct facility emissions above a threshold; the cracker emits almost none, and the emissions embodied in imported ammonia are outside the Act. Low-carbon ammonia only raises the cost. A life-cycle carbon price would change this, but such a price is hypothetical.

Two further findings refine rather than oppose the essay. Grey ammonia at 450 USD/t is not cheap enough for cracked hydrogen to compete with the 3.06 USD/kg benchmark; the break-even is 320 USD/t. And the earlier claim that a raw Pd-Ag membrane is cheaper than PSA for industrial hydrogen does not hold robustly; the ranking turns on PSA recovery, with parity near 0.80.

## 4.3 What changed since the Phase 1 release

The Phase 1 release of 23 November 2026 used two cost bases (3.92 and 3.61 USD/kg) and Cho et al. (2026) catalyst prices. Unifying the basis raised the baseline to 4.015 USD/kg, mainly because the reference capital cost (7.67 MUSD) is higher than the Phase 1 equipment estimate (2.78 MUSD). As a result, the feed share fell from 84 to 76 %, the break-even ammonia price against the benchmark fell from 375 to 320 USD/t, and the net present value at 3.06 USD/kg fell from -10.1 to -17.5 MUSD. The direct-use advantage over fired cracking and cracking with PSA grew from 5 and 15 % to 7.6 and 16.5 %, and the advantage of exhaust-heated cracking shrank from 4 to 1.3 %. No verdict was moved to make a hypothesis look better: the verdict changes come from new evidence (thresholds, exchanger costing, carbon-policy reading) and from the version 2 aggregation, which was fixed before the analysis.

## 4.4 Validation status by evidence kind

The validation items are kept apart by the kind of evidence they provide. Table 6 counts the research validation items. The core flowsheet validation matrix is counted separately: of its 137 items, 105 pass, 22 fail and 10 are informational. Twenty of its failures share one cause, a feed-section enthalpy difference between the property models, and two are the Takahashi prediction checks.

Table: **Table 6.** Research validation items by evidence kind and status, as stored at the time of writing. *Source: results/research/validation/\*.json (all workstream files except summary.json).*

| Evidence kind | Pass | Fail | Informational | Not available |
|---|---:|---:|---:|---:|
| Numerical verification | 437 | 5 | 19 | 0 |
| Python against Aspen comparison | 156 | 5 | 22 | 0 |
| Comparison with published literature | 11 | 2 | 35 | 0 |
| Independent experimental validation | 0 | 0 | 0 | 1 |
| **Total (693 items)** | **604** | **12** | **76** | **1** |

The numerical-verification failures are the RPlug runs that end slightly above equilibrium (Section 2.2). The Python against Aspen failures are the FEHE duty checks (Section 2.3). The single item of the experimental kind is recorded as not available, because no such evidence exists. The literature failures are the two Takahashi prediction checks, which also appear in the core matrix: an independent re-implementation reproduces the stored predictions to 10^-8^, so these are a limit of the published law as it can be reproduced, not an implementation error. The held-out data confirm this: the dilution and hydrogen co-feed series are under-predicted.

None of these counts is experimental validation. AmCraX has no measurement of its own and no comparison with plant data. Agreement between Aspen and Python shows that two implementations agree; it does not show that either is right. Agreement with a published number shows consistency with that source. No model is called validated outside the range in which it was checked, and every kinetic result at 20 bar is an extrapolation.

# 5 Limitations

- No supplier catalyst quotation exists. All catalyst prices are derived from metal content.
- No sourced overall heat-transfer coefficient at 20 bar exists for the FEHE.
- No sourced turbine efficiency exists for the H~2~/N~2~ fuel of a fired cracker.
- No measured PSA recovery on cracked ammonia exists, and AmCraX has no adsorption-cycle model.
- The full texts of Halim et al. (2025) and of a 2025 PSA design study for cracked ammonia were not obtained. The kinetics of Ru-K/CaO (Sayas et al., 2020) were not obtained.
- The Takahashi laws under-predict the dilution and hydrogen co-feed series, a model-form limit.
- No rate law is validated at 20 bar; three are validated against their own fitting data, two are extrapolated and three catalysts are not modelled.
- The reference capital cost comes from one paper's itemised table. For the power-plant cracker it is extrapolated more than 30-fold from the 82 kg/h reference plant.
- The exchanger cost is added on top of the reference heat-exchanger item, which is conservative and may count part of it twice.
- The electricity cost covers pump power only; PSA and compression power are outside the cost boundary, which is why the electricity price has almost no sensitivity index.
- The browser simulator has no membrane model and uses an ideal-gas equilibrium.
- One hydrogen price benchmark (3.06 USD/kg) was used. No Singapore hydrogen transaction price exists.
- There is no experimental validation of any kind.

# 6 Conclusions

On one frozen, conservative cost basis, cracked hydrogen from grey ammonia in a 1.7 t/h plant in Singapore costs 4.015 USD/kg (5.174 SGD/kg). The ammonia price is the decisive input. The verdicts, under a rule fixed before the analysis, are:

- **H1, INCONCLUSIVE.** Direct ammonia combustion is about 8 to 17 % cheaper than standalone cracking at equal turbine efficiency. Cracking with PSA would need a turbine about 12.6 points more efficient, above every sourced value, so that half is a robust finding. Fired cracking has no sourced efficiency, and exhaust-heated cracking is marginally cheaper than direct use on the reference basis.
- **H2, MIXED.** Affordable ammonia (below about 320 USD/t against the benchmark) and low-carbon ammonia are both necessary. Under the actual Singapore carbon tax, low-carbon ammonia earns no cost advantage.
- **H3, PARTIALLY SUPPORTED.** Heat integration reduces energy use by about one fifth and pays after the exchanger cost. Lower-temperature operation saves about 5 % of fired duty at equal conversion. At realistic ruthenium prices the low-temperature catalysts do not pay.
- **H4, PARTIALLY SUPPORTED.** Recovery losses trade against fuel up to a recovery of about 0.765. The choice between PSA and a Pd-Ag membrane turns on PSA recovery and is not robust.

The most useful next measurements are a supplier quotation for ruthenium and nickel catalysts, a measured PSA recovery on cracked ammonia, a turbine efficiency on cracked fuel, a rate law fitted at elevated pressure, and an overall heat-transfer coefficient for the FEHE at 20 bar. Each of these closes a threshold identified here.

# Data and code availability

The models, Aspen input files, stored results, figures, tests and documents are available at <https://github.com/weewzr/AmCraX>. The Phase 1 release is preserved under the tag amcrax-research-expansion-2026-11-23; the Phase 2 results reported here are in the repository after that tag. The reference scenario is `backend/amcrax/data/reference_scenario.yaml`, the verdict rule is `docs/research/verdict_methodology_v2.md`, and every number in this paper traces to a file under `results/research/`. The interactive simulator is published at <https://weewzr.github.io/AmCraX/>. Aspen Plus V15 is commercial software; its stored outputs are included, and the Python models run without it.

# References

Ahmad, A. H., Tsujimura, T., Shimura, M., Fan, Y., Ito, H., Iki, N., Kurata, O., Jo, H., & Aziz, M. (2025). Thermodynamic and preliminary techno-economic analysis of NH3 utilization in combined cycle power plant: Comparison of direct liquid, vaporized, and cracked NH3-based combustion methods. *International Journal of Hydrogen Energy*, *173*, 151337.\
<https://doi.org/10.1016/j.ijhydene.2025.151337>

Argus Media. (2026). *Argus Hydrogen and Future Fuels, sample report (regional hydrogen cost markers)*.\
<https://view.argusmedia.com/rs/584-BUW-606/images/POW-Sample-Report-20260106-Hydrogen.pdf?version=0>

Bell, I. H., Wronski, J., Quoilin, S., & Lemort, V. (2014). Pure and pseudo-pure fluid thermophysical property evaluation and the open-source thermophysical property library CoolProp. *Industrial & Engineering Chemistry Research*, *53*(6), 2498-2508.\
<https://doi.org/10.1021/ie4033999>

Carbon Pricing Act 2018 (Singapore). (2026). *2020 Revised Edition, current version as at 23 November 2026*. Singapore Statutes Online, Attorney-General's Chambers.\
<https://sso.agc.gov.sg/Act/CPA2018>

Cechetto, V., Di Felice, L., Medrano, J. A., Makhloufi, C., Zuniga, J., & Gallucci, F. (2021). H2 production via ammonia decomposition in a catalytic membrane reactor. *Fuel Processing Technology*, *216*, 106772.\
<https://doi.org/10.1016/j.fuproc.2021.106772>

Cho, S., Lee, Y., & Lee, I. (2026). Comparative assessment of ammonia decomposition processes based on nickel and ruthenium catalysts: A techno-economic perspective. *Energy Conversion and Management*, *348*, 120796.\
<https://doi.org/10.1016/j.enconman.2025.120796>

Chopra, M., Srivastava, N., & Arora, P. (2026). Decentralized hydrogen production via ammonia decomposition: Process simulation, techno-economic, and environmental assessment. *Fuel*, *415*, 138463.\
<https://doi.org/10.1016/j.fuel.2026.138463>

Di Carlo, A., Vecchione, L., & Del Prete, Z. (2014). Ammonia decomposition over commercial Ru/Al2O3 catalyst: An experimental evaluation at different operative pressures and temperatures. *International Journal of Hydrogen Energy*, *39*(2), 808-814.\
<https://doi.org/10.1016/j.ijhydene.2013.10.110>

European Central Bank. (2026). *Euro foreign exchange reference rates* [Data set, reference date 20 November 2026].\
<https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml>

Farokhi, V., Øi, L. E., & Hansen, P. M. (2025). Simulation and cost optimization of ammonia cracker process. *IFAC-PapersOnLine*, *59*(29), 48-53.\
<https://doi.org/10.1016/j.ifacol.2025.12.180>

Gemserv Ltd, H2SITE, Equans, University of Birmingham, Yara, & Tyseley Energy Park. (2025). *AMMOGEN: HYS2204 Deliverable 1.21, final project report*. UK Department for Energy Security and Net Zero.\
<https://assets.publishing.service.gov.uk/media/695ceb3a6056a077857e735a/tyseley-ammonia-to-green-hydrogen.pdf>

Haario, H., Saksman, E., & Tamminen, J. (2001). An adaptive Metropolis algorithm. *Bernoulli*, *7*(2), 223-242.\
<https://doi.org/10.2307/3318737>

Halim, I., Zain, N. S., & Khoo, H. H. (2025). Assessing the feasibility of ammonia utilization for power generation: A techno-economic-environmental study. *Applied Energy*, *386*, 125581.\
<https://doi.org/10.1016/j.apenergy.2025.125581>

International Organization for Standardization. (2019). *Hydrogen fuel quality: Product specification* (ISO Standard No. 14687:2019).\
<https://www.iso.org/standard/69539.html>

Jansen, M. J. W. (1999). Analysis of variance designs for model output. *Computer Physics Communications*, *117*(1-2), 35-43.\
<https://doi.org/10.1016/S0010-4655(98)00154-4>

Karpilov, I., Papkov, V., & Pashchenko, D. (2025). Thermodynamic analysis of combined cycle power plant fired with ammonia. *Energy Proceedings*, *52*.\
<https://energy-proceedings.org/wp-content/uploads/icae2024/1728014537.pdf>

Kennedy, M. C., & O'Hagan, A. (2001). Bayesian calibration of computer models. *Journal of the Royal Statistical Society Series B: Statistical Methodology*, *63*(3), 425-464.\
<https://doi.org/10.1111/1467-9868.00294>

Kum, J., Ko, Y., Chang, J. H., & Lee, C.-H. (2026). Dynamic modeling and techno-economic analysis of a heat-integrated NH3 cracking plant for cost-effective H2 production under uncertainty. *Applied Energy*, *406*, 127210.\
<https://doi.org/10.1016/j.apenergy.2025.127210>

Lee, K., Liu, X., Vyawahare, P., Sun, P., Elgowainy, A., & Wang, M. (2022). Techno-economic performances and life cycle greenhouse gas emissions of various ammonia production pathways including conventional, carbon-capturing, nuclear-powered, and renewable production. *Green Chemistry*, *24*(12), 4830-4844.\
<https://doi.org/10.1039/D2GC00843B>

Lucentini, I., Garcia Colli, G., Luzi, C. D., Serrano, I., Martinez, O. M., & Llorca, J. (2021). Catalytic ammonia decomposition over Ni-Ru supported on CeO2 for hydrogen production: Effect of metal loading and kinetic analysis. *Applied Catalysis B: Environmental*, *286*, 119896.\
<https://doi.org/10.1016/j.apcatb.2021.119896>

Maritime and Port Authority of Singapore. (2025). *Consortium appointed for next phase of study on low- or zero-carbon ammonia power generation and bunkering solution*.\
<https://www.mpa.gov.sg/media-centre/details/consortium-appointed-for-next-phase-of-study-on-low--or-zero-carbon-ammonia-power-generation-and-bunkering-solution>

Mehr, A. S., Scheffknecht, G., Zohourian, R., Reinmöller, M., & Maier, J. (2026). Design, simulation, and techno-economic evaluation of a high-capacity ammonia cracking facility for pipeline-grade hydrogen production. *Energy Science & Engineering*, *14*(9), 4197-4212.\
<https://doi.org/10.1002/ese3.70618>

National Energy Technology Laboratory. (2023). *Cooled gas turbine and combined cycle analysis for H2-CH4 fuel mixes (up to 100% H2)*. U.S. Department of Energy.\
<https://netl.doe.gov/projects/files/CooledGasTurbineandCombinedCycleAnalysisforH2CH4FuelMixesUpto100H2_052523.pdf>

National Energy Technology Laboratory. (2024). *Cooled gas turbine and combined cycle analysis for NH3-CH4 fuel mixes (up to 100% NH3)*. U.S. Department of Energy.\
<https://netl.doe.gov/projects/files/CooledGasTurbineCombinedCycleAnalysisNH3CH4FuelMixesUp100NH3_103024.pdf>

Peng, D.-Y., & Robinson, D. B. (1976). A new two-constant equation of state. *Industrial & Engineering Chemistry Fundamentals*, *15*(1), 59-64.\
<https://doi.org/10.1021/i160057a011>

Richard, S., Ramirez Santos, A., Olivier, P., & Gallucci, F. (2024). Techno-economic analysis of ammonia cracking for large scale power generation. *International Journal of Hydrogen Energy*, *71*, 571-587.\
<https://doi.org/10.1016/j.ijhydene.2024.05.308>

Saltelli, A., Annoni, P., Azzini, I., Campolongo, F., Ratto, M., & Tarantola, S. (2010). Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index. *Computer Physics Communications*, *181*(2), 259-270.\
<https://doi.org/10.1016/j.cpc.2009.09.018>

Sayas, S., Morlanes, N., Katikaneni, S. P., Harale, A., Solami, B., & Gascon, J. (2020). High pressure ammonia decomposition on Ru-K/CaO catalysts. *Catalysis Science & Technology*, *10*(15), 5027-5035.\
<https://doi.org/10.1039/d0cy00686f>

Takahashi, A., & Fujitani, T. (2016). Kinetic analysis of decomposition of ammonia over nickel and ruthenium catalysts. *Journal of Chemical Engineering of Japan*, *49*(1), 22-28.\
<https://doi.org/10.1252/jcej.14we431>

Turton, R., Shaeiwitz, J. A., Bhattacharyya, D., & Whiting, W. B. (2018). *Analysis, synthesis, and design of chemical processes* (5th ed.). Prentice Hall.\
<https://www.pearson.com/en-us/subject-catalog/p/analysis-synthesis-and-design-of-chemical-processes/P200000003310>

U.S. Geological Survey. (2026). Platinum-group metals. In *Mineral commodity summaries 2026*.\
<https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-platinum-group.pdf>

VDI e. V. (Ed.). (2010). *VDI heat atlas* (2nd ed.). Springer.\
<https://doi.org/10.1007/978-3-540-77877-6>

Vehtari, A., Gelman, A., Simpson, D., Carpenter, B., & Bürkner, P.-C. (2021). Rank-normalization, folding, and localization: An improved R-hat for assessing convergence of MCMC (with discussion). *Bayesian Analysis*, *16*(2), 667-718.\
<https://doi.org/10.1214/20-BA1221>

Yáñez, M., Relvas, F., Ortiz, A., Gorri, D., Mendes, A., & Ortiz, I. (2020). PSA purification of waste hydrogen from ammonia plants to fuel cell grade. *Separation and Purification Technology*, *240*, 116334.\
<https://doi.org/10.1016/j.seppur.2019.116334>
