<!-- cites: cho2026nickel, ahmad2025gtcc, chopra2026decentralized, farokhi2025costoptimization, kum2026heatintegrated, halim2025ammonia, nea_carbon_tax, spgroup_tariff_2026q4, ema_usep, adb_fx, mpa_ema_ammonia_2025, sp_blue_ammonia_2025, sp_singapore_h2_2025, argus_h2_markers, ace_h2_delivered, eu2018_2066_annex6, mti_hydrogen_strategy -->

# 27 Singapore techno-economic analysis

## 27.1 Scope and boundary

This section re-costs the baseline ammonia cracker (Aspen Plus V15 baseline, 600 °C, 20 bar; Sections 5 and 15) for a Singapore setting, with Jurong Island as a representative industrial site. No claim is made that such a facility exists or is planned. The activity data (feed, heat duty, product flow) are stored **Aspen Plus V15 simulation** results; every cost, price scenario and indicator below is an **independent Python calculation** (`amcrax.economics.singapore`) with inputs from `backend/amcrax/data/singapore.yaml`. Three cost metrics are kept apart throughout.

* **REC** (reconversion cost, USD/kg H~2~): LCOH minus the cost of the contained feed NH~3~. It includes supplementary NH~3~ burnt for heat, capital, fixed and variable operating cost, catalyst and carbon tax. It carries no feedstock price.
* **LCOH** (USD/kg H~2~): REC plus the feed NH~3~ cost, at the plant gate, before any onward transport or storage.
* **Landed cost**: LCOH plus transport and distribution. It is **not computed**, because no sourced transport cost was found; the module returns `None` unless a cost is supplied.

Ammonia prices are **scenarios** (grey, blue, three green cases), taken from the literature and S&P-type summaries; they are not Singapore transaction prices. The cost base is mixed 2024 to 2026 nominal USD with no escalation index, because the conflicting CEPCI values in the library do not allow a defensible index. The boundary excludes product compression and storage, NO~x~ treatment, product purification beyond the existing PSA block (Section 28), land, and the ammonia terminal.

## 27.2 Method

The LCOH follows Eq. (19.1) of Section 19, with the CAPEX built at equipment level instead of the single-correlation estimate of Section 19:

$$ \mathrm{LCOH} = \frac{\mathrm{CRF}\,C_\mathrm{cap} + C_\mathrm{fix} + C_\mathrm{var}}{\dot m_{\mathrm{H_2}}\,t_\mathrm{op}}, \qquad \mathrm{REC} = \mathrm{LCOH} - c_\mathrm{feed}, \qquad c_\mathrm{feed} = \frac{p_{\mathrm{NH_3}}\, y_\mathrm{feed}}{1000} \qquad (27.1) $$

where $p_{\mathrm{NH_3}}$ (USD/t) is the ammonia price, $y_\mathrm{feed}$ (kg NH~3~/kg H~2~) the contained feed per kg of product H~2~, and the remaining symbols are as in Eq. (19.1). Supplementary NH~3~ burnt for heat is priced at the same $p_{\mathrm{NH_3}}$ at 100 % of its lower heating value and sits in $C_\mathrm{var}$ (hence in REC). The total capital investment is the Farokhi et al. (2025) purchased-equipment cost at 500 kmol/h NH~3~ feed (1702 kUSD, Table 5), split by the Chopra et al. (2026) shares, scaled with feed to the power 0.8 (Chopra et al., 2026, Eq. 5) and multiplied by the ratio of total capital investment to purchased-equipment cost, 5.93 (10 096 kUSD over 1702 kUSD, Farokhi et al., 2025, Table 5). The unit of the Farokhi table (kUSD) is inferred, not stated.

Because LCOH is linear in $p_{\mathrm{NH_3}}$, the break-even ammonia price at which the plant meets a hydrogen benchmark price $p_{\mathrm{H_2}}^*$ is

