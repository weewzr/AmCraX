---
title: "Ammonia cracking for hydrogen supply in Singapore: a threshold-based test of four hypotheses with an Aspen Plus flowsheet, Python models and uncertainty quantification"
author: "AmCraX project"
date: "24 November 2026"
---

# Abstract

Ammonia is proposed as a hydrogen carrier for Singapore, but it is not settled when the ammonia should be cracked back to hydrogen and what decides the cost. This paper tests four hypotheses from an earlier essay: end-use suitability (H1), feedstock (H2), catalyst and heat integration (H3) and purification (H4). The methods are an Aspen Plus V15 flowsheet (600 °C, 20 bar) with RPlug reactors for five published rate laws, Python models, one frozen cost scenario and Sobol uncertainty analysis. A row that rests on an assumption can only be supported by a threshold analysis against sourced values. The reference levelised cost of hydrogen is 4.015 USD/kg (5.174 SGD/kg) with fuel counted at 100 % of its lower heating value, an optimistic choice (4.038 to 4.063 USD/kg at 92 to 85 %). Ammonia feed is 76 % of the cost, and its price explains about 90 % of the variance. H1: yes, under the modelled conditions, direct ammonia combustion gives electricity 8 to 17 % cheaper than standalone cracking; the gas turbine is not modelled, so both fuels are assumed to run at 49.64 % efficiency, and cracking with pressure-swing adsorption would need a turbine 12.55 percentage points more efficient, above the only sourced bound of 7.3. H2: yes, feed dominates the cost and low-carbon ammonia is needed for lower emissions; not established that ammonia is cheap enough (break-even 320 USD/t, which sourced prices straddle); no cost advantage under the actual Singapore carbon tax. H3: yes for energy, modestly; the cost saving of heat integration and the catalyst trade-off are not established. H4: not established. Under a stricter rule fixed before the analysis the formal classifications are INCONCLUSIVE, MIXED, PARTIALLY SUPPORTED and INCONCLUSIVE. AmCraX has no independent experimental validation.

# 1 Introduction

## 1.1 Context

Singapore is studying ammonia as a low-carbon fuel for power generation and bunkering (Maritime and Port Authority of Singapore, 2025). Ammonia carries 17.8 % hydrogen by mass and is traded at scale; to deliver molecular hydrogen it must be cracked over a catalyst at high temperature and the product purified. Recent process and techno-economic studies cover parts of this chain (Chopra et al., 2026; Cho et al., 2026; Farokhi et al., 2025; Kum et al., 2026; Mehr et al., 2026; Richard et al., 2024), and turbine studies compare direct ammonia combustion with cracked fuel (Ahmad et al., 2025; Halim et al., 2025). The studies differ in plant size, cost basis, catalyst, purity target and end use, so their conclusions cannot be compared directly.

An earlier essay by the project author argued four positions on this question. This paper tests them with one consistent model chain and one cost basis, and reports where the evidence does not support the essay.

## 1.2 The four hypotheses

- **H1, end-use suitability.** Cracking is most justified when the end use needs molecular hydrogen, not where ammonia can be used directly.
- **H2, feedstock.** Affordable, low-carbon ammonia is essential to economic and environmental competitiveness.
- **H3, catalyst and heat integration.** Low-temperature, high-activity catalysts with effective heat integration reduce energy use and can outweigh a higher catalyst cost.
- **H4, purification.** Purification must balance purity requirements against recovery losses, energy and equipment cost.

Each hypothesis joins several claims. H2, for example, makes an economic claim and an environmental claim, and can also be read as saying that low carbon intensity is rewarded economically. Section 2.5 describes how the hypotheses were split into components and rows.

## 1.3 Contribution

The paper costs every pathway on one frozen reference scenario; where a conclusion depends on an assumed quantity, it computes the value at which the conclusion reverses and compares that threshold with sourced values; and it states which of four kinds of evidence supports each number: numerical verification, Python against Aspen comparison, comparison with published literature, or independent experimental validation. AmCraX has none of the last kind.

# 2 Methods

## 2.1 Aspen Plus V15 flowsheet

The baseline flowsheet converts saturated liquid ammonia (99.8 mol% NH~3~, 0.2 mol% H~2~O, 100 kmol/h, 1.013 bar) into hydrogen in a single train without recycle. A pump raises the liquid to 21 bar. A vaporiser heats it to 10 K above the dew point. A feed/effluent heat exchanger (FEHE) heats the vapour to 550 °C against the reactor effluent, and a trim heater closes the last 50 K. The baseline cracker is an isothermal RGibbs equilibrium reactor at 600 °C and 20 bar, which reaches an NH~3~ conversion of 0.9808. The cracked gas is cooled to 40 °C and sent to a pressure-swing adsorption (PSA) unit, modelled as a reduced-order splitter with an assumed hydrogen recovery of 0.85, above the published range of about 0.71 to 0.81 (tested in Sections 3.2 and 3.4). The tail gas is burned with 15 % excess air, and its heat is credited against the process heat demand. The property method is PENG-ROB (Peng & Robinson, 1976). The baseline produces 251.6 kg/h of hydrogen at 99.96 mol%; this purity follows from the assumed PSA split fractions and is not a prediction.

## 2.2 Kinetic reactors in Aspen RPlug

The equilibrium reactor carries no catalyst, so H3 needs a reactor in which the catalyst sets the conversion. Published rate laws were implemented in Aspen RPlug reactors when a complete law (form, pre-exponential factor, activation energy and every adsorption or inhibition constant, with units) was found in a primary source. Five laws met this condition: a Temkin-Pyzhev law for Ru/Al~2~O~3~ (Kum et al., 2026), fitted to data of Di Carlo et al. (2014); Langmuir-Hinshelwood-Hougen-Watson laws for 5Ni1Ru/CeO~2~ and 2.5Ni0.5Ru/CeO~2~ (Lucentini et al., 2021); and microkinetic laws for Ni/MgO and Ru/MgO (Takahashi & Fujitani, 2016), represented in Aspen by a fitted approximation. No rate law was found for Ni/CeO~2~ or Ru/CeO~2~; for Ru-K/CaO the main text of Sayas et al. (2020) gives orders and an apparent activation energy (75 kJ/mol at 350 °C, 1 atm) but the rate constant is in supplementary information that was not obtained. These three catalysts are not modelled and no parameter was invented for them.

