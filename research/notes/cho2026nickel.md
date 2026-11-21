# cho2026nickel

**APA 7:** Cho, S., Lee, Y., & Lee, I. (2026). Comparative assessment of ammonia decomposition processes based on nickel and ruthenium catalysts: A techno-economic perspective. *Energy Conversion and Management, 348*, 120796. https://doi.org/10.1016/j.enconman.2025.120796

- DOI: 10.1016/j.enconman.2025.120796. Verified via the doi.org handle API (responseCode 1) on 2026-11-21.
- Type: research article. Received 22 Jul 2025; revised 18 Nov 2025; accepted 19 Nov 2025; available online 26 Nov 2025. Volume year 2026 (PDF p. 1).
- Affiliation: School of Chemical Engineering, Pusan National University, Korea.
- Pages are PDF pages, which equal the journal article pages 1-19. The file "1-s2.0-S0196890425013202-main (1)" is a duplicate and was ignored.
- **Not available:** the Supplementary Materials (S1 catalyst kinetics, S2 installed-cost equations, S3 bounds, S4 simulation results, S5 cost breakdowns, S6 swap inputs).

## Scope
- Cost-optimised NH3-cracking process designs for a **Ni/Al2O3** catalyst and a **Ru-K/CaO** catalyst, compared within one thermodynamic and economic framework.
- Five pressure-based configurations: 1.2, 5, 10, 20 and 30 bar (Fig. 2, p. 4).
- Two-step Bayesian optimisation minimising LCOH (Fig. 3, p. 8). Energy and exergy analysis, sensitivity analysis, and Monte Carlo uncertainty analysis (10,000 iterations).

## Process configuration (§2 p. 5; Table 2 p. 5; Table 3 p. 6)
- Simulator: **Aspen Plus V14**. Property method: **Peng-Robinson EOS** throughout (p. 6 §3.1).
- Liquid NH3 feed: **20 °C, 10 bar, 630 kg-NH3/h**.
- Flow path: HX1 evaporates the feed. The vapour mixes with a recycled H2 stream, is heated in HX2/HX3, and enters an **isothermal multi-tubular reactor (RPlug)**.
- Reactor data:
  - Tube diameter 0.01 m [64]; tube length 2.607 m (selected).
  - Space velocity 9,000 mL_NH3/(g_cat·h) (selected); bed void fraction 0.4 [57].
  - Ni/Al2O3, 8 wt % Ni, catalyst density 970 kg/m3 [57].
  - Ru-K/CaO, 3 wt % Ru, catalyst density 1,500 kg/m3 [65].
- Conversion constraint: **≥ 97 %**.
- Configuration by reactor pressure:
  - 1.2 and 5 bar: the feed is valved down; the effluent is compressed in 2 or 1 stages to 10 bar.
  - 10 bar: the reactor and TSA run at feed pressure (the simplest layout).
  - 20 and 30 bar: the feed is pumped up; the effluent is expanded to 10 bar for power recovery; the recycled H2 is compressed.
- **NH3 removal (TSA):** black-box model [38]; Zeolite 4A, 3 beds.
  - Inlet 61.05 °C, 10 bar.
  - Product NH3 < 0.1 ppm; regeneration at 350 °C. Regeneration heat comes from flue gas.
  - Adsorbent data: skeletal density 2,413.37 kg/m3, total porosity 0.678 (Vo et al. 2023 [53]).
- **H2 PSA:** black-box model [38]; Zeolite 5A, 4 beds.
  - Inlet 40 °C, 7 bar; desorption at 1.2 bar (assumed).
  - **H2 recovery 75.6 %, purity 99.11 mol%** (Yáñez et al. 2020 [55]).
  - Adsorbent data: skeletal density 2,360 kg/m3, porosity 0.69.
- Product: compressed to **180 bar** for storage [56].
- **Furnace:** the TSA and PSA tail gases burn in an external boiler (RGibbs, adiabatic, 1.2 bar, excess air). Supplementary **NH3 fuel** is added when the tail gas is insufficient [38]. The flue gas heats the reactor, TSA regeneration, and NH3 heating and evaporation.
- NOx: SCR after-treatment is costed. The flue gas is taken as > 95 % NO and < 5 % NO2 (p. 7).
- Design basis (Table 2):
  - Cooling water: 25 °C inlet, +5 °C rise.
  - Compressor isentropic efficiency 75 % [62]; expander 85 % [63]; pump adiabatic efficiency 75 % [17].
  - Maximum compression ratio 3.5. ΔTmin 10 °C [17].
