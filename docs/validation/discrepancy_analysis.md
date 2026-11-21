# Aspen Plus vs AmCraX Python: discrepancy analysis

Generated from real Aspen Plus V15 runs (`results/validation/equilibrium_aspen_grid.csv`, 84 T-P points x
{PENG-ROB, IDEAL}, pure NH3 feed, isothermal RGibbs) and the independent Python model (`amcrax.thermodynamics`).
Nothing was tuned. Reproduce with `python scripts/analyse_equilibrium_discrepancy.py` (point-by-point table:
`results/validation/equilibrium_discrepancy.csv`; summary: `equilibrium_discrepancy_summary.json`).

## 1. Where the reported 1.48 pp comes from

`scripts/validate_equilibrium.py` compares each Aspen run with **both** Python EOS options. Its largest
deviation (X_Python − X_Aspen = −1.48 pp at 250 °C / 40 bar) compares **Aspen PENG-ROB with Python ideal gas**.
That is not a like-for-like comparison. When the same physics is compared:

| Comparison (84 points, 250–900 °C, 1–40 bar) | max abs(dX), pp | where | mean abs(dX), pp |
|---|---|---|---|
| Aspen IDEAL vs Python ideal | 0.045 | 250 °C / 10 bar | 0.005 |
| Aspen PENG-ROB vs Python PR (k_ij = 0) | 0.185 | 250 °C / 40 bar | 0.023 |
| Aspen PENG-ROB vs Python ideal (mixed) | 1.476 | 250 °C / 40 bar | 0.098 |

The 1.48 pp is therefore almost entirely the **fugacity-coefficient (non-ideality) effect**. Aspen's own
PENG-ROB − IDEAL difference at that point is −1.51 pp. It is not a thermochemical-data error. The exact
decomposition is: (Aspen PR − Python PR) = (Aspen IDEAL − Python ideal) [data] + (EOS effect Aspen − EOS effect Python).

## 2. (a) Thermochemical data: equilibrium constant and reaction enthalpy

For every Aspen IDEAL point, Kp = y_N2^0.5 · y_H2^1.5 / y_NH3 · (P / 1 bar) was back-calculated and compared
with the Python K(T) (GRI-Mech 3.0 NASA-7 polynomials via Cantera). The comparison is expressed as an
equivalent Gibbs-energy offset ΔG = −RT·Δln K (`results/figures/validation_lnK_offset.png`):

* **Aspen PURE41 ideal-gas data − Python**: ΔG runs from −10.3 J/mol (250 °C) through 0 (≈ 420 °C) to
  +11.6 J/mol (900 °C). The mean is +1.3 J/mol. It is a smooth function of T and independent of P: the spread
  over 1–40 bar at a fixed T is below 0.001 J/mol. This shows that the offset is a property of the standard-state data,
  not of the solver. In ln K this is at most 2.4 × 10⁻³ (250 °C).
* **NIST-JANAF − Python**: −9.7 to −14.9 J/mol (mean −12.0 J/mol).
* **Aspen − NIST-JANAF**: +4.6 to +23.7 J/mol (mean +13.3 J/mol, 75 resolved points).
* **Which is closer to JANAF?** The mean abs(ΔG) vs JANAF is 13.3 J/mol for Aspen and 12.0 J/mol for Python,
  so the two are practically equally close. Aspen is closer below ≈ 400 °C (4.6 vs 14.9 J/mol at 250 °C).
  Python is closer above ≈ 450 °C (12.0 vs 23.7 J/mol at 900 °C). All three data sets agree within 25 J/mol,
  about 0.15 % of ΔG°(298 K) = 16.4 kJ/mol.
* **Reaction enthalpy.** Aspen IDEAL duty / conversion (= ΔH_r(T) for an isothermal ideal-gas RGibbs with feed at T)
  is compared with Python ΔH_r(T). In the regenerated grid the difference lies between −0.050 and −0.001 kJ/mol
  (median −0.031 kJ/mol). Mean abs(ΔH) vs JANAF is 0.011 kJ/mol for Aspen and 0.018 kJ/mol for Python.
  ΔH_r(298 K) = 45.899 kJ/mol (Python), and JANAF gives 45.898 kJ/mol.
