# sayas2020rukcao: full-text reading (24 November 2026)

Sayas, S., Morlanes, N., Katikaneni, S. P., Harale, A., Solami, B., & Gascon, J. (2020). High pressure ammonia
decomposition on Ru-K/CaO catalysts. *Catalysis Science & Technology, 10*(15), 5027-5035.
https://doi.org/10.1039/d0cy00686f (CC BY 3.0).

The main article was read in full from a copy supplied by the user. Every number in
`research/data/sayas2020_extract.json` was checked against the page images. Figure values were read from zoomed images,
and their uncertainty is stated. The electronic supplementary information (ESI) was **not** available. This note
replaces the access status in `sayas2020rukcao.md` (written 23 November, full text not read) and does not change it.
Nothing was fitted, estimated or implemented. No model, analysis or verdict was changed.

Page numbers are journal pages (5027 = PDF page 1).

## 1. What the paper gives

**Catalyst** (pp. 5027-5030, Tables 1-2, Fig. 2)
- Best formulation: 3%Ru10%K/CaO (nominal wt%). ICP gives 2.8 wt% Ru and 9.6 wt% K (Table 1).
- Preparation: incipient wetness with RuCl3 in acetone, then Ar at 500 degC; then KOH in ethanol, then Ar at 500 degC.
- Characterisation: BET area 5 m2/g. CO chemisorption gives dispersion 15.5 % and particle size 6 nm. TEM gives a mean
  of 7 nm (range 2-15 nm) with K, and 9 nm without K.
- The abstract gives a K/Ru *atomic* ratio of 0.9. This does not match the stated loadings: 10 wt% K and 3 wt% Ru give
  8.6 mol/mol (reader arithmetic). Project notes that repeat "K/Ru = 0.9" carry this inconsistency.
- Support screening (Table 3) used 5 wt% Ru with 10 wt% K on MWCNT, MgO, sepiolite and CaO, at 400 degC and 1 atm.
  The conversions were 30.8, 39.4, 46.6 and 53.7 %. No Al2O3 or commercial catalyst was tested.

**Tests** (pp. 5028-5029; captions of Figs. 3-5)
- Reactor: alumina-coated stainless-steel fixed bed in a PID Microactivity unit. Diameter, bed length and thermocouple
  position are not given.
- Bed: 200 mg of catalyst, pellets of 300-500 um, diluted with 1 g SiC. Activation in H2 at 500 degC for 3 h.
- Feed: pure NH3.
  - At 1 atm: 30-100 mL/min, WHSV 9000-30000 mL gcat-1 h-1. All plotted data use 30 mL/min (WHSV 9000).
  - At 10-40 bar: liquid NH3 is pumped at **30 N mL min-1, WHSV 9000 mL gcat-1 h-1**, so the molar feed is the same
    at every pressure.
  - The reference state of "N mL" is not defined.
- Pressures in Fig. 4: 1, 10, 20 and 40 bar. Temperatures 250-550 degC. Total reaction time 7 h. No longer stability
  test is reported. XRD after the test still shows metallic Ru.
- The paper says the 1 atm loading study has no heat- or mass-transfer limitation. The evidence (Figs. S1-S3) is in
  the ESI.

**Measured conversions of 3%Ru10%K/CaO** (Fig. 4A, figure reading, +/-2 percentage points)

| T (degC) | 1 bar | 10 bar | 20 bar | 40 bar | Xeq, 40 bar (Fig. 4A curve) |
|---|---|---|---|---|---|
| 350 | 27 | 7 | 5.5 | 4.5 | 63 |
| 400 | 61 | 21.5 | 17 | 13.5 | 76 |
| 450 | 90 | 50.5 | 39.5 | 33 | 85 |
| 500 | 100 | 80.5 | 68 | 62 | 91 |
| 550 | 100 | 93.5 | 87.5 | 84.5 | 94 |