- Other assumptions (p. 6): steady state; ambient 25 °C and 1.01325 bar; air 79/21 N2/O2; **no pressure drop** anywhere; no catalyst or adsorbent degradation.
- Optimisation constraints (p. 9): ΔTmin > 10 °C; flue gas leaving TSA desorption > 360 °C; conversion > 97 %.
- **Kinetic rate expressions are NOT in the main text.** They are in Supplementary Section S1, which is unavailable. The Ni/Al2O3 kinetics come from Collins (1993) [57]. The Ru-K/CaO kinetics come from Sayas et al. (2020), Catal. Sci. Technol. 10:5027 [59], and Lim et al. 2021 [37].

## Governing equations (main text)
- **Eq. (1):** 2NH3 ↔ N2 + 3H2, with **ΔHr = 45.6 kJ/mol NH3** (p. 2).
- **Eq. (2):** specific thermal energy demand [MJ/kg-H2] = LHV_NH3 · ṁ_NH3,Fuel / ṁ_H2 (p. 6).
- **Eq. (3):** specific power demand [MJ/kg-H2] = W_net / ṁ_H2 × 1/1000 (W in kW, ṁ in kg/s).
- **Eq. (4):** W_net [kW] = Σ W_Comp,i + W_Pump − W_Exp.
- **Eq. (5):** η_th = LHV_H2 · ṁ_H2 / [LHV_NH3 · (ṁ_NH3,Feed + ṁ_NH3,Fuel) + W_net/1000] × 100 %.
- **Eqs. (6)-(14), exergy (p. 6-7):**
  - Ėx_stream = Ėx_ph + Ėx_ch.
  - Ėx_ph = ṁ[(H − H0) − T0(S − S0)].
  - Ėx_ch = (Σ x_i·STD_i + R·T0·Σ x_i·ln x_i)·ṅ.
  - Ėx_in = Ėx_NH3,feed + Ėx_NH3,fuel + Ėx_air + Ėx_CW,in + Ėx_power.
  - Ėx_out = Ėx_H2 + Ėx_exhaust + Ėx_CW,out.
  - Destruction = in − out. Loss = exhaust + CW,out. Unused = destruction + loss.
  - η_ex = (1 − Ėx_unused/Ėx_in) × 100 % = Ėx_H2/Ėx_in × 100 %.
  - Reference state T0 = 25 °C, 1.01325 bar; R = 8.314 J/(mol·K).
- **Eq. (15):** LCOH = (C_AC + C_AO + C_NOx) / (ṁ_H2 × 3600 × OH). ṁ_H2 is in kg/s and OH in h/yr (p. 7).
- **Eq. (16):** C_AC = C_C × CRF.
- **Eq. (17):** CRF = d(1+d)^PL / [(1+d)^PL − 1].
- **Eq. (18):** C_C = ISBL + OSBL + Engineering + Contingency.
- **Eq. (19):** ISBL = Σ IEC_i (installed cost; the correlations are in SI S2.1, not available).
- **Eq. (20):** C_AO = OPEX_fixed + OPEX_variable.
- **Eq. (21):** OPEX_variable = C_NH3 + C_Elec + C_CW + C_Ads,TSA + C_Ads,PSA + C_Cat.
- **Eq. (22):** C_NOx = c_levelized,NOx × ṁ_NOx × 3600 × OH.
- **Eq. (23):** REC = LCOH − C_Feed / (ṁ_H2 × 3600 × OH). This is the reconversion cost, which excludes feed NH3.
- **Eqs. (25)-(27), combustion and excess air:**
  - 4NH3 + 3O2 → 2N2 + 6H2O.
  - 2H2 + O2 → 2H2O.
  - Excess air % = (ṅ_feed,air − ṅ_stoi,air)/ṅ_stoi,air × 100.

