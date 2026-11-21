<!-- cites: cho2026nickel, mehr2026highcapacity, richard2024technoeconomic, hansen2024hysys, farokhi2025costoptimization, cechetto2023membrane, iso2019hydrogen -->

# 5 Process design and process flow diagram

## 5.1 Design basis

The baseline converts refrigerated liquid ammonia into compressed hydrogen in a single train without material recycle. Every value in Table 5.1 is a field of the case object `CaseInputs` or of `config/flowsheet.json`, so the same basis drives the Aspen Plus V15 model and the independent Python model.

Table: **Table 5.1.** Baseline design basis and the origin of each choice. *Source: results/simulations/baseline.json (inputs, streams), aspen/models/baseline.inp; literature as cited.*

| Item | Baseline value | Origin |
|---|---|---|
| Feed state | Saturated liquid at 1.013 bar (Aspen bubble point -32.96 degC) | Engineering assumption: refrigerated atmospheric storage; Mehr et al. (2026) use the same boundary (liquid NH~3~ at -33 degC, 1 bar) |
| Feed composition | 99.8 mol% NH~3~, 0.2 mol% H~2~O | Engineering assumption (water as the representative impurity) |
| Capacity basis | 100 kmol/h = 1703.25 kg/h (40.88 t/d, of which 40.79 t/d NH~3~) | Engineering assumption (round modelling basis) |
| Reactor | Equilibrium (RGibbs), isothermal, 600 degC, 20 bar | Engineering assumption informed by literature: 20-30 bar cases in Cho et al. (2026), 17.5-21 bar in Mehr et al. (2026), 20 bar in Richard et al. (2024) |
| Vaporiser outlet | Dew point + 10 K | Engineering assumption |
| Feed/effluent exchanger | Cold outlet = reactor temperature - 50 K | Engineering assumption (hot-end approach) |
| PSA feed temperature | 40 degC | Engineering assumption |
| PSA H~2~ recovery | 0.85 | **Engineering assumption above the published 0.71-0.81** (Section 4.3); reduced-order splitter (Section 11) |
| PSA N~2~ slip | 0.001 of the N~2~ fed | Engineering assumption |
| Burner | Adiabatic, complete combustion, 15 % excess air | Engineering assumption |
| Stack temperature | 150 degC | Engineering assumption |
| Property method | PENG-ROB | Literature-informed (Section 8) |

<!-- data: results/simulations/baseline.json inputs; streams.FEED (temperature_C -32.9617, mass_flow_kg_h 1703.25294, component_mole_flow NH3 99.8); t/d = kg/h x 24 / 1000; NH3 99.8 x 17.0305 = 1699.64 kg/h; research/notes/mehr2026highcapacity.md (p. 3; Table 6 21 bar; text 17.5 bar), cho2026nickel.md, richard2024technoeconomic.md (Table 6, 20 bar) -->

## 5.2 Process flow diagram

Figure 5.1 shows the flowsheet as built and solved in Aspen Plus V15, and Figure 5.2 the same topology as drawn by the AmCraX dashboard from `config/flowsheet.json`, with the solved block duties. The block and stream names are used throughout the report.

![**Figure 5.1.** AmCraX baseline flowsheet in the Aspen Plus V15 main flowsheet window: PUMP, VAPORIZR, feed/effluent exchanger FEHE, trim HEATER, RGibbs CRACKER, COOLER, PSA splitter, tail-gas BURNER and flue-gas cooler FLUEHX, with streams FEED, S1-S7, H2PROD, TAILGAS, AIR, FLUE and STACK. The loop FEHE-HEATER-CRACKER-FEHE is the heat-integration path that makes Aspen tear stream S4 (Section 6.5). *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/01_flowsheet.png){width=95%}

![**Figure 5.2.** Process flow diagram of the same baseline in the AmCraX dashboard, coloured by dominant component, with the Aspen block duties (kW) and the convergence and balance-closure status of the case. The dashboard reads the topology from the same configuration file as the Aspen input generator, so the two diagrams cannot drift apart (Section 22). *Source: AmCraX dashboard screenshot; values from Aspen Plus V15 simulation.*](../../docs/screenshots/dashboard_pfd.png){width=95%}

## 5.3 Block-by-block description

