# Phase 2 task X1: feed/effluent exchanger (FEHE) sizing, cost and net benefit

Script: `scripts/research/heat_exchanger_study.py`. Module: `backend/amcrax/heat_integration/exchanger.py`.
Results: `results/research/heat_exchanger/heat_exchanger_study.json`, `fehe_duty_diagnosis.json`;
validation `results/research/validation/heat_exchanger.json`; figures `results/figures/research/heat_exchanger_*.png`.
No Aspen run. Economic basis: unified reference scenario (frozen; LCOH 4.015 USD/kg), FX 1.288444 SGD/USD (ECB, 20 Nov 2026).

## 1. Why Python FEHE duty is 3.4-4.4 % above Aspen (HCAT-ASPY-*-HI-heat)
The offset is +20.8 kW in every case. It splits exactly into two model-form parts:

| Part | kW | Cause |
|---|---|---|
| Vaporiser outlet state S2 | +8.76 | Both models specify dew point + 10 K. Python dew point (Raoult, CoolProp Psat) 60.09 degC; Aspen PENG-ROB with its NH3-H2O binary 65.90 degC. Python S2 is 5.81 K colder, so the FEHE does more of the heating (the vaporiser does 25.8 kW less). |
| Cold-side residual enthalpy | +12.1 | Python uses the reference EOS (CoolProp, Gao 2020) NH3 residual: -39.8 kW at S2 against -28.3 kW for PR. Aspen uses PENG-ROB. |

On the PR basis at the Aspen S2/S3 states, Python reproduces the Aspen duty within 0.12 %; the hot side (PR) agrees within 0.05 %.
Both choices are documented in `process_model/properties.py` and `flowsheet.py`. They are model-form differences, not implementation
errors, so the five checks stay failing and the 3 % tolerance is unchanged. A change would alter stored flowsheet results (and the
reference-EOS residual is the more accurate one for pure ammonia), so none was applied. The exact change, if the orchestrator wants
Aspen-like behaviour: in `flowsheet.py` FEHE `coldH`, use `pp.gas_enthalpy_kW(n_feed, T, Pb, "pr")` (offset falls to 1.4-1.9 %, from the S2
state alone). That change was not applied.

## 2. U (overall heat-transfer coefficient), typical-range values
- VDI Heat Atlas (2010), ch. C3: shell-and-tube, gas ~1 bar / gas ~1 bar 5-35 W/(m2 K); high-pressure gas (200-300 bar) both sides
  150-500 W/(m2 K) (read from a search excerpt; same on engineeringtoolbox.com).
- No sourced value at 20 bar was found. Cases used: low 35 (top of the 1-bar range), high 150 (bottom of the high-pressure range),
  central 72.5 (their geometric mean; a derived number, not a sourced one). The Phase 1 50 W/(m2 K) assumption is kept for comparison only.

## 3. Cost correlations
- Central: Turton et al. (2018) App. A, fixed-tube-sheet exchanger: log10 Cp0 = 4.3247 - 0.3030 log A + 0.1634 (log A)^2, A 10-1000 m2,
  CEPCI 397 (2001). Pressure factor (both sides, 19.5 barg) 1.07. SS/SS FM 2.73. Bare module B1 1.63, B2 1.66.
- Cross-check: Towler and Sinnott (2013) U-tube, 28,000 + 54 A^1.2 USD (Jan 2010, CEPCI 532.9), SS 1.3, Hand factor 3.5.
- Escalation to 2024 (the cost year of the reference CAPEX): CEPCI 797.9 (chemengonline 2023 annual average; 2024 "just below 800").
  Library values conflict (Kum 720.2, Ahmad 800.3); both are run as sensitivities.
- TCI-equivalent = installed cost x 1.4336 (reference OSBL, engineering and contingency). This is conservative, because Turton's
  bare-module cost already holds some indirect costs.
- Turton and Towler coefficients are transcribed from the textbooks. They were not re-checked against page images in this session.

## 4. Key results (baseline, Aspen 600 degC)
- Q 612.2 kW. Hot side 600 -> 228.4 degC, cold side 75.9 -> 550 degC. There is a temperature cross, so a 1-2 shell is infeasible.
  The design uses 5 x 1-2 shells in series, F 0.84, LMTD 91.9 K, segmented UA 7.32 kW/K.
- Area: 249 / 120 / 58 m2 at U 35 / 72.5 / 150.
- Cost (Turton, multi-shell):

  | | Low U | Central U | High U |
  |---|---|---|---|
  | Purchase (MUSD) | 0.56 | 0.49 | 0.45 |
  | Installed (MUSD) | 1.24 | 1.08 | 1.00 |
  | TCI-equivalent (MUSD) | 1.78 | 1.54 | 1.44 |
  | TCI-equivalent (MSGD) | 2.30 | 1.99 | 1.85 |

- One counter-current unit (F = 1, single tube pass) would have a TCI-equivalent of 0.35-0.59 MUSD.
- Fuel saving from heat integration is 0.2138 USD/kg: heat fuel 0.2119 plus cooling water 0.0019. The annualised FEHE cost is
  0.118-0.147 USD/kg (multi-shell) or 0.029-0.049 USD/kg (counter-current).
- The net benefit is +0.067 / +0.087 / +0.095 USD/kg (multi-shell, low / central / high U). The saving survives the exchanger cost.
- Break-even FEHE TCI is 2.59 MUSD (3.34 MSGD). Break-even U is 11.3 W/(m2 K) with Turton and 7.8 with Towler.
- The net benefit is negative in four sensitivity corners:
  - U = 10;
  - NH3 at 300 USD/t with U 35;
  - CRF 0.199 (15 %, 10 yr) with U 35;
  - approach 20 K with U 35.
- Catalyst design cases (10 cases, Aspen at T_op and Python at T_opt): the saving is 0.20-0.26 USD/kg, the net benefit is
  +0.071 to +0.137 USD/kg, and the break-even U is 7.7-10.7 W/(m2 K).

## 5. Reference CAPEX comparison
The reference item `heat_exchangers` has a TCI of 2.09 MUSD. It covers all exchangers of the Cho plant and does not respond to area.
The FEHE alone is 69-85 % of that item in the multi-shell design and 17-28 % as one counter-current unit.

The two estimates are consistent in order of magnitude. If the multi-shell design is used, the reference item looks low for the whole
exchanger set. This is not a validation.
