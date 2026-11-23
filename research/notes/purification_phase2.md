# Hydrogen purification evidence, Phase 2 (PSA against Pd-Ag membranes; readiness by configuration)

Workstream D1. Access date 23 November 2026. Data: `research/data/purification_literature.json` (entries P, M, L, S; ranges block) and `research/data/membrane_trl.json`. References: `research/reference_additions/phase2_purification.json`. Phase 1 context: `docs/internal/research_reports/purification.md`.

## 1. Result in one paragraph

The Phase 1 membrane case needed an ideal H2/N2 selectivity of at least 12,919 (300 ppm N2) and found no sourced value. One is now sourced: Cechetto et al. (2021) measured ideal H2/N2 above 500,000 and above 400,000 (two sealing methods) at 450 degC on a new Pd-Ag double-skin membrane, with H2 purity 99.980 to 99.995 % in a working membrane reactor and 600 h of stable operation. That removes the "no source" objection, but only for new membranes, single gas, one research group, and not for NH3 at percent level. The PSA side did not improve: no cracked-ammonia PSA recovery at 99.9 % or Grade D purity was found in a source that could be read. The one clean recovery-purity pair (Yanez 2020) is for ammonia-plant purge gas and gives 55.5 % at 99.97 % and 75.3 % at 99.25 %, which is far below the Phase 1 PSA recovery assumption (0.85) and below its bounds (0.71, 0.751) at Grade D. The Phase 1 reading "partly supported or inconclusive" for H4 stands; the Phase 1 PSA recovery assumptions are, if anything, optimistic at Grade D.

## 2. Pd and Pd-Ag membranes (task item 1)

| Quantity | Value | Source | Grade |
|---|---|---|---|
| H2 permeance, 450 degC, 4.61 um Pd-Ag | above 1.5e-6 mol m-2 s-1 Pa-1 | Cechetto 2021, p. 4 | measured short-term |
| N2 permeance, 450 degC | 3e-12 and 3.7e-12 mol m-2 s-1 Pa-1 | same | measured short-term |
| Ideal H2/N2 | above 500,000 (dead end), above 400,000 (double sealed) | same | measured short-term |
| Stability | about 600 h at 450 degC, 3 bar(a), no loss of purity or recovery | same, Fig. 9 | measured long-term (discontinuous) |
| Purity / recovery | 99.995 % H2, NH3 2.9 ppm; 90.5 % recovery at 5 bar, 450 degC | Cechetto 2023 review, Tables 8, 10 | measured short-term |
| NH3 effect | no flux inhibition at 450 degC with 200-500 ppm NH3; inhibition at lower T (about 36 % loss after 20 h at 300 degC, secondary excerpt) | Peters 2016 | measured short-term |
| Temperature window | above 300 degC (embrittlement below 300 degC and 2 MPa for pure Pd); 500 degC upper limit | Cechetto 2023 review | review statement |
| Pressure exponent | 0.5 (Sieverts) | Di Marcoberardino 2019 Table 4; Richard 2024 | modelled |
| Membrane cost | 5,000 to 15,000 USD/m2 (10,000 used); 6,800 EUR/m2 derived (ceramic, 2017 data); 9,300 to 11,200 EUR/m2 (steel); 6,000 EUR/m2 in Phase 1 | Sweeney 2023; Di Marcoberardino 2019; Richard 2024 | modelled |
| Lifetime | 2-3 years (literature), 3 years or 5 years (assumed); measured: 600 h lab, 2,068 h system (Ammogen); over 6,000 h for Pd in natural-gas reforming (secondary excerpt) | see data file | assumption / measured |

