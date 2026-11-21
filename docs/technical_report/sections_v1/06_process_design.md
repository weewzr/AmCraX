<!-- cites: cho2026nickel, hansen2024hysys, farokhi2025costoptimization, mehr2026highcapacity, kum2026heatintegrated, cechetto2023membrane, richard2024technoeconomic, iso2019hydrogen -->

# 6 Overall process design

## 6.1 Design basis

The baseline converts refrigerated liquid ammonia into hydrogen in a single-train flowsheet without material recycle; the feed/effluent exchanger and the calculator TLINK nevertheless make Aspen tear stream S4 (Section 7.2). Every value in Table 6.1 is an input of the case object `CaseInputs`, so the same basis drives the Aspen Plus V15 model and the independent Python model.

Table: **Table 6.1.** Baseline design basis and the origin of each choice. *Source: results/simulations/baseline.json (inputs, streams), aspen/models/baseline.inp; literature as cited.*

| Item | Baseline value | Origin |
|---|---|---|
| Feed state | Saturated liquid (vapour fraction 0) at 1.013 bar; Aspen bubble point -32.96 degC | Engineering assumption: atmospheric refrigerated storage; a liquid NH~3~ inlet near -33 degC and 1 bar is also the boundary used by Mehr et al. (2026) |
| Feed composition | 99.8 mol% NH~3~, 0.2 mol% H~2~O | Engineering assumption (water as the representative impurity of commercial ammonia) |
| Capacity basis | 100 kmol/h feed = 1703.25 kg/h = 40.88 t/d (40.79 t/d NH~3~) | Engineering assumption (round modelling basis); conversions from the Aspen FEED stream |
| H~2~ product (result) | 124.80 kmol/h H~2~ = 251.59 kg/h = 6.04 t/d at 99.961 mol% H~2~ (392 ppm N~2~) | Aspen Plus V15 simulation. **Not fuel-cell grade**: above the 300 ppm N~2~ vehicle limit of ISO 14687 (Section 6.4); NH~3~ polishing to 0.1 ppm required but not modelled |
| Reactor | RGibbs, isothermal 600 degC, 20 bar | Engineering assumption informed by literature: 20-30 bar cracker cases in Cho et al. (2026); 17.5-21 bar in Mehr et al. (2026); 20 bar in Richard et al. (2024) |
| Feed/effluent exchanger | Cold outlet = reactor T - 50 K | Engineering assumption (hot-end approach) |
| PSA feed temperature | 40 degC | Engineering assumption |
| PSA H~2~ recovery | 0.85 | **Engineering assumption above the published range of 0.71-0.81** (0.756, Cho et al., 2026; about 0.81, Mehr et al., 2026; 0.80, Kum et al., 2026); the PSA is a reduced-order component splitter (Section 12) |
| PSA N~2~ slip | 0.001 of the N~2~ fed | Engineering assumption |
| Burner | Adiabatic, complete combustion, 15% excess air | Engineering assumption |
| Stack temperature | 150 degC | Engineering assumption |
| Property method | PENG-ROB (Section 9) | Literature-informed: Peng-Robinson is used by Cho et al. (2026), Hansen et al. (2024) and Farokhi et al. (2025) |

<!-- data: results/simulations/baseline.json streams.FEED (temperature_C, mass_flow_kg_h, mass_frac), kpis.h2_product_kmol_h, kpis.h2_product_kg_h; t/d = kg/h x 24 / 1000 -->
<!-- data: research/notes/cho2026nickel.md (20/30 bar, PSA 75.6 %), mehr2026highcapacity.md (17.5/21 bar, ~81 %), kum2026heatintegrated.md (80 %), richard2024technoeconomic.md (20 bar) -->

The effect of the assumed recovery is examined in Section 15.

## 6.2 Block flow description

Figure 6.1 shows the flowsheet as built in Aspen Plus V15. The block and stream identifiers are those of `config/flowsheet.json` and are used throughout the report.

![**Figure 6.1.** AmCraX baseline flowsheet in the Aspen Plus V15 main flowsheet window: feed pump, vaporiser, feed/effluent exchanger, trim heater, RGibbs cracker, cooler, PSA splitter, tail-gas burner and flue-gas cooler. The figure fixes the block and stream names used in all tables of this report. *Source: Aspen Plus V15 screenshot.*](../../aspen/screenshots/01_flowsheet.png){width=95%}

**Feed conditioning.** PUMP (Pump, efficiency 0.75) raises the liquid from 1.013 to 21.0 bar. Pumping the liquid is much cheaper than compressing the cracked gas; the brake power is 1.85 kW. VAPORIZR (Heater) evaporates the stream at 20.8 bar and superheats it 10 K above its dew point, to 75.90 degC, so that the exchanger downstream handles only vapour. The vaporiser duty is 739.46 kW.

