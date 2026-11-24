//! Stage 1 checks: data loading parity and thermodynamics (golden tables in `rust/golden/stage1`).

use super::{Acc, Golden, Report, add_species, error_matches, num, py_error, species_map};
#[cfg(feature = "yaml")]
use crate::data::DataRoot;
use crate::error::EngineError;
use crate::props::Phase;
use crate::species::{Comp, Species};
use crate::thermo::equilibrium::{self as eq, Eos};
use crate::thermo::nasa7::{self, Nasa7};
use crate::thermo::peng_robinson::{self as pr, Alpha, Kij};
use serde_json::Value;

fn kij_of(v: &Value) -> Result<Kij, EngineError> {
    let mut pairs = Vec::new();
    for p in v.as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let a = Species::from_name(p[0].as_str().unwrap_or(""))
            .ok_or_else(|| EngineError::data("golden", "kij species"))?;
        let b = Species::from_name(p[1].as_str().unwrap_or(""))
            .ok_or_else(|| EngineError::data("golden", "kij species"))?;
        pairs.push((a, b, num(&p[2])));
    }
    Kij::from_pairs(&pairs)
}

fn comp_of(v: &Value) -> Result<Comp, EngineError> {
    let mut c = [0.0; 5];
    for (s, x) in species_map(v)? {
        c[s.index()] = x;
    }
    Ok(c)
}

fn alpha_of(v: &Value) -> Alpha {
    Alpha::from_python(v.as_str().unwrap_or("standard"))
}

/// Record an expected-error case: Python raised `py`, Rust returned `r`.
fn add_error_case<T>(acc: &mut Acc, case: &str, py: &str, r: &Result<T, EngineError>) {
    let ok = matches!(r, Err(e) if error_matches(py, e));
    acc.add_bool(case, ok, || match r {
        Ok(_) => format!("python raised {py}, rust returned a value"),
        Err(e) => format!("python raised {py}, rust error {e}"),
    });
}

// ------------------------------------------------------------------------------------- data files

/// Python `str()` of a scalar YAML value (strings, integers, booleans, floats with repr form).
#[cfg(feature = "yaml")]
fn py_str(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Bool(true) => "True".to_string(),
        Value::Bool(false) => "False".to_string(),
        Value::Null => "None".to_string(),
        Value::Number(n) => {
            if n.is_f64() {
                let f = n.as_f64().unwrap_or(f64::NAN);
                if f.fract() == 0.0 && f.abs() < 1e16 {
                    format!("{f:.1}")
                } else {
                    format!("{f}")
                }
            } else {
                n.to_string()
            }
        }
        other => other.to_string(),
    }
}

/// Differences between two JSON value trees: `(path, python, rust)`.
#[cfg(feature = "yaml")]
fn tree_diff(
    path: &mut Vec<String>,
    py: &Value,
    rs: &Value,
    out: &mut Vec<(String, String, String)>,
) {
    let here = |p: &Vec<String>| format!("/{}", p.join("/"));
    match (py, rs) {
        (Value::Object(a), Value::Object(b)) => {
            for (k, va) in a {
                path.push(k.clone());
                match b.get(k) {
                    Some(vb) => tree_diff(path, va, vb, out),
                    None => out.push((here(path), va.to_string(), "<missing>".into())),
                }
                path.pop();
            }
            for k in b.keys() {
                if !a.contains_key(k) {
                    path.push(k.clone());
                    out.push((here(path), "<missing>".into(), b[k].to_string()));
                    path.pop();
                }
            }
        }
        (Value::Array(a), Value::Array(b)) => {
            if a.len() != b.len() {
                out.push((
                    here(path),
                    format!("array of {}", a.len()),
                    format!("array of {}", b.len()),
                ));
                return;
            }
            for (i, (va, vb)) in a.iter().zip(b).enumerate() {
                path.push(i.to_string());
                tree_diff(path, va, vb, out);
                path.pop();
            }
        }
        (Value::Number(a), Value::Number(b)) => {
            let ai = a.is_i64() || a.is_u64();
            let bi = b.is_i64() || b.is_u64();
            let same = if ai && bi {
                (a.as_i64(), a.as_u64()) == (b.as_i64(), b.as_u64())
            } else if !ai && !bi {
                let (x, y) = (
                    a.as_f64().unwrap_or(f64::NAN),
                    b.as_f64().unwrap_or(f64::NAN),
                );
                x.to_bits() == y.to_bits()
            } else {
                false
            };
            if !same {
                let t = |n: &serde_json::Number, i: bool| {
                    format!("{} {}", if i { "int" } else { "float" }, n)
                };
                out.push((here(path), t(a, ai), t(b, bi)));
            }
        }
        (a, b) => {
            if a != b {
                out.push((here(path), a.to_string(), b.to_string()));
            }
        }
    }
}

