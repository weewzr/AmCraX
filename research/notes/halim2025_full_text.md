# Halim, Zain and Khoo (2025): full-text reading

Source: Halim, I., Zain, N. S., & Khoo, H. H. (2025). Assessing the feasibility of ammonia utilization for power generation: A techno-economic-environmental study. *Applied Energy*, 386, 125581. https://doi.org/10.1016/j.apenergy.2025.125581 (citekey `halim2025ammonia`).

Read on 24 November 2026: all 15 pages, with every page that holds a table, flowsheet or chart checked on the page image (pp. 1, 3-13). The supplementary material (Tables A1 and A2) was not available. Data with page references and status: `research/data/halim2025_extract.json`. Status words: *verbatim* (printed, checked on the image), *figure reading*, *derived* (arithmetic by this reader from printed numbers, not a number of the paper), *absent* (searched for and not found).

This note compares AmCraX with published literature. It is not a validation of AmCraX, and it changes no analysis, rule or verdict.

## 1. What the paper models

- **Pathways (p. 9, Fig. 5, Table 5).** There are four scenarios. Green or blue NH3 is cracked to H2 (purified by PSA), or green or blue NH3 is used directly as fuel. There is no fuel cell, no exhaust-heated cracker, and no unpurified H2/N2 cracked gas sent to a turbine.
- **Power plant (p. 3).** A Mitsubishi H-25 that the vendor page (ref. [32]) says generates "up to 60.1 MW" with a combined-cycle efficiency of 54 %. The paper does not say whether the 54 % is on LHV or HHV, or for which fuel. The turbine is **not modelled**: no inlet conditions, pressure ratio or firing temperature are given.
- **Fuel to the turbine (p. 3).** 60 % NH3 and 40 % H2 by energy, i.e. 12,815.5 kg/h NH3 + 1,339.8 kg/h H2, or 53 % NH3 and 47 % H2 by volume. The H-25 is said to run on 30 to 60 vol% H2, citing a trade-press article (ref. [31], POWER magazine).
- **Cracker (pp. 3-7).** Aspen Plus v14 with PC-SAFT and NRTL, Ru-K/CaO kinetics fitted to Sayas et al. The furnace is **fired with 18 % of its own outlet gas** (NH3 + H2), at excess air 3.09 and flame temperature 1,359 °C. Feed enters at 200 °C and 5.6 bar; the tube outlet is 489 °C. Single-pass conversion is 80 %. Unconverted NH3 is absorbed in water and recycled. TSA + PSA (zeolite 4A) give 98 mol% H2 at 90 % recovery; this recovery is a literature value from ref. [40], not computed. A steam Rankine loop on the furnace outlet gives 284 kW (−284 kW in Table 2). Electricity use falls from 2.48 to 2.28 kWh/kg H2, mostly the adsorber compressor at 3,262 kW. Capacity is 32 t H2/day.
- **Economics (pp. 7-9, Tables 3-4).** 10 %, 30 years, capacity factor 0.9 (all from Makhloufi and Kezibri 2021), CEPCI 800. PEIC is 71.6 M USD, of which about half is the 25,000 t refrigerated storage tank (35.6 M USD) and about 40 % the furnace (28.3 M USD). TCI is 282.5 M USD. Fixed O&M is 25.3 M USD/yr, 10 % of FCI. Prices (Platts, July 2024, Middle East) are green NH3 944.20 USD/t FOB (986.20 delivered less 42 transport) and blue 397.96 USD/t FOB. Grid electricity is 0.16 USD/kWh. **No turbine or power-plant capital or O&M is included in any pathway, and no LCOE is computed.**

## 2. Efficiencies: what is assumed and what is computed

The paper computes the cracker. It does **not** compute any turbine efficiency. One number, 54 %, is applied to every fuel:

- 60.1 MW / (12,815.5 × 18.6 + 1,339.8 × 120.0 MJ/h ÷ 3600) = 60.1 / 110.87 MW = **54.2 %** on fuel LHV (53.9 % at an NH3 LHV of 18.8). This is the vendor figure applied to the NH3/H2 mix (derived).
- The direct case replaces the cracked H2 with NH3 "to provide the same energy output": 8,579.9 kg/h (p. 9). Then 1,339.8 × 119.99 / 8,579.9 = 18.74 MJ/kg, which is the NH3 LHV. Equal fuel energy for equal output means the **same turbine efficiency on NH3 and on H2**.

**Turbine efficiency on fuel fed (AmCraX basis 2):** H2-rich fuel minus direct NH3 = **0 pp**. This is an assumption of the paper, not a result.