* **Former Aspen duty anomaly (resolved).** The first grid had one IDEAL point (600 °C, 30 bar) with a duty that
  was 1.24 kJ/mol off. The cause was a defect in the automation, not in Aspen's thermodynamics. Section 6 gives the details.

**(c) Why low T / high P magnifies small data differences.** For pure NH3 feed and an ideal gas,
ln K = ln(0.5^0.5·1.5^1.5) + 2 ln X − ln(1 − X²) + ln P, so **dX/d ln K = X(1 − X²)/2**. This sensitivity is 0.19
at 250 °C / 10 bar (X = 0.54) and 1.4 × 10⁻⁴ at 900 °C / 1 bar (X ≈ 0.9997). The ideal-gas conversion difference
between Aspen and Python is **equivalent to a standard-Gibbs-energy offset of at most 11.6 J/mol NH3** (75 resolved
points with X < 0.999; `dG_offset_max_abs_resolved_J_mol` in the summary JSON), magnified where conversion is far
from 1: the same offset shifts X by 0.045 pp at 250 °C / 10 bar and by less than 0.001 pp above 600 °C.

This is a restatement, not an explanation. The Δln K is back-calculated from Aspen's own equilibrium composition,
so (dX/d ln K)·Δln K reproduces Aspen's conversion by construction; the remaining 1.7 × 10⁻⁵ pp is only the
second-order term of the linearisation. The matrix item `EQ-AMPLIFY` is therefore **informational**. What the
offset itself means physically (a difference of the standard-state data, P-independent to < 0.001 J/mol) is judged
by `EQ-DG-ASPEN` and `EQ-DG-JANAF`. See `results/figures/validation_parity_by_method.png`, panel (b).

## 3. (b) Equation of state: fugacity coefficients

`results/figures/validation_eos_effect.png` compares the EOS effect, X(PR) − X(ideal), in each code:

| 250 °C / 40 bar | EOS effect, pp |
|---|---|
| Aspen PENG-ROB − IDEAL | −1.509 |
| Python PR − ideal (standard α, k_ij = 0) | −1.291 |
| Python PR − ideal (Boston–Mathias α above Tc, k_ij = 0) | −1.332 |

* Both codes predict the same sign and trend. Non-ideality lowers conversion because φ_NH3 < 1 at high P and
  low T. The effect grows with P and falls with T, and it is below 0.05 pp above 600 °C at 40 bar.
* In Aspen the effect is about 17 % stronger: 0.218 pp more at the worst point. Switching Python to the
  Boston–Mathias α-function, which Aspen applies to supercritical components, explains 0.04 pp of this.
  **0.18 pp remains unexplained.** Aspen reports "BINARY PARAMETERS PRKBV … RETRIEVED FROM EOS DATABANK EOS-LIT"
  (see the baseline run messages), while Python uses k_ij = 0 for all pairs; differences in critical constants or
  acentric factors (Python uses CoolProp; Aspen uses PURE41) may also contribute. An export of the Binary
  Interaction forms was attempted (`results/validation/aspen_binary_parameters.json`, see section 6), but the PRKBV-1
  input form holds no user values. No k_ij values were invented.
* **k_ij sensitivity (not a calibration; used nowhere).** With the repaired `kij` argument (section 7) the
  PR-vs-PR gap at 250 °C / 40 bar (Aspen − Python = −0.185 pp) was recomputed with one Python k_ij at a time
  (`kij_sensitivity_250C_40bar` in `equilibrium_discrepancy_summary.json`; matrix item `EQ-KIJ-SENS`). The range
  ±0.3 is **illustrative**: `research/` holds no sourced PR k_ij for NH3–H2 or NH3–N2. A positive k_ij lowers the
  Python conversion, but weakly: −0.0146 pp per 0.1 for NH3–H2, −0.0068 pp for NH3–N2 and −0.0056 pp for H2–N2. The
  k_ij that would be needed to close the gap is **+1.26 (NH3–H2)** or **+2.69 (NH3–N2)**, and no value in [−2, 3]
  closes it for H2–N2. All three pairs at +0.3 together close 0.081 pp. Values of this size are far outside any
  physical range, so **binary parameters alone are an unlikely explanation** of the remaining 0.18 pp; the pure-
  component constants and Aspen's α treatment of the supercritical components are the more plausible candidates.
  This is still not verified.

