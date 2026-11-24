# Abdoos, Di Benedetto and Russo (2025): full-text reading for H4

Source: Abdoos, B., Di Benedetto, A., & Russo, D. (2025). Integrated design, scale-up, and surrogate-based
optimization of PSA systems for hydrogen purification from ammonia decomposition. *Chemical Engineering Journal*,
526, 170994. https://doi.org/10.1016/j.cej.2025.170994 (open access, CC BY 4.0).

Read in full on 24 November 2026. Every table and figure page was checked on the page image. The supplementary
material (Table S1 bed sizes, Figs. S1 and S2) was not read. The structured values, with page, table and status
(verbatim, figure reading, derived, not reported), are in `research/data/abdoos2025_extract.json`. This note
summarises them and compares them with the AmCraX inputs. It is a comparison with published literature, not a
validation. The paper is a simulation study, not a measurement. No AmCraX analysis, rule or verdict was changed.

## 1. What the paper models

| Item | Value | Where | Status |
|---|---|---|---|
| Feed | 75 % H2 / 25 % N2, dry. Full NH3 conversion assumed. Trace NH3 removal "beyond the scope" | p. 3, Sec. 2.1 | verbatim |
| NH3, H2O | not model components | whole text | not reported |
| Adsorbent | zeolite 5A, one layer (13X fitted and rejected) | pp. 3, 5, 8 | verbatim |
| Beds, cycle | 4 adiabatic beds, 8 steps (AD, EQ-DP, DP-SP, BD, PU, EQ-RP, RP), steps of 15 s and 85 s alternately | p. 4, Table 1, Fig. 2 | verbatim |
| Cycle time | 400 s, 100 s adsorption per bed. Not a decision variable | Table 1 | derived |
| Pressures (base) | 10 bar adsorption, 5.7 bar after EQ, 2.85 bar after DP-SP, atmospheric blowdown and purge, 4.95 bar after EQ-RP | pp. 4-5, Fig. 3 | verbatim |
| Purge-to-feed ratio | not given | - | not reported |
| Model | Aspen Adsorption: Peng-Robinson, adiabatic, LDF, Ergun, axial dispersion, 20 upwind nodes, extended Langmuir-Freundlich (Table 7) | p. 5, Table 2; p. 9, Table 7 | verbatim |
| Validation | Breakthrough only (H2/N2/CH4/Ar, 1 bar, 40 °C, 1.3e-3 kmol/h) against Kast 1988 and Yanez et al. 2020, compared graphically. No cyclic-PSA experiment | p. 8, Fig. 6 | verbatim |
| Surrogate | MLP 12-6 trained on 2,000 LHS runs, NSGA-II (pop. 400). Agreement with the full-order model: R2 0.999 purity, 0.996 recovery, 0.996 SEC | p. 6; Fig. 13 | verbatim |
| Scale | feed 60-150 kmol/h (optima 83-98 kmol/h, about 99-122 kg/h H2 product). Similarity-based scale-up | Table 6, Table 8; Sec. 2.4 | verbatim / derived |
| Decision bounds | 6-12 bar, 10-50 °C, D 0.7-1.2 m, L 1.7-4.5 m | Table 6 | verbatim |

## 2. Every purity-recovery-energy point