**Feed conditioning.** PUMP raises the liquid from 1.013 to 21.0 bar with an assumed efficiency of 0.75. Raising the pressure of the liquid needs only 1.85 kW of shaft power; raising it after evaporation would need a gas compressor. VAPORIZR evaporates the feed at 20.8 bar and superheats it 10 K above its dew point, to 75.90 degC, so that the exchanger downstream sees only vapour; it absorbs 739.46 kW. With 0.2 mol% water the dew point is set by the NH~3~-H~2~O vapour-liquid equilibrium model, so this outlet temperature and duty depend on the property method (Section 8.3).

**Preheat and cracking.** FEHE heats the vapour to 550.0 degC against the reactor effluent and recovers 612.21 kW that would otherwise be rejected to cooling water. HEATER closes the last 50 K to 600 degC with 73.66 kW. CRACKER minimises the Gibbs energy over NH~3~, H~2~, N~2~ and H~2~O at 600 degC and 20 bar, reaching an NH~3~ conversion of 0.9808 and absorbing 1480.00 kW. It is the largest heat demand of the plant (Section 9).

**Cooling and purification.** The cracked gas (S5, 197.88 kmol/h) leaves FEHE at 228.38 degC and COOLER brings it to the PSA feed temperature of 40 degC, rejecting 304.95 kW. PSA sends 85 % of the H~2~ and 0.1 % of the N~2~ to H2PROD at 19.0 bar; all NH~3~ and H~2~O and the rest of the gas go to TAILGAS at 1.3 bar. The product purity of 99.961 mol% H~2~ follows from these assumed split fractions; it is not a prediction (Section 11).

**Tail-gas combustion.** BURNER burns the H~2~ and NH~3~ of the tail gas completely with air; the calculator AIRCALC sets the air flow to 68.17 kmol/h for 15 % excess air (Section 6.4). The adiabatic flame temperature is 1368.90 degC. This is the complete-combustion value; an equilibrium calculation with dissociation gives about 2.3 K less (Section 15), and NO~x~ formation is not modelled (Section 21). FLUEHX cools the flue gas to the 150 degC stack temperature and releases 1520.25 kW, the heat available from the tail gas. In Aspen this heat is not returned to the process; it is credited against the heat demand in the KPIs and the pinch analysis (Sections 5.6 and 18).
<!-- data: results/simulations/baseline.json blocks.*.duty_kW, blocks.PUMP.power_kW 1.84528517, streams.S2/S3/S5/S6/H2PROD/AIR/FLUE temperature_C and flows, kpis.nh3_conversion, kpis.h2_purity_mole_frac; results/validation/independent_physics_checks.csv baseline dT_equilibrium_minus_complete_K -2.2515 -->

## 5.4 Pressure profile

The process train and the combustion side each have one pressure level (Table 5.2). The pressure drops are fixed block specifications (engineering assumptions), not hydraulic calculations. Because the cracker runs at the pumped pressure, the product leaves at 19.0 bar without gas compression.

Table: **Table 5.2.** Pressure profile of the baseline. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json; pressure drops are engineering assumptions in aspen/models/baseline.inp.*

| Location | Stream | Pressure (bar) |
|---|---|---|
| Storage / pump suction | FEED | 1.013 |
| Pump discharge | S1 | 21.0 |
| Vaporiser outlet | S2 | 20.8 |
| FEHE cold outlet | S3 | 20.5 |
| Reactor inlet | S4 | 20.2 |
| Reactor outlet | S5 | 20.0 |
| FEHE hot outlet | S6 | 19.7 |
| PSA feed | S7 | 19.5 |
| H~2~ product | H2PROD | 19.0 |
| Tail gas / combustion air | TAILGAS, AIR | 1.3 |
| Flue gas | FLUE | 1.2 |
| Stack | STACK | 1.1 |

<!-- data: results/simulations/baseline.json streams.*.pressure_bar -->

## 5.5 Key streams

Table 5.3 lists the streams that define the process; the full stream table and the mass, element and energy balance closures are in Section 15.

Table: **Table 5.3.** Key streams of the baseline (600 degC, 20 bar). *Source: Aspen Plus V15 simulation, results/simulations/baseline.json.*

| Stream | T (degC) | P (bar) | Flow (kmol/h) | Composition (mol%) |
|---|---|---|---|---|
| FEED | -32.96 | 1.013 | 100.00 | NH~3~ 99.8, H~2~O 0.2 |
| S4 (reactor feed) | 600.0 | 20.2 | 100.00 | NH~3~ 99.8, H~2~O 0.2 |
| S5 (cracked gas) | 600.0 | 20.0 | 197.88 | H~2~ 74.20, N~2~ 24.73, NH~3~ 0.97, H~2~O 0.10 |
| H2PROD | 40.0 | 19.0 | 124.85 | H~2~ 99.961, N~2~ 0.039 |
| TAILGAS | 40.0 | 1.3 | 73.03 | N~2~ 66.95, H~2~ 30.16, NH~3~ 2.62, H~2~O 0.27 |
| FLUE | 1368.90 | 1.2 | 130.67 | N~2~ 79.36, H~2~O 19.21, O~2~ 1.43 |

