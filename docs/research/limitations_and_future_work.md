# Limitations and future work (Phase 2)

This page lists what the Phase 2 results cannot show, grouped by area (updated for the fix pass of 24 November 2026; every changed number is in `results/research/fix_pass_2026-11-24.json`). Each limitation names its consequence for the conclusions. The last section ranks the next research steps by the value they would add. All numbers come from the result files under `results/research/` and from [unified_baseline.md](unified_baseline.md); where a number is a sourced bound it says so.

Evidence kinds are kept apart throughout: (1) numerical verification, (2) Python against Aspen comparison, (3) comparison with published literature, (4) independent experimental validation. AmCraX has no evidence of kind (4). No model on this page is called validated outside the range in which it was checked.

The older limitation lists remain valid unless this page says otherwise: [../known_limitations.md](../known_limitations.md) (all layers) and [validation_and_limitations.md](validation_and_limitations.md) (per workstream).

## Limitations by area

### Thermodynamics

| Limitation | Consequence for the conclusions |
|---|---|
| The Aspen flowsheet cracker is an equilibrium reactor (RGibbs). Conversion is an upper bound. | Baseline heat duties are those of an equilibrium cracker. Catalyst-specific results come from the kinetic RPlug cases and the Python model. |
| Five feed-effluent exchanger duty checks still fail (Python above Aspen by 3.45 to 4.44 %, tolerance 3 %). The offset is 20.8 kW in every case: 8.8 kW from the vaporiser outlet state and 12.1 kW from the residual enthalpy of ammonia. The tolerance was not changed. | Absolute Python duties carry a known offset. Differences between catalysts are less affected. The H3-a saving (25 kW at equal conversion) is resolved only for temperature differences of 72 K or more, because of the 15 kW Python to Aspen offset. On the spread of that offset across catalysts (1.4 kW) the NiRu savings of 4 to 5 kW would also be resolved; the verdicts use the absolute offset. |
| Three kinetic RPlug checks were above the equilibrium conversion. The cause is the reverse-rate term as implemented in Aspen: part was fixed and part is a limit of the form. The 20 bar cases now pass in the partial-pressure form. The 40 bar case still fails. | Aspen kinetic results at 40 bar are slightly optimistic. The baseline pressure of 20 bar is not affected. |
| The browser simulator uses an ideal-gas equilibrium constant. | Where it differs from Aspen PENG-ROB, the simulator shows the stored Aspen value and labels it. Away from stored cases the difference is of the order seen in the 168-point equilibrium grid (up to 1.48 percentage points between ideal and Peng-Robinson). |

### Kinetics

| Limitation | Consequence for the conclusions |
|---|---|
| No rate law is validated at 20 bar. Three laws are validated against literature, within the conditions of their own fitting data. Two are extrapolated. | The temperature ordering of catalysts at 20 bar (H3-b) is INCONCLUSIVE. |
| Ni/CeO2, Ru/CeO2 and Ru-K/CaO have no rate law. None was invented. | These catalysts are not modelled. Statements about them rest on the cited papers only. |
| The Takahashi laws under-predict the dilution and H2 co-feed series of the held-out data. Two published-curve checks still fail. | This is a model-form limit, not an implementation error. Kinetic results for Ni/MgO and Ru/MgO are approximate. |
| Ni/MgO and Ru/MgO in Aspen use a fitted approximation of the Takahashi law, valid at 20 bar only (RMS rate error 12 %, maximum about 50 %). | These two catalysts are labelled as approximations. |
| Effectiveness factor 1, no pressure drop in the cost studies, no deactivation. | Catalyst masses are lower bounds. |
| Published Lucentini intervals change LCOH by less than 0.035 USD/kg (`results/research/uq/kinetic_param_propagation.json`). | Within the published parameter intervals, kinetic parameter uncertainty is small for cost. Model-form error is not included. |

### Heat integration