/// Data loading parity: SHA-256 of every data file, Rust parse versus Python parse, YAML 1.1/1.2
/// differences, reference-scenario provenance stamp.
#[cfg(feature = "yaml")]
pub fn data(root: &DataRoot, golden: &Golden) -> Result<Report, EngineError> {
    let mut rep = Report::new("data");
    let t = golden.load("data_files.json")?;
    let mut sha = Acc::exact(
        "data.raw_sha256",
        "SHA-256 of the raw bytes of each data file",
    );
    let mut vals = Acc::exact(
        "data.parsed_values",
        "every leaf value of the parsed file (type and value; floats bitwise)",
    )
    .note(
        "Rust: serde_json (JSON) and serde-saphyr (YAML 1.2); Python: json.loads and PyYAML safe_load \
         (YAML 1.1); paths listed as YAML 1.1/1.2 differences are compared with the YAML 1.2 core value",
    );
    let mut documented = Acc::exact(
        "data.yaml11_vs_yaml12_documented",
        "documented YAML 1.1 (PyYAML) versus 1.2 (core schema) differences reproduced by the Rust parser",
    );
    for f in t["files"].as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let rel = f["file"].as_str().unwrap_or("");
        let raw = root.read(rel)?;
        let want = f["raw_sha256"].as_str().unwrap_or("");
        sha.add_bool(rel, raw.sha256 == want, || {
            format!("rust {} python {want}", raw.sha256)
        });
        let rust_v: Value = if rel.ends_with(".yaml") {
            raw.parse_yaml()?
        } else {
            raw.parse_json()?
        };
        let py_v = golden.load(f["canonical"].as_str().unwrap_or(""))?;
        let mut diffs = Vec::new();
        tree_diff(&mut Vec::new(), &py_v, &rust_v, &mut diffs);
        let expected: Vec<(String, Value)> = f["yaml11_vs_yaml12_differences"]
            .as_array()
            .map(Vec::as_slice)
            .unwrap_or(&[])
            .iter()
            .map(|d| {
                let p: Vec<String> = d["path"]
                    .as_array()
                    .map(Vec::as_slice)
                    .unwrap_or(&[])
                    .iter()
                    .map(|x| match x {
                        Value::String(s) => s.clone(),
                        other => other.to_string(),
                    })
                    .collect();
                (format!("/{}", p.join("/")), d["yaml12_core_value"].clone())
            })
            .collect();
        let n_leaves = count_leaves(&py_v);
        let unexpected: Vec<&(String, String, String)> = diffs
            .iter()
            .filter(|d| !expected.iter().any(|e| e.0 == d.0))
            .collect();
        vals.add_bool(
            &format!("{rel} ({n_leaves} values)"),
            unexpected.is_empty(),
            || {
                format!(
                    "{} unexpected difference(s), first: {:?}",
                    unexpected.len(),
                    unexpected.first()
                )
            },
        );
        for (path, core) in &expected {
            let rv = pointer(&rust_v, path);
            let ok = match (rv, core) {
                (Some(Value::Number(a)), Value::Number(b)) => {
                    a.as_f64().map(f64::to_bits) == b.as_f64().map(f64::to_bits)
                }
                (Some(a), b) => a == b,
                (None, _) => false,
            };
            documented.add_bool(&format!("{rel}{path}"), ok, || {
                format!("rust {rv:?}, YAML 1.2 core value {core}")
            });
            rep.findings.push(format!(
                "YAML parsers disagree in {rel} at {path}: PyYAML (YAML 1.1) reads a string, the \
                 YAML 1.2 core schema (Rust) reads {core}; rust value {}",
                rv.map(|v| v.to_string())
                    .unwrap_or_else(|| "<missing>".into())
            ));
        }
    }
    rep.push(sha);
    rep.push(vals);
    rep.push(documented);

    // provenance stamp of the reference scenario (Python economics.reference.provenance_stamp)
    let stamp = &t["reference_scenario_provenance_stamp"];
    let rel = stamp["file"].as_str().unwrap_or("");
    let raw = root.read(rel)?;
    let d: Value = raw.parse_yaml()?;
    let mut st = Acc::exact(
        "data.reference_scenario_stamp",
        "provenance stamp of reference_scenario.yaml (file, sha256, version, id, fx, fx date, CAPEX method)",
    );
    let fields = [
        ("sha256", Value::String(raw.sha256.clone())),
        ("version", Value::String(py_str(&d["version"]))),
        ("id", d["id"].clone()),
        (
            "fx_SGD_per_USD",
            d["currency"]["fx_SGD_per_USD"]["value"].clone(),
        ),
        (
            "fx_date",
            Value::String(py_str(&d["currency"]["fx_SGD_per_USD"]["date"])),
        ),
        (
            "capex_method",
            Value::String(py_str(&d["capex"]["method"]["value"])),
        ),
    ];
    for (k, v) in fields {
        let want = &stamp[k];
        let ok = match (&v, want) {
            (Value::Number(a), Value::Number(b)) => {
                a.as_f64().map(f64::to_bits) == b.as_f64().map(f64::to_bits)
            }
            (a, b) => a == b,
        };
        st.add_bool(k, ok, || format!("rust {v} python {want}"));
    }
    rep.push(st);
    Ok(rep)
}