**Electricity per NH3 LHV fed (AmCraX basis 1, NH3 LHV 18.60 MJ/kg; derived):**
- The cracker's NH3 feed is not printed. Dividing the Table 4 feedstock cost by its price gives 102,126,100 / 944.20 = 108,162 t/yr. The blue-NH3 and transport lines give the same tonnage. That is 12,347 kg/h at 8,760 h, or 9.22 kg NH3 per kg H2. Check: 12,347 × 0.9442 / 1,339.8 = 8.70 USD/kg H2, the feed cost printed in Fig. 5.
- NH3 LHV to H2 LHV through cracker + PSA: 8,579.9 / 12,347 = **69.5 %**. AmCraX's stored Aspen value is 87.7 %. The difference comes from burning 18 % of the product gas for heat and from the 90 % PSA recovery.
- Whole 60.1 MW plant: with cracking, 60.1 / ((12,815.5 + 12,347) × 18.6 / 3600) = **46.2 %**. Direct: 60.1 / ((12,815.5 + 8,579.9) × 18.6 / 3600) = **54.4 %**. Difference **−8.1 pp**.
- H2 share alone: 0.5397 × 1,339.8 × 119.99 / 3600 = 24.10 MW. That is 1.95 kWh/kg NH3 by cracking against 2.81 kWh/kg NH3 direct (37.8 % against 54.4 %), a difference of −16.6 pp. With this cracker, the H2 turbine would need to be 1/0.695 = 1.44 times as efficient as the NH3 turbine to break even on energy.

## 3. Costs and the numbers the essay attributes to the paper

| Scenario | USD/kg H2 | Largest items (Fig. 5) |
|---|---|---|
| Green NH3 cracking (LCOH) | 15.1 | NH3 8.70 (57.5 %), fixed O&M 2.39 (15.8 %) |
| Blue NH3 cracking (LCOH) | 10.1 | NH3 3.67 (36.3 %), fixed O&M 2.39 (23.7 %) |
| Green NH3 direct (LCOA) | 9.2 | NH3 6.05 (65.5 %), fixed O&M 1.21 (13.1 %) |
| Blue NH3 direct (LCOA) | 5.7 | NH3 2.55 (44.5 %), fixed O&M 1.21 (21.1 %) |

Reproduced from Tables 3-4 with eq. (6) (derived): CCF 0.10608 and annual H2 1,339.8 × 8,760 × 0.9 kg give 15.147 and 10.113 USD/kg. LCOA is expressed per kg H2 of equivalent fuel energy.

| Essay attribution | Fate | Where | What it is |
|---|---|---|---|
| 60.1 MW | **Located** | p. 3, p. 11 | Vendor rating of the H-25 (ref. [32]), used as the target output |
| LCOH 15.1 and 10.1 USD/kg | **Located** | p. 1 Highlights, p. 9, Fig. 5, Table 5 | Cracked-H2 cost from green and blue NH3 |
| "about 40 % cheaper" | **Located, different quantity** | p. 1 Highlights; p. 9 gives 39 % (green) and 44 % (blue) | 1 − LCOA/LCOH: cost of fuel delivered to the turbine, per kg H2 of energy, for the 40 % H2 share only. Equal turbine efficiency; power plant excluded. **Not a cost of electricity.** |
| 30 to 60 vol% H2, H-25 | **Located** | p. 3 | Relayed from trade press (ref. [31]), vendor-claim grade |

## 4. Environment and policy

- Supply-chain GHG (p. 10, Fig. 6): green 0.779 and blue 5.21 kg CO2e/kg H2. The cracking-plant labels are 0.23 (green) and 1.54 (blue).
- Power plant (Fig. 7): green 0.006 to 0.043 and blue 0.187 to 0.461 kg CO2e/kWh, against Singapore's 2022 grid factor of 0.417. Coal-gasification blue NH3 exceeds the grid factor at 73 % H2 or more. Derived: the per-kWh values use about 18.0 kWh of electricity per kg H2 (33.33 × about 0.54).
- NCAC (Table 5): 0.67 to 0.71 USD/kg CO2e for green direct, 1.11 to 1.21 for green cracking, 0.74 and 2.37 for blue SMR (direct, cracking), 1.44 and −6.83 for blue coal. Basis observation (derived): eq. (8) puts the cost on a fuel kWh (33.33 kWh/kg H2) but divides by an abatement per kWh of electricity. On a consistent electricity basis every NCAC would be about 1.85 times larger; the ranking is unchanged.
- NOx is computed only in the **cracker furnace flue gas**, by a Gibbs (equilibrium) reactor. Treatment is 4 USD/kg and 466,000 USD/yr, which implies about 116,500 kg/yr (derived). The paper has no turbine NOx, **no N2O**, and **no carbon price or Singapore carbon tax**.