Each law was classified by the range of temperature and pressure in which it was fitted. Three laws are validated against literature, in the sense that they reproduce their own published fitting data. Two are extrapolated. None is validated at 20 bar, the operating pressure of the plant, so every kinetic result at 20 bar is an extrapolation. Figure 1 shows the Aspen RPlug conversion against temperature at 20 bar.

![**Figure 1.** Aspen RPlug NH~3~ conversion against reactor temperature for the five modelled rate laws at 20 bar, 100 kg of catalyst and 100 kmol/h NH~3~, with the RGibbs equilibrium for comparison. Open markers denote a law used outside its fitted range; dashed lines denote the fitted approximation of the Takahashi laws. All points at 20 bar are extrapolations. *Source: Aspen Plus V15 stored runs, results/research/aspen_kinetic/.*](../../results/figures/research/aspen_kinetic_conversion_vs_T.png){width=82%}

Aspen and the independent Python plug-flow model agree within 4.0 × 10^-4^ in conversion against a tolerance of 0.005. Three RPlug runs end slightly above the RGibbs equilibrium; they stay recorded as failures (Section 4.4).

## 2.3 Independent Python models

The Python package reproduces the flowsheet with its own thermodynamics (CoolProp reference equations for ammonia; Bell et al., 2014), equilibrium and plug-flow models, heat-integration analysis, purification models, end-use pathways and cost models. It is used for studies that Aspen cannot run in bulk, and as an independent check on Aspen. Where the two differ by model form rather than by error, the difference is kept and quantified: Python is 20.8 kW above Aspen in the FEHE, a model-form difference (Section 4.4).

## 2.4 Unified reference scenario

All Phase 2 economic results use one reference scenario (version 1.0.0): 8000 operating hours per year, a 10 % discount rate, a 25-year life, grey ammonia at 450 USD/t, and electricity at 0.1402 USD/kWh. Capital cost follows the itemised installed cost of the Cho et al. (2026) nickel plant in 2024 USD, with the product compressor removed, each item scaled by the size ratio to the power 0.8 (Chopra et al., 2026), and outside battery limits, engineering and contingency added as in Cho et al. (2026). Calculations are in USD; every output is also reported in SGD at 1.288444 SGD/USD, the cross rate of the European Central Bank reference rates of 20 November 2026 (European Central Bank, 2026).

The capital cost of 7.67 MUSD is the highest of the comparable estimates; the independent published range of 3.1 to 6.5 MUSD, normalised to the AmCraX plant, would give 3.64 to 3.92 USD/kg. This choice works against cracking: it raises the LCOH, lowers the break-even ammonia price and widens the direct-use advantage in H1. The selection criteria were recorded together with the choice; that they preceded the comparison cannot be shown. No verdict changes across the independent capital range. Two earlier baselines, 3.919 USD/kg (a legacy plant-level correlation) and 3.613 USD/kg (the Phase 1 equipment method), are superseded for research outputs.

The supplementary ammonia burned for process heat is counted at 100 % of its lower heating value. This is optimistic. The stored flowsheet delivers 92.25 % of the tail-gas heating value to the process and the catalyst comparison uses 85 %; at these values the LCOH is 4.038 and 4.063 USD/kg and the break-even ammonia price 317.9 and 315.5 USD/t. The assumed PSA recovery of 0.85 lies above the only published front for this gas composition (Abdoos et al., 2025, simulated at 8 to 12 bar); at its recoveries of 0.8192 and 0.7744 the LCOH is 4.066 and 4.146 USD/kg (break-even 314.1 and 304.9 USD/t). The reference values are kept frozen and printed with these envelopes.

Catalyst prices are derived from metal content plus a non-metal part, because no supplier quotation was found (Table 4; Ni/MgO 37 USD/kg). Ruthenium values used in earlier studies (for example 542 USD/kg in Cho et al., 2026) are below the ruthenium metal value today (U.S. Geological Survey, 2026) and appear only as a labelled historical case. Table 1 gives the reference breakdown.

Table: **Table 1.** Reference levelised cost of hydrogen (LCOH), grey NH~3~ at 450 USD/t, heat integration on, plant gate, fuel counted at 100 % of its lower heating value (optimistic; 4.038 to 4.063 USD/kg at 92.25 to 85 %). *Source: results/research/reference_scenario/baseline.json.*

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

The net present value at a selling price of 3.06 USD/kg, the north-east Asia steam-reforming marker (Argus Media, 2026), is -17.46 MUSD (-17.87 to -18.32 MUSD over the fuel envelope), and no internal rate of return exists at that price.

## 2.5 Verdict methodology and its provenance

Version 1 of the verdict rule called a hypothesis SUPPORTED only if every row was SUPPORTED; under it every hypothesis was INCONCLUSIVE. Version 2 keeps the row standard and changes the aggregation. Each hypothesis is split into components, the separable claims inside it. Primary rows test a component directly; secondary rows test whether a number quoted in the essay can be reproduced, and do not vote.

A row is SUPPORTED only if its result is computed, does not follow from an assumption built into the model, holds across its sensitivity or uncertainty range, and has a stated envelope. A row whose direction follows from an assumption can become SUPPORTED only through a threshold analysis: compute the value of the assumed quantity at which the conclusion reverses, and compare it with sourced values. If sourced values lie clearly on one side, the row is SUPPORTED inside the envelope they define. If no source exists, or sourced values straddle the threshold, the row is INCONCLUSIVE and the threshold is the finding. A row that makes two claims needs both. A result smaller than the numerical resolution of the model cannot decide a row. A hypothetical scenario can only support a row that is explicitly conditional on it.

