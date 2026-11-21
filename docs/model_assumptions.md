# AmCraX assumption register

This register is compiled from the code and the parameter files of the repository (version 0.1.0). It has one table per model layer.
"Source" is either a citation key (`research/references.json`, page and table locator as recorded in the parameter file),
`literature`/`assumption` as labelled in the file (the same labels as `amcrax.schemas.DataSource`), or "design basis (no citation recorded)"
where the file states a value without a source. Rationales are quoted or paraphrased from the files named in the "Where" column; none are
added here. "Impact" is qualitative and limited to what the files or validation documents say; quantitative effects are in the results files named in the tables, which are regenerated
when a model changes (see [reproducing.md](reproducing.md)).

Conventions: `CaseInputs` = `backend/amcrax/schemas.py` (line numbers refer to that file at writing time); YAML keys are given as
`file: path.to.key`. The limitations that follow from these assumptions are in [known_limitations.md](known_limitations.md).

## 1. Flowsheet design basis (Aspen Plus V15 model and Python mirror)

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| Plant basis (feed) | 100 | kmol/h NH3 feed | `CaseInputs.feed_total_kmol_h` (schemas.py:58) | design basis (no citation recorded); `flowsheet.json` "basis 100 kmol/h" | Linear scale of flows/duties; the Aspen sweep `results/sensitivity/aspen_feed_rate.csv` checks scaling. Absolute size does not change specific quantities |
| Feed state | saturated liquid, 1.013 bar (about -33 degC) | - | `config/flowsheet.json: feed.condition`; `inp_writer.FEED_PRESSURE_BAR` (inp_writer.py:48) | design basis: refrigerated storage | Sets the vaporiser duty |
| Feed water | 0.002 (0.2 mol%) | mole fraction | `CaseInputs.feed_h2o_mole_frac` (schemas.py:59); `flowsheet.json: feed` | design basis; Aspen study `aspen_feed_water.csv` varies it | Small effect on duties; treated as inert in the cracker |
| Reactor temperature | 600 | degC | `CaseInputs.reactor_temperature_C` (schemas.py:60); `config/scenarios.json` baseline rationale | "High-temperature operation typical of Ni-based catalysts" (scenarios.json) | Dominant lever on equilibrium conversion and duty (`aspen_temperature.csv`) |
| Reactor pressure | 20 | bar | `CaseInputs.reactor_pressure_bar` (schemas.py:61) | scenarios.json: "PSA-compatible pressure" | Higher P lowers equilibrium conversion, lowers downstream compression need |
| Reaction set / products | NH3 <-> 0.5 N2 + 1.5 H2; H2O inert; components NH3, H2, N2, H2O, O2 | - | `flowsheet.json: components`; `schemas.COMPONENTS`; `inp_writer.py` CRACKER RGIBBS | design basis (single net reaction, no NOx / hydrazine / side products) | Neglects any side reaction; fine for NH3 cracking at the studied T,P |
| Cracker model | isothermal RGibbs (equilibrium), outlet at reactor pressure | - | `flowsheet.json: blocks[CRACKER]`; `inp_writer.py:193` | design basis. Not kinetics-limited, not catalyst-specific | Upper bound on conversion at given T,P; no catalyst mass or approach to equilibrium (see section 5 for the PFR) |
| Pressure profile | pump +1.0, vaporiser +0.8, HEATER +0.2, cracker outlet 0, FEHE drops 0.3 + 0.3 (hot and cold), COOLER -0.5, H2PROD -1.0 | bar relative to reactor | `inp_writer.DP` (inp_writer.py:33-41); `flowsheet.json: pressure_profile_bar_relative_to_reactor` | design basis (no citation recorded) | Fixes stream pressures for all cases; model valid for P >= `MIN_FLOWSHEET_PRESSURE_BAR` = 3 bar (inp_writer.py:30) |
| Tail-gas / air / burner / flue pressures | 1.3 / 1.3 / 1.2 / 1.1 | bar abs | `inp_writer.py:42-45` | design basis | Minor |
| Vaporiser superheat | 10 | K | `inp_writer.VAPORIZER_SUPERHEAT_K` (inp_writer.py:46) | flowsheet.json: "so that the downstream exchanger handles single-phase gas" | Small effect on vaporiser duty |
| Pump efficiency | 0.75 | - | `inp_writer.PUMP_EFFICIENCY` (inp_writer.py:47) | ASSUMPTION: "typical centrifugal-pump efficiency" (process_model/flowsheet.py docstring), same value in the Python model | Pump power is a small fraction of duties |
| FEHE hot-end approach | 50 | K (hot inlet minus cold outlet) | `CaseInputs.fehe_hot_end_approach_K` (schemas.py:63) | design basis; Aspen study `aspen_fehe_approach.csv`; optimisation range 20-150 K | Trades recovered heat against exchanger area |
| Heat integration | on (FEHE present) | - | `CaseInputs.heat_integration` (schemas.py:62) | design option; `baseline_no_hi` is the paired case | Reduces external heating; see `results/figures/aspen_heat_integration_vs_none.png` |
| FEHE feasibility guard | cold-outlet minimum = NH3 saturation temperature at the vaporiser outlet pressure + vaporiser superheat + 25 K; 120 degC if CoolProp is unavailable | degC | `inp_writer.fehe_cold_outlet_minimum_C`, `FEHE_GUARD_MARGIN_K` (inp_writer.py) | engineering margin: about 15 K for the dew-point rise caused by the feed water plus a 10 K minimum driving force (comment in inp_writer.py). Pressure dependent | Rejects specifications the fixed topology cannot represent; the guard is a screening estimate, not a heat-exchanger design |
| PSA feed temperature | 40 | degC | `CaseInputs.psa_feed_temperature_C` (schemas.py:64) | design basis; matches the Cho et al. PSA inlet 40 degC (separation.yaml: psa.operating_points[cho2026_5A]) | Sets COOLER duty |
| PSA H2 recovery | 0.85 | fraction | `CaseInputs.psa_h2_recovery` (schemas.py:65) | assumption; separation.yaml: `psa.amcrax_baseline` "No local source supports 0.85 numerically (literature 0.71-0.81); kept only so the Aspen baseline can be reproduced" | Direct lever on H2 yield, tail-gas heat and LCOH (`aspen_psa_recovery.csv`) |
| PSA N2 slip | 0.001 | fraction of N2 in PSA feed to product | `CaseInputs.psa_n2_slip` (schemas.py:66) | design basis | Sets the H2 purity of the reduced-order PSA |
| PSA model | component splitter (`Sep` block) | - | `flowsheet.json: blocks[PSA]`; `inp_writer.py` PSA FRAC | design basis: "NOT a designed adsorption model" | No cycle, bed count, energy or pressure-swing penalty (see section 6) |
| Burner | complete combustion, adiabatic, excess air 0.15 | fraction over stoichiometric | `CaseInputs.burner_excess_air` (schemas.py:67); `inp_writer.py:209` (RSTOIC, DUTY=0) | design basis | NOx / N2O not modelled (environmental.yaml: heating.ammonia_self_firing note) |
| Air | 25 degC, 79 mol% N2 / 21 mol% O2 | - | `flowsheet.json: air` | design basis | - |
| Stack temperature | 150 | degC | `CaseInputs.stack_temperature_C` (schemas.py:68) | design basis | Sets recoverable flue-gas heat |
| Aspen property method | PENG-ROB | - | `CaseInputs.property_method` (schemas.py:69); `flowsheet.json: property_method` | selection discussed in `docs/technical_report/sections/09_property_methods.md` | See section 2: ideal vs PR differences quantified in `docs/validation/discrepancy_analysis.md` |
| Tail-gas combustion heat (KPI) | `max(-Q_FLUEHX, 0)`: the heat released while the burner flue gas cools to the stack temperature | kW | `amcrax.kpis` (`tailgas_combustion_heat_kW`) | definition of the KPI | Used in the net fuel-heat deficit (first-law credit only) |
| Lower heating values | H2 241.826, NH3 316.80 | kJ/mol | `schemas.LHV_KJ_PER_MOL` (schemas.py:41) | derived from standard enthalpies of formation at 298.15 K, gaseous water product (comment in schemas.py) | Efficiency and CI use these |
| Molar masses | IUPAC 2021 rounded | kg/kmol | `schemas.MOLAR_MASS` (schemas.py:31) | IUPAC standard atomic weights | - |
| Steady state, nominal operation | - | - | whole model | design basis | No start-up, turn-down or dynamics |