| Point | Purity % | Recovery % | SEC MJ/kg (kWh/kg) | Operating point | Where | Status |
|---|---|---|---|---|---|---|
| Base case | 96.35 | 91.1 | 7.2 (2.00) | D 0.866, L 3, 25 °C, 92 kmol/h, 10 bar | p. 13, Table 8 | verbatim |
| Optimal 1 | 99.99 | 77.44 | 8.76 (2.43) | D 0.9679, L 4.499, 10 °C, 84.19 kmol/h, 11.60 bar | Table 8; Fig. 12 | verbatim |
| Optimal 2 | 99.95 | 81.92 | 8.10 (2.25) | D 0.949, L 4.445, 10 °C, 98.107 kmol/h, 11.29 bar | Table 8; Fig. 12 | verbatim |
| Optimal 3 | 99.03 | 83.92 (text 83.9) | 6.4 (1.78) | D 0.99, L 4.4, 10.65 °C, 83.18 kmol/h, 7.87 bar | Table 8; p. 13 | verbatim |
| Ultra-high purity, D about 0.96 m | "up to 99.99" | not given | 8.6 | 10 bar | p. 11 text | verbatim |
| Ultra-high purity, D 1.2 m | "same purity" | not given (figure: about 72-75) | 7.8 | - | p. 11 text; Fig. 12 | verbatim / figure reading |
| Abstract | "up to 99.99" | 77.4 | "as low as 5.19" | **not one point** | p. 1 | verbatim |
| Pareto front | 90 to 99.99 | about 69 to 92 | about 4.9 to 8.8 | Figs. 9, 12 | p. 10, p. 12 | figure reading |
| Front at about 99.99 % | 99.99 | about 69 to 77.4 | about 6.5 to 8.76 | Fig. 12 colours | p. 12 | figure reading (about ±3 points) |
| Front at about 99.2-99.8 % | 99.2-99.8 | up to about 84-87 | about 7.9 to 8.3 | Fig. 12 colours | p. 12 | figure reading (about ±3 points, ±0.1 % purity) |

- The two "improvements" in the abstract both belong to Optimal 3 against the base case: 2.78 % in purity and 11.11 % in
  energy (99.03/96.35 and 6.4/7.2). At 99.99 % the SEC is 22 % above the base case. The search summary that reached
  the project earlier ("about 99.99 %, 77 %, 5.2 MJ/kg") joins two different points. Its "four-layer bed, 35 bar,
  99.97 %, 79 %" is the paper's citation of Moon et al. (2016), which treats syngas. It is not a result of this paper.
- N2 in the product (derived; binary product, so N2 = 1 - purity): about 100 ppm (Opt 1; 50-150 ppm allowing for
  rounding), about 500 ppm (Opt 2), about 9,700 ppm (Opt 3) and about 36,500 ppm (base). NH3 in the product is not modelled.
- ISO 14687 Grade D: the paper does not mention it. On H2 and N2, only Optimal 1 is compatible (99.99 % and about 100 ppm,
  at **77.44 % recovery**). Optimal 2 fails the N2 limit (about 500 ppm > 300). The NH3 limit and the other species cannot be
  assessed from the paper.
- Tail gas: blowdown and purge are at atmospheric pressure (p. 5, Fig. 3). The composition is not printed. A binary
  mass balance gives H2 in the tail gas of about 40 % (Opt 1), 35 % (Opt 2), 33 % (Opt 3) and 23 % (base) (derived).
- Productivity: Fig. 9 colour bar about 0.005-0.028 kmol/(kg h), with high-purity points near 0.005 (figure reading).
  Table 8 does not give productivity. The sensitivity figures disagree with each other on the base-case productivity.
- SEC definition (Table 5, Eq. 12): adiabatic compressor work with eta 0.8 per kg of H2 product. The compressor inlet
  pressure is not printed. Compressing the whole feed from 1 bar to the adsorption pressure reproduces all four Table 8
  SEC values within 1-3 % (derived; gamma 1.4, eta 0.8, single stage, feed temperature; for example Opt 1: 8.92 against
  8.76 printed). **The SEC is therefore the feed compression from about
  atmospheric pressure. It is not a PSA's own power.**

## 3. Scale-up and cost

- Table 9 (Aspen Process Economic Analyzer): CAPEX 8.556 / 8.6104 / 8.3879 MUSD, OPEX 6.926 / 7.8288 / 6.801 MUSD/yr,
  sales 9.494 / 2.7882 (as printed) / 7.983 MUSD/yr, payout 3.332 / 4.412 / 7.096 yr for Optimal 1 / 2 / 3.
- Internal inconsistencies:
  - Optimal 2 sales of 2.7882 cannot give a 4.412-yr payout; that payout implies about 9.78 MUSD/yr.
  - The text calls Zone 1 the highest CAPEX, but the table shows Zone 2 higher.
- Operating hours, H2 price, cost year and the meaning of "raw materials" are not stated. No per-kg purification cost is
  printed. The OPEX evidently includes the feed (about 8 USD/kg H2 at an assumed 8,760 h/yr). A purification-only
  cost per kg cannot be extracted.