<!-- data: results/simulations/baseline.json streams.{FEED,S4,S5,H2PROD,TAILGAS,FLUE} temperature_C, pressure_bar, mole_flow_kmol_h, mole_frac -->

## 5.6 Headline KPIs

Table 5.4 defines the KPIs (`backend/amcrax/kpis.py`) and gives their baseline values, with and without the feed/effluent exchanger.

Table: **Table 5.4.** Headline KPIs of the baseline and their definitions. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json and baseline_no_hi.json (kpis).*

| KPI | Definition | Baseline | Without FEHE |
|---|---|---|---|
| NH~3~ conversion | 1 - n~NH3~(S5) / n~NH3~(S4) | 0.9808 | 0.9808 |
| H~2~ product (kg/h) | n~H2~(H2PROD) M~H2~ | 251.59 | 251.59 |
| H~2~ purity (mol fraction) | y~H2~(H2PROD), set by the assumed PSA split | 0.99961 | 0.99961 |
| Overall H~2~ yield | n~H2~(H2PROD) / (1.5 n~NH3~(FEED)) | 0.8337 | 0.8337 |
| Total external heating (kW) | Q~VAPORIZR~ + Q~HEATER~ + Q~CRACKER~ | 2293.12 | 2905.33 |
| Heat recovered in FEHE (kW) | Q~FEHE~ | 612.21 | 0 |
| Tail-gas combustion heat (kW) | -Q~FLUEHX~ | 1520.25 | 1520.25 |
| Net fuel heat deficit (kW) | External heating - tail-gas combustion heat | 772.87 | 1385.08 |
| Specific heat demand (kWh/kg H~2~) | External heating / H~2~ product | 9.11 | 11.55 |
| LHV efficiency | LHV(H2PROD) / (LHV(FEED) + max(deficit, 0) + pump power) | 0.877 | 0.824 |

<!-- data: results/simulations/baseline.json kpis; results/simulations/baseline_no_hi.json kpis -->

The exchanger lowers the external heating by 612.21 kW and raises the LHV efficiency from 0.824 to 0.877; conversion and product are unchanged because the reactor state is the same. The tail gas covers about two-thirds of the external heat demand (1520.25 of 2293.12 kW). The net fuel heat deficit and the LHV efficiency are first-law, upper-bound metrics: external heat is counted one-to-one against fuel LHV, as if delivered by a 100 %-efficient fired heater, and flue-gas heat below the reactor temperature is credited although it cannot drive the reaction. With temperature levels respected, the pinch analysis gives a baseline heat import of 752.6 kW against the KPI deficit of 772.9 kW (Section 18).
<!-- data: results/simulations/baseline.json kpis (tailgas_combustion_heat_kW 1520.24946, total_external_heating_kW 2293.1167774, net_fuel_heat_deficit_kW 772.8673174); results/simulations/heat_integration_baseline.json configurations[2] (c) external_heating_kW 752.628 -->

## 5.7 Design simplifications

* No gas compression: the product leaves at 19.0 bar; lower-pressure designs would need recompression (Cho et al., 2026).
* No NH~3~ polishing: the residual 1.92 kmol/h NH~3~ in S7 goes to the tail gas by specification; a real plant needs a polishing step to meet 0.1 ppm (ISO, 2019, as cited in Cechetto et al., 2023, p. 10779).
* The PSA is a component splitter without isotherms, cycle or pressure-swing energy (Section 11).
* The cracker is an equilibrium reactor with no catalyst volume or pressure drop from geometry (Sections 9 and 14).
* The burner heat is not physically connected to the cracker or vaporiser in Aspen; the coupling is a first-law credit in the KPIs and a temperature-resolved target in the pinch analysis.

As in other Gibbs-reactor flowsheets (Hansen et al., 2024; Farokhi et al., 2025), these simplifications make the baseline an upper reference for yield and efficiency rather than a plant design.
<!-- data: results/simulations/baseline.json streams.S7.component_mole_flow_kmol_h.NH3 = 1.91512572 -->
