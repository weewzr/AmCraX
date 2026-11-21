# takahashi2016kinetic

## Bibliographic data
- Takahashi, A., & Fujitani, T. (2016). Kinetic analysis of decomposition of ammonia over nickel and ruthenium catalysts. *Journal of Chemical Engineering of Japan, 49*(1), 22–28. https://doi.org/10.1252/jcej.14we431
- Affiliation: AIST (Interdisciplinary Research Center for Catalytic Chemistry), Tsukuba, Japan. Received 26 Dec 2014, accepted 11 May 2015 (p. 1).
- DOI 10.1252/jcej.14we431 verified via `https://doi.org/api/handles/10.1252/jcej.14we431`, which returned responseCode 1 (registered). It resolves to J-STAGE.
- Type: original research article. Source PDF: `research/papers/49_14we431.pdf` (7 pages; PDF page N = journal page 21+N).

## Scope
The paper gives a microkinetic model for NH3 decomposition with 4 lumped elementary steps. The same mechanism and the same model equations are fitted separately to Ni/MgO and to Ru/MgO. The model is integrated as an isothermal packed-bed PFR along catalyst mass. The paper uses it to show that the rate is controlled by NH3 dehydrogenation on Ni and by recombinative N2 desorption on Ru (abstract, p. 1; Conclusions, p. 7).

## Catalysts and reactor (p. 2, Section 1)
- **Ni/MgO: 30 wt% Ni.** **Ru/MgO: 5 wt% Ru.** Both were prepared by impregnation of MgO (made from Mg(NO3)2·6H2O) with aqueous Ni(NO3)2 or RuCl3. They were dried at 110 °C and calcined at 600 °C.
- Particle size 22–42 mesh (pressed, crushed and sieved).
- Pretreatment: 20 % H2 at 30 cm³·min⁻¹ and 600 °C.
- **Reactor:** continuous-flow fixed-bed quartz tube at **atmospheric pressure**, with a thermocouple in the bed. Analysis by online GC-TCD (Shincarbon ST column). NH3 conversion was calculated from H2 production.
- **Not reported:** catalyst mass per run, bed volume, bed density, reactor diameter and the volumetric basis of SV. See Limitations.

## Mechanism (p. 2, Eqs. 1–4); s = vacant site
1. NH3(g) + s ⇌ NH3(a), with forward constant k1 and reverse constant k−1
2. NH3(a) + 3s → N(a) + 3H(a), with constant k2. The step is irreversible; NH3 resynthesis is neglected at 1 atm.
3. 2N(a) → N2(g) + 2s, with constant k3. The step is irreversible. Preliminary experiments showed the rate was independent of p_N2.
4. 2H(a) ⇌ H2(g) + 2s, with forward constant k4 and reverse constant k−4. H2 re-adsorption is included to represent H2 inhibition.

## Governing equations (pp. 2–3; checked against the rendered PDF pages)
- (5) r1 = k1·(p_NH3/p_total)·θs − (k1/K1)·θ_NH3
- (6) r2 = k2·θ_NH3·θs³
- (7) r3 = k3·θN²
- (8) r4 = k4·θH² − (k4/K4)·(p_H2/p_total)·θs²
- (9) K1 = k1/k−1
- (10) K4 = k4/k−4
- (11) θs = 1 − θ_NH3 − θN − θH
- (12) dθ_NH3/dt = r1 − r2 = 0
- (13) dθN/dt = r2 − 2r3 = 0
- (14) dθH/dt = 3r2 − 2r4 = 0
- (15) dF/dm = −r1 + r3 + r4
- (16) dy_NH3/dm = [−r1 − y_NH3(−r1 + r3 + r4)]/F
- (17) dy_N2/dm = [r3 − y_N2(−r1 + r3 + r4)]/F
- (18) dy_H2/dm = [r4 − y_H2(−r1 + r3 + r4)]/F
- (19) dy_Ar/dm = [−y_Ar(−r1 + r3 + r4)]/F
- (20) k1 = A1, so adsorption is non-activated.
- (21) k2 = A2·exp(−Ea,2/RT)
- (22) k3 = A3·exp(−Ea,3/RT)
- (23) k4 = A4·exp(−Ea,4/RT)
- (24) K1 = A5·exp(−Ea,5/RT)
- (25) K4 = A6·exp(−Ea,4/RT). Eq. 25 uses the same Ea,4 as k4, so k−4 = k4/K4 = A4/A6 is temperature-independent; this matches the zero activation energy assumed for H2 adsorption.
- (26) Temkin–Pyzhev, quoted as the "generally accepted" form (p. 6): r = k·(p_NH3²/p_H2³)^β. **No value of β or k is given in this paper.** The form is attributed to Egawa et al. (1984), Chellappa et al. (2002), Yin et al. (2004) and Zhang et al. (2005b).

