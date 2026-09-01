#!/usr/bin/env python3
"""RC6 F4 adapter: exact-match calibrated collision plus pre-contact containment."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene-f3.py")
EXPECTED_BASE_SHA256 = "0d7c8603e555d2affeff4e08492630ba4a79244251823676c3c5305a2e9703d8"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F4 base scene adapter identity mismatch")

source = BASE.read_text(encoding="utf-8")
anchor = 'exec(compile(source, str(BASE) + "#F3_CALIBRATED_CAUSE_AND_BOUNDED_FLUID", "exec"), globals(), globals())'
injected = '''f4_replacements = (
    ('rigid_body(cup, "ACTIVE", mass=0.34, shape="CONVEX_HULL", friction=0.75, restitution=0.05)', 'rigid_body(cup, "ACTIVE", mass=0.34, shape="CYLINDER", friction=0.75, restitution=0.05)', "exact collision proxy"),
    ('bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.07, depth=0.16, location=(0.32, 0, 0.15))', 'bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.055, depth=0.14, location=(0.32, 0, 0.145))', "smaller liquid source"),
    ('    initial_fluid = fluid_samples[0]\n    maximum_spread = max(row["floorSpreadMeters"] for row in fluid_samples)', '    initial_fluid = fluid_samples[0]\n    precontact_maximum_outside = max(row["outsideCupFraction"] for row in fluid_samples if row["frame"] < contact_frame) if contact_frame > 1 else initial_fluid["outsideCupFraction"]\n    maximum_spread = max(row["floorSpreadMeters"] for row in fluid_samples)', "pre-contact metric"),
    ('        "initialContainment": initial_fluid["outsideCupFraction"] <= 0.05,', '        "initialContainment": initial_fluid["outsideCupFraction"] <= 0.05,\n        "preContactContainment": precontact_maximum_outside <= 0.05,', "pre-contact gate"),
    ('                "initialVertexCount": initial_fluid["vertexCount"],', '                "initialVertexCount": initial_fluid["vertexCount"],\n                "preContactMaximumOutsideCupFraction": round(precontact_maximum_outside, 8),', "pre-contact receipt"),
)
for before, after, label in f4_replacements:
    if source.count(before) != 1:
        raise RuntimeError(f"RC6 F4 {label} target is not unique")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F4_EXACT_PROXY_AND_PRECONTACT_CONTAINMENT", "exec"), globals(), globals())'''
if source.count(anchor) != 1:
    raise RuntimeError("RC6 F4 execution anchor is not unique")
source = source.replace(anchor, injected)
exec(compile(source, str(BASE) + "#F4_ADAPTER", "exec"), globals(), globals())