| Limitation | Consequence for the conclusions |
|---|---|
| No sourced overall heat-transfer coefficient U at 20 bar for ammonia, hydrogen and nitrogen exists in the library. The central value is an assumption with a range (low, central, high). | The net heat-integration benefit (+0.067 to +0.095 USD/kg after exchanger cost) is threshold-dependent: the break-even U is 7.7 to 11.3 W/(m2 K), inside the only sourced range (5 to 35 at about 1 bar), and the break-even capital recovery factor (solved) is 0.186 / 0.223 / 0.244 at U low / central / high; worst sensitivity case -0.012 USD/kg. The cost half of H3-d is INCONCLUSIVE, so row H3-d and component H3-H are INCONCLUSIVE; the energy reduction (heat deficit 1385 to 773 kW, 44 %) is reported as a finding. |
| Exchanger cost is added on top of the reference CAPEX item. | This is conservative and may double count part of the reference exchanger cost. |
| Pinch targets are thermodynamic targets. No heat-exchanger network was designed. | Network cost and layout are not known. |
| The Phase 1 value of a 17 % lower fired duty came from unequal conversion and is withdrawn. At equal conversion (Python only) the saving with heat integration is at most 25 kW (485 against 510 kW), 4.9 % of the fired duty and 1.1 % of the 2293 kW total external heating; without heat integration 31 to 163 kW. Cost-optimised Ru designs run hotter and use 19 to 21 kW more. | The energy case for a lower temperature is narrower than the essay states. |

### Purification

| Limitation | Consequence for the conclusions |
|---|---|
| The PSA is a component splitter. No cycle, adsorbent, purge or purity-recovery relation is computed. The only sourced slope is for a different feed. | H4-a is INCONCLUSIVE. PSA recovery stays an input. |
| The ranking of PSA against a Pd-Ag membrane depends on PSA recovery. Parity is at a PSA recovery of 0.783 (Grade D) and 0.795 (industrial) against the central membrane, 0.745 and 0.749 against the high-cost membrane. The ranking reverses inside sourced ranges. | H4-d is INCONCLUSIVE. No technology ranking is claimed. |
| Membrane selectivity is ideal, single gas, for a new membrane. The source gives 40,541 (from the printed permeances) and 500,000 (stated). The paper is internally inconsistent, so both are carried. The requirement computed for this case is 12,919. | Membrane purity is an upper bound. Membrane TRL is 4 to 5 against 9 for PSA. |
| The purity-only increment of Grade D hydrogen is 0.002 to 0.17 USD/kg and rests on a proxy. Most of the Grade D cost increment is 350 bar delivery. | H4-b is INCONCLUSIVE under the strict row rule. |
| No NH3 polishing, no compression in the flowsheet. The baseline product has about 392 ppm N2 and is not fuel-cell grade. | Product quality claims are limited to an industrial grade. |

### Economics

| Limitation | Consequence for the conclusions |
|---|---|
| No supplier quotation exists for any ammonia cracking catalyst. Prices are derived from metal content plus a non-metal part. Published TEA prices for Ru catalysts are below the Ru metal value and are shown only as a labelled historical case. | H3-c is INCONCLUSIVE. With heat integration, at derived central prices and with the Ni reference at its modelled 594 degC (extrapolated law), three of the four low-temperature catalysts are dearer beyond the 0.006 USD/kg resolution (+0.011 to +0.081 USD/kg); 2.5Ni0.5Ru/CeO2 (+0.005) is within resolution; without heat integration the two NiRu catalysts are slightly cheaper; against sourced Ni design temperatures (736, 760 degC) every low-temperature design is cheaper. |
| Reference CAPEX comes from one paper's itemised table (7.667 MUSD). It is extrapolated more than 30-fold for the power-plant cracker. The independent published range (3.1 to 6.5 MUSD) gives 3.64 to 3.92 USD/kg. | The reference is the highest of the comparable estimates; it works against cracking. The selection criteria were recorded with the choice; that they preceded the comparison cannot be shown. No verdict changes across the independent range. Absolute LCOH has a wide uncertainty (90 % range 3.21 to 4.84 USD/kg in the Sobol sample; 3.25 to 4.88 in the separate Monte Carlo of Section 27 of the technical report). |
| The main benchmark is one regional marker (3.06 USD/kg, NE Asia SMR); a 6.0 USD/kg delivered low-carbon benchmark is the second. No Singapore transaction price exists. | The break-even ammonia price is 320 USD/t against the marker (277 to 371 over the CAPEX range; 379 with favourable non-feed inputs) and 720 USD/t against the 6.0 USD/kg benchmark. Sourced prices (300 to 1052 USD/t) straddle both, so H2-b is INCONCLUSIVE and the threshold is the finding. |
| Grey ammonia at 450 USD/t is not cheap enough against the marker. P(LCOH < 3.06 USD/kg) is 1.4 %, conditional on the assumed triangular input distributions. NPV at 3.06 USD/kg is -17.46 MUSD. | Component H2-E is PARTIALLY SUPPORTED (H2-a SUPPORTED, H2-b INCONCLUSIVE). |
| Supplementary ammonia fuel is counted at 100 % of its lower heating value (optimistic). | The reference LCOH 4.015 USD/kg becomes 4.038 at the flowsheet's own tail-gas ratio (0.9225) and 4.063 at 0.85; the break-even ammonia price 317.9 and 315.5 USD/t. In H1 the same assumption favours cracking: the fired-cracking threshold rises from +5.16 to +5.82 and +6.54 points (computed). No verdict changes. |
| Several inputs (blue ammonia price, hydrogen benchmarks, electricity price) are secondary or derived values. No Singapore gas price, WACC or location factor is sourced. | Absolute figures are for the stated basis only. |
| The CAPEX model does not respond to temperature or reactor volume. | A capital effect of the operating temperature cannot be shown. |