## 2. Thermodynamics (independent Python model, `amcrax.thermodynamics`)

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| Thermochemical data | NASA-7 polynomials, GRI-Mech 3.0 | - | `backend/amcrax/data/nasa7.json`, `thermodynamics/nasa7.py` | Cantera GRI-Mech 3.0 (cited `smith_grimech30`/`goodwin2018cantera` in pfr.py); cross-checked with NIST-JANAF tables parsed into `thermodynamics/reference/janaf.json` | Standard-state offset vs Aspen PURE41 data of -10.3 to +11.6 J/mol in Delta G (`docs/validation/discrepancy_analysis.md` section 2); explains the ideal-gas deviation completely |
| Reaction basis | per mol NH3, standard state 1 bar | - | `thermodynamics/equilibrium.py` docstring | engineering basis | - |
| Phase | gas phase only; valid T >= 250 degC, P <= 100 bar | - | `thermodynamics/equilibrium.py` docstring | NH3 supercritical region, Tc = 405.6 K | Not valid for condensation |
| Default EOS | `ideal` (also `pr`) | - | `solve_equilibrium(..., eos="ideal")`; `/api/thermo/equilibrium?eos=` | design choice; `pr` available | Ideal vs PR differ most at low T / high P (see discrepancy analysis section 3) |
| Peng-Robinson binary interaction | k_ij = 0 for all pairs | - | `thermodynamics/peng_robinson.py:10` | ASSUMPTION: "no sourced values collected" | Aspen (PENG-ROB with retrieved kij) vs Python PR differ by up to 0.185 pp conversion at 250 degC / 40 bar (discrepancy_analysis.md) |
| Critical properties | Tc, Pc, omega from CoolProp reference EOS | K, bar, - | `backend/amcrax/data/critical_properties.json` (provenance block) | CoolProp 8.0.0 (Bell et al. 2014) | - |
| Ammonia liquid / vaporisation properties (process model) | CoolProp reference EOS, anchored to the NASA scale at 298.15 K, 1 Pa | - | `process_model/properties.py` docstring | Gao et al. 2020 (CoolProp key `Gao-JPCRD-2020`) | Explains the vaporiser duty deviation from Aspen PENG-ROB (`results/validation/aspen_vs_python_flowsheet.csv`, item `FS-baseline` in `validation_matrix.json`) |
| Feed water | ideal-gas / ideal-solution component; liquid h from pure-water CoolProp at 298.15 K | - | `process_model/properties.py` docstring; `heat_integration/streams.py:33` (ASSUMPTIONS) | documented simplification (0.2 mol%) | Latent heat of the water neglected in the heat-integration curve ("<0.4 % of feed duty" per streams.py) |

