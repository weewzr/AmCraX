//! Stage 2 checks: rate laws, viscosity, plug-flow reactor and the derived searches (golden tables
//! in `rust/golden/stage2`).

use super::{Acc, Golden, Report, error_matches, num, py_error};
use crate::error::EngineError;
use crate::kinetics::{
    self, KeqBasis, KineticsRegistry, Overrides, RateOpts, kum_keq, rate_detail, reaction_quotient,
    takahashi_constants, takahashi_coverages,
};
use crate::reactor::{
    PfrInput, PfrResult, SolverOptions, Target, catalyst_mass_for_conversion, simulate_pfr,
    temperature_for_conversion,
};
use crate::transport::{NV, SPECIES, Transport};
use serde_json::Value;

fn arr(v: &Value) -> &[Value] {
    v.as_array().map(Vec::as_slice).unwrap_or(&[])
}

fn pressures(v: &Value) -> Vec<(String, f64)> {
    v.as_object()
        .map(|m| m.iter().map(|(k, x)| (k.clone(), num(x))).collect())
        .unwrap_or_default()
}

fn opts_of(c: &Value) -> Result<(Option<bool>, KeqBasis, Option<Overrides>), EngineError> {
    let af = c["approach_factor"].as_bool();
    let kb = KeqBasis::from_python(c["keq_basis"].as_str().unwrap_or("published"))?;
    let ov = c["param_overrides"].as_object().map(|m| {
        m.iter()
            .map(|(k, v)| (k.clone(), num(v)))
            .collect::<Overrides>()
    });
    Ok((af, kb, ov))
}

fn add_err<T>(acc: &mut Acc, case: &str, py: &str, r: &Result<T, EngineError>) {
    let ok = matches!(r, Err(e) if error_matches(py, e));
    acc.add_bool(case, ok, || match r {
        Ok(_) => format!("python raised {py}, rust returned a value"),
        Err(e) => format!("python raised {py}, rust error {e}"),
    });
}