- Bed sizes for the pilot and industrial scales are only in Supplementary Table S1 (not read). The optimal beds are 4.4-4.5 m
  long and 0.95-0.99 m in diameter, at 83-98 kmol/h of feed.

## 4. Sensitivities and the authors' limitations

One-at-a-time around a base case (Figs. 7-8, figure reading, about ±0.5):

| Variable | Purity | Recovery | SEC (MJ/kg) |
|---|---|---|---|
| Pressure 6 to 12 bar | 83.7 to 95.8 % | 95.2 to 90.9 % | 4.9 to 8.0 |
| Temperature 10 to 50 °C | 95.6 to 87.7 % | 91.7 to 93.1 % | 6.8 to 7.7 |
| Bed length 1.7 to 4.5 m | 85 to 95.6 % | 95.6 to 88.3 % | 6.9 to 7.45 |
| Diameter 0.7 to 1.2 m | 88.3 to 98.4 % | 94.3 to 82 % | 6.9 to 8.05 |
| Flow 60 to 150 kmol/h | 97.6 to 86 % | 88 to 95.2 % | 7.5 to 6.9 |

- Every variable that raises purity lowers recovery. This is the paper's stated trade-off (pp. 8, 11).
- The curves do not pass through the Table 8 base case: at 10 bar they give about 93 % purity, against 96.35 %.
- Purge ratio, cycle time and residual NH3 were not studied.
- Authors' limitations:
  - The adiabatic and no-radial-gradient assumptions may limit accuracy.
  - A cycling bed breaks through earlier than a fresh one.
  - Experimental validation of the optimised cycles and the effect of NH3 traces are future work.
  - Data are available on request.

## 5. Assessment against AmCraX (comparison with published literature)

**(a) H4-a, higher purity costs recovery.**
- The paper gives the first purity-recovery relation for a cracked-ammonia composition in the library. It is
  simulated, idealised (dry, NH3-free) and limited to 6-12 bar.
- Along the reported optima: 99.03 % at 83.92 %, 99.95 % at 81.92 % and 99.99 % at 77.44 %. The front at about 99.99 %
  extends down to about 69 % recovery (figure reading).
- The direction agrees with H4-a and with Yanez et al. 2020. The slope between 99.95 and 99.99 % is about 1.1
  recovery points per 0.01 purity point. Yanez gives 0.275 points per 0.01 point over 99.25-99.97 %. The paper's slope is
  steeper, but over a much narrower purity span.
- The paper is not independent of Yanez: its equations (Table 2) and its breakthrough check (Fig. 6) cite Yanez et al. 2020.
- What the coded rule `v2_h4a` reads, as written: the four keys `row_evidence/H4-a/numbers/{yanez2020_recovery_99.25,
  yanez2020_recovery_99.97, mass_balance_recovery_99.91, mass_balance_recovery_99.975}` in
  `results/research/purification/phase2_comparison.json`, and the `source_type` of every entry under
  `inputs/psa_recovery/<grade>/<case>`.
- The verdict depends only on whether every `source_type` begins with `python` or `aspen`.
- Consequences of adding the paper's numbers:
  - **Added under new keys** in `row_evidence/H4-a/numbers` (for example `abdoos2025_recovery_99.99` = 0.7744,
    `abdoos2025_recovery_99.95` = 0.8192, `abdoos2025_recovery_99.03` = 0.8392): the rule would not read them without a
    code change, and it would still return **INCONCLUSIVE**. Its conclusion text ("only sourced slope: Yanez") would
    then be out of date.
  - **Added as entries under `inputs/psa_recovery`** with `source_type` "literature" (for example
    `fuel_cell_grade_D/abdoos` = 0.7744, `industrial_99.9/abdoos` = 0.8192): `computed` stays False, so the rule
    returns **INCONCLUSIVE**.
- The methodology treats a published simulation as a literature comparison, not as a computed AmCraX result, so the
  rule could not move to SUPPORTED even after a code change. A further point: if `computed` were ever True, the
  SUPPORTED/CONTRADICTED branch compares the two flat mass-balance numbers (0.751276 < 0.751626). It does not compare
  any sourced slope, so the rule as written cannot use this paper's slope in its decision.