## 5. Sensitivity and stated limitations

- **Sensitivities:** excess air (Fig. 3); GHG across supply routes and H2 fraction (Fig. 7, Table 5); green against blue price. No economic sensitivity is reported on CAPEX, discount rate, capacity factor, scale or turbine efficiency, although Section 3's title names one.
- **Limitations stated by the authors (p. 11):** no dynamics or supply-chain uncertainty, and no optimisation of the cracker.

## 6. Assessment

**(a) Fired-cracker turbine efficiency for H1-a: not provided.**
- The paper's cracker is fired, by its own product gas. Its turbine burns NH3 with PSA-purified H2, not H2/N2 cracked gas, and the efficiency is a single vendor headline (54 %, basis and fuel not stated) applied to every fuel. The implied difference is 0 pp.
- 0 pp lies **below** every AmCraX fired threshold: +5.16 reference, 3.29 to 8.79 over 11 bases, +5.82 at a cracker fuel efficiency of 0.9225 and +6.54 at 0.85. It also lies below the cracking + PSA thresholds (+12.55; 9.68 to 18.10), the 40 % purified blend (+4.66; 3.47 to 6.96) and the 20 % fired blend (+1.17; 0.70 to 2.07).
- But it is **the same equal-efficiency assumption AmCraX already makes** (eta_gt_gas = direct value). It is not a simulation, vendor or measured value for H2-rich fuel. Methodology v2 requires evidence independent of the assumption, so it cannot test H1-a.
- It is not like-for-like either: H-25 class (about 40 to 60 MW) against the AmCraX turbine calibrated on Ahmad; the efficiency basis is not stated; the fuel is NH3/H2 rather than H2/N2. The paper confirms the gap rather than closing it.

**(b) H1-a under the coded rule as written.**
- `v2_h1a` reads the fired-half sourced value from `results/research/enduse/turbine_threshold.json`, key `sourced_values/fired_H2N2_fuel_delta_pp/sourced`. This is a single number, compared as `side(thresholds over the 11 bases of thresholds/full_fired/bases, src, src)`.
- That key is **hard-coded `None`** in `scripts/research/enduse_threshold.py` (the `fired_H2N2_fuel_delta_pp` block, about line 208). An entry added to `research/data/turbine_efficiency_literature.json` (for example under `key_deliverable_efficiency_difference/not_like_for_like_values`, with `id`, `delta_pp`, `type`, `detail`, `grade`) would **not reach the rule**. The generating script would also have to read it, which is a code change, not a data change.
- If `sourced` were set to 0.0, the fired half would be `below`. Together with the purified half `below` (NETL 6.08 to 7.3 against 9.68 to 18.10), `v2_h1a` would return **SUPPORTED**. That result would be circular, because it would feed the model's own assumption back as evidence. Recommendation: **do not add it**. H1-a stays INCONCLUSIVE on the evidence.

**(c) H1-b, H1-c, H1-d.**
- **H1-b.** The 40 % is **located, but it is a different quantity**: fuel cost at the turbine inlet per kg H2 of energy (39 % green, 44 % blue), with the power plant excluded and equal turbine efficiency.
  - AmCraX compares LCOE, where turbine capital and O&M dilute any fuel-cost gap. The computed maximum is 16.6 %. The essay's "power ~40 % cheaper" is therefore a mis-description of the paper's quantity; the paper itself is not contradicted.
  - Orientation only (derived here; not computed in the repository): the comparable AmCraX quantity is 1 − (NH3 price × 119.96/18.6) / LCOH. That is 1 − 2.90/4.015 = 27.7 % for grey at 450 USD/t, 22.7 % at 709 USD/t and 20.0 % at 1000 USD/t. Same direction, smaller gap. The paper's cracker loses more energy (69.5 % against 87.7 %), carries a 35.6 M USD storage tank, and is small (32 t/d).
  - The rule reads `row_evidence/H1-b/numbers/claim_pct` (40) and `forty_percent_figure/*` (LCOE gaps), so it still returns **CONTRADICTED** (16.6 < 20). To read the paper's quantity like for like, both of the following would be needed (neither done):
    - a new computed key, for example `forty_percent_figure/fuel_cost_gap_pct_at_turbine_inlet`, in `enduse_threshold.py`;
    - a rule change.
  - The hard-coded conclusion "Halim et al. full text was not accessible" (`build_evidence_matrix.py`, `v2_h1b`) and `forty_percent_figure/halim_status` are now out of date (text edits in code; not done).