## 3. Python process model and heat integration

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| FEHE specification | cold outlet T = hot inlet T - approach; counter-current profile checked on 41 points for a temperature cross | - | `process_model/flowsheet.py` docstring | design | Infeasible approach raises `FlowsheetSpecError` |
| COOLER condensation | Raoult dew-point check flags, does not model, condensation | - | `process_model/flowsheet.py` docstring | simplification | Not valid if condensation occurs |
| Python vs Aspen agreement | tolerance 2 % on key KPIs in the validation matrix | - | `amcrax.validation.checks` (items `FS-*`) | acceptance tolerance set by the validation module | Items `FS-baseline` and `FS-baseline_no_hi` do not pass at this tolerance (see [known_limitations.md](known_limitations.md)) |
| Minimum approach for pinch analysis | dT_min = 20 (default, user-adjustable in the dashboard) | K | `heat_integration/analysis.py:124` (`analyse(..., dT_min_K=20.0)`); `scripts/run_heat_integration.py --dtmin` | engineering assumption (default) | Moves the pinch targets (`results/simulations/heat_integration_*.json`) |
| Overall heat-transfer coefficient (FEHE area only) | 50 (range 10-100) | W/(m2 K) | `heat_integration/analysis.py:21-23` | ASSUMPTION: "overall U for a gas-gas exchanger ... order-of-magnitude area only - no specific textbook" | Affects the reported FEHE area only, not duties |
| Stream pressures in H-T curves | each stream at its inlet pressure; exchanger pressure drops neglected for enthalpy | - | `heat_integration/streams.py:37` | ASSUMPTION | Small |
| Isothermal duties | represented as 0.01 K wide segments | K | `heat_integration/streams.py:36` | numerical device | None on duty |
| Flue-gas heat | tail-gas combustion heat considered as a separate "process + flue gas" target | - | `heat_integration/analysis.py:141` | design | Flue heat below T_reactor + dT_min cannot supply reaction heat (warning in analysis.py) |