Components are SUPPORTED when every primary row is SUPPORTED, MIXED when at least one is SUPPORTED and one CONTRADICTED, PARTIALLY SUPPORTED when at least one is SUPPORTED and none CONTRADICTED, CONTRADICTED when none is SUPPORTED and at least half are CONTRADICTED, and INCONCLUSIVE otherwise. The hypothesis verdict follows from the components by the same pattern; a MIXED component counts for nothing at hypothesis level. The version 1 verdict is shown beside every version 2 verdict.

Provenance is stated plainly. Only the roles, the components, the aggregation rule and the general row standard were fixed in a commit before the analyses. The row-by-row coded rules were written after the results were known. They were then tested by an independent adversarial review, which moved three rows from SUPPORTED to INCONCLUSIVE: H2-b, H3-d and H4-e (Section 3).

## 2.6 Uncertainty quantification

Global sensitivity of the LCOH, the reconversion cost and the net present value was computed with variance-based Sobol indices (Saltelli et al., 2010; Jansen, 1999) over ten inputs with sourced ranges (ammonia price, capital multiplier and scaling exponent, PSA recovery, operating hours, discount rate, plant life, electricity price, catalyst price and lifetime), with N = 8192 base samples and 1000 bootstrap resamples. The estimator was checked on the Ishigami function (maximum error 0.0017 against a tolerance of 0.02). Kinetic parameter uncertainty was propagated by Latin-hypercube sampling of the published parameter intervals of the Lucentini laws; the Takahashi laws were recalibrated with an adaptive Metropolis sampler (Haario et al., 2001) in the Bayesian calibration framework of Kennedy and O'Hagan (2001), with the rank-normalised R-hat as convergence check (Vehtari et al., 2021). The result describes the uncertainty of a model given its stated input ranges; it is not experimental validation.

## 2.7 Interactive simulator

The project website opens with an interactive process simulator, a static page that cannot run Aspen or Python. Its numbers come from stored results, interpolation of stored grids, or browser code tested against the Python model. It uses an ideal-gas equilibrium, has no membrane model, and its animation shows flow paths only, not a transient simulation.

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

Yes, under the modelled conditions: direct ammonia combustion gives cheaper electricity than the standalone cracking pathways (about 8 to 17 %; 5 to 15 % on the earlier cost basis). The gas turbine is not modelled: both fuels are assumed to run at the same 49.64 % efficiency, and the actual advantage depends on fuel-specific turbine performance.

Because the direction of row H1-a follows from that assumption, the threshold test decides it (Figure 2). For cracking with PSA, the turbine on pure hydrogen would need an efficiency 12.55 percentage points above the ammonia turbine to match direct use. The only sourced comparison is the difference between two National Energy Technology Laboratory studies, pure hydrogen (steam-diluted) against pure ammonia, which gives +7.3 points (National Energy Technology Laboratory, 2023, 2024). This is a single source, an H-class cycle simulation with steam-diluted hydrogen and not like for like with the 49.64 % AmCraX turbine; it is treated as an upper bound. It lies below the threshold on every one of the 11 bases. For fired cracking without purification the threshold is +5.16 points, and no source gives a turbine efficiency on the H~2~/N~2~ fuel of a fired cracker. Row H1-a claims both halves, so it is INCONCLUSIVE; the purified half alone passes the test against that single source.

The cracker heat is counted at 100 % of the fuel's lower heating value, which favours cracking. At 92.25 % and 85 % the fired-cracking threshold rises from +5.16 to +5.82 and +6.54 points, and the PSA threshold from +12.55 to +12.94 and +13.38 points (computed); no verdict changes.

![**Figure 2.** Turbine-efficiency thresholds for H1. Left: the efficiency gain on H~2~-rich fuel, relative to 49.64 %, at which fired and purified cracking pathways would match direct NH~3~ combustion; dots at the reference basis, bars over 11 bases; dashed line the NETL upper bound of +7.3 points. Right: the system efficiency gain needed by exhaust-heated cracking; shaded band the sourced 4.9 to 5.5 points. *Source: results/research/enduse/turbine_threshold.json; cracker from stored Aspen Plus V15 runs; turbine calibrated to Ahmad et al. (2025).*](../../results/figures/research/enduse_turbine_threshold.png){width=100%}

Row H1-c asks whether cracking pays where ammonia could be burned directly. Exhaust-heated full cracking raises the system efficiency by a sourced 4.9 to 5.5 points (Ahmad et al., 2025, rescaled to the AmCraX heating-value basis; Karpilov et al., 2025, maximum values), against a threshold of +4.04 points. On the reference basis it is therefore about 1.3 % cheaper than direct use, which goes against the essay. The outcome is not robust: a cracker capital cost 1.22 times the reference removes the advantage, and an ammonia price of 300 USD/t, 6000 operating hours or less, or a doubled cracker capital cost favour direct use. Row H1-c is INCONCLUSIVE.

Row H1-d tests the second half of the hypothesis: cracking is justified where hydrogen is the product. Cracked hydrogen from grey ammonia costs 4.015 USD/kg, above the 3.06 USD/kg north-east Asia steam-reforming marker and below the 6.0 USD/kg delivered low-carbon benchmark. The energy side depends again on the turbine assumption (per kg of ammonia, 2.565 kWh direct; 2.251 to 2.582 kWh by cracking with PSA). Row H1-d is INCONCLUSIVE.

Row H1-b is secondary. It tests the essay's "about 40 % cheaper power", attributed to Halim et al. (2025). The largest computed gap in the cost of electricity is 16.6 %, so the essay's sentence is CONTRADICTED; the row does not vote. The paper, read in full, computes no cost of electricity: its 39 % (green) and 44 % (blue) compare fuel cost per kg of hydrogen-equivalent energy at the turbine inlet, with one vendor turbine efficiency for every fuel. On that basis AmCraX gives 20 to 33 % (27.7 % for grey ammonia), the same direction and a smaller gap, reconciled to within half a point by the paper's lower energy retention (69.5 against 87.7 %) and its storage and capital costs.

