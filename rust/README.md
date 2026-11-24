# AmCraX Rust workspace

The Rust implementation of the AmCraX numerical engine. Python stays the reference: every Rust
routine is checked against golden tables produced by the Python code, and a Python module is
retired only after its Rust port has passed its gate.

## Layout

```
rust/
  Cargo.toml                 workspace: members, shared dependencies, lints, profiles
  Cargo.lock                 committed (reproducible builds, audited in CI)
  rustfmt.toml
  crates/
    amcrax-numerics/         numerical methods, no dependencies, no I/O, no AmCraX physics
      src/roots.rs           brentq (exact port of SciPy brentq.c)
      src/ode.rs             Dormand-Prince 5(4), dense output, events (port of solve_ivp RK45)
      src/interp.rs          PCHIP (SciPy), linear (numpy.interp), bilinear (browser model)
      src/poly.rs            real roots of cubics (analytic + Newton polishing)
      src/stats.rs           sum, mean, var, std, median, quantile (NumPy, method "linear")
      src/random.rs          SeedSequence and PCG64 (NumPy)
      src/qmc.rs             Sobol' (SciPy, Joe-Kuo directions) and Latin hypercube sampling
      src/sobol_directions.rs  generated from SciPy's direction-number table (do not edit)
      tests/golden.rs        all golden-table comparisons
    amcrax-engine/           AmCraX science (stage 0: module layout, data types, units, errors)
    amcrax-cli/              binary `amcrax` (stage 0: --version, verify)
    amcrax-wasm/             wasm-bindgen facade for the browser (wasm32-unknown-unknown)
  golden/
    generate_numerics_golden.py   writes the golden tables (NumPy/SciPy only)
    numerics/*.json               golden tables, MANIFEST.json with SHA-256 and case counts
```

Dependency graph: `amcrax-cli -> amcrax-engine[yaml] -> amcrax-numerics`,
`amcrax-wasm -> amcrax-engine (no yaml) -> amcrax-numerics`.

## Dependencies

| Crate | Version | Used by | Why |
|---|---|---|---|
| serde (derive) | 1.0.229 | engine | typed data and result structures |
| serde_json (`float_roundtrip`) | 1.0.154 | engine, cli; numerics tests | JSON data, golden tables; `float_roundtrip` parses every float exactly |
| thiserror | 2.0.21 | engine | `EngineError` |
| sha2 | 0.11.1 | engine; numerics tests | SHA-256 provenance of input files and golden tables |
| serde-saphyr (`deserialize` only) | 2.2.0 | engine, feature `yaml` | YAML 1.2 into serde types (the YAML data files) |
| wasm-bindgen | 0.2.130 | wasm | JavaScript bindings |

`amcrax-numerics` has no dependencies at all: PCG64, SeedSequence, Sobol' and the solvers are
implemented in the crate (each a few dozen lines, ported from the reference so that the output is
identical). `cargo audit --deny warnings` runs in CI against the RustSec advisory database.

## Build policy

**All compilation and testing runs in GitHub Actions** (`.github/workflows/rust.yml`, Linux and
Windows runners). On development machines where endpoint protection blocks freshly compiled
executables (cargo build scripts and test binaries are such executables), do not run
`cargo build`, `cargo check`, `cargo test`, `cargo run`, `cargo clippy`, `cargo bench` or
`cargo install`, and keep rust-analyzer from building: the repository's `.vscode/settings.json`
disables build scripts, proc-macro expansion and check-on-save. These commands are safe there,
because they do not compile or run crate code: `cargo fmt`, `cargo metadata --no-deps`,
`cargo generate-lockfile`, `cargo update`, `rustc --version`.

The feedback loop is: edit, `cargo fmt`, commit, push, read the workflow result.

CI jobs: `cargo fmt --check`; `cargo clippy --all-targets --all-features -- -D warnings`;
`cargo test --workspace --profile ci` (optimised, debug assertions and overflow checks on) on
Linux and on Windows (MSVC); `cargo doc`; `amcrax --version` and `amcrax verify numerics`; the
`amcrax-wasm` build for `wasm32-unknown-unknown` with a 400 KB size budget; `cargo audit`. The
toolchain is pinned to Rust 1.100.0 (`rust-version` in `Cargo.toml`), warnings are errors.