## 4. Kinetics and reactor (`amcrax.kinetics`, `amcrax.reactor`)

All kinetic constants live in `backend/amcrax/data/kinetics.yaml` (paths are `catalysts.<id>.parameters.<name>`), each with citekey, page and
locator. Values are not repeated here; this table records the assumptions *around* them.

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| Ni/MgO and Ru/MgO microkinetic constants | Table 1 of `takahashi2016kinetic` (p. 4) | - | kinetics.yaml: `catalysts.ni_takahashi_microkinetic`, `ru_takahashi_microkinetic` | literature | Fit 350-450 degC (Ni), 300-400 degC (Ru), X < 20 %, **1 atm** |
| Ru/Al2O3 Temkin-Pyzhev constants | k0 55245.9, Ea 114224 J/mol, beta 0.27 | mixed | kinetics.yaml: `catalysts.ru_kum_temkin_pyzhev` | `kum2026heatintegrated` Table 1 (p. 5) | Fit to 36 points of `dicarlo2014ammonia`, 623-723 K, 1-10 bar |
| Pressure extrapolation | rates used at 20 bar although fitted at 1 atm (Takahashi) or <= 10 bar (Kum) | - | kinetics.yaml `validity` blocks; `reactor/pfr.py` docstring | assumption (unvalidated extrapolation, labelled `python_model`) | Largest kinetic uncertainty; items `KIN-NI-PRED`, `KIN-RU-PRED` fail the 0.05 tolerance |
| Equilibrium approach factor | r = r_published (1 - Q/Kp) | - | kinetics.yaml: `equilibrium_approach_factor` | assumption (AmCraX extension): published model omits reverse steps; "forces r -> 0 at equilibrium; switchable" | Prevents conversion above equilibrium at 20 bar |
| Temkin-Pyzhev Keq basis | dGr read as J per 2 mol NH3; Keq^2 = exp(-dGr/RT) | - | kinetics.yaml: `catalysts.ru_kum_temkin_pyzhev.equilibrium_constant` | assumption, "verified against Cantera gri30 to < 0.5 kJ" | Option `keq_basis='amcrax_thermo'` (API default) uses Kp from the thermodynamics module |
| H2 seed for Temkin-Pyzhev | small H2 seed at the inlet | - | `reactor/pfr.py` docstring; kinetics.yaml limitations | numerical assumption (rate singular at p_H2 = 0) | Negligible if seed is small |
| Reactor model | 1-D pseudo-homogeneous PFR; effectiveness factor 1; no film transfer, radial gradients, dispersion, deactivation; Ergun pressure drop | - | `reactor/pfr.py` docstring | engineering simplification | Over-predicts conversion per kg catalyst relative to real pellets |
| Bed properties (Kum) | eps_b 0.36, rho_cat 980 kg/m3, dp 0.0006 m, tube D 0.126 m | - | kinetics.yaml: `catalysts.ru_kum_temkin_pyzhev.bed_properties` | `kum2026heatintegrated` Table 1 | Affects pressure drop and catalyst mass only |
| Gas constant | 8.314 | J/(mol K) | kinetics.yaml: `unit_conversions` | as used by the sources | - |
| Normal conditions for space velocity | 0 degC, 1 atm (22.414 L/mol) | - | kinetics.yaml: `validation.dicarlo_ru_al2o3_500C` | assumption ("'N' = 273.15 K, 101325 Pa") | Check only |