- **H1-c.** No exhaust-heated cracker and no unpurified partial cracking are in the paper. The rule reads `sourced_values/exhaust_heated_system_delta_pp/supported_range` (Ahmad, Karpilov), and the paper adds nothing there. The rule returns **INCONCLUSIVE**, unchanged. The 30 to 60 vol% statement is a vendor-grade operability claim, not an efficiency.
- **H1-d.** The rule compares direct kWh/kg NH3 with cracking + PSA at **sourced** turbine gains (`row_evidence/H1-d/numbers/kWh_per_kg_NH3/*NETL*`) and deliberately excludes the equal-efficiency copy. The paper's implied 1.95 against 2.81 kWh/kg NH3 rests on that same equal-efficiency assumption, so it is not admissible. The rule returns **INCONCLUSIVE**, unchanged.
  - The paper's LCOH (15.1 and 10.1 USD/kg, green and blue NH3 at July 2024 prices) could be listed as published model outputs beside the benchmarks in `row_evidence/H1-d/numbers/benchmarks`. However, `v2_h1d` reads only `ne_asia_smr_production_cost` and `blue_delivered_east_asia`, and its verdict depends only on the energy side, so nothing would change.
  - Comparison with published literature: the paper's NH3-to-H2 retention of 69.5 % is far below AmCraX's 87.7 %. On that design, the energy half of H1-d ("larger loss when H2 is an intermediate fuel") would need an H2 turbine about 1.44 times as efficient to break even. This is informative, but it comes from a different flowsheet.

**(d) Points against current project statements.**
1. `enduse_turbine_literature.md` §3 and `enduse_cost_literature.json` (`halim_numbers` `see_also`) call the 30 to 60 vol% H-25 figure a likely mis-attribution from NETL/Baker Hughes. **It is in the paper (p. 3)**, relayed from POWER magazine (ref. [31]).
2. "Not in the abstract and could not be located" (`enduse_turbine_literature.md` §7, `turbine_efficiency_literature.json` `halim2025_status`, `turbine_threshold.json` `halim_status`, `references.json` verification) is now superseded: all four numbers are located.
3. `carrier_cost_literature.md` (d) says the quoted 40 % "is power generation cost (Halim et al.)". **It is not.** It is a fuel cost per kg H2 equivalent (LCOA against LCOH).
4. The evidence matrix `published_figures_checked` entry ("power about 40 % cheaper ... not reproduced") describes the essay's wording. Against the paper's own quantity the direction is reproduced and the size is smaller (orientation 20 to 28 %, derived).
5. Nothing in the paper conflicts with AmCraX numbers on a like-for-like basis. Its 54 % efficiency (vendor) is higher than the AmCraX direct-NH3 49.64 % (Ahmad simulation), but neither is measured on ammonia.

**(e) Boundary differences that limit every comparison.**
- **Scope:** the paper covers the cracker, NH3 storage and supply only. AmCraX covers the whole power plant (LCOE).
- **Fuel compared:** only the 40 % H2 energy share is cracked, not full cracking.
- **Turbine:** equal efficiency by construction, 54 % vendor value, basis not stated.
- **Purification and heating:** purified H2 (PSA 90 % recovery, assumed). The cracker is fired by its own product gas, with no supplementary NH3 and no exhaust heat.
- **Finance:** capacity factor 0.9 (7,884 h) against AmCraX 8,000 h; life 30 against 25 years; 10 % discount rate in both.
- **Prices:** green 944 and blue 398 USD/t (Middle East, July 2024) against AmCraX grey 450 USD/t. Grid electricity is bought at 0.16 USD/kWh.
- **Capital:** a 25,000 t storage tank is charged to the cracker (about half of PEIC); the price year is not stated.
- **Emissions:** GHG uses supply-chain factors from an unavailable supplement; NOx comes from a furnace equilibrium model; N2O and the carbon tax are absent.

## 7. What could not be determined from the paper

- Turbine inlet conditions, and the efficiency basis and fuel of the 54 %.
- A separate efficiency for NH3, H2 or cracked gas.
- The H2 delivery pressure to the turbine.
- The cracker's NH3 feed flow (only derivable from costs) and its heat duty in MW.
- Power-plant cost and LCOE.
- Turbine NOx and N2O.
- The price year.
- The stream table (Table A1) and emission factors (Table A2).
- Any economic sensitivity.