**H1 answer: yes, under the modelled conditions**; the turbine efficiency is assumed, and exhaust-heated cracking and hydrogen as the product are not established. Formal classification (rule fixed before the analysis): INCONCLUSIVE (version 1 the same), components H1-P and H1-Q INCONCLUSIVE, because the assumed efficiency cannot count as support.

## 3.2 H2: feedstock

**Economic component (H2-E).** Ammonia feed is 3.040 of 4.015 USD/kg, a share of 75.7 %. The Sobol analysis (Figure 3) gives the ammonia price a total-effect index of 0.896 (95 % interval 0.875 to 0.917) on the LCOH; the capital multiplier follows at 0.063 and the PSA recovery at 0.033.

![**Figure 3.** First-order (S1) and total-effect (ST) Sobol indices of the LCOH, grey scenario, heat integration on, N = 8192, with 95 % bootstrap intervals. *Source: results/research/uq/gsa_sobol.json; Python cost model on the stored Aspen Plus V15 baseline.*](../../results/figures/research/uq_gsa_sobol.png){width=80%}

Feed dominance follows from assumed prices, so the threshold test was applied with one comparator, a feed share of 50 %. The feed share falls to 50 % only below 115 USD/t of ammonia (174 USD/t with adverse non-feed inputs), or at a capital multiplier of 4.27 at 450 USD/t (2.81 at 300 USD/t). The lowest sourced ammonia price is 300 USD/t. The largest capital multiplier considered, 1.5, is the sensitivity bound of Cho et al. (2026), not a sourced cost; the independent published estimates correspond to 0.41 to 0.85. All values lie on the feed-dominant side, so row H2-a is SUPPORTED, inside the envelope of capacity scale 1, both heat-integration cases and PSA recovery down to 0.756. The reconversion cost, the cost excluding feed, is driven instead by the capital multiplier (total-effect index 0.473) and PSA recovery (0.420).

Row H2-b states that only affordable ammonia keeps cracked hydrogen competitive. The break-even ammonia price against the 3.06 USD/kg marker is 320 USD/t: 277 to 371 USD/t over the capital range (multipliers 1.5 to 0.41) and 379 USD/t with favourable non-feed inputs (315.5 to 317.9 USD/t over the fuel envelope). Against a 6.0 USD/kg delivered low-carbon benchmark it is 720 USD/t. Sourced prices start at 300 USD/t (grey, low) and 315 USD/t (green 2050, low) and reach 1052 USD/t, so they straddle both break-evens. Row H2-b is INCONCLUSIVE and the threshold is the finding: only the low ends of the sourced ranges reach about 320 USD/t. An earlier reading as a necessity statement against central prices had no way to fail and was replaced. The probability of an LCOH below 3.06 USD/kg is 1.4 %, conditional on the assumed triangular input distributions. Component H2-E is PARTIALLY SUPPORTED.

**Environmental component (H2-C).** The life-cycle carbon intensity of cracked hydrogen, in kg CO~2~e per kg H~2~, is 19.52 for grey ammonia (range 15.11 to 34.22), 8.93 for blue ammonia (6.07 to 14.53), and 2.43 for green ammonia including embedded emissions (0.93 to 3.93) (Lee et al., 2022, with AmCraX accounting). For cracked hydrogen to beat unabated steam reforming, ammonia must be produced at 1.31 to 1.58 kg CO~2~e/kg NH~3~ or less; for direct ammonia power to beat a natural-gas combined cycle, at 0.81 to 1.33. The lowest sourced value for grey ammonia, 2.0, is above every break-even, and green ammonia lies below them. Rows H2-c and H2-d are SUPPORTED as necessity statements. Against steam reforming with capture (break-even 0.41 to 0.67, reported, not voted) grey fails and green passes only below the break-even; its high value of 0.48 fails the strictest case. Component H2-C is SUPPORTED.

**Cross-claim (H2-X): is low carbon intensity rewarded economically?** This was evaluated in two modes, kept apart. Mode A is the actual Singapore boundary (Carbon Pricing Act 2018, 2020 Rev. Ed.): SGD 45 per tCO~2~e for 2026 and any later year, applied only to direct facility emissions at or above 25,000 tCO~2~e per year, with a global warming potential of 265 for N~2~O. A rise to 50 to 80 SGD/t by 2030 is a stated aim, not law. The self-fired reference plant burns ammonia for heat, emits no direct CO~2~ and is far below the threshold, and upstream emissions of imported ammonia are outside the Act. The tax is zero for every ammonia route, so low-carbon ammonia earns no cost advantage: blue ammonia raises the LCOH by 0.272 USD/kg and green ammonia at current prices by 4.04 USD/kg. Row H2-e is CONTRADICTED under Mode A. This follows from the statute, not from a model assumption.

Mode B applies a hypothetical life-cycle carbon price to the embodied emissions of each route. It is hypothetical and is not Singapore law. Table 3 gives the carbon prices at which one route overtakes another (Figure 4).

Table: **Table 3.** Mode B, hypothetical life-cycle carbon price (not Singapore law): crossover prices between ammonia routes, SGD/tCO~2~e. *Source: results/research/carbon_pricing/thresholds.json.*

| Crossover | Central | Range from carbon-intensity ranges |
|---|---:|---|
| Blue overtakes grey | 33 | 12 to 605 |
| Green (current price) overtakes grey | 305 | 156 to 466 |
| Green (2030 projection) overtakes grey | 144 | 74 to 219 |
| Green (current price) overtakes blue | 747 | 357 to 2275 |

![**Figure 4.** Mode B: LCOH by ammonia route against a hypothetical life-cycle carbon price, which is not Singapore law. Bands show the carbon-intensity ranges. Vertical lines mark the legislated SGD 45, the stated 2030 aim of 50 to 80, and an EU emissions-trading level for context. Under Mode A, the actual Singapore boundary, the carbon cost is zero for every route. *Source: results/research/carbon_pricing/scenarios.json and price_sweep.csv.*](../../results/figures/research/carbon_price_sweep.png){width=90%}

