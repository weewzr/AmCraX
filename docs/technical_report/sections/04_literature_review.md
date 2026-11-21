<!-- cites: su2023review, maccarrone2025comprehensive, xu2025review, cechetto2023membrane, takahashi2016kinetic, purcel2024stability, kum2026heatintegrated, cho2026nickel, richard2024technoeconomic, mehr2026highcapacity, chopra2026decentralized, ahmad2025gtcc, hansen2024hysys, farokhi2025costoptimization, realpe2024repurposing, yanez2020psa, jiang2021hollow, dicarlo2014ammonia -->

# 4 Literature review

The AmCraX library holds 14 papers: four reviews, two experimental catalyst studies and eight process-simulation or techno-economic studies, each abstracted into a note with page references, parameters and the inconsistencies found on reading (`research/notes/`). All values in this section are **published literature**, not AmCraX results. Table 4.1 summarises the papers and their use.

## 4.1 Catalysts and kinetics

The three catalyst reviews (Su et al., 2023; Maccarrone et al., 2025; Xu et al., 2025) agree that Ru is the most active metal, Ni the practical non-noble choice, and that Ni sinters at high temperature. Long-term data are scarce: the 800 h Ni test of Purcel et al. (2025, p. 4) exceeds every test in their comparison table (5-180 h). The reviews are secondary sources with errors: Maccarrone et al. (2025, pp. 3-4) print equilibrium-constant correlations with typographical errors (one gives a negative *K*~p~), Xu et al. (2025, p. 11) tabulate rates incompatible with the stated conversions, and Su et al. (2023, p. 8114) label a power law as Temkin-Pyzhev. AmCraX therefore takes rate parameters only from primary sources.

Only two papers give rate laws that can be reproduced from the printed text: the four-step microkinetic model of Takahashi and Fujitani (2016, p. 25) for Ni/MgO and Ru/MgO at 1 atm, and the reversible Temkin-Pyzhev law of Kum et al. (2026, pp. 5, 9) for Ru/Al~2~O~3~, fitted to 36 points of Di Carlo et al. (2014) at 1-10 bar with a mean absolute percentage error of 0.81 %. Both are implemented (Section 14). The rate laws of Cho et al. (2026) and Richard et al. (2024) are only in unavailable supplementary material, Chopra et al. (2026) print a malformed parameter table, and Mehr et al. (2026) give no pre-exponential factor. No paper provides kinetics measured at 20 bar, so every kinetic prediction at the AmCraX baseline pressure is an extrapolation.

## 4.2 Reactors and heat integration

Industrial designs use fired multi-tubular packed beds: 336 tubes of 3 m reaching 96.3 % conversion at 79.25 kJ/mol NH~3~ with more than 2 bar pressure drop (Kum et al., 2026, pp. 5, 10, 12), or 96 tubes of 5 m with a Ni catalyst (Mehr et al., 2026, p. 4201). Pd-membrane reactors reach more than 99 % conversion with 90-97.5 % hydrogen recovery at 400-500 °C and 4-7 bar, with the membranes limited to 500 °C (Cechetto et al., 2023, pp. 10784, 10789), and a thermal efficiency of 85 % against 68.5 % for a fired reactor, but need at least 5-6 bar (Richard et al., 2024, pp. 581-584).

Heat integration is the main efficiency lever. Feed preheat with product heat raised the yield from 0.131 to 0.141 kg H~2~/kg NH~3~ (Hansen et al., 2024, p. 83), and additional recovery lowered the LCOH from 5.5 to 5.1 USD/kg for a purchased-equipment cost rising only from 1702 to 1850 kUSD (Farokhi et al., 2025, p. 52). A pinch-based network recovers 94.56 % of the waste-heat potential against 18.22 % in a conventional plant and cuts the net energy demand by 37.1 % (Kum et al., 2026, pp. 13, 15). Feed/effluent integration plus a pre-cracker raised the process efficiency from 65.7 to 75.3 % (Realpe et al., 2024, as cited in Xu et al., 2025, p. 30). Whether tail gas alone can heat the cracker is disputed: yes at full load in Mehr et al. (2026, p. 4207), generally not in Cechetto et al. (2023, p. 10780). AmCraX follows this pattern with a feed/effluent exchanger, a tail-gas burner and a pinch analysis (Sections 10 and 18).

