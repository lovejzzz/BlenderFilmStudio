#!/usr/bin/env python3
"""C2 routes the unchanged canonical-order runner to codec-complete tools."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts/run-rc6-native-reader-c33-readiness-c1.py"
spec = importlib.util.spec_from_file_location("c33_c1_runner", BASE)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

if __name__ == "__main__":
    adapter.module.tree = adapter.canonical_tree
    adapter.module.SPEC = ROOT / "specs/ai-native-studio-rc6-native-reader-c33-readiness-c2.v1.25.json"
    contract = json.loads(adapter.module.SPEC.read_text())
    def retained_exact():
        for row in contract["retainedRoots"]:
            assert hashlib.sha256(adapter.module.canonical(adapter.canonical_tree(Path(row["root"])))).hexdigest() == row["sha256"]
    retained_exact()
    code = adapter.module.main()
    retained_exact()
    raise SystemExit(code)
