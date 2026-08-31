#!/usr/bin/env python3
"""C1 wrapper binding the unchanged runner to freeze C1 and fresh attempt-02 roots."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "scripts/run-ai-native-studio-pc2.py"
BASE_SHA256 = "b4574e86b8e21c6231af104c207334cd777b55c9d542ad3ba649561db2e51a0f"
REPLACEMENTS = {
    'FREEZE_URI = "specs/ai-native-studio-pc2-tool-freeze.v0.1.json"': 'FREEZE_URI = "specs/ai-native-studio-pc2-tool-freeze-c1.v0.2.json"',
    'EVIDENCE_URI = "experiments/ai-native-studio-post-pb7/PC.2-2026-08-31-mac-m2max-attempt-01"': 'EVIDENCE_URI = "experiments/ai-native-studio-post-pb7/PC.2-2026-08-31-mac-m2max-attempt-02"',
    'WORK_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.2-2026-08-31-mac-m2max-attempt-01")': 'WORK_ROOT = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.2-2026-08-31-mac-m2max-attempt-02")',
}


payload = BASE.read_bytes()
if hashlib.sha256(payload).hexdigest() != BASE_SHA256:
    raise RuntimeError("C1_BASE_RUNNER_HASH")
source = payload.decode("utf-8")
for old, new in REPLACEMENTS.items():
    if source.count(old) != 1:
        raise RuntimeError("C1_BASE_RUNNER_PATCH_SITE")
    source = source.replace(old, new)
exec(compile(source, str(BASE), "exec"), {"__name__": "__main__", "__file__": str(BASE)})