## Building elsewhere

On a machine where compiling is allowed, with Rust 1.100 or later:

```
cd rust
cargo test --workspace --profile ci          # all tests including the golden tables
cargo run -p amcrax-cli -- verify numerics   # integrity and spot checks of the golden tables
rustup target add wasm32-unknown-unknown
cargo build -p amcrax-wasm --target wasm32-unknown-unknown --profile wasm
```

## Golden tables and tolerances

The tables in `golden/numerics/` are generated **once** by Python with
`python rust/golden/generate_numerics_golden.py` (project virtual environment; it imports only
the standard library, NumPy and SciPy) and committed. They are never regenerated from Rust.
Floats are written with `repr()` (shortest round-trip form), non-finite values as `"nan"`,
`"inf"`, `"-inf"`; `MANIFEST.json` records the library versions (NumPy 2.5.5, SciPy 1.18.1,
Python 3.12.10), the case counts and the SHA-256 of every table, and the tests check those
hashes before using a table. `.gitattributes` fixes LF line endings for `rust/**`, and disables
line-ending conversion for the Python data files, so hashes do not depend on the platform.

| Routine | Reference | Rule | Why |
|---|---|---|---|
| brentq | `scipy.optimize.brentq` | bitwise: root, iterations, calls, flag and the whole evaluation trace | exact port of `brentq.c`; transcendental test functions are replayed from the recorded trace so libm differences cannot hide an algorithm difference |
| DOPRI5 | `solve_ivp(method="RK45")` | identical RHS count and accepted steps; values at `t_eval` and event times within 0.05 x (atol + rtol abs(y)); analytic solutions within 200 x (atol + rtol max abs(y)) | same method and controller, but NumPy's BLAS dot products sum in a different order, so the error estimate (a cancelling sum) and hence the step sizes differ in the last digits |
| PCHIP | `PchipInterpolator` | bitwise values; knot derivatives within 1e-12 x max abs(d) | same operations in SciPy's order; SciPy re-evaluates derivatives through the derivative polynomial |
| linear | `numpy.interp` | bitwise | same formula and fallbacks |
| bilinear | browser model (`frontend/src/sim`) | bitwise | same expression |
| cubic roots | `numpy.roots`, real if abs(imag) < 1e-10 | same number of real roots; 1e-10 relative | different algorithm (analytic vs eigenvalues), both backward stable |
| sum, mean, var, std, median, quantile | NumPy | bitwise | port of pairwise summation and of `_quantile`/`_lerp` |
| PCG64, SeedSequence, random, uniform, shuffle | NumPy | bitwise (including 3 streams of 10^6 draws by SHA-256) | integer algorithms ported exactly |
| Sobol' unscrambled | `qmc.Sobol(scramble=False)` | bitwise, d up to 1111 | integer recurrence, exact scale |
| Sobol' scrambled (LMS + shift), LHS | `qmc.Sobol(rng=seed)`, `qmc.LatinHypercube(rng=seed)` | bitwise for the recorded versions | exact port of SciPy's scrambling and NumPy's bounded integers / shuffle |

Not promised bit-identical across library versions: normal and other non-uniform variates (not
ported), shuffles and bounded integers (NumPy does not freeze these streams), and therefore the
scrambled Sobol' and LHS designs. For those, the promise is statistical equivalence (balance and
stratification properties, tested in the unit tests).

## Stages

0. Workspace, CI, numerics (this stage).
1. Data loading, thermodynamics (NASA-7), ideal-gas and Peng-Robinson equilibrium.
2. Kinetics and the plug-flow reactor.
3. Process balance, separation, heat integration, UQ estimators.
4. Economics, carbon, LCA, end use.
5. Optimisation objectives, MCMC.
6. (optional) Python extension module.