Notes:
- The permeance in Cechetto 2021 is printed per Pa. The paper's text does not state the pressure exponent. A Sieverts cross-check (data file P11) shows the Richard 2024 fit and the Cechetto lower bound agree in magnitude (about 0.6 to 0.74 mol m-2 s-1 at 5 bar feed and 1 bar permeate), but the check assumes n = 1 for the second value, so treat it as a plausibility test only.
- Text extraction of the PDF lost the minus signs of the N2 permeance exponents. The exponent -12 is inferred from the stated ratios (1.5e-6 / 3.7e-12 = 4.05e5 reproduces "above 400,000"). Check against the PDF before quoting.
- Not found: mixed-gas H2/N2 selectivity as a number, selectivity decay rate in cracked ammonia, a measured degradation rate, sealing lifetime, NH3 inhibition at percent level, a supplier price with year. A table quoting selectivity decay from 6000 to 4300 and 4300 to 1000 in about 1000 h appeared only as a search excerpt and is not used.
- The DOE document (OSTI 1460402) was too large for the fetch tool; its numbers are secondary and flagged.

## 3. Technology readiness by configuration (task item 2)

| Configuration | TRL | Evidence | Commercial or emerging |
|---|---|---|---|
| PSA on cracked ammonia | PSA unit 9; integrated cracker + NH3 wash + PSA at fuel-cell grade 6 to 7 | AEA: PSA mature for 99.97 %; Air Liquide pilot at Antwerp (no numbers); Air Products Rotterdam design (planned); Topsoe/KBR plants are for uses without purification | PSA component commercial; integrated fuel-cell-grade chain not shown at scale |
| Pd-Ag membrane separator downstream of a cracker | 4 to 5 | Lab permeation (Cechetto 2021); Ammogen had an optional 40 barg membrane separator but did not need it; CSIRO/Fortescue downstream purifier is vanadium-core, not Pd-Ag, so excluded | emerging |
| Pd-Ag membrane reactor | 7 (project report) / 6 (same company, grant text) | Ammogen: 2,068 h, 5,289 kg H2 (about 61 kg/day mean, derived), 375-450 degC, 2-8 barg, purity at least 99.98 %, conversion above 99.5 %; 200 kg/day, over 97 % recovery and cost KPIs not met; TRL 8 needs a commercial off-taker | emerging, pre-commercial |
| CSIRO V-core Pd-coated purifier (contrast only) | 6 | 5 / 40 / 200 kg/day steps; 200 kg/day status unconfirmed | emerging |

Plain statement: what is commercially demonstrated is PSA for N2/H2-rich gas and the cracker itself in large fired units (Topsoe Arroyito, 2,400 t NH3/day, no purification). Pd-Ag membrane reactors have a roughly 60 kg/day pilot that missed its rate and recovery targets. Pd-Ag as a stand-alone downstream separator on cracker effluent is laboratory-level in the evidence found. The details and caveats are in `membrane_trl.json`.

## 4. PSA for cracked ammonia (task item 3)

- Recovery against purity: Yanez 2020 (ammonia purge gas, 9 bar, 5A, 4 columns): 75.3 % at 99.25 %, 55.5 % at 99.97 %. Cho 2026 (from Yanez as cited): 75.6 % at 99.11 %. Hansen 2024 quoting Cha 2021: 71 % at 99 %, activated carbon, 2.5 bar. Lee 2023: 79 % fixed, not computed. Mehr 2026: 99.96 % at about 81 %, but the paper is internally inconsistent (also 99.81 % at about 25 %), so low confidence.
- At 99.9 %: no source; interpolation of the Yanez pair gives about 57 % (different feed). At Grade D: low 55.5 %, high 81 % (low confidence), central none.
- Abdoos et al. (2025, doi 10.1016/j.cej.2025.170994) is the most relevant recent PSA design paper found. A search-result summary quoted about 99.99 % purity, about 77 % recovery and about 5.2 MJ/kg, but I could not confirm these (publisher blocked); they are not entered. This is the first thing to obtain.
- "Deka et al. 2025": no record found in this search. The Phase 1 library also lists it as unread.
- NH3 upstream: water wash column with distillation and recycle (Air Liquide process page); adsorbent beds or TSA (reviews: clinoptilolite to below 0.025 ppm, zeolite 13X to below 0.75 ppm). Measured NH3 after a full cracker wash/TSA/PSA train: not found.
- Power: no verified PSA-only specific power. Mehr 2026 SEC (1.12 kWh/kg total plant) is inconsistent with the same paper's compressor figures; not used.
- Cost: no sourced PSA unit cost beyond the Cho 2026 figure in the library (0.084 USD/kg for T/PSA CAPEX, about 82 kg/h, Phase 1 note).
- Commercial references: Air Products (Rotterdam design, 99.97 mol %, tail-gas compressor recycle), Air Liquide (Antwerp pilot), KBR (H2ACT, PSA in the process). None gives recovery or power.

