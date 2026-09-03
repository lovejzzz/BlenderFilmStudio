#!/usr/bin/env python3
"""Versioned C1: canonical relative-string row order, unchanged execution."""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts/run-rc6-native-reader-c33-readiness.py"
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == "014d0dc78c7216e6916e693797eba94884b61cfe3759485b183f83edf3a9dcdd"
spec = importlib.util.spec_from_file_location("c33_retained_runner", BASE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original_tree = module.tree


def canonical_tree(root):
    return sorted(original_tree(root), key=lambda row: row["path"])


if __name__ == "__main__":
    assert not (ROOT / "experiments/physical-richness/RC6-2026-09-03-native-reader-c33-readiness-attempt-112").exists()
    assert not Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-03-native-reader-c33-readiness-attempt-112").exists()
    module.tree = canonical_tree
    module.SPEC = ROOT / "specs/ai-native-studio-rc6-native-reader-c33-readiness-c1.v1.24.json"
    raise SystemExit(module.main())
