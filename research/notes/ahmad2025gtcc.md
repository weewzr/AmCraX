# ahmad2025gtcc - Ahmad et al. (2025): NH3 utilisation in combined-cycle power plants (liquid, vaporised and cracked NH3)

## Bibliographic data
- Authors: Azaria Haykal Ahmad, Taku Tsujimura, Masayasu Shimura, Yong Fan, Hiroshi Ito, Norihiko Iki, Osamu Kurata, Hyun Jo, Muhammad Aziz (corresp.)
- Title: Thermodynamic and preliminary techno-economic analysis of NH3 utilization in combined cycle power plant: Comparison of direct liquid, vaporized, and cracked NH3-based combustion methods
- Journal: International Journal of Hydrogen Energy, vol. 173 (2025), article 151337 (special issue "Integrated Energy Solutions")
- Received 12 May 2025; revised 27 Aug 2025; accepted 1 Sep 2025; online 9 Sep 2025. Open access, CC BY-NC-ND 4.0 (p. 1)
- DOI: 10.1016/j.ijhydene.2025.151337 (verified via doi.org handle API, responseCode 1, resolves to PII S0360319925043393)
- APA 7: Ahmad, A. H., Tsujimura, T., Shimura, M., Fan, Y., Ito, H., Iki, N., Kurata, O., Jo, H., & Aziz, M. (2025). Thermodynamic and preliminary techno-economic analysis of NH3 utilization in combined cycle power plant: Comparison of direct liquid, vaporized, and cracked NH3-based combustion methods. *International Journal of Hydrogen Energy, 173*, 151337. https://doi.org/10.1016/j.ijhydene.2025.151337
- Type: article (simulation study; 22 PDF pages; Supplementary Material not available to us)

## Scope
Aspen Plus V14 process simulation of a 43 MW-class gas-turbine combined cycle (GTCC), based on the Keramasan NGCC plant at PR 8. It is fired with:
- Case 1: liquid NH3 (LNH3)
- Case 2a: vaporised NH3 (VNH3) with a pressurised evaporator at 1 MPa
- Case 2b: VNH3 with an atmospheric evaporator at 0.2 MPa
- NH3/H2-N2 blends from partial to complete cracking, with the cracker heated by turbine exhaust

NOx is modelled with ANSYS Chemkin-Pro 2024R1 (Okafor mechanism: 42 species, 130 reactions) in a reactor network (FZ, PFZ, QZ, LBZ). A preliminary techno-economic model gives the LCOE. Pressure-ratio study: PR 5-30; cracking pressure 5-30 bar.

## Process model (Sec. 2.2, p. 3-6)
- Thermodynamic model PR-BM (Peng-Robinson-Boston-Mathias). Assumptions: steady state; no heat or pressure losses; constant isentropic efficiency; chemical and phase equilibrium in the combustor and cracking reactor. Ambient 25 °C, 1 atm (p. 3).
  - **Inconsistency:** p. 3 says the cracker reaches chemical equilibrium, but p. 5 models it as a kinetic PFR. Sec. 3.3 (p. 17) uses an equilibrium reactor.
- Eq. (1), p. 4: `2NH3 <-> N2 + 3H2  (Δhf 45.6 kJ/mol)`. **Ambiguity:** the value is per mol NH3 (it matches 91.2/2), but it is printed next to the 2-mol equation and labelled Δhf rather than ΔH_r. It is not referenced.
- Cracker conditions:
  - T = 500 °C, chosen because conversion is higher at the same pressure [30]. A CRT sensitivity (Supplementary) shows 500 °C gives "higher efficiency and economic benefits" (p. 5).
  - P = 10 bar, "due to the similar conversion of the Ru catalyst under equilibrium conditions [38]" (p. 5).
  - Table 2 (p. 5): "TCrack = 500 °C and P = 10 bar (adiabatic)". **Ambiguity:** "adiabatic" conflicts with the exhaust-heated reactor in Fig. 2/3.