**Symbols** (Nomenclature, p. 7):

| Symbol | Meaning | Unit |
|---|---|---|
| A | Pre-exponential factor | mol·s⁻¹·g⁻¹, or dimensionless for A5 and A6 |
| Ea | Activation energy | J·mol⁻¹ (tabulated in kJ·mol⁻¹) |
| F | Total molar flow | mol·s⁻¹ |
| K | Equilibrium constant | dimensionless |
| k | Kinetic constant | mol·s⁻¹·g⁻¹ (per gram of catalyst) |
| m | Catalyst mass | g |
| p | Partial pressure | atm |
| p_total | Total pressure | atm |
| r | Rate | mol·s⁻¹·g⁻¹ |
| R | Gas constant | J·K⁻¹·mol⁻¹ |
| SV | Space velocity | h⁻¹ |
| T | Temperature | Listed as °C, but Arrhenius terms require K (see open issue 1) |
| y | Mole fraction | dimensionless |
| θ | Coverage | dimensionless |

**Consequences of the model structure:**
- At steady state r1 = r2 = 2r3 = (2/3)r4. The net NH3 consumption rate per gram of catalyst is therefore r_NH3 = r2 = k2·θ_NH3·θs³.
- Pressures enter only as the ratios p_i/p_total, i.e. as mole fractions. The model therefore has **no intrinsic total-pressure dependence** of the rate per gram.
- The model contains no reverse (synthesis) reaction, so it cannot approach thermodynamic equilibrium.

Numerical method (p. 3): Runge–Kutta integration over m with a step of 0.001 g. At each step Eqs. 11–14 were solved by Newton–Raphson. Parameters were fitted by the Box complex method plus SQP, minimising the sum of squared relative errors of outlet H2 fraction, in EQUATRAN-G.

## Parameters — Table 1, p. 4 (fitted by this paper)
| Constant | Ni A | Ni Ea [kJ/mol] | Ru A | Ru Ea [kJ/mol] |
|---|---|---|---|---|
| k1 [mol·s⁻¹·g⁻¹] | 7.55×10¹ | 0 | 8.36×10¹ | 0 |
| k2 [mol·s⁻¹·g⁻¹] | 7.54×10¹⁵ | 144.0 | 1.34×10¹⁴ | 105.8 |
| k3 [mol·s⁻¹·g⁻¹] | 3.12×10⁶ | 127.8 | 6.26×10⁵ | 123.5 |
| k4 [mol·s⁻¹·g⁻¹] | 3.92×10⁴ | 109.0 | 7.18×10² | 67.8 |
| K1 [—] | 2.26×10⁻¹⁴ | −79.4 | 3.49×10⁻¹³ | −64.0 |
| K4 [—] | 4.13×10⁶ | 109.0 | 1.51×10⁴ | 67.8 |

- The negative Ea for K1 means exothermic NH3 adsorption: K1 = A5·exp(+79.4 kJ/mol / RT) for Ni.
- The paper calls the "activation energy" values 128 kJ/mol (Ni) and 124 kJ/mol (Ru), i.e. those of k3 for N2 desorption. It compares them with 125–210 kJ/mol from Chellappa et al. (2002), 205 kJ/mol on Ni foil from Ertl & Rüstig (1982), 184 kJ/mol on Ru(001) from Tsai & Weinberg (1987) and 147 kJ/mol for Ru/MgO from Hayashi et al. (2013) (p. 4). **Those four literature values are cited, not measured here.**
- p. 4: the surface-reaction pre-exponential factors on Ni are about 50× those on Ru. The authors attribute this to about 80× more surface metal sites per gram on the 30 wt% Ni catalyst. That site estimate uses dispersions from Zhang et al. (2005b) and Newman et al. (2014), not a measurement.