## 5. Low, central, high (task item 5)

| Quantity | Low | Central | High | Basis |
|---|---|---|---|---|
| Pd-Ag H2 permeance, 400-500 degC (mol m-2 s-1 Pa-1, permeate 1 atm) | 1.5e-6 (a lower bound) | null | null | P01; Sieverts model 1.89e-3 mol m-2 s-1 Pa-0.5 at 450 degC (P10, modelled) |
| Ideal H2/N2 selectivity | 6,000 | 400,000 | 500,000 | P13 (secondary), P05, P04; new membranes, single gas, all lower bounds |
| Membrane lifetime (years, assumed) | 2 | 3 | 5 | L01, L02, L03/L04; measured: 600 h, 2,068 h (system) |
| Membrane cost | 6,800 EUR/m2 | 10,000 USD/m2 | 15,000 USD/m2 | M03, M01, M01; currencies not converted here |
| PSA recovery at 99.9 % | 57.4 % (derived) | null | null | S02 |
| PSA recovery at Grade D | 55.5 % | null | 81 % (low confidence) | S01, S06 |
| PSA specific power (kWh/kg H2) | null | null | null | no verified source |

## 6. Gaps and what could not be verified

1. Abdoos 2025 (and any other recent cracked-ammonia PSA paper): abstract and numbers not obtained.
2. Mixed-gas H2/N2 selectivity of Pd-Ag in cracker effluent, and its change over time; NH3 inhibition at percent level; Ag/Pd attack by NH3 over thousands of hours.
3. Per-membrane lifetime, replacement interval and degradation rate from a measured source (no source beyond about 2,000 h for a system and 600 h for a lab reactor).
4. A dated supplier price for Pd-Ag membranes; all prices are literature or model values.
5. Ammogen: achieved H2 recovery number (the report says only that the KPI was not met).
6. DOE report 1460402 and the 2019 membrane-reformer review table: not opened. Patent and permitting excerpts: not opened.
7. CSIRO/Fortescue 200 kg/day pilot outcome: no source found after 2023.
8. The NUS researchers: no relevant quantitative work (see `nus_membrane_researchers.md`).

## 7. Consequences for the other workstreams (for the orchestrator)

- The H4 membrane case may now cite a sourced selectivity lower bound (400,000, ideal, 450 degC, new membrane) but should keep the condition "new membrane, single gas". The required selectivity of 12,919 corresponds to a factor of about 30 below that value.
- PSA recovery at Grade D of 0.71 to 0.751 and the base 0.85 are not source-supported; the only sourced Grade D point is 0.555 (purge-gas feed) with one low-confidence model at 0.81. A sensitivity at 0.555 would show the membrane advantage widening, but this rests on one feed composition that differs from cracked ammonia.
- Membrane cost: Phase 1 used 6,000 EUR/m2 at parity as USD. The literature range is 5,000 to 15,000 USD/m2; the Phase 1 sensitivity (x0.5 to x2) covers it.
- TRL wording: do not write "Pd-Ag membranes are at TRL x". Use the table in section 3.
- Ammogen did not meet its rate and recovery targets; a favourable membrane cost per kg that assumes 0.90 recovery is not supported by the demonstration.
