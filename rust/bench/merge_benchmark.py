"""Combine the Python and Rust timings of one benchmark job into benchmark_stage3.json (run in the same job).

    python rust/bench/merge_benchmark.py bench_python.json bench_rust.json benchmark_stage3.json
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys


def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def ratio(p, r):
    return None if not p or not r else p / r


def main():
    py = json.load(open(sys.argv[1]))
    rs = json.load(open(sys.argv[2]))
    cpu = None
    lscpu = sh("lscpu") or ""
    for line in lscpu.splitlines():
        if line.startswith("Model name"):
            cpu = line.split(":", 1)[1].strip()
    comp = {}
    for k, pk, rk in (("economics one evaluate", ("economics", "one_evaluate_s"), ("economics", "one_evaluate_s")),
                      ("economics batch 1e5 (dict output)", ("economics", "batch_evaluate_dict_s"), ("economics", "batch_evaluate_dict_s")),
                      ("economics batch 1e5 (Rust typed path)", ("economics", "batch_evaluate_dict_s"), ("economics", "batch_evaluate_typed_s")),
                      ("PFR isothermal one solve", ("pfr", "one_isothermal_s"), ("pfr", "one_isothermal_s")),
                      ("PFR adiabatic one solve", ("pfr", "one_adiabatic_s"), ("pfr", "one_adiabatic_s")),
                      ("PFR external one solve", ("pfr", "one_external_s"), ("pfr", "one_external_s")),
                      ("PFR batch of 200 isothermal", ("pfr", "batch_isothermal_s"), ("pfr", "batch_isothermal_s")),
                      ("global sensitivity study (17 analyses)", ("gsa", "full_study_s"), ("gsa", "full_study_s")),
                      ("kinetic propagation slice, 1 thread", ("kinetic_slice", "threads_1", "seconds"),
                       ("kinetic_slice", "threads_1", "seconds"))):
        def get(d, path):
            for x in path:
                d = (d or {}).get(x)
            return d
        p, r = get(py, pk), get(rs, rk)
        comp[k] = {"python_s": p, "rust_s": r, "speedup_python_over_rust": ratio(p, r)}
    ks = rs.get("kinetic_slice", {})
    t1 = (ks.get("threads_1") or {}).get("seconds")
    curve = {k: {"seconds": v["seconds"], "speedup_vs_1_thread": ratio(t1, v["seconds"]),
                 "identical_results": v.get("identical_to_first_thread_count")}
             for k, v in ks.items() if k.startswith("threads_")}
    doc = {
        "schema": "amcrax.benchmark/1",
        "description": "Stage 3 benchmark: Python reference against the Rust release build, measured in one GitHub Actions job",
        "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_sha": os.environ.get("GITHUB_SHA"),
        "runner": {"os": platform.platform(), "runner_os": os.environ.get("RUNNER_OS"),
                   "runner_name": os.environ.get("RUNNER_NAME"), "cpu_model": cpu, "cpu_count": os.cpu_count(),
                   "image": os.environ.get("ImageOS"), "image_version": os.environ.get("ImageVersion")},
        "rustc": sh("rustc", "--version"), "cargo_profile": "release (opt-level 3, thin LTO, codegen-units 1)",
        "rustflags": os.environ.get("RUSTFLAGS"), "python": py.get("python"), "numpy": py.get("numpy"),
        "scipy": py.get("scipy"),
        "timing": "wall clock (Rust std::time::Instant, Python time.perf_counter); median of the repetitions in each raw block",
        "comparison": comp, "rust_kinetic_slice_thread_curve": curve,
        "peak_rss_kB": {"python": py.get("peak_rss_kB"), "rust": rs.get("peak_rss_kB")},
        "raw": {"python": py, "rust": rs},
    }
    json.dump(doc, open(sys.argv[3], "w"), indent=1)
    print(json.dumps(doc, indent=1))


if __name__ == "__main__":
    main()