- Reactor model: PFR with perfect radial mixing and no axial dispersion (Towler & Sinnott 2008 [39]).
- Catalyst: commercial Ru catalyst Hypermec 10010 (TM), 97 % conversion at 10 bar, 500 °C and GHSV 1200 h^-1 (from Di Carlo et al. 2014 [38], Int. J. Hydrogen Energy 39:808-814, doi 10.1016/j.ijhydene.2013.10.110). The product name is as printed, not verified.
- Rate law, Eq. (2), p. 5 (checked against the PDF image). Called "Temkin-Phyzey" [sic], from Temkin & Pyzhev 1940 [40]. Validated in [38], [41] Chiuta et al. 2016 and [42] Prasad et al. 2009.
  - As printed: `r = k * exp(-E0/(R T)) * ( (p_NH3)^3 / (p_H2)^3 )^beta`
  - Symbols: k0 (printed k in the equation) = pre-exponential factor; E0 = activation energy; T = temperature; p_NH3, p_H2 = partial pressures; beta = kinetic order.
  - **Ambiguities:**
    - The NH3 exponent prints as 3. The classic Temkin-Pyzhev decomposition form is (p_NH3^2 / p_H2^3)^beta, so this is probably a typesetting error.
    - k vs k0 naming is inconsistent.
    - **No numerical values of k0, E0 or beta and no units are given in the paper.** They must be taken from the original sources (Di Carlo 2014 / Chiuta 2016 / Prasad 2009).
- Table 2 (p. 5):
  - NH3: m = 4.667 kg/s (= 87.74 MWth), 10 bar. The text uses 4.66 kg/s (p. 6).
  - Air: O2 21 %, N2 79 %.
  - Combustor: Q = 0 kWth, P = 8 bar.
  - Heat exchangers: ΔTmin = 5 °C [35]; T_SHout = 200 °C; T_vent = T_stack = 110 °C; x_EVAout = 1.
  - Expander/compressor/pump efficiency 85 % [36].
  - P2 = 10.2 bar; P_comp,out = 8 bar [30]; P_Turb,out = 1.02 bar [30].
- LNH3 injection at 10 bar and combustion at 8 bar to avoid cavitation (p. 4). The injector keeps a minimum ΔP of 2 bar above saturation (AIST guidance, p. 17).
- From the authors' earlier work [30]: evaporator UA 20,000 W/K and superheater UA 6250 W/K at 400 °C cracking temperature (p. 2-3).
- NH3 latent heat 1.15 MJ/kg at 1 MPa, about 6 % of LHV (p. 9). The introduction says about 7 % (p. 2).
- Combustor modelled with RGibbs. Global primary equivalence ratio 1.15. Maximum TIT about 2000 K (1700 °C) [55]. Combustor exit temperature (CET) is set equal to the TIT.

## Efficiency definitions (p. 6-7)
- NH3 fraction in fuel, Eq. (3): `alpha = NH3 / (H2 + NH3)` (molar). N2 is not counted as fuel.
- Stoichiometric combustion, R1: `alpha NH3 + (1-alpha) H2 + (2+alpha)/2 (O2 + 3.76 N2) -> (2+alpha)/2 H2O + (3.76 + 1.88 alpha) N2`.
  - **As printed.** Check: the H balance gives 3alpha + 2(1-alpha) = 2 + alpha H, i.e. (2+alpha)/2 H2O, which is OK. But the O balance needs (2+alpha)/4 O2, not (2+alpha)/2. The N2 coefficient 3.76 + 1.88 alpha is also inconsistent with (2+alpha)/2 x 3.76 + alpha/2. **The printed coefficients are not balanced; recompute before use.**
  - Confirmed against the PDF image (p. 6). The balanced form is `alpha NH3 + (1-alpha) H2 + (2+alpha)/4 (O2 + 3.76 N2) -> (2+alpha)/2 H2O + (1.88 + 1.44 alpha) N2`. The printed equation doubles the air.