## Economic inputs (Table 4, p. 7; Table 8, p. 14). USD, analysis year 2024
| Item | Value | Ref. |
|---|---|---|
| Year of analysis | 2024 | - |
| Plant lifetime | 25 yr | [17] Cho et al. 2025 ECM 325:119430 |
| Operating hours | 8,000 h/yr | [67] Cho et al. 2024 ECM 300:117969 |
| Discount rate | 8.5 % | [17] |
| OSBL | 12 % of ISBL | [73] Noh et al. 2024 |
| Engineering | 10 % of (ISBL+OSBL) | [73] |
| Contingency | 18 % of (ISBL+OSBL) | [73] |
| Maintenance | 3 % of annualized CAPEX | [74] Do et al. 2023 |
| Operating charges | 15 % of labor | [74] |
| Plant overhead | 25 % of (labor + maintenance) | [74] |
| G&A | 6 % of annual fixed OPEX | [74] |
| Operator salary | 34,167 $/yr | [39] Devkota et al. 2024 |
| NH3 price | 450 $/t (assumed; current conventional NH3 300-610 $/t [70-72]) | assumed |
| Electricity | 0.084 $/kWh | [75] Noh & Lee 2024 |
| Cooling water | 2.125×10⁻⁷ $/kJ | [17] |
| NOx after-treatment | 4 $/kg-NOx treated | [17] |
| **Ni catalyst price** | **33.4 $/kg** | "Calculated" (method in SI) |
| **Ru catalyst price** | **542 $/kg** | "Calculated" |
| Adsorbent price | 10 $/kg | [53] |
| **Catalyst lifetime** | **2 yr (assumed)** | assumed |
| Adsorbent lifetime | 4 yr (assumed) | assumed |

Sensitivity ranges (Table 8, p. 14), given as pessimistic / base / optimistic:
- NH3 price: 610 / 450 / 300 $/t.
- Electricity: 0.126 / 0.084 / 0.042 $/kWh.
- Ni catalyst: 66.8 / 33.4 / 16.7 $/kg.
- Ru catalyst: 1,084 / 542 / 271 $/kg.
- Catalyst lifetime: 4 / 2 / 1 yr. This is **as printed**: the "pessimistic" column shows 4 yr and the "optimistic" 1 yr, which looks inverted.
- NOx cost: 6 / 4 / 3 $/kg.
- CAPEX: +50 % / 0 / −50 %.

Renewable NH3 cost outlook (Table 9, p. 15):
- Current: US 893-1,410; W. Europe 1,275-1,911; Japan 1,861-2,681; China 891-1,169 $/t [81, IEA ETP 2023].
- Future: 2030 472-946; 2040 380-748; 2050 315-611 $/t [82, IRENA 2022].
- Extended sensitivity prices: 1,000 (current), 709 (2030), 564 (2040), 463 (2050) $/t (p. 17).

## Results
### First optimisation step (Table 5, p. 9)
| | Ni 1.2 | Ni 5 | Ni 10 | Ni 20 | Ni 30 | Ru 1.2 | Ru 5 | Ru 10 | Ru 20 | Ru 30 bar |
|---|---|---|---|---|---|---|---|---|---|---|
| T_rx (°C) | 653.15 | 684.50 | 701.59 | 727.93 | 746.98 | 482.50 | 535.33 | 566.69 | 616.84 | 639.35 |
| NH3 fuel (kmol/h) | 0.562 | 0.910 | 1.093 | 1.610 | 1.995 | − | − | − | − | 0.277 |
| Excess air (%) | 15.00 | 15.00 | 15.00 | 15.00 | 15.00 | 58.70 | 38.70 | 30.00 | 15.01 | 15.00 |

### Net power demand and power by unit (Table 6, p. 11)
Net power (kW):

| | 1.2 bar | 5 bar | 10 bar | 20 bar | 30 bar |
|---|---|---|---|---|---|
| Ni | 302.40 | 193.18 | 145.16 | 74.68 | 33.94 |
| Ru | 307.50 | 195.72 | 146.47 | 90.07 | 58.46 |

- Comp2 (H2 product compressor) draws about 136-138 kW in every case.
- Expander output: Ni 72.90 kW (20 bar) and 115.28 kW (30 bar); Ru 56.62 and 88.96 kW.

