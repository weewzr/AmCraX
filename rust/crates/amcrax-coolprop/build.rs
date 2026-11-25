//! Links the CoolProp static library when `COOLPROP_LIB_DIR` names a directory that contains
//! `libCoolProp.a` (built in CI from the pinned CoolProp sources, see
//! `.github/workflows/rust.yml`, job `coolprop`). Without it the crate compiles in stub mode.
//! This build script only prints link directives and copies the CoolProp licence text; it does
//! not compile or download anything.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    println!("cargo:rustc-check-cfg=cfg(coolprop_linked)");
    println!("cargo:rerun-if-env-changed=COOLPROP_LIB_DIR");
    println!("cargo:rerun-if-env-changed=COOLPROP_LICENCE_FILE");
    println!("cargo:rerun-if-changed=build.rs");
    let out = PathBuf::from(env::var("OUT_DIR").unwrap_or_else(|_| ".".into()));
    let mut licence = String::from(
        "CoolProp is not linked into this build (stub mode: COOLPROP_LIB_DIR was not set at build time).",
    );
    if let Ok(dir) = env::var("COOLPROP_LIB_DIR")
        && !dir.is_empty()
    {
        println!("cargo:rustc-link-search=native={dir}");
        println!("cargo:rustc-link-lib=static=CoolProp");
        match env::var("CARGO_CFG_TARGET_OS").as_deref() {
            Ok("macos") => println!("cargo:rustc-link-lib=dylib=c++"),
            Ok("windows") => {}
            _ => {
                println!("cargo:rustc-link-lib=dylib=stdc++");
                println!("cargo:rustc-link-lib=dylib=dl");
                println!("cargo:rustc-link-lib=dylib=pthread");
            }
        }
        println!("cargo:rustc-cfg=coolprop_linked");
        licence = match env::var("COOLPROP_LICENCE_FILE") {
            Ok(f) => fs::read_to_string(Path::new(&f)).unwrap_or_else(|e| {
                format!("CoolProp (MIT License): licence file {f} could not be read: {e}")
            }),
            Err(_) => {
                "CoolProp (MIT License): licence file not given (COOLPROP_LICENCE_FILE)".into()
            }
        };
    }
    if let Err(e) = fs::write(out.join("coolprop_licence.txt"), licence) {
        println!("cargo:warning=cannot write the licence text: {e}");
    }
}
