#!/usr/bin/env python3
"""Route unchanged independent numeric oracle to C1's fresh spec/root."""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts/audit-rc6-native-reader-c33-readiness.py"
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == "0992fe2e16f4c6a26d042b0c6d9481d86dcb754d819d52f7e898c087be2e2f47"
spec = importlib.util.spec_from_file_location("c33_retained_auditor", BASE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == "__main__":
    module.SPEC = ROOT / "specs/ai-native-studio-rc6-native-reader-c33-readiness-c1.v1.24.json"
    raise SystemExit(module.main())
