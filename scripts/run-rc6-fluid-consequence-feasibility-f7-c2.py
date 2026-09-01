#!/usr/bin/env python3
"""RC6 F7 C2: bind attempt-12 and route corrected scene to attempt-13."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-feasibility-f7-c1.py")
EXPECTED_BASE_SHA256 = "e25e5b1718290c4af62d16af71ea6a91397094dc66b307a2b87e6050291d0513"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-feasibility-attempt-12/failure-audit.json"
EXPECTED_FAILURE_AUDIT_FILE_SHA256 = "6cb4ac6ac5fca8a687de76c8315a7b705cafa3f70c8f4bfb1e965ebb6a521238"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F7 C2 base host identity mismatch")
if hashlib.sha256(FAILURE_AUDIT.read_bytes()).hexdigest() != EXPECTED_FAILURE_AUDIT_FILE_SHA256:
    raise RuntimeError("RC6 F7 C2 retained attempt-12 audit identity mismatch")

source = BASE.read_text(encoding="utf-8")
old_root = '"RC6-2026-09-01-feasibility-attempt-12", 1)'
new_root = '"RC6-2026-09-01-feasibility-attempt-13", 1)'
if source.count(old_root) != 1:
    raise RuntimeError("RC6 F7 C2 fresh-root target is not unique")
source = source.replace(old_root, new_root)
anchor = 'source = BASE.read_text(encoding="utf-8")'
injected = anchor + '''
scene_before = '"run-rc6-fluid-consequence-scene-f7.py", 1),'
scene_after = '"run-rc6-fluid-consequence-scene-f7-c1.py", 1),'
if source.count(scene_before) != 1:
    raise RuntimeError("RC6 F7 C2 scene routing target is not unique")
source = source.replace(scene_before, scene_after)'''
if source.count(anchor) != 1:
    raise RuntimeError("RC6 F7 C2 scene injection target is not unique")
source = source.replace(anchor, injected)
exec(compile(source, str(BASE) + "#F7_C2_ATTEMPT13", "exec"), globals(), globals())
