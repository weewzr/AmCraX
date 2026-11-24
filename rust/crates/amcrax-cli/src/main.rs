//! `amcrax`: command-line front end of the AmCraX engine.
//!
//! Stage 0 provides `--version` and `verify`, which checks golden reference tables. The study
//! commands (`amcrax study <name>`, `amcrax eval`, `amcrax export-simulator`) arrive with the
//! stages that port them.

mod verify;

use std::path::PathBuf;
use std::process::ExitCode;

const USAGE: &str = "\
amcrax: AmCraX engine command-line interface

USAGE:
    amcrax --version
    amcrax --help
    amcrax verify <target> [--golden <dir>]

VERIFY TARGETS:
    numerics    check the SHA-256 of every golden table in <dir> (default: rust/golden/numerics
                under $AMCRAX_ROOT or the current directory) and compare the Rust numerics with
                the bit-exact tables (brentq, PCG64, Sobol, LHS, statistics, interpolation)
";

#[derive(Debug, PartialEq, Eq)]
enum Command {
    Version,
    Help,
    Verify {
        target: String,
        golden: Option<PathBuf>,
    },
}

fn parse_args(args: &[String]) -> Result<Command, String> {
    let mut it = args.iter();
    match it.next().map(String::as_str) {
        None | Some("-h") | Some("--help") | Some("help") => Ok(Command::Help),
        Some("-V") | Some("--version") | Some("version") => Ok(Command::Version),
        Some("verify") => {
            let mut target = None;
            let mut golden = None;
            while let Some(a) = it.next() {
                match a.as_str() {
                    "--golden" => {
                        let v = it.next().ok_or("--golden needs a directory")?;
                        golden = Some(PathBuf::from(v));
                    }
                    s if s.starts_with('-') => return Err(format!("unknown option {s}")),
                    s => {
                        if target.is_some() {
                            return Err(format!("unexpected argument {s}"));
                        }
                        target = Some(s.to_string());
                    }
                }
            }
            let target = target.ok_or("verify needs a target (numerics)")?;
            Ok(Command::Verify { target, golden })
        }
        Some(other) => Err(format!("unknown command {other}")),
    }
}

fn default_golden_dir() -> PathBuf {
    let rel = PathBuf::from("rust").join("golden").join("numerics");
    if let Some(root) = std::env::var_os(amcrax_engine::data::ROOT_ENV) {
        let p = PathBuf::from(root).join(&rel);
        if p.is_dir() {
            return p;
        }
    }
    for cand in [rel.clone(), PathBuf::from("golden").join("numerics")] {
        if cand.is_dir() {
            return cand;
        }
    }
    rel
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match parse_args(&args) {
        Ok(Command::Version) => {
            println!("amcrax {}", amcrax_engine::ENGINE_VERSION);
            ExitCode::SUCCESS
        }
        Ok(Command::Help) => {
            print!("{USAGE}");
            ExitCode::SUCCESS
        }
        Ok(Command::Verify { target, golden }) => {
            let dir = golden.unwrap_or_else(default_golden_dir);
            match target.as_str() {
                "numerics" => match verify::numerics(&dir) {
                    Ok(report) => {
                        print!("{}", report.render());
                        if report.passed() {
                            ExitCode::SUCCESS
                        } else {
                            ExitCode::FAILURE
                        }
                    }
                    Err(e) => {
                        eprintln!("amcrax verify numerics: {e}");
                        ExitCode::from(2)
                    }
                },
                other => {
                    eprintln!("amcrax verify: unknown target {other} (available: numerics)");
                    ExitCode::from(2)
                }
            }
        }
        Err(e) => {
            eprintln!("amcrax: {e}\n\n{USAGE}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn parses_commands() {
        assert_eq!(parse_args(&args(&["--version"])), Ok(Command::Version));
        assert_eq!(parse_args(&args(&[])), Ok(Command::Help));
        assert_eq!(
            parse_args(&args(&["verify", "numerics", "--golden", "g"])),
            Ok(Command::Verify {
                target: "numerics".into(),
                golden: Some(PathBuf::from("g"))
            })
        );
        assert!(parse_args(&args(&["verify"])).is_err());
        assert!(parse_args(&args(&["verify", "a", "b"])).is_err());
        assert!(parse_args(&args(&["frobnicate"])).is_err());
    }
}
