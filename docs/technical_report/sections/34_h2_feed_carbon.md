<!-- cites: sg_cpa2018, argus_h2_markers, lee2022ammonia, gmk2026euaprice, ahmad2025gtcc -->

# 34 Feedstock (H2): feed dominance and carbon pricing

Hypothesis H2 states that affordable, low-carbon ammonia is essential for cracking to make sense in Singapore. Phase 2 splits it into a cost component (does the ammonia price dominate the cost of cracked hydrogen, and how cheap must it be?), a carbon component (does low-carbon ammonia deliver low-carbon hydrogen?), and a cross-claim (does Singapore carbon pricing reward low-carbon ammonia?). Cost and carbon intensity are kept apart throughout.

## 34.1 Feed dominance (H2-a)

On the unified basis the ammonia feed is 3.040 of 4.015 USD/kg, a share of 75.7 %; with the supplementary NH~3~ burnt for heat the share is 82.4 %. The share is 70 % at 300 USD/t and 80 % at 610 USD/t. Because a share follows from assumed prices, the row was tested by thresholds with one comparator throughout, a feed share of 50 % of the LCOH: the feed stays above half of the LCOH for NH~3~ above 115 USD/t (174 with adverse non-feed inputs, 125 without heat integration), and for a CAPEX multiple below x4.27 at 450 USD/t (x2.81 at 300 USD/t). Sourced NH~3~ prices run from 300 to 1052 USD/t. The largest CAPEX multiple considered, x1.5, is the sensitivity bound of Cho et al. (2026, Table 8), not a sourced plant cost; the independent published estimates correspond to x0.41 to x0.85. All of these lie on the feed-dominant side. In a Monte Carlo analysis with 5000 draws the feed share has p5/p50/p95 of 0.694/0.751/0.802 (minimum 0.643), and feed is the largest item in every draw. The variance-based analysis of Section 37 agrees: the NH~3~ price has a total-effect index of 0.896 [0.875, 0.917]. One caveat is stated with this result: the reconversion cost (all items except feed) is driven by CAPEX and PSA recovery, not by the NH~3~ price.
<!-- data: results/research/carbon_pricing/feed_dominance.json feed_share 0.7571, feed_share_at_cho_range, thresholds (114.9 USD/t; x7.24 / x4.70 / x4.27; x4.83 / x3.09 / x2.81), monte_carlo; results/research/uq/gsa_sobol.json -->

![**Figure 34.1.** Feed share of the LCOH against the NH~3~ price and the CAPEX multiple, with the sourced ranges. *Source: independent Python calculation, results/figures/research/carbon_feed_dominance.png.*](../../results/figures/research/carbon_feed_dominance.png){width=85%}

## 34.2 How cheap must ammonia be (H2-b)

Against the NE Asia SMR marker of 3.06 USD/kg (Argus Media, 2026) the break-even NH~3~ price is 320.0 USD/t; against a Singapore willingness to pay of 3.0 USD/kg it is 311.8 USD/t. Over the CAPEX range the break-even is 371 (x0.41), 363 (x0.5), 320 (x1.0) and 277 USD/t (x1.5), and 379 USD/t with favourable non-feed inputs. Against the 6.0 USD/kg delivered low-carbon benchmark it is 720 USD/t. The sourced NH~3~ prices start at 300 USD/t (grey, low) and 315 USD/t (green 2050, low), so they lie on both sides of the break-even against the marker, and on both sides of 720 USD/t as well. By the threshold rule the row is therefore INCONCLUSIVE, and the threshold is the finding; component H2-E (feed dominance and break-even price) is then PARTIALLY SUPPORTED, resting on row H2-a. An earlier reading of this row as a necessity statement, compared only with the central prices, could not fail and was withdrawn after the independent review (Section 31.4). At the central grey price of 450 USD/t, ammonia is not cheap enough against the 3.06 USD/kg marker. In the Monte Carlo analysis P(LCOH < 3.06 USD/kg) = 1.4 % for grey ammonia, conditional on the assumed triangular input distributions (whose lower NH~3~ price bound lies only 20 USD/t below the break-even), and the NPV at that price is negative (mean -16.8 MUSD, p95 -2.6 MUSD in Section 37).
<!-- data: results/research/carbon_pricing/feed_dominance.json breakeven_vs_ne_asia_smr_by_capex_multiplier, monte_carlo P(grey LCOH < 3.06) 0.014; results/research/uq/row_evidence.json H2-b -->