**Preheat and cracking.** FEHE (HeatX, shortcut design mode) heats the vapour to 550.0 degC against the reactor effluent and recovers 612.21 kW. HEATER (Heater) trims the feed to 600 degC with 73.66 kW. CRACKER (RGibbs) minimises the Gibbs energy at 600 degC and 20 bar over NH~3~, H~2~, N~2~ and H~2~O. It reaches an NH~3~ conversion of 0.9808 and absorbs 1480.00 kW of reaction and sensible heat.

**Heat recovery and cooling.** The cracked gas (S5, 197.88 kmol/h) leaves FEHE at 228.38 degC. COOLER (Heater) brings it to 40 degC and rejects 304.95 kW.

**Purification.** PSA (Sep) sends 85% of the H~2~ and 0.1% of the N~2~ to H2PROD at 19.0 bar. All NH~3~ and H~2~O and the remaining gas go to TAILGAS at 1.3 bar. The product contains 0.99961 mol fraction H~2~.

**Tail-gas combustion.** BURNER (RStoic, duty 0) burns the residual H~2~ and NH~3~ completely with air. The calculator AIRCALC sets the air flow to 68.17 kmol/h (Section 7). The adiabatic flame temperature is 1368.90 degC. FLUEHX cools the flue gas to 150 degC and releases 1520.25 kW, which is the heat available from the tail gas.

<!-- data: results/simulations/baseline.json blocks.*.duty_kW, blocks.PUMP.power_kW, streams.S2/S3/S5/S6/H2PROD/AIR/FLUE temperature_C and flows, kpis.nh3_conversion, kpis.h2_purity_mole_frac -->

## 6.3 Pressure profile

The process train and the combustion side each have one pressure level; pressure drops are fixed block specifications (engineering assumptions), not hydraulic calculations.

Table: **Table 6.2.** Pressure profile of the baseline. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json; pressure drops are engineering assumptions in aspen/models/baseline.inp.*

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

## 6.4 Stream summary

Table: **Table 6.3.** Main stream results of the baseline (600 degC, 20 bar). *Source: Aspen Plus V15 simulation, results/simulations/baseline.json.*

| Stream | T (degC) | P (bar) | Vapour fraction | Flow (kmol/h) | Flow (kg/h) | y~NH3~ | y~H2~ | y~N2~ | y~H2O~ | y~O2~ |
|---|---|---|---|---|---|---|---|---|---|---|
| FEED | -32.96 | 1.013 | 0 | 100.00 | 1703.25 | 0.998 | 0 | 0 | 0.002 | 0 |
| S2 | 75.90 | 20.8 | 1 | 100.00 | 1703.25 | 0.998 | 0 | 0 | 0.002 | 0 |
| S4 | 600.0 | 20.2 | 1 | 100.00 | 1703.25 | 0.998 | 0 | 0 | 0.002 | 0 |
| S5 | 600.0 | 20.0 | 1 | 197.88 | 1703.25 | 0.00968 | 0.7420 | 0.2473 | 0.00101 | 0 |
| S6 | 228.38 | 19.7 | 1 | 197.88 | 1703.25 | 0.00968 | 0.7420 | 0.2473 | 0.00101 | 0 |
| S7 | 40.0 | 19.5 | 1 | 197.88 | 1703.25 | 0.00968 | 0.7420 | 0.2473 | 0.00101 | 0 |
| H2PROD | 40.0 | 19.0 | 1 | 124.85 | 252.96 | 0 | 0.99961 | 0.00039 | 0 | 0 |
| TAILGAS | 40.0 | 1.3 | 1 | 73.03 | 1450.29 | 0.0262 | 0.3016 | 0.6695 | 0.00274 | 0 |
| AIR | 25.0 | 1.3 | 1 | 68.17 | 1966.72 | 0 | 0 | 0.79 | 0 | 0.21 |
| FLUE | 1368.90 | 1.2 | 1 | 130.67 | 3417.02 | 0 | 0 | 0.7936 | 0.1921 | 0.0143 |
| STACK | 150.0 | 1.1 | 1 | 130.67 | 3417.02 | 0 | 0 | 0.7936 | 0.1921 | 0.0143 |

<!-- data: results/simulations/baseline.json streams.{FEED,S2,S4,S5,S6,S7,H2PROD,TAILGAS,AIR,FLUE,STACK} -->

