# maccarrone2025comprehensive

## Bibliographic data
- Authors: Domenico Maccarrone, Cristina Italiano, Gianfranco Giorgianni, Gabriele Centi, Siglinda Perathoner, Antonio Vita, Salvatore Abate
- Title: A Comprehensive Review on Hydrogen Production via Catalytic Ammonia Decomposition
- Journal: Catalysts (MDPI), 2025, vol. 15, issue 9, article 811, 41 pp. Received 19 Jul 2025, published 26 Aug 2025 (p. 1). Open access, CC BY 4.0.
- DOI: 10.3390/catal15090811 (verified: doi.org handle API responseCode 1, resolves to https://www.mdpi.com/2073-4344/15/9/811)
- APA 7: Maccarrone, D., Italiano, C., Giorgianni, G., Centi, G., Perathoner, S., Vita, A., & Abate, S. (2025). A comprehensive review on hydrogen production via catalytic ammonia decomposition. *Catalysts, 15*(9), 811. https://doi.org/10.3390/catal15090811
- Type: review. Almost every number in it is quoted from other papers. The original source is given for each item below. The review's own contribution is the WHSV normalisation (per g catalyst and per g metal), productivity columns and the comparison tables.

## Scope
Thermodynamics (Section 2, pp. 3-5), Ru catalysts and non-Ru catalysts (Section 3, pp. 6-19, Tables 1-3), kinetic models (Section 4, pp. 19-21, Tables 4-5), reactors (Section 5, pp. 21-33: packed-bed, PBMR, CMR, microreactor, proton-conducting membrane, plasma, electro- and photocatalytic), economics (Section 6, pp. 33-34) and an industrial overview (Section 7, pp. 34-35).

## Thermodynamics (pp. 3-5)
- Reaction (Eq. 1, p. 3): NH3 -> 3/2 H2 + 1/2 N2. The paper prints dH deg = +45.984 kJ mol-1 NH3, dS deg = +99.046 "J/K" and dG deg = +16.610 kJ mol-1 NH3. The dS unit is printed as J/K and is presumably J mol-1 K-1 per mol NH3. **Consistency check (AmCraX, not from the paper):** 45.984 - 298.15 x 0.099046 = 16.45 kJ/mol, not 16.610. The printed values are internally inconsistent by about 0.16 kJ/mol. No source is cited for them.
- Ideal-gas equilibrium (Eq. 2, p. 4): Kp = (yN2 Ptot)^0.5 (yH2 Ptot)^1.5 / (yNH3 Ptot) = yN2^0.5 yH2^1.5 / yNH3 * Ptot. The paper states that the ideal-gas assumption is valid for 1-20 bar [33 = Shacham & Brauner 2015]. The pressure unit and standard state are not stated explicitly (presumably bar or atm).
- Kp(T) correlations as printed (p. 4). All three have typographical problems:
  - Eq. 3, attributed to Yin et al. 2004 [36] (the text also cites [34]): Kp = exp[(40100 - 25.46 T log T + 0.00917 T^2 - 103000/T + 64.81 T)/(R T)]. As printed the exponent has no minus sign. The bracket is dG deg(T) in J/mol (log = ln). The correct form is almost certainly Kp = exp(-dG/RT). AmCraX check: this form gives Kp = 2.97 (500 K), 102 (700 K) and 647 (873 K), which matches Fig. 1a.
  - Eq. 4, attributed to Shacham & Brauner 2015 [33], based on synthesis data at 30 bar: Kp = 1 / 10^[2.10 + (1/4.571)(9591/T - 0.00046 T + 0.85e-6 T^2) - (4.98/1.985) log10 T]. The bracketing in the PDF is ambiguous. The reading given here reproduces Kp = 3.01, 105 and 663 at 500, 700 and 873 K (AmCraX check).
  - Eq. 5, attributed to Wang et al. 1999 [35]: printed as Kp = 1/(2250.322/T - 0.85340 - 1.52049 log T - 2.58987e-4 T + 1.48961e-7 T^2). Read literally this gives a **negative** Kp. Reading the bracket as log10 of the synthesis constant, i.e. Kp = 10^-(...), gives 3.54, 118 and 726 at 500, 700 and 873 K, consistent with the other two correlations. Check against Wang, Padban, Ye, Andersson & Bjerle (1999), *Ind. Eng. Chem. Res.* 38, 4175, before using it.
- Statements (pp. 4-5): the Wang correlation is valid for 500-1300 K, with an average deviation of 0.00055 and a maximum of 0.0016 (the review cites [36] for this, but the context implies [35]). dG < 0 above 450 K (text says "the equilibrium constant becomes negative", meaning dG; Fig. 1b). At 1 bar with pure NH3 the equilibrium conversion "approaches completion around 550 K, with the inflection point ... at 350 K" (Fig. 2, read qualitatively). Conversion decreases with pressure (Fig. 3a) and increases with inert dilution (Fig. 3b). The figures give no tabulated values.
- Typical operation: 400-700 deg C (p. 2), above 400 deg C and near atmospheric pressure (p. 4).

## Mechanism (pp. 6-7)
Elementary steps, Eqs. 6-11 (* = site): NH3 + * <-> NH3*; NH3* <-> NH2* + H*; NH2* <-> NH* + H*; NH* <-> N* + H*; 2N* <-> N2 + 2*; 2H* <-> H2 + 2*.
- Rate-determining step: N2 desorption on Ru, Ni, Co, Fe and Cr; N-H cleavage on Rh, Ir, Pt, Pd and Cu (p. 6, citing [43] Tehenics 2020, a BSc thesis).
- Ru/C12A7:e-: Ea of N2 desorption is 64 kJ/mol against an overall Ea of 55 kJ/mol, which suggests N-H cleavage is rate-limiting on this catalyst (p. 6, [37] Hayashi et al. 2013).
- B5 sites: optimal Ru particle size 1.8-3 nm (p. 6, [15,41,45]). Ru/MgO(111) has an Ea of 71 kJ/mol against 119 kJ/mol for MgO(100), by TPSR (p. 9, [14] Fang et al. 2023).
- Table 1 (p. 7): % d-character from Ganley et al. 2004 [42]: Ru 50, Ni 40, Rh 50, Co 39.5, Ir 49, Fe 39.7, Pt 44, Cr 39, Pd 46, Cu 36, Te/Se/Pb 0.

## Kinetic models (Section 4, pp. 19-21). Verified against the rendered PDF.
- Eq. 12, Temkin-Pyzhev (cited to [44,65,72]): r = k_app [ (p_NH3^2 / p_H2^3)^beta - (p_N2 / K_eq^2) (p_H2^3 / p_NH3^2)^(1-beta) ]
- Eq. 13: k_app = k0,app exp(-E_app / (R T)), with R = 8.314 J K-1 mol-1.
- Eq. 14, power law (used at atmospheric pressure, [61]): r = k p_NH3^alpha p_H2^gamma
- Table 4 rate laws:
  1. -r_NH3 = k_dec p_NH3 / p_H2^1.5 ([14] Fang et al. 2023)
  2. -r_NH3 = k p_NH3^alpha p_H2^gamma [1 - (1/K_eq) (p_H2^3 p_N2 / p_NH3^2)] ([61] Sayas et al. 2020, Ru-K/CaO, high pressure). As printed, the reverse term uses the stoichiometry 2NH3 = N2 + 3H2, so K_eq here is the equilibrium constant per 2 mol NH3 (= Kp(per mol)^2). The paper does not state this; it is an inference.
  3. r = kf (p_NH3^2 - p_H2^3 p_N2 / kp) / (p_H2^1.5 + sqrt(kn * p_NH3^2))^2 ([10] Itoh et al. 2014, Langmuir-Hinshelwood, N2 desorption RDS, N* most abundant species). Units (p. 20): kf in "mmol s/(kg_cat MPa)" as printed (probably a misprint for mmol/(s kg_cat MPa); the dimensions do not close), kn in MPa, kp in MPa^2. **The review gives no numerical values for kf, kn or kp.**
- Table 5 (p. 20), "Estimated modeling parameters based on the Temkin-Pyzhev model". Values copied exactly:

| Catalyst | Load % | E_app kJ/mol | T deg C | K0,app | alpha | beta | gamma | RDS | Original source |
|---|---|---|---|---|---|---|---|---|---|
| Ru/Al2O3 | 8.5 | 117 | (blank) | 1.5 x 10^-9 mol m-3 s-1 | - | 0.27 | - | N2 desorption | Di Carlo et al. 2014 [65] |
| Ru/C12A7:e- | 2.2 | 22.1 | 600 | - | 0.9 | - | 0.04 | N2 desorption | Hayashi et al. 2013 [37] |
| Ru/C12A7:O2- | 2 | 24.6 | 600 | - | 0.4 | - | 0.14 | N2 desorption | [37] |
| Ru-K/C | 2.7 | 41.8 | 600 | - | 0.58 | - | 0.15 | N2 desorption | [37] |
| Ru-10%K/CaO | 3 | 111 | 350 | 8584.8 mol gcat-1 s-1 | 0.5 | - | -1.2 | N2 desorption/N-H cleavage | Sayas et al. 2020 [61] |
| Ni/Ba-Al-O | 20 | 76.5 | 450 | - | 0.47 | - | -0.32 | H2 desorption | Im et al. 2020 [39] |
| Ni/Sr-Al-O | 20 | 81.1 | 450 | - | 0.58 | - | -0.38 | H2 desorption | [39] |
| Ni/Ca-Al-O | 20 | 87.2 | 450 | - | 0.70 | - | -0.42 | H2 desorption | [39] |
| Ni/Mg-Al-O | 20 | 89.3 | 450 | - | 0.39 | - | -0.62 | H2 desorption | [39] |

  Caveats. The K0,app values have inconsistent and probably wrong units: 1.5e-9 mol m-3 s-1 is implausibly small for a pre-exponential factor, and the pressure units are not given. The C12A7 E_app values (22-42 kJ/mol) are far below the 55 kJ/mol quoted on p. 6 for the same catalyst. The "T" column appears to be the temperature at which the orders were measured. **Do not use the K0,app values in a rate model without the original papers.** Alpha and gamma are usable as reaction orders with their source cited.
- Text (p. 20): Sayas et al. orders alpha ≈ 0.5 and gamma ≈ -1.2, "in excellent agreement with Temkin-Pyzhev". Hayashi et al.: Ru/CaO and Ru/Al2O3 alpha ≈ 0.4 with large negative gamma (strong H2 inhibition). Im et al. (Ni): H2 desorption is the RDS and the N2 partial pressure has a negligible effect.

## Catalyst performance (Tables 2 and 3, pp. 12-18). Benchmark data, all quoted from the original papers.
WHSV is in NmL NH3 per g catalyst per hour (the review stresses that WHSV is not GHSV). Selected rows at P = 1 bar and 100% NH3 feed unless noted:
- Ru/MgO(111) 3%: 30,000 NmL/(gcat h), 425 deg C, 99% conversion [14] Fang 2023 (p. 12)
- Ru/Al2O3 4.7%: 30,000, 500 deg C, 85% [41] Zheng 2007
- Ru/Al2O3 8.5% (commercial) [65] Di Carlo 2014, WHSV 286: at 500 deg C 99.7% (1 bar), 98.5% (5 bar), 97.2% (10 bar); at 1 bar, 450 deg C 99.5% and 400 deg C 99.1% (p. 12). The row layout is complex; reading from the PDF is recommended.
- Ru-10%K/CaO 3% [61] Sayas 2020, WHSV 9000 (from row grouping), 500 deg C: 98% (1 bar), 80% (10 bar), 65% (20 bar), 60% (40 bar) (p. 13). This is the only high-pressure series and is directly relevant to the 20 bar AmCraX baseline.
- Ru/C12A7:e- 2.2%: 15,000, 400 deg C 70%, 460 deg C 99% [37]
- Ru/MgO 3%, DP/CP/WI [52] Fujitani 2020: WHSV 15,000; 400 deg C 60/62/17%; 500 deg C 99/99/90% (pp. 8, 14)
- Ru/Mg-Al monolith 0.025%: WHSV 9, 625 deg C, 98% [66] Koo 2024
- Ni/Ba-Al-O 20%: WHSV 6000, 550 deg C, 90.3%; Ni/Sr 78.8%, Ni/Ca 62.2%, Ni/Mg 38.8% [39] Im 2020 (Table 3, p. 18)
- Ni/CeO2 10% (44% NH3 feed): 13,800, 450 deg C, 62% [64]
- Fe3O4@CeO2: 24,000, 600 deg C, 88% [75]; MoN@C 25.9%: 15,000, 625 deg C, 100% [76]

## Membrane reactors (pp. 21-28)
- Driving force: dP_H2 = p_H2,ret - p_H2,perm > 0 (p. 22). It is maintained by sweep gas or vacuum. **No Sieverts-law expression, exponent or permeance values are given in this review.**
- H2 recovery factor (Table 6, p. 23): HRF = H2,perm / (H2,perm + H2,ret) (based on H2 produced; [11,109]) or HRF = H2,perm / (1.5 NH3,feed) (based on theoretical H2; [10,101]).
- Pd membranes operate at 350-500 deg C ([129], p. 29). Embrittlement occurs below the operating range. Ag, Cu or Au alloying reduces embrittlement but lowers permeability (p. 29).
- Kinetic diameters (p. 26, [115]): H2 296 pm, NH3 326 pm, N2 345 pm.
- Compression energy (p. 24, Cerrillo et al. 2022 [11]): 6.0 kWh/kg H2 to pressurise H2 from 1 to 700 bar, equivalent to 1.3 kg CO2/kg H2. From 20 to 700 bar it is about 4.5 kWh/kg H2.
- Table 7 (p. 28, read from the rendered PDF). Selected rows:
  - #4 Ru/(La)Al2O3, Pd/Pd on Ta 1.5 um, 425 deg C, 5 bar, H2O/N2 sweep: X 99%, HRF 85% [110] Park 2020
  - #5 Ru/gAl2O3 commercial, Pd-Ag 4.6 um, vacuum, 472 deg C, 5 bar, WHSV 8520: X 99%, HRF 96.3%, purity > 99.99% (p. 24) [109] Kim 2022
  - #6 Pd-Ag 4.61 um, vacuum, 400 deg C, 5 bar, WHSV 120: X 99%, HRF 93.5% [120] Cechetto 2021
  - #1 Ba-CoCe with Pd-Au 8 um, vacuum, 485 deg C, 4 bar: X 99%, HRF 80% [11]
  - #10 Pd/Ru/YSZ 6 um CMR, 400 deg C, 5 bar, no sweep: X 98%, HRF 87.5%, purity 99% (p. 26) [114] Zhang 2019
  - #12 Jiang 2021 [112], 450 deg C, 7 bar: MFI 8 um X 98.6% / HRF 93.3%; Pd-Ag 1.8 um 95.45% / 91.4%; CMS 0.9 um 99.55% / 94.4%. Permeate purity (p. 24): CMS 95.98%, MFI 87.26%, Pd-Ag "almost 100%".
  - #13 Ru/SiO2 4.1 wt%, 50% NH3 feed, Pd 200 um, vacuum, 450 deg C, P printed as 10 bar: X 99%, HRF 60%, PP H2 6.463 [10] Itoh 2014. Inconsistencies: the text (p. 24) gives 75% -> 85% conversion and 60% recovery "at 400 deg C", and cechetto2023membrane (Tables 3 and 6) gives 1 bar reaction pressure for the same Itoh 2014 work.
  - #6 (Cechetto 2021 [120]) is printed at 5 bar. cechetto2023membrane gives 4 bar for the vacuum case with X 99.3% and HRF 93.5%. Use the cechetto2023membrane values, written by the original authors.
  - #11 Li 2012 [115] SiO2 CMR, vacuum, 10 bar as printed: at 450 deg C X 78% and HRF 72%; at 500 deg C X 99%.
  - The #12 mapping follows the column order of the membrane headers (MFI/Pd-Ag/CMS). It is consistent with the text: CMS has the highest HRF and Pd-Ag the highest purity.
  - The Table 7 PP H2 (purified productivity) unit is not stated in the table. The footnote defines it only as "moles of hydrogen produced ... collected at permeate side".

## Economics (pp. 33-34). All quoted.
- Devkota et al. 2024 [88]: LCOH $6/kg H2, ammonia is 62% of total expenditure, ROI > 23.7%. CO2: 1.11 (coal), 0.055 (solar), 0.014 (wind) kg CO2/kg H2.
- Kanaan et al. 2023 [147]: membrane reactor, large scale, LCOH $7.72/kg. Truck on-board alkaline electrolysis $9.67/kg. Small scale electrolysis $5.79/kg.
- Peng et al. 2023 [148]: thermocatalysis + PEM LCOE < $0.5/kWh. Electrolysis about $2.3/kWh. Plasma $2.1-6.3/kWh.

## Limitations
Secondary source with no new experiments. Several equations have typographical errors (Eqs. 3-5, and the units of the Itoh constants). Table 5 K0 units are inconsistent. Thermodynamic constants are uncited and slightly inconsistent. No permeation law or permeance data are given. No PSA data are given. Figures 1-3 are untabulated.

## Relevance to AmCraX
1. The Kp correlations are cross-checks for `amcrax.thermodynamics.equilibrium_constant` (use the corrected forms only as a check, and cite the originals [33,35]).
2. Reaction orders (alpha, gamma) and E_app for Ru-K/CaO (Sayas 2020) and Ni/Ba-Al-O (Im 2020) are candidate power-law kinetics for `amcrax.kinetics`, with the K0 values to be retrieved from the original papers.
3. The Sayas high-pressure series (1-40 bar, 500 deg C) supports the pressure sensitivity at the 20 bar baseline.
4. The HRF definitions and Table 7 benchmarks are relevant to the membrane option in `amcrax.separation`.