### Unit CAPEX (Fig. 7a, p. 12; $/kg-H2)
| | 1.2 bar | 5 bar | 10 bar | 20 bar | 30 bar |
|---|---|---|---|---|---|
| Ni | 0.647 | 0.595 | 0.562 | 0.582 | 0.597 |
| Ru | 0.626 | 0.580 | 0.549 | 0.573 | 0.598 |

### LCOH (Fig. 7b; $/kg-H2)
| | 1.2 bar | 5 bar | 10 bar | 20 bar | 30 bar |
|---|---|---|---|---|---|
| Ni | 5.614 | 5.502 | 5.449 | 5.441 | 5.447 |
| Ru | 5.454 | 5.340 | 5.293 | 5.307 | 5.357 |

- OPEX is 86-88 % of LCOH. NH3 feed is 61-65 % of LCOH. Labor is about 0.67 $/kg (p. 14).
- Specific NH3 consumption: theoretical 5.632 kg/kg-H2. Ni up to 8.05 (Ni-30 bar). Ru about 7.6, with Ru-30 bar at 7.76 (p. 10-11).

### Cost-optimal designs (Table 7, p. 13; Fig. 8, p. 13; Conclusion, p. 17)
| | **Ni-24.34 bar** | **Ru-10 bar** |
|---|---|---|
| Reactor T (°C) | 735.52 | 566.69 |
| NH3 fuel (kmol/h) | 1.736 | 0 |
| Excess air (%) | 15.00 | 30.00 |
| Specific NH3 consumption (kg/kg-H2) | 8.011 | 7.639 |
| NOx (mg/Nm3) | 1,517 | 863 |
| Specific thermal energy (MJ/kg-H2) | 6.7 | 0 |
| Specific power (MJ/kg-H2) | 2.4 | 6.4 |
| Energy efficiency (%) | 79.25 | 80.82 |
| Exergy efficiency (%) | 75.35 | 77.00 |
| Unit CAPEX ($/kg-H2) | 0.586 | 0.549 |
| (OSBL+Eng+Cont) | 0.177 | 0.166 |
| (boiler) | 0.126 | 0.126 |
| (heat exchangers) | 0.098 | 0.090 |
| (compressor) | 0.050 | 0.049 |
| (T/PSA) | 0.084 | 0.083 |
| (decomposition reactor) | 0.036 | 0.035 |
| Raw material ($/kg) | 3.443 | 3.437 |
| Fixed OPEX ($/kg) | 1.028 | 1.025 |
| Other OPEX ($/kg) | 0.232 | 0.197 |
| NOx after-treatment ($/kg), *derived as the remainder* | ≈0.150 | ≈0.085 |
| **LCOH ($/kg-H2)** | **5.439** | **5.293** |
| **REC ($/kg-H2)** | **1.995** | **1.856** |

- Ru-10 bar compared with Ni-24.34 bar (p. 14-15): 6.3 % less capital investment and 42.9 % lower NOx cost. Energy efficiency is 1.6 %p higher and exergy efficiency 1.7 %p higher. LCOH is 2.7 % lower and REC 7.0 % lower.
- Best thermodynamic cases from step 1 (p. 13): Ni-30 bar reaches η_th 79.4 % and η_ex 75.4 %. Ru-20 bar reaches 81.9 % and 77.9 %.
- Swap test (Fig. 9, p. 14): the Ni catalyst run at the Ru-10 bar conditions (566.69 °C) gives +116 % LCOH.
- Sensitivity (Fig. 10, p. 15-17): NH3 price has the largest effect on LCOH, followed by CAPEX. CAPEX dominates the REC. Ru is more sensitive to electricity price and to catalyst price and lifetime. Ni is more sensitive to NH3 price and NOx cost. Catalyst-related parameters have only a minor effect overall.
- Extended sensitivity (Fig. 11, p. 17): Ru REC stays at 1.856 $/kg for every NH3 price. Ni REC is 2.193 (current), 2.089 (2030) and 2.000 (2050) $/kg.
- Monte Carlo (Fig. 12, p. 17): mean REC is 2.001 $/kg for Ni and 1.865 $/kg for Ru. Ru standard deviations are 3.7 % (LCOH) and 2.4 % (REC) lower.
- Derived H2 output (my calculation): Ru-10 bar 630/7.639 ≈ 82.5 kg/h; Ni (630 + 1.736×17.031)/8.011 ≈ 82.3 kg/h. The paper does not tabulate these in the main text.