## 4. Flowsheet cross-check (Aspen baseline vs `run_python_case` with identical inputs)

File: `results/validation/aspen_vs_python_flowsheet.csv` (every stream and block quantity, Python eos ideal and pr).

Numbers after the 2026-11-21 corrections of the Python model (section 7: shared KPI definitions, real-gas FEHE
basis). The FEHE cold side is now on one real-gas basis in both eos modes, so the FEHE duty is the same for
eos = ideal and eos = pr.

| Quantity (baseline) | Aspen (PENG-ROB) | Python eos = ideal | Python eos = pr |
|---|---|---|---|
| NH3 conversion | 0.98081 | 0.98086 (+0.005 pp) | 0.98074 (−0.007 pp) |
| CRACKER duty, kW | 1480.0 | 1474.2 (−0.39 %) | 1479.3 (−0.04 %) |
| VAPORIZR outlet T, °C | 75.90 | 70.09 (−5.8 K) | 70.09 (−5.8 K) |
| VAPORIZR duty, kW | 739.5 | 713.6 (−3.49 %) | 713.6 (−3.49 %) |
| FEHE duty (recovered heat), kW | 612.2 | 633.0 (+3.40 %; was 637.2) | 633.0 (+3.40 %; was 632.3) |
| HEATER (trim) duty, kW | 73.66 | 77.09 (+4.66 %) | 72.92 (−1.01 %) |
| COOLER duty, kW | −305.0 | −282.1 (−7.49 %, magnitude) | −284.9 (−6.58 %) |
| HEATER duty, no-HI case, kW | 685.9 | 710.1 (+3.54 %) | 706.0 (+2.93 %) |
| PSA duty, kW | 0.726 | ≈ 0 | 1.40 (PR residual of the split streams) |

In eos = ideal the trim heater carries the difference between the real-gas basis of its inlet and the ideal-gas
basis of its outlet S4 (+3.6 kW at the baseline, block detail `s4_basis_minus_reference_real_gas_kW`); in eos = pr
this difference is −0.6 kW.

**Feed section: different property models, quantified at identical states.** The two models use different
property models in the feed section. Aspen uses PENG-ROB for the liquid, the vaporisation and the NH3–H2O dew
point. The Python model uses the reference equation of state for ammonia (CoolProp, Gao et al. 2020) and an
ideal-liquid (Raoult) dew point. The numbers below are recomputed by `scripts/build_validation_matrix.py`
(`results/validation/feed_section_analysis.json`, matrix item `FEEDSEC-ANALYSIS`):

