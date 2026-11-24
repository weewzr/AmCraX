//! Stage 4 tests: process flowsheet (and heat integration, separation) against the tables of the
//! Python reference (`rust/golden/generate_stage4_golden.py`) and the stored results, on the
//! `tables` fluid-property back end (tabulated CoolProp values, exact only at stored states).

use amcrax_engine::verify::{Golden, stage4};
use std::path::PathBuf;

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn golden() -> Golden {
    Golden::open(&root().join("rust").join("golden").join("stage4")).expect("stage 4 golden tables")
}

fn check(r: amcrax_engine::verify::Report) {
    print!("{}", r.render());
    assert!(r.passed(), "{} golden comparison failed", r.target);
}

#[test]
fn flowsheet_golden_tables_backend() {
    let g = golden();
    let b = stage4::tables_backend(&g).expect("coolprop_states table");
    check(stage4::flowsheet(&g, &b, &root()).expect("flowsheet check runs"));
}
