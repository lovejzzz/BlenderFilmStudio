#!/usr/bin/env python3
"""Adapt the frozen RC6 local matrix to a signed-topology conservation screen."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-liquid-local-static-matrix.py")
EXPECTED_BASE_SHA256 = "d4f6e52197fce178114c818fbff4003fe3e1b66440de39a23c15a7990b287d66"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 particle-conservation runner base identity mismatch")


def replace_unique(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise RuntimeError(f"RC6 particle-conservation {label} target count is {count}, expected 1")
    return source.replace(before, after)


source = BASE.read_text(encoding="utf-8")
old_root = "RC6-2026-09-01-local-static-attempt-19"
new_root = "RC6-2026-09-01-particle-conservation-attempt-20"
if source.count(old_root) != 2:
    raise RuntimeError("RC6 particle-conservation root target mismatch")
source = source.replace(old_root, new_root)
source = replace_unique(source, '"scripts/run-rc6-liquid-local-static-scene.py"', '"scripts/run-rc6-liquid-component-diagnostic-scene.py"', "scene tool")
source = replace_unique(source, '"scripts/audit-rc6-liquid-local-static-matrix.py"', '"scripts/audit-rc6-liquid-particle-conservation-matrix.py"', "audit tool")
source = replace_unique(source, '"specs/ai-native-studio-rc6-liquid-local-static.v0.19.json"', '"specs/ai-native-studio-rc6-liquid-particle-conservation.v0.20.json"', "spec")
source = replace_unique(
    source,
    'CELLS = (("radius-1p0", 1.0), ("radius-1p1", 1.1), ("radius-1p2", 1.2), ("radius-1p3", 1.3))',
    'CELLS = (("sim-radius-1p0", 1.0), ("sim-radius-1p3", 1.3), ("sim-radius-1p6", 1.6), ("sim-radius-2p0", 2.0))',
    "cells",
)

old_pass = '''def cell_passes(row, thresholds):
    metrics = row["metrics"]
    return (
        metrics["maximumNonManifoldEdgeCount"] == 0
        and metrics["maximumConnectedComponentCount"] <= thresholds["maximumConnectedComponentCount"]
        and metrics["minimumLargestComponentFraction"] >= thresholds["minimumLargestComponentFraction"]
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
    )'''
new_pass = '''def signed_topology_passes(row, thresholds):
    for sample in row["samples"]:
        components = sample.get("components", [])
        positive = [item for item in components if item["signedVolumeCubicMeters"] > 1e-12]
        negative = [item for item in components if item["signedVolumeCubicMeters"] < -1e-12]
        if len(positive) != 1 or len(negative) > thresholds["maximumNegativeNestedShellCount"]:
            return False
        if any(item["nonManifoldEdgeCount"] for item in components):
            return False
        outer = positive[0]
        for inner in negative:
            if any(inner["boundsMinWorld"][axis] < outer["boundsMinWorld"][axis] - 1e-7 or inner["boundsMaxWorld"][axis] > outer["boundsMaxWorld"][axis] + 1e-7 for axis in range(3)):
                return False
            separation = sum((inner["centroidWorld"][axis] - outer["centroidWorld"][axis]) ** 2 for axis in range(3)) ** 0.5
            if separation > thresholds["maximumNestedCentroidSeparationMeters"]:
                return False
    return True


def cell_passes(row, thresholds):
    metrics = row["metrics"]
    return (
        metrics["maximumNonManifoldEdgeCount"] == 0
        and metrics["maximumAbsoluteVolumeDriftFraction"] <= thresholds["maximumAbsoluteTemporalDriftFraction"]
        and metrics["maximumAbsoluteSourceVolumeErrorFraction"] <= thresholds["maximumAbsoluteSourceVolumeErrorFraction"]
        and metrics["maximumOutsideCupInteriorPlusOneVoxelFraction"] <= thresholds["maximumOutsideCupInteriorPlusOneVoxelFraction"]
        and signed_topology_passes(row, thresholds)
    )'''
source = replace_unique(source, old_pass, new_pass, "signed topology acceptance")

old_rank = '''        ranked = sorted(results, key=lambda row: (
            row["metrics"]["maximumNonManifoldEdgeCount"] > 0,
            row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
            row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
            row["metrics"]["maximumConnectedComponentCount"],
            -row["metrics"]["minimumLargestComponentFraction"],
            row["configuration"]["particleRadius"],
        ))'''
new_rank = '''        ranked = sorted(results, key=lambda row: (
            not signed_topology_passes(row, thresholds),
            row["metrics"]["maximumAbsoluteSourceVolumeErrorFraction"],
            row["metrics"]["maximumAbsoluteVolumeDriftFraction"],
            row["configuration"]["particleRadius"],
        ))'''
source = replace_unique(source, old_rank, new_rank, "ranking")
source = source.replace("bfs.rc6LiquidLocalStatic", "bfs.rc6LiquidParticleConservation")
source = source.replace("RC6 local static", "RC6 particle conservation")
source = source.replace("RC6_LOCAL_STATIC_MATRIX=", "RC6_PARTICLE_CONSERVATION_MATRIX=")

exec(compile(source, str(BASE) + "#PARTICLE_CONSERVATION_V01", "exec"), globals(), globals())