#[cfg(feature = "yaml")]
fn count_leaves(v: &Value) -> usize {
    match v {
        Value::Object(m) => m.values().map(count_leaves).sum(),
        Value::Array(a) => a.iter().map(count_leaves).sum(),
        _ => 1,
    }
}

#[cfg(feature = "yaml")]
fn pointer<'a>(v: &'a Value, path: &str) -> Option<&'a Value> {
    let mut cur = v;
    for part in path.trim_start_matches('/').split('/') {
        cur = match cur {
            Value::Object(m) => m.get(part)?,
            Value::Array(a) => a.get(part.parse::<usize>().ok()?)?,
            _ => return None,
        };
    }
    Some(cur)
}

// ------------------------------------------------------------------------------------- thermo

const GATE_NASA: f64 = 1e-12;
const GATE_PR: f64 = 1e-10;
const GATE_X: f64 = 1e-10;

/// Thermodynamics: NASA-7, reaction properties, ideal and Peng-Robinson equilibrium, PR
/// properties and root classification, dew points and saturation temperatures.
pub fn thermo(golden: &Golden) -> Result<Report, EngineError> {
    let mut rep = Report::new("thermo");
    let sha_embedded = Nasa7::embedded().sha256.clone();
    rep.findings.push(format!(
        "embedded nasa7.json SHA-256 {sha_embedded}; critical_properties.json SHA-256 {}",
        pr::CriticalProperties::embedded().sha256
    ));
    nasa7_checks(golden, &mut rep)?;
    equilibrium_checks(golden, "equilibrium_ideal.json", "eq_ideal", &mut rep)?;
    pr_checks(golden, &mut rep)?;
    dew_checks(golden, &mut rep)?;
    equilibrium_checks(golden, "equilibrium_pr.json", "eq_pr", &mut rep)?;
    enthalpy_checks(golden, &mut rep)?;
    Ok(rep)
}

