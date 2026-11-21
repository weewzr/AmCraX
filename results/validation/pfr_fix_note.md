# PFR hydraulic-stop fix: effect on reported numbers

Source: python_model (amcrax.reactor). The comparison is against checkpoint e26ffc6. The outputs were regenerated with
`python scripts/run_kinetics_study.py`.

## Defects (reproduced before the fix)

1. `simulate_pfr` stopped at the terminal low-pressure event (P < 5 % of inlet). It then built the outlet from the
   last `t_eval` point before the stop. Example: `simulate_pfr('ni_takahashi_microkinetic', 100.0, n_tubes=50,
   P_in_bar=1.01325, T_in_C=500, n_points=3)` gave X = 0.0, W_reached = 0.0 kg, P = 1.01325 bar. With
   n_points=2001 the same call gave X = 0.2321 at 47.40 kg.
2. `catalyst_mass_for_conversion` evaluated its trial masses with `n_points=2`. A trial beyond the stop therefore
   read X = 0, the bracket did not close, and the function returned nan without a message. Example: the same bed with
   target 0.15 returned nan, although X = 0.169 at 30 kg. The geometric growth (1e-3 kg x 4^k) also ended at the last
   power below `W_max_kg` and did not try `W_max_kg` itself.

## Fix

* At the stop, the event state (`sol.t_events`, `sol.y_events`) is appended to the profile, and the outlet is built
  from it. The outlet has two new fields, `hydraulic_limit` (bool) and `W_requested_kg`. `W_reached_kg` is now the
  catalyst mass at the stop. Example 1 now gives X = 0.23217 at W = 47.4215 kg and P = 0.0507 bar, for every
  n_points.
* `catalyst_mass_for_conversion` evaluates a stopped trial at `W_reached_kg`. If the target is reached before the
  stop, the search refines the root below the stop. If it is not reached, the function returns nan with a reason:
  a `RuntimeWarning` by default, or a `reason` field with `return_details=True`. The last trial is clamped to
  `W_max_kg`. Example 2 now gives 25.457 kg (X = 0.15000 there).
* There are three new regression tests in `tests/test_reactor.py`.

## Changed reported numbers (old -> new)

| File | Item | Old | New |
|---|---|---|---|
| results/sensitivity/pfr_temperature_sweep.csv | T = 475 degC, ni_takahashi_microkinetic, W_99pct_eq_kg | NaN | 4968.12 kg |
| results/simulations/pfr_baseline.json | adiabatic and external Kum cases, outlet | - | new keys `W_requested_kg` (221.88 kg) and `hydraulic_limit` (false); no numerical value changed |

The new 475 degC Ni W99 point is a long bed: at 4968 kg the outlet pressure is 11.15 bar (pressure drop 8.85 bar
from 20 bar), and the hydraulic stop is at 6977 kg. The target is 99 % of X_eq at the *inlet* T and P. The pressure
drop along the bed raises the local X_eq, so this value depends on the hydraulics as well as on the kinetics.

## Unchanged

* All baseline catalyst masses in `pfr_baseline.json` are unchanged (relative difference < 1e-9). This includes 95 %
  and 99 % of equilibrium for Ni and Ru at 600 degC, and Ru (Kum, Takahashi) at 450 and 500 degC. Values: Ni 600 degC
  73.55 / 112.69 kg; Ru-Takahashi 600 degC 17.87 / 25.21 kg; Ru-Kum 600 degC 8.90 / 11.09 kg; Ru-Kum 450 degC
  199.23 / 257.59 kg; Ru-Kum 500 degC 62.99 / 80.13 kg; Ru-Takahashi 450 degC 384.78 / 566.53 kg; Ru-Takahashi
  500 degC 112.40 / 164.85 kg. The at_W99 values (dP, duty, GHSV) and all profiles are also unchanged.
* `kinetics_validation.csv`: all 40 rows are unchanged. The lab-reactor validation runs have no pressure drop, so
  no stop occurs.
* The sweep `X_at_100kg` column is unchanged: no stop occurs before 100 kg with 40 tubes at 20 bar.
* Still NaN in the sweep, now with an explicit reason: Ni at 400, 425 and 450 degC, both 95 % and 99 %. These targets
  are not reached before the hydraulic stop: at 400 degC the stop is at 12025.5 kg with X = 0.411; at 425 degC at
  9870.1 kg with X = 0.630; at 450 degC at 8139.0 kg with X = 0.844. The 475 degC Ni W95 value (3526.95 kg) was
  already finite before the fix and is unchanged.
* The figures pfr_profiles_*.png and kinetics_validation.png are byte-identical. pfr_catalyst_mass_vs_T.png changed
  only by the added 475 degC Ni point.