/// Rate laws and viscosity.
pub fn kinetics(golden: &Golden, reg: &KineticsRegistry) -> Result<Report, EngineError> {
    let mut rep = Report::new("kinetics");
    let t = golden.load("kinetics.json")?;
    let mut rate = Acc::rel(
        "kinetics.rate",
        "net NH3 rate, all laws, options and overrides",
        1e-12,
    )
    .note(
        "relative to max(|r|, term scale): |r_published| (1 + Q/K) with the approach factor, \
             k (fwd + rev) for Temkin-Pyzhev; near equilibrium the rate is a cancelling difference",
    );
    let mut edge = Acc::rel(
        "kinetics.rate_edge_cases",
        "zero H2, zero NH3, negative and tiny pressures, inerts",
        1e-12,
    );
    let mut errs = Acc::exact(
        "kinetics.errors",
        "Temkin-Pyzhev singularity, unknown catalyst, zero pressure",
    );
    let mut its = Acc::info(
        "kinetics.takahashi_brentq_iterations",
        "brentq iterations of the Takahashi site balance (relative difference)",
    );
    for (list, acc) in [(&t["cases"], &mut rate), (&t["edge_cases"], &mut edge)] {
        for c in arr(list) {
            let cid = c["catalyst_id"].as_str().unwrap_or("");
            let tk = num(&c["T_K"]);
            let p = pressures(&c["p_bar"]);
            let pr: Vec<(&str, f64)> = p.iter().map(|(k, v)| (k.as_str(), *v)).collect();
            let (af, kb, ov) = opts_of(c)?;
            let case = format!(
                "{cid} T={tk} {} X={} af={af:?} keq={:?} ov={}",
                c["feed_name"].as_str().unwrap_or(""),
                c["X"],
                kb,
                c["param_overrides"]
            );
            let r = rate_detail(
                reg,
                cid,
                tk,
                &pr,
                RateOpts {
                    approach_factor: af,
                    keq_basis: kb,
                    param_overrides: ov.as_ref(),
                },
            );
            match (py_error(&c["rate"]), r) {
                (Some(e), r) => add_err(&mut errs, &case, e, &r),
                (None, Err(e)) => errs.add_bool(&case, false, || format!("rust error {e}")),
                (None, Ok(d)) => {
                    errs.add_bool(&case, true, String::new);
                    acc.add_scaled(&case, d.rate, num(&c["rate"]), d.scale);
                    if let Some(b) = c.get("brentq").filter(|b| !b.is_null()) {
                        its.add(&case, f64::from(d.iterations), num(&b["iterations"]));
                    }
                }
            }
        }
    }
    let h = &t["helpers"];
    let mut keq = Acc::rel(
        "kinetics.kum_keq",
        "Kum Keq, published and amcrax_thermo bases",
        1e-12,
    );
    for c in arr(&h["kum_keq"]) {
        let tk = num(&c["T_K"]);
        keq.add(
            &format!("T={tk} published"),
            kum_keq(reg, tk, KeqBasis::Published)?,
            num(&c["published"]),
        );
        keq.add(
            &format!("T={tk} thermo"),
            kum_keq(reg, tk, KeqBasis::AmcraxThermo)?,
            num(&c["amcrax_thermo"]),
        );
    }
    let mut tk_acc = Acc::rel(
        "kinetics.takahashi_constants_coverages",
        "Takahashi k_i, K_i, coverages and r2",
        1e-12,
    )
    .note("coverages relative to max(|theta|, 1e-300)");
    for c in arr(&h["takahashi"]) {
        let cid = c["catalyst_id"].as_str().unwrap_or("");
        let tk = num(&c["T_K"]);
        let (yn, yh) = (num(&c["y_NH3"]), num(&c["y_H2"]));
        let case = format!("{cid} T={tk} yNH3={yn} yH2={yh}");
        let k = takahashi_constants(reg, cid, tk, None)?;
        let kc = &c["constants"];
        for (name, v) in [
            ("k1", k.k1),
            ("k_minus1", k.k_minus1),
            ("k2", k.k2),
            ("k3", k.k3),
            ("k4", k.k4),
            ("k_minus4", k.k_minus4),
            ("K1", k.big_k1),
            ("K4", k.big_k4),
        ] {
            tk_acc.add(&format!("{case} {name}"), v, num(&kc[name]));
        }
        let cov = takahashi_coverages(reg, cid, tk, yn, yh, None)?;
        let pc = &c["coverages"];
        for (name, v) in [
            ("theta_s", cov.theta_s),
            ("theta_NH3", cov.theta_nh3),
            ("theta_N", cov.theta_n),
            ("theta_H", cov.theta_h),
            ("r_mol_per_g_s", cov.r_mol_per_g_s),
        ] {
            tk_acc.add(&format!("{case} {name}"), v, num(&pc[name]));
        }
    }
    let mut luc = Acc::rel(
        "kinetics.lucentini_published",
        "Lucentini published rate, mol/(g s)",
        1e-12,
    );
    for c in arr(&h["lucentini_g"]) {
        let cid = c["catalyst_id"].as_str().unwrap_or("");
        let tk = num(&c["T_K"]);
        let p = pressures(&c["p_bar"]);
        let pr: Vec<(&str, f64)> = p.iter().map(|(k, v)| (k.as_str(), *v)).collect();
        luc.add(
            &format!("{cid} T={tk}"),
            kinetics::lucentini_rate_mol_per_g_s(reg, cid, tk, &pr, None)?,
            num(&c["rate_mol_per_g_s"]),
        );
    }
    for c in arr(&h["reaction_quotient"]) {
        let p = pressures(&c["p_bar"]);
        let pr: Vec<(&str, f64)> = p.iter().map(|(k, v)| (k.as_str(), *v)).collect();
        luc.add(
            &format!("Q {}", c["p_bar"]),
            reaction_quotient(&pr),
            num(&c["Q"]),
        );
    }
    for a in [rate, edge, errs, its, keq, tk_acc, luc] {
        rep.push(a);
    }
    viscosity(golden, &mut rep)?;
    Ok(rep)
}

