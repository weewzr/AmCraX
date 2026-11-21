<!-- cites: -->

# 21 Conclusion

AmCraX models a complete ammonia-to-hydrogen plant twice: as a scripted Aspen Plus V15 flowsheet and as independent Python models. Both are driven from the same case definition, and every reported value carries its provenance.

At the baseline (600 degC, 20 bar, 100 kmol/h feed) the **Aspen Plus V15 simulation** gives an NH~3~ conversion of 0.9808 and 251.6 kg/h H~2~ at 99.961 mol% (392 ppm N~2~), with balances closed to about 10^−9^. The product is not fuel-cell grade, and NH~3~ polishing is not modelled. The cracker duty (1480.0 kW) dominates the 2293.1 kW external heat demand. The feed/effluent exchanger recovers 612.2 kW and raises the LHV efficiency from 0.824 to 0.877. Tail-gas firing covers about two-thirds of the demand and leaves a 772.9 kW deficit. Pinch analysis shows that this deficit is a temperature-level problem: reaction heat at 600 degC cannot come from the low-temperature part of the flue gas.

Above about 550 degC, temperature and pressure change the plant KPIs only slightly, because unconverted NH~3~ returns as burner heat. PSA recovery and heat integration are the main levers. The preliminary LCOH is 3.925 USD/kg H~2~ at 450 USD/t NH~3~, and the NH~3~ feed is 78 % of it. This is a lower bound for the stated scope, not a cost estimate. The carbon intensity is set by the NH~3~ origin: 18.56 kg CO~2~e/kg H~2~ for grey NH~3~ with natural-gas heating against 0.41 for green NH~3~ with self-firing (simplified accounting, not an LCA).

The optimisation on the Python model finds flat optima that are largely set by the variable bounds. The minimum LCOH is 3.810 USD/kg. All ten candidates re-solved in Aspen converged, and their LCOH agrees with the Python value within 0.25 % (Section 18.4).

The validation matrix holds 130 items: 103 pass, 22 fail and 5 are informational. Both root causes of the failures are documented and none was relaxed. The validation also found and removed one automation defect. The main limitations are the equilibrium reactor, the reduced-order PSA, the plant-level cost correlation and the extrapolated kinetics (Section 20).

<!-- data: results/simulations/baseline.json kpis, balances; baseline_no_hi.json kpis.lhv_efficiency 0.8244; economics_baseline.json lcoh 3.925, feed share; environmental_baseline.json comparison rows (18.56, 0.41); results/optimisation/single_objective.json min_lcoh 3.810; results/validation/validation_matrix.json summary -->