- Eq. (4): `AFR_stoic = m_air,stoic / (m_NH3 + m_H2) = (2+alpha)/2 * (32 + 3.76*28) / (17 alpha + 2 (1-alpha))`, with molar masses in g/mol. It inherits the R1 O2 coefficient issue.
- Eq. (5): `Phi = AFR_stoic / AFR_real = m_air,stoic / m_air,real`.
- Eq. (6): `W_net = W_GT + W_HPST + W_LPST - W_COMGT - W_HPP - W_LPP`.
- Eq. (7): `eta_th = W_net / (m_NH3 * LHV_NH3)`, with LHV_NH3 = 18.8 MJ/kg. The basis is the total NH3 feed, so cracker heat taken from exhaust is internal.

## Economic model (Sec. 2.4, p. 7-8)
- Equation (8): `C_E = (CEPCI_2024 / CEPCI_Ref) * C_Ref * (S/S_Ref)^x`, with CEPCI_2024 = 800.3.
- Equation (9): `TCI = sum(C_E) * (1 + sum f) + CAPEX_NH3cracking`, with sum f = 2.06 (from Li et al. 2021 [53]).
- NH3 cracker CAPEX correlation, Fig. 6, p. 7 (adapted from Cesaro et al. 2021 [47], Appl. Energy 282:116009): `CAPEX [MUSD] = 18.171 * (Size [t-H2/h])^0.7451`, R^2 = 0.9158.
  - Fitted to SMR and NH3-cracker data spanning about 0.007-200 t H2/h.
  - Cost-year basis not stated. The axis label gives MUSD.
  - The paper notes the analogy to SMR is preliminary and that NH3 cracking is at TRL 4-6 [33].
- Table 4 reference equipment, p. 7. Columns: equipment; size basis; S_Ref; x; C_Ref (MUSD); CEPCI_Ref/year; source.
  - GT, generator and auxiliaries: net power; 272.12 MW; 0.3; 49.4; 525.4/2007 [29]
  - HRSG, ducting and stack: UA; 12.9 MW/K; 0.67; 32.6; 525.4/2007 [29]
  - ST, generator and auxiliaries: gross power; 200 MW; 0.67; 33.7; 525.4/2007 [29]
  - Heat exchanger: heat transferred; 57.2 MW; 0.9; 1.64; 576.1/2014 [50]
  - Cooling water and BOP: heat rejected; 470 MWth; 0.67; 1.64; 525.4/2007 [29]
  - Compressor: work; 10 MW; 0.67; 7.3; 607.5/2019 [51]
  - Pump: volume flow; 250 m3/h; 0.14; 0.02; 525.4/2007 [50]
  - NH3 tank: mass; 25000 t; 0.67; 26.1; 607.5/2019 [52]
  - The NH3 tank is sized for a 7-day emergency inventory [49].
- Labour, Eq. (10): `C_Labor = 4.5 * (6.29 + 0.23 N_np)^0.5 * c_Labor`. N_np = number of equipment pieces; c_Labor = 52,900 USD/y per operator [56] (p. 8).
- Other operating costs (p. 8): maintenance 2.5 % of TCI and insurance 2 % of TCI [57]. NH3 price 480 USD/t [54] (Japan Basic Hydrogen Strategy 2023). Sensitivity uses 320 USD/t.
- Equation (11): `LCOE = (TCI*CRF + OC_var*CF + OC_fix) / (CF * W_net)`, with W_net in kWh at full capacity.
- Equation (12): `CRF = r(1+r)^t / ((1+r)^t - 1)`, with t = 25 y and r = 10 % [56].
- Capacity factor CF: **value not stated in the main text.**

## Validation (Sec. 2.5, p. 8)
- The GTCC model on natural gas was validated earlier with a maximum error of 2.65 % [30].
- LNH3 two-stage combustion was checked against Okafor et al. [19] (210 kWth, air at 500 °C, 1090 m3/h at 20 °C). Results: PZ 1934 °C and SZ 921 °C.
- CET vs thermal input from 150 to 210 kWth: maximum relative error 3 % (Table 5, p. 8). Example: 153.0 kWth, phi 0.145, experiment 820.16 °C vs simulation 816.22 °C (0.48 %).
- NO minimum at a global primary equivalence ratio of 1.1-1.2. Chemkin underestimates NO.

