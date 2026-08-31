#!/usr/bin/env python3
"""C1 wrapper: audit protected state against exact accepted PC.1 evidence structure."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "scripts/audit-ai-native-studio-pc2.py"
BASE_SHA256 = "2891f7be72ee744a376b6d281760fcf3111c54d2179d1d6be05e44afcde07da7"
OLD = '''if hash_value(protected) != spec["acceptedPc1Baseline"]["cameraLightSentinelsCanonicalSha256"]:
    raise RuntimeError("PROTECTED_BASELINE")'''
NEW = '''accepted_pc1_build_path = args.spec.resolve().parent.parent / "experiments/ai-native-studio-post-pb7/PC.1-2026-08-31-mac-m2max-attempt-04/build.json"
if sha256_file(accepted_pc1_build_path) != "a908299143cc4ce62cd135126884c67cee438f7a3f0d937cca1a22738d3d2be5":
    raise RuntimeError("ACCEPTED_PC1_BUILD_FILE")
accepted_pc1_build = json.loads(accepted_pc1_build_path.read_text(encoding="utf-8"))
if protected != accepted_pc1_build["protectedStateAfter"]:
    raise RuntimeError("PROTECTED_BASELINE")'''


payload = BASE.read_bytes()
if hashlib.sha256(payload).hexdigest() != BASE_SHA256:
    raise RuntimeError("C1_BASE_AUDITOR_HASH")
source = payload.decode("utf-8")
if source.count(OLD) != 1:
    raise RuntimeError("C1_BASE_AUDITOR_PATCH_SITE")
exec(compile(source.replace(OLD, NEW), str(BASE), "exec"), {"__name__": "__main__", "__file__": str(BASE)})
