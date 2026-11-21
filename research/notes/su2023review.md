# su2023review

## Bibliographic data
- Su, T., Guan, B., Zhou, J., Zheng, C., Guo, J., Chen, J., Zhang, Y., Yuan, Y., Xie, W., Zhou, N., Dang, H., Xu, B., & Huang, Z. (2023). Review on Ru-based and Ni-based catalysts for ammonia decomposition: Research status, reaction mechanism, and perspectives. *Energy & Fuels, 37*(12), 8099–8127. https://doi.org/10.1021/acs.energyfuels.3c00804
- Received 13 Mar 2023, revised 12 May 2023, published 26 May 2023 (p. 1).
- DOI verified: `https://doi.org/api/handles/10.1021/acs.energyfuels.3c00804` returned responseCode 1.
- Type: review. PDF `research/papers/ef3c00804.pdf` has 29 pages; PDF page N = journal page 8098+N.
- **All numbers in this review are quoted from primary literature.** The review's reference numbers are recorded below for tracing.

## Scope
The review covers:
- Ru- and Ni-based NH3 decomposition catalysts: preparation method, support and promoters (Tables 1–6).
- Rate expressions and mechanism, including the debate over the rate-determining step (RDS) (Section 3, pp. 16–19).
- Catalytic membrane reactors (p. 19 onwards).

Its stated target is complete conversion at about 30,000 mL·g_cat⁻¹·h⁻¹ at about 350 °C with affordable catalysts (abstract, p. 1).

## Rate expressions (Section 3.1, p. 16; checked against the rendered PDF page)
- (1) 2NH3 ⇌ N2 + 3H2
- (R1–R6) Stepwise mechanism, cited to ref 168, where * is a site:
  - NH3 + * ⇌ NH3*
  - NH3* + * ⇌ NH2* + H*
  - NH2* + * ⇌ NH* + H*
  - NH* + * ⇌ N* + H*
  - 2N* ⇌ N2 + 2*
  - 2H* ⇌ H2 + 2*
- (2) Empirical rate law, cited to ref 170 (Sun et al. 2022, Renew. Sustain. Energy Rev. 169, 112918):
  - r_NH3 = k·c^α(NH3)·c^β(H2)·c^γ(N2)
  - c are gas concentrations and α, β, γ are reaction orders, with α > 0 and β, γ < 0.
  - **No units or values are given.**