## 4.3 Purification

PSA is "the most well developed technology" for this separation (Cechetto et al., 2023, p. 10778), yet every flowsheet study treats it as a black box. Reported recoveries are 75.6 % at 99.11 mol% after a temperature-swing adsorber that removes NH~3~ below 0.1 ppm (Cho et al., 2026, p. 6, citing Yáñez et al., 2020), 80 % (Kum et al., 2026, p. 3), and 71 % at 99 mol% and 79 % in two earlier studies quoted by Hansen et al. (2024, p. 80). Mehr et al. (2026, p. 4201) give about 81 % at 99.96 mol% but also 25 % at 99.81 mol% in their validation (p. 4203), so AmCraX does not use their point. The published range of 0.71-0.81 is below the 0.85 assumed for the AmCraX baseline, which is why recovery is a sensitivity variable (Section 17). Pd-Ag membranes reached more than 99.999 % purity with less than 0.01 ppm NH~3~ (Jiang et al., 2021, as cited in Cechetto et al., 2023, p. 10791); the membrane option is assessed in Section 11.
<!-- data: research/notes/cho2026nickel.md (PSA 75.6 %, 99.11 mol%); kum2026heatintegrated.md (80 %, p. 3); hansen2024hysys.md (Cha et al. 2021 71 % at 99 mol%, Lee et al. 2023 79 %, PDF p. 2 = proceedings p. 80); mehr2026highcapacity.md (p. 5 = 4201, validation p. 7); backend/amcrax/data/separation.yaml (Mehr point not used) -->

## 4.4 Simulation practice

Aspen Plus is used by Cho et al. (2026, V14), Richard et al. (2024, v11), Ahmad et al. (2025, V14), Chopra et al. (2026) and Kum et al. (2026, V14 coupled with gPROMS); Aspen HYSYS by Hansen et al. (2024), Farokhi et al. (2025) and Mehr et al. (2026). Peng-Robinson is the usual property method (Section 8). A Gibbs reactor represents the cracker when catalyst data are missing (Hansen et al., 2024, p. 81; Farokhi et al., 2025, p. 49), RPlug is used with kinetics (Cho et al., 2026; Richard et al., 2024), and burners are usually Gibbs reactors. AmCraX uses RGibbs, PENG-ROB and an RStoic burner (Sections 6 to 9).

## 4.5 Techno-economics, environment and technology status

Published LCOH values differ in scale, ammonia price, discount rate and scope: 5.293 (Ru) and 5.439 USD/kg (Ni) at 450 USD/t NH~3~ and an 8.5 % discount rate (Cho et al., 2026, p. 13); 6.44 USD/kg as the most probable value of a Monte Carlo analysis (Kum et al., 2026, p. 16); 5.1 and 4.45 EUR/kg for fired and membrane reactors (Richard et al., 2024, pp. 582-584); 8.36 EUR/kg with a cost breakdown that does not sum to the total (Mehr et al., 2026, p. 4210); and 6.84-17.12 USD/kg for 400 kg/d delivered at 350 bar (Chopra et al., 2026, p. 6). Ammonia is the largest cost item in all of them (Section 19). Only Chopra et al. (2026, p. 8) perform a life-cycle assessment (17.91 kg CO~2~-eq/kg H~2~ for grey and 3.214 for solar-based ammonia); Kum et al. (2026, p. 17) report 0.38 kg CO~2~/kg H~2~ for the cracking stage alone (Section 21). Commercial information is second-hand, such as vendor single-train capacities of 1000-1200 t/d NH~3~ (Mehr et al., 2026, p. 4203), and no paper reports industrial operating data.