fn viscosity(golden: &Golden, rep: &mut Report) -> Result<(), EngineError> {
    let t = golden.load("viscosity.json")?;
    let tr = Transport::embedded();
    let mut sha = Acc::exact(
        "viscosity.transport_data_sha256",
        "embedded transport_gri30.json equals the exported file",
    );
    let want = t["transport_sha256"].as_str().unwrap_or("");
    sha.add_bool("transport_gri30.json", tr.sha256 == want, || {
        format!("embedded {} exported {want}", tr.sha256)
    });
    let mut pure = Acc::rel(
        "viscosity.pure",
        "pure-species viscosity versus Cantera",
        1e-10,
    );
    for c in arr(&t["pure"]) {
        let tk = num(&c["T_K"]);
        let (v, _) = tr.species_viscosities(tk);
        for (k, s) in SPECIES.iter().enumerate() {
            pure.add(&format!("{s} T={tk}"), v[k], num(&c["mu_Pa_s"][*s]));
        }
    }
    let mut mix = Acc::rel(
        "viscosity.mixture",
        "mixture viscosity (Wilke) versus Cantera gas.viscosity",
        1e-10,
    );
    for c in arr(&t["mixture"]) {
        let tk = num(&c["T_K"]);
        let mut x = [0.0; NV];
        for (k, v) in c["y"].as_object().into_iter().flatten() {
            let v = num(v);
            match k.as_str() {
                "Ar" => {
                    if v > 0.0 {
                        x[5] = v;
                    }
                }
                name => {
                    if let Some(i) = SPECIES.iter().position(|s| *s == name) {
                        x[i] = v.max(0.0);
                    }
                }
            }
        }
        mix.add(
            &format!("T={tk} y={}", c["y"]),
            tr.mixture_viscosity(tk, &x)?,
            num(&c["mu_Pa_s"]),
        );
    }
    rep.push(sha);
    rep.push(pure);
    rep.push(mix);
    Ok(())
}

fn input_of(c: &Value) -> Result<PfrInput, EngineError> {
    let mut obj = c["kwargs"].as_object().cloned().unwrap_or_default();
    obj.insert("catalyst_id".into(), c["catalyst_id"].clone());
    obj.insert("W_kg".into(), c["W_kg"].clone());
    serde_json::from_value(Value::Object(obj))
        .map_err(|e| EngineError::data("pfr.json", e.to_string()))
}

struct PfrAccs {
    errs: Acc,
    hyd: Acc,
    npts: Acc,
    grid: Acc,
    w_stop: Acc,
    out_x: Acc,
    out_t: Acc,
    out_p: Acc,
    prof_x: Acc,
    prof_t: Acc,
    prof_p: Acc,
    prof_y: Acc,
    xeq: Acc,
    rate0: Acc,
    algebra: Acc,
    assumptions: Acc,
    info_rate: Acc,
    info_tau: Acc,
    info_heat: Acc,
    tight: Acc,
    lsoda_err: Acc,
}

impl PfrAccs {
    fn new() -> PfrAccs {
        PfrAccs {
            errs: Acc::exact(
                "pfr.errors",
                "input errors (same Python exception class) and successful runs",
            ),
            hyd: Acc::exact("pfr.hydraulic_limit_flag", "hydraulic-limit outcome"),
            npts: Acc::exact(
                "pfr.output_points",
                "number of output points (t_eval points before a stop, plus the stop)",
            ),
            grid: Acc::abs("pfr.W_grid", "output grid (numpy.linspace)", 0.0),
            w_stop: Acc::info(
                "pfr.W_at_hydraulic_stop",
                "catalyst mass at the hydraulic stop (relative)",
            ),
            out_x: Acc::abs("pfr.outlet_conversion", "outlet conversion", 1e-7),
            out_t: Acc::abs("pfr.outlet_T_K", "outlet temperature, K", 1e-4),
            out_p: Acc::abs("pfr.outlet_P_bar", "outlet pressure, bar", 1e-6),
            prof_x: Acc::abs("pfr.profile_conversion", "conversion profile", 1e-6),
            prof_t: Acc::abs("pfr.profile_T_K", "temperature profile, K", 1e-4),
            prof_p: Acc::abs("pfr.profile_P_bar", "pressure profile, bar", 1e-6),
            prof_y: Acc::abs("pfr.profile_y", "mole-fraction profiles", 1e-6),
            xeq: Acc::abs(
                "pfr.X_eq_local",
                "local equilibrium conversion along the bed",
                1e-6,
            )
            .note("a function of the local T and P: inherits their gates (|dX_eq/dT| < 1e-2 /K)"),
            rate0: Acc::rel("pfr.rate_inlet", "rate at the inlet (same state)", 1e-12),
            algebra: Acc::rel("pfr.derived_constants", "W/F, GHSV, bed volume", 1e-12),
            assumptions: Acc::exact(
                "pfr.assumptions",
                "assumption texts (hydraulic sentence up to the stop position)",
            ),
            info_rate: Acc::info(
                "pfr.rate_profile",
                "rate profile (relative; ~0 near equilibrium)",
            ),
            info_tau: Acc::info("pfr.residence_time", "outlet residence time (relative)"),
            info_heat: Acc::info("pfr.heat_input", "heat input kW (relative)"),
            tight: Acc::info(
                "pfr.rust_vs_lsoda_tight",
                "Rust profile conversion versus LSODA at rtol 1e-11 (absolute)",
            ),
            lsoda_err: Acc::info(
                "pfr.lsoda_production_vs_tight",
                "Python LSODA rtol 1e-8 versus rtol 1e-11 (absolute): the reference's own error",
            ),
        }
    }

