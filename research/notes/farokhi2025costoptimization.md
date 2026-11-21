# farokhi2025costoptimization

## Bibliographic data
- **Authors:** Vahid Farokhi, Lars Erik Øi, Per Morten Hansen (University of South-Eastern Norway).
- **Title:** Simulation and Cost optimization of Ammonia Cracker Process.
- **Journal:** IFAC-PapersOnLine 59(29) (2025), pp. 48-53. Open access, CC BY-NC-ND (p. 1).
- **DOI:** 10.1016/j.ifacol.2025.12.180. Verified through the doi.org handle API (responseCode 1).
- **APA 7 reference:** Farokhi, V., Øi, L. E., & Hansen, P. M. (2025). Simulation and cost optimization of ammonia cracker process. *IFAC-PapersOnLine, 59*(29), 48-53. https://doi.org/10.1016/j.ifacol.2025.12.180
- **Page numbering:** "p. N" means page N of the PDF. Journal page = 47 + N.
- **Basis:** the paper builds on the Farokhi (2024) MSc thesis at USN and on Hansen et al. 2024 (citekey hansen2024hysys).

## Scope
The paper re-uses the Hansen et al. 2024 HYSYS V12 flowsheet. It adds cases with progressively more heat recovery and computes an LCOH for each case. The aim is to find the cost optimum between NH3 fuel saved and heat-exchanger cost.

## Simulator set-up (p. 2)
- Aspen HYSYS V12 with the Peng-Robinson property package.
- The cracker is a Gibbs reactor. The furnace is also a Gibbs reactor.
- The adsorber and the PSA are modelled as ideal component splitters.
- The stream specifications in Table 1 (p. 2) are identical to Hansen et al. 2024 Table 2:
  - NH3: -27.6 °C, 1.3 bar, 592.33 kmol/h
  - H2: 25.5 °C, 30 bar, 698.07 kmol/h
  - Air: 608.13 kmol/h
  - Flue gas: 139 °C, 999.28 kmol/h
- **Final case heat recovery (p. 4):**
  - Cracker product heats the cracker feed.
  - It then heats the NH3 fuel.
  - Coolers on the H2 and N2 streams supply heat to a feed heater.

## Cost method (p. 3)
- **Purchased equipment cost:** Aspen In-Plant Cost Estimator V12.
- **Heat-exchanger areas:**
  - U = "50 kW/m2*°C" for all heat exchangers. **AMBIGUOUS:** a value of 50 kW/m2K is not physical for gas service. The value is almost certainly 50 W/m2K.
  - Minimum approach temperature: 20 K.
- **TCI** = 5.93 × PEC (p. 3; Table 5 p. 5). The percentage shares are taken from Devkota et al. 2023/2024.
- **Eq. 1, capital recovery factor:** CRF = i(1+i)^n / ((1+i)^n - 1). Source: Byun et al. 2020.
- **Eq. 2:** yearly CAPEX = CRF × TCI.
- **Eq. 3:** OPEX = C_RM + 2.3125 C_L + C_U + 0.137 FCI + 0.1 TCI.
  - The text extraction garbles the symbols (doubled glyphs). This is a reconstruction. The last term is read as TCI.
- **Eq. 4:** LCOH = (CRF × TCI + OPEX) / annual production capacity. Source: Makhloufi & Kezibri 2021.

### Table 4 (p. 5): assumptions, as stated, from Devkota et al. (2023)
- NH3: 0.52 USD/kg
- Cooling water: 0.051 USD/m3
- Water: 1.5 USD/m3
- Discount rate: 10 %
- **Plant uptime: 4000 h/yr**
- Plant life: 25 yr
- Adsorbent: 3.41 USD/kg
- Labour: 15 persons at "34.167" USD/person-yr. This is presumably 34,167 USD.
- H2 price: 9.06 USD/kg

### Table 5 (p. 5): base-case CAPEX
The "Cost, USD" column is consistent with **kUSD** (thousand USD). The check: 0.1102 × 10,096 kUSD = 1.112 MUSD, which matches the stated yearly CAPEX.

| Item | % of PEC | Cost |
|---|---|---|
| Purchased equipment cost (PEC) | 100 | 1702 |
| Direct costs | 360 | 6129 |
| Indirect costs | 144 | 2451 |
| Working capital | 89 | 1515 |
| FCI | 504 | 8581 |
| TCI | 593 | 10096 |

## Results
| Case | NH3 to cracker (kmol/h) | NH3 burned (kmol/h) | Cracker conversion (%) | H2 (kmol/h) | kg H2/kg NH3 | LCOH (USD/kg) |
|---|---|---|---|---|---|---|
| Base (no heat recovery below the 139 °C flue gas) | 455 | 45 | 98.15 | 535 | 0.128 | 5.5 |
| Final | not stated | not stated | not stated | 586 | 0.140 | 5.1 |

- The base-case row comes from Table 3 (p. 4), which is mislabelled "improved case". The abstract (p. 1) confirms that 0.128 is the base case.
- Table 2 (p. 3) repeats the older Hansen base case: 556.1 kmol/h and 0.1316 kg/kg.
- **Base case costs (p. 5):** yearly CAPEX 1.112 MUSD, OPEX 22.961 MUSD.
- **Final case costs (p. 5):**
  - The text gives "CAPEX 23.151 mill. USD and yearly OPEX 1.208 mill. USD". These labels are swapped.
  - From Table 6, CRF × TCI = 0.1102 × 10,970 kUSD = 1.209 MUSD. So the yearly CAPEX is 1.208 MUSD and the OPEX is 23.151 MUSD.
  - Table 6: PEC 1850, FCI 9324, TCI 10970 (kUSD).
- **Reconstruction check (my own arithmetic):**
  - Final case: 24.359 MUSD / (586 kmol/h × 2.016 kg/kmol × 4000 h) = 5.16 USD/kg. The paper prints 5.1.
  - Base case: (1.112 + 22.961) / (535 × 2.016 × 4000) = 5.58 USD/kg. The paper prints 5.5.
- **Literature comparison (p. 5):** Devkota et al. 2024 report an LCOH of 6.05 USD/kg. Restelli report 5.6-6.3 EUR/kg.

## Limitations
- The cracker is a Gibbs equilibrium reactor, and the PSA is an ideal splitter. The authors themselves say the LCOH is probably underestimated.
- The U value has an ambiguous unit.
- There are internal labelling errors: the Table 3 title, and the swapped CAPEX/OPEX in Sec. 5.3.
- The 4000 h/yr uptime is low compared with other TEAs (7000-8000 h). It is quoted as Devkota's assumption.
- There is no uncertainty analysis.
- The details of the final-case flowsheet are only in the MSc thesis.

## Relevance to AmCraX
- It provides a simple TEA recipe: a Lang-type factor of 5.93 × PEC, the OPEX formula (Eq. 3), and CRF at 10 % over 25 years.
- It gives an LCOH benchmark of 5.1-5.5 USD/kg for an equilibrium-cracker flowsheet with 500 kmol/h NH3 feed.
- It shows the heat-recovery trade-off. The extra heat exchangers increase PEC by only 1702 -> 1850 kUSD, while the NH3 fuel saving dominates the result.