### Carbon accounting

| Limitation | Consequence for the conclusions |
|---|---|
| Under the actual Singapore carbon tax boundary the tax is zero for every route. Upstream emissions are outside the Act and a self-fired plant is far below the 25,000 t threshold. The legislated rate is SGD 45/tCO2e for 2026 and any later year. A rise to SGD 50 to 80 by 2030 is a stated aim, not law. | H2-e is CONTRADICTED under the actual boundary: low-carbon ammonia earns no cost advantage from the tax. |
| The life-cycle carbon price (Mode B) is hypothetical and is not Singapore law. Blue overtakes grey at about 33 SGD/t (range 12 to 605). Green at current prices needs about 305 SGD/t (range 156 to 466). | Mode B results answer a what-if question only. H2-e is INCONCLUSIVE under it. |
| Life-cycle factors for coal ammonia, SMR with capture and methane leakage are low-confidence. Shipping distance (5000 km) is an assumption. N2O is not quantified for the plant. | Intensities are scenario results, not measurements. |
| The browser simulator carbon module is aligned to the stored model for the cases tested. A formal check of the browser carbon-pricing code against the Python carbon-pricing results was not completed. | Carbon cost in the browser is labelled. Read it together with `results/research/carbon_pricing/`. |

### End use

| Limitation | Consequence for the conclusions |
|---|---|
| No sourced turbine efficiency exists for the hydrogen and nitrogen fuel of a fired cracker. The comparison assumes equal efficiency (49.64 %) for all pathways. | H1-a is INCONCLUSIVE. The cost advantage of direct use (7.6 % against fired cracking, 16.5 % against cracking with PSA) depends on this assumption. |
| Thresholds: fired cracking needs +5.16 percentage points of turbine efficiency (range 3.29 to 8.79 over 11 bases) to match direct use. Cracking with PSA needs +12.55 (9.68 to 18.10), above the only sourced upper bound of +7.3 (NETL, pure hydrogen). | The PSA half passes on every basis against a single sourced gain (NETL, H-class cycle simulation with steam-diluted hydrogen, not like for like; an upper bound). The fired-cracking half has no sourced efficiency. |
| Exhaust-heated cracking is 1.3 % cheaper than direct use on the reference basis. The outcome flips with CAPEX (x1.22 removes it), an ammonia price of 300 USD/t and 6000 operating hours or fewer; the margin is not robust. | This is a finding against the essay and H1-c is INCONCLUSIVE. |
| Halim et al. and Abdoos et al. could not be read in full. | The essay figures from them (including the 40 % advantage) are unverified. H1-b is CONTRADICTED only in the sense that the largest computed gap is 16.6 %. |

### Uncertainty quantification