## 4.6 Gap addressed by AmCraX

Key inputs are often only in unavailable supplementary material, several papers are internally inconsistent, and no study publishes an executable flowsheet that a reader can rerun and check with independent code. AmCraX contributes this transparency for a standard fired-cracker design (generated Aspen flowsheet, independent Python models, provenance labels, dashboard); it proposes no new catalyst or reactor concept.

Table: **Table 4.1.** The 14 library papers and how AmCraX uses them. *Source: research/notes/\*.md; values are published literature, not AmCraX results.*

| Citation | Type | Focus | Key quantitative finding | Use in AmCraX |
|---|---|---|---|---|
| Takahashi & Fujitani (2016) | Experiment + model | Ni/MgO, Ru/MgO microkinetics, 1 atm | Dehydrogenation *E*~a~ 144.0 (Ni) / 105.8 (Ru) kJ/mol | Kinetic parameters of the reactor model (Section 14) |
| Su et al. (2023) | Review | Ru and Ni catalysts, mechanism | Ru apparent *E*~a~ 41.55-98.2 kJ/mol | Mechanism, plausibility ranges (Sections 3, 14) |
| Maccarrone et al. (2025) | Review | Catalysts, kinetics, reactors | Ru-K/CaO conversion 98 % (1 bar) to 65 % (20 bar) at 500 °C | Reaction orders, *K*~p~ cross-checks, membrane recovery definitions |
| Xu et al. (2025) | Review | Catalysts, waste-heat reforming | Most catalysts need about 600 °C for full conversion | Context, property data (Table 2.1) |
| Cechetto et al. (2023) | Review | Membrane reactors, H~2~ quality | Equilibrium conversion 98.7 % at 5 bar, 500 °C; ISO NH~3~ ≤ 0.1 ppm | Equilibrium cross-check (Section 13), purity limits |
| Purcel et al. (2025) | Experiment | Ni long-term stability | 91.9 % to 90.4 % conversion between 250 and 800 h at 534 °C | Catalyst-stability context (Section 3) |
| Kum et al. (2026) | Simulation + TEA | Heat-integrated plant, dynamics | 94.56 % waste-heat recovery; LCOH 6.44 USD/kg | Ru rate law, PSA recovery, heat-integration benchmark |
| Cho et al. (2026) | Simulation + TEA | Ni vs Ru, 1.2-30 bar | LCOH 5.293 (Ru) / 5.439 (Ni) USD/kg | Closest flowsheet analogue; economic inputs, PSA benchmark |
| Richard et al. (2024) | Simulation + TEA | Fired tubular vs membrane reactor for power | LCOH 5.1 vs 4.45 EUR/kg | Membrane parameters, cost factors |
| Mehr et al. (2026) | Simulation + TEA | 1000 t/d NH~3~, pipeline-grade H~2~ | LCOH 8.36 EUR/kg (inconsistent breakdown) | Large-scale context only |
| Chopra et al. (2026) | Simulation + TEA + LCA | 400 kg/d refuelling station | GWP 17.91 (grey) / 3.214 (solar) kg CO~2~-eq/kg H~2~ | Environmental benchmark, cost inputs |
| Ahmad et al. (2025) | Simulation + TEA | NH~3~ in combined-cycle plant | Thermal efficiency 47.7-49.12 % | Plant-level cracker CAPEX correlation |
| Hansen et al. (2024) | Simulation | HYSYS Gibbs-reactor flowsheet | 0.131 to 0.141 kg H~2~/kg NH~3~ with feed preheat | Yield check, PSA recovery points |
| Farokhi et al. (2025) | Simulation + TEA | Heat-recovery cost optimum | LCOH 5.5 to 5.1 USD/kg | Heat-recovery and LCOH benchmark, cost inputs |

<!-- data: research/notes/*.md (page references in text); backend/amcrax/data/{economics,kinetics,separation}.yaml (citekeys actually used as inputs) -->
