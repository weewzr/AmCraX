<!-- cites: -->

# 1 Executive summary

**What was built.** AmCraX is a process-engineering platform for an ammonia-cracking plant that produces hydrogen. It has four parts: an Aspen Plus V15 flowsheet generated from a typed case definition and run through COM; independent Python models (thermochemistry and equilibrium, a flowsheet mirror, pinch analysis, kinetics and plug-flow reactor, economics, carbon intensity and separation); a FastAPI back end that runs Aspen in an isolated worker process; and a React Flow dashboard. Every value carries a provenance label.

**Aspen evidence.** The Aspen evidence comprises the baseline, the variant without heat integration, eight named scenarios, the optimisation candidates re-solved in Aspen, 91 sensitivity runs and a 168-point equilibrium grid (PENG-ROB and IDEAL). All runs converged, with balance closures of about 10^−9^. Sixteen real GUI screenshots document the model.

Table: **Table 1.1.** Headline results of the baseline (600 degC, 20 bar, 100 kmol/h refrigerated NH~3~, PSA H~2~ recovery 0.85). *Source: as labelled per row.*

| Quantity | Value | Provenance |
|---|---|---|
| NH~3~ conversion | 0.9808 | Aspen Plus V15 simulation |
| H~2~ product | 251.6 kg/h at 99.961 mol% (392 ppm N~2~) | Aspen Plus V15 simulation |
| External heat demand / FEHE recovery / net deficit | 2293.1 / 612.2 / 772.9 kW | Aspen Plus V15 simulation |
| LHV efficiency with / without FEHE | 0.877 / 0.824 | Aspen Plus V15 simulation (KPI definition, Eq. 16.1) |
| LCOH at 450 USD/t NH~3~ | 3.925 USD/kg H~2~ (preliminary) | independent Python calculation on Aspen results |
| Carbon intensity, grey NH~3~ + natural gas / green NH~3~ + self-firing | 18.56 / 0.41 kg CO~2~e/kg H~2~ | independent Python calculation (not an LCA) |
| Minimum LCOH, four variables | 3.810 USD/kg H~2~ | independent Python calculation (optimisation) |
| Validation matrix | 130 items: 103 pass, 22 fail, 0 not run, 5 informational | results/validation/validation_matrix.json |

<!-- data: results/simulations/baseline.json kpis (nh3_conversion 0.98081, h2_product_kg_h 251.588, h2_purity_mole_frac 0.999608, total_external_heating_kW 2293.12, recovered_heat_kW 612.21, net_fuel_heat_deficit_kW 772.87, lhv_efficiency 0.8772); baseline_no_hi.json kpis.lhv_efficiency 0.8244; economics_baseline.json lcoh_USD_per_kg 3.9253; environmental_baseline.json comparison rows 18.5596, 0.4072; results/optimisation/single_objective.json min_lcoh 3.810; results/validation/validation_matrix.json summary -->

**Main findings.** Above about 550 degC, temperature and pressure change the efficiency and the LCOH only slightly, because unconverted NH~3~ is burned for heat. Heat integration lowers the LCOH by about 5 %. PSA recovery is the strongest process lever. The NH~3~ price is the largest cost driver (78 % of the LCOH). The baseline product does not meet the ISO 14687 fuel-cell limits of 99.97 % H~2~ and 300 ppm N~2~, so it must not be called fuel-cell grade. The purity-driven case is the Aspen scenario `scn_fuel_cell_grade` (99.979 mol%, +1.2 % LCOH). NH~3~ polishing to 0.1 ppm is required but not modelled. The optimisation objectives hardly conflict in this model. Ten optimisation candidates, at exactly the reported optima, were re-solved in Aspen. All converged and all pass the stated criterion: primary metrics within 1.24 % and LCOH within 0.25 % (tolerance 2 %; Section 18.4).

**Validation.** The 22 failures have two documented causes. Twenty are flowsheet cross-checks that fail because the Python feed-section enthalpy model differs from Aspen PENG-ROB; the primary quantities of the same cases all pass. Two are kinetic items in which published figure data are not reproduced within the 0.05 tolerance. The validation also exposed an automation defect, a stale value read during an asynchronous run, which was fixed.

**Main limitations.** The reactor is an equilibrium model and the PSA is a reduced-order splitter, whose 0.85 recovery is an assumption above the 0.71-0.81 literature range. The costs are order-of-magnitude estimates, the carbon accounting is not an LCA, and the kinetics are extrapolated to 20 bar (Section 20).