Under the hypothetical Mode B price, grey ammonia is cheapest up to about 33 SGD/t and blue ammonia above that; green ammonia at current prices is never cheapest up to 500 SGD/t. The blue-over-grey range of 12 to 605 straddles every reference price, so H2-e under Mode B is INCONCLUSIVE. It is reported beside the verdict and does not change the row about actual policy.

**H2 answer: yes** for feed dominance and the emissions need, no for a cost reward under the actual tax, not established for affordability. Formal classification (rule fixed before the analysis): MIXED (version 1: INCONCLUSIVE). H2-E is PARTIALLY SUPPORTED (H2-a SUPPORTED, H2-b INCONCLUSIVE), H2-C is SUPPORTED, and the cross-claim H2-X is CONTRADICTED under the actual Singapore carbon tax.

## 3.3 H3: catalyst and heat integration

**Lower-temperature operation (H3-T).** Phase 1 reported a 17 % reduction of fired process duty for Ru/Al~2~O~3~ at 499 °C against Ni/MgO at 594 °C, from Aspen runs with 100 kg of catalyst that reached unequal conversion (Ni 0.9589, Ru 0.9496); most of that figure is an artefact and it is withdrawn. At equal conversion of 0.95 and 20 bar (Python only), the fired duty with heat integration is 485.1 kW for Ru/Al~2~O~3~ against 510.3 kW for Ni/MgO, a saving of 25.1 kW. This is 4.9 % of the supplementary fired duty and 1.1 % of the 2293 kW total external heating. Without heat integration the saving is 31 to 163 kW. With heat integration the saving exceeds the 15 kW Python against Aspen offset only for the two ruthenium catalysts, whose temperature differences from Ni/MgO are 72 K or more (Ru/MgO 18.6 kW, Ru/Al~2~O~3~ 25.1 kW); for the Ni-Ru catalysts it is 4 to 5 kW. The resolution has two readings: the absolute Python-Aspen offset (15.2 kW; 0.0060 USD/kg), used for the verdicts, and the spread of that offset across catalysts (1.4 kW; 0.0006 USD/kg), under which the Ni-Ru savings would also be resolved. When the designs are optimised for cost, the ruthenium designs run hotter and use 19 to 21 kW more energy. Row H3-a is SUPPORTED inside this narrow envelope.

Row H3-b states that the active catalysts allow a lower temperature for the same duty. The temperature ordering rests on rate laws extrapolated to 20 bar, and kinetic uncertainty is large: for 5Ni1Ru/CeO~2~ the temperature for a conversion of 0.95 spans 529 to 615 °C (5th to 95th percentile). Row H3-b is INCONCLUSIVE. Component H3-T is PARTIALLY SUPPORTED.

**Heat integration (H3-H).** Row H3-d claims that heat integration reduces energy use and cost, and both halves are needed. The energy half is computed: in Aspen, the FEHE reduces the first-law heat deficit from 1385.1 to 772.9 kW (44 %) and the total external heating from 2905.3 to 2293.1 kW (21 %), far more than the catalyst temperature does. For the cost half the exchanger was sized (five 1-2 shells in series, because of a temperature cross) and costed at 1.44 to 1.78 MUSD for overall heat-transfer coefficients of 150 to 35 W/(m^2^ K) (Turton et al., 2018). The gross saving of 0.214 USD/kg (0.232 and 0.251 at 92.25 and 85 % fuel efficiency) leaves +0.067 to +0.095 USD/kg after the annualised exchanger cost. The break-even coefficient is 7.7 to 11.3 W/(m^2^ K), and the break-even capital recovery factor 0.186, 0.223 and 0.244 at low, central and high coefficient; the worst sensitivity case is -0.012 USD/kg. No sourced coefficient at 20 bar was found; the only sourced range, 5 to 35 W/(m^2^ K) for gas at about 1 bar (VDI e. V., 2010), straddles the break-even. The cost half is INCONCLUSIVE, so row H3-d and component H3-H are INCONCLUSIVE; the energy reduction is reported as a finding. The exchanger cost is added on top of the reference heat-exchanger item, which makes the net benefit conservative.

**Catalyst cost (H3-K).** Table 4 summarises the catalyst economics.

Table: **Table 4.** Low-temperature catalysts against Ni/MgO at its modelled 594 °C, equal conversion 0.95, 20 bar, heat integration and exchanger costed, catalyst lifetime 2 years. A positive LCOH difference means the low-temperature catalyst is dearer; the resolution is 0.006 USD/kg. Break-even prices hold each design at its equal-conversion temperature. All results rest on laws extrapolated to 20 bar. *Source: results/research/catalyst_economics/catalyst_economics.json and catalyst_breakeven.csv.*

| Catalyst | Derived central price (USD/kg) | Metal-content floor (USD/kg) | LCOH difference (USD/kg H~2~) | Break-even price (USD/kg) | Ni temperature at which it wins, kinetics-free (°C) |
|---|---:|---:|---:|---:|---:|
| Ru/Al~2~O~3~ | 4791 | 1775 | +0.081 | 1506 | 670 |
| Ru/MgO | 3006 | 1109 | +0.043 | 1297 | 676 |
| 5Ni1Ru/CeO~2~ | 628 | 223 | +0.011 | 177 | 640 |
| 2.5Ni0.5Ru/CeO~2~ | 330 | 111 | +0.005 | 151 | 540 |

With heat integration, at derived central prices and with the nickel reference at its modelled 594 °C (an extrapolated law), three of the four low-temperature catalysts are dearer than Ni/MgO beyond the model resolution; 2.5Ni0.5Ru/CeO~2~ (+0.005 USD/kg) is within it. Without heat integration the two Ni-Ru catalysts are slightly cheaper (-0.0010 and -0.0056 USD/kg). Each break-even price in Table 4 is below the derived central price; only for the cost-re-optimised designs at the central price are the ruthenium break-evens also below the ruthenium metal value. When temperature and catalyst mass are optimised for cost, an expensive catalyst is best used as a small charge at a high temperature (Ru/Al~2~O~3~ at 614 °C with 7.5 kg), so the low-temperature operation the hypothesis needs is not chosen.