| Limitation | Consequence for the conclusions |
|---|---|
| Sobol sensitivity indices use ranges taken from sources where they exist and stated ranges elsewhere. The ammonia price total-effect index is 0.896 [0.875, 0.917]. | The dominance of the feed price holds inside the sampled ranges. Ranges outside them are not covered. |
| The reconversion cost (cost excluding feed) is driven by CAPEX (index 0.47) and PSA recovery (0.42), not by the ammonia price. | Statements about price dominance must name the quantity they apply to. |
| The Bayesian check of the Takahashi law is a model-form diagnostic on digitised points. It is not a calibration against plant data. | It shows where the law fails. It does not validate it. |

### Simulator

| Limitation | Consequence for the conclusions |
|---|---|
| The site is static. The simulator computes in the browser from stored Aspen and Python results and from code tested against the Python model (parity to about 1e-7 for the ported functions). It does not run Aspen Plus. | Values away from stored cases are browser-model values and are labelled so. The animation shows flow direction only. It is not a transient simulation. |
| The simulator has no membrane model. | Purification route comparisons are made on the research pages, not in the simulator. |
| Against stored Aspen kinetic cases, the browser model is close for the Kum law inside its fitted range and differs more elsewhere. | Each kinetic output shows a fitted-range warning when it is extrapolated. |
| IRR is not computed in the browser. | Only the quantities listed on the page are available. |
| The automated browser check covers four viewport sizes. Visual inspection of every viewport after every change was not done. | Layout defects at less common sizes are possible. See `docs/reproducing.md` for the check. |

### Validation

| Limitation | Consequence for the conclusions |
|---|---|
| There is no independent experimental validation of any kind. | Every result is a model result. Pass counts describe numerical verification, comparison between two models and comparison with published values. They are not experimental validation. |
| Failures are kept: the exchanger duty items, the above-equilibrium items at 40 bar and two Takahashi prediction items. Tolerances were not changed. | Each failing item has a recorded cause. See `docs/validation/research_validation.md`. |
| A pass count from a validation file has no single meaning. | No single percentage is given for validation anywhere in these documents. |

## Ranked next research steps

Ranked by how much each step would reduce the uncertainty of a verdict that is now INCONCLUSIVE or threshold-dependent.

1. **Fuel-specific turbine data** for hydrogen and nitrogen mixtures (a turbine manufacturer statement or a test report). It decides H1-a and H1-c. The thresholds are +5.16 and +4.04 percentage points for the two standalone and exhaust-heated cases.
2. **Supplier quotations for ammonia cracking catalysts** (nickel and ruthenium, per kilogram, with the loading and life). It would replace the metal-content derivation and decide H3-c, which now rests on derived prices.
3. **A cracked-ammonia PSA cycle model with recovery and purity** (for example an adsorption-cycle simulation of the cracked gas). It would replace the recovery input, which controls H4-a, H4-e (threshold 0.765) and H4-d (parity 0.783 Grade D, 0.795 industrial).
4. **Measured kinetics at 10 to 20 bar** for the main catalysts, including hydrogen inhibition and reversibility. It would give laws checked against data inside a stated pressure range and decide H3-b.
5. **A film-coefficient estimate of the exchanger coefficient** at 20 bar for ammonia, hydrogen and nitrogen, or a vendor rating. The break-even U is 7.7 to 11.3 W/(m2 K), inside the 1 bar typical range (5 to 35), so this decides the cost half of H3-d.
6. **A sourced hydrogen benchmark set for Singapore** and a gas price, WACC and location factor, so that the break-even ammonia price rests on more than one benchmark.
7. **Reference CAPEX from equipment-level costing** with sized units, including temperature and volume dependence, replacing the single paper table extrapolated 30-fold.
8. **Full texts of Halim et al., Abdoos et al. and Sayas et al.**, to verify or withdraw the essay figures that depend on them and to obtain Ru-K/CaO kinetics.
9. **A membrane module model** with a sourced module cost and measured mixed-gas selectivity for cracked ammonia, to replace the ideal single-gas figure.
10. **Singapore policy tracking.** If a carbon price covering embodied emissions is legislated, Mode B becomes an actual boundary and H2-e must be recomputed.
11. **Independent experimental data**, for example a small packed-bed test on one catalyst at 20 bar. It would be the first evidence of kind (4).
12. **API and page wiring** of the end-use and life-cycle packages, and a membrane model and IRR in the browser simulator.