$$ p_{\mathrm{NH_3}}^* = \frac{p_{\mathrm{H_2}}^* - a}{b}, \qquad \mathrm{LCOH} = a + b\,p_{\mathrm{NH_3}}, \quad b = \frac{y_\mathrm{feed} + y_\mathrm{fuel}}{1000} \qquad (27.2) $$

where $a$ (USD/kg H~2~) is the price-independent part of the cost and $y_\mathrm{fuel}$ (kg NH~3~/kg H~2~) the NH~3~ burnt for heat. Net present value, internal rate of return and payback are computed at a hydrogen selling price (the NE Asia SMR benchmark, Table 27.4), before tax and at constant prices.

The Singapore carbon tax is applied only to direct, in-scope emissions of a facility at or above the 25 000 t CO~2~e/yr threshold (National Environment Agency, n.d.):

$$ C_\mathrm{tax} = \begin{cases} \tau\, E_\mathrm{direct} & E_\mathrm{direct} \ge 25\,000 \\ 0 & \text{otherwise} \end{cases} \qquad (27.3) $$

where $\tau$ (SGD/t CO~2~e) is the rate (45 in 2026 and 2027) and $E_\mathrm{direct}$ (t CO~2~e/yr) the facility's direct emissions. Burning ammonia for heat emits no direct CO~2~, so $E_\mathrm{direct}$ is zero in the baseline. N~2~O is a covered gas but is not quantified here, because no primary-source emission factor for NH~3~ combustion in a furnace was found.

## 27.3 Data and assumptions

Table: **Table 27.1.** Principal inputs. All web values accessed 23 November 2026. *Source: results/research/singapore/assumptions.json; backend/amcrax/data/singapore.yaml.*

| Input | Value | Unit | Origin | Source |
|---|---|---|---|---|
| NH~3~ price, grey | 450 | USD/t | scenario (literature) | Cho et al. (2026), Table 4; range 300 to 610, Table 8 |
| NH~3~ price, blue | 487 | USD/t | scenario (secondary web) | S&P Global Commodity Insights (2025): 400 (Far East Asia) and 574 (NW Europe); derived mean, article not fetched (HTTP 403) |
| NH~3~ price, green now / 2030 / 2050 | 1000 / 709 / 463 | USD/t | scenario (literature) | Cho et al. (2026), p. 17, Table 9 |
| Electricity | 0.140 | USD/kWh | derived | 2025 mean USEP (Energy Market Authority, 2026) plus network and fees (SP Group, 2026); not an industrial contract price |
| Regulated tariff, Q4 2026 | 28.59 | cent/kWh before GST | literature | SP Group (2026) |
| Carbon tax 2026 and 2027 | 45 | SGD/t CO~2~e | literature | National Environment Agency (n.d.); 50 to 80 intended by 2030 (not legislated) |
| Carbon tax threshold | 25 000 | t CO~2~e/yr | literature | National Environment Agency (n.d.) |
| Exchange rate | 1.290 | SGD/USD | secondary web | Asian Development Bank (2026), close of 20 November 2026 |
| Catalyst (Ni) price, life | 33.4, 2 | USD/kg, yr | literature | Cho et al. (2026), Tables 3 and 4 |
| Discount rate, plant life | 0.10, 25 | -, yr | literature | Kum et al. (2026), Table 5 |
| Operating hours | 8000 | h/yr | literature | Cho et al. (2026), Table 4 |
| Singapore location factor | 1.0 | - | assumption | no sourced factor found |
| Heat fuel | supplementary NH~3~, 100 % LHV | - | assumption | `economics.yaml` |
| Hydrogen benchmarks | 3.0, 3.06, 6.0, 10.0 | USD/kg | secondary web (3.06: Argus sample report PDF, p. 2) | Table 27.4 |

