# cechetto2023membrane

## Bibliographic data
- Authors: Valentina Cechetto, Luca Di Felice, Fausto Gallucci (Eindhoven University of Technology)
- Title: Advances and Perspectives of H2 Production from NH3 Decomposition in Membrane Reactors
- Journal: Energy & Fuels, 2023, vol. 37, pp. 10775-10798. Received 7 Mar 2023, published 16 Jul 2023 (p. 1). Open access (ACS AuthorChoice). The issue number is not printed on the pages read and is not given here.
- DOI: 10.1021/acs.energyfuels.3c00760 (verified: doi.org handle API responseCode 1, resolves to https://pubs.acs.org/doi/10.1021/acs.energyfuels.3c00760)
- APA 7: Cechetto, V., Di Felice, L., & Gallucci, F. (2023). Advances and perspectives of H2 production from NH3 decomposition in membrane reactors. *Energy & Fuels, 37*, 10775-10798. https://doi.org/10.1021/acs.energyfuels.3c00760
- Type: review. PDF page numbers below run 1-24, corresponding to journal pages 10775-10798.
- **Own work vs. quoted work.** The review's own contributions are:
  - the equilibrium curves in Fig. 2 (Aspen Plus V11, RGibbs);
  - the equilibrium-conversion column in Table 3 (presumably computed by the authors; the source is not stated);
  - the "calculated" values marked b in Tables 8-10.

  All other data come from the cited experiments, including the authors' own earlier papers [40,65].

## Scope
Ammonia as an H2 carrier (Table 1), thermodynamics (Fig. 2), conventional vs membrane-reactor process schemes (Fig. 3), fuel-cell H2 specifications, membranes (Table 2), effects of operating conditions (Tables 3-7, Figs. 5-9), "efficient" membrane reactors (Table 8), a full literature summary (Table 9), H2 purity and residual NH3 (Table 10), diluted streams (Table 11), and challenges.

## Thermodynamics
- Eq. 1 (p. 3): NH3 <-> 0.5 N2 + 1.5 H2, printed as "dH_f deg = 45.92 kJ/mol". The label says "f" (formation), but the value is the standard reaction enthalpy per mol NH3, i.e. minus the formation enthalpy of NH3. The symbol is mislabelled.
- Fig. 2 (p. 3). Equilibrium NH3 conversion versus T (200-800 deg C) at 1, 5, 10 and 20 bar, computed with Aspen Plus V11 RGibbs (the authors' own calculation).
  - Stated: > 99% at 1 bar for T > 400 deg C; > 95% for all pressures (1-20 bar) above 500 deg C.
  - Read from the figure (approximate): at 200 deg C about 75% (1 bar), 43% (5 bar), 32% (10 bar) and 24% (20 bar).
- Table 3 (p. 9) equilibrium conversions:
  - at 5 bar: 91.9% (350 deg C), 95.9% (400), 97.0% (425), 97.8% (450), 98.3% (475), 98.7% (500);
  - at 4 bar: 96.7% (400 deg C), 97.6% (425), 98.2% (450);
  - at 1 bar: 97.3% (325 deg C), 98.2% (350), 98.7% (375), 99.1% (400), 99.7% (450).

  In the column headers of Table 3 the first "Permeate pressure [bar]" is evidently the reaction (retentate) pressure; Table 4 lists the same values as "Reaction pressure". These are useful cross-checks for `amcrax.thermodynamics.solve_equilibrium`.
- Energy to extract H2 from NH3 is 30.6 kJ/mol H2, against 0.907 kJ/mol H2 for regasifying liquid H2 (p. 3; Table 1 from refs 7, 36, 38).
- Table 1 (p. 2, from refs 7, 36, 38) gives the properties of liquid NH3:
  - storage at 25 deg C and 9.9 bar;
  - density 600 kg/m3;
  - LHV 18.6 MJ/kg;
  - volumetric energy density 12.7 MJ/L;
  - H2 content 17.8 wt% and 121 kg H2/m3;
  - explosive limit 15-28 vol% in air.

  Autoignition 650 deg C (NH3) vs 520 deg C (H2). Flammability range 15.15-27.35% in dry air (p. 3).

## Hydrogen quality specification (FOCUS b)
- ISO 14687:2019 (ref 35), as quoted on p. 5:
  - NH3 must not exceed 0.1 ppm in both stationary and vehicle PEMFC applications;
  - N2 may make up to 50% by volume for stationary applications and must not exceed 300 ppm for vehicle applications.

  Consequence (p. 5): an NH3 removal unit is always required. An N2 separation unit is needed for vehicle-grade H2 in conventional plants, but may be avoided with a highly H2/N2-selective membrane. Optimal PEMFC operating pressure is typically 3-4 bar (p. 11, ref 90).
- PSA (p. 4, ref 23): "the most well developed technology for the separation of hydrogen produced via ammonia decomposition". Cryogenic separation is an alternative at large scale. NH3 can be removed by water absorption, commercial adsorbents or ion-exchanged zeolites. **No PSA recovery or purity numbers are given.**
- Off-gas (p. 6): combustion of off-gases alone provides insufficient heat; additional fuel is required. Combusting NH3 is economically favourable, but N2-diluted off-gas may need H2 co-firing to stay within flammability limits. The membrane-reactor retentate (unconverted NH3 + H2) can be burned for reactor heat. These statements are qualitative.

## Membranes (Section 4.1, pp. 6-7, Table 2 p. 5)
- Pd-based membranes have the highest permeance and selectivity, are mature, and are stable in NH3 (ref 64).
  - Pd alloys have higher H2 permeation than pure Pd (ref 68).
  - Pure Pd suffers H2 embrittlement below 300 deg C and 2 MPa (refs 69-71).
  - Pd membranes form defects above 550 deg C (refs 72-73).
  - In membrane reactors, Pd-based membranes "should never" exceed 500 deg C (p. 10).
  - Thicker membranes give higher selectivity but lower permeance.
- **No Sieverts-law equation, pressure exponent, or numerical permeance/permeability values appear in this review.** These must come from another source (e.g. the original Cechetto 2021/2022 papers or Gallucci et al.).
- Selective-layer thicknesses (Table 2):
  - Pd 6.2 um (Zhang 2019) and ~3 um (Zhang 2006);
  - Pd-Ag ~6-8 um [40] and 4.61 um [65], both with a ~1 um mesoporous Al2O3-YSZ protective layer;
  - Pd-Au 8 um [66];
  - Pd-Ag 1.8 um (Jiang 2021);
  - Pd 200 um unsupported (Itoh 2014);
  - Pd ~5 um on Inconel (Kim 2022);
  - SiO2 < 0.3 um (Li 2012).

## Membrane reactor benchmarks (conventional reactor vs membrane reactor). Table 3, p. 9.
Cechetto et al. 2021 [65]: 2 wt% Ru/Al2O3 (250 g), Pd-Ag 4.61 um, 4 bar, 500 mLN/min NH3.

Permeate at 1 bar (temperature: equilibrium / conventional reactor / membrane reactor / H2 recovery):
- 400 deg C: 96.7 / 65.4 / 72.2 / 94%
- 425 deg C: 97.6 / 86.2 / 98.0 / 97%
- 450 deg C: 98.2 / 96.8 / 99.5 / 97%

Permeate at 0.01 bar (vacuum):
- 400 deg C: membrane reactor 99.3, recovery 52%
- 425 deg C: 99.6, recovery 80%
- 450 deg C: 99.8, recovery 85%

The vacuum recovery values (52/80/85) conflict with Table 6 and Table 8, which give 93.5% recovery at 400 deg C under vacuum for the same work. The H2 recovery column in Table 3 for [65] may be misaligned between the 1 bar and 0.01 bar rows; it is reproduced as printed.

Other works in Table 3:
- Zhang 2019 (Cs/Ru): 350 deg C, conventional reactor 8% -> membrane reactor 86%, recovery 87%; 400 deg C, 31 -> 99%, recovery 95%.
- Itoh 2014 (5% Ru/SiO2, Pd 200 um, 1 bar, permeate 0.01 bar): 450 deg C, 73 -> 87%, recovery 59%. Values read from figures.

## "Efficient" membrane reactors (conversion > 99% and recovery > 90%). Table 8, p. 15.

| Work | Catalyst | Membrane | T deg C | P bar | P perm | X % | R_H2 % | Vol. productivity mol m-3 s-1 | Cat. utilisation g/cm2 |
|---|---|---|---|---|---|---|---|---|---|
| Zhang 2019 | 0.41 Cs-Ru/YSZ | Pd 6.2 | 450 | 5 | 1 | >99 | - | 31.6 | N/A |
| Cechetto 2022 [40] | 2 Ru/Al2O3 | Pd-Ag 6-8 | 500 | 6 | 1 | 99.8 | 91.6 | 1.2a | 2.915a |
| Cechetto 2021 [65] | 2 Ru/Al2O3 | Pd-Ag 4.61 | 450 | 5 | 1 | 99.7 | 90.5 | 1.2a | 2.992a |
| Cechetto 2021 [65] | 2 Ru/Al2O3 | Pd-Ag 4.61 | 400 | 4 | vacuum | 99.3 | 93.5 | 1.3a | 2.814a |
| Cerrillo 2022 | 5 Ba-CoCe | Pd-Au 8 | 485 | 5 | 1 | 99a | 91a | N/A | 0.143 |
| Jiang 2021 | 3 Ru-Y-K/Al2O3 | Pd-Ag 1.8 | 450 | 7 | 1 | >99.1 | >90.6 | >40.8a | 0.168a |
| Kim 2022 | 2 Ru/Al2O3 | Pd 5 | 430 | 5 | vacuum | 99.4 | 97.5 | 1.5a | N/A |
| Sitar 2022 | 1.9 Ru/YSZ + 0.5 Ru/a-Al2O3 | Pd 4.23 | 450 | 5 | 1 | >99 | >90 | 54.2 | 0.221 |

a = calculated by the review authors. In the "Total catalyst utilisation [g/cm2]" column, the text defines the quantity as "amount of catalyst per unit volume of membrane", which conflicts with the g/cm2 unit; the review does not resolve this. The general rule stated on p. 11 is that X > 99% is achievable at 450 deg C and 5-7 bar with permeate at 1 atm on Ru catalysts.

## H2 purity and residual NH3 (Table 10, p. 17; text pp. 12-15)
- Jiang 2021: Pd-Ag 1.8 um, 450 deg C, 7 bar, 50-250 mL/min over 3 g catalyst. Purity > 99.999%; NH3 < 0.01 ppm (< 10 ppb by sensor); N2 < 0.01%. This meets ISO for vehicles. With CMSM the purity was 96.84% and with MFI 91.16% (Table 10). The text (p. 13) says < 97% and < 94%.
- Omata 2022: Pd-Ag/V-Fe (V-Fe 100 um), 350 deg C, 3 bar, 10 mL/min. NH3 0.06 ppm (ion chromatography); meets ISO.
- Cechetto 2021 [65]: Pd-Ag 4.61 um, 450 deg C, dP 1 bar. Purity 99.995%, NH3 2.9 ppm by FTIR (Table 10 gives 2.91 ppm; text p. 13 gives 2.9). Does not meet ISO.
- Cechetto 2022 [40]: Pd-Ag 6-8 um, 500 deg C. Purity 99.998%, NH3 < 0.75 ppm (the FTIR limit).
- Cerrillo 2022: Pd-Au 8 um, 350-500 deg C, 4-15 bar. Purity 99.97 +/- 0.03%. NH3 is reported "free", but the micro-GC detection limit is unknown.
- Li 2012: SiO2. Purity 84.0%, NH3 4.5% (45,000 ppm).
- Jo 2018: Pd/Ta, 450 deg C, 6.5 bar. Purity > 99.9999%, NH3 0.8 ppm. The method is inconsistent: Nessler in the text, TDLAS in Table 10.
- Park 2020: Pd/Ta/Pd, 425 deg C, 3 bar. NH3 4.2 ppm, reduced to 1.8 ppm with a 300 cm3 DI-water bubbler.
- Downstream polishing:
  - clinoptilolite reduced NH3 from ~1000 ppm to < 0.025 ppm (Sitar 2022, p. 14);
  - a zeolite 13X bed at ambient conditions gave < 0.75 ppm (Cechetto 2022, p. 14).

## Effects of operating conditions (pp. 10-11; qualitative)
- Higher T raises conversion, recovery and purity. The upper limit is 500 deg C for Pd.
- Higher reaction pressure raises recovery and conversion (through the membrane) but lowers purity.
- Vacuum on the permeate raises conversion and recovery.
- A higher NH3 feed flow lowers conversion and recovery but raises purity.
- Cerrillo 2022 (485 deg C, 200 mLN/min, 10 g Ba-CoCe): conversion and recovery fall as P_ret/P_perm falls (permeate 1-15 bar, retentate 4-50 bar; Fig. 8, no table).

## Other quoted facts
Haber-Bosch: 400-500 deg C, 10-30 MPa, 28-37 GJ/t NH3, 2.0-4.6 t CO2/t NH3, about 400 Mt CO2/yr, about 1.5% of global GHG emissions (p. 19, refs 101-103). Cost per energy stored: 0.54 USD/kg H2 for ammonia vs 14.95 USD/kg H2 for hydrogen (p. 1, ref 1). The context of that cost figure is unclear.

## Limitations
Review of lab-scale experiments: tens of mL/min up to 2.84 L/min NH3. Many values are read from figures (marked a). Membrane permeation is not quantified (no permeance, no Sieverts law). There is no PSA design data. Some internal inconsistencies:
- Table 3 header;
- Cechetto 2021 recovery under vacuum (Table 3 vs Tables 6 and 8);
- Kim 2022 conditions (text: 472 deg C, 2840 mL/min, ~1 um; Tables 6 and 8: 430 deg C, 950 mL/min, Pd 5 um);
- NH3 measurement method for Jo 2018;
- the unit of catalyst utilisation.

## Relevance to AmCraX
1. ISO 14687:2019 limits: NH3 <= 0.1 ppm, N2 <= 300 ppm (vehicle) or <= 50% (stationary). These are product-spec constraints for the PSA/purification block, cited via this review (primary source: ISO 14687:2019).
2. The equilibrium conversions in Table 3 and Fig. 2 (Aspen V11) are external cross-checks for the AmCraX RGibbs and Python equilibrium at 1-5 bar, 325-500 deg C.
3. Membrane-reactor benchmarks (X > 99%, R_H2 90-97.5% at 400-500 deg C, 4-7 bar) support a literature comparison of the membrane option against the AmCraX baseline PSA recovery of 0.85. That baseline is an AmCraX assumption; this review gives no PSA recovery.
4. Heat-integration statement: burning the retentate/off-gas alone is insufficient and supplementary fuel is needed (qualitative).
