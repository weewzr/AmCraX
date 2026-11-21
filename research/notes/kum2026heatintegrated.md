# kum2026heatintegrated

## Bibliographic data
- Authors: Jaesung Kum, Younghyu Ko, Jae Hun Chang, Chang-Ha Lee (Yonsei University; DogWoodAI Inc.)
- Title: Dynamic modeling and techno-economic analysis of a heat-integrated NH3 cracking plant for cost-effective H2 production under uncertainty
- Journal: Applied Energy, 406 (2026), article 127210. Received 3 Sep 2025, accepted 4 Dec 2025, available online 23 Dec 2025 (p. 1).
- DOI: 10.1016/j.apenergy.2025.127210 (verified via doi.org handle API, responseCode 1)
- APA 7: Kum, J., Ko, Y., Chang, J. H., & Lee, C.-H. (2026). Dynamic modeling and techno-economic analysis of a heat-integrated NH3 cracking plant for cost-effective H2 production under uncertainty. *Applied Energy, 406*, 127210. https://doi.org/10.1016/j.apenergy.2025.127210
- Note: the coordinator brief calls it "Kum et al. 2025" (online year). The volume year printed on the article is 2026, so the citekey uses 2026.
- Page references below are PDF pages. PDF page n = journal page n (the article starts at page 1).

## Scope
Industrial-scale NH3-to-H2 plant: fired tubular cracker (Ru/Al2O3), TSA for trace-NH3 removal (zeolite 4A), lumped 4-bed H2 PSA, furnace burning TSA + PSA tail gas, IP/LP steam-turbine cycle, plant-wide HEN with pinch analysis, TEA with Monte Carlo (500,000 scenarios), and carbon intensity.
Simulation set-up: hybrid model. The cracker and TSA are dynamic models in gPROMS. Pumps, compressors, heat exchangers and flashes are steady-state models in Aspen Plus V14 (p. 4, Sec. 3.1). The paper does not name the Aspen property method.

## Process (Fig. 1, pp. 3-4)
- NH3 feed at 298.15 K and 1 bar, compressed to 13 bar in two stages, preheated in HX2 by flue gas, then sent to the catalytic tubes (p. 3).
- Cracked gas is cooled to 334.15 K and goes to the 3-bed TSA at 10 bar (zeolite 4A). The treated gas is cooled to 298.15 K and goes to a 4-bed PSA that removes N2 (p. 3).
- PSA is a lumped model with an assumed H2 recovery of 80 %, taken from [14] Devkota et al. 2024 and [33] Lee et al. 2025 (p. 3; Appendix I, p. 19).
- Cracker conversion constraint: outlet NH3 mole fraction < 2 % at steady state, so that TSA operation stays stable (p. 3).
- Furnace fuel is TSA + PSA tail gas with 1.2 x stoichiometric O2. The flue gas is at chemical equilibrium, Eqs. 5-9 (p. 5).
- Steam cycle: IP turbine 30 -> 4.2 bar, LP turbine 4.2 -> 1.3 bar [35]. Water is pumped to 30 bar and superheated to 723.15 K in HX1. MITA = 10 K (p. 4).

## Governing equations: tubular cracker (Table 2, p. 5)
Domains: tube (2D, 0<z<Ltube, 0<r<Rin), wall (2D, Rin<r<Rout), flue gas (1D). The boundary conditions are in Supplementary Table S1, which is not in this PDF.

- Reaction (Eq. 1): NH3 -> 1/2 N2 + 3/2 H2
- Kinetics, Temkin-Pyzhev (Eq. 2, p. 4):
  r = ko exp(-Ea/(R T)) [ (P_NH3^2 / P_H2^3)^beta - (P_N2 / Keq^2) (P_H2^3 / P_NH3^2)^(1-beta) ]
  - r is in mol/(g-cat s). P is in bar. ko = 55245.9 mol/g-cat/s*(bar^0.27). Ea = 114224 J/mol. beta = 0.27 (Table 1, p. 5).
  - The authors fitted these parameters to the experimental data of Di Carlo et al. 2014 [37] (Hypermec 10010, 8 wt% Ru). The parameters are original to this paper.
- Keq = exp(-dG_r/(R T)) (Eq. 3). dG_r = 95117 - 193.67 T - 0.035293 T^2 + 9.22e-6 T^3 (Eq. 4, p. 4). This correlation is taken from [18] Realpe et al. 2024.
  - AMBIGUITY: at T = 298.15 K, Eq. 4 gives about 34.5 kJ, which is the value for 2 NH3 -> N2 + 3 H2 (about 2 x 16.4 kJ/mol). The rate law, however, uses Keq^2. This implies Keq is on the per-mol-NH3 basis. The units of dG_r are not printed, and the nomenclature gives R in m3 bar/(mol K). Check the basis numerically before using it.