At 250 and 300 degC, all conversions above 1 bar are about zero. Fig. 4B gives X/Xeq at 400 degC (62/23/20/19 % at
1/10/20/40 bar) and at 450 degC (90.5/52.5/42.5/38 %). These readings agree within reading error with the 500 degC
series that maccarrone2025comprehensive Table 2 attributes to this paper (98/80/65/60 %). The text says "around 80%"
at 550 degC and 40 bar; the plotted point reads about 84 %.

**Rates, productivity and the "40 times" claim** (Figs. 4C-D). The caption says the rates were computed as for a
differential reactor, taking into account the operating pressure. The plotted values equal X x (F/W) x P: for
example, 0.845 x 0.368 x 40 = 12.4 against about 12.5 mol NH3 gcat-1 h-1 read at 40 bar and 550 degC (reader
arithmetic, with F/W = 0.368 mol gcat-1 h-1). The feed is the same molar flow at every pressure. The NH3 actually
converted per gram is therefore X x F/W, and it *falls* with pressure. The abstract claims hydrogen productivities and
TOFs 40 times bigger at high pressure. That claim comes from this multiplication by pressure. It is not a larger
measured molar output. (xu2025review flagged the claim; this resolves it.)

**Kinetics** (pp. 5031-5034, Table 4, eqns (1)-(3), Fig. 6)
- Eqn (1): (-r_NH3) = k P_NH3^a P_H2^b.
- Eqn (2) adds the factor [1 - (1/Keq) P_N2 P_H2^3 / P_NH3^2].
- Eqn (3): W/F = integral of dX/(-r_NH3), for an integral plug-flow fit.
- Table 4, at 350 degC and atmospheric pressure, from differential experiments:

  | Catalyst | Ea (kJ/mol) | a (NH3 order) | b (H2 order) |
  |---|---|---|---|
  | 3%Ru10%K/CaO | 75 | 0.5 | -1.2 |
  | 3%Ru/CaO | 96 | 0.8 | -1.9 |

  No uncertainties and no N2 order are given. This confirms the essay values that were earlier marked NOT VERIFIED.
- The paper includes both H2 inhibition (the negative order b) and the reverse reaction (eqn (2)).
- The fit used atmospheric data only. The high-pressure conversions were then *predicted*: the parity in Fig. 6 has
  slope 0.9837 and R2 0.9846.
- The 12 red high-pressure points match the Fig. 4A points for 350-500 degC at 10, 20 and 40 bar. The 550 degC points
  (84-94 %) are not in Fig. 6 (reader inference). At 350-400 degC the model over-predicts by 3-6 points.
- **The main text contains no k, no k0, no units of k or P, no Keq definition, no fitted range of the integral fit and
  no parameter uncertainty.** All of these are placed in the ESI.
- research/model_parameters.yaml carries Ea 111 kJ/mol and K0 8584.8 (from maccarrone2025comprehensive Table 5).
  Neither number is in this paper's main text, and they differ from the 75 kJ/mol of Table 4. They stay unverified.
- The text gives inconsistent statements about where the reverse term matters. It says the term grows above 400 degC
  and also that it is non-negligible below 500 degC (p. 5033).
- Other inconsistencies:
  - The activation temperature is 500 degC in the text and 525 degC in the Fig. 2 caption.
  - The Fig. 4 caption says "atm" where the legend and text say bar.
  - The NAS column header in Table 2 is off by a factor of 100 (per 100 g). The TOFs use the correct value,
    4.6e-5 mol/g.

**Comparison and limitations stated by the authors**
- Ru-K/CaO beats the other supports tested (Table 3), which the authors attribute to basicity.
- K promotion lowers Ea and the H2 inhibition.
- The authors acknowledge thermodynamic limits at high pressure: conversion falls strongly from 1 to 40 bar.
- They state that the mechanistic models cannot identify the rate-limiting step.
- They suggest that high-pressure experiments may not be needed, because 1 atm kinetics predicted their 10-40 bar
  data.

## 2. Assessment (comparison with published literature only; not experimental validation of AmCraX)

