//! `amcrax verify numerics`: integrity of the golden tables and bit-exact spot checks of the
//! numerics against them. The full comparison (all routines, all rules) is the test suite
//! `rust/crates/amcrax-numerics/tests/golden.rs`; this command lets a user re-check a checkout
//! without building the tests.

use amcrax_engine::provenance::sha256_hex;
use amcrax_numerics::qmc::Sobol;
use amcrax_numerics::random::{Pcg64, SeedSequence};
use amcrax_numerics::roots::{BrentOptions, brentq};
use amcrax_numerics::stats;
use serde_json::Value;
use std::path::{Path, PathBuf};

/// One verification check.
#[derive(Debug, Clone, PartialEq)]
pub struct Check {
    pub name: String,
    pub ok: bool,
    pub detail: String,
}

/// Result of a verification run.
#[derive(Debug, Clone, PartialEq)]
pub struct Report {
    pub dir: PathBuf,
    pub checks: Vec<Check>,
}

impl Report {
    /// True when every check passed.
    pub fn passed(&self) -> bool {
        !self.checks.is_empty() && self.checks.iter().all(|c| c.ok)
    }

    /// Human-readable report.
    pub fn render(&self) -> String {
        let mut s = format!("golden tables: {}\n", self.dir.display());
        for c in &self.checks {
            s.push_str(&format!(
                "  [{}] {:<34} {}\n",
                if c.ok { "PASS" } else { "FAIL" },
                c.name,
                c.detail
            ));
        }
        let failed = self.checks.iter().filter(|c| !c.ok).count();
        s.push_str(&format!(
            "{} checks, {failed} failed: {}\n",
            self.checks.len(),
            if self.passed() { "PASS" } else { "FAIL" }
        ));
        s
    }
}

fn read_json(path: &Path) -> Result<(Vec<u8>, Value), String> {
    let bytes = std::fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let v = serde_json::from_slice(&bytes).map_err(|e| format!("{}: {e}", path.display()))?;
    Ok((bytes, v))
}

fn num(v: &Value) -> f64 {
    match v {
        Value::Number(n) => n.as_f64().unwrap_or(f64::NAN),
        Value::String(s) if s == "inf" => f64::INFINITY,
        Value::String(s) if s == "-inf" => f64::NEG_INFINITY,
        _ => f64::NAN,
    }
}

fn nums(v: &Value) -> Vec<f64> {
    v.as_array()
        .map(|a| a.iter().map(num).collect())
        .unwrap_or_default()
}

fn same(a: f64, b: f64) -> bool {
    a.to_bits() == b.to_bits() || (a.is_nan() && b.is_nan())
}

fn words(v: &Value) -> Vec<u32> {
    v.as_array()
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_u64())
                .map(|x| x as u32)
                .collect()
        })
        .unwrap_or_default()
}

fn check(name: &str, ok: bool, detail: String) -> Check {
    Check {
        name: name.to_string(),
        ok,
        detail,
    }
}