## 34.3 Carbon intensity of the hydrogen (H2-c, H2-d)

Table: **Table 34.1.** Carbon intensity of cracked hydrogen by ammonia route, kg CO~2~e/kg H~2~, central value and range. Simplified accounting, not a full LCA. *Source: independent Python calculation with literature factors (Lee et al., 2022), results/research/carbon_pricing/carbon_intensity.json routes.*

| Route | Central | Range |
|---|---|---|
| Grey NH~3~ | 19.52 | 15.11 to 34.22 |
| Blue NH~3~ (Lee v1) | 8.93 | 6.07 to 14.53 |
| Blue NH~3~ (Lee v2) | 6.07 | 6.07 to 11.95 |
| Green NH~3~, embedded emissions included | 2.43 | 0.93 to 3.93 |
| Green NH~3~, Lee boundary (0 upstream) | 0.41 | - |

For cracked hydrogen to beat unabated SMR hydrogen, the ammonia gate emission factor must lie below 1.31 to 1.58 kg CO~2~e/kg NH~3~; to beat SMR with carbon capture, below 0.41 to 0.67. For direct NH~3~ power to beat a natural-gas combined cycle the factor must lie below 0.81 to 1.33 (over efficiencies of 0.50 to 0.60 and methane leakage of 0 to 3 %), and 0.98 against the grid. The lowest sourced grey factor (2.0) is above every one of these. Rows H2-c and H2-d are SUPPORTED as necessity statements: low-carbon ammonia is necessary. They are not sufficiency statements: blue v1 (1.16) fails except at high leakage. Against SMR with carbon capture (break-even 0.41 to 0.67) grey fails, and green passes only below that break-even: its high value of 0.48 fails the 3.4 kg/kg capture case.

![**Figure 34.2.** Carbon intensity of the hydrogen by ammonia route, with the break-even emission factors. *Source: independent Python calculation, results/figures/research/carbon_intensity_routes.png.*](../../results/figures/research/carbon_intensity_routes.png){width=85%}

## 34.4 Carbon pricing: Mode A, the actual Singapore boundary (H2-e)

Mode A applies the Singapore carbon tax as legislated. The rate is SGD 45/tCO~2~e for 2026 and any later year; 50 to 80 SGD/t by 2030 is a stated government aim, not law (Carbon Pricing Act 2018; Singapore Statutes Online, 2026). The tax applies to a facility's direct emissions above 25,000 tCO~2~e/yr, with N~2~O counted at a GWP of 265. The self-fired reference plant emits no direct CO~2~ and, by default, no N~2~O, so it is not liable, and the tax is zero for every ammonia route. The upstream emissions of imported ammonia lie outside the Act. Liability would need 11.8 kg/h of N~2~O, which is 5.0 % of the burnt fuel nitrogen or about 1521 ppmv in the estimated flue gas; the turbine value of 0.15 ppmv from Ahmad et al. (2025), transferred to this burner as an illustration only, gives 2.5 tCO~2~e/yr. A natural-gas-heated variant emits 1,249 tCO~2~e/yr and becomes liable only at 20 times the capacity; even then the tax does not depend on the ammonia route. Under the actual boundary, low-carbon ammonia earns no cost advantage: it raises the LCOH by 0.272 (blue) and 4.04 USD/kg (green, current). Row H2-e is CONTRADICTED under Mode A. This follows from the statute, not from a model assumption.
<!-- data: results/research/carbon_pricing/scenarios.json mode_a_actual_boundary (rate 45, threshold 25000, GWP 265, N2O 11.8 kg/h, 5.0 %, 1521 ppmv, 2.5 t/yr, NG variant 1249 t/yr x20.0) -->