## 5. Separation (`amcrax.separation`, parameters in `separation.yaml`)

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| PSA recovery / purity operating points | 0.756 / 0.9911 (Cho), 0.80 (Kum), 0.71 / 0.99 (Cha via Hansen), 0.79 (Lee via Hansen) | - | separation.yaml: `psa.operating_points` | `cho2026nickel` p. 6 Table 3; `kum2026heatintegrated` p. 3; `hansen2024hysys` p. 2 | Literature points, never interpolated (psa.py docstring) |
| AmCraX baseline recovery | 0.85 | - | separation.yaml: `psa.amcrax_baseline` | assumption (see section 1) | Above all quoted literature values |
| PSA feed pressure requirement | 7.0 (alternatives 15.0, 2.5) | bar | separation.yaml: `psa.feed_pressure_requirement_bar` | `cho2026nickel` p. 6 Table 3 | Triggers a cracked-gas compressor if S7 pressure is below it (`evaluate.py`) |
| Product purity spec | 0.99 | mole fraction | separation.yaml: `psa.product_purity_spec` | `chopra2026decentralized` p. 4 | Optimisation constraint |
| Impurity split | NH3 and H2O retained by the adsorbent (go to tail gas); product impurity is N2 | - | separation.yaml: `psa.impurity_split_assumption` | assumption: "N2 is the least-adsorbed impurity" | Residual NH3 in H2 is handled separately (ammonia_slip) |
| Compression | isentropic efficiency 0.75 (range 0.70-0.85), max ratio 3.5 per stage, ideal intercooling, no cooler pressure drop | - | separation.yaml: `compression` | `cho2026nickel` p. 5 Table 2 (efficiency adopted as an AmCraX assumption) | Compression power enters LCOH and CI only through `optimisation/evaluate.py` |
| Membrane flux law | Sieverts, n = 0.5; permeability set `richard_ref53` (Pe0 4.57e-8, Ea 9.23 kJ/mol, 5.2 um) | mixed | separation.yaml: `membrane` | `richard2024technoeconomic` pp. 6-7 Eqs. 1-2, Table 2 (set [52] excluded: misprinted pre-exponential) | Reduced-order, no module design |
| Membrane operating point | 400 degC (window 350-500), permeate 1 bar | - | separation.yaml: `membrane.default_temperature_C` (assumption), `default_permeate_pressure_bar` | assumption inside the Pd window / `richard2024technoeconomic` Table 1 | - |
| Concentration polarisation | not applied by default (multiplier 1.0) | - | separation.yaml: `membrane.concentration_polarisation_factor` | source ambiguous (0.15 or 1 - 0.15) | Explicit `flux_multiplier` input for sensitivity |
| Membrane selectivity | infinite (pure-H2 permeate) | - | separation.yaml: `membrane.selectivity` | model assumption of the source | Optimistic purity |
| NH3 polishing | none modelled; fuel-cell limit 0.1 ppm NH3 (ISO 14687:2019 as quoted) | ppm | separation.yaml: `ammonia_slip` | `cechetto2023membrane` p. 5 | Product NH3 content not demonstrated (see known limitations) |

