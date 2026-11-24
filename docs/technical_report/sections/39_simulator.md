<!-- cites: takahashi2016kinetic, kum2026heatintegrated, lucentini2021nirukinetic, goodwin2018cantera -->

# 39 Interactive process simulator

The first page of the public website is now an interactive process simulator. The site is static (GitHub Pages): it cannot run Python or Aspen Plus. Every number on the simulator page therefore comes from one of three places, and each displayed value carries a source badge that says which: a stored Aspen Plus V15 result, an interpolation of a stored Aspen or Python grid, or a browser-side calculation whose code is tested against the Python model. The particle animation along the streams shows direction and relative flow only; it is not a transient simulation and no number is taken from it.

## 39.1 What is computed in the browser

The browser port (`frontend/src/sim`, TypeScript) contains:

* the five catalyst rate laws (Takahashi & Fujitani, 2016, for Ni/MgO and Ru/MgO; the Temkin-Pyzhev law used by Kum et al., 2026, for Ru/Al~2~O~3~; Lucentini et al., 2021, for the two NiRu/CeO~2~ catalysts) in a plug-flow reactor with isothermal, adiabatic, wall-heated and fixed-duty modes and an optional Ergun pressure drop, using a viscosity table from Cantera (Goodwin et al., 2018) for the baseline feed only;
* an ideal-gas equilibrium conversion, shown next to the stored Aspen RGibbs (PENG-ROB) value on its grid of 14 temperatures from 250 to 900 °C and 6 pressures from 1 to 40 bar;
* the cracker duty, hydrogen production, tail-gas heating value and burner heat as an exact port of the Python flowsheet, while the pump, vaporiser, preheater, FEHE and cooler duties are bilinear interpolations of a stored Python flowsheet grid (17 temperatures from 400 to 800 °C x 9 pressures from 3 to 50 bar, heat integration on and off);
* the economics on the unified reference scenario of Section 32 (CAPEX method `cho2026_itemised_v1`, 2024 USD, 1.288444 SGD/USD of 20 November 2026), with LCOH, cost breakdown, capital cost, NPV and simple payback, and a catalyst price selector (derived central, low, high, or the labelled Phase 1 TEA prices);
* the carbon intensity by ammonia route and the carbon cost in Mode A (actual Singapore boundary, default) or Mode B (hypothetical life-cycle price, labelled not Singapore law), as in Section 34.

At the stored baseline the page shows an LCOH of 4.015 USD/kg (5.174 SGD/kg), a capital cost of 7.67 MUSD, an NPV of -17.46 MUSD at 3.06 USD/kg and a payback of "not reached", the same values as the Python reference scenario. Outside a rate law's fitted range the reactor output is labelled "extrapolation" and a domain warning is shown; the fitted ranges are those of Table 35.2.

## 39.2 Parity with Python (numerical verification)

Tolerances were fixed before any comparison: conversion 1e-3 absolute, temperature 0.5 K, pressure 1e-3 bar, duties, costs and carbon intensity 0.5 % relative.

Table: **Table 39.1.** Browser model against the Python model (numerical verification). *Source: results/research/simulator/parity_report.json.*

| Quantity | Cases | Largest difference |
|---|---|---|
| Plug-flow reactor, all laws and modes, full profiles: conversion | 35 | 4.0e-8 |
| Same: outlet temperature | 35 | 2.9e-5 K |
| Same: pressure | 35 | 8.5e-6 bar |
| Rate laws | 15 | inside 0.5 % |
| Process on grid nodes | - | 4e-15 relative |
| Interpolated duties off the grid (reported, not asserted) | - | within 0.07 % |
| LCOH on the unified basis | 10 | 2.1e-16 relative |
| Carbon intensity | 8 | 0 |

The frontend has 227 passing unit tests in 25 files, including these parity tests, and the Python side has 9 tests on the exported simulator data.

## 39.3 Comparison with Aspen Plus (Python against Aspen kind)

The browser model was also run on 203 stored Aspen kinetic cases. This is a comparison of two models, never validation. Inside the fitted range of the Ru/Al~2~O~3~ law (12 isothermal cases) conversion agrees within 5.4e-4. The largest conversion difference over all cases is 0.065, and the largest differences are for the Takahashi laws at 20 bar, which is extrapolation. The isothermal duty differs by up to 14.8 % (a case with a 179 kW Aspen duty), and the largest outlet-temperature difference in the non-isothermal cases is 4.4 K. In the integrated flowsheets the largest relative difference, 0.147, is in the net fuel deficit, a difference of large numbers; the vaporiser is 3.5 % lower in every case. The browser ideal-gas equilibrium differs from Aspen PENG-ROB by up to 0.0148 in conversion, a non-ideality (model-form) difference.
<!-- data: docs/internal/research_reports/phase2-w1-agent6.md and phase2-w2-agent2.md, from results/research/simulator/parity_report.json -->

## 39.4 Interface

The process-flow diagram uses the Aspen block and stream names (FEED, S1 to S7, H2PROD, TAILGAS, AIR, FLUE, STACK; PUMP, VAPORIZR, FEHE, HEATER, CRACKER, BURNER, COOLER, PSA, FLUEHX). Its interaction pattern was adapted from the NUS-H2 interactive process-flow site, re-implemented in React and TypeScript without copying its code or images: every unit and stream is a keyboard-focusable element that opens a panel with what the unit does and its computed values with source badges, each control pairs a slider with a number box and shows its allowed range, out-of-range input is blocked with a message, and presets and a reset restore stored cases. Eight graphs (conversion against temperature, rate against temperature, axial profiles along the bed, profiles against catalyst mass, hydrogen against heat input, cost against a chosen variable, energy balance, carbon by route) are computed from the same functions. Results can be exported as JSON or CSV. The site check passes on four viewports (390 to 1920 px wide).

## 39.5 Limits

The browser simulator has no membrane model and uses an ideal-gas equilibrium. The PSA is a splitter with assumed recovery and N~2~ slip, and the product purity is always labelled an assumption. The downstream duties are interpolated from a grid computed at equilibrium conversion with a fixed FEHE approach of 50 K, stack temperature and excess air, which the user cannot change. Feed composition is fixed. The economics port does not include IRR, the catalyst-mass and exchanger-area size drivers of the CAPEX method, or the legacy CAPEX. In equilibrium mode the catalyst cost uses the Python reference inventory and the Phase 1 TEA Ni price, so that the frozen baseline of 4.015 USD/kg is reproduced; the catalyst price selector is disabled there.
