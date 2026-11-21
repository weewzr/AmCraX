# richard2024technoeconomic

## Bibliographic data
- **Authors:** Simon Richard, Alvaro Ramirez Santos, Pierre Olivier (ENGIE Lab CRIGEN), Fausto Gallucci (TU Eindhoven).
- **Title:** Techno-economic analysis of ammonia cracking for large scale power generation.
- **Journal:** International Journal of Hydrogen Energy, 71 (2024), pages 571-587.
- **Dates:** received 3 Nov 2023, accepted 19 May 2024, available online 22 May 2024.
- **Licence:** open access, CC BY.
- **DOI:** 10.1016/j.ijhydene.2024.05.308. Verified through the doi.org handle API (responseCode 1).
- **APA 7:** Richard, S., Ramirez Santos, A., Olivier, P., & Gallucci, F. (2024). Techno-economic analysis of ammonia cracking for large scale power generation. *International Journal of Hydrogen Energy, 71*, 571-587. https://doi.org/10.1016/j.ijhydene.2024.05.308
- **Page numbering:** "p. N" means PDF page N. Journal page = 570 + N.

## Scope
The paper compares two ways of cracking NH3 to supply H2 for a 30 vol% H2 / 70 % NH3 fuel blend in a retrofitted CCGT:
- a conventional fired tubular reactor (FTR);
- a Pd-Ag packed-bed membrane reactor (MR).

The reference plant is a GE 9FB-based NGCC with 420 MW net output (p. 4). The required H2 flow is **2600 kmol/h at 30 bar** (p. 4). The cracking island is not heat-integrated with the power island (p. 6). The paper also gives LCOH and LCOE with Monte Carlo uncertainty, and a check of Pd and Ru material scarcity.

## Simulator set-up (pp. 4, 6)
- **Software:** Aspen Plus v11. The property method is **Peng-Robinson**. NRTL is used for the water absorption section.
- **Membrane reactor:** written in Aspen Custom Modeler (ACM) as a 1D steady-state model. It has no radial dispersion and is integrated with Euler steps.
- **FTR:**
  - The reactor tubes use an **RPlug** block with an imposed **parabolic heat-flux profile**, following Makhloufi et al. 2021 [47].
  - NH3 combustion is modelled with a **Gibbs reactor**.
- **Unconverted NH3:** removed by water absorption and stripping, then recycled.
- **FTR purification:** cryogenic rather than PSA, because PSA at this scale would need large pressurised H2 storage at 200 bar. The steps are:
  1. compress to 240 bar in 6 stages with intercooling;
  2. cool in 3 plate-fin heat exchangers;
  3. expand through a Joule-Thomson valve to about 1 bar, reaching about -230 °C so that N2 liquefies [47].
- **MR heat supply:** the retentate is throttled and burned to supply heat, with extra NH3 fuel when needed. The permeate leaves at 1 bar and is compressed to 30 bar.
- **Not covered:** NOx treatment.

## Main assumptions (Table 1, p. 6)
**Reactors**
- Reactor inlet temperature: 400-460 °C.
- Reaction-side pressure: 10-25 bar.
- Permeate pressure: 1 bar.

**Gas turbine**
- Gross power: 280 MW.
- Turbine inlet temperature (TIT): 1360 °C.
- Pressure ratio: 18.
- Isentropic efficiency: turbine 0.87, compressor 0.85 (the table prints the unit "%").

**Steam cycle**
- Evaporation pressures: 130 / 28 / 4 bar.
- Condenser pressure: 0.0509 bar.
- Pinch ΔT (HP / IP / LP): 50 / 30 / 10 °C.

**CO2 compression**
- Delivered at 110 bar with 85 % isentropic efficiency.

**Drives and auxiliaries**
- Driver efficiency: 95 %.
- Generator efficiency: 98.5 %.
- Mechanical efficiency: 99.6 %.

**Heat exchangers**
- Minimum ΔT: gas-water 15 °C, gas-gas 30 °C.
- **U (gas/gas): 60 W/m2/K.**
- **U (gas/liquid): 70 W/m2/K.**

**Pumps and compressors**
- Pump isentropic efficiency 70 %, pump motor 85 %.
- Compressor isentropic efficiency 70 %, compressor motor 85 %.

**Reference natural gas**
- LHV: 46.482 MJ/kg.