The labour rate, fixed-cost fractions and CAPEX shares are Indian or European small-plant bases (Chopra et al., 2026, Table 2) and are not Singapore values. No Singapore gas price, WACC, labour rate or location factor was retrieved. Electricity contributes less than 0.1 % of LCOH, so its derived status does not affect the results. The NE Asia SMR marker (3.06 USD/kg including capex, 6 January 2026) was read from page 2 of the Argus sample report PDF in the independent review; an earlier value of 4.68 USD/kg, taken from search-result text for a different issue, was not in that source and was replaced. The 2025 monthly USEP values and the S&P and ASEAN Centre for Energy figures come from search-result text only, because the source pages were script-rendered, blocked or returned errors; they are flagged `secondary_web` in the assumptions register. The Ministry of Trade and Industry (2022) hydrogen strategy URL returned HTTP 404 on 23 November 2026 and no number is taken from it.

## 27.4 Results

### Cost by ammonia scenario

Table: **Table 27.2.** LCOH and REC of the baseline cracker by ammonia scenario, with and without heat integration (HI). The plant makes 2012.7 t H~2~/yr (251.6 kg/h) and needs a total capital investment of 2.78 MUSD. *Source: independent Python calculation on Aspen Plus V15 baseline results; results/research/singapore/scenario_results.json, results[*].lcoh_USD_per_kg, rec_USD_per_kg.*

| Scenario | NH~3~ price (USD/t) | LCOH, HI on (USD/kg) | LCOH, HI off (USD/kg) | REC, HI on (USD/kg) | REC, HI off (USD/kg) |
|---|---|---|---|---|---|
| Grey | 450 | 3.613 | 3.827 | 0.573 | 0.787 |
| Blue | 487 | 3.885 | 4.116 | 0.595 | 0.826 |
| Green, 2050 | 463 | 3.708 | 3.928 | 0.581 | 0.801 |
| Green, 2030 | 709 | 5.517 | 5.852 | 0.727 | 1.063 |
| Green, current | 1000 | 7.656 | 8.128 | 0.900 | 1.373 |

<!-- data: results/research/singapore/scenario_results.json results["<scenario>|heat_integration_on|off"].lcoh_USD_per_kg, rec_USD_per_kg, nh3_price_USD_per_t; annual_h2_kg 2012706.44; capex_total_USD 2780626.64 -->

In the grey case with heat integration, the feed NH~3~ is 3.040 of 3.613 USD/kg (84 %); annualised capital is 0.152, fixed operating cost 0.149, supplementary NH~3~ for heat 0.268, and electricity, cooling water and catalyst together 0.004 USD/kg (Figure 27.1). Heat integration lowers the LCOH by 0.214 USD/kg (3.827 to 3.613), 5.6 % of the case without it, entirely through supplementary fuel (0.479 to 0.268 USD/kg) and cooling water. Heat-exchanger capital does not respond to heat integration in this model, because no sourced cost per unit area exists, so this saving is gross of exchanger cost.
<!-- data: results/research/singapore/scenario_results.json results["grey|heat_integration_on"].breakdown_USD_per_kg; results["grey|heat_integration_off"].lcoh_USD_per_kg 3.826710; tornado.json bars[heat_integration].swing 0.21378 -->

![**Figure 27.1.** Cost breakdown of the baseline cracker by ammonia scenario. The feed NH~3~ term dominates every scenario; REC changes little between scenarios, because only the supplementary fuel scales with the NH~3~ price. *Source: independent Python calculation on Aspen Plus V15 baseline results (results/research/singapore/scenario_breakdown.csv).*](../../results/figures/research/singapore_cost_breakdown.png){width=85%}

### Sensitivity

Table: **Table 27.3.** One-at-a-time sensitivity of the LCOH, grey scenario (450 USD/t), heat integration on, base 3.613 USD/kg. *Source: results/research/singapore/tornado.json bars[*].swing.*