## Table 2, p. 5 — rate constants at 500 °C (1 atm NH3, SV 15000 h⁻¹), in mol·s⁻¹·g⁻¹
| Constant | Ni | Ru |
|---|---|---|
| k1 | 7.55×10¹ | 8.36×10¹ |
| k−1 | 1.50×10¹⁰ | 1.17×10¹⁰ |
| k2 | 1.51×10⁶ | 9.97×10⁶ |
| k3 | 7.48×10⁻³ | 3.02×10⁻³ |
| k4 | 1.79×10⁻³ | 1.94×10⁻² |
| k−4 | 9.49×10⁻³ | 4.75×10⁻² |

Text on p. 5 gives K4(500 °C) = 1.89×10⁻¹ for Ni and 4.07×10⁻¹ for Ru.

**Consistency check (run by this agent, not reported by the paper).**
- Method: Table 1 was evaluated at T = 773.15 K with R = 8.314 J/(mol·K).
- Ni results: k2 = 1.41×10⁶, k3 = 7.24×10⁻³, k4 = 1.69×10⁻³, K4 = 0.178, k−1 = 1.44×10¹⁰, k−4 = 9.49×10⁻³.
- Ru results: k2 = 9.53×10⁶, k3 = 2.83×10⁻³, k4 = 1.89×10⁻², K4 = 0.396, k−1 = 1.14×10¹⁰, k−4 = 4.75×10⁻².
- Comparison: the values are 2–7 % below Table 2 and the K4 values quoted in the text. k−4 = A4/A6 matches exactly.
- Interpretation:
  - Temperature in kelvin is clearly intended; °C would give absurd values.
  - The residual offset is probably rounding of the tabulated A and Ea values, or a different R or T conversion. The paper does not resolve it.
  - Recommendation: use Table 1 as the parameter set and accept a reproduction tolerance of about 10 % against Table 2. **Do not tune the parameters.**

## Operating ranges (experimental basis)
All runs were at **total pressure 1 atm**.
- **Kinetic fitting** used 5 temperature runs and 15 runs at varied NH3 partial pressure, restricted to <20 % conversion (p. 3).
  - Ni: 350–450 °C with p_NH3 = 1 atm and SV 15000 h⁻¹ (Fig. 1a). The p_NH3 series ran from about 0.1 to 1.0 atm (Ar balance) at 370 °C/SV 15000, 400 °C/SV 20000 and 430 °C/SV 30000 h⁻¹ (Fig. 1b).
  - Ru: 300–400 °C (Fig. 2a). The p_NH3 series was at 300 °C/15000, 330 °C/20000 and 350 °C/30000 h⁻¹ (Fig. 2b).
- **Extrapolation tests** covered 20–100 % conversion (Section 4.1, p. 4).
  - Ni: 500–650 °C, p_NH3 0.25–1 atm at 500 °C, and SV 2000–20000 h⁻¹ at 450/500/550 °C (Fig. 3).
  - Ru: 450–550 °C, p_NH3 0.25–1 atm at 450 °C, and SV 2000–20000 h⁻¹ at 400/450/500 °C (Fig. 4).
- **H2 inhibition** runs used p_H2 = 0–0.7 atm with p_NH3 = 0.3 atm, Ar balance and SV 15000 h⁻¹, at 500 °C for Ni and 450 °C for Ru (Fig. 5, p. 5).
- The paper reports an average relative deviation of less than 1 % for all fits and simulations (p. 4).
- External mass transfer was excluded because the rate did not depend on linear velocity. Internal diffusion was excluded by the Weisz criterion (p. 3).

## Validation data (figures; read from figure, approximate ±2 percentage points; "H2 yield" in %)
These points were read from 300-dpi renders of PDF p. 5 (Figs. 3–4) and p. 3 (Figs. 1–2). "H2 yield" is assumed to equal NH3 conversion because the paper computes conversion from H2 production (p. 2).

**Ni catalyst**
- Fig. 3a (1 atm NH3, SV 15000 h⁻¹): 500 °C ≈ 29.5; 550 °C ≈ 62; 600 °C ≈ 94; 650 °C ≈ 99.
- Fig. 3b (500 °C, SV 15000 h⁻¹; p_NH3 in atm): 0.25 ≈ 70.5; 0.50 ≈ 47; 0.75 ≈ 35.5; 1.0 ≈ 30.
- Fig. 3c (1 atm NH3; SV in h⁻¹ → yield):

| T | SV 2000 | SV 4000 | SV 7000 | SV 12000 | SV 15000 | SV 20000 |
|---|---|---|---|---|---|---|
| 550 °C | ≈ 96 | ≈ 90 | ≈ 82 | ≈ 70 | — | ≈ 58 |
| 500 °C | ≈ 69 | ≈ 55 | ≈ 43 | ≈ 34 | ≈ 29 | — |
| 450 °C | ≈ 32 | ≈ 24 | ≈ 19 | ≈ 15 | ≈ 12 | — |