- Tube mass balance:
  eps_b dCi/dt + eps_b Vz dCi/dz = eps_b D_eff,i [d2Ci/dz2 + d2Ci/dr2 + (1/r) dCi/dr] + nu_i (1-eps_b) rho_cat r
- Tube energy balance:
  [eps_b rho_gas Cp_gas + (1-eps_b) rho_cat Cp_cat] dT/dt + eps_b Vz rho_gas Cp_gas dT/dz = k_eff [d2T/dz2 + d2T/dr2 + (1/r) dT/dr] + nu_NH3 (1-eps_b) rho_cat dH_r r
- Momentum balance (Ergun):
  -dP/dz = 150 mu Vz (1-eps_b)^2 / (dp^2 eps_b^3) + 1.75 rho_gas Vz^2 (1-eps_b) / (eps_b dp)
  - As printed, the inertial term lacks the eps_b^3 in the denominator that the standard Ergun form has. This is likely an extraction or typesetting issue. Check it against the PDF image before use.
- Wall energy balance: rho_w Cp_w dTw/dt = k_w [d2Tw/dz2 + d2Tw/dr2 + (1/r) dTw/dr]
- Flue-gas energy balance (1D):
  rho_fg Cp_fg dTfg/dt + rho_fg Vz,fg Cp_fg dTfg/dz = (4 h_fg / Dout)(Tw(Rout) - Tfg) + (4 sigma_SB e / Dout)(Tw^4(Rout) - Tfg^4)
  - The text extraction shows the first term as d/dz. It is presumably d/dt.
- The heat-transfer coefficient correlations (h_fg, k_eff, D_eff) are in Supplementary Material A, which is not in this PDF. The further-reading list cites Petukhov 1970 for turbulent pipe flow.
- Conversion (Eq. 10): X = [Fin(0) yNH3(0) - Fout(L) yNH3(L)] / [Fin(0) yNH3(0)] x 100
- GHSV (Eq. 16): GHSV = V_STP (m3/h) / V_cat (m3)

## Cracker and catalyst parameters (Table 1, p. 5)
| Item | Value | Unit | Source |
|---|---|---|---|
| L_tube | 3 | m | the authors set the length with pressure drop in mind; the base geometry is from SMR [38] Vo et al. 2019 |
| D_in / R_in | 0.126 / 0.063 | m | [38] |
| D_out / R_out | 0.146 / 0.073 | m | [38] |
| Number of tubes | 336 | - | [38] |
| Flue-gas zones | 96 | - | [38] |
| Tube spacing factor | 2.05 | - | [19] Cho et al. 2024 |
| rho_wall | 7720 | kg/m3 | Table 1 |
| Cp_wall | 502 | J/kg/K | Table 1 |
| k_wall | 29.58 | W/m/K | Table 1 |
| eps_b | 0.36 | - | catalyst [36,37] |
| rho_cat | 980 | kg/m3 | used as (1-eps_b) rho_cat, so it is a particle density, not a bulk density. Not stated explicitly. |
| d_p | 0.0006 | m (printed "M") | 0.6 mm bead |
| k_cat | 44 | W/m/K | |
| Cp_cat | 890 | J/kg/K | |
| dH_r,298 | 46110 | J/mol | |
| ko | 55245.9 | mol/g-cat/s*(bar^0.27) | fitted in this paper |
| Ea | 114224 | J/mol | fitted in this paper |
| beta | 0.27 | - | fitted in this paper |
Catalyst: commercial Ru (8 wt%)-Al2O3 beads, Hypermec 10010 (ACTA) (p. 4). The kinetics are valid for 623.15-773.15 K (p. 7).

## Kinetic validation (p. 9, Fig. 4)
- Data: Di Carlo et al. 2014 [37]. 36 points at 623.15-723.15 K, 1-10 bar, GHSV 300 and 2400 h-1.
- Fit statistics: MAPE 0.81 %, R2 0.80, RMSE 1.81. With 2 outliers removed: MAPE 0.41 %, R2 0.98, RMSE 0.61.
- Reactor model check against the adiabatic PFR profiles of Devkota et al. 2024 [14]: within 2 %.

