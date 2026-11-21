# chopra2026decentralized

**APA 7:** Chopra, M., Srivastava, N., & Arora, P. (2026). Decentralized hydrogen production via ammonia decomposition: Process simulation, techno-economic, and environmental assessment. *Fuel, 415*, 138463. https://doi.org/10.1016/j.fuel.2026.138463

- DOI: 10.1016/j.fuel.2026.138463 (doi.org handle API responseCode 1, so the DOI is registered and verified on 2026-11-21)
- Type: research article (Fuel, Elsevier). Received 7 Nov 2025, accepted 17 Jan 2026, online 22 Jan 2026 (p. 1).
- Affiliation: Dept. of Hydro and Renewable Energy, IIT Roorkee, India.
- Page references below are PDF pages (PDF p. N = journal page N, 10 pages total). The supplementary information (Eqs. I-VII, Tables S1-S2, Figs. S1-S7) is **not** in the repository. Several key inputs are only there, including the NH3 prices (Fig. S6), the PSA recovery and the stream table (Table S2).

## Scope
- Supply-chain model for **decentralised H2 at hydrogen refuelling stations (HRS): 400 kg H2/day delivered at 350 bar**, produced by on-site NH3 cracking (p. 1 abstract; p. 3 §2).
- The scenarios differ in how the NH3 is made. I = grid electricity with electrolytic Haber-Bosch (HB), II = solar PV, III = grid + solar, IV = off-grid PV + battery, V = grey (conventional) NH3. VI = direct solar PEM water electrolysis (PEMWE, 7 h sun) used as the reference. SMR is a conventional benchmark (p. 3 §2).
- Methods: process simulation, techno-economic analysis (TEA) and LCA. The Indian context applies throughout (location factor, grid mix, inventories).

## Process configuration (p. 3 Fig. 2; p. 4 §2.2; p. 5 Fig. 4; p. 6 §3.1)
- Simulator: **Aspen Plus®** (the version is not stated). Property method: **RKS-BM** (Redlich-Kwong-Soave with Boston-Mathias alpha function) (p. 3 §2).
- Feed: **3084 kg/day NH3** (F1) (p. 4 §2.2). Liquid NH3 leaves storage through a feed valve at **2.5 bar** (p. 6 §3.1).
- The feed is preheated to **300 °C** in a feed/product exchanger (FPH). It then enters a **six-zone catalytic reactor (R1-R6)**, with one burner per zone (Fig. 4, p. 5).
- Zone gas temperatures, read from the Fig. 4 labels: inlet 300 °C. Outlets: R1 345, R2 370, R3 390, R4 415, R5 450, R6 **470 °C**.
- Burner temperatures 1334.03-1336.9 °C (Burner 1 1336.12, 2 1336.04, 3 1336.18, 4 1335.74, 5 1334.03, 6 1336.9 °C).
- Zone flue-gas exits: 337, 336, 376, 297, 390, 454 °C (Fig. 4, p. 5).
- **Reactor pressure is not stated explicitly** in the main text. Only the 2.5 bar feed-valve outlet is given.
- **Furnace fuel:** CNG at start-up (**61.7 kg/h CNG**, flame **1347 °C**, p. 6). In steady state **18 % of the reactor product gas** (P1) is split to the burners (S1 splitter, p. 4; Fig. 4).
- Recycled product composition as printed: "74.5 % N2, 24.8 % H2 & 0.45 % NH3" (p. 6). **This looks swapped.** Cracked gas should be about 75 % H2 / 25 % N2. See Ambiguities.
- Heat integration: heat from the product streams (P2, P4) preheats the NH3 feed (FPH) and the combustion air (APH). **10 % heat leakage** is assumed for the heat exchangers (p. 4, citing [31-33]).
- NH3 removal: the product is cooled to **70 °C** and passed through an activated-carbon adsorber (capacity **0.5 mg NH3/g at 70 °C**, from Rodrigues et al. 2007 [34]) (p. 4).
- Purification: compression to **15 bar**, then PSA. The H2 product has **99 % purity** (p. 4, citing [35,36]). The **PSA recovery is not given** in the main text (it may be in Table S2).
- Product compression: **350 bar** (citing Restelli et al. 2024 [16]) (p. 4).
- Results: **99 % NH3 conversion** (Fig. S2), with a **catalyst loading of 42.88 kg** (p. 6).
- Derived check (my calculation, not in the paper): 3084 kg/d NH3 × 0.1776 = 547.7 kg/d theoretical H2. The 400 kg/d product is therefore about 73 % of the theoretical H2. This is consistent with the 18 % fuel recycle plus the separation losses.