/// Verify the numerics golden tables in `dir`.
pub fn numerics(dir: &Path) -> Result<Report, String> {
    let (_, manifest) = read_json(&dir.join("MANIFEST.json"))?;
    let files = manifest["files"]
        .as_object()
        .ok_or("MANIFEST.json has no `files`")?;
    let mut checks = Vec::new();
    for (name, entry) in files {
        let want = entry["sha256"].as_str().unwrap_or_default();
        let got = std::fs::read(dir.join(name)).map(|b| sha256_hex(&b));
        checks.push(match got {
            Ok(h) => check(
                &format!("sha256 {name}"),
                h == want,
                if h == want {
                    "matches MANIFEST.json".into()
                } else {
                    format!("{h} != {want}")
                },
            ),
            Err(e) => check(&format!("sha256 {name}"), false, e.to_string()),
        });
    }
    if checks.iter().any(|c| !c.ok) {
        return Ok(Report {
            dir: dir.to_path_buf(),
            checks,
        });
    }

    // PCG64: default_rng(seed).random(1000)
    let (_, t) = read_json(&dir.join("pcg64.json"))?;
    let streams = t["streams"].as_array().cloned().unwrap_or_default();
    let mut bad = 0;
    for s in &streams {
        let mut g =
            Pcg64::from_seed_sequence(&SeedSequence::from_words(&words(&s["entropy_words"]), &[]));
        let want = nums(&s["random_1000"]);
        if want.is_empty() || !want.iter().all(|w| same(g.random(), *w)) {
            bad += 1;
        }
    }
    checks.push(check(
        "PCG64 random() streams",
        bad == 0 && !streams.is_empty(),
        format!("{} seeds x 1000 draws, {bad} differ", streams.len()),
    ));

    // Sobol: unscrambled points
    let (_, t) = read_json(&dir.join("sobol.json"))?;
    let cases = t["unscrambled"].as_array().cloned().unwrap_or_default();
    let mut bad = 0;
    for c in &cases {
        let d = c["d"].as_u64().unwrap_or(0) as usize;
        let m = c["m"].as_u64().unwrap_or(0) as u32;
        let pts = Sobol::new(d).and_then(|mut s| s.random_base2(m));
        let want: Vec<Vec<f64>> = c["points"]
            .as_array()
            .map(|a| a.iter().map(nums).collect())
            .unwrap_or_default();
        let ok = match pts {
            Ok(p) => {
                p.len() == want.len()
                    && p.iter().zip(&want).all(|(a, b)| {
                        a.len() == b.len() && a.iter().zip(b).all(|(x, y)| same(*x, *y))
                    })
            }
            Err(_) => false,
        };
        if !ok {
            bad += 1;
        }
    }
    checks.push(check(
        "Sobol scramble=False points",
        bad == 0 && !cases.is_empty(),
        format!("{} designs, {bad} differ", cases.len()),
    ));

    // brentq: the cubic test function
    let (_, t) = read_json(&dir.join("brentq.json"))?;
    let cases = t["cases"].as_array().cloned().unwrap_or_default();
    let mut n = 0;
    let mut bad = 0;
    for c in cases
        .iter()
        .filter(|c| c["function"] == "cubic" && c["converged"].as_bool() == Some(true))
    {
        n += 1;
        let opts = BrentOptions {
            xtol: num(&c["xtol"]),
            rtol: num(&c["rtol"]),
            maxiter: c["maxiter"].as_u64().unwrap_or(100) as u32,
        };
        let r = brentq(
            |x| x * x * x - 2.0 * x - 5.0,
            num(&c["a"]),
            num(&c["b"]),
            opts,
        );
        if !matches!(r, Ok(root) if same(root.x, num(&c["root"]))) {
            bad += 1;
        }
    }
    checks.push(check(
        "brentq roots (x^3 - 2x - 5)",
        bad == 0 && n > 0,
        format!("{n} brackets, {bad} differ"),
    ));

    // statistics: mean and quantiles
    let (_, t) = read_json(&dir.join("stats.json"))?;
    let cases = t["cases"].as_array().cloned().unwrap_or_default();
    let mut bad = 0;
    for c in &cases {
        let x = nums(&c["x"]);
        let q = stats::quantiles(&x, &nums(&c["q"]));
        let ok = same(stats::mean(&x), num(&c["mean"]))
            && q.iter()
                .zip(nums(&c["quantiles"]))
                .all(|(a, b)| same(*a, b));
        if !ok {
            bad += 1;
        }
    }
    checks.push(check(
        "mean and quantiles (NumPy)",
        bad == 0 && !cases.is_empty(),
        format!("{} vectors, {bad} differ", cases.len()),
    ));

    Ok(Report {
        dir: dir.to_path_buf(),
        checks,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn committed_golden_tables_verify() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../golden/numerics");
        let report = numerics(&dir).unwrap();
        assert!(report.passed(), "{}", report.render());
    }

    #[test]
    fn missing_directory_is_an_error() {
        assert!(numerics(Path::new("does/not/exist")).is_err());
    }
}
