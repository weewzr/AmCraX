//! Stage 3 tests: economics, carbon pricing and the uncertainty-quantification estimators against
//! the tables of the Python reference (`rust/golden/generate_stage3_golden.py`) and the stored
//! research results.
#![cfg(feature = "yaml")]

use amcrax_engine::economics::reference::EconomicsData;
use amcrax_engine::verify::{Golden, stage3};
use std::path::{Path, PathBuf};

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn golden() -> Golden {
    Golden::open(&root().join("rust").join("golden").join("stage3")).expect("stage 3 golden tables")
}

fn check(r: amcrax_engine::verify::Report) {
    print!("{}", r.render());
    assert!(r.passed(), "{} golden comparison failed", r.target);
}

#[test]
fn economics_golden() {
    check(
        stage3::economics(&golden(), EconomicsData::embedded(), Path::new(&root()))
            .expect("economics check runs"),
    );
}