    fn push_all(self, rep: &mut Report) {
        for a in [
            self.errs,
            self.hyd,
            self.npts,
            self.grid,
            self.w_stop,
            self.out_x,
            self.out_t,
            self.out_p,
            self.prof_x,
            self.prof_t,
            self.prof_p,
            self.prof_y,
            self.xeq,
            self.rate0,
            self.algebra,
            self.assumptions,
            self.info_rate,
            self.info_tau,
            self.info_heat,
            self.tight,
            self.lsoda_err,
        ] {
            rep.push(a);
        }
    }
}

fn cmp_series(acc: &mut Acc, case: &str, r: &[f64], p: &Value) {
    for (i, (a, b)) in r.iter().zip(arr(p)).enumerate() {
        acc.add(&format!("{case}[{i}]"), *a, num(b));
    }
}

fn hyd_prefix(s: &str) -> &str {
    s.split(" at W = ").next().unwrap_or(s)
}

fn compare_pfr(a: &mut PfrAccs, case: &str, r: &PfrResult, py: &Value, assumptions: &Value) {
    let po = &py["outlet"];
    let ph = po["hydraulic_limit"].as_bool().unwrap_or(false);
    a.hyd.add_bool(case, ph == r.outlet.hydraulic_limit, || {
        format!("python {ph}, rust {}", r.outlet.hydraulic_limit)
    });
    let pw = arr(&py["W_kg"]);
    a.npts.add_bool(case, pw.len() == r.w_kg.len(), || {
        format!("python {} points, rust {}", pw.len(), r.w_kg.len())
    });
    let n = pw.len().min(r.w_kg.len());
    for i in 0..n {
        let is_stop = ph && i + 1 == pw.len();
        if is_stop {
            a.w_stop.add(case, r.w_kg[i], num(&pw[i]));
        } else {
            a.grid.add(&format!("{case}[{i}]"), r.w_kg[i], num(&pw[i]));
        }
    }
    a.out_x
        .add(case, r.outlet.conversion, num(&po["conversion"]));
    a.out_t
        .add(case, r.outlet.t_c + 273.15, num(&po["T_C"]) + 273.15);
    a.out_p.add(case, r.outlet.p_bar, num(&po["P_bar"]));
    cmp_series(&mut a.prof_x, case, &r.conversion, &py["conversion"]);
    cmp_series(&mut a.prof_t, case, &r.t_k, &py["T_K"]);
    cmp_series(&mut a.prof_p, case, &r.p_bar, &py["P_bar"]);
    for (k, v) in &r.y {
        cmp_series(&mut a.prof_y, &format!("{case} y_{k}"), v, &py["y"][k]);
    }
    cmp_series(&mut a.xeq, case, &r.x_eq_local, &py["X_eq_local"]);
    if let (Some(r0), Some(p0)) = (
        r.rate_mol_per_kgcat_s.first(),
        arr(&py["rate_mol_per_kgcat_s"]).first(),
    ) {
        a.rate0.add(case, *r0, num(p0));
    }
    cmp_series(
        &mut a.info_rate,
        case,
        &r.rate_mol_per_kgcat_s,
        &py["rate_mol_per_kgcat_s"],
    );
    a.algebra.add(
        &format!("{case} W/F"),
        r.w_over_f_kg_s_per_mol_nh3,
        num(&py["W_over_F_kg_s_per_mol_NH3"]),
    );
    a.algebra.add(
        &format!("{case} GHSV"),
        r.ghsv_h_inv,
        num(&py["GHSV_h_inv"]),
    );
    a.algebra.add(
        &format!("{case} V_bed"),
        r.bed_volume_m3,
        num(&py["bed_volume_m3"]),
    );
    a.info_tau.add(
        case,
        r.outlet.residence_time_s,
        num(&po["residence_time_s"]),
    );
    a.info_heat
        .add(case, r.outlet.heat_input_kw, num(&po["heat_input_kW"]));
    let pa: Vec<&str> = arr(assumptions).iter().filter_map(Value::as_str).collect();
    let same = pa.len() == r.assumptions.len()
        && pa.iter().zip(&r.assumptions).all(|(p, q)| {
            if p.starts_with("integration stopped") {
                hyd_prefix(p) == hyd_prefix(q)
            } else {
                *p == q.as_str()
            }
        });
    a.assumptions.add_bool(case, same, || {
        format!("python {pa:?}, rust {:?}", r.assumptions)
    });
}