- Fig. 5a (500 °C, 0.3 atm NH3; p_H2 in atm): 0 ≈ 61; 0.1 ≈ 54; 0.3 ≈ 37; 0.5 ≈ 27; 0.7 ≈ 23.
- Fig. 1a (low-conversion fitting data): 350 ≈ 1; 375 ≈ 2.5; 400 ≈ 4; 425 ≈ 7.5; 450 °C ≈ 12.

**Ru catalyst**
- Fig. 4a (1 atm NH3, SV 15000 h⁻¹): 450 °C ≈ 42.5; 500 °C ≈ 85.5; 550 °C ≈ 99.5.
- Fig. 4b (450 °C, SV 15000 h⁻¹): 0.25 ≈ 92.5; 0.50 ≈ 64.5; 0.75 ≈ 50; 1.0 ≈ 42.5.
- Fig. 4c (1 atm NH3; SV in h⁻¹ → yield):

| T | SV 2000 | SV 4000 | SV 7000 | SV 12000 | SV 15000 | SV 20000 |
|---|---|---|---|---|---|---|
| 500 °C | ≈ 100 | — | ≈ 100 | ≈ 93 | ≈ 85.5 | ≈ 80.5 |
| 450 °C | ≈ 92 | — | ≈ 70 | ≈ 50 | ≈ 42 | ≈ 36 |
| 400 °C | ≈ 55.5 | ≈ 41.5 | ≈ 32 | ≈ 25 | ≈ 16.5 | — |

- Fig. 5b (450 °C, 0.3 atm NH3; p_H2 in atm): 0 ≈ 89; 0.1 ≈ 81; 0.3 ≈ 68; 0.5 ≈ 59; 0.7 ≈ 53.
- Fig. 2a (low-conversion fitting data): 300 ≈ 1; 325 ≈ 2.5; 350 ≈ 4.5; 375 ≈ 9; 400 °C ≈ 16.

**Simulated coverages** (Fig. 7, p. 6; 500 °C, 1 atm, SV 15000 h⁻¹)
- Total coverage θ_all ≈ 60 % throughout the bed, dominated by H(a).
- θN on Ni ≤ about 0.1.
- θN on Ru ≈ 0.4 near the inlet.

## Limitations
1. **Atmospheric pressure only.** Rates depend on p_i/p_total, so the model predicts no total-pressure effect on the rate per gram. Extrapolating to 20 bar (AmCraX baseline) is unvalidated.
2. **No reverse reaction.** NH3 synthesis and N2 re-adsorption are omitted, so the model can predict conversions above equilibrium. At 1 atm and ≥450 °C equilibrium is above 99 %, so this did not matter in the paper. At 20 bar it matters. A downstream user must cap the result at equilibrium or add an approach-to-equilibrium factor, **labelled as an assumption**.
3. **SV basis and catalyst mass are not stated.** The figures (vs SV) cannot be converted to W/F_NH3 without assuming a bed density or catalyst mass. Model-vs-figure validation therefore needs an explicit assumption.
4. **Isothermal lab bed** (small catalyst amount). The model contains no heat-transfer terms.
5. **Lab catalysts only.** These are 30 wt% Ni/MgO and 5 wt% Ru/MgO, not commercial pellets. There are no internal-diffusion (effectiveness factor) data for large pellets.
6. **Unit inconsistency in the nomenclature**, where T is listed in °C; kelvin is required.
7. **Table 1 reproduces Table 2 only to within 2–7 %.**

## Relevance to AmCraX
This is the **primary source** for `amcrax.kinetics` rate laws for both Ni and Ru.
- Rate: r_NH3 [mol·s⁻¹·g_cat⁻¹] from Eqs. 5–14 with the Table 1 parameters. Multiply by 1000 for per-kg.
- Partial pressures enter as mole fractions. They are the atm-based ratio p_i/p_total, so bar or atm does not matter as long as the units are consistent.
- PFR: Eqs. 15–19 over catalyst mass.
- Validity range: Ni 350–650 °C and Ru 300–550 °C, at 1 atm.
- Use at 600 °C/20 bar requires labelled assumptions: pressure extrapolation and an equilibrium cap.
- Figs. 3–5 provide the validation targets, with an assumed bed basis.