## Key results (benchmarks; all are this paper's simulations)
- Table 6 (p. 9), optimum parameters for Case 1 / Case 2a / Case 2b:
  - Thermal efficiency: 47.7 / 49.12 / 48.44 %
  - W_net: 41.87 / 43.1 / 42.5 MW
  - Gas-cycle net power: 28.02 / 29.94 / 30.21 MW
  - Steam-cycle net power: 13.85 / 13.16 / 13.39 MW
  - Compressor: 0 / 0 / 1.086 MW
  - UA_HRSG: 223.27 / 213.32 / 216.9 kW/K
  - Gas flow: 138.17 / 150.52 / 150.52 t/h
  - Share of flue gas to evaporator: 0 / 11.17 / 10.51 %
- Evaporator heat: 5460 kWth (Case 2b) vs 5751 kWth (Case 2a) (p. 9).
- NO: 83.8 / 107 / 116 ppmv for Cases 1 / 2a / 2b (p. 9). The AIST experiments cited give 282 ppmv for LNH3 [19] and 337 ppmv minimum for VNH3 [34]. N2O is 0.18 ppmv (LNH3) and 0.15 ppmv (VNH3).
- Economics (Sec. 3.1.3, p. 11-13; conclusion, p. 18):
  - TCI: 179.23 / 181.25 / 188.61 MUSD (Cases 1 / 2a / 2b).
  - LCOE: 0.2871 / 0.2798 / 0.2876 USD/kWh (conclusion, p. 18).
  - Case 1 LCOE breakdown: TCI 0.0655, OC_var 0.19261, OC_fix 0.02894 USD/kWh.
  - Case 2a breakdown: 0.06433 / 0.18707 / 0.02843 USD/kWh.
  - Case 2b breakdown: 0.06789 / 0.1897 / 0.02995 USD/kWh.
- Cracking ratio study (p. 13-15, 20):
  - The NH3 bypass share is 81.25, 58.76, 48.45, 37.24, 25.02, 11.65 and 0 % for alpha = 0.75, 0.5, 0.4, 0.3, 0.2, 0.1 and 0.
  - Thermal efficiency is about 54 % at alpha = 0 (full cracking, PR 8) (p. 15).
  - TCI rises from 180 MUSD (alpha = 1) to 230 MUSD (alpha = 0), +28 %. The cracking reactor is about 45 MUSD, about 20 % of TCI at alpha = 0. Evaporator plus superheater is about 5 MUSD (p. 15).
  - LCOE is non-monotonic in alpha. Cracking loses its advantage if reactor cost rises by more than 20 %.
  - At an NH3 price of 320 USD/t, pure VNH3 gives 0.217 USD/kWh vs 0.22 USD/kWh with full cracking (p. 15).
  - **Inconsistencies:** the conclusion (p. 20) states "58.6 MW net power at 8 bar PR" for alpha = 0, but 58.6 MW is the PR 30 / CRP 5 bar result in Sec. 3.3 (p. 18). The abstract and conclusion also attribute the 0.22 -> 0.217 USD/kWh numbers inconsistently.
- Pressure study (Sec. 3.3, p. 17-18), alpha = 0.5:
  - Net power rises from 40.09 MW at PR 5 to 52.55 MW at PR 30.
  - With low-pressure cracking (CRP 5 bar) and PR 30: 58.6 MW net (GT 45.6, ST 9.2, H2-N2 compressor -3.8 MW). At CRP 30 bar: 52.59 MW (GT 43.99, ST 8.62).
  - Direct fuel fraction to the combustor: 57.00 / 57.98 / 58.98 / 59.49 % at CRP 30 / 20 / 10 / 5 bar.
  - No intercooling is modelled.