- (3) Arrhenius: k = A·exp(−Ea/RT), with R = 8.314 J mol⁻¹ K⁻¹.
- (4) Tamaru form, cited to ref 176 (Tamaru, K. 1988, Acc. Chem. Res. 21(2), 88–94):
  - r_NH3 = k_R·K·P_NH3 / (1 + K·P_NH3)
  - k_R [molecules cm⁻² s⁻¹] = 1.57×10²⁸ exp(−49600/RT)
  - K [Torr⁻¹] = 6.7×10⁻⁹ exp(39600/RT)
  - **Ambiguities:**
    - The energy unit of 49600 and 39600 is not stated. It is most likely cal/mol (Tamaru's convention), but this is unverified.
    - The metal or surface it applies to is not stated in the review.
    - The rate basis is per surface area (cm²), not per catalyst mass.
- (5) Power law: r_NH3 = k′·P_NH3^α·P_H2^β, with α and β the reaction orders of NH3 and H2. **No values are given.**
- (6) Labelled "Temkin–Pyzhev" and cited to ref 35 (Egawa et al. 1984):
  - r_NH3 = k0·exp(−E_app/RT)·P_NH3^α·P_H2^β
  - **Ambiguity:** as printed, this is an Arrhenius power law. It is not the classical Temkin–Pyzhev form r = k(p_NH3²/p_H2³)^β given by takahashi2016kinetic Eq. 26.
  - The two forms coincide only if α = 2β and the H2 order is −3β.
  - No values are given.

## Mechanism and RDS statements (pp. 17–19; all cited)
- Fang et al. 2022 (ref 46): N-recombination is the RDS at 300–500 °C. At higher T the RDS may switch to N–H cleavage (p. 17, Fig. 5b).
- Ganley et al. 2004 (ref 182): the RDS is N recombination on Ni and Fe, and N–H cleavage on noble metals (Ru, Pd, Rh) (p. 17).
- McCabe (ref 191): on Ni above about 1000 K, the RDS shifts from N2 desorption to NH3 adsorption (p. 18).
- Tsai & Weinberg (ref 190), on Ru(001): at low T, N2 desorption controls the rate; at high T, NH3 desorption competes with N–H scission (p. 18).
- Chellappa et al. 2002 (ref 194): no obvious H2 inhibition on Ni-Pt/Al2O3 (p. 18).
- Lucentini et al. 2021 (ref 172), Ni-Ru/CeO2:
  - NH3 dehydrogenation is the RDS, with H2 inhibition (p. 19).
  - **Activation energies range from 107 to 124 kJ mol⁻¹** across the Ni/CeO2–Ru/CeO2 span.
- Hayashi et al. 2013 (ref 77), Ru/C12A7:e⁻: **TOF ≈ 12 s⁻¹ at 400 °C** and **64 kJ mol⁻¹** activation energy for N2 desorption (p. 8).
- DFT (Fu et al., ref 207): Ni/Al2O3 barrier 1.483 eV vs 1.448 eV for CoNi/Al2O3 (p. 19).
- Ideal Ni particle size for Ni/MCM-41 is 3.1–3.6 nm (Duan et al., ref 200, p. 19). Ru B5 sites are optimal at about 1.8–3.0 nm hemispherical particles (Karim et al., ref 55, p. 17).

## Table 2 (p. 6) — Ru on different supports, selected rows (values as printed)
Columns: Ru wt %, T (°C), GHSV (mL_NH3·g_cat⁻¹·h⁻¹), X_NH3 (%), r_H2 (mmol·min⁻¹·g_cat⁻¹), TOF_H2 (s⁻¹), E_app (kJ/mol).

**Ref-column caveat.** In the rendered page the reference superscripts sit between rows, so a row-to-reference mapping can be off by one row. Trace to the primary paper before citing a row.

| Catalyst | Ru wt% | T °C | GHSV | X % | r_H2 | TOF s⁻¹ | E_app |
|---|---|---|---|---|---|---|---|
| Ru/MgO | 5.0 | 450 | 30,000 | 56.5 | 18.9 | – | – |
| Ru/MgO | 1.7 | 450 | 60,000 | 62.1 | 36.0 | – | – |
| Ru/ACX | 1.5 | 450 | 2000 | 95.8 | – | – | 76.6 |
| Ru/γ-Al2O3 | 4.7 | 400 | 30,000 | 17.6 | 6.11 | – | 90 |
| Ru/γ-Al2O3 | 2 | 400 | 15,000 | 13.2 | 3.6 | 1.0 | 86.0 |
| Ru/κ-Al2O3 | 1.0 | 400 | 60,000 | 41.0 | 7.0 | – | 65.9 |
| Ru/θ-Al2O3 | 1.0 | 400 | 60,000 | 40.1 | 6.9 | – | 98.2 |
| Ru/CeO2 | 2.0 | 400 | 13,800 | 77.0 | 11.9 | 1.8 | – |
| Ru/La2O3-700-i | 4.8 | 450 | 18,000 | 58.2 | 11.7 | 2.4 | 41.55 |
| Ru/Pr6O11 | 5.0 | 450 | 30,000 | 18.2 | 7.68 | 0.8 | 87.2 |
| Ru/Pr2O3 | 5.0 | 450 | 30,000 | 67.3 | 28.4 | 1.5 | 61.9 |
| Ru/Ba-ZrO2 | 3.0 | 450 | 30,000 | 23.6 | 7.9 | 5.2 | 92.1 |
| Ru/Y2O3 | 5.0 | 450 | 30,000 | 82.2 | 25.2 | 1.85 | 90.4 |
| Ru/BHA | 3.0 | 450 | 30,000 | 42.4 | 12.7 | 11.4 | – |
| Ru/CNTs | 3.2 | 450 | 6500 | 30.2 | 2.2 | 0.04 | – |
| Ru/CNFs | 3.2 (row blank, inherits) | 450 | 6500 | 77.6 | 5.6 | 0.16 | – |
| Ru/C12A7:e⁻ | 2.2 | 600 | 120,000 | 80.2 | 108.8 | – | – |

Summary of Table 2: Ru E_app ranges from 41.55 to 98.2 kJ/mol, and Ru TOF_H2 from 0.04 to 11.4 s⁻¹.

## Table 5 (p. 13) — Ni on different supports, selected rows
Columns: Ni wt %, T (°C), GHSV (mL_NH3·g_cat⁻¹·h⁻¹), X_NH3 (%), r_H2 (mmol·min⁻¹·g_cat⁻¹). **Table 5 has no TOF or E_app column.** Blank cells inherit from the row above (ambiguous).

| Catalyst | Ni wt% | T °C | GHSV | X % | r_H2 |
|---|---|---|---|---|---|
| Ni/Al2O3 | 10 | 550 | 6000 | 70.0 | 4.7 |
| Ni/Y2O3 | (10) | (550) | (6000) | 87.0 | 5.8 |
| Ni/MS | 15 | 650 | 30,000 | 97.2 | 32.5 |
| Ni/MRM | 15 | 600 | 30,000 | 97.9 | 32.8 |
| Ni/SBA-15 | 7.2 | 500 | 30,000 | 22.0 | 7.3 |
| Ni/SBA-15 | 23.4 | 500 | 30,000 | 57.0 | 19.1 |
| Ni1.26(Al0.3On) | 71.4 | 600 | 30,000 | 80.0 | 26.7 |
| Ni/Al2O3 | 9.6 | 500 | 6000 | 43.0 | 2.9 |
| Ni0.5Ce0.1Al0.4Ox | 39.1 | 500 | 18,000 | 90.0 | 18.1 |
| Ni/Ce0.8Zr0.2O2 | 13.2 | 550 | 3600 | 95.7 | 4.0 |

## Stability and deactivation data (all cited)
- **Ru/MgO endurance test** (Yamazaki et al. 2022, ref 81, Ind. Eng. Chem. Res. 61(17), 5778–5785), reproduced in Fig. 3a, p. 6:
  - Tests ran for more than 1000 h, up to about 4000 h on the figure axis, at 873, 923 and 973 K.
  - Conversion X at 773 K was about 99.7 → 99.4–99.6 %, read from figure (approximate).
  - Deactivation was modelled as linear, X = −k·t + X0, with an Arrhenius fit ln k = A − Ea/RT (correlation 0.9992) used to project 10-year activity.
  - The cause given is loss of mesoporosity in the MgO support (p. 7).
- Ru/La2O3-700-i (4.7 nm Ru) was stable at 798 K for more than 3 days (ref 83, p. 7).
- 10%Ni/rGO was stable for more than 27 h at 700 °C (ref 142, p. 13).
- A Ru-free Ni-based catalyst (Tabassum et al. 2022, ref 129) gave complete conversion at 450 °C and 6000 mL·g_cat⁻¹·h⁻¹. It ran for 600 h at 1.5 bar and 500 °C in a membrane reactor prototype (p. 21).
- Ni sintering is described as a key deactivation issue; most Ni catalysts carry more than 10 wt% Ni (pp. 20–21).

## Limitations
- This is a secondary source. Parameter values must be traced to the primary references.
- The rate-law equations are generic. Apart from the Tamaru expression, no parameter values are given.
- The GHSV basis is mL_NH3 per g_cat per h, so it is not directly comparable to the volumetric SV in takahashi2016kinetic.
- Table rows use blank cells and misaligned reference markers.

## Relevance to AmCraX
- Provides context ranges to sanity-check AmCraX kinetics: Ru E_app is about 41–98 kJ/mol and Ru TOF about 0.04–11.4 s⁻¹ (Table 2); Ni-Ru/CeO2 Ea is 107–124 kJ/mol.
- Provides the generic rate-law forms (power law, Tamaru, Temkin–Pyzhev).
- Gives qualitative RDS and H2-inhibition evidence.
- Provides stability evidence for Ru/MgO (linear deactivation model) and Ni sintering.
- **Not a source of rate parameters for the PFR.**