fn nasa7_checks(golden: &Golden, rep: &mut Report) -> Result<(), EngineError> {
    let t = golden.load("nasa7.json")?;
    let d = Nasa7::embedded();
    let note =
        "relative to max(|python|, sum of |polynomial terms|): the condition scale of the sum";
    let mut cp = Acc::rel("nasa7.cp", "cp, cp/R per species", GATE_NASA).note(note);
    let mut h = Acc::rel("nasa7.h", "h, h/RT per species", GATE_NASA).note(note);
    let mut s = Acc::rel("nasa7.s", "s, s/R per species", GATE_NASA).note(note);
    let mut g = Acc::rel("nasa7.g", "g = h - T s per species", GATE_NASA).note(note);
    let mut errs = Acc::exact("nasa7.range_errors", "temperature outside the NASA-7 range");
    for c in t["species_cases"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[])
    {
        let sp = Species::from_name(c["species"].as_str().unwrap_or(""))
            .ok_or_else(|| EngineError::data("nasa7.json", "species"))?;
        let tk = num(&c["T_K"]);
        let case = format!("{} T={tk}", sp.name());
        if let Some(e) = c.get("result").and_then(py_error) {
            add_error_case(&mut errs, &case, e, &d.cp_j_mol_k(sp, tk));
            continue;
        }
        let (scp, sh, ss) = d.term_scales(sp, tk)?;
        let r = nasa7::R_J_MOL_K;
        cp.add_scaled(&case, d.cp_j_mol_k(sp, tk)?, num(&c["cp_J_molK"]), scp);
        cp.add_scaled(&case, d.cp_r(sp, tk)?, num(&c["cp_R"]), scp / r);
        h.add_scaled(&case, d.enthalpy_kj_mol(sp, tk)?, num(&c["h_kJ_mol"]), sh);
        h.add_scaled(
            &case,
            d.h_rt(sp, tk)?,
            num(&c["h_RT"]),
            sh * 1000.0 / (r * tk),
        );
        s.add_scaled(&case, d.entropy_j_mol_k(sp, tk)?, num(&c["s_J_molK"]), ss);
        s.add_scaled(&case, d.s_r(sp, tk)?, num(&c["s_R"]), ss / r);
        g.add_scaled(
            &case,
            d.gibbs_kj_mol(sp, tk)?,
            num(&c["g_kJ_mol"]),
            sh + tk * ss / 1000.0,
        );
    }
    let mut dh = Acc::rel("reaction.dH", "standard reaction enthalpy", GATE_NASA).note(note);
    let mut dg = Acc::rel("reaction.dG", "standard reaction Gibbs energy", GATE_NASA).note(note);
    let mut ds = Acc::rel("reaction.dS", "standard reaction entropy", GATE_NASA).note(note);
    let mut kp = Acc::rel("reaction.Kp", "equilibrium constant Kp (1 bar)", GATE_NASA);
    for c in t["reaction_cases"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[])
    {
        let tk = num(&c["T_K"]);
        let case = format!("T={tk}");
        if let Some(e) = c.get("result").and_then(py_error) {
            add_error_case(&mut errs, &case, e, &eq::equilibrium_constant(tk));
            continue;
        }
        let mut sh = 0.0;
        let mut sg = 0.0;
        for (sp, nu) in eq::NU {
            let (_, a, b) = d.term_scales(sp, tk)?;
            sh += nu.abs() * a;
            sg += nu.abs() * (a + tk * b / 1000.0);
        }
        dh.add_scaled(
            &case,
            eq::reaction_enthalpy_kj_mol(tk)?,
            num(&c["dH_kJ_mol"]),
            sh,
        );
        dg.add_scaled(
            &case,
            eq::reaction_gibbs_kj_mol(tk)?,
            num(&c["dG_kJ_mol"]),
            sg,
        );
        ds.add_scaled(
            &case,
            eq::reaction_entropy_j_mol_k(tk)?,
            num(&c["dS_J_molK"]),
            (sh + sg) * 1000.0 / tk,
        );
        kp.add(&case, eq::equilibrium_constant(tk)?, num(&c["Kp"]));
    }
    for a in [cp, h, s, g, dh, dg, ds, kp, errs] {
        rep.push(a);
    }
    Ok(())
}

/// Python `RuntimeError`/`ValueError` of `solve_equilibrium(eos="pr")` at the upper bracket end
/// (negative mole fractions from `exp(ln n_max)` rounding): a documented reference defect whose
/// occurrence depends on the last bit of the platform's exp/log.
fn is_bracket_end_defect(msg: &str) -> bool {
    msg.starts_with("mole fractions must be finite and >= 0")
}