* At identical states (Aspen's S1 and S2) the Aspen vaporiser duty is **2.4 % above** the reference EOS:
  739.46 vs 721.8 kW.
* The residual enthalpy of NH3 vapour at S2 (75.9 °C, 20.8 bar) is −1.017 kJ/mol with PR (k_ij = 0) and
  −1.436 kJ/mol with the reference EOS. The reference EOS is the more accurate model for pure-ammonia enthalpy.
* The vaporiser outlet temperature is set by the 0.2 mol% water and by the VLE model. Dew point at 20.8 bar:
  pure-NH3 saturation 50.9 °C; PR with k_ij = 0 52.7 °C; Raoult 60.1 °C; PR with k_ij(NH3–H2O) = −0.25
  65.1 °C; Aspen 65.9 °C (S2 − 10 K superheat). No reference NH3–H2O mixture model was available to arbitrate,
  so neither dew point can be called right.
* Of the 20.8 kW baseline FEHE gap (Python 633.0, Aspen 612.2 kW): **8.7 kW** come from the inlet temperature
  (the dew-point difference), **11.6 kW** from the PR vs reference residual enthalpy at S2, **0.7 kW** from the
  residual at S3 (reference EOS −0.151, PR −0.178 kJ/mol) and **−0.2 kW** remain (ideal-gas cp sources, PR
  constants). Before the correction the Python eos = ideal value carried another 4.2 kW from its ideal-gas S3
  (637.2 kW). NASA-7 + PR (k_ij = 0) evaluated between Aspen's own S2 and S3 states gives 612.0 kW against Aspen's
  612.2 kW, so the Aspen FEHE duty itself is reproduced once the same states and property model are used.

The FS items therefore measure a **model-form difference in both directions**: the Python model is closer to the
reference EOS for the ammonia enthalpy, while the dew point depends on a VLE model that neither side has validated.
The colder Python vaporiser outlet lowers the vaporiser duty (−3.5 %), lets the FEHE recover more heat (+3.4 %) and
leaves the effluent colder, so the cooler removes less heat (−6.6 % with eos = pr). Nothing was tuned. All 20
`FS-<case>` items (baseline, baseline_no_hi, 8 scenarios, 10 optimisation candidates) keep the stated 2 %
tolerance on key KPIs and **fail**; they are reported as such.

**`FS-PRIMARY-<case>` (restructured 2026-11-21).** This family compares Aspen PENG-ROB with Python eos = pr on the
**independent** reaction-section quantities only: NH3 conversion and the cracked-gas mole fractions (0.5 pp
absolute, = EQ-PR) and the reactor duty (1 % relative). H2 purity, H2 product flow, overall yield, tail-gas flow
and LHV and flame temperature are functions of the conversion and of the fixed PSA split fractions, which are
inputs; they are listed in the item text as "derived, not independent" and are not judged. In particular the H2
purity is set by the assumed PSA split, it is not predicted (a 0.5 pp purity tolerance would be 13 times the
total impurity of 0.039 mol%). All 20 items pass; the largest normalised deviation is 0.118 (scn_high_pressure:
reactor duty −0.118 %). This family does not replace `FS-<case>`.

## 5. What remains unexplained

1. 0.18 pp of the Aspen vs Python PR conversion difference at 250 °C / 40 bar (0.03 pp at 600 °C / 40 bar).
   The PRKBV k_ij values cannot be read from the Aspen input forms (section 6), and the k_ij sensitivity
   (section 3) shows that single-pair values within ±0.3 close at most 0.044 pp of it; pure-component constants
   and the α treatment are the remaining candidates. Not verified.
2. The origin of the 10–25 J/mol spread between PURE41, GRI-Mech and JANAF standard-state data. Its effect on
   conversion is at most 0.045 pp, and AmCraX does not try to resolve it.
3. Which NH3–H2O dew point is right at 20.8 bar (Raoult 60.1 °C, Aspen 65.9 °C, PR 52.7–65.1 °C depending on
   k_ij). No reference mixture model or measurement was available (section 4).

The −1.24 kJ/mol duty anomaly from earlier versions of this note is no longer on this list. It was explained and
fixed (section 6).

## 6. Update 2026-11-21: stale-duty defect fixed; binary parameters not readable

**(a) EQ-DH-ASPEN root cause and fix.** The point at 600 °C / 30 bar carried the heat duty of the previous grid point.
The automation started the engine asynchronously (`Engine.Run2(1)` followed by polling `IsRunning`). In the sweep
without re-initialisation, it then read the block duty while Aspen was still loading results into the variable tree.
The fix was made at the source:

* `backend/amcrax/aspen/session.py` now runs synchronously (`Run2()`).
* The equilibrium grid is re-initialised at every point.
* `aspen/automation/run_equilibrium_grid.py` has two guards. A repeatability check requires independent sessions to
  give identical values. A physical stale-value check requires duty/X not to depend on pressure, as it must for an
  ideal gas.

The grid `results/validation/equilibrium_aspen_grid.csv` was regenerated with 168 rows (84 per method). On the stored
grid, the matrix item `EQ-GRID-STALE` recomputes the pressure spread of duty/X at fixed T as 3.2 × 10⁻⁷ kJ/mol
(tolerance 1 × 10⁻³). `EQ-DH-ASPEN` now passes: max 0.050 kJ/mol at 250 °C / 40 bar, with no anomalous points. The
re-run did not change the conversions, K offsets or EOS-effect numbers above. Flowsheet runs were never affected,
because they always re-initialise. Their mass, element and energy closures (largest 4.5 × 10⁻⁹ over 20 Aspen cases)
confirm that the extracted streams and duties are consistently mapped, converted and signed; they test the
extraction and bookkeeping, not the physics (Aspen closes its own balances). The defect was found by the validation
itself, because an ideal-gas duty that depended on pressure is physically impossible.

**(b) Aspen PR binary parameters.** `results/validation/aspen_binary_parameters.json` is a raw dump of the Binary
Interaction forms. The PRKBV-1 input form contains labels (kaij, kbij, kcij, Tlower, Tupper) but no values. Aspen
retrieves the EOS-LIT k_ij at run time and does not expose them in the Input nodes. The k_ij hypothesis for the
remaining ≈ 0.18 pp PENG-ROB gap therefore stays **unverified**, and the sensitivity of section 3 makes it unlikely.
`EQ-PR` passes its 0.5 pp tolerance (max 0.185 pp).

## 7. Update 2026-11-21 (independent review): corrections and new independent checks

**(a) Peng-Robinson `kij` argument.** The argument was unusable: species with zero mole fraction were dropped before
the k_ij matrix was applied (a 3 × 3 matrix crashed `solve_equilibrium(..., {"NH3": 1}, eos="pr", kij=...)` with a
shape error), the species order came from iterating a Python `set` (it depended on `PYTHONHASHSEED`; two stored
equilibrium values differed in the last bit between seeds), and the infinite-dilution branch ignored k_ij. Now
`kij` is `None` or a mapping keyed by species pairs (order-insensitive), arrays are assembled in the fixed
`schemas.COMPONENTS` order, the k_ij matrix spans all species including zero-fraction ones, and (1 − k_ij) is applied
at infinite dilution. With `kij = None` every stored fugacity coefficient, departure enthalpy, equilibrium and
flowsheet result is bit-for-bit identical to the previous code run with hash seed 0. Verification
(`tests/test_thermodynamics.py`): CoolProp's PR backend with k_ij set through `set_binary_interaction_double`
(AmCraX constants replaced by CoolProp's; agreement of ln φ to 5 × 10⁻⁶, the k_ij-induced shift to 0.2 %), a hand
calculation for an NH3–H2 binary (10⁻¹³), symmetry and the k_ij = 0 limit (bit-for-bit). A PR dew-point routine
was added for the feed-section comparison of section 4 (validation use only).

**(b) Shared KPI definitions.** `run_python_case` computed its own KPIs and differed from `amcrax.kpis` when the
flame temperature is below the stack temperature (900 °C / 3 bar / H2 recovery 1.0: flame 49.1 °C; combustion heat
−41.2 kW instead of 0 and external heating 2327.0 kW instead of 2368.3 kW). The Python engine now calls
`compute_kpis` / `compute_balances`. For the baseline the KPIs are identical to the former definition (regression
test).

**(c) Real-gas FEHE basis.** The Python FEHE balance took S3 on the gas-section basis of the selected eos, i.e. ideal
gas for eos = ideal, against a real-gas S2. At 60–80 bar this rejected feasible specifications (420 °C / 80 bar /
10 K: "−19.23 K cross"; 450 °C / 60 bar / 5 K: 0.48 K instead of 5.00 K). The cold side is now NASA-7 ideal gas +
reference-EOS NH3 residual enthalpy in both modes (NASA-7 rather than CoolProp's own ideal-gas part, because NASA-7
is within 0.012 kJ/mol of NIST-JANAF for NH3 at 500–900 K and CoolProp's ideal-gas part is up to 0.09 kJ/mol below
it). The hot side uses NASA-7 + PR for the temperatures in both modes: an ideal-gas hot side mis-placed T6 by up to
7 K at 100 bar, which is not negligible. Results: 420 °C / 80 bar / 10 K is feasible with a 4.8 K (eos = pr) or 5.4 K
(eos = ideal) minimum at the cold end, 450 °C / 60 bar / 5 K is limited by the 5.00 K hot-end approach, and the
baseline FEHE duty is 633.0 kW in both modes (was 637.2 ideal, 632.3 pr). An independent fine-grid profile on the same
property basis agrees within 0.06 K. The reviewer's reference with CoolProp's full ammonia enthalpy on the cold side
gives 6.3 K at 420 °C / 80 bar; of the 1.5 K difference, 0.9 K is the ideal-gas cp source and 0.5 K comes from
evaluating the cold inlet at the outlet pressure P3 instead of the S2 pressure (tests in `tests/test_process_model.py`).

**(d) Classification.** `EQ-AMPLIFY` (circular, see section 2c) and `THERMO-VANTHOFF` (code self-consistency: the
Gibbs–Helmholtz relation holds exactly for NASA-7 polynomials) are now informational. The balance items `BAL-ASPEN`,
`BAL-PY` and `SENS` are described as extraction-consistency checks; the energy closure of `BAL-PY` is zero by
construction and is informational.

**(e) New independent-physics items** (`results/validation/independent_physics_checks.csv`, 20 stored Aspen cases):

| Item | Recalculation | Worst deviation | Tolerance (assumption) |
|---|---|---|---|
| `PHYS-FLAME` | adiabatic complete-combustion T of the Aspen TAILGAS + AIR, Cantera (GRI-Mech 3.0) | 0.58 K (scn_low_recovery); baseline 1368.80 vs 1368.90 °C | 2 K |
| `PHYS-FLAME-DISSOC` | Cantera HP equilibrium with dissociation (OH, H, O, NO ...) | −2.25 K at the baseline, −0.04 to −6.33 K | informational |
| `PHYS-FLUEHX` | n (h(T_stack) − h(T_flue)) of the Aspen flue gas, Cantera | 3.5 × 10⁻⁴ relative | 0.5 % |
| `PHYS-PUMP` | n v_L ΔP / 0.75 with CoolProp liquid NH3 volume | +0.29 % (baseline 1.851 vs 1.845 kW) | 1 % |
| `PHYS-FEHE-UA` | Aspen UA vs Q / LMTD from the four terminal temperatures | 4 × 10⁻⁹ (Aspen's cal = 4.1868 J) | 10⁻⁴ |

The flame temperatures of the matrix and the models are complete-combustion values (as the Aspen RStoic burner);
with dissociation the baseline flame is 2.3 K lower. The UA item checks the consistency of the Aspen HeatX
shortcut output, not heat transfer.

**(f) Note on the GRI-Mech N2 entropy.** The GRI-Mech 3.0 N2 entropy is 0.071–0.098 J/(mol K) below the NIST-JANAF
1-bar values over 298–1200 K (checked against `thermodynamics/reference/janaf.json`; the review quoted 0.08–0.10).
Alone, this raises the reaction Gibbs energy by 0.5 (G_GRI − G_JANAF)(N2) = 14 J/mol at 298 K, 23 J/mol at 500 K and
44 J/mol at 1000 K, so the bound of 18 J/mol quoted in the review holds only below about 400 K. The net effect of all
species is what `EQ-DG-JANAF` measures: JANAF − Python is −9.7 to −14.9 J/mol over 250–900 °C, i.e. the N2 offset is
largely compensated by opposite offsets of the H2 and NH3 data. That net offset changes the conversion by at most
0.07 pp (250 °C / 10 bar, dX/d ln K = 0.19) and by less than 0.001 pp above 600 °C.
