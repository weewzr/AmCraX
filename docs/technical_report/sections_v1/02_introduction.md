<!-- cites: cechetto2023membrane, xu2025review, mehr2026highcapacity, ahmad2025gtcc, richard2024technoeconomic, cho2026nickel, kum2026heatintegrated, hansen2024hysys, farokhi2025costoptimization, bartels2008feasibility -->

# 2 Introduction and motivation

## 2.1 The hydrogen transport and storage problem

Hydrogen is attractive as a carbon-free energy vector, but it is difficult to store and move. Its volumetric energy density is low, and liquefaction or high-pressure compression adds cost and energy losses. One option is to move hydrogen chemically bound in a carrier and release it close to the point of use. Ammonia is the leading candidate. Liquid ammonia holds 121 kg H~2~ per m^3^ and can be stored at 25 degC and 9.9 bar (Cechetto et al., 2023, p. 10776). For pipeline transport over 1610 km, a cost of about 0.194 USD/kg H~2~ for ammonia has been reported, against 0.51-3.22 USD/kg H~2~ for gaseous hydrogen (Bartels, 2008, as cited in Xu et al., 2025).
<!-- data: research/notes/cechetto2023membrane.md (Table 1, p. 2); research/notes/xu2025review.md ("Other property data quoted") -->

The hydrogen must then be released by endothermic catalytic decomposition ("cracking") at several hundred degC: 30.6 kJ/mol H~2~ against 0.907 kJ/mol H~2~ for regasifying liquid hydrogen (Cechetto et al., 2023, p. 10777). Cracking is also less mature than the ammonia chain: technology readiness levels of 7 for fired tubular crackers, 4-5 for membrane reactors (Richard et al., 2024) and 4-6 overall (Ahmad et al., 2025), with vendor single-train capacities of 1000-1200 t/d NH~3~ (Mehr et al., 2026, p. 4203). The efficiency, recovery and cost of cracking therefore decide whether ammonia is a competitive carrier.
<!-- data: research/notes/cechetto2023membrane.md (p. 3); research/notes/richard2024technoeconomic.md (TRL, uncertainty-analysis paragraph); research/notes/ahmad2025gtcc.md (p. 7); research/notes/mehr2026highcapacity.md (p. 7 = journal p. 4203) -->

## 2.2 What AmCraX is

AmCraX (Ammonia Cracking Simulation and Optimisation Platform) is a process-engineering platform for a complete ammonia-to-hydrogen plant. It has four layers:

1. **Aspen Plus V15 flowsheet.** The rigorous reference model has pump, vaporiser, feed/effluent heat exchanger, fired heater, an RGibbs equilibrium cracker, cooler, a hydrogen separation block, and a tail-gas burner with flue-gas heat recovery. The model is built from a generated input file and run through the Aspen Plus COM interface.
2. **Independent Python models.** These cover thermochemistry and equilibrium, a Python mirror of the flowsheet, pinch analysis, kinetics and reactor models, economics, carbon intensity and separation. They cross-check the Aspen results with independent data and code.
3. **FastAPI back end.** It runs cases, queues Aspen jobs in an isolated worker process, and serves results with a provenance label (Aspen Plus V15, Python model, literature, assumption or demo).
4. **React Flow dashboard.** It shows the flowsheet, stream and block results, and the sensitivity and optimisation studies in a browser.

The baseline cracks 100 kmol/h of refrigerated liquid ammonia at 600 degC and 20 bar with an assumed hydrogen recovery of 0.85 (an engineering assumption above published PSA values; Section 6).

## 2.3 Scope, claims and limits

Sections 3-5 give the background (carrier, fundamentals, literature). Sections 6-13 describe the process design and its Aspen Plus and Python implementation. Sections 14-19 report validation, sensitivity, efficiency, techno-economic, optimisation and environmental results. Section 20 lists limitations and Section 21 concludes.

The claims are limited on purpose:

* The cracker is an **equilibrium** (RGibbs) model. It shows the thermodynamic limit, not a reactor design. Kinetic and reactor models are treated separately and are labelled as such.
* The hydrogen separation block is a **reduced-order splitter** with a fixed recovery. It is not a designed pressure-swing adsorption (PSA) unit.
* The baseline product (99.961 mol% H~2~, 392 ppm N~2~) is **not fuel-cell grade**, and NH~3~ polishing is not modelled.
* Costs are **preliminary estimates**. The carbon-intensity accounting is **not a full life-cycle assessment**.
* Literature values are used only as inputs or benchmarks. They are always cited and are never presented as AmCraX results.

The engineering questions are the same as in comparable simulation studies (Cho et al., 2026; Farokhi et al., 2025; Hansen et al., 2024; Kum et al., 2026): how much ammonia must be burned to heat the cracker, how much heat can be recovered, and what this means for hydrogen yield and cost.
<!-- data: results/simulations/baseline.json inputs (600 degC, 20 bar, 100 kmol/h, psa_h2_recovery 0.85), streams.H2PROD.mole_frac (H2 0.999608, N2 0.000392) -->
