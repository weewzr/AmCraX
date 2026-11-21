<!-- cites: su2023review, maccarrone2025comprehensive, xu2025review, cechetto2023membrane, takahashi2016kinetic, purcel2024stability, kum2026heatintegrated, cho2026nickel, richard2024technoeconomic, mehr2026highcapacity, chopra2026decentralized, ahmad2025gtcc, hansen2024hysys, farokhi2025costoptimization, realpe2024repurposing, yanez2020psa, jiang2021hollow, iso2019hydrogen -->

# 5 Literature review

The AmCraX library holds 14 papers (four reviews, two experimental catalyst studies, eight process-simulation or techno-economic studies), each abstracted into a structured note with page references, parameters and documented inconsistencies (`research/notes/`). All values below are **published literature**, not AmCraX results. Table 5.1 summarises the papers; catalyst and mechanism material is in Section 4.

## 5.1 Catalysts and kinetics

The three catalyst reviews (Su et al., 2023; Maccarrone et al., 2025; Xu et al., 2025) agree that Ru is the most active metal, Ni the practical non-noble choice, and that Ni sinters at high temperature; Maccarrone et al. (2025, pp. 3-4) also give *K*~p~ correlations with typographical errors. Long-term data are scarce (Purcel et al., 2025; Table 4.2). Only Takahashi and Fujitani (2016, p. 25) give a fully parameterised microkinetic model for Ni and Ru; Kum et al. (2026, pp. 5, 9) give a reversible Temkin-Pyzhev law fitted to 36 points at 1-10 bar (mean absolute percentage error 0.81 %). Both are implemented (Sections 4.6, 10.5). The rate laws of Cho et al. (2026) and Richard et al. (2024) are only in unavailable supplementary material, Chopra et al. (2026) print a malformed table without β, and Mehr et al. (2026) give no pre-exponential factor.

## 5.2 Reactors, heat integration and purification

Industrial designs use fired multi-tubular packed beds: 336 tubes of 3 m with 96.3 % conversion at 79.25 kJ/mol NH~3~ and more than 2 bar pressure drop (Kum et al., 2026, pp. 5, 10); 96 tubes of 5 m with Ni (Mehr et al., 2026, p. 4201); an isothermal RPlug with at least 97 % conversion (Cho et al., 2026, p. 5). Pd-membrane reactors reach more than 99 % conversion with 90-97.5 % recovery at 400-500 degC and 4-7 bar, with membranes limited to 500 degC (Cechetto et al., 2023, pp. 10784, 10789), and a thermal efficiency of 85 % against 68.5 % for a fired reactor, but need at least 5-6 bar (Richard et al., 2024, pp. 581-584).

Heat integration is the main efficiency lever. Feed preheat with product heat raised the yield from 0.131 to 0.141 kg H~2~/kg NH~3~ (Hansen et al., 2024, p. 83); added recovery lowered the LCOH from 5.5 to 5.1 USD/kg for purchased-equipment cost rising from 1702 to 1850 kUSD (Farokhi et al., 2025, p. 52); a pinch-based network recovers 94.56 % of the waste-heat potential against 18.22 % and cuts net energy demand by 37.1 % (Kum et al., 2026, pp. 13, 15); feed/effluent integration plus a pre-cracker raised efficiency from 65.7 to 75.3 % (Realpe et al., 2024, as cited in Xu et al., 2025, p. 30). Tail gas covers the furnace duty at full load in Mehr et al. (2026, p. 4207), whereas Cechetto et al. (2023, p. 10780) find off-gas alone generally insufficient. The AmCraX feed/effluent exchanger and tail-gas burner follow this pattern.

PSA is "the most well developed technology" for this duty (Cechetto et al., 2023, p. 10778) and is treated as a black box: 75.6 % recovery at 99.11 mol% after a TSA that removes NH~3~ below 0.1 ppm (Cho et al., 2026, p. 6, from Yáñez et al., 2020); 80 % (Kum et al., 2026, p. 3); about 81 % at 99.96 mol% (Mehr et al., 2026, p. 4201); ideal splitters (Hansen et al., 2024; Farokhi et al., 2025). Pd-Ag membranes reached above 99.999 % with less than 0.01 ppm NH~3~ (Jiang et al., 2021, as cited in Cechetto et al., 2023, p. 10791); ISO 14687 limits are discussed in Section 3.4 (ISO, 2019).

## 5.3 Simulation practice

Aspen Plus is used by Cho et al. (2026, V14), Richard et al. (2024, v11), Ahmad et al. (2025, V14), Chopra et al. (2026) and Kum et al. (2026, V14 with gPROMS); Aspen HYSYS by Hansen et al. (2024), Farokhi et al. (2025) and Mehr et al. (2026). Peng-Robinson dominates (Section 9.1). Gibbs reactors represent the cracker when catalyst data are missing (Hansen et al., 2024, p. 81; Farokhi et al., 2025, p. 49), RPlug is used with kinetics (Cho et al., 2026; Richard et al., 2024), and burners are usually Gibbs reactors. AmCraX uses RGibbs, PENG-ROB and an RStoic burner (Sections 7-10).

