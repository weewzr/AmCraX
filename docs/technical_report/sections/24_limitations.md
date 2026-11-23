<!-- cites: iso2019hydrogen, takahashi2016kinetic, kum2026heatintegrated -->

# 24 Limitations

This section collects the limitations stated where they apply in Sections 5 to 23. They bound what the results can be used for. The repository keeps the same list with suggested remedies in `docs/known_limitations.md`.

## 24.1 What AmCraX is not

AmCraX is not a validated digital twin of a plant. No plant or pilot data were available, so no result has been compared with measured operation. The models are steady state: start-up, shut-down, turn-down and dynamics are outside the scope. Everything below should be read with that in mind.

## 24.2 Process model

* **Equilibrium reactor.** The Aspen cracker is an RGibbs block (Section 9). Its conversion, 0.9808 at the baseline, is the thermodynamic ceiling at the given temperature and pressure; it carries no catalyst, residence time, heat-flux limit, pressure drop from geometry or deactivation. The kinetic plug-flow reactor of Section 14 is a separate Python model, and none of its results enter the flowsheet, the costs or the optimisation.
* **Reduced-order PSA.** The PSA is a component splitter (Section 11). Its H~2~ recovery of 0.85 is an engineering assumption above the 0.71-0.81 range reported in the literature, and its N~2~ slip of 0.001 is also assumed. Product flow, tail-gas fuel and the LCOH all depend on these two numbers; the recovery sensitivity of Section 17.5 shows how strongly.
* **Purity is an input consequence.** The baseline purity of 99.961 mol% H~2~ (392 ppm N~2~) follows from the assumed split fractions; it is not a prediction. It is below the 99.97 mol% and 300 ppm limits of ISO 14687:2019 grade D (ISO, 2019), so the baseline product is not fuel-cell grade. The purity-driven scenario reaches 99.979 mol% only because its split fractions were set to do so.
* **No NH~3~ polishing.** The cracked gas holds 9678 ppm NH~3~; reaching the 0.1 ppm limit needs a polishing step that is not modelled, so its energy, cost and NH~3~ recovery are missing from every balance. The Sep block meets the limit only because its NH~3~ fraction to product is set to zero.
* **No compression, fixed pressure drops.** The flowsheet contains no gas compressor, and the pressure drops are fixed specifications, not hydraulic results (Section 5.4).
* **Burner model.** The burner assumes complete combustion. NO~x~, N~2~O and NH~3~ slip are not predicted, and the flame temperature is the complete-combustion value, about 2.3 K above an equilibrium calculation with dissociation (Section 10.4). The burner heat is not physically connected to the cracker in Aspen; it is a first-law credit in the KPIs.
* **First-law efficiency.** The LHV efficiency and the net fuel heat deficit are upper-bound metrics (Eq. (18.1)): external heat is counted one-to-one against fuel LHV, as from a 100 %-efficient fired heater, and flue heat below reactor temperature is credited. With temperature levels respected the pinch analysis gives a heat import of 752.6 kW against the KPI's 772.9 kW (Section 18.3); furnace losses, PSA and compression power and cooling utilities are not counted.
* **Feed section.** The vaporiser outlet follows the assumed "dew point + 10 K" rule, and the dew point of the 0.2 mol% water mixture depends on the NH~3~-H~2~O model (65.9 °C in Aspen PENG-ROB, 60.1 °C with an ideal liquid, 50.9 °C for pure NH~3~; Section 8.3). No reference mixture model or measurement was available to decide between them.

## 24.3 Thermodynamics and kinetics