## Cracker results (benchmarks, pp. 10-12)
Base condition: GHSV 1800 h-1, preheat 623.15 K.
- Heat duty: 79.25 kJ/mol NH3 (p. 1, p. 12).
- Steady-state NH3 conversion: 96.3 %. Outlet NH3 < 2 mol% (p. 10).
- Hot spot: maximum 705 K at z = 0.5 m. The hot region spans 0.1-1.5 m. The outlet is about 650 K (p. 10).
- Pressure drop: more than 2 bar (13 bar inlet -> about 10 bar at the TSA) (p. 12, Fig. 6b).
- 95.9 vol% of the furnace flue gas goes to the cracker (p. 12).
- Start-up to steady state takes 4000 s (base), 3800 s (773.15 K preheat) and 4500 s (GHSV 1200 h-1). The NH3 lost during start-up is 656.9 kmol, worth 5594 USD (p. 10, p. 12).

## TSA model (Tables 3-4, pp. 5-6)
- Bed geometry: length 0.9 m, ID 1.5 m, OD 1.8 m. Three beds. Cycle steps AD-HT-IDLE-CL-PG. Cyclic steady state is taken after 50 cycles. Purge-to-feed (P/F) ratio = 0.1 on an H2 basis (Eq. 11).
- Zeolite 4A properties [40] Bhadra 2012 and [26] Vo et al. 2023: dp 0.002751 m, rho_app 1110.15 kg/m3, rho_sk 2413.37 kg/m3, Cp 850 J/kg/K, k 0.125 W/m/K, eps_b 0.301, eps_t 0.6784.
- Toth isotherm: q_eq,i = q_s,i b_i P y_i / [1 + (sum b_i P y_i)^t_i]^(1/t_i), with b_i = b_o,i exp(B_i/T), t_i = t_o,i + C_i/T, and LDF dq/dt = omega_i (q_eq - q).
  - N2: q_s 1.9472 mol/kg, b_o 5.43e-8 Pa-1, B 1343.91 K, C 0, t_o 1, omega 0.0005 s-1, dH_ad 11000 J/mol.
  - H2: q_s 3.2916, b_o 6.62e-8, B 0, C 0, t_o 1, omega 0.005, dH_ad 7500.
  - NH3: q_s 11.999, b_o 4.27e-9, B 5769.508, C 2.685, t_o 0.22, omega 0.189, dH_ad 50110.
  - Source for all: [26,40].
- Validation: NH3 breakthrough 3250 s vs 3300 s in [26]. Energy 66.28 vs 70.55 kJ/mol NH3 for TSA-N in [26] (p. 10).
- Results at cyclic steady state (Table 7, p. 12):
  - Cracked gas: 1160.38 kmol/h at 334.15 K and 10.03 bar. Composition N2 0.245, H2 0.736, NH3 0.019.
  - Treated gas: 1122.08 kmol/h, N2 0.250, H2 0.750, NH3 0.000.
  - Air: 124.00 kmol/h.
  - Tail gas: 162.30 kmol/h at 396.85 K.
  - Electricity 375.53 kW (61.32 kJ/mol NH3). Heat 220.97 kW (36.08). Cooling 222.44 kW (36.32). The normalisation is per mol of NH3 removed.
  - H2 recovery: 98.57 %.

## HEN / pinch results (p. 13, Figs. 8-9)
- MITA 10 K. Minimum cooling duty 3871 kW. Maximum waste-heat-recovery (WHR) potential 6081 kW.
- Recovered heat: conventional plant 1108 kW (18.22 %), HEN plant 5750 kW (94.56 %).
- The HEN uses HX1 (steam), HX2 (feed preheat), HX3 (TSA heating air to 623.15 K, which replaces the fired heater), HX4 (fuel preheat), HX5 (compressed-air cooling recovered into the steam cycle) and HX6 (cracked-gas cooling recovered into the steam cycle).
- Net energy: 36.79 kJ/mol NH3, 37.1 % below the conventional plant (p. 15).
- NHC (Eq. 18): 79.18 % (conventional) and 82.93 % (HEN). Energy conversion rate (Eq. 19): 79.58 % and 84.19 % (p. 15).
- Energy losses: 11.66 MW (conventional) and 8.62 MW (HEN) (p. 15).
- Appendix I (p. 19): H2 production is 673.24 kmol/h at 80 % PSA recovery, with 690.46 kW of power generation. At 76 % recovery: 639.58 kmol/h and 1308.58 kW.

