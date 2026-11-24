<!-- cites: cho2026nickel, usgs_mcs2026_pgm, jm_base_price_wso_2026, takahashi2016kinetic, kum2026heatintegrated, dicarlo2014ammonia, lucentini2021nirukinetic, sayas2020rukcao, mehr2026highcapacity, purcel2024stability, turton2018analysis, vdi2010heatatlas, towler2013chemical -->

# 35 Catalysts (H3): prices, economics, kinetic validity and exchanger sizing

Hypothesis H3 states that low-temperature catalysts combined with heat integration reduce energy use and can outweigh their higher cost. Section 26 tested it on the Phase 1 basis with the published TEA catalyst prices. Phase 2 replaced those prices, re-ran the comparison at equal conversion, classified the validity of every rate law at the 20 bar operating pressure, and sized and costed the feed/effluent heat exchanger (FEHE). The results move against the essay on cost and confirm the heat-integration saving after the exchanger cost.

## 35.1 Catalyst prices

No supplier quotation (grade A) or published commercial price (grade B) exists for any ammonia-cracking catalyst; the product pages of the large vendors give no prices. Every ruthenium catalyst price in the TEA literature lies below the value of the ruthenium it contains. For example, Cho et al. (2026) use 542 USD/kg for Ru-K/CaO with 3 wt% Ru, while the metal content alone is worth 666 USD/kg at the USGS 2025 average ruthenium price (U.S. Geological Survey, 2026) and 1,784 USD/kg at the Johnson Matthey base price of 20 November 2026 (1,850 USD/oz, read from a secondary display; wallstreet-online.de, 2026). Phase 2 therefore derives prices from metal content plus a non-metal part: price = (w~Ni~/100) P~Ni~ + (w~Ru~/100) P~Ru~ + N, with N = 32.2 USD/kg (Cho's calculated 33.4 USD/kg for 8 wt% Ni/Al~2~O~3~ less its nickel). These are derived values (metal part grade E, non-metal part grade C), not quotations. The published TEA prices are kept only as a labelled historical case.

Table: **Table 35.1.** Derived catalyst prices, USD/kg of finished catalyst (SGD at 1.288444 SGD/USD). Low uses the USGS 2025 Ru average and N = 0 (a metal floor, not a market price); central and high use the Johnson Matthey Ru price; high equals central for Ru because no higher sourced Ru price exists. *Source: research/data/catalyst_prices.json; results/research/catalyst_economics/catalyst_prices_sgd.json.*

| Catalyst | Low | Central | High | Central (SGD/kg) |
|---|---|---|---|---|
| Ni/MgO (30 wt% Ni) | 4.50 | 36.79 | 39.94 | 47.4 |
| Ru/MgO (5 wt% Ru) | 1,109 | 3,006 | 3,006 | 3,873 |
| Ru/Al~2~O~3~ (8 wt% Ru) | 1,775 | 4,791 | 4,791 | 6,172 |
| 5Ni1Ru/CeO~2~ | 222.6 | 627.8 | 628.3 | 809 |
| 2.5Ni0.5Ru/CeO~2~ | 111.3 | 330.0 | 330.2 | 425 |
| Ru-K/CaO (3 wt% Ru), price only | 665.5 | 1,816.6 | 1,816.6 | - |

<!-- data: research/data/catalyst_prices.json scenarios; results/research/catalyst_economics/catalyst_prices_sgd.json; catalyst_cost_table.csv (SGD/kg central 6172, 3873, 809, 425, 47.4) -->

Catalyst lifetimes of 1, 2, 4 and 5 years come from TEA assumptions (Cho et al., 2026; a steam-reforming changeout analogue), not measurement. The only measured stability datum in the library is a 13.5 % loss of maximum conversion over 800 h at 534 °C for a Ni/Al~2~O~3~ catalyst (Purcel et al., 2025), a laboratory result, not an industrial lifetime.

## 35.2 Kinetic validity classes

Each rate law was classified by the range in which it was fitted and checked.

Table: **Table 35.2.** Validity class of each catalyst rate law at the 20 bar operating pressure. *Source: results/research/kinetics/validity_classification.json.*

| Catalyst | Rate law | Fitted range (°C / bar) | Class at 20 bar |
|---|---|---|---|
| Ni/MgO | microkinetic (Takahashi & Fujitani, 2016) | 350-650 / 1.013 | extrapolated; prediction check KIN-NI-PRED fails |
| Ru/MgO | microkinetic (Takahashi & Fujitani, 2016) | 300-550 / 1.013 | extrapolated; prediction check KIN-RU-PRED fails |
| Ru/Al~2~O~3~ | Temkin-Pyzhev (Kum et al., 2026, on the data of Di Carlo et al., 2014) | 350-450 / 1-10 | validated against literature (its own fitting data) |
| 5Ni1Ru/CeO~2~ | LHHW (Lucentini et al., 2021) | 350-600 / 1.013 | validated against literature (its own fitting data) |
| 2.5Ni0.5Ru/CeO~2~ | LHHW (Lucentini et al., 2021) | 350-600 / 1.013 | validated against literature (its own fitting data) |
| Ni/CeO~2~, Ru/CeO~2~ | none published | - | unmodelled |
| Ru-K/CaO | full text not obtainable (Sayas et al., 2020) | - | unmodelled |

No rate law is validated at 20 bar: 3 laws are validated against literature (against their own fitting data), 2 are extrapolated, and 3 catalysts are unmodelled because no rate law was found, and none was invented. Every kinetic result at 20 bar in this report is therefore an extrapolation in pressure. Section 38 gives the quantified causes of the kinetic validation failures.

## 35.3 Energy at equal conversion (H3-a)

The Phase 1 Aspen comparison (Section 26) found a 17 % lower fired duty for Ru/Al~2~O~3~ at 499 °C than for Ni/MgO at 594 °C, with 100 kg of catalyst each. Those runs reach unequal conversion (Ni 0.9589, Ru 0.9496), so less unconverted NH~3~ reaches the tail gas with Ni and Ni needs more fired heat. At equal conversion of 0.95 and 20 bar (independent Python calculation, cross-checked against Aspen Plus V15 at the same temperature and conversion), the fired duty is 485.1 kW for Ru/Al~2~O~3~ against 510.3 kW for Ni/MgO with heat integration, a saving of 25 kW or about 5 %, and 163 kW without heat integration. The saving is larger than the 15 kW Python-Aspen offset only for temperature differences of about 60 K or more (Ru/Al~2~O~3~ and Ru/MgO); for the NiRu catalysts it is 4 to 5 kW and not resolved. The Phase 1 figure of 17 % is withdrawn. Heat integration also saves less at low temperature: the net heat-integration saving is 0.099 USD/kg for Ru/Al~2~O~3~ at 499 °C against 0.132 USD/kg for Ni at 594 °C.
<!-- data: results/research/catalyst_economics/catalyst_economics.json findings (python_Top_X095_*: 485.1 / 510.3 kW; 163 kW without HI; resolution); row_evidence.H3-a -->

## 35.4 Catalyst economics (H3-c)

**Against the essay.** At the derived prices every low-temperature catalyst is dearer than Ni/MgO at equal conversion of 0.95, with the same kinetic operating temperature and the FEHE costed: Ru/Al~2~O~3~ +0.081, Ru/MgO +0.043, 5Ni1Ru +0.011 and 2.5Ni0.5Ru +0.005 USD/kg H~2~ (+0.105, +0.056, +0.015, +0.006 SGD/kg). The break-even catalyst prices, 1506, 1297, 177 and 151 USD/kg, lie well below the derived central prices (4791, 3006, 628, 330); against the metal floors (1775, 1109, 223, 111) they are lower for Ru/Al~2~O~3~ and 5Ni1Ru and higher for Ru/MgO and 2.5Ni0.5Ru. Against the re-optimised Ni design the break-even prices fall to 630, 313, 92 and 98 USD/kg, all below the metal floors. When temperature and catalyst mass are re-optimised for cost, the optimum for an expensive catalyst is a small charge at high temperature: Ru/Al~2~O~3~ 614 °C with 7.5 kg, Ru/MgO 622 °C with 14.3 kg, against Ni/MgO at 537 °C with 539 kg. The low-temperature operation the hypothesis needs is then not chosen, and no low-temperature catalyst is cheaper by more than the resolution of 0.0060 USD/kg. In the sensitivity set a resolved low-temperature win occurs in 1 of 100 rows (2.5Ni0.5Ru with the Ni rate divided by 5). The NPV of choosing the low-temperature catalyst is -1.78, -0.99, -0.25 and -0.10 MUSD, with no payback.
<!-- data: results/research/catalyst_economics/catalyst_economics.json comparisons, breakeven, crossover, sensitivity; catalyst_breakeven.csv; resolution CE-RESOLUTION (-0.0054 to -0.0060 USD/kg) -->

The verdict is nevertheless INCONCLUSIVE, not CONTRADICTED, because the outcome depends on the nickel reference temperature. Against Ni at the sourced design temperatures of 735.52 °C (Cho et al., 2026) and 760 °C (Mehr et al., 2026), the low-temperature designs win; the Ni temperatures at which each catalyst breaks even, which do not need a Ni rate law, are 670 °C (Ru/Al~2~O~3~), 676 °C (Ru/MgO), 640 °C (5Ni1Ru) and 540 °C (2.5Ni0.5Ru). The AmCraX Ni/MgO law, which is in class "extrapolated", puts the Ni optimum at 537 to 549 °C. The sourced values and the model straddle the thresholds. With rate laws validated against literature only, the kinetics-independent energy result, the price and break-even arithmetic and these Ni threshold temperatures survive; every ranking against Ni/MgO does not.

![**Figure 35.1.** LCOH difference of each low-temperature catalyst against Ni/MgO at the derived price cases. *Source: independent Python calculation, results/figures/research/catalyst_econ_cost_per_kg.png.*](../../results/figures/research/catalyst_econ_cost_per_kg.png){width=85%}

![**Figure 35.2.** Break-even catalyst price against the derived price range and the metal floor. *Source: independent Python calculation, results/figures/research/catalyst_econ_breakeven.png.*](../../results/figures/research/catalyst_econ_breakeven.png){width=85%}

## 35.5 Heat-exchanger sizing and the net value of heat integration (H3-d)

The baseline FEHE transfers 612.2 kW, from a hot side cooling from 600 to 228.4 °C to a cold side heating from 75.9 to 550 °C. The temperatures cross, so one 1-2 shell is infeasible; the design is five 1-2 shells in series with F = 0.84, an LMTD of 91.9 K and a segmented UA of 7.32 kW/K. No overall heat-transfer coefficient U at 20 bar was found in the literature. The VDI Heat Atlas (VDI, 2010; read from a search excerpt) gives 5 to 35 W/(m^2^ K) for gas on both sides at about 1 bar and 150 to 500 at 200 to 300 bar. The cases are therefore 35 (low), 150 (high) and their geometric mean of 72.5 W/(m^2^ K), a derived number, giving areas of 249, 120 and 58 m^2^. With the Turton et al. (2018) fixed-tube-sheet correlation (stainless steel, 19.5 barg, CEPCI 797.9) and the reference indirect factor of 1.4336, the total-capital equivalent is 1.784, 1.542 and 1.437 MUSD (2.298, 1.987 and 1.852 MSGD); the Towler and Sinnott (2013) U-tube correlation gives 1.18 to 1.38 MUSD.

Heat integration saves 0.2138 USD/kg H~2~ (4.2292 against 4.0155), almost all supplementary NH~3~ fuel. After the annualised exchanger cost the net benefit is +0.067, +0.087 and +0.095 USD/kg at the low, central and high U, and +0.071 to +0.137 USD/kg in all ten catalyst cases. It turns negative only for U below about 12 W/(m^2^ K) (break-even 11.3 with Turton, 7.8 with Towler), NH~3~ below about 310 USD/t, a capital recovery factor above about 0.15, or a 20 K approach at U = 35. The energy result is an Aspen Plus V15 result: the first-law heat deficit falls from 1385.1 to 772.9 kW (-44 %) and the total external heating from 2905.3 to 2293.1 kW (-21 %). Row H3-d is SUPPORTED for energy. The cost side depends on the unsourced U and is stated in the row envelope; it does not vote. The exchanger cost is added on top of the reference CAPEX item, which may count part of it twice; this makes the net benefit conservative.
<!-- data: results/research/heat_exchanger/heat_exchanger_study.json baseline (Q 612.2 kW, 5 shells, F 0.84, LMTD 91.9 K, UA 7.32 kW/K, areas 249/120/58, TCI 1.784/1.542/1.437 MUSD, saving 0.2138, net 0.067/0.087/0.095, break-even U 11.3 / 7.8), catalyst_cases, sensitivity, row_evidence.H3-d -->

![**Figure 35.3.** Net benefit of heat integration after the annualised FEHE cost against the overall heat-transfer coefficient. *Source: independent Python calculation, results/figures/research/heat_exchanger_net_benefit.png.*](../../results/figures/research/heat_exchanger_net_benefit.png){width=85%}

## 35.6 Rows H3-b, H3-e and H3-f

Row H3-b (the temperature ordering of the catalysts) is INCONCLUSIVE because it rests on rate laws extrapolated to 20 bar. Row H3-e tests the statement of Cho et al. (2026) that a Ru cracker needs no supplementary fuel while a Ni cracker does: that pattern exists only for PSA recoveries between 0.7564 and 0.7813, and Cho's own 0.756 lies 0.0004 below the Ni edge; it is INCONCLUSIVE. Row H3-f tests Cho's 7.0 % lower reconversion cost for Ru: AmCraX gives -4.5 to +1.6 % at Cho's prices and -16.2 to +1.0 % at the derived Ru-K/CaO price, depending on the inventory basis and PSA recovery; it is INCONCLUSIVE.