The outcome depends on the temperature at which nickel must run. Against the sourced nickel design temperatures of 736 °C (Cho et al., 2026) and 760 °C (Mehr et al., 2026), above the kinetics-free thresholds of 540 to 676 °C, every low-temperature design is cheaper. The AmCraX Ni/MgO law places the nickel cost optimum at 537 to 549 °C, below most thresholds. The sourced values and the model straddle the threshold, so row H3-c and component H3-K are INCONCLUSIVE; at derived ruthenium prices the evidence leans against the hypothesis. Two secondary rows test reproductions of Cho et al. (2026): their supplementary-fuel pattern appears only for PSA recoveries of 0.7564 to 0.7813 (H3-e), and their 7.0 % lower relative economic cost for ruthenium becomes -16.2 to +1.6 % depending on the price and inventory basis (H3-f). Both are INCONCLUSIVE and do not vote.

**H3 answer: yes for energy, modestly**; cost and catalyst trade-off not established. Formal classification (rule fixed before the analysis): PARTIALLY SUPPORTED, resting only on H3-T (version 1: INCONCLUSIVE). H3-T is PARTIALLY SUPPORTED (H3-a SUPPORTED in a narrow envelope, H3-b INCONCLUSIVE), H3-H is INCONCLUSIVE and H3-K is INCONCLUSIVE.

## 3.4 H4: purification

H4 has one component, H4-B: purity must be balanced against recovery, energy and cost.

Row H4-a asks whether higher PSA purity costs recovery. No PSA purity-recovery relation is computed in AmCraX; the PSA is a splitter with an assumed recovery. Two published relations show the direction: a measured slope (75.3 to 55.5 % recovery between 99.25 and 99.97 % purity) for a different feed (Yáñez et al., 2020), and a simulated front for dry, ammonia-free cracked-ammonia composition at 8 to 12 bar (Abdoos et al., 2025: 83.92 % at 99.03 %, 81.92 % at 99.95 %, 77.44 % at 99.99 %). Neither is computed by AmCraX, so row H4-a is INCONCLUSIVE.

Row H4-b asks whether stricter purity raises the cost per kg of usable hydrogen. The order raw product < industrial 99.9 % < fuel-cell Grade D (International Organization for Standardization, 2019) holds in every sourced combination (3.784, 3.984 and 4.237 USD/kg at the cheapest configuration of each), but most of the Grade D increment is the 350 bar delivery pressure; the increment from purity alone is 0.002 (assumed mass balance), 0.080 (Abdoos front) or 0.166 USD/kg (Yáñez points), and three points of the front's surrogate scatter reverse the sign of the Abdoos value. Row H4-b is INCONCLUSIVE.

Row H4-e asks whether recovery losses trade against energy. In the flowsheet, hydrogen not recovered is burned in the cracker furnace; this restates the tail-gas routing, an assumption built into the model, so the threshold test decides the row. At a recovery of 0.765 the tail-gas heat equals the furnace demand of 2293 kW. Above it, supplementary ammonia must be burned (a 773 kW deficit at the assumed 0.85); below it, the lost hydrogen has no use in this flowsheet. Sourced and assumed recoveries of 0.555 to 0.85 lie on both sides, so row H4-e is INCONCLUSIVE and the threshold is the finding.

Row H4-d, secondary, compares PSA with a Pd-Ag membrane (Figure 5). For industrial purity the PSA LCOH is 5.605, 4.269 or 4.046 USD/kg at recoveries of 0.5715 (Yáñez et al., 2020, different feed), 0.7516 (mass-balance relation) and 0.85 (assumption). The membrane, annualised with the capital recovery factor over its life, gives 4.109 to 4.282 USD/kg over sourced costs. Over the full factorial of sourced inputs it is cheaper in 56.9 % of pairs for industrial purity and 57.5 % for Grade D. The ranking reverses at a PSA recovery of 0.795 (industrial) or 0.783 (Grade D) against the central membrane, and sourced PSA values straddle these. The required ideal H~2~/N~2~ selectivity for Grade D is 12,919; Cechetto et al. (2021) report 40,541 (from the printed permeances) to 500,000 (stated) for a new membrane in single-gas tests. Technology readiness favours PSA (unit level 9 against 4 to 5), and a recent membrane demonstration missed its recovery target (Gemserv Ltd et al., 2025). Row H4-d is INCONCLUSIVE.

![**Figure 5.** LCOH of usable hydrogen against PSA recovery for industrial 99.9 % hydrogen at 30 bar (left) and ISO 14687:2019 Grade D at 350 bar (right), with the central Pd-Ag membrane case. Marked points are published or assumed recoveries; recovery is an input, as no adsorption-cycle model exists. *Source: results/research/purification/phase2_comparison.json; Python reduced-order models on Aspen Plus V15 cracked gas.*](../../results/figures/research/purification_phase2_psa_recovery.png){width=100%}

Row H4-c, secondary, is CONTRADICTED: the published PSA point of Cho et al. (2026), 75.6 % recovery at 99.11 % H~2~, leaves about 8900 ppm N~2~ and does not meet ISO 14687 grades for fuel cells.

**H4 answer: not established.** Formal classification (rule fixed before the analysis): INCONCLUSIVE (version 1 the same); every primary row of H4-B is INCONCLUSIVE.

## 3.5 Summary of answers

