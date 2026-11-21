# mehr2026highcapacity

**APA 7:** Mehr, A. S., Scheffknecht, G., Zohourian, R., Reinmöller, M., & Maier, J. (2026). Design, simulation, and techno-economic evaluation of a high-capacity ammonia cracking facility for pipeline-grade hydrogen production. *Energy Science & Engineering, 14*(9), 4197–4212. https://doi.org/10.1002/ese3.70618

- DOI: 10.1002/ese3.70618. Verified on 2026-11-21 through the doi.org handle API (responseCode 1).
- Type: original article, open access (CC BY).
- Dates: received 20 Apr 2026, revised 30 Jun 2026, accepted 21 Jul 2026.
- Affiliations: IED, University of Stuttgart; EnBW Energie Baden-Württemberg AG (funder).
- Author name: the first author is printed as "Amin Soleimani Mehr". The publisher file name uses "Mehr" as the surname, which is what the APA string follows. If the surname is "Soleimani Mehr", the APA form would be "Soleimani Mehr, A.". **Check this before final use.**
- Page convention: page numbers below are **PDF pages**, so PDF p. 1 = journal p. 4197 and PDF p. N = journal p. 4196+N. The PDF has 16 pages.

## Scope
- The paper designs a **1000 MTPD NH3 → ~137 MTPD H2** facility for pipeline injection.
- It has three units:
  - Unit 100: refrigerated storage with boil-off-gas (BOG) re-liquefaction.
  - Unit 200: a fired tubular Ni/Al2O3 cracker with PSA.
  - Unit 300: three-stage centrifugal H2 compression.
- Steady-state and off-design simulations cover 50-100 % load.
- The techno-economic analysis (TEA) is set in a European market context.
- The CO2-avoidance comparison against fossil H2 is simple.

## Simulators and property method
- **Aspen HYSYS V11** covers Units 100, 200 and heat integration. **Aspen Plus V12** covers Unit 300 compression (p. 3 §2.2).
- Property method: **Peng-Robinson EOS with default binary-interaction parameters** (p. 7 §2.7).
- Capital costs come from the **Aspen Process Economic Analyzer (APEA)** (p. 6 §2.6; p. 13).

## Process configuration and operating conditions
- Boundary (p. 3 §2.3): the inlet is liquid NH3 at −33 °C and 1 bar. The outlet is H2 at 104 bar and 40 °C.
  - Elsewhere the paper gives the outlet as 115 bar (p. 2 §2.1; p. 8 §3.1.3). **This is inconsistent.**
- Table 1 (p. 3):
  - NH3 feed: "1000% ± 10%" MTPD (typo; read as 1000 ± 10 %).
  - H2 product pressure: 104 bar.
  - Cooling water inlet and ambient temperature: both 30 °C.
  - **Heat-recovery efficiency of the feed-heater network: 85-90 %.**
  - **Furnace heat-loss allowance: 1 %.**
- Storage (p. 4 Table 2; p. 4-5):
  - Two tanks of 27,000 t each (54,000 t total, about 30 days). One 7,200 t day/surge tank.
  - BOG is 14,412 kg/day per tank; the BOG range is 0.033-0.133 %/day.
  - Tank geometry: L/D 0.75, D 40.7 m, design level 30.5 m.
  - BOG cycle: two-stage compression, 1 → 4 bar then 14 bar.
  - Compressor power is about 238 kW and heat-exchanger area 51.6 m2.
  - Table 5 (p. 8) instead gives boil-off 0.83 %/day and BOG compressor duty 99.84 kW. **These are inconsistent** with 238 kW and with 0.1 %/day.
- **Reactor (Unit 200)**:
  - A fired tubular reactor with a fixed bed of commercial **Ni/Al2O3**.
  - Feed preheat comes from flue gas and product-gas heat recovery.
  - Stated reactor conditions: "operating at **480 °C and 17.5 bar**" (p. 5 §2.4.2). The reactor outlet is **760 °C** (p. 8 §3.1.2).
  - Table 6 (p. 8) gives **21 bar**, inlet 480 °C, outlet 760 °C and conversion **99.7 %**. The text (p. 8) gives a conversion of 98.6 %. The conclusion (p. 15) gives a range of 480-720 °C.
  - Geometry (Table 3, p. 5): **96 parallel tubes**, 5 m long, 0.127 m internal diameter, 5 mm wall, total volume 6.08 m3.
  - Off-design (Table 8, p. 11): chamber temperature about 506-513 °C; stack temperature 230-239.9 °C.
