<!-- cites: -->

# 20 Limitations and future work

## 20.1 Limitations by layer

Table: **Table 20.1.** Limitations of AmCraX and their consequences. *Source: docs/known_limitations.md, results/validation/validation_matrix.json, docs/validation/discrepancy_analysis.md and Sections 6-19.*

| Layer | Limitation | Consequence |
|---|---|---|
| Aspen flowsheet | Fixed pressure drops; no compressor; no NH~3~ polishing; burner heat not coupled to the reactor | Hydraulics, compression and polishing energy missing; heat coupling is first-law only |
| Property method | PENG-ROB with databank k~ij~; refrigerated-liquid NH~3~ not validated (dew point 5.81 K above the Python route) | Vaporiser duty uncertain by a few per cent; 0.18 pp of the EOS effect at 250 degC/40 bar unexplained |
| Reactor model | RGibbs equilibrium, steady state; no catalyst, deactivation or heat-flux limit | Conversion is an upper bound; bed heat-transfer limits (Section 10.5) are absent |
| Purification | Splitter with assumed 0.85 recovery (literature 0.71-0.81) and 0.001 N~2~ slip | Product flow and purity are assumptions; baseline (392 ppm N~2~) not fuel-cell grade |
| Heat integration | Pinch targets, no designed network; assumed U | Area and network cost order-of-magnitude only |
| Kinetics | Fitted at 1 atm or ≤ 10 bar, used at 20 bar; W/F from one anchor point; (1 - Q/K) factor assumed | Catalyst masses are lower bounds; two kinetic items fail |
| Economics | Plant-level CAPEX correlation; mixed 2024-2025 USD; imported heat at 100 % LHV; the whole feed including 0.2 mol% water priced as NH~3~ (6.770 kg/kg H~2~), whereas the environmental module counts NH~3~ only (6.756 kg/kg) | LCOH is preliminary and a lower bound for the scope; the water pricing overstates it by about 0.006 USD/kg (0.16 %), reported, not changed |
| Environmental accounting | Factors times activity data, not an LCA; NO~x~, N~2~O, NH~3~ slip, construction excluded | Carbon intensities indicative; self-firing needs burner emission data |
| Optimisation | Python surrogate; CAPEX blind to PSA size, exchanger area and compressors; no kinetic constraint | Recovery and approach optima sit on bounds; low-temperature optima unchecked kinetically |
| Validation coverage | 22 of 130 items fail (20 flowsheet cross-checks: feed-section enthalpy model; 2 kinetic-figure reproductions); PSA, membrane, costs and carbon intensity unvalidated; no plant data | Python model is a cross-check, not an Aspen replacement; unvalidated layers carry assumption-level confidence |
| Software / platform | Windows, COM and licensed Aspen Plus V15; one Aspen instance; no authentication; in-memory job queue | Not deployable as a shared service without hardening |
| Software (documented, not fixed) | Tail-gas combustion KPI uses the magnitude of the flue-gas cooler duty | Where flue gas must be heated to stack temperature, that heat would be credited instead of charged |
| Software (documented, not fixed) | FEHE feasibility guard uses a fixed 120 degC threshold | Too low above about 65 bar (outside the studied 5-40 bar) |
| Software (documented, not fixed) | Orphan-process detection infers the Aspen process id from a before/after process list | An Aspen process started elsewhere at the same moment could be mis-attributed |

## 20.2 Future work

In order of priority:

1. Add NH~3~ polishing (TSA) and a designed PSA or coupled purity-recovery model, so that purity becomes a design result.
2. Add and cost cracked-gas and product compression.
3. Replace RGibbs by a kinetic RPlug reactor with a heat-flux profile once 20 bar rate data exist.
4. Build an equipment-based cost estimate in one cost year and correct the feed-water pricing.
5. Base the Python feed-section properties on PENG-ROB, removing the cause of the 20 flowsheet failures.
6. Perform a full LCA including burner NO~x~/N~2~O, and fix the three documented software items.

## 20.3 What AmCraX does not claim

AmCraX is not a validated digital twin; no plant data were used. It is steady state only. It contains no designed PSA or heat-exchanger network, no detailed cost estimate and no LCA, and its 20 bar kinetic results are extrapolations.

<!-- data: results/validation/validation_matrix.json summary (130 items, 103 pass, 22 fail, 5 informational, failure_root_causes); results/simulations/economics_baseline.json kg_nh3_feed_per_kg_h2 6.770; results/simulations/environmental_baseline.json kg_nh3_per_kg_h2 6.756; (6.770 - 6.756) x 0.450 USD/kg = 0.0063 USD/kg = 0.16 % of 3.925 -->