* **Unexplained equation-of-state gap.** Aspen PENG-ROB and the Python Peng-Robinson model differ by up to 0.185 percentage points in equilibrium conversion, at 250 °C and 40 bar. The Boston-Mathias α-function explains 0.04 points; about 0.18 points remain unexplained. A sensitivity study makes the binary interaction parameters an unlikely cause, but the actual cause has not been identified (Section 13.4).
* **Feed-section model form.** The 20 failing `FS-<case>` items record that the two flowsheet models use different property models in the feed section (Section 16.4). The difference runs in both directions and is not resolved; individual feed-section and exchanger duties of the Python model therefore differ from Aspen by 3.5-11.8 % in the worst KPI per case.
* **Kinetics extrapolated.** The microkinetic models were fitted at 1 atm (Takahashi & Fujitani, 2016) and the Temkin-Pyzhev law at 350-450 °C and up to 10 bar (Kum et al., 2026); every result at 20 bar is an extrapolation. The contact time was inferred from one anchor point per catalyst, two of four kinetic validation items fail, and the equilibrium-approach factor and the reading of the Kum equilibrium constant are AmCraX assumptions. Diffusion, external transfer, radial gradients and deactivation are neglected, so the catalyst masses are lower bounds (Section 14.6).

## 24.4 Economics and environment

* **Preliminary costs.** The LCOH of 3.919 USD/kg H~2~ is an order-of-magnitude estimate. The CAPEX is a plant-level correlation in hydrogen capacity alone, so it does not see exchanger area, PSA size, catalyst volume or compressors; costs are in mixed 2024-2025 USD without escalation. NO~x~ treatment, NH~3~ polishing, H~2~ compression and storage, installed-cost, contingency and owner's-cost factors, land, taxes and working capital are omitted, and imported heat is priced at 100 % of the NH~3~ LHV. These omissions explain why the result lies below the 5.1-6.4 USD/kg published at comparable ammonia prices; 3.919 USD/kg should be read as a lower bound for the stated scope (Section 19.4).
* **Simplified carbon accounting.** The carbon intensity multiplies activity data by emission factors. It is not a life-cycle assessment: it has no inventory analysis, allocation or review, excludes construction, catalyst manufacture, N~2~O, NO~x~, NH~3~ slip, H~2~ leakage and the upstream natural-gas chain, and three of its factors were confirmed only through secondary listings (Section 21).
* **Optimisation on a surrogate.** The optima come from the Python process model. Only the ten candidates re-solved in Aspen are confirmed there, and the recovery and exchanger-approach optima sit on their bounds because equipment size is not costed (Section 20.6). No kinetic-feasibility constraint is applied.

## 24.5 Validation coverage

The PSA and membrane models, the costs, the carbon accounting, the kinetics at 20 bar and the NH~3~-H~2~O dew point have no validation item that can pass or fail. Balance closures of about 10^-9^ show that values were extracted and booked consistently; they do not test the physics, because Aspen closes its own balances by construction. The test suites (391 Python tests passing, one opt-in live-Aspen test skipped by default, 96 frontend unit tests) show that the code behaves as specified, not that the models are right.

## 24.6 Software and platform

* **Aspen access.** Live simulation needs Windows, pywin32 and a licensed Aspen Plus V15; another version needs another COM ProgID. One Aspen instance runs at a time under a machine-wide lock, so jobs are strictly serial and a waiting job counts towards its time-out (Section 12.5).
* **Orphan clean-up.** The process id of an Aspen instance is inferred from a before-and-after list of processes. If another Aspen instance starts at the same moment, the wrong process could be recorded; a hung engine is stopped only by killing the worker and cleaning up on the next run.
* **Job queue.** The Aspen job queue is held in memory and is unbounded: submissions are not limited in number, and a restart of the API abandons queued and running jobs.
* **Deployment.** The local platform uses development servers without authentication or HTTPS and must not be exposed to a network.
* **Static website.** The public site never runs Aspen Plus and never contacts an API. It is only as current as the last export of the stored results, and the only calculation it performs is the ideal-gas equilibrium of a pure NH~3~ feed (Section 23).
<!-- data: docs/known_limitations.md sections 1, 2, 4-7, 10; results/validation/validation_matrix.json items FS-* (max 0.1180, min 0.0354), EQ-PR, EQ-KIJ-SENS, KIN-*; results/simulations/separation_baseline.json ammonia_slip nh3_cracked_gas_ppm 9677.98; heat_integration_baseline.json configurations (c) 752.628 -->