| Parameter and range | Swing in LCOH (USD/kg) |
|---|---|
| NH~3~ price 300 to 610 USD/t | 2.279 |
| Capacity ×0.25 to ×4 (feed 25 to 400 kmol/h) | 0.400 |
| PSA recovery 0.95 to 0.756 (linear rescale of the stored result, not re-simulated) | 0.247 |
| CAPEX multiplier 0.5 to 1.5 | 0.229 |
| Heat integration on versus off | 0.214 |
| Operating hours 8000 to 7000 h/yr | 0.043 |
| Capacity exponent 0.7451 to 0.8 | 0.021 |
| Discount rate 8.5 to 10 % | 0.017 |
| Plant life 25 to 20 yr | 0.010 |
| Catalyst price 0.5× to 2×, or lifetime 4 to 1 yr | 0.003 each |
| Electricity 0.084 to 0.222 USD/kWh | 0.001 |
| Carbon tax 0 to 80 SGD/t | 0.000 |

<!-- data: results/research/singapore/tornado.json bars[*].swing -->

![**Figure 27.2.** Tornado diagram of the LCOH (grey scenario, heat integration on). The ammonia price outweighs every other parameter by a factor of five or more. *Source: independent Python calculation (results/research/singapore/tornado.csv).*](../../results/figures/research/singapore_tornado.png){width=85%}

Over a feed range of 25 to 1000 kmol/h NH~3~ the grey LCOH falls from 3.903 to 3.463 USD/kg, a ratio of 1.127. Deka et al. (2025), as quoted in the project brief, report 5.21 to 3.58 USD/kg over the same range, a ratio of 1.455; the paper is not in the library and the value is unverified. The weaker scale effect here follows from the feed-dominated cost structure and the 0.8 scaling exponent.
<!-- data: results/research/singapore/cost_vs_capacity.csv lcoh at 25 and 1000 kmol/h; benchmarks.json comparisons[Deka].amcrax_ratio_25_to_1000_kmol_h 1.12691, literature_ratio 1.45531 -->

![**Figure 27.3.** LCOH and REC against plant capacity, grey scenario. *Source: independent Python calculation (results/research/singapore/cost_vs_capacity.csv).*](../../results/figures/research/singapore_cost_vs_capacity.png){width=80%}

### Break-even ammonia price

Table: **Table 27.4.** Delivered NH~3~ price at which LCOH equals each hydrogen benchmark (Eq. 27.2). The benchmarks differ in basis and none is a Singapore transaction price. *Source: results/research/singapore/breakeven_ammonia_price.json results.heat_integration_on|off[*].breakeven_nh3_USD_per_t.*

| Hydrogen benchmark | USD/kg H~2~ | Break-even NH~3~, HI on (USD/t) | Break-even NH~3~, HI off (USD/t) |
|---|---|---|---|
| Singapore low-carbon willingness to pay (S&P Global Commodity Insights, 2025) | 3.0 | 367 | 344 |
| NE Asia SMR production cost incl. capex (Argus Media, 2026) | 3.06 | 375 | 352 |
| Blue hydrogen delivered to East Asia, midpoint of 5 to 7 (ASEAN Centre for Energy, n.d.) | 6.0 | 775 | 728 |
| Low-carbon offers FOB Malaysia (S&P Global Commodity Insights, 2025) | 10.0 | 1319 | 1239 |

<!-- data: results/research/singapore/breakeven_ammonia_price.json results.heat_integration_on|off.<benchmark>.breakeven_nh3_USD_per_t (366.61, 374.77, 774.76, 1318.97 | 344.30, 351.97, 727.88, 1239.31) -->

![**Figure 27.4.** Break-even NH~3~ price against hydrogen benchmarks. *Source: independent Python calculation (results/research/singapore/breakeven_ammonia_price.json).*](../../results/figures/research/singapore_breakeven.png){width=80%}

At the NE Asia SMR benchmark of 3.06 USD/kg no scenario recovers its cost: with heat integration the NPV is -10.1 MUSD (grey), -15.1 MUSD (blue), -11.8 MUSD (green 2050), -44.9 MUSD (green 2030) and -84.0 MUSD (green, current), and no IRR or payback exists for any of them. Every scenario LCOH (3.613 USD/kg and above, Table 27.2) lies above this selling price. These indicators are pre-tax, at constant prices and with equipment-level CAPEX that probably understates real cost (Section 27.5); they are screening figures, not an investment case.
<!-- data: results/research/singapore/scenario_results.json results["<scenario>|heat_integration_on"].npv_USD, irr, payback_yr -->