- Equilibrium cracking conversion, Fig. 19(b), p. 19. Aspen Plus equilibrium reactor; feed presumably pure NH3. Read from figure, approximate (±0.3 points):

  | Cracking pressure | 400 °C | 450 °C | 500 °C |
  |---|---|---|---|
  | 1 bar | ~99.7 % | - | ~99.8 % |
  | 10 bar | ~95.5 % | ~97.8 % | ~98.9 % |
  | 30 bar | ~89.6 % | ~94.0 % | ~96.4 % |

  **Discrepancy:** an ideal-gas equilibrium cross-check by this agent (NIST Shomate data, pure NH3 feed; not a project deliverable) gives 92.3 / 81.0 % at 400 °C, 95.7 / 88.6 % at 450 °C and 97.5 / 93.1 % at 500 °C for 10 / 30 bar. Fig. 19(b) is systematically 1.5-8.6 points higher at elevated pressure. PR-BM non-ideality alone is unlikely to explain this. Possible causes are a different feed or basis, or a plotting error. **Do not use Fig. 19(b) as an equilibrium benchmark.** Xu et al. 2025, Fig. 4(a) agrees with the ideal-gas calculation.
- Cracker heat demand: **not reported numerically in the main text.** It is shown only qualitatively, as larger at lower alpha (p. 15). Detailed power and heat breakdown is in the Supplementary Material, which was not available.
- Other context (p. 2, 7):
  - Topsoe offers a commercial NH3 cracking unit up to 500 tpd H2 (Nielsen 2021 [48], Ammonia Energy Conference).
  - Mitsubishi Power is developing a 40 MW-class gas turbine for 100 % NH3 [7,12]. NG combustors are limited to about 30 vol% H2 without modification [7-9].
  - A 2 MW-class GT ran with a 20 cal% NH3 blend [11].

## Literature table (Table 1, p. 3; values quoted from others)
- Juangsa et al. [28] (PR 30, full cracking): power efficiency 43.7 % with lithium nitrohydride vs 48.3 % with Ru-catalysed cracking.
- Richard et al. 2024 [29] (PR 18): a membrane reactor vs fired tubular reactor gives +25 % thermal efficiency and -10 % LCOH.
- Waluyo et al. [32]: combined-cycle efficiency 48.1-49.3 %, NO <100 ppm below 1500 °C.
- Devkota et al. 2023 [26]: thermal efficiency 59 %, fuel saving 22 %, product yield 77 %.
- Makhloufi & Kezibri 2021 [27] (Int. J. Hydrogen Energy 46:34777): fired cracker thermal efficiency 68.5 %, 200 MTPD H2 at 250 bar. LCOH 5.65 EUR/kg now, 3.00 EUR/kg by 2040.
- El-Shafie et al. 2024 [33]: 25 kg H2/day; 6.06 vs 6.39 USD/kg H2; 4.72 USD/kg with N2 co-production.

## Limitations
- Process-level equilibrium/kinetic simulation only, with no experiments on the cracker. The kinetic parameters of the rate law used are not reported.
- Several typographic or internal inconsistencies (Eq. 2 exponent, R1/Eq. 4 coefficients, "adiabatic" cracker, 58.6 MW attribution).
- Cracker heat duty, capacity factor and the CRT sensitivity are only in the Supplementary Material (not reviewed).
- The CAPEX correlation is derived from SMR analogies; the paper states TRL 4-6.
- LNH3 combustion at high pressure has not been demonstrated experimentally (stable only up to 0.25 MPa [16]).

## Relevance to AmCraX
- Gives a fully stated LCOE/TCI methodology (CEPCI scaling, sum f = 2.06, CRF with 10 %/25 y, maintenance 2.5 %, insurance 2 %) and an NH3 cracker CAPEX correlation (18.171 x Size^0.7451 MUSD, Size in t-H2/h). The economics agent can use these as **literature-sourced** inputs, citing Cesaro et al. 2021 as the original data source.
- NH3 price 480 USD/t (base) and 320 USD/t (sensitivity) are literature price points (Japan, 2023).
- Process context: exhaust-heated cracker at 500 °C and 10 bar on Ru, with ΔTmin 5 °C. Lower cracking pressure gives higher conversion, which outweighs the recompression penalty. This is relevant to AmCraX pressure sensitivity (baseline 20 bar).
- Do not use Fig. 19(b) as an equilibrium validation target (see discrepancy). Use Xu 2025 Fig. 4(a) or our own thermodynamics module instead.