## Governing equations
- **Eq. 1, Richardson/Sieverts flux (p. 6):** J_H2 = (Pe/δ)(p_H2,ret^n - p_H2,perm^n), in mol/(s m2).
  - n = 0.5, so the expression is Sieverts' law.
  - A **concentration-polarisation (CP) factor of 0.15** multiplies the flux. This value comes from CFD in [59] Richard et al. 2023 (p. 7).
  - The membrane is assumed to have infinite selectivity, so the permeate is pure H2.
- **Eq. 2, permeability:** Pe = Pe0,H2 exp(-Ea/(R T)).
  - Table 2 (p. 7) lists the fitted values for Pd-Ag membranes:

    | Source | Thickness (μm) | Pe0 (mol m-1 s-1 Pa-0.5) | Ea (kJ/mol) |
    |---|---|---|---|
    | [54] Helmi 2018 | 4.2 | 1.76e-8 | 7.1 |
    | [53] de Nooijer 2018 | 5.2 | 4.57e-8 | 9.23 |
    | [52] Fernandez 2015 | 5 | **6.93e8 as printed (almost certainly a typo for 6.93e-8)** | 9.99 |

  - The paper says the parameters "are sourced from" Fernandez 2015 [52].
- **Eq. 3, reaction:** NH3 <-> 1/2 N2 + 3/2 H2, ΔH = 45.9 kJ/mol.
  - It is printed as "3/3 H2" and labelled "ΔH°f". Both are typos.
- **Eq. 4, rate law (p. 7):** R_NH3 = k0 exp(-E0/(R T)) (p_NH3^2 / p_H2^3)^β.
  - This is a Temkin-Pyzhev-like power law with **no reverse/equilibrium term**.
  - The fitted k0, E, β for Hypermec 10010 (8 % Ru) [60], Alfa Aesar 2 % Ru [41], Ru(3%)-K-CaO [86] and a Ni catalyst [87] are given only in Supplementary S4. **They are not in this PDF.**
  - The nomenclature (p. 2) gives k0 in "mol m-2 s-1 bar0.5". This is ambiguous: it looks like a permeation unit and does not match a per-catalyst-mass rate.
- **Eq. 5, total plant cost:** TPC = (Σ Ci)(1+%TIC)(1+%IC)(1+%C&OC).
- **Eq. 6, cost scaling:** Ci = Ci,0 (Si/Si,0)^f.
- **Eq. 7, capital charge factor:** CCF = i(1+i)^n / ((1+i)^n - 1).
- **Eq. 8, LCOH:**
  - LCOH = [TPC·CCF + C_O&M,fix + C_O&M,var·heq] / [production capacity·heq].
  - The heading prints the unit as €/Nm3, but the results are given in €/kg. Treat the heading unit as a typo.
- **Eq. 9, LCOE:** the same form as Eq. 8, in €/MWh.
- **Eq. 10, conversion:** X = (F_NH3,in - F_NH3,out) / F_NH3,in.
- **Eq. 11, H2 recovery factor:** HRF = F_H2,perm / (1.5·F_NH3,in) × 100.
- **Eq. 12, thermal efficiency:** η_th = (F_H2·LHV_H2 - W_aux) / (F_NH3·LHV_NH3).
  - LHV_H2 = 120 MJ/kg and LHV_NH3 = 18 MJ/kg (p. 10).

## Membrane reactor specification (Table 3, p. 7)
| Parameter | Value |
|---|---|
| Membrane OD | 0.014 m |
| Membrane length | 2.7 m |
| Reactor diameter | 0.7 m |
| Active bed height | 3 m |
| Membranes per reactor | 260 |
| Membrane volumetric coverage | 0.1 |
| Membrane start position | 0.3 m |
| Catalyst density | **980 kg/m3** (not stated whether bulk or particle) |
| Bed porosity | **0.4** (the table labels it "β") |
| CP factor | 0.15 |

Table 8 (p. 15) gives a bed density of 846 kg/m3 for the Sayas et al. Ru-K/CaO catalyst.

## TEA assumptions
**Cost basis (pp. 7, 9; Table 4 p. 7; Table 5 p. 9)**
- CEPCI: 701 (2021).
- Hydrogen-island equipment: Turton 2018 correlations for stainless steel.
- Power-island equipment: DOE/NETL 2007 scaling, with f = 0.3-0.8 (Table 4).
- **CCF: 0.153.** The table labels it "Discount rate CCF". The underlying discount rate and plant lifetime are not stated.
- Capacity factor: 0.65.