## 6. Economics (`amcrax.economics`, parameters in `economics.yaml`)

Every default carries a citekey/page/locator or `source: assumption` in the file. Key entries (YAML path `economics.yaml: defaults.<name>`):

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| Ammonia feed basis | the feed is priced on its contained NH3 (`feed NH3 kmol/h x molar mass`); the feed water (0.2 mol% by default) is not priced | kg NH3/h | `amcrax.economics.lcoh.compute_lcoh` | definition; same basis as the environmental module and the stoichiometric floor | An earlier version priced the whole feed stream as ammonia. Every LCOH result carries a note that states the basis |
| Cost basis | nominal USD, mixed source cost years 2024-2025 or not stated; no CEPCI escalation | - | economics.yaml: `cost_basis` and header | conflicting 2024 CEPCI values in the library (720.2 vs 800.3) | LCOH labelled "mixed 2024-2025 USD" |
| NH3 price | 450 (alternatives 300-1000) | USD/t | `defaults.nh3_price_USD_per_t` | `cho2026nickel` p. 7 Table 4 | Dominant LCOH term; swept in `results/sensitivity/lcoh_vs_ammonia_price_*.csv` |
| Electricity price | 0.084 | USD/kWh | `defaults.electricity_price_USD_per_kWh` | `cho2026nickel` p. 7 Table 4 | Small |
| Heat import mode | extra NH3 burnt (`ammonia_fuel`), efficiency 1.0 on LHV | - | `defaults.heat_import_mode`, `ammonia_fuel_heat_efficiency` | assumption (lower bound on fuel NH3: "optimistic") | Understates fuel cost if furnace efficiency < 1 |
| Surplus heat credit | not credited | - | `defaults.credit_heat_surplus` | assumption | - |
| Catalyst | Ni 33.4 USD/kg, Ru 542 USD/kg; life 2 yr; space velocity 9000 mL NH3/(g h) | - | `defaults.catalyst_price_USD_per_kg`, `catalyst_lifetime_yr`, `catalyst_space_velocity_mL_NH3_per_gcat_h` | `cho2026nickel` Tables 3-4 (catalyst choice Ni is an assumption) | Catalyst inventory is sized from the Cho space velocity because the AmCraX cracker has no catalyst mass |
| CAPEX method | plant-level correlation CAPEX_MUSD = 18.171 S^0.7451 (S in t H2/h; fit range 0.007-200, R2 0.9158) | MUSD | `defaults.capex_method`, `capex_references.ahmad2025_correlation` | `ahmad2025gtcc` p. 7 Fig. 6; chosen because it is the only plant-level fit covering 0.25 t/h (assumption) | Order-of-magnitude (class 4-5) estimate; two point estimates are reported beside it |
| Operating factors | maintenance 3 %, insurance 1.5 % of CAPEX/yr; labour 109,756 USD/yr (India basis, 2025); overhead 25 % of labour+maintenance; G&A 6 % of fixed OPEX | - | `defaults.maintenance_frac_capex_per_yr` ... `g_and_a_frac_fixed_opex` | `chopra2026decentralized` Table 2; `cho2026nickel` Table 4 | Small-plant labour basis |
| Financial | discount rate 10 %, plant life 25 yr, 8000 h/yr | - | `defaults.discount_rate`, `plant_life_yr`, `operating_hours_h_per_yr` | `kum2026heatintegrated` Table 5; `cho2026nickel` Table 4 | Annuity factor |
| Compression power | 0 kW unless supplied | kW | `defaults.compression_power_kW` | assumption: no cracked-gas compressor in the flowsheet | LCOH understated when PSA pressure < requirement (handled in `optimisation/evaluate.py`) |
| Normal molar volume | 22.414 | L/mol | `defaults.normal_molar_volume_L_per_mol` | assumption (source reference state not stated) | Catalyst inventory only |