### Uncertainty

Table: **Table 27.5.** Monte Carlo LCOH (5000 samples, seed 20261123, heat integration on, independent draws). Ranges: NH~3~ price triangular over the scenario range; electricity 0.084 to 0.2216 USD/kWh; catalyst price 0.5× to 2×; catalyst life 1 to 4 yr; CAPEX multiplier 0.5 to 1.5; discount rate 8.5 to 10 %; operating hours 7000 to 8000 h/yr; plant life 20 to 25 yr. *Source: results/research/singapore/monte_carlo.json results.<scenario>.lcoh_p5, lcoh_p50, lcoh_p95.*

| Scenario | p5 (USD/kg) | p50 (USD/kg) | p95 (USD/kg) |
|---|---|---|---|
| Grey | 2.849 | 3.643 | 4.432 |
| Blue | 3.444 | 3.900 | 4.341 |
| Green, current | 7.045 | 7.547 | 7.909 |
| Green, 2030 | 4.300 | 5.525 | 6.713 |

![**Figure 27.5.** Monte Carlo distributions of the LCOH by scenario. *Source: independent Python calculation (results/research/singapore/monte_carlo_samples_grey.csv and monte_carlo.json).*](../../results/figures/research/singapore_monte_carlo.png){width=85%}

### Carbon tax

With ammonia-fired heat the baseline has no direct CO~2~ and the carbon-tax term is exactly zero for tax rates from 0 to 80 SGD/t (Table 27.3). For a hypothetical gas-fired furnace, which is not the baseline, the heat duty would emit 1248.7 t CO~2~e/yr, below the 25 000 t threshold, so no tax would be due. The heat map that ignores the threshold (labelled hypothetical, gas heat at 4.25 USD/GJ, Kum et al., 2026; 56.1 t CO~2~/TJ, European Commission, 2018) shows an LCOH of 3.392 USD/kg at 450 USD/t with no tax and 3.414 USD/kg at 45 SGD/t. Gas-fired heat is cheaper than ammonia-fired heat here (3.392 against 3.613 USD/kg), but the comparison depends on an assumed gas price and on no Singapore gas price source. The 56.1 t CO~2~/TJ factor is the IPCC 2006 default quoted in the EU Regulation; the Annex VI PDF returned no readable text on 23 November 2026.
<!-- data: results/research/singapore/tornado.json bars[carbon_tax_SGD_per_t].swing 0; results/research/validation/economics.json items[E14, E15].observed 0.0 and 1248.706; heatmap_nh3_price_x_carbon_tax_gas_heat_hypothetical.csv row carbon_tax 0 and 45, column nh3_450 (3.39240, 3.41404) -->

![**Figure 27.6.** LCOH over ammonia price and carbon tax for gas-fired heat (hypothetical; threshold ignored). The tax shifts the LCOH by a few hundredths of a USD per kg across the legislated range. *Source: independent Python calculation (results/research/singapore/heatmap_nh3_price_x_carbon_tax_gas_heat_hypothetical.csv).*](../../results/figures/research/singapore_heatmap_nh3_price_carbon_tax.png){width=80%}

![**Figure 27.7.** LCOH over ammonia price and plant capacity. *Source: independent Python calculation (results/research/singapore/heatmap_nh3_price_x_capacity.csv).*](../../results/figures/research/singapore_heatmap_nh3_price_capacity.png){width=80%}

## 27.5 Validation status and failures