fn equilibrium_checks(
    golden: &Golden,
    file: &str,
    tag: &str,
    rep: &mut Report,
) -> Result<(), EngineError> {
    let t = golden.load(file)?;
    let mut conv = Acc::abs(
        &format!("{tag}.conversion"),
        "equilibrium NH3 conversion",
        GATE_X,
    );
    let mut ext = Acc::abs(
        &format!("{tag}.extent_rel_feed"),
        "extent / total feed",
        GATE_X,
    );
    let mut nout = Acc::abs(
        &format!("{tag}.n_out_rel_feed"),
        "n_out / total feed",
        GATE_X,
    );
    let mut y = Acc::abs(&format!("{tag}.y"), "equilibrium mole fractions", GATE_X);
    let mut keys = Acc::exact(&format!("{tag}.species_sets"), "species kept in the result");
    let mut kq = Acc::rel(&format!("{tag}.K_eq"), "K_eq", GATE_NASA);
    let mut phi = Acc::rel(
        &format!("{tag}.phi"),
        "fugacity coefficients at equilibrium",
        GATE_PR,
    );
    let mut res = Acc::abs(
        &format!("{tag}.residual"),
        "residual of ln K at the root",
        1e-12,
    );
    let mut errs = Acc::exact(&format!("{tag}.errors"), "input and bracket errors");
    let mut its = Acc::info(
        &format!("{tag}.brentq_iterations"),
        "brentq iterations and function calls (relative difference, informative)",
    );
    let mut defect = 0usize;
    let mut defect_agree = 0usize;
    for c in t["cases"].as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let tk = num(&c["T_K"]);
        let p = num(&c["P_bar"]);
        let feed = comp_of(&c["feed"])?;
        let eos = if c["eos"].as_str() == Some("pr") {
            Eos::Pr
        } else {
            Eos::Ideal
        };
        let kij = kij_of(&c["kij"])?;
        let alpha = alpha_of(&c["alpha"]);
        let case = format!(
            "{} T={tk} P={p} kij={} alpha={}",
            c["feed_name"].as_str().unwrap_or("?"),
            c["kij"].as_array().map(|a| a.len()).unwrap_or(0),
            c["alpha"].as_str().unwrap_or("")
        );
        let r = eq::solve_equilibrium(tk, p, &feed, eos, &kij, alpha);
        let pyr = &c["result"];
        if let Some(e) = py_error(pyr) {
            let msg = pyr["message"].as_str().unwrap_or("");
            if eos == Eos::Pr && is_bracket_end_defect(msg) {
                defect += 1;
                if matches!(&r, Err(EngineError::Domain(m)) if is_bracket_end_defect(m)) {
                    defect_agree += 1;
                }
                continue;
            }
            add_error_case(&mut errs, &case, e, &r);
            continue;
        }
        let r = match r {
            Ok(r) => r,
            Err(e) => {
                errs.add_bool(&case, false, || format!("python solved, rust error {e}"));
                continue;
            }
        };
        errs.add_bool(&case, true, String::new);
        let scale: f64 = feed.iter().sum();
        conv.add(&case, r.conversion, num(&pyr["conversion"]));
        ext.add(&case, r.extent / scale, num(&pyr["extent"]) / scale);
        let pn = species_map(&pyr["n_out"])?;
        let scaled: Vec<(Species, f64)> = r.n_out.iter().map(|x| (x.0, x.1 / scale)).collect();
        let pscaled: serde_json::Map<String, Value> = pn
            .iter()
            .map(|x| (x.0.name().to_string(), serde_json::json!(x.1 / scale)))
            .collect();
        add_species(
            &mut nout,
            &mut keys,
            &case,
            &scaled,
            &Value::Object(pscaled),
        );
        add_species(&mut y, &mut keys, &case, &r.y, &pyr["y"]);
        add_species(&mut phi, &mut keys, &case, &r.phi, &pyr["phi"]);
        kq.add(&case, r.k_eq, num(&pyr["K_eq"]));
        res.add(&case, r.residual, num(&pyr["residual"]));
        if let Some(b) = pyr.get("brentq").filter(|b| !b.is_null()) {
            its.add(&case, f64::from(r.iterations), num(&b["iterations"]));
            its.add(
                &case,
                f64::from(r.function_calls),
                num(&b["function_calls"]),
            );
        }
    }
    for a in [conv, ext, nout, y, keys, kq, phi, res, errs, its] {
        rep.push(a);
    }
    if defect > 0 {
        rep.findings.push(format!(
            "{tag}: {defect} case(s) where Python solve_equilibrium(eos='pr') raises ValueError at the \
             upper bracket end (exp(ln n_max) > n_max gives mole fractions of -1e-16, rejected by \
             peng_robinson._prepare; reference defect, equilibrium.py lines 290-292); Rust raises the \
             same error in {defect_agree} of them (the outcome depends on the last bit of exp/log)"
        ));
    }
    Ok(())
}

fn phase_of(k: &str) -> Phase {
    if k.contains("liquid") {
        Phase::Liquid
    } else {
        Phase::Vapour
    }
}