The baseline product (99.961 mol% H~2~, 392 ppm N~2~ from the assumed 0.1 % slip) exceeds the 300 ppm N~2~ vehicle limit of ISO 14687:2019 (ISO, 2019, as cited in Cechetto et al., 2023) and is therefore **not fuel-cell grade**. The purity-driven case is the Aspen scenario `scn_fuel_cell_grade` (N~2~ slip 0.0005, recovery 0.80): 99.979 mol% H~2~ (208 ppm N~2~) and 236.79 kg/h H~2~. Its NH~3~ content is zero only because the splitter sends no NH~3~ to the product; a real plant needs NH~3~ polishing to 0.1 ppm, which is not modelled (Section 12).

<!-- data: results/simulations/baseline.json streams.H2PROD.mole_frac (H2 0.999607997, N2 0.000392003136); results/simulations/scn_fuel_cell_grade.json inputs.psa_n2_slip 0.0005, psa_h2_recovery 0.8, kpis.h2_purity_mole_frac 0.99979171, streams.H2PROD.mole_frac.N2 0.00020828994, kpis.h2_product_kg_h 236.789; research/notes/cechetto2023membrane.md item 1 -->

## 6.5 Balance closures

Balances are taken over {FEED, AIR} -> {H2PROD, STACK} (`amcrax.kpis.compute_balances`); the energy balance counts every block duty and pump power except the internal FEHE and is normalised by the sum of absolute external duties.

Table: **Table 6.4.** Overall balance closures. *Source: Aspen Plus V15 simulation, results/simulations/baseline.json balances.*

| Balance | In | Out | Relative closure |
|---|---|---|---|
| Mass (kg/h) | 3669.98 | 3669.98 | -5.4 x 10^-10^ |
| N atoms (kmol/h) | 207.508 | 207.508 | - |
| H atoms (kmol/h) | 299.800 | 299.800 | - |
| Energy (kW) | -1534.08 | -1534.08 | 3.2 x 10^-9^ |

<!-- data: results/simulations/baseline.json balances -->

All closures are at round-off level, so the extraction and KPI arithmetic lose no stream or duty.

## 6.6 Headline KPIs

Table: **Table 6.5.** Headline KPIs of the baseline and their definitions (`backend/amcrax/kpis.py`). *Source: Aspen Plus V15 simulation, results/simulations/baseline.json kpis; the no-heat-integration variant from results/simulations/baseline_no_hi.json.*

| KPI | Definition | Baseline | Without FEHE |
|---|---|---|---|
| NH~3~ conversion | 1 - n~NH3~(S5)/n~NH3~(S4) | 0.9808 | 0.9808 |
| H~2~ product (kg/h) | n~H2~(H2PROD) x M~H2~ | 251.59 | 251.59 |
| H~2~ purity (mol fraction) | y~H2~(H2PROD) | 0.99961 | 0.99961 |
| Overall H~2~ yield | n~H2~(H2PROD) / (1.5 n~NH3~(FEED)) | 0.8337 | 0.8337 |
| Total external heating (kW) | Q~VAPORIZR~ + Q~HEATER~ + Q~CRACKER~ | 2293.12 | 2905.33 |
| Recovered heat in FEHE (kW) | Q~FEHE~ | 612.21 | 0 |
| Tail-gas combustion heat (kW) | abs(Q~FLUEHX~) | 1520.25 | 1520.25 |
| Net fuel heat deficit (kW) | total external heating - tail-gas combustion heat | 772.87 | 1385.08 |
| Specific heat demand (kWh/kg H~2~) | total external heating / H~2~ product | 9.11 | 11.55 |
| LHV efficiency | LHV(H2PROD) / (LHV(FEED) + max(deficit, 0) + pump power) | 0.877 | 0.824 |

<!-- data: results/simulations/baseline.json kpis; results/simulations/baseline_no_hi.json kpis -->

The FEHE reduces external heating by 612.21 kW and raises the LHV efficiency from 0.824 to 0.877. The tail gas covers about two-thirds of the heat demand; the deficit is charged as extra fuel at its LHV. This is a first-law credit only; temperature feasibility is assessed by pinch analysis (Sections 11 and 16).

## 6.7 Design simplifications

* No cracked-gas compression: the cracker runs at the pumped pressure and the product leaves at 19.0 bar; lower-pressure designs need recompression (Cho et al., 2026).
* No NH~3~ polishing: residual NH~3~ (1.92 kmol/h in S7) goes to the tail gas by specification.
* The PSA is a reduced-order splitter without isotherms, cycle or pressure-swing energy (Section 12).
* The burner heat (FLUEHX duty) is not transferred to the reactor or vaporiser in Aspen; the coupling is a first-law comparison in the KPIs and the pinch analysis.
* The cracker is an equilibrium (RGibbs) reactor (Section 10); no pressure drop is calculated from geometry.

<!-- data: results/simulations/baseline.json streams.S7.component_mole_flow_kmol_h.NH3 = 1.91512572 -->