**(a) Is a complete rate law given?** **No.**
- Present:
  - the functional form, eqns (1)-(2);
  - the orders a = 0.5 and b = -1.2, and the apparent Ea of 75 kJ/mol (350 degC, 1 atm, differential);
  - the integral PFR equation;
  - the catalyst composition;
  - the reactor charge, W = 0.2 g;
  - the feed basis: pure NH3, 30 N mL/min.
- Missing:
  - k0, with its units, basis and pressure unit;
  - whether Ea and the orders were refitted in the integral fit;
  - the definition of Keq and its standard state;
  - the fitted T, P and conversion range;
  - the uncertainties;
  - how the P_H2 -> 0 singularity at the inlet was handled (b < 0 with a pure NH3 feed).
- So nothing can be implemented, and nothing may be fitted in this task.
- A legitimate later step has two routes:
  1. Obtain the ESI and transcribe k0 and Keq. This needs no fitting.
  2. Perform a new, separately labelled modelling step: an "AmCraX fit to digitised Sayas data". It would have to state
     the flow reference state (0 vs 25 degC is a 9 % difference in F), the H2 seed at the inlet, the Keq basis and the
     points used. The points used for fitting could then not also serve as the comparison points for that law.
- Note for later: as printed, the eqn (2) factor is 1 - (Q/Kp)^2, with Q and Kp per mol NH3, if Keq = Kp^2. This is
  not the same as AmCraX's approach factor 1 - Q/Kp. Both vanish at equilibrium, but they differ away from it.

**(b) Literature comparison points at 10-40 bar**
- 15 non-zero points: 10, 20 and 40 bar x 350, 400, 450, 500 and 550 degC (table above).
- Conditions: 3%Ru10%K/CaO, 200 mg, pure NH3, 30 N mL min-1, isothermal set-point.
- Specified well enough to simulate in principle (W/F is known), but with three limitations:
  - the reference state of "N mL" is undefined, a +/-9 % uncertainty in F;
  - the bed geometry and temperature profile are unknown;
  - the values are figure readings (+/-2 points).
- Of these points, 500 and 550 degC at 20 and 40 bar fall inside the AmCraX operating window (499-594 degC, at least
  15 bar).
- Fig. 4D rates must not be used: they are pressure-scaled (see above).

**(c) Effect under the coded rules as written**
- `kinetics_validity_classification.py` hard-codes Ru-K/CaO in `UNMODELLED`. Adding this evidence would change only
  the text of the `reason` and `experimental` fields, for example:
  - feed: pure NH3;
  - high-pressure WHSV: 9000 only;
  - conversion: about 84 % at 550 degC and 40 bar.
- The class stays `unmodelled`, and the counts stay 0 / 3 / 2 / 3.
- Ru-K/CaO could become `validated_at_relevant_conditions` only if two things happened:
  - a complete law were implemented (which needs the ESI);
  - its PFR prediction passed a comparison at 20 or 40 bar and 500-550 degC.
- Note for that case: `classify()` does not check `comparison_uses_fitting_data`. The Sayas 10-40 bar points are, per
  the authors, outside their own fitting set.
- H3-b reads `kinetic_classes` only for LOWT (Ru/Al2O3, Ru/MgO, the two NiRu/CeO2) plus Ni/MgO, from
  catalyst_economics.json. It also needs the Ni/MgO reference to be validated. Ru-K/CaO is not in LOWT, and the paper
  has no Ni data, so **H3-b stays INCONCLUSIVE** whatever is added from this paper. Only the counts printed in its
  conclusion would change, and they do not change while the law is incomplete.
- H3-a, H3-c and H3-d read no kinetic-validity entry that this paper can supply: **unchanged**.
- H3-e and H3-f use the Ru/Al2O3 law as a proxy for Cho's Ru-K/CaO. This paper supplies no complete law, so the proxy
  and both secondary verdicts (INCONCLUSIVE) are **unchanged**.