fn pr_checks(golden: &Golden, rep: &mut Report) -> Result<(), EngineError> {
    let t = golden.load("peng_robinson.json")?;
    let mut phi = Acc::rel(
        "pr.phi",
        "fugacity coefficients (vapour and liquid root)",
        GATE_PR,
    );
    let mut keys = Acc::exact("pr.species_sets", "species of the fugacity result");
    let mut z = Acc::rel("pr.Z", "compressibility (vapour and liquid root)", GATE_PR);
    let mut band: Vec<String> = Vec::new();
    let mut hd = Acc::rel(
        "pr.H_dep",
        "enthalpy departure (vapour and liquid root)",
        GATE_PR,
    )
    .note(
        "relative to max(|H_dep|, |RT(Z-1)| + |a-term|): the two terms cancel in a near-ideal gas, and \
         da/dT is a central difference of mixing sums that NumPy/BLAS add in another order",
    );
    let mut roots = Acc::exact(
        "pr.root_count",
        "one or several physical roots (Z_vapour == Z_liquid in Python)",
    );
    let mut errs = Acc::exact("pr.errors", "invalid mole fractions and kij");
    for c in t["cases"].as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let y = species_map(&c["y"])?;
        let tk = num(&c["T_K"]);
        let p = num(&c["P_bar"]);
        let kij = kij_of(&c["kij"])?;
        let alpha = alpha_of(&c["alpha"]);
        let case = format!(
            "{} T={tk} P={p} {} kij={}",
            c["comp"].as_str().unwrap_or(""),
            c["alpha"].as_str().unwrap_or(""),
            c["kij_name"].as_str().unwrap_or("")
        );
        for key in ["phi_vapour", "phi_liquid"] {
            let r = pr::fugacity_coefficients(&y, tk, p, &kij, alpha, phase_of(key));
            match (py_error(&c[key]), r) {
                (Some(e), r) => add_error_case(&mut errs, &format!("{case} {key}"), e, &r),
                (None, Ok(v)) => {
                    add_species(&mut phi, &mut keys, &format!("{case} {key}"), &v, &c[key])
                }
                (None, Err(e)) => errs.add_bool(&case, false, || format!("{key}: rust error {e}")),
            }
        }
        let mut zz = [f64::NAN; 2];
        for (i, key) in ["Z_vapour", "Z_liquid"].iter().enumerate() {
            let r = pr::compressibility(&y, tk, p, &kij, alpha, phase_of(key));
            match (py_error(&c[*key]), r) {
                (Some(e), r) => add_error_case(&mut errs, &format!("{case} {key}"), e, &r),
                (None, Ok(v)) => {
                    zz[i] = v;
                    z.add(&format!("{case} {key}"), v, num(&c[*key]));
                }
                (None, Err(e)) => errs.add_bool(&case, false, || format!("{key}: rust error {e}")),
            }
        }
        let py_one = num(&c["Z_vapour"]) == num(&c["Z_liquid"]);
        let rs_one = zz[0] == zz[1];
        roots.add_bool(&case, py_one == rs_one, || {
            format!("python single root {py_one}, rust single root {rs_one}")
        });
        for key in ["H_dep_vapour_J_mol", "H_dep_liquid_J_mol"] {
            let r = pr::enthalpy_departure_terms_j_mol(&y, tk, p, &kij, alpha, phase_of(key));
            match (py_error(&c[key]), r) {
                (Some(e), r) => add_error_case(&mut errs, &format!("{case} {key}"), e, &r),
                (None, Ok((t1, t2))) => hd.add_scaled(
                    &format!("{case} {key}"),
                    t1 + t2,
                    num(&c[key]),
                    t1.abs() + t2.abs(),
                ),
                (None, Err(e)) => errs.add_bool(&case, false, || format!("{key}: rust error {e}")),
            }
        }
    }
    for c in t["invalid_inputs"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[])
    {
        let y = species_map(&c["y"])?;
        let case = format!("invalid {}", c["y"]);
        let kij = kij_of(&c["kij"]);
        let r = kij.and_then(|k| {
            pr::fugacity_coefficients(&y, 500.0, 10.0, &k, Alpha::Standard, Phase::Vapour)
        });
        match py_error(&c["phi_vapour"]) {
            Some(e) => add_error_case(&mut errs, &case, e, &r),
            None => errs.add_bool(&case, r.is_ok(), || "python returned a value".into()),
        }
        let kij = kij_of(&c["kij"]);
        let r = kij
            .and_then(|k| pr::compressibility(&y, 500.0, 10.0, &k, Alpha::Standard, Phase::Vapour));
        match py_error(&c["Z_vapour"]) {
            Some(e) => add_error_case(&mut errs, &format!("{case} Z"), e, &r),
            None => errs.add_bool(&case, r.is_ok(), || "python returned a value".into()),
        }
    }
    // cubic classification near double roots
    let mut count_out = Acc::exact(
        "pr.cubic_root_count",
        "number of real and of physical roots, |relative offset from the double-root boundary| >= 1e-12",
    )
    .note("numpy.roots + |imag| < 1e-10 versus the analytic cubic + the same rule on the deflated pair");
    let mut count_in = Acc::info(
        "pr.cubic_root_count_band",
        "root-count disagreement (0/1) within 1e-12 of a double-root boundary (informative)",
    );
    let mut zc = Acc::info(
        "pr.cubic_Z_near_double_root",
        "selected Z near double roots (ill-conditioned there: about sqrt(eps) for both methods)",
    );
    for c in t["cubic_near_double_roots"]["cases"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[])
    {
        let a = num(&c["A"]);
        let b = num(&c["B"]);
        let off = num(&c["rel_offset"]);
        let case = format!("B={b} A={a:e} offset={off:e}");
        let a2 = -(1.0 - b);
        let a1 = a - 3.0 * b.powf(2.0) - 2.0 * b;
        let a0 = -(a * b - b.powf(2.0) - b.powf(3.0));
        let cl = pr::classify_cubic(a2, a1, a0);
        let n_real = cl.real.len();
        let n_phys = cl.real.iter().filter(|z| **z > b).count();
        let py_real = c["numpy"]["n_real_numpy_rule"].as_u64().unwrap_or(99) as usize;
        let py_phys = c["numpy"]["n_physical"].as_u64().unwrap_or(99) as usize;
        let ok = n_real == py_real && n_phys == py_phys;
        let detail = || {
            format!(
                "numpy real/physical {py_real}/{py_phys}, rust {n_real}/{n_phys} (analytic {} real, pair imag {:e})",
                cl.n_real_analytic, cl.pair_imag
            )
        };
        if off.abs() >= 1e-12 {
            count_out.add_bool(&case, ok, detail);
        } else {
            if !ok {
                band.push(format!("{case}: {}", detail()));
            }
            count_in.add_bool(&case, ok, detail);
        }
        for key in ["Z_vapour", "Z_liquid"] {
            if py_error(&c[key]).is_none()
                && let Ok(v) = pr::z_root(a, b, phase_of(key))
            {
                zc.add(&case, v, num(&c[key]));
            }
        }
    }
    for a in [phi, keys, z, hd, roots, errs, count_out, count_in, zc] {
        rep.push(a);
    }
    if !band.is_empty() {
        rep.findings.push(format!(
            "Peng-Robinson cubic: {} of the cases within a relative offset of 1e-12 from a double-root \
             boundary classify the roots differently (numpy eigenvalues versus analytic cubic; both are \
             within rounding of a double root there): {}",
            band.len(),
            band.join("; ")
        ));
    }
    Ok(())
}

