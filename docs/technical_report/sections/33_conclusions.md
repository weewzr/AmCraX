<!-- cites: cho2026nickel -->

# 33 Conclusions and future research

## 33.1 Conclusions on the AmCraX model

1. **A reproducible Aspen model.** The Aspen Plus V15 flowsheet is generated from a typed case object and solved without manual GUI work. All 279 Aspen runs behind this report converged, every stored case names the input file that reproduces it, and the COM-driven temperature sweep agrees with Aspen's own Sensitivity block to 4.8 × 10^-10^ (Sections 6, 12 and 17).
2. **The baseline is heat-limited, not conversion-limited.** At 600 °C and 20 bar the equilibrium conversion is 0.9808 and the plant delivers 251.6 kg/h of H~2~. The cracker duty of 1480.0 kW dominates the 2293.1 kW of external heating. The feed/effluent exchanger recovers 612.2 kW and lowers the LCOH by 0.214 USD/kg (5.2 %) before its own cost is counted (Sections 5, 10 and 19).
3. **Tail gas alone cannot heat the cracker.** On a first-law basis tail-gas firing leaves a deficit of 772.9 kW. The pinch analysis shows that the limit is the temperature level: only 977.5 kW of the flue heat lies above 620 °C, against 1480.0 kW of reaction heat at 600 °C (Section 18).
4. **Temperature and pressure matter little above 550 °C; recovery matters a lot.** Between 550 and 800 °C the specific heat demand stays between 9.10 and 9.21 kWh/kg H~2~, and the named temperature and pressure scenarios move the LCOH by less than 0.4 %, because unconverted NH~3~ returns as burner heat. A PSA recovery between 0.70 and 0.95 moves the specific heat demand from 11.07 to 8.16 kWh/kg H~2~ (Sections 17 and 20.5).
5. **Ammonia sets the cost and the carbon intensity.** The NH~3~ feed is 78 % of the preliminary 3.919 USD/kg LCOH, the LCOH rises by 7.35 × 10^-3^ USD/kg per USD/t of ammonia, and the ammonia route, not the heating option, sets the carbon intensity: 18.56 kg CO~2~e/kg H~2~ for grey NH~3~ with natural gas against 0.41 for green NH~3~ with tail-gas firing (Sections 19 and 21).
6. **The baseline product is not fuel-cell grade.** Its purity of 99.961 mol% follows from assumed split fractions and is below the ISO 14687:2019 grade D limits; NH~3~ polishing is required and not modelled (Section 11).
7. **Optimisation adds little within this model.** The objectives largely do not conflict, the optima mostly sit on variable bounds, and the four-variable minimum LCOH is 2.7 % below the Python baseline only because recovery and exchanger approach are not costed. The ten candidates re-solved in Aspen confirm the Python surrogate within 1.15 % on the primary metrics (Section 20).
8. **The validation is useful because it can fail.** Of 137 items, 105 pass, 22 fail and 10 are informational. The failures are documented: 20 record a feed-section model-form difference that remains unresolved, and 2 record that published kinetic curves are not reproduced. The equilibrium and reaction-section results agree like for like with an independent implementation, and the validation found and removed one automation defect (Section 16).

Taken together, AmCraX is a transparent, re-runnable screening model of an ammonia cracker with an honest record of what is checked and what is assumed. It is suited to comparing design options and to teaching, not to sizing equipment or predicting plant performance (Section 32).
<!-- data: results/sensitivity/aspen_native_STEMP_baseline.csv vs aspen_temperature.csv; results/simulations/baseline.json kpis; economics_baseline.json and economics_baseline_no_hi.json (4.132623 - 3.918842 = 0.2138; /4.1326 = 0.0517); heat_integration_baseline.json; results/sensitivity/aspen_temperature.csv (9.102-9.209 kWh/kg from 550 degC), aspen_psa_recovery.csv (11.068, 8.155); scenario_comparison.json; lcoh_vs_ammonia_price_baseline.csv slope; environmental_baseline.json; single_objective.json min_lcoh delta_rel -0.0267; aspen_verification.json; validation_matrix.json summary -->