## 5.4 Techno-economics, environment and technology status

Published LCOH values are not directly comparable because their bases differ (Table 5.1; Section 17.4 compares them with AmCraX): 5.293 (Ru) and 5.439 USD/kg (Ni) at 450 USD/t NH~3~, 8.5 % discount rate (Cho et al., 2026, p. 13); 6.44 USD/kg most probable (Kum et al., 2026, p. 16); 5.1 and 4.45 EUR/kg (fired and membrane reactor; Richard et al., 2024, pp. 582-584); 8.36 EUR/kg with an inconsistent breakdown (Mehr et al., 2026, p. 4210); 6.84-17.12 USD/kg for 400 kg/d delivered at 350 bar (Chopra et al., 2026, p. 6). NH~3~ cost is the largest item in all of them. Only Chopra et al. (2026, p. 8) perform an LCA (17.91 kg CO~2~-eq/kg H~2~ for grey and 3.214 for solar ammonia); Kum et al. (2026, p. 17) report 0.38 kg CO~2~/kg H~2~ for the cracking stage alone. Commercial information is second-hand: vendor single-train capacities of 1000-1200 t/d NH~3~ (Mehr et al., 2026, p. 4203) and TRL 7 for fired crackers against 4-5 for membrane reactors (Richard et al., 2024). No paper reports industrial operating data.

## 5.5 Gap addressed by AmCraX

Key inputs (kinetics, cost correlations, stream tables) are often only in unavailable supplementary material, several papers are internally inconsistent, and no study publishes an executable flowsheet that a reader can rerun and cross-check with independent code. AmCraX contributes this transparency and reproducibility for a standard design: a scripted Aspen Plus V15 flowsheet, independent Python models, provenance labels on every value and an interactive dashboard. It does not propose a new catalyst or reactor concept.

Table: **Table 5.1.** The 14 library papers and how AmCraX uses them. *Source: research/notes/\*.md; values are published literature, not AmCraX results.*

| Citation | Type | Focus | Key quantitative finding | Use in AmCraX |
|---|---|---|---|---|
| Takahashi & Fujitani (2016) | Experiment + model | Ni/MgO, Ru/MgO microkinetics, 1 atm | Dehydrogenation *E*~a~ 144.0 (Ni) / 105.8 (Ru) kJ/mol | Primary kinetic parameters (Section 10) |
| Su et al. (2023) | Review | Ru and Ni catalysts, mechanism | Ru *E*~app~ 41.55-98.2 kJ/mol | Mechanism, rate-law forms, plausibility ranges |
| Maccarrone et al. (2025) | Review | Catalysts, kinetics, reactors | Ru-K/CaO conversion 98 % (1 bar) to 65 % (20 bar) at 500 degC | Reaction orders, *K*~p~ cross-checks |
| Xu et al. (2025) | Review | Catalysts, waste-heat reforming | Most catalysts need about 600 degC for full conversion | Context, property data (Table 3.1) |
| Cechetto et al. (2023) | Review | Membrane reactors, H~2~ quality | Equilibrium conversion 98.7 % at 5 bar, 500 degC; ISO NH~3~ ≤ 0.1 ppm | Equilibrium cross-check, purity specification |
| Purcel et al. (2025) | Experiment | Ni long-term stability | 91.9 % → 90.4 % over 250-800 h at 534 degC | Catalyst-life assumptions |
| Kum et al. (2026) | Simulation + TEA | Heat-integrated plant, dynamics | 94.56 % waste-heat recovery; LCOH 6.44 USD/kg | Ru rate law, heat-integration benchmark |
| Cho et al. (2026) | Simulation + TEA | Ni vs Ru, 1.2-30 bar | LCOH 5.293 (Ru) / 5.439 (Ni) USD/kg | Closest flowsheet analogue; economic inputs |
| Richard et al. (2024) | Simulation + TEA | Fired tubular vs membrane reactor for power | LCOH 5.1 vs 4.45 EUR/kg | Membrane option, cost factors |
| Mehr et al. (2026) | Simulation + TEA | 1000 t/d NH~3~ pipeline-grade H~2~ | LCOH 8.36 EUR/kg (inconsistent breakdown) | Large-scale context only |
| Chopra et al. (2026) | Simulation + TEA + LCA | 400 kg/d refuelling station | GWP 17.91 (grey) / 3.214 (solar) kg CO~2~-eq/kg H~2~ | Environmental benchmark |
| Ahmad et al. (2025) | Simulation + TEA | NH~3~ in combined-cycle plant | Thermal efficiency 47.7-49.12 % | Context: partial cracking for power |
| Hansen et al. (2024) | Simulation | HYSYS Gibbs-reactor flowsheet | 0.131 → 0.141 kg H~2~/kg NH~3~ with feed preheat | Model-fidelity lower bound, yield check |
| Farokhi et al. (2025) | Simulation + TEA | Heat-recovery cost optimum | LCOH 5.5 → 5.1 USD/kg | Heat-recovery trade-off benchmark |

<!-- data: research/notes/*.md (page references in text) -->