Table: **Table 5.** Plain answers first, with the claims inside each hypothesis, then the formal classification under the version 2 rule fixed before the analysis (version 1 in brackets). Plain answers are a reading aid derived in code from the formal rows: Yes only where the test is SUPPORTED, Yes (assumption) only where the result is computed in the claimed direction on every basis and the test is inconclusive solely because one unsourced quantity is assumed, No only where CONTRADICTED, otherwise not established. They change no classification. *Source: results/research/evidence_matrix.json (headline_answer, plain_answers); rule in docs/research/verdict_methodology_v2.md.*

| Plain answer | Hypothesis | Claims | Formal classification (rule fixed before the analysis) |
|---|---|---|---|
| Yes, under the modelled conditions | H1 end use | Cheaper than cracking + PSA for power: Yes. Cheaper than fired cracking: Yes (assumption: same 49.64 % turbine efficiency; break-even +5.16 points). Turbine-front cracking does not pay: not established. Justified for hydrogen as product: not established. | INCONCLUSIVE (INCONCLUSIVE); H1-P, H1-Q INCONCLUSIVE |
| Yes | H2 feedstock | Ammonia price dominates: Yes. Low-carbon ammonia needed for lower emissions: Yes. Cheap ammonia makes it competitive: not established (320 USD/t). Rewarded in Singapore: No. | MIXED (INCONCLUSIVE); H2-E PARTIALLY SUPPORTED, H2-C SUPPORTED, H2-X CONTRADICTED |
| Yes for energy | H3 catalyst and heat integration | Lower temperature saves energy: Yes, modestly. Heat integration saves energy: Yes; saves cost: not established. Active catalysts at 20 bar: not established. Savings outweigh catalyst cost: not established, leaning no. | PARTIALLY SUPPORTED, resting only on H3-T (INCONCLUSIVE) |
| Not established | H4 purification | Purity costs recovery, raises cost, tail gas offsets fuel, membrane beats PSA: all not established. | INCONCLUSIVE (INCONCLUSIVE) |

# 4 Discussion

## 4.1 What the evidence supports

The strongest result is about cost structure, not technology choice. On a conservative capital basis, ammonia feed is three quarters of the cost of cracked hydrogen and its price explains about 90 % of the variance of the LCOH; the capital cost would have to rise more than fourfold before feed fell to half of the cost. The reconversion cost is different: there, capital cost and PSA recovery dominate, and these are the quantities that engineering can change.

The second result is that cracking ammonia to pure hydrogen in order to burn it in a turbine does not pay against burning ammonia directly unless a hydrogen turbine is more than 12.55 percentage points more efficient than an ammonia turbine. The only sourced comparison, a single upper-bound estimate, suggests at most 7.3 points.

Several results are thresholds rather than verdicts: the ammonia price at which cracked hydrogen meets the marker (320 USD/t), the heat-transfer coefficient at which the exchanger pays (7.7 to 11.3 W/(m^2^ K)), the nickel temperature at which low-temperature catalysts win (540 to 676 °C) and the PSA recovery at which the tail gas covers the furnace (0.765). Each is the number a measurement must beat.

## 4.2 Findings against the original essay

1. **Exhaust-heated cracking is slightly cheaper than direct use.** On the reference basis, cracking with turbine exhaust heat is about 1.3 % cheaper than direct combustion, and partial cracking to 40 vol% hydrogen costs the same. The margin reverses with plausible changes of capital cost, ammonia price or operating hours, so the row is INCONCLUSIVE rather than CONTRADICTED. It does not support the essay.
2. **At derived ruthenium prices, the low-temperature catalysts mostly do not pay.** With the nickel reference at its modelled 594 °C, three of the four low-temperature catalysts are dearer beyond the model resolution and the fourth is within it; without heat integration the two Ni-Ru catalysts are slightly cheaper. Against the sourced nickel design temperatures of 736 and 760 °C, every low-temperature design is cheaper.
3. **The energy saving of low-temperature operation is at most 25 kW, not 17 %.** It is 4.9 % of the fired duty and 1.1 % of the total external heating at equal conversion. The Phase 1 figure came from unequal conversion and is withdrawn.
4. **Low-carbon ammonia is not rewarded by the actual Singapore carbon tax.** The tax covers direct facility emissions above a threshold; the cracker emits almost none, and the emissions embodied in imported ammonia are outside the Act. A life-cycle carbon price would change this, but such a price is hypothetical.

## 4.3 What changed since the Phase 1 release

Unifying the two Phase 1 cost bases (3.92 and 3.61 USD/kg) raised the baseline to 4.015 USD/kg, mainly through the capital cost (7.67 against 2.78 MUSD); the break-even ammonia price fell from 375 to 320 USD/t. The classification changes come from new evidence, the version 2 aggregation and the stricter row reading after the adversarial review, which moved three rows down, not up.

## 4.4 Validation status by evidence kind

Table 6 counts the research validation items by the kind of evidence they provide. The core flowsheet validation matrix is counted separately: of its 137 items, 105 pass, 22 fail and 10 are informational; twenty of its failures share one cause, a feed-section enthalpy difference between the property models.

Table: **Table 6.** Research validation items by evidence kind and status, 24 November 2026. *Source: results/research/validation/summary.json.*

| Evidence kind | Pass | Fail | Informational | Not available | Total |
|---|---:|---:|---:|---:|---:|
| Numerical verification | 440 | 5 | 19 | 0 | 464 |
| Python against Aspen comparison | 156 | 5 | 22 | 0 | 183 |
| Comparison with published literature | 11 | 2 | 35 | 0 | 48 |
| Independent experimental validation | 0 | 0 | 0 | 1 | none exists |
| **Total** | **607** | **12** | **76** | **1** | **696** |

The numerical-verification failures are RPlug runs that end slightly above equilibrium (up to 4.9 × 10^-4^ against a tolerance of 10^-4^), traced to how Aspen evaluates the reverse-rate term. The Python against Aspen failures are five FEHE duty checks: Python is 20.8 kW above Aspen, from a different vaporiser outlet state (8.76 kW) and the residual-enthalpy model of ammonia (12.1 kW); on the Peng-Robinson basis it reproduces the Aspen duty within 0.12 %. The literature failures are the two Takahashi prediction checks, a limit of the published law, not an implementation error. All stay recorded as failures at unchanged tolerances.

