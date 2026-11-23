# lucentini2021nirukinetic

## Bibliographic data
- Authors: Ilaria Lucentini, German Garcia Colli, Carlos D. Luzi, Isabel Serrano, Osvaldo M. Martinez, Jordi Llorca
- Title: Catalytic ammonia decomposition over Ni-Ru supported on CeO2 for hydrogen production: Effect of metal loading and kinetic analysis
- Journal: Applied Catalysis B: Environmental, 286 (2021), 119896.
- DOI: 10.1016/j.apcatb.2021.119896
- APA 7: Lucentini, I., Garcia Colli, G., Luzi, C. D., Serrano, I., Martinez, O. M., & Llorca, J. (2021). Catalytic ammonia decomposition over Ni-Ru supported on CeO2 for hydrogen production: Effect of metal loading and kinetic analysis. *Applied Catalysis B: Environmental, 286*, 119896. https://doi.org/10.1016/j.apcatb.2021.119896
- Text read: accepted-manuscript postprint from the UPCommons repository (Universitat Politecnica de Catalunya), accessed 23 November 2026. Page numbers below are postprint pages (36 pages), not journal pages.

## Catalysts and experiments (Sec. 2.3, p. 6-7; Table 1, p. 10)
- Six Ni-Ru/CeO2 catalysts by co-impregnation on nanopolycrystalline CeO2. Kinetics fitted for 5Ni1Ru/CeO2 (Ni 4.98, Ru 0.64 wt% by ICP-MS) and 2.5Ni0.5Ru/CeO2 (Ni 2.39, Ru 0.35 wt%).
- 0.1 g catalyst powder (d_cat 0.10 mm) mixed with SiC (d_P 0.37 mm), bed volume about 0.41 cm3, stainless-steel tube d_i 4.572 mm, 1 atm, MS analysis (+/-5 %).
- Temperature runs 350-600 degC in 50 K steps, Ar:NH3 = 1.2:1, total 25 mL/min (F/W 15.0 L g^-1 h^-1, GHSV 3660 h^-1). Also F/W series (25, 50, 75 mL/min), NH3 50/60/70 % at F/W 30, H2 co-feed 0-67.5 % and N2 co-feed 0-67.5 % at 10 % NH3, F/W 30 (GHSV 7320 h^-1).
- Gas-volume reference state of mL/min is not stated.
- Blank (empty reactor, SiC, bare CeO2): 4, 9, 24 % conversion at 400, 450, 500 degC (p. 10). Subtraction from the catalyst data is not stated.

## Table 1 conversions at F/W 15.0 L/(g h), Ar:NH3 1.2:1, 1 atm (p. 10)
| Catalyst | 400 degC | 450 degC | 500 degC | TOF_H2 400 degC (1/s) |
|---|---|---|---|---|
| 10Ni2Ru | 35.1 | 84.5 | 99.2 | 0.88 |
| 5Ni1Ru | 36.5 | 86.1 | 99.6 | 1.01 |
| 2.5Ni0.5Ru | 49.7 | 88.7 | 99.2 | 2.00 |
| 2.0Ni0.4Ru | 36.2 | 81.2 | 98.4 | 1.57 |
| 1.5Ni0.5Ru | 41.9 | 86.3 | 97.8 | 2.44 |
| 2.5Ni0.3Ru | 23.2 | 73.4 | 98.1 | 1.11 |

## Kinetic model (Sec. 2.4 p. 8-9; Sec. 3.3 p. 21-25)
- Reactor model for the fit: isothermal 1-D pseudo-homogeneous PFR, no axial dispersion, no interfacial gradients (Eqs. 2-4); internal heat and mass transfer resistances checked negligible. rho_ap 1651.8 kg/m3 (MIP), f_v 0.606e-7/3.095e-7, V_L 4.095e-7 m3, eps_L 0.2451 (Eq. 5, Dias et al.), eps_av 0.3855 (Eq. 6, Mariani et al.).
- Fit: unweighted nonlinear regression (MATLAB nlinfit) on conversion; confidence intervals by nlpredci.
- Mechanism Eqs. 8-13; N2 desorption irreversible (no N2 effect, Fig. 3b), H2 desorption reversible (H2 inhibition, Fig. 3a). Best model (Table 2): rate-determining step 2, the first dehydrogenation NH3(a) + s -> NH2(a) + H(a).
- Eq. 17: r = k K1 C_NH3 / (1 + K1 C_NH3 + sqrt(C_H2 / K4))^2, r in mol NH3 g_cat^-1 s^-1, C in mol m^-3.
- Eq. 18: k = k0 exp(-Ek/(R T)).
- Table 3 (p. 24):
  | Parameter | 5Ni1Ru/CeO2 | 2.5Ni0.5Ru/CeO2 |
  |---|---|---|
  | k0 (mol NH3 g^-1 s^-1) | 3.9e6 +/- 0.7e6 | 3.3e5 +/- 0.8e5 |
  | Ek (kJ/mol) | 124 +/- 8 | 107 +/- 11 |
  | K1 (m3/mol) | 1.1 +/- 0.2 | 1.2 +/- 0.3 |
  | K4 (mol/m3) | 4.7e-2 +/- 0.1e-2 | 4.5e-2 +/- 0.2e-2 |
- K1 and K4 are temperature independent as published. The law is irreversible (no equilibrium term). The paper calculated the equilibrium constant only to check the equilibrium limit.
- Parity plots within +/-10 %, most within +/-5 % (Fig. 9). Fig. 10: simulated pure NH3 at 1 atm on 2.5Ni0.5Ru: > 99 % conversion at 450 degC with F/W 3.2 L/(g h); 13.5 L_H2/(g h) at 500 degC and F/W 9 L/(g h).
- Literature values quoted (not this work): Ni/CeO2 71 kJ/mol and Ni/Al2O3 99.5 kJ/mol (Deng et al.), Ru/CeO2 149.2 kJ/mol (Hu et al.).

## Applicability limits
- 1 atm only; 350-600 degC; NH3 10-100 % in Ar; H2 up to 67.5 %. Use at 20-40 bar is an extrapolation of a concentration-based law.
- Powder kinetics (0.1 mm): industrial pellets need an effectiveness factor.
- Stability: 2.5Ni0.5Ru loses about 2 % in 100 h at 450 degC; 5Ni1Ru stable (Fig. 2a).

## Implemented in AmCraX
- backend/amcrax/data/kinetics.yaml `research_catalysts.nire_ceo2_5ni1ru_lucentini_lhhw` and `nire_ceo2_2p5ni0p5ru_lucentini_lhhw`; rate in backend/amcrax/kinetics/rate_laws.py `lucentini_rate_mol_per_g_s`; AmCraX equilibrium approach factor (1 - Q/Kp) applied by default (labelled assumption, switchable).
- Reproduction of Table 1: results/research/kinetics/validation_5Ni1Ru_CeO2.json, validation_2p5Ni0p5Ru_CeO2.json. The Table 1 points are part of the fitting data, so this is a consistency check, not an independent validation.