## TEA inputs (Table 5, p. 8; Table 6, p. 9; text p. 7)
- Plant life 25 y. Operating capacity 80 % (7000 h/yr). Discount rate 10 %. Depreciation 7 %. CRF 0.11.
- CEPCI: 532.9 (2010) and 720.2 (2024). Material factor 3 (SS). Pressure factor 1.5 (7-50 bar). The cracker and furnace PEC use Towler & Sinnott [43], Eq. 20: PEC = (a + b S^n)(CEPCI2024/CEPCIbase) Fm FP. The paper does not list the a, b and n values. The furnace is costed as a 35 MW cylindrical furnace.
- Catalyst: 25 USD/kg for 4 wt% Ru [14], extrapolated to 8 wt% (the extrapolated value is not stated).
- Other PECs come from Aspen Process Economic Analyzer V14. TCI uses Peters' method.
- OPEX unit costs:
  - NH3 0.5 USD/kg (base; close to the DOE value of 0.475 USD/kg [45]).
  - Fired heat 4.25e-6 USD/kJ (natural gas basis).
  - Cooling water 2.12e-7 USD/kJ.
  - Electricity 0.0775 USD/kWh.
  - Maintenance 5 % of FCI. Local tax 2.5 % of FCI. Insurance 0.7 % of FCI.
  - Operating labour 10 % of OPEX. Supervision 10 % of OL. Operating supplies 10 % of M. Laboratory 10 % of OL.
  - Overhead 50 % of (M+OL+S). Administration 15 % of (M+OL+S).
  - Distribution and selling 3 % of OPEX. R&D 3 % of OPEX.
- CAPEX breakdown (% of FCI): PEC 27, installation 8.1, instrumentation 6.8, piping 13.5, electrical 7, buildings 5, yard 3, service facilities 7, engineering 6.5, construction 7, legal 0.6, contractor 4.5, contingency 8, working capital 15.
- Selling prices: H2 9 USD/kg [14]. Electricity 0.0625 USD/kWh (EIA 2023 wholesale) [47].
- Monte Carlo (Table 6, normal distributions, mean ± SD):
  - Electricity cost 0.0775 ± 0.03 USD/kWh.
  - Wholesale price 0.0625 ± 0.02 USD/kWh.
  - Discount rate 10 ± 3 %.
  - H2 price 9 ± 3 USD/kg.
  - NH3 price 0.5 ± 0.05 USD/kg.
- Equations: H2 cost (Eq. 22) = (CAPEX+OPEX)/(H2 kg/h x h/yr). Revenue (Eq. 23). Specific profit (Eq. 24). Depreciation (Eq. 25) = FCI (1-d)^(n-1) d. Cash flow (Eq. 26). NPV (Eq. 27). CRF (Eq. 21).

## TEA results
- Most probable H2 cost: 6.44 USD/kg. Specific profit: 0.35 USD/kg NH3. NPV: 244 MUSD. More than 80 % of cases are profitable and more than 78 % have NPV > 0 (pp. 16-17).
- The sensitivity index of H2 cost to NH3 price is 0.988 (p. 17).
- Uniform distribution: mean 6.53 USD/kg (range 6.20-6.83). Triangular distribution: mode 6.52 USD/kg (p. 17).
- Table 8 (p. 17), H2 cost vs NH3 price [45]:
  | NH3 price (USD/kg) | NH3 source | H2 cost (USD/kg) |
  |---|---|---|
  | 0.284 | NG without capture | 4.34 |
  | 0.343 | NG with capture | 4.93 |
  | 0.918 | nuclear | 10.74 |
  | 1.055 | renewable | 12.13 |
  | 0.475 | DOE | 6.27 |
  | 0.27 | long-term target | 4.2 |

## Environmental (p. 17)
- Grid emission factor 0.207 kg CO2/kWh [53,54]. Cracking stage: 0.38 kg CO2/kg H2.
- An NH3 footprint of 0.2-3.4 kg CO2/kg NH3 gives 1.87-25.7 kg CO2/kg H2. The break-even footprint for the 4 kg CO2/kg H2 threshold is 0.486 kg CO2/kg NH3.
- Flue gas: NO 0.291 ppm, NO2 0.052 ppm. N2O 2.85e-8 kmol/h, equivalent to 3.01 kg CO2/yr at GWP 300.

## Limitations
- The PSA is lumped (fixed 80 % recovery, no purity or cycle model).
- The supplementary boundary conditions and heat-transfer correlations are not available in this PDF.
- The Keq basis is ambiguous (see above).
- The kinetics are validated only up to 723.15 K and 10 bar, but are applied up to 773.15 K and 13 bar.
- GHSV is limited to ≤1800 h-1 by the pressure drop over 0.6 mm particles.
- The PEC correlation coefficients are not given.
- The Aspen property method is not stated.

## Relevance to AmCraX
This is the most complete source for:
- a Ru/Al2O3 Temkin-Pyzhev rate law with fitted parameters that can be used in an Aspen RPlug LHHW/user kinetic block;
- tube geometry for a multi-tube fired cracker;
- a pressure-drop benchmark;
- duty benchmarks (79.25 kJ/mol NH3, X = 96.3 %);
- TSA performance;
- the HEN/pinch target (94.56 % of WHR);
- a full Peters-method TEA factor table plus Monte Carlo distributions.

The Ergun and Keq points must be checked before implementation.