## 34.5 Carbon pricing: Mode B, a hypothetical life-cycle price

Mode B is hypothetical, not Singapore law. It charges a carbon price on the life-cycle intensity of the hydrogen and replaces the Mode A tax term, so nothing is charged twice. At a price of zero it reproduces Mode A exactly; a validation check confirms this and a second check confirms that the Mode B term replaces a non-zero actual tax rather than adding to it.

Table: **Table 34.2.** LCOH by ammonia route under the hypothetical life-cycle carbon price (Mode B, not Singapore law), USD/kg H~2~. The 127.4 SGD/t case uses an EU ETS price of about EUR 90/t (Yermolenko, 2026) as context only. *Source: independent Python calculation, results/research/carbon_pricing/scenarios.json.*

| Route | 0 SGD/t | 45 SGD/t | 127.4 SGD/t |
|---|---|---|---|
| Grey | 4.015 | 4.697 | 5.939 |
| Blue | 4.287 | 4.599 | 5.168 |
| Green, current | 8.058 | 8.143 | 8.298 |
| Green, 2030 | 5.919 | 6.004 | 6.159 |
| Green, 2050 | 4.111 | 4.196 | 4.351 |

Table: **Table 34.3.** Hypothetical carbon price at which one ammonia route overtakes another (Mode B, not Singapore law), SGD/tCO~2~e. The closed form, price difference x exchange rate / emission-factor difference, does not depend on CAPEX. *Source: independent Python calculation, results/research/carbon_pricing/thresholds.json pairwise, monte_carlo.*

| Crossover | Central | Range from the intensity ranges | Monte Carlo p5 / p50 / p95 |
|---|---|---|---|
| Blue over grey | 33.1 | 12.4 to 605 | 0 / 21.9 / 156 |
| Green (current) over grey | 305 | 156 to 466 | - |
| Green (2030) over grey | 144 | 74 to 219 | - |
| Green (2050) over grey | 7.2 | 3.7 to 11.0 | - |
| Green (current) over blue | 747 | 357 to 2275 | - |
| Green (2030) over blue | 323 | 155 to 984 | - |

At current prices grey is cheapest up to about 33 SGD/t (closed form; the first point of the 5 SGD/t sweep above it is 35) and blue above it; green at current prices is never cheapest up to 500 SGD/t. With 2030 prices, blue is cheapest from 35 and green from 325 SGD/t. Green 2050 is a projection, so comparing it with today's grey and blue prices mixes time bases. The Monte Carlo draws grey and blue prices independently, which probably overstates the spread of the gap. Under Mode B row H2-e is INCONCLUSIVE: the blue-over-grey range (12 to 605) straddles every reference price, and green needs prices above all of them. The row verdict that votes is the Mode A verdict, because the row is about actual policy.

![**Figure 34.3.** LCOH by ammonia route against the hypothetical life-cycle carbon price (Mode B, not Singapore law). *Source: independent Python calculation, results/figures/research/carbon_price_sweep.png.*](../../results/figures/research/carbon_price_sweep.png){width=85%}

## 34.6 Validation

The carbon-pricing workstream has 28 validation items: 25 numerical verifications and 2 comparisons with published literature (the GWP of 265 and the rate of 45 against the Act) pass, and the one experimental-validation item is marked not available, because none exists. The Python functions are twins of the browser code and agree on 18 test vectors to a relative tolerance of 1e-9.
<!-- data: results/research/validation/carbon_pricing.json; results/research/carbon_pricing/test_vectors.json -->
