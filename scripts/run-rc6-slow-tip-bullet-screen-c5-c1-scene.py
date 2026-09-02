#!/usr/bin/env python3
"""C5-C1 sentinel correction for the removed legacy separation metric."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-slow-tip-bullet-screen-c5-scene.py")
EXPECTED_BASE_SHA256 = "270e163dcd9b596bde4cacb3b5e520410b692fd613eb97dc590d3a49e19ebda2"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("slow-tip C5-C1 scene base identity mismatch")

source = BASE.read_text(encoding="utf-8")
before = "'    hinge_pivot_drift = (cup.matrix_world @ hinge_pivot_cup_local - hinge_pivot_world).length',"
after = "'    hinge_pivot_drift = (cup.matrix_world @ hinge_pivot_cup_local - hinge_pivot_world).length\\n    separation = math.inf',"
if source.count(before) != 1:
    raise RuntimeError("slow-tip C5-C1 separation sentinel target mismatch")
source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C5_C1_SEPARATION_SENTINEL", "exec"), globals(), globals())