## Literature values quoted in Table 1 (p. 2). These are NOT this paper's results; cite the originals
| Study | Reactor | Catalyst | Conditions | Energy eff. | LCOH | Emissions |
|---|---|---|---|---|---|---|
| Lim et al. 2021 [37] | packed bed | Ru-K/CaO | 600 °C, 40 bar | 82.6 % | 3.58-5.21 $/kg | 2.9-6.3 kg CO2/kg H2 |
| Devkota et al. 2024 [39] | multi packed bed | Ru/Al2O3 | 500 °C, 10 bar | 79 % | 6.05 $/kg | 0.01-1.11 kg CO2/kg H2 |
| Nasharuddin et al. 2019 [40] | - | Ni | 600-650 °C, 1.8-2 bar | - | 5.50 $/kg | - |
| Makhloufi & Kezibri 2021 [41] | - | Ru/Al2O3 | 400-550 °C, 10-30 bar | 68.5 % | 4.83 EUR2019/kg | - |
| Cha et al. 2021 [45] | - | Ru/La-Al2O3 | 525 °C, 1.2 bar | 83.6 % (reformer eff.) | 3.98-7.03 $/kg | < 1 kg CO2/kg H2 |
| Kanaan et al. 2023 [46], packed bed | - | Ru/Al2O3 | 650 °C, 1.013 bar | 78-80 % | 8-11.36 $/kg | - |
| Kanaan et al. 2023 [46], membrane | - | Ru/Al2O3 | 550 °C, 10 bar | 87-90 % | 7.72-11 $/kg | - |
| Lim et al. 2022 [47], packed bed | - | Ru-K/CaO | 500 °C, 1 bar | 79.1 % | 10-13.6 $/kg (breakeven) | 5.4 kg CO2/kg H2 |
| Lim et al. 2022 [47], membrane | - | Ru-K/CaO | 400 °C, 40 bar | 82.7 % | 8.6-12.1 $/kg (breakeven) | 4.5 kg CO2/kg H2 |
| Akhtar et al. 2021 [48] | - | Ru/La-Al2O3 | 400 °C, 1.01 bar | - | 9.74 $/kg | 6.81 kg CO2/kg H2 |

- Makhloufi & Kezibri [41] design detail: firebox 12 × 15 × 12 m with 352 radiant tubes; 8.5 wt % Ru/Al2O3; 200 TPD H2 at 250 bar (p. 3).

## Limitations
- Kinetics, installed-cost correlations, catalyst-price derivation and decision-variable bounds are all in the SI, which is unavailable. The kinetic models therefore cannot be reproduced from the main text.
- The model assumes no pressure drop and no catalyst deactivation. Conversion is fixed at ≥ 97 %.
- TSA and PSA are black-box models.
- The scale is small: 630 kg/h NH3, about 2 t/d H2.
- There is no LCA. NOx enters only as a cost via SCR.
- The catalyst lifetime of 2 yr is an assumption. The ordering in the Table 8 lifetime row looks inverted (pessimistic 4 yr, optimistic 1 yr).

## Relevance to AmCraX
- **Directly comparable to the AmCraX baseline.** AmCraX's PSA + tail-gas burner + RGibbs/RPlug structure matches this paper: Aspen Plus, PR EOS, tail-gas boiler with NH3 make-up fuel, PSA black box.
- Benchmarks:
  - Ni-24.34 bar at 735.52 °C gives LCOH 5.439 $/kg and η_th 79.25 %.
  - Ru-10 bar at 566.69 °C gives LCOH 5.293 $/kg and η_th 80.82 %.
  - PSA recovery 75.6 % and purity 99.11 % (from Yáñez 2020).
- Inputs usable for the economics module:
  - Catalyst prices: Ni 33.4 $/kg, Ru 542 $/kg; lifetime 2 yr (assumption).
  - Discount rate 8.5 %, 25 yr life, 8,000 h/yr.
  - OSBL/engineering/contingency factors: 12 %, 10 % and 18 %.
  - Electricity 0.084 $/kWh; NOx cost 4 $/kg.
- The paper's energy-efficiency definition (Eq. 5) is a good template for AmCraX's efficiency KPI.