- Net effect: the row's literature-comparison text can be strengthened ("two sources, one for cracked-ammonia
  composition, agree on the direction"). The coded verdict stays INCONCLUSIVE.

**(b) H4-b, stricter purity raises cost.**
- The paper gives no per-kg purification cost and no purity-only cost increment. Its Table 9 has an inconsistent
  Zone 2 sales figure and does not state hours or price.
- Its energy increment from 99.95 % to 99.99 % (+0.66 MJ/kg = +0.18 kWh/kg) is extra feed compression to a higher
  adsorption pressure (11.29 to 11.60 bar), with less product to divide by. It does not transfer to the AmCraX 20 bar feed, which
  needs no feed compressor.
- What transfers is the recovery step 0.8192 to 0.7744. Interpolation in the AmCraX industrial-grade cost curve
  (`psa_recovery_sensitivity`, 30 bar delivery) gives about 4.10 USD/kg at 0.8192 and 4.21 at 0.7744, an increment of
  about **0.11 USD/kg** (interpolation, not a model run). This is above the 0.006 USD/kg resolution and lies between the
  existing Yanez (0.166) and mass-balance (0.002) increments.
- Under `v2_h4b` as written, an added `equal_delivery_increment` key would not change the verdict: the rule requires
  every basis to exceed the resolution, and the mass-balance basis (0.002) does not.

**(c) H4-d, membrane against PSA.**
- **Grade D**: the only paper point that meets the N2 limit is 0.7744 (at 99.99 %). It lies **between** the parities
  0.745 (high-cost membrane) and 0.783 (central membrane): the membrane is cheaper against the central membrane cost and
  PSA is cheaper against the high-cost one.
- At the AmCraX Grade D purity of 99.975 % a linear interpolation between the paper's 99.95 % and 99.99 % points gives
  about 0.79, just above 0.783. The two points come from different Pareto regions, and the surrogate recovery error is
  1-3 points.
- So the paper's Grade D recovery sits on the parity band and does not decide the row.
- **Industrial grade**: 0.8192 at 99.95 % lies above both industrial parities (0.749, 0.795), so PSA is cheaper.
- The comparisons are not like for like:
  - The paper works at 6-12 bar against the AmCraX 19.5-20 bar feed.
  - Its feed is dry and NH3-free; AmCraX has about 1 % NH3 and TSA.
  - Its purity is a cycle-average N2 impurity; Grade D adds NH3 ≤ 0.1 ppm, which the paper does not model.
  - Its point is a surrogate-optimised design, not an operating plant.

**(d) H4-e, threshold 0.765.**
- All four Table 8 points (0.7744, 0.8192, 0.8392, 0.911) lie above 0.765. In AmCraX terms the tail gas would not cover the
  furnace demand, and NH3 would be burned for heat.
- The Grade D-compatible point is only 0.009 above the threshold, inside the 1-3 point surrogate recovery scatter.
- The front at about 99.99 % reaches down to about 0.69 (figure reading), below the threshold.
- Under `v2_h4e` as written, adding these values to `inputs/psa_recovery` leaves the sourced range at 0.555-0.85.
  The result is "straddle", so the row stays **INCONCLUSIVE**.

**(e) The AmCraX recovery assumptions.**
- **0.85 at industrial purity** (PSA_AMCRAX, 99.96 %) is **not supported**. It lies above the paper's front at
  matching purity (0.8192 at 99.95 %, 0.7744 at 99.99 %). Recoveries of about 0.85 appear on the front only at about
  99.2-99.8 % purity (figure reading). This is a comparison with one simulation at lower pressure, so it argues against
  the assumption but does not refute it.
- **Industrial low and central cases (0.5715 Yanez, 0.7516 mass balance at 99.91 %)**: the paper's value at 99.91 % would
  be at least about 0.82 if the front is monotonic. That is above both cases, so the paper **brackets** the industrial
  range from above at about 0.82, between the central value and the 0.85 assumption. Interpolated cost at 0.8192: about
  4.10 USD/kg, against 4.05 at 0.85 and 4.27 at 0.7516.
