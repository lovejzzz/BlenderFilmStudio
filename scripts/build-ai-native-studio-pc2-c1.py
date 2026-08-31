#!/usr/bin/env python3
"""C1 wrapper: replace one cross-language protected-state hash check with exact structure comparison."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "scripts/build-ai-native-studio-pc2.py"
BASE_SHA256 = "2f0c7abd6f5f861ef6bf9608f31e621f43a25ad73d6fe00dcee9c9f725395a83"
OLD = '''if hash_value(protected_before) != spec["acceptedPc1Baseline"]["cameraLightSentinelsCanonicalSha256"]:
    raise RuntimeError("BASELINE_PROTECTED_STATE")'''
NEW = '''accepted_pc1_build_path = args.spec.resolve().parent.parent / "experiments/ai-native-studio-post-pb7/PC.1-2026-08-31-mac-m2max-attempt-04/build.json"
if sha256_file(accepted_pc1_build_path) != "a908299143cc4ce62cd135126884c67cee438f7a3f0d937cca1a22738d3d2be5":
    raise RuntimeError("ACCEPTED_PC1_BUILD_FILE")
accepted_pc1_build = json.loads(accepted_pc1_build_path.read_text(encoding="utf-8"))
if protected_before != accepted_pc1_build["protectedStateAfter"]:
    raise RuntimeError("BASELINE_PROTECTED_STATE")'''


payload = BASE.read_bytes()
if hashlib.sha256(payload).hexdigest() != BASE_SHA256:
    raise RuntimeError("C1_BASE_BUILDER_HASH")
source = payload.decode("utf-8")
if source.count(OLD) != 1:
    raise RuntimeError("C1_BASE_BUILDER_PATCH_SITE")
exec(compile(source.replace(OLD, NEW), str(BASE), "exec"), {"__name__": "__main__", "__file__": str(BASE)})