- **Furnace fuel** (p. 11): at full capacity the PSA purge (tail) gas alone meets the furnace duty. At part load a slipstream of NH3 feed is burned, about **192 kg/h at 50 % load**. Low-NOx NH3 burners are assumed [3, 20]. No NOx results are given.
- **PSA**: two beds with four steps, 5A zeolite. Each bed is 2 m in diameter and 12 m high, with a cycle time of 360 s. The feed is 231 kmol/h, 35 °C, "approximately 1 bar" (p. 5).
  - **H2 purity 99.96 mol% and recovery about 81 %** (p. 5; Table 6, p. 8).
  - The validation section (p. 7) reports **99.81 mol% at about 25 % recovery**. The PSA outlet is given as 99.9 mol% at about 21 bar (p. 6), 99.81 mol% at about 1 bar (p. 8) and 99.97 mol% at about 20 bar (p. 12). **These are inconsistent.**
  - A feed of 231 kmol/h cannot match a 5,726 kg/h H2 product, which is about 2,840 kmol/h H2 (my calculation). The PSA feed figure therefore looks wrong or refers to something else.
- **Compression (Unit 300)**: three stages, centrifugal, with intercooling (25 °C cooling water, p. 9).
  - Pressure ratio about 1.75 per stage. Maximum outlet temperature 147.29 °C.
  - Peak isentropic efficiency 80 % (Tables 4 and 7, p. 6 and 9).
  - Three stages at 1.75 give 5.36 overall. That is consistent with 20 → 104 bar but not with 1 → 104 bar (my check).
- Hydrogen product: **137.42 t/d** (Table 3), equal to **5,726 kg/h** (Table 7). The text also gives about 5,710 kg/h (p. 13).
- **Yield**: the paper reports "0.78 kg H2 per kg NH3". This is physically impossible: the stoichiometric maximum is 0.1776 kg H2/kg NH3. The figure must mean the fraction of theoretical H2 recovered. Check: 137.42/177.6 = 0.774 (my calculation). Table 10 labels it correctly as "kg H2/kg H2 in NH3 feed".

## Governing equations
- **Eq. (1)** (p. 2): 2NH3 → N2 + 3H2, with ΔH = 92.4 kJ/mol. The value is per mol of reaction as written, i.e. 46.2 kJ/mol NH3.
- **Eq. (3)** (p. 5), conversion: α_NH3 = (F_H2 − F0_H2) / (1.5·F0_NH3).
  - F0_H2 is the inlet H2 molar flow, F_H2 the outlet H2 molar flow and F0_NH3 the inlet NH3 molar flow, all in mol/s.
- **Eq. (4)** (p. 5), rate law as printed: r = α·(P_NH3² / P_H2³)^β, with "β = 0.5".
  - The text then says "α was taken as **0.209**" and that this gives apparent orders of **0.418 for NH3 and −0.627 for H2**. Those orders actually correspond to **β = 0.209**, not to α (0.418 = 2×0.209; 0.627 = 3×0.209).
  - The validation section (p. 7) gives "Ea = **95.6 kJ mol⁻¹**, **β = 0.21**".
  - **Eq. (4) has no Arrhenius term and the pre-exponential factor is never reported.** The units of r and P are not stated.
  - The kinetic source is given as Ref. [6] (Ertl 2008 Nobel lecture, which is not a kinetics dataset) on p. 4-5, and as Ref. [4] "Spatolisano et al. 2023" on p. 7-8. **The rate law cannot be reproduced from this paper.**
- **Eq. (5)** (p. 6), compressor part-load efficiency: η(Q) = η_max·exp[−((Q − Q_design)/(σ·Q_design))²], with η_max = 0.8 and σ = 0.2.
  - Q is the throughput and Q_design the design throughput.
  - The paper says this is "consistent with manufacturer performance maps [18,19]" (MAN ES 2022; Siemens Energy 2023). In effect it is a modelling assumption.
- **Eq. (6)** (p. 6), LCOH: LCOH = (CAPEX·CRF + OPEX + C_el + C_NH3) / m_H2.
  - CAPEX is in €; CRF is the capital recovery factor (0.10); OPEX is annual O&M in €/y; C_el is the annual electricity cost in €/y; C_NH3 is the annual NH3 cost in €/y; m_H2 is in kg/y.