**(d) Cho et al.'s point at 566.69 degC and 10 bar**
- The paper has no data above 550 degC. Cho's temperature is 16.69 K above the highest measured temperature.
- At the same nominal space velocity (9000 mL gcat-1 h-1, Cho Table 3), 10 bar and 550 degC, pure NH3 gave about
  93.5 %. Cho's design point requires at least 97 % and includes an H2 recycle, which this catalyst's -1.2 H2 order
  would penalise.
- The paper therefore neither confirms nor contradicts that Cho's point is reachable.
- Composition: 3 wt% Ru (ICP 2.8) with 10 wt% K (ICP 9.6) supports the 3 wt% Ru basis of the derived Ru-K/CaO price.
  The K content is confirmed as 10 wt% K (KOH precursor; K2O by XRD).
- Lifetime: the paper reports 7 h only. It gives no support for a multi-year catalyst lifetime and no deactivation
  rate.
- Density: no catalyst or bed density is given (Cho's 1500 kg/m3 and Richard's 846 kg/m3 come from other sources).

**(e) Points that go against current project statements**
1. "K/Ru = 0.9" (sayas2020rukcao.md, reference entries) is inconsistent with the stated loadings (about 8.6 mol/mol).
2. The Ea of 111 kJ/mol attributed to Sayas via maccarrone2025comprehensive (model_parameters.yaml) is not in the main
   text. Table 4 gives 75 kJ/mol for the same catalyst. Treat 111 kJ/mol and K0 8584.8 as unverified secondary values.
3. The "40 times higher productivity/TOF" statement is an artefact of multiplying by pressure (see above). It is not a
   measured effect.
4. A caution for the Ru/Al2O3 extrapolation (not evidence under the rules, and different catalysts):
   - At 20 bar and 500 degC, Sayas measured about 68 % with about 0.07 g Ru h/mol NH3 (0.2 g x 2.8 % / 0.080 mol/h).
   - At 20 bar, the AmCraX Ru/Al2O3 law (8 wt% Ru, fitted at 1-10 bar) reaches 95 % at 499 degC with 0.08 g Ru h/mol
     (100 kg per 100 kmol/h).
   - The pressure-extrapolated law is therefore far more active per gram of Ru than the catalyst this paper calls among
     the most active Ru solids, measured at 20 bar.
   - Dispersion, support and bed differ, so this is not a test. It is a reason to keep the Ru/Al2O3 20 bar results
     labelled as extrapolation, which the project already does.
5. "About 80 % at 550 degC, 40 bar" (methodology_transfer.json, validity classification) matches the authors' text.
   The figure reads about 84 %.

**(f) Boundary differences that limit each comparison**
- Lab bed against plant:
  - 0.2 g diluted in SiC, 300-500 um pellets, near-isothermal set-point and a fresh catalyst run for 7 h;
  - against an AmCraX isothermal PFR with effectiveness factor 1, a commercial-scale inventory and multi-year use.
- Feed: pure NH3, against AmCraX and Cho feeds (Cho recycles H2).
- Space velocity:
  - Sayas: one WHSV at high pressure. W/F is about 2.5 g h/mol, 2.5 times the AmCraX 100 kg per 100 kmol/h basis.
  - The flow reference state is undefined.
- Pressure and temperature: 10, 20 and 40 bar only (no 24.34 or 30 bar); T at most 550 degC, against the AmCraX
  window of 499-594 degC and Cho's 566.69 and 735.52 degC.
- Catalyst: Ru-K/CaO is not any of the catalysts AmCraX models (Ru/Al2O3, Ru/MgO, NiRu/CeO2, Ni/MgO). Cross-catalyst
  comparisons are context only.
- The Fig. 6 model check covers 350-500 degC. It does not cover the near-equilibrium 550 degC points.

## 3. What only the ESI can settle
- k0 and its units.
- The definition of Keq.
- Whether Ea and the orders were refitted in the integral fit.
- The fitted ranges and uncertainties.
- The Arrhenius temperature range.
- The transport checks and whether they cover 10-40 bar.
- The mechanistic models (S5)-(S8).
- Treatment of the inlet singularity.
- Possibly the reactor dimensions and the "N mL" reference state.