## Governing equations
- **Eq. (1), p. 3:** 2NH3 ⇌ N2 + 3H2, with ΔH°R = 46.22 "kJ mol H2^-1" as printed, cited from Spatolisano et al. 2023 [27]. The unit is ambiguous (see Ambiguities).
- **Eq. (2), p. 4 (Temkin-Pyzhev-type rate law):** r = k0 · exp(−E0/(R·T)) · (P_NH3² / P_H2³)^β
  - r: reaction rate (unit not stated)
  - k0: pre-exponential factor, 2.92 × 10^6 s⁻¹ (Table 1)
  - E0: activation energy, 141.5 kJ mol⁻¹ (Table 1)
  - R: universal gas constant
  - T: temperature, K
  - P_i: partial pressures (unit not stated)
  - β: kinetic order, **value not reported in the main text**
  - The parameters were "determined from the reported experimental data [28,29]" (Armenise et al. 2013 PCCP; Armenise et al. 2018 Fuel) and entered in Aspen Plus. The paper attributes Table 1 (reaction conditions, catalyst and reactor dimensions) to Jackson et al. 2020 (Ecuity/BEIS HS420 report) [30].
- **Eq. (4), p. 4 (CEPCI escalation):** C2 = C1 · (I2/I1), with I1 = CEPCI 2001 = 397 and I2 = CEPCI 2025 = 798.8.
- **Eq. (5), p. 4 (capacity scaling):** C2 = C1 · (A2/A1)^n, with n = **0.8**. The location factor for India is **0.65**.
- There is no Eq. (3) in the paper (the numbering jumps from 2 to 4).
- The CAPEX/OPEX/LCOH formulas (Eqs. I-VII) are in the SI and are not available here.
- Costing methods: Turton correlations; Guthrie method for CAPEX (Turton et al. 2008 [37]).

## Table 1 (p. 3) as printed. **The table is typographically malformed in the publisher PDF.**
| Row label as printed | Value column as printed |
|---|---|
| "ReactorLength (m)Diameter (m) Number of tubes" | 0.0766 |
| "CatalystBed density (kg m−3)Bed voidage" | Lithium imide (Li2NH) / 33500.41 |
| Activation energy (kJ mol−1) | 141.5 |
| Pre-exponential factor (s−1) | 2.92 x 10^6 |

The length, number of tubes, bed density and voidage values are missing or merged. 0.0766 and 33500.41 cannot be assigned to a row unambiguously. **Do not use them.** Note also that a lithium-imide (Li2NH) catalyst is listed. This is unusual for a "Temkin-Pyzhev" fit to Ru/Al monolith data [28,29].

## Economic inputs (Table 2, p. 4; §2.3 p. 4; §3.2 p. 7-8). USD, cost year 2025
| Item | Value | Source given |
|---|---|---|
| Water | 1 $/m3 | none |
| Electricity | 80 $/MWh | IEA Electricity 2025 [38] |
| Catalyst | 24 $/kg | Devkota et al. 2024 [18] |
| Discount rate | 10 % | Devkota et al. 2024 [18] |
| Plant life | 20 yr | Sahu et al. 2024 [14] |
| Labour | 109,756 $/yr (4 per shift; 3 operators, 1 manager) | Sahu et al. 2024 [14] |
| Maintenance | 3 % of FCI | none |
| Insurance | 1.5 % of FCI | none |
| PEMWE | 959 $/kW | Sahu et al. 2024 [14] |
| H2 storage | 700 $/kg | Burke et al. 2024 [39] |
| Operating days | 330 d/yr | p. 8 |
| CEPCI 2001 / 2025 | 397 / 798.8 | Turton [37] / not cited |
| Scaling exponent n | 0.8 | p. 4 |
| India location factor | 0.65 | p. 4 |
| NH3 boil-off | 0.04 %/day | [9,25] p. 3 |

