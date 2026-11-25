"""Platform experiment of stage 5 (Linux side): NumPy's standard_normal stream on this machine against the Windows
reference recorded in rust/golden/stage5/ziggurat.json (SHA-256 of 10^6 draws per seed). Prints one JSON line.

    python rust/tools/ziggurat_numpy_sha.py
"""
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
g = json.loads((REPO / "rust/golden/stage5/ziggurat.json").read_text(encoding="utf-8"))
out = {"platform": platform.platform(), "numpy": np.__version__, "reference_platform": g["platform"],
       "reference_numpy": g["numpy"], "seeds": []}
for s in g["seeds"]:
    v = np.random.default_rng(s["seed"]).standard_normal(s["n"])
    sha = hashlib.sha256(np.ascontiguousarray(v, "<f8").tobytes()).hexdigest()
    out["seeds"].append({"seed": s["seed"], "sha256_le_f8": sha, "equals_reference": sha == s["sha256_le_f8"]})
print("ZIGGURAT-NUMPY " + json.dumps(out))
sys.exit(0)