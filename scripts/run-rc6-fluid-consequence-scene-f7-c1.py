#!/usr/bin/env python3
"""RC6 F7 scene C1: order unchanged quality replacements after F4 containment."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene-f7.py")
EXPECTED_BASE_SHA256 = "7d8a13ed3c157f33f1e9cd427d1818a7728312aefa32a745523e889c124c8b9c"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F7 scene C1 base identity mismatch")

source = BASE.read_text(encoding="utf-8")
anchor = 'source = BASE.read_text(encoding="utf-8")'
injected = anchor + '''
old_order_line = next((line for line in source.splitlines() if line.startswith("tuple_anchor = ")), None)
f4_source = BASE.with_name("run-rc6-fluid-consequence-scene-f4.py").read_text(encoding="utf-8")
final_f4_tuple = next((line.strip() for line in f4_source.splitlines() if "pre-contact receipt" in line), None)
if old_order_line is None or final_f4_tuple is None:
    raise RuntimeError("RC6 F7 scene C1 ordering anchors missing")
new_order_line = "tuple_anchor = " + repr(final_f4_tuple)
if source.count(old_order_line) != 1:
    raise RuntimeError("RC6 F7 scene C1 old ordering target is not unique")
source = source.replace(old_order_line, new_order_line)'''
if source.count(anchor) != 1:
    raise RuntimeError("RC6 F7 scene C1 injection target is not unique")
source = source.replace(anchor, injected)
exec(compile(source, str(BASE) + "#F7_C1_LATE_QUALITY_ORDER", "exec"), globals(), globals())