- NH3 prices per scenario are only in Fig. S6 (SI) and are **not extracted**.
- Central NH3 plant capacity: 2000 t/d (V), 333 t/d (I, III, IV), 97 t/d (II). Number of 400 kg/d HRS supplied: 528 (V), 96 (I, III, IV), 27 (II) (p. 3).

## Economic results
- **Cracking-plant CAPEX: $0.71 million** for 400 kg/d at 350 bar. The same-capacity PEMWE plant costs **$7.75 million**. PEMWE with PV and H2 storage costs **$10.32 million** (p. 7-8).
- TCI breakdown for cracking (Fig. 5a, p. 5): compressor 44 %, PSA 26 %, cracker 21 %, heat exchanger 5 %, adsorber 4 %.
- TCI breakdown for electrolysis (Fig. 5b): PEMWE 98.9 %. The remaining 1.04 % splits into compressor (the bulk), pump 2 % and heater 2 % of that slice. The text on p. 7 says "95 %" for PEMWE, which is inconsistent with the figure.
- CAPEX including NH3 storage and transport: Scenario II +71 % (**$1.22 million**), Scenario V +42 % (**$1.01 million**) (p. 8).
- Sensitivity (Fig. S5, p. 8): compressor capital cost ±10 % gives a CAPEX change of −19 % to +21 %. Compressor efficiency ±10 % gives −15 % to +13 %. A ±10 % input producing a ~±20 % total change is not plausible arithmetically when the compressor is 44 % of CAPEX. **Flag this.**
- OPEX/ALCC shares of total yearly cost (Fig. 6, p. 6; values read from figure labels):

| Scenario | NH3 | Storage | Others | ALCC |
|---|---|---|---|---|
| I | 70 % | 2 % | 20 % | 8 % |
| II | 79 % | 2 % | 13 % | 6 % |
| III | 70 % | 2 % | 20 % | 8 % |
| IV | 80 % | 2 % | 13 % | 5 % |
| V | 51 % | 4 % | 33 % | 12 % |

  Scenario VI: OPEX 8 %, ALCC 92 %. The text on p. 8 says the Scenario V ammonia share is "~58 %", while the figure label is 51 %.
- **LCOH, $/kg H2** (Fig. 7, p. 6; text p. 8):

| Scenario | LCOH |
|---|---|
| I | **11.51** |
| II | **17.02** |
| III | **11.24** |
| IV | **17.12** |
| V | **6.84** |
| VI | **12.77** (p. 8 text says 12.76) |
| SMR | **2.94** |

  The abstract rounds these to SMR 2.9 and V 6.8. The text on p. 9 swaps the II and VI costs ("$17.02 and $12.77 ... respectively" attached to VI and II). Fig. 7 is authoritative: II = 17.02, VI = 12.77.

## Environmental (LCA) (§2.4 p. 4-5; §3.3 p. 8-9; Fig. 8)
- Method: ISO 14040/44, **Environmental Footprint 3.0**, GaBi with Thinkstep databases, Indian datasets.
- Boundary: **cradle-to-gate**, including the HRS (dispensing). Functional unit (FU): **1 kg H2**.
- Scenario VI excludes transport. 5 % of H2 is lost in transport and handling.
- Inventories: NH3 production from Sahu et al. 2024 [14]. PEMWE adapted from [40,41] (Alghool et al. 2024; Wulf et al. 2018). HRS from Burkhardt et al. 2016 [42].
- **GWP (kg CO2-eq/kg H2), p. 8:**

| Scenario | GWP |
|---|---|
| I | **112.79** |
| II | **3.214** |
| III | **78.05** |
| IV | **9.96** |
| V (grey NH3 cracking) | **17.91** |
| VI (solar PEMWE) | **1.21** |
| SMR | **13.48** |

  The abstract rounds these to 13.5, 17.9 and 3. NH3 production accounts for 73 % (II) to 96 % (I) of the cracking-route GWP.