None of these counts is experimental validation. AmCraX has no measurement of its own and no comparison with plant data. Agreement between Aspen and Python shows that two implementations agree, not that either is right, and no model is called validated outside the range in which it was checked.

# 5 Limitations

- No supplier catalyst quotation exists; all catalyst prices are derived from metal content.
- No sourced overall heat-transfer coefficient at 20 bar, turbine efficiency for the H~2~/N~2~ fuel of a fired cracker, or measured PSA recovery on cracked ammonia exists, and AmCraX has no adsorption-cycle model.
- The PSA threshold of H1 rests on a single upper-bound source.
- Halim et al. (2025), Abdoos et al. (2025) and the main text of Sayas et al. (2020) were read in full on 24 November 2026; no classification moved. The Sayas supplementary information (the Ru-K/CaO rate constant) was not obtained.
- No rate law is validated at 20 bar; three are validated against their own fitting data, two are extrapolated, three catalysts are not modelled, and the Takahashi laws under-predict the dilution and hydrogen co-feed series.
- The reference capital cost comes from one paper's itemised table; for the power-plant cracker it is extrapolated more than 30-fold. The exchanger cost is added on top of the reference heat-exchanger item.
- Supplementary fuel is counted at 100 % of its lower heating value (optimistic); the envelope is given beside the reference values.
- The electricity cost covers pump power only; PSA and compression power are outside the cost boundary.
- The main hydrogen benchmark is one regional marker (3.06 USD/kg); no Singapore hydrogen transaction price exists.
- The browser simulator has no membrane model and uses an ideal-gas equilibrium.
- There is no experimental validation of any kind.

# 6 Conclusions

On one frozen, conservative cost basis, cracked hydrogen from grey ammonia in a 1.7 t/h plant in Singapore costs 4.015 USD/kg (5.174 SGD/kg) with fuel counted at 100 % of its lower heating value, and 4.038 to 4.063 USD/kg at 92.25 to 85 %. The ammonia price is the decisive input. The answers, with the formal classification after each, are:

- **H1: yes, under the modelled conditions.** Direct ammonia combustion gives electricity about 8 to 17 % cheaper than standalone cracking. The gas turbine is not modelled: both fuels are assumed at 49.64 % efficiency. Cracking with PSA would need a turbine 12.55 points more efficient, above the single sourced upper bound of 7.3; fired cracking (+5.16 points) has no sourced efficiency; exhaust-heated cracking is about 1 % cheaper than direct use on the reference basis (not robust). Formal classification: INCONCLUSIVE.
- **H2: yes** for feed dominance and the emissions need. Feed dominates the cost: competitiveness with the marker needs ammonia at or below about 320 USD/t (277 to 371), a threshold that sourced prices straddle. Low-carbon ammonia is necessary for lower emissions (H2-C SUPPORTED). Under the actual Singapore carbon tax it earns no cost advantage. Formal classification: MIXED.
- **H3: yes for energy, modestly.** Lower-temperature operation saves at most 25 kW at equal conversion, resolved only for the ruthenium catalysts. Heat integration cuts the heat deficit by 44 %, but whether it pays depends on an unsourced heat-transfer coefficient (H3-H INCONCLUSIVE). Whether the savings outweigh catalyst cost is not established and leans no at derived ruthenium prices. Formal classification: PARTIALLY SUPPORTED, resting only on H3-T.
- **H4: not established.** Published PSA relations agree that purity costs recovery, but AmCraX computes none; the tail gas covers the furnace below a PSA recovery of 0.765, with sourced recoveries on both sides; PSA against a Pd-Ag membrane turns on PSA recovery. Formal classification: INCONCLUSIVE.

The most useful next measurements, each closing a threshold identified here, are a catalyst quotation, a measured PSA recovery on cracked ammonia, a turbine efficiency on cracked fuel, a rate law fitted at elevated pressure and an FEHE heat-transfer coefficient at 20 bar.

# Data and code availability

The models, Aspen input files, stored results, figures, tests and documents are available at <https://github.com/weewzr/AmCraX>. The Phase 1 release is preserved under the tag amcrax-research-expansion-2026-11-23; the Phase 2 results reported here are in the repository after that tag, and every number changed by the fix pass is recorded in `results/research/fix_pass_2026-11-24.json`. The reference scenario is `backend/amcrax/data/reference_scenario.yaml`, the verdict rule is `docs/research/verdict_methodology_v2.md`, and every number in this paper traces to a file under `results/research/`. The interactive simulator is published at <https://weewzr.github.io/AmCraX/>. Aspen Plus V15 is commercial software; its stored outputs are included, and the Python models run without it.

# References

Ahmad, A. H., Tsujimura, T., Shimura, M., Fan, Y., Ito, H., Iki, N., Kurata, O., Jo, H., & Aziz, M. (2025). Thermodynamic and preliminary techno-economic analysis of NH3 utilization in combined cycle power plant: Comparison of direct liquid, vaporized, and cracked NH3-based combustion methods. *International Journal of Hydrogen Energy*, *173*, 151337.\
<https://doi.org/10.1016/j.ijhydene.2025.151337>

Argus Media. (2026). *Argus Hydrogen and Future Fuels, sample report (regional hydrogen cost markers)*.\
<https://view.argusmedia.com/rs/584-BUW-606/images/POW-Sample-Report-20260106-Hydrogen.pdf?version=0>

Bell, I. H., Wronski, J., Quoilin, S., & Lemort, V. (2014). Pure and pseudo-pure fluid thermophysical property evaluation and the open-source thermophysical property library CoolProp. *Industrial & Engineering Chemistry Research*, *53*(6), 2498-2508.\
<https://doi.org/10.1021/ie4033999>

Carbon Pricing Act 2018, 2020 Rev. Ed. (Singapore). Singapore Statutes Online, Attorney-General's Chambers (version in force on 23 November 2026).\
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