- **Eq. (7)** (p. 6): m_H2 = ṁ_H2·8760·A, with ṁ_H2 in kg/h and availability A = 0.9.
- **Eqs. (8)-(11)** (p. 10), tank heat ingress: Q_in = ΔT·(U_side,liq·A_side,liq + U_side,vap·A_side,vap + U_top·A_top + U_bot·A_bot).
  - A_side,liq = π·D·h; A_side,vap = π·D·(H − h); A_top = A_bot = π·D²/4. The π symbols are lost in the text extraction, and the image form is consistent with this reading.
  - BOG flow = boil-off rate × liquid NH3 in the tank.
  - **No U values are given.**

## Techno-economic inputs (Table 9 p. 13; Table 10 p. 14; §2.6, §3.3). EUR, 2025-2026 market basis; the cost year is not stated explicitly
| Item | Value | Note |
|---|---|---|
| Project lifetime | 20 yr | "conservative" (p. 13) |
| Plant availability | 90 % | [11] |
| CRF | 0.10 (stated directly; **no discount rate given**) | p. 6 |
| Specific CAPEX range | 385-900 €/(kg H2·day⁻¹) | Table 9 |
| Base-case CAPEX | **€642.7 million** | p. 14 |
| Electricity | 0.10 €/kWh (100 €/MWh), European industrial | p. 14 |
| NH3 price | 0.90 €/kg (Table 9); "0.9-0.5 €/kg" from S&P Global Q3 2025 [22] (p. 14); **0.626 €/kg** (Table 10) | inconsistent |
| O&M (excl. electricity) | 10 % of electricity cost | Table 9 |
| Exchange rate | 1 € = 1.09 $ | Table 9 |

- No equipment-level CAPEX breakdown, cost correlation, scaling exponent or catalyst price/lifetime is given.

## Economic results
- **LCOH = €8.36/kg H2** at nominal capacity, with CAPEX €642.7 M as the base case (p. 14; Table 10).
- The abstract gives a range of 4.8-9.0 €/kg. Low CAPEX with 0.5 €/kg NH3 gives about **4.78**; the CAPEX upper bound gives about **9.04 €/kg** (p. 14; Fig. 15).
- Text breakdown (p. 14): feedstock about 48 %, CAPEX about 47 %, electricity about 5 %, OPEX below 1 % (Fig. 16).
  - p. 15 instead says feedstock makes up "nearly half ... (≈ 78 %)". **This is inconsistent.**
- Per kg H2, the text gives feedstock **€6.56/kg H2** (at 0.9 €/kg NH3), OPEX 0.28 and CAPEX 1.4 (p. 14, garbled sentence).
- Table 10 gives a different set:

| Table 10 item | Value |
|---|---|
| Feed cost | 2.74 €/kg H2 |
| Effective CAPEX | 2.73 €/kg H2 |
| Electricity | 0.113-0.133 €/kg H2 |
| O&M + cooling | 0.028 €/kg H2 |
| Marginal cost excl. CAPEX (high end) | 6.96 €/kg H2 |
| Total | 8.36 €/kg H2 |

  - The Table 10 components (2.74 + 2.73 + 0.133 + 0.028 ≈ 5.63) **do not sum to 8.36** (my arithmetic).
  - Consistency check (my calculation):
    - CAPEX × CRF / annual H2 = 64.27 M€ / (5,726 kg/h × 8,760 × 0.9 = 45.1 Mkg) = **1.42 €/kg**. This matches the text value of 1.4, not Table 10's 2.73.
    - Feed at 0.9 €/kg: 900,000 €/d / 137,420 kg/d = **6.55 €/kg**. This matches 6.56.
    - The sum 6.56 + 1.42 + 0.13 + 0.03 ≈ 8.1 is close to 8.36.
    - At 0.626 €/kg NH3 the feed cost would be 4.56 €/kg, not 2.74.
    - €642.7 M / 137,420 kg/d = 4,677 €/(kg/d), **outside** the stated 385-900 €/(kg/d) range.
- Sensitivity (p. 14): ±10 % NH3 price changes LCOH by ±0.27 €/kg H2, which the paper calls about 10× the effect of electricity or CAPEX. The ±0.27 figure is not consistent with 6.56 €/kg × 10 % = 0.66.

## Energy results
- Unit 200 electricity is **833 kW** (Table 3) or **836 kW** (Table 6). Table 6 gives SEC 0.175-0.146 "kW/kh H2" (sic).
- Overall SEC is **1.12 kWh/kg H2 at 100 % load and 1.32 at 50 % load** (p. 14). The abstract and conclusion give 1.1-1.3 kWh/kg.
  - Other statements conflict: "7.54 kWh/kg" overall (p. 9 §3.1.4); compressor SEC "7.5 kWh/kg at optimal load to 13.6 at 50 %" (p. 6); and "compression ≈ 93 % of plant electricity" (p. 9). **Mutually inconsistent.**
  - Check (my calculation, ideal gas): 3 stages at a pressure ratio of 1.75, inlet 30 °C, cp(H2) about 14.3 kJ/(kg·K), γ about 1.41.
    - Isentropic work is about 0.64 kWh/kg H2, or about 0.8 kWh/kg at 80 % efficiency.
    - This is consistent with the 1.1-1.3 kWh/kg total, but not with 7.5 kWh/kg.