- AP (mol H+/kg H2), I-VI then SMR: 1.58, 0.0604, 1.101, 0.1547, 0.2073, 0.00729, 0.0393 (p. 8).
- EP-F (kg P eq), I-VI then SMR: 6.93E-5, 0.59E-5, 4.9E-5, 0.94E-5, 1.44E-5, 0.29E-5, 2.01E-5 (p. 8-9).
- HTC (CTUh): V 3.99E-9, SMR 3.0E-9 (p. 9).
- PM: II 5.48E-7, I 2.49E-5. **The unit is not stated.**
- WU (m3 world-eq deprived/kg H2): I 13.68, II 1.204 (p. 9).
- Future grid (Fig. S7, p. 9): GWP falls 63.1 % (2030) and 89 % (2040). Scenario I reaches **11.85** kg CO2-eq/kg H2 (conclusion, p. 9; the year is not stated explicitly, presumably 2040).
- Transport sensitivity, Scenario VI road: 100 km is insignificant, 500 km adds +5 % GWP.
- Maritime transport of Scenario II NH3: 5,000 km gives 3.54 and 10,000 km gives 3.93 kg CO2-eq/kg H2 (p. 9).
- NOx from the burner is "expected to be minimal". **No NOx model** is used (p. 6). Detailed NOx analysis is listed as future work (p. 9).

## Limitations
- Small HRS scale (400 kg/d), with Indian costs and grid. Not transferable to large plants without rescaling.
- Kinetic Table 1 is malformed and β is not reported, so the rate law cannot be reproduced.
- Reactor pressure and PSA recovery are absent from the main text.
- NH3 prices, CAPEX/OPEX equations and stream tables are only in the SI (not available).
- There are internal inconsistencies (product-gas composition, PEMWE share, LCOH attribution in the p. 9 text, CAPEX sensitivity).
- No uncertainty analysis. No NOx quantification.

## Relevance to AmCraX
- It is an Aspen Plus NH3-cracker model with a **product-gas recycle as burner fuel** (18 % split) and feed/air preheat by product-gas heat recovery. It is useful as a small-scale reference for AmCraX's burner and tail-gas heat-integration concept.
- It provides an **LCOH range for decentralised cracking** ($6.84-17.12/kg incl. NH3 supply, 350 bar) and **GWP by NH3 origin** (grey 17.91, PV 3.214 kg CO2-eq/kg H2). These are suitable as literature benchmarks for the environmental module, with the boundary caveat: cradle-to-gate including NH3 synthesis, transport and dispensing, Indian grid.
- Economic constants usable with citation: electricity 80 $/MWh, catalyst 24 $/kg, discount rate 10 %, life 20 yr, maintenance 3 % FCI, insurance 1.5 % FCI, n = 0.8, CEPCI 2025 = 798.8. Most are secondary citations; see the JSON for the original sources.
- **Do not use the kinetic constants of Table 1** for AmCraX (malformed, β missing, catalyst ambiguous).

## Ambiguities / issues
1. Eq. (1) unit "kJ mol H2^-1" with 46.22. The standard ΔH for 2NH3 → N2 + 3H2 is about 92 kJ per mol reaction, which is about 46 kJ per mol NH3, not per mol H2. The value is per mol NH3.
2. Table 1 is malformed. Reactor length, diameter, tube count, bed density and voidage cannot be read.
3. β of Eq. (2) is not reported. The units of r and P are not reported.
4. The recycled product-gas composition (74.5 % N2 / 24.8 % H2) is likely transposed.
5. PEMWE share of TCI: 95 % (text) vs 98.9 % (Fig. 5b).
6. Scenario V NH3 share of OPEX: ~58 % (text) vs 51 % (Fig. 6).
7. LCOH of II and VI are swapped in the p. 9 text. VI is 12.76 (p. 8) or 12.77 (Fig. 7).
8. The CAPEX sensitivity magnitudes look inconsistent with a 44 % compressor share.
9. Reactor operating pressure is not given in the main text.
