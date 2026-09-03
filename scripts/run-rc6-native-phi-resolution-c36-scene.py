#!/usr/bin/env python3
"""Adapt exact C34 Data-only observation from Preview96 to frozen Review128."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-native-phi-c34-scene.py")
EXPECTED_BASE_SHA256 = "49eec8a0133abcf55152fefc75cecddb79e8840155ca8ab29b52643cf22905f5"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C36 exact C34 scene identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c34_scene", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("RESOLUTION = 96", "RESOLUTION = 128", "resolution constant", 1),
        ("BASE_VOXEL_METERS = 0.90 / 96.0", "BASE_VOXEL_METERS = 0.90 / 128.0", "voxel constant", 1),
        ("settings.resolution_max == 96", "settings.resolution_max == 128", "resolution check", 1),
        ('"resolutionMax": 96', '"resolutionMax": 128', "result resolution", 1),
        ('"bfs.rc6NativePhiC34SceneResult.v1"', '"bfs.rc6NativePhiResolutionC36SceneResult.v1"', "schema", 1),
        ('"exactC29PreviewConfiguration"', '"exactC29Review128Configuration"', "configuration check name", 1),
        ("RC6_NATIVE_PHI_C34_SCENE=", "RC6_NATIVE_PHI_RESOLUTION_C36_SCENE=", "marker", 1),
        ("C34 Data bake did not finish", "C36 Data bake did not finish", "bake failure", 1),
        ("C34 scene checks failed", "C36 scene checks failed", "check failure", 1),
        (
            "Exact-C29 uninterrupted Preview-96 Data-only bake with resumable native fields. No Mesh, render, physical PASS, exact mass, solver-operation cause, product default or film-quality claim.",
            "Exact-C29 physical inputs at frozen Review-128, uninterrupted Data-only with resumable native fields. No Mesh, render, physical PASS, exact mass, solver-operation cause, product default or film-quality claim.",
            "claim ceiling",
            1,
        ),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C36 {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_NATIVE_PHI_RESOLUTION_C36", "exec"), globals(), globals())
