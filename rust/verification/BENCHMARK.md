# Benchmarks of stages 3 and 5

Source: `benchmark_stage3.json` (GitHub Actions run 45405266952, commit a542cca, job "benchmark").
Python reference and Rust release build ran one after the other in the same job, so the hardware
is the same: Intel Xeon Platinum 8370C at 2.80 GHz, 4 vCPUs, Ubuntu (image ubuntu26
20261116.202.1), rustc 1.100.0 (release profile: opt-level 3, thin LTO, codegen-units 1,
RUSTFLAGS `-D warnings`), Python 3.12.16 with NumPy 2.5.5 and SciPy 1.18.1.

Timing is wall clock (Rust `std::time::Instant`, Python `time.perf_counter`), the median of the
repetitions: 2001 single economics evaluations, 3 batches of 100,000, 21 single reactor solves,
3 batches of 200, one run of the global sensitivity study and of the kinetic slice. Shared
runners vary from run to run, so the ratios below describe this run only.

| Item | Python (s) | Rust (s) | Python / Rust |
|---|---|---|---|
| one `evaluate` (full result dict) | 4.09e-5 | 2.69e-5 | 1.5 |
| 100,000 `evaluate` (full result dict) | 4.74 | 2.80 | 1.7 |
| 100,000 evaluations, Rust typed path (what the studies use) | 4.74 | 0.179 | 26.5 |
| one PFR solve, isothermal | 0.0625 | 0.00203 | 30.8 |
| one PFR solve, adiabatic | 0.0838 | 0.00222 | 37.7 |
| one PFR solve, external heating | 0.0814 | 0.00225 | 36.2 |
| 200 isothermal PFR solves | 12.4 | 0.372 | 33.3 |
| global sensitivity study (16 cases + dummy, N = 8192, 1000 bootstraps) | 187.8 | 30.0 | 6.3 |
| kinetic propagation slice (first 25 draws of C1 and C2 of both catalysts, 12,958 PFR solves), one thread | 250.9 | 19.4 | 12.9 |

Rust kinetic slice on more threads (identical results for every thread count): 2 threads
10.3 s (1.88 x), 4 threads 9.67 s (2.01 x; the 4 vCPUs are two hyper-threaded cores, and 25
draws per case split into small chunks).

Peak resident memory (Linux VmHWM / ru_maxrss): Python 169,704 kB, Rust 15,240 kB.

Notes: the dict-building `evaluate` is dominated by the construction of the Python-shaped JSON
result (strings, provenance stamp, notes); the typed path computes the same numbers. The full
kinetic propagation study (16,000 draws) runs in its own job ("kinetic"), whose timing is in its
report; it is not part of this comparison, which uses a fixed slice so both implementations run
on the same machine within the job time.

Full Rust kinetic propagation study (16,000 draws, 2,085,296 PFR solves of which 141,592 used the Radau fallback; job "kinetic", 4 threads, not on the benchmark runner, so not a comparison): 820.4 s on an Intel Xeon 6975P-C runner (run 45413488525) and 1332.2 s on an AMD EPYC 7763 runner (run 45405266952); figures from the kinetic-study job logs, not committed.

## Stage 5 items

Source: the `benchmark_stage3.json` artifact of GitHub Actions run 45521208605 (commit 6173ba7,
job "benchmark"); AMD EPYC 7763, 4 vCPUs, same image, toolchain and Python versions as above. The
whole set was measured again in that job (economics 1.5 / 1.7 / 29.0, PFR 30.8 to 37.8, global
sensitivity 7.1, kinetic slice 13.3); this runner is slower than the Xeon of the stage 3 run.
The raw timings are in the CI artifact 'benchmark' of that run (kept until 2027-02-23); they are
not committed to the repository.

| Item | Python (s) | Rust (s) | Python / Rust |
|---|---|---|---|
| catalyst comparison: one LCOH(T) curve (Ru Temkin-Pyzhev, 59 temperatures, heat integration; PFR mass search, kinetic flowsheet, heat accounting, economics) | 46.0 | 0.719 | 63.9 |
| optimisation objective: `evaluate_result` and the constraint values on the stored baseline result (2001 repetitions) | 2.06e-4 | 1.31e-4 | 1.6 |
| MCMC: four adaptive-Metropolis chains of 20,000 iterations on the bicubic surrogate of the main calibration grid | 5.94 | 0.180 | 33.1 |

Notes: in the catalyst curve Python takes its fluid properties from the CoolProp 8.0.0 wheel and
Rust from the recorded tables back end (CoolProp itself is not linked in the benchmark job), so
part of the ratio is the cost of CoolProp calls; the verified agreement of the two back ends is
in `stage5_report.json`. The objective item excludes the flowsheet solve, which dominates one
optimiser evaluation in both implementations; like the dict-building `evaluate`, it is dominated
by building the result dict.

## Stage 5, second part

Source: run 45537898469 (commit 2fc58cc, job "benchmark"), Intel Xeon Platinum 8370C, 4 vCPUs.
The raw timings are in the CI artifact 'benchmark' of that run (kept until 2027-02-23); they are
not committed to the repository.

| Item | Python (s) | Rust (s) | Python / Rust |
|---|---|---|---|
| catalyst economics: cost-optimal designs of the five catalysts (exchanger mode, central prices, 2 yr, fresh caches: 5 K grid refined on 1 K, PFR mass searches, kinetic flowsheets, FEHE sizing, economics) | 111.4 | 2.98 | 37.4 |
| catalyst comparison LCOH(T) curve (as above) | 40.2 | 0.659 | 61.0 |
| MCMC, 4 x 20,000 iterations | 4.90 | 0.165 | 29.7 |
| optimisation objective | 1.73e-4 | 1.22e-4 | 1.4 |

As for the catalyst curve, Python takes its properties from the CoolProp wheel and Rust from the
tables back end. The end-use studies are not timed: the Python drivers draw their figures in the
same functions, so no like-for-like Python time exists.