## 7. Environmental (`amcrax.environmental`, parameters in `environmental.yaml`) - simplified accounting, not an LCA

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| Upstream NH3 | grey 2.60; blue 1.16 (capture version 2 0.77); green 0.0 | kg CO2e/kg NH3 | `environmental.yaml: upstream_ammonia.*` | `lee2022ammonia` p. 13 Fig. 8 (well-to-plant-gate) | "Green = 0" only because equipment manufacture is excluded by the source (file note) |
| Sea transport | 0.011 kg CO2e/(t km) x 5000 km | - | `transport.ship_ef` (literature, GLEC v3 via secondary listing), `transport.distance_km` (**assumption**, user-adjustable) | `glec2023v3` (primary PDF not opened) | Boil-off and port handling not counted |
| Grid factor | Singapore 2024: 0.402; EU 0.207; nuclear 0.0072 | kg CO2/kWh | `electricity.*` | `ema2025ses` (value from a search extract, page script-rendered), `kum2026heatintegrated`, `lee2022ammonia` (converted) | Flagged in the dashboard as "to be verified against primary source" |
| Natural-gas heating | 56,100 kg CO2/TJ (LHV), combustion only; upstream methane leakage excluded | - | `heating.natural_gas_combustion` | `ipcc2006v2ch2` Table 2.2 | Lower bound |
| Furnace / electric heater efficiency | 1.0 / 1.0 | - | `heating.fired_heater_efficiency_lhv`, `electric_heater_efficiency` | assumption | Lower bound on fuel / electricity demand |
| NOx, N2O from NH3 / tail-gas combustion | not counted | - | `heating.ammonia_self_firing` note | outside model boundary | Understates GHG of NH3 firing |
| Reference lines | EU RFNBO threshold from 94 g/MJ comparator and 70 % saving; IEA low-emission 4 kg CO2e/kg H2 | - | `reference_lines.*` | `eu2023_1185` (values via secondary extracts), `kum2026heatintegrated` p. 17 | Indicative only: EU boundary is well-to-wheel |

## 8. Optimisation (`amcrax.optimisation`; engine = Python model)

| Assumption | Value | Unit | Where | Source / rationale | Expected impact |
|---|---|---|---|---|---|
| Decision variables and bounds | T 400-800 degC; P 5-40 bar; PSA recovery 0.70-0.95; FEHE approach 20-150 K | - | `optimisation/problems.py:30-38` (`VARIABLES`) | bounds = Aspen-simulated ranges (sweep CSVs named in the file) | Optimum cannot lie outside the verified range |
| Constraints | NH3 conversion >= 0.95 (design assumption), H2 purity >= 0.99, FEHE feasibility; optional thermal self-sufficiency | - | `optimisation/problems.py:55-75` (`DEFAULT_CONSTRAINTS`, `CONSTRAINT_DOCS`) | purity: `chopra2026decentralized` p. 4; conversion 0.95: design assumption (literature crackers 99.42 %, 99.6 %, `hansen2024hysys`) | Drives the optimum toward high T |
| Solver | scipy differential evolution (seed 12345) + SLSQP polish | - | `optimisation/problems.py:160-193`; `scripts/run_optimisation.py` (`SEED`) | deterministic | Reproducible; global optimality not proven |
| Metric evaluation | LCOH and CI evaluated by the same functions for Aspen and Python results; default route `grey/self_firing`; compression added when S7 pressure < 7 bar | - | `optimisation/evaluate.py` docstring | consistency with the economics default heat mode | - |
| Verification | optimum must be re-solved in Aspen before being presented as a result | - | `aspen/automation/verify_candidates.py` | design rule | `results/optimisation/aspen_verification.json` holds the candidates re-solved in Aspen with their deviations and pass/fail flags; the checks `OPT-ASPEN` and `OPT-FEAS` in the validation matrix report the outcome |