Fifteen items are recorded in `results/research/validation/economics.json`: 9 pass, 0 fail, 6 informational. The passes are reproduction of the stored Section 19 LCOH (3.918842 USD/kg, exact to 10^-9) in a legacy CAPEX mode, closure of the cost breakdown, unit consistency, the REC definition, the break-even inversion, the stoichiometric floor on feed NH~3~ (6.756 against 5.632 kg/kg), zero tax on ammonia heat, and the below-threshold gas-heat case. The informational items are comparisons that are not like for like, plus the Cho et al. Ru-to-Ni REC difference (6.97 %, against the 7.0 % quoted), which is arithmetic on Cho's own numbers and therefore a literature consistency check, not a validation.

**REC against Cho et al. (2026).** The AmCraX REC of 0.573 USD/kg is far below the 1.856 (Ru) to 1.995 (Ni) USD/kg of Cho et al. (2026, Fig. 8d). Cho et al. include 180 bar product compression, temperature-swing adsorption, NO~x~ treatment, off-site, engineering and contingency items, and a plant of about 100 kg H~2~/h with a 97 % conversion optimisation. The AmCraX boundary has none of these and runs at 251.6 kg H~2~/h. The gap is a boundary difference and is neither a validation pass nor a failure. The legacy-CAPEX LCOH of 3.919 USD/kg and the equipment-level value of 3.613 USD/kg both lie below the 5.439 USD/kg total of Cho et al. (2026) at 450 USD/t, for the same reason. The equipment-level CAPEX is a feed-scaled screening estimate and is probably optimistic.

**Halim et al. (2025).** The LCOH values of 15.1 (green) and 10.1 (blue) USD/kg for a 60.1 MW plant could not be checked: only the abstract of Halim et al. (2025) was available. Those values are not used in any comparison here.

**Consistency between sections.** The same plant appears at 3.613 USD/kg here (equipment-level CAPEX, 0.152 USD/kg capital) and at 3.919 USD/kg in Sections 19, 28 and 29 (correlation CAPEX, 0.356 USD/kg capital). The 0.31 USD/kg difference comes from the CAPEX basis and the CAPEX-proportional fixed costs (capital 0.356 against 0.152, fixed operating cost 0.252 against 0.149 USD/kg); the feed and heat terms are identical. Cross-section comparisons must use one basis.

## 27.6 Comparison with literature

The Singapore-specific literature offers prices but few like-for-like costs. The 3 USD/kg willingness to pay for low-carbon hydrogen and the 3.06 USD/kg NE Asia SMR cost are benchmark prices, not plant costs, and their basis differs. The break-even prices in Table 27.4 are therefore thresholds against stated benchmarks and not forecasts. Ammonia direct combustion and bunkering projects in Singapore (Maritime and Port Authority of Singapore, 2025) concern use of ammonia as a fuel and are discussed in Section 29.

## 27.7 Limitations

* Ammonia prices are scenarios from non-Singapore sources, three of them from one paper (Cho et al., 2026) and one (blue) from unretrievable secondary text.
* CAPEX is a screening estimate; no equipment was sized. Heat-exchanger cost does not follow heat integration.
* The catalyst mass comes from the Cho et al. space velocity (248.5 kg), not from the kinetic PFR results; its effect on LCOH is 0.003 USD/kg.
* Labour, overhead, location factor and discount rate are not Singapore values.
* Landed cost, product compression, storage, NO~x~ treatment and N~2~O are not modelled or quantified.
* NPV, IRR and payback are pre-tax, at constant prices and at a single selling price.

## 27.8 Implication for hypothesis H2

For the baseline cracker the feedstock term is 84 % of the LCOH in the grey case, and the ammonia price alone moves the LCOH by 2.279 USD/kg over 300 to 610 USD/t, five times the next parameter; REC varies only from 0.573 to 0.900 USD/kg across all scenarios. The cost result therefore turns on the ammonia price. It does not by itself test the other half of H2, low carbon intensity, which depends on how each price scenario is produced (Section 30); the cheapest scenarios here (grey, 450 USD/t; green 2050, 463 USD/t) are not equally low in carbon, and the low-carbon scenario at today's price (green, 1000 USD/t) gives an LCOH of 7.656 USD/kg. The verdict on H2 is given in Section 31.