/// Plug-flow reactor and the derived searches.
pub fn reactor(
    golden: &Golden,
    reg: &KineticsRegistry,
    sopt: &SolverOptions,
) -> Result<Report, EngineError> {
    let mut rep = Report::new("reactor");
    let t = golden.load("pfr.json")?;
    let mut a = PfrAccs::new();
    let mut stiff = Vec::new();
    let mut max_steps = (0usize, String::new());
    for (group, list) in [("parity", &t["parity_cases"]), ("wider", &t["cases"])] {
        for c in arr(list) {
            let case = format!("{group}:{}", c["id"].as_str().unwrap_or(""));
            let inp = input_of(c);
            let r = inp.and_then(|i| simulate_pfr(reg, &i, sopt));
            let py = &c["result"];
            match (py_error(py), r) {
                (Some(e), r) => add_err(&mut a.errs, &case, e, &r),
                (None, Err(e)) => a.errs.add_bool(&case, false, || format!("rust error {e}")),
                (None, Ok(r)) => {
                    a.errs.add_bool(&case, true, String::new);
                    if r.solver.n_steps > max_steps.0 {
                        max_steps = (r.solver.n_steps, case.clone());
                    }
                    if r.solver.stiff {
                        stiff.push(format!(
                            "{case}: {} DOPRI5 steps ({} RHS)",
                            r.solver.n_steps, r.solver.nfev
                        ));
                    }
                    compare_pfr(&mut a, &case, &r, py, &c["assumptions"]);
                    if let Some(tr) = c.get("tight_reference") {
                        cmp_series(&mut a.tight, &case, &r.conversion, &tr["conversion"]);
                        for (i, (p, q)) in arr(&py["conversion"])
                            .iter()
                            .zip(arr(&tr["conversion"]))
                            .enumerate()
                        {
                            a.lsoda_err.add(&format!("{case}[{i}]"), num(p), num(q));
                        }
                    }
                }
            }
        }
    }
    a.push_all(&mut rep);
    rep.findings.push(format!(
        "DOPRI5 stiffness check (threshold {} accepted steps at rtol {:e}): {} case(s) above; largest step count {} ({})",
        sopt.stiff_steps,
        sopt.rtol,
        stiff.len(),
        max_steps.0,
        max_steps.1
    ));
    rep.findings.extend(stiff);

    let s = golden.load("searches.json")?;
    let mut mw = Acc::rel(
        "search.catalyst_mass",
        "catalyst mass for a target conversion",
        1e-5,
    );
    let mut mflags = Acc::exact(
        "search.catalyst_mass_flags",
        "reachable and hydraulic-limit outcomes",
    );
    let mut mtarget = Acc::rel(
        "search.target_conversion",
        "target conversion (fraction of equilibrium)",
        1e-10,
    );
    let mut minfo = Acc::info(
        "search.reached_state",
        "W and X reached when not reachable (relative)",
    );
    for c in arr(&s["catalyst_mass"]) {
        let case = format!(
            "{} {}",
            c["catalyst_id"].as_str().unwrap_or(""),
            c["name"].as_str().unwrap_or("")
        );
        let mut obj = c["kwargs"].as_object().cloned().unwrap_or_default();
        obj.insert("catalyst_id".into(), c["catalyst_id"].clone());
        obj.insert("W_kg".into(), Value::from(1.0));
        let base: PfrInput = serde_json::from_value(Value::Object(obj))
            .map_err(|e| EngineError::data("searches.json", e.to_string()))?;
        let tg = &c["target"];
        let target = if let Some(f) = tg.get("fraction_of_equilibrium") {
            Target::FractionOfEquilibrium(num(f))
        } else {
            Target::Conversion(num(&tg["target_conversion"]))
        };
        let w_max = tg.get("W_max_kg").map(num).unwrap_or(1e6);
        let r = catalyst_mass_for_conversion(reg, &base, target, w_max, sopt);
        let py = &c["result"];
        match (py_error(py), r) {
            (Some(e), r) => add_err(&mut mflags, &case, e, &r),
            (None, Err(e)) => mflags.add_bool(&case, false, || format!("rust error {e}")),
            (None, Ok(m)) => {
                let preach = py["reachable"].as_bool().unwrap_or(false);
                let phyd = py["hydraulic_limit"].as_bool().unwrap_or(false);
                mflags.add_bool(
                    &case,
                    preach == m.reachable && phyd == m.hydraulic_limit,
                    || {
                        format!(
                            "python reachable {preach} hydraulic {phyd}; rust {} {} ({:?})",
                            m.reachable, m.hydraulic_limit, m.reason
                        )
                    },
                );
                mtarget.add(&case, m.target_conversion, num(&py["target_conversion"]));
                if preach && m.reachable {
                    mw.add(&case, m.w_kg, num(&py["W_kg"]));
                } else {
                    if let Some(wr) = m.w_reached_kg {
                        minfo.add(&format!("{case} W"), wr, num(&py["W_reached_kg"]));
                    }
                    if let Some(xr) = m.x_reached {
                        minfo.add(&format!("{case} X"), xr, num(&py["X_reached"]));
                    }
                }
            }
        }
    }
    let mut tt = Acc::abs(
        "search.temperature_for_conversion",
        "inlet temperature for a target conversion, K",
        0.05,
    );
    let mut tflags = Acc::exact(
        "search.temperature_bracketed",
        "target bracketed between 300 and 900 degC",
    );
    for c in arr(&s["temperature_for_conversion"]) {
        let cid = c["catalyst_id"].as_str().unwrap_or("");
        let case = format!("{cid} P={} W={} X={}", c["P_bar"], c["W_kg"], c["X_target"]);
        let mut base = PfrInput::new(cid, num(&c["W_kg"]));
        base.p_in_bar = num(&c["P_bar"]);
        base.feed_kmol_h = Some([("NH3".to_string(), 100.0)].into_iter().collect());
        base.pressure_drop = false;
        base.eps_b = num(&c["bed"][0]);
        base.rho_particle_kg_m3 = num(&c["bed"][1]);
        let r =
            temperature_for_conversion(reg, &base, num(&c["X_target"]), 300.0, 900.0, 0.05, sopt)?;
        let pok = c["ok"].as_bool().unwrap_or(false);
        tflags.add_bool(&case, pok == r.ok, || {
            format!("python ok {pok}, rust {}", r.ok)
        });
        if pok && r.ok {
            tt.add(&case, r.t_required_c, num(&c["T_required_C"]));
        }
    }
    for acc in [mw, mflags, mtarget, minfo, tt, tflags] {
        rep.push(acc);
    }
    Ok(rep)
}