- Thermal efficiency: about **88 %** with heat recovery (p. 8, Unit 200) vs **about 68 % LHV** for the overall plant (p. 9).
- Benchmark claims (p. 7): Topsoe H2Retake about 96 % LHV efficiency at about 75 kt H2/yr [12]; KBR H2ACT single-train capacity 1000-1200 MTPD NH3 [13]. Both are vendor white papers.
- Off-design results (Table 8, p. 11):

| Feed (kg/h) | Electricity (kW) | Conversion (%) | H2 yield (mass-based, %) | Chamber T (°C) | Stack T (°C) | Cooling water (m3/h) |
|---|---|---|---|---|---|---|
| 25,002 | 500.7 | 100 | 77.91 | 509.3 | 235.2 | 87.08 |
| 29,169 | 584.4 | 100 | 77.91 | 509.1 | 235 | 101.6 |
| 33,336 | 667.1 | 100 | 77.91 | 509.4 | 233 | 116.1 |
| 37,503 | 751.6 | 99.99 | 77.91 | 509.9 | 235 | 130.6 |
| 41,670 | 835.6 | 99.97 | 78.08 | 506 | 230 | 145.1 |
| 45,837 | 920 | 99.93 | 77.85 | 513.00 | 239.9 | 160 |

## Environmental
- Table 11 (p. 15) quotes CO2 intensities from the literature; these are not this paper's results:
  - Coal gasification: 11-12 kg CO2/kg H2 (95-105 g/MJ; 0.34-0.37 t/MWh) [1,2].
  - SMR: 8.5-9.5 kg CO2/kg H2 (70-85 g/MJ; 0.25-0.30 t/MWh) [3,4].
  - Fossil-ammonia reformation: 9-10 kg CO2/kg H2 (75-90 g/MJ; 0.28-0.32 t/MWh) [5].
- For "this study (green ammonia cracking)" the paper assumes about 0 emissions. That gives **0.27-0.36 t CO2/MWh H2 avoided** (calculated by the authors).
- **No LCA was performed.** The boundary implicitly covers only direct process CO2. Upstream NH3 production, electricity emissions and NOx/N2O are not counted.
- The cited references [1-5] in the reference list are mostly not emission-factor sources (e.g., an Ursua electrolysis review and Ertl's Nobel lecture). Treat these intensities as unverified.

## Limitations / reliability
- There are **many internal inconsistencies**: reactor pressure, conversion, PSA purity and recovery, delivery pressure, BOG rate and compressor duty, SEC, the LCOH breakdown, NH3 price, and the CAPEX range vs the base case.
- The kinetic parameters cannot be reproduced. There is no pre-exponential factor, α and β are confused, and the kinetic sources are dubious.
  - Ref. [4] is listed as "A. Spatolisano, S. Dell'Era, F. Mazzocchia, IJHE 48(6) 2023 2211-2223". This **could not be matched** to the known Spatolisano et al. 2023 paper (Ind. Eng. Chem. Res. 62:10813). **Verify before citing.**
- The reference list has no DOIs, and several vendor white papers are cited.
- No equipment-level CAPEX, no discount rate (CRF only), no catalyst cost or lifetime, no NOx analysis, no LCA.

## Relevance to AmCraX
- Its main value is as a **large-scale (1000 t/d NH3) contextual benchmark**: an LCOH of about 4.8-9.0 €/kg H2 (base 8.36 €/kg) at 0.10 €/kWh and 0.5-0.9 €/kg NH3, with NH3 feedstock as the dominant cost.
- It also shows a fired Ni tubular cracker in which the PSA tail gas covers the furnace duty at full load, with an NH3 slipstream at part load. This matches the AmCraX tail-gas burner concept.
- The part-load compressor η(Q) Gaussian (Eq. 5) could be reused, labelled as an assumption-grade correlation.
- **Do not use its kinetic parameters, its SEC or its Table 10 breakdown as validation targets** without flagging the inconsistencies above.
- Use for qualitative trends: part-load behaviour and feedstock dominance.