- **Grade D cases (0.555 Yanez, 0.7513 mass balance, 0.81 Mehr)**: 0.7744 lies between the central (0.7513) and high
  (0.81) cases, well above the Yanez low case. The interpolated Grade D cost at 0.7744 is about **4.40 USD/kg**. That
  is 0.06 below the mass-balance central (4.46), 0.16 above the 0.85 assumption (4.24) and far below the Yanez case (5.96).
- The phase-2 note calls the mass-balance central "optimistic". Against this paper it is slightly pessimistic at
  Grade D and clearly pessimistic at industrial grade.

**(f) PSA specific energy.**
- AmCraX adds PSA energy only as cracked-gas compression when the feed pressure is below the requirement (`psa.py`).
  At 19.5 bar the requirement is met, so PSA own power is zero ("not modelled") and only product compression is costed.
- The paper's 6.4-8.76 MJ/kg (1.8-2.4 kWh/kg) is feed compression from about 1 bar. It is **not** a PSA own-power figure
  and should not be added to the AmCraX 20 bar flowsheet.
- The paper therefore does not fill the "no verified PSA own power" gap (purification_literature.json S08). Its earlier
  candidate "5.2 MJ/kg = 1.44 kWh/kg" is a low-purity point of the same compression quantity.

**(g) Paper findings against the project's current statements.**
1. S07 in `purification_literature.json` and the phase-2 note list "about 5.2 MJ/kg" with 99.99 %/77 %, and "four-layer 35 bar,
   99.97 %/79 %" as this paper's results. Both are wrong: the first joins two points, the second is Moon et al. (syngas).
2. The H4-a plain answer says "the only sourced slope (Yanez) is for a different feed". A cracked-ammonia-composition
   slope (simulated) now exists.
3. The 0.85 assumption at 99.96 % lies above this paper's front.
4. The "optimistic" label on the mass-balance central recoveries is not borne out against this paper.
5. `membrane_trl.json` ("no peer-reviewed measurement of PSA on real cracked-ammonia gas") stays true, because this paper is a simulation.
6. Docs that list Abdoos as unread (`known_limitations.md`, `limitations_and_future_work.md`, `41_limitations.md`) are now out of date.

**(h) Boundary differences.**
- Adsorption pressure: the paper's 6-12 bar is below the AmCraX 19.5 bar. The paper's own trend (higher pressure, higher
  purity, lower recovery) means extrapolation to 20 bar is not neutral.
- Feed:
  - The paper's feed is ideal, dry and NH3-free, with no guard layer. AmCraX has about 1 % NH3 and 0.1 % H2O upstream of TSA.
  - Scale: 83-98 kmol/h against about 198 kmol/h.
  - Temperature: 10 °C optimum (feed chilling implied but not costed) against 40 °C in `psa.py`.
- Method:
  - Recovery is an adsorption-step average, from a surrogate with 1-3 point recovery error at 72-78 %.
  - There is no cyclic experiment.
  - Cycle times are fixed and purge is not optimised.
- Energy and cost boundary:
  - The SEC is feed compression, not PSA own power.
  - The costs include feed and have unstated hours and price.
- Purity: purity is the N2 impurity alone. Grade D compliance needs the NH3 polishing that the paper leaves out of scope.

## 6. What could not be determined from the paper

- NH3 and H2O in product or tail gas. Grade D on NH3. Effect of residual NH3 on 5A.
- Purge-to-feed ratio. Optimised step times. Mass-transfer coefficients (not in the main text).
- Bed sizes per scale (Supplementary Table S1, not read).
- Whether the Table 8 values are surrogate or full-order outputs.
- Compressor inlet pressure. It is inferred to be about 1 bar from the SEC reconstruction.
- Per-kg purification cost, operating hours, H2 price and cost year. The correct Zone 2 sales figure.
- The recovery at exactly 99.97 % or 99.975 % (only interpolation between two different optima).
- Any behaviour above 12 bar.

## 7. Reference record

`research/reference_additions/phase2_fulltext_abdoos.json` carries the same citekey `abdoos2025psa` as the earlier,
unread entry in `phase2_purification.json`. The report builder takes the first file in sorted order on a duplicate key
(`phase2_fulltext_abdoos.json` sorts first). The evidence matrix collects keys into a set. In both cases the
full-text record is the one used.