## 33.2 Conclusions on the four hypotheses

The verdicts below are read from the evidence matrix at build time (Section 31).

1. **H1 End-use suitability:** {{VERDICT:H1}}. {{VERDICT_SUMMARY:H1}} Row outcomes: {{ROW_OUTCOMES:H1}}.
2. **H2 Feedstock:** {{VERDICT:H2}}. {{VERDICT_SUMMARY:H2}} Row outcomes: {{ROW_OUTCOMES:H2}}.
3. **H3 Catalyst and heat integration:** {{VERDICT:H3}}. {{VERDICT_SUMMARY:H3}} Row outcomes: {{ROW_OUTCOMES:H3}}.
4. **H4 Purification:** {{VERDICT:H4}}. {{VERDICT_SUMMARY:H4}} Row outcomes: {{ROW_OUTCOMES:H4}}.

Three findings carry most of the weight. First, catalyst kinetics could be put into Aspen Plus RPlug reactors exactly for three published laws and approximately for two, and they agree with an independent Python reactor within 7 × 10^-4^ in conversion for the exact laws (Section 25). Second, once each catalyst is given its own cost-optimal temperature and mass, the catalyst choice moves the fired duty by less than 5 % and the LCOH by about 0.3 %, while heat integration saves 469-604 kW for every catalyst; heat integration therefore matters more than the catalyst in this flowsheet, and the two partly substitute for each other (Section 26). Third, several quantitative claims carried over from the literature into the essay are not reproduced on AmCraX boundaries, among them the 40 % cost advantage of direct ammonia power and the statement that a ruthenium cracker needs no supplementary fuel (Section 31.7).
<!-- data: results/research/validation/aspen_kinetic.json (native laws |dX| <= 7e-4); results/research/catalyst_comparison/catalyst_comparison.json findings.cost_optimal_python (fired duty 495-518 kW, LCOH 3.6644-3.6750); results/research/aspen_kinetic/catalyst_comparison.json (no-HI minus HI external heating 469-604 kW) -->

## 33.3 Future research

In order of the effect on the conclusions:

1. **Make purity a design result.** Add an NH~3~ polishing step (temperature-swing adsorption) and replace the PSA splitter by a model with a purity-recovery trade-off, keeping the published points as bounds; obtain PSA recovery data at 99.97 % purity and measured Pd-membrane H~2~/N~2~ selectivity, which decide H4.
2. **Resolve the feed-section difference.** Obtain NH~3~-H~2~O vapour-liquid data or a reference mixture model to decide the dew point, and run the Python feed section with an equation of state matched to Aspen, so that the `FS-<case>` items test physics rather than model form.
3. **Kinetics at process pressure.** Fit or validate rate laws on data measured near 20 bar, obtain the Ni/Al~2~O~3~ and Ru-K/CaO laws used by Cho et al. (2026), implement the microkinetic laws exactly through a user kinetics subroutine, and replace the isothermal RPlug by a fired tubular reactor with a furnace heat-flux profile.
4. **Build an equipment-based cost estimate.** Size the exchanger, PSA, compressors and catalyst bed, apply installed-cost factors in one cost year, and add NO~x~ treatment, polishing and compression, so that the optimiser sees equipment size.
5. **Close the heat-supply loop.** Design a heat-exchanger network and a fired heater with its efficiency, so that the efficiency KPI no longer depends on an ideal heater.
6. **Strengthen the environmental and end-use evidence** with measured or kinetically modelled burner NO~x~ and N~2~O for NH~3~-rich tail gas and NH~3~ turbines, sourced sea distances and boil-off, and primary-source checks of the Singapore plant study quoted in the essay.
7. **Explain the remaining PENG-ROB gap** by comparing Aspen's pure-component constants and α-function treatment term by term with the Python implementation.
8. **Harden the platform.** Capture the Aspen process id from the COM server, bound and persist the job queue, and add authentication before any shared deployment.
