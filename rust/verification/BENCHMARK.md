# Stage 3 benchmark

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