fn dew_checks(golden: &Golden, rep: &mut Report) -> Result<(), EngineError> {
    let t = golden.load("dew_point.json")?;
    let mut td = Acc::rel("dew.T", "dew-point temperature", 1e-8);
    let mut xs = Acc::abs(
        "dew.x",
        "incipient liquid composition at the dew point",
        1e-8,
    )
    .note("x at T_dew inherits the 1e-9 K brentq tolerance: |dx/dT| * 1e-9 K < 1e-8");
    let mut keys = Acc::exact("dew.species_sets", "species of the liquid");
    let mut scan = Acc::exact(
        "dew.scan_decisions",
        "at every scan temperature: dew_liquid fails or not, and the sign of S - 1",
    );
    let mut scan_v = Acc::rel("dew.scan_S", "S - 1 at the scan temperatures", 1e-10);
    let mut brk = Acc::exact(
        "dew.bracket",
        "bracket chosen by the scan (or not bracketed)",
    );
    let mut errs = Acc::exact("dew.errors", "dew_point_K raises (not bracketed)");
    let mut sat = Acc::rel(
        "dew.saturation_T",
        "pure-component saturation temperature",
        1e-8,
    );
    let mut ds = Acc::rel(
        "dew.dew_liquid_S",
        "S of dew_liquid on a (T, P) grid",
        1e-10,
    );
    let mut dx = Acc::abs(
        "dew.dew_liquid_x",
        "x of dew_liquid on a (T, P) grid",
        1e-10,
    );
    for c in t["cases"].as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let y = species_map(&c["y"])?;
        let p = num(&c["P_bar"]);
        let kij = kij_of(&c["kij"])?;
        let alpha = alpha_of(&c["alpha"]);
        let case = format!(
            "{} P={p} kij={}",
            c["mix"].as_str().unwrap_or(""),
            c["kij"].as_array().map(|a| a.len()).unwrap_or(0)
        );
        let mut trace = Vec::new();
        let r = pr::dew_point_k_traced(p, &y, &kij, alpha, &mut trace);
        if let Some(sc) = c.get("scan").and_then(Value::as_array) {
            let same_len = sc.len() == trace.len();
            scan.add_bool(&format!("{case} length"), same_len, || {
                format!("python scan {} points, rust {}", sc.len(), trace.len())
            });
            for (pt, (tr, vr)) in sc.iter().zip(&trace) {
                let tp = num(&pt["T_K"]);
                let pcase = format!("{case} T={tp}");
                let py_fail = pt.get("error").is_some();
                let ok = tp == *tr
                    && match (py_fail, vr) {
                        (true, None) => true,
                        (false, Some(v)) => {
                            let pv = num(&pt["S"]) - 1.0;
                            scan_v.add(&pcase, *v, pv);
                            (pv > 0.0) == (*v > 0.0) && (pv < 0.0) == (*v < 0.0)
                        }
                        _ => false,
                    };
                scan.add_bool(&pcase, ok, || {
                    format!("python {pt}, rust T={tr} S-1={vr:?}")
                });
            }
        }
        let pyr = &c["result"];
        match (py_error(pyr), r) {
            (Some(e), r) => add_error_case(&mut errs, &case, e, &r),
            (None, Err(e)) => errs.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(dp)) => {
                errs.add_bool(&case, true, String::new);
                td.add(&case, dp.t_k, num(&pyr["T_K"]));
                add_species(&mut xs, &mut keys, &case, &dp.x, &pyr["x"]);
                if let Some(b) = c.get("bracket").and_then(Value::as_array) {
                    let ok = dp
                        .brentq
                        .map(|r| r.a == num(&b[0]) && r.b == num(&b[1]))
                        .unwrap_or(false);
                    brk.add_bool(&case, ok, || {
                        format!("python [{}, {}], rust {:?}", b[0], b[1], dp.brentq)
                    });
                }
            }
        }
    }
    for c in t["dew_liquid"].as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let y = species_map(&c["y"])?;
        let tk = num(&c["T_K"]);
        let p = num(&c["P_bar"]);
        let case = format!("{} T={tk} P={p}", c["mix"].as_str().unwrap_or(""));
        let r = pr::dew_liquid(&y, tk, p, &Kij::zero(), Alpha::Standard, 2000);
        match (py_error(&c["result"]), r) {
            (Some(e), r) => add_error_case(&mut errs, &case, e, &r),
            (None, Err(e)) => errs.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok((x, s, _))) => {
                ds.add(&case, s, num(&c["result"]["S"]));
                add_species(&mut dx, &mut keys, &case, &x, &c["result"]["x"]);
            }
        }
    }
    for c in t["saturation"].as_array().map(Vec::as_slice).unwrap_or(&[]) {
        let sp = Species::from_name(c["species"].as_str().unwrap_or(""))
            .ok_or_else(|| EngineError::data("dew_point.json", "species"))?;
        let p = num(&c["P_bar"]);
        let alpha = alpha_of(&c["alpha"]);
        let case = format!("{} P={p} {}", sp.name(), c["alpha"].as_str().unwrap_or(""));
        let r = pr::saturation_temperature_k(sp, p, alpha);
        match (py_error(&c["result"]), r) {
            (Some(e), r) => add_error_case(&mut errs, &case, e, &r),
            (None, Err(e)) => errs.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok((tk, rec))) => {
                sat.add(&case, tk, num(&c["result"]["T_K"]));
                let b = &c["result"]["brentq"];
                brk.add_bool(
                    &case,
                    rec.a == num(&b["a"]) && rec.b == num(&b["b"]),
                    || {
                        format!(
                            "python [{}, {}], rust [{}, {}]",
                            b["a"], b["b"], rec.a, rec.b
                        )
                    },
                );
            }
        }
    }
    for a in [td, xs, keys, scan, scan_v, brk, errs, sat, ds, dx] {
        rep.push(a);
    }
    Ok(())
}