**Fixed O&M**
- Maintenance: 2.5 % of TPC.
- Insurance: 2 % of TPC.
- Labour: 6 M€ (no retrofit) or 9 M€ (retrofit). Source for these: [64] Manzolini 2013.

**Variable costs**
- NH3: **450 €/t**.
- NH3 storage: 0.9 (unit unclear; given as €/kg) [84].
- Natural gas: 9.15 €/GJ LHV.
- Water: 6 €/m3 [85].
- Electricity: 60 €/MWh.
- Catalyst: **143 €/kg** [79], with a 5-year life.
- Pd membrane: 6000 €/m2 [83], with a 3-year life.
- Carbon tax (NG CCGT case only): 25 €/t CO2.

**Inconsistency on membrane cost recovery:** Table 5 gives 0.5 × membrane cost, but the text on p. 9 says a recovery factor of 0.8.

**Uncertainty analysis:** Monte Carlo with 10,000 runs per technology and log-normal distributions, following Neveux 2020 [68] and AACE. TRLs are 7 (FTR) and 4-5 (MR).

## Benchmarks / results
- **Fig. 6 (p. 10):** conversion vs temperature for the four catalysts at 10 bar and W/F = 2 kg h/kmol, over 250-550 °C. Curves only.
- **Fig. 7 (p. 11):** at 425 °C and 10 bar with Pperm = 0.1 bar and CP = 0.25, MR conversion is up to 87 % higher than TR at GHSV 500 h-1, and 15 % higher at 4000 h-1. Recovered H2 peaks near GHSV 1000 h-1.
- **Fig. 8 (p. 11):** at W/F = 5, MR conversion is 70 % higher than TR at 10 bar and 36 % higher at 5 bar. The MR needs at least 5-6 bar to outperform the TR.
- **Table 6 (p. 12):** MR optimum for minimum LCOH:

  | Quantity | Value |
  |---|---|
  | NH3 feed | 2046 kmol/h |
  | Pressure | 20 bar |
  | Temperature | 439.4 °C |
  | Number of reactors | 57.05 |
  | GHSV | 570 h-1 |
  | η_th | 0.85 |
  | LCOH | 4.45 €/kg |
  | NOx | 0.018 kg/kg H2 |

  The maximum-efficiency case reaches η_th 0.84 with LCOH 4.48 €/kg.
- **FTR system (p. 14):** η_th **68.5 %**, LCOH **5.1 €/kg H2**.
  - NH3 accounts for 65 % of the FTR LCOH and 70 % of the MR LCOH.
  - Cracking, purification and compression make up 85 % of the FTR TPC.
- **Sensitivity (p. 12):**
  - Raising pressure from 10 to 15 bar lowers LCOH by about 7 %.
  - Raising temperature from 400 to 460 °C lowers LCOH by 4.8 % and the number of reactors by 30 %.
- **CCGT level (p. 15):**
  - NH3 is about 80 % of LCOE.
  - CAPEX contributes about 20.6 €/MWh (FTR), 19.4 €/MWh (CCS) and about 26 €/MWh (MR).
- **Literature values cited (p. 3), not original to this paper:**
  - Makhloufi et al. 2021: FTR LCOH 4.82 €/kg at 450 €/t NH3, 68.5 % efficiency, 200 t/d H2 at 250 bar.
  - Nasharuddin 2019: 4.70 €/kg.

## Limitations
- The fitted kinetic parameters are only in the Supplementary material. Eq. 4 has no equilibrium term.
- The FTR heat flux is imposed rather than modelled from the firebox.
- There is no heat integration with the CCGT. NOx treatment is not included.
- The Table 2 exponent typo and the inconsistent membrane cost recovery reduce confidence in those inputs.
- The CCF basis is not stated.

## Relevance to AmCraX
- **Simulator set-up precedent:** Aspen Plus with PR, RPlug, a parabolic heat flux and a Gibbs-reactor furnace.
- **Heat-exchanger U values:** 60 and 70 W/m2/K.
- **TEA framework:** TPC factors, CCF, LCOH equation and O&M fractions.
- **Benchmarks:** FTR at 68.5 % efficiency and 5.1 €/kg; MR as an alternative.
- **Sieverts membrane parameters** for an optional MR extension.
- **Catalyst cost:** 143 €/kg with a 5-year life.