fn enthalpy_checks(golden: &Golden, rep: &mut Report) -> Result<(), EngineError> {
    let t = golden.load("equilibrium_pr.json")?;
    let mut hi = Acc::rel(
        "enthalpy.ideal",
        "mixture enthalpy flow, ideal gas",
        GATE_NASA,
    )
    .note("relative to max(|H|, sum of |n_i h_i|)");
    let mut hp = Acc::rel(
        "enthalpy.pr",
        "mixture enthalpy flow with PR departure",
        GATE_PR,
    )
    .note("relative to max(|H|, sum of |n_i h_i|)");
    let mut errs = Acc::exact("enthalpy.errors", "errors");
    for c in t["enthalpy_cases"]
        .as_array()
        .map(Vec::as_slice)
        .unwrap_or(&[])
    {
        let n = species_map(&c["n_kmol_h"])?;
        let tk = num(&c["T_K"]);
        let p = num(&c["P_bar"]);
        let eos = if c["eos"].as_str() == Some("pr") {
            Eos::Pr
        } else {
            Eos::Ideal
        };
        let case = format!(
            "{} T={tk} P={p} {:?}",
            c["flows"].as_str().unwrap_or(""),
            eos
        );
        let r = eq::mixture_enthalpy_kw(&n, tk, Some(p), eos, &Kij::zero(), Alpha::Standard);
        match (py_error(&c["H_kW"]), r) {
            (Some(e), r) => add_error_case(&mut errs, &case, e, &r),
            (None, Err(e)) => errs.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(v)) => {
                let mut scale = 0.0;
                for (s, f) in &n {
                    if *f != 0.0 {
                        scale += (f * nasa7::species_enthalpy_kj_mol(*s, tk)?).abs() / 3.6;
                    }
                }
                let acc = if eos == Eos::Pr { &mut hp } else { &mut hi };
                acc.add_scaled(&case, v, num(&c["H_kW"]), scale);
            }
        }
    }
    for a in [hi, hp, errs] {
        rep.push(a);
    }
    Ok(())
}
