#!/usr/bin/env python3
"""Export source-bound D12.11 owner/acceptance visualizations for the research site."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SCALE = 4
CRITICAL = "SAME_INDEX_DEPTH_CROSSING_179X113"
SWEEP = "ROTATED_SWEEP_HIGH_FREQUENCY_157X103"
COLORS = {
    "empty": np.array([12, 18, 26], dtype=np.uint8),
    "shared": np.array([91, 103, 116], dtype=np.uint8),
    "background": np.array([32, 93, 128], dtype=np.uint8),
    "foreground": np.array([241, 124, 64], dtype=np.uint8),
    "accepted": np.array([68, 184, 118], dtype=np.uint8),
    "removed": np.array([245, 187, 66], dtype=np.uint8),
    "alias": np.array([238, 66, 91], dtype=np.uint8),
    "radius": np.array([50, 91, 132], dtype=np.uint8),
    "support": np.array([245, 187, 66], dtype=np.uint8),
    "risk": np.array([207, 70, 163], dtype=np.uint8),
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_png(path: Path, pixels: np.ndarray) -> None:
    enlarged = np.repeat(np.repeat(np.ascontiguousarray(pixels, dtype=np.uint8), SCALE, axis=0), SCALE, axis=1)
    spec = oiio.ImageSpec(enlarged.shape[1], enlarged.shape[0], 3, oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec) or not writer.write_image(enlarged) or not writer.close():
        raise RuntimeError(oiio.geterror() or "D12.11 site proxy PNG write failed")


def load(path: Path, shape: tuple[int, int], dtype: str = "<f4") -> np.ndarray:
    return np.frombuffer(path.read_bytes(), dtype=dtype).reshape(shape).copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--h1-root", type=Path, required=True)
    parser.add_argument("--localization-root", type=Path, required=True)
    parser.add_argument("--formal-result", type=Path, required=True)
    parser.add_argument("--adversarial-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite D12.11 site proxies")
    formal = json.loads(args.formal_result.read_text())
    adversarial = json.loads(args.adversarial_result.read_text())
    if formal["verdict"] != "MATERIAL_INDEX_OWNER_INTERVENTION_SAFE_BUT_COVERAGE_NOT_SUPPORTED" or adversarial["verdict"] != "MATERIAL_INDEX_OWNER_INTERVENTION_ADVERSARIAL_AUDIT_ACCEPTED":
        raise RuntimeError("accepted bounded D12.11 result and adversarial audit required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    outputs = []

    critical_shape = (113, 179)
    adapter = args.formal_root / "adapters" / CRITICAL / "R1" / "arrays"
    object_path = adapter / "current-object-index.f32"
    material_path = adapter / "current-owner.f32"
    object_index = load(object_path, critical_shape)
    material_index = load(material_path, critical_shape)
    object_rgb = np.broadcast_to(COLORS["empty"], (*critical_shape, 3)).copy()
    object_rgb[object_index == np.float32(14555)] = COLORS["shared"]
    material_rgb = np.broadcast_to(COLORS["empty"], (*critical_shape, 3)).copy()
    material_rgb[material_index == np.float32(21301)] = COLORS["background"]
    material_rgb[material_index == np.float32(21302)] = COLORS["foreground"]
    for filename, pixels, source in (
        ("object-index-shared.png", object_rgb, object_path),
        ("material-index-separated.png", material_rgb, material_path),
    ):
        target = args.output_dir / filename
        write_png(target, pixels)
        outputs.append({"uri": str(target), "sha256": sha_file(target), "sourceUri": str(source), "sourceSha256": sha_file(source), "nearestScale": SCALE})

    material_accepted_path = args.formal_root / "consumers/python" / CRITICAL / "R1" / "arrays/accepted.u8"
    h1_accepted_path = args.h1_root / "consumers/python" / CRITICAL / "R1" / "arrays/accepted.u8"
    truth_path = args.localization_root / "payloads" / CRITICAL / "R1" / "true-owner-bilinear.u8"
    material_accepted = load(material_accepted_path, critical_shape, "u1").astype(bool)
    h1_accepted = load(h1_accepted_path, critical_shape, "u1").astype(bool)
    truth = load(truth_path, critical_shape, "u1").astype(bool)
    registered_alias = h1_accepted & ~truth
    removed = h1_accepted & ~material_accepted
    delta_rgb = np.broadcast_to(COLORS["empty"], (*critical_shape, 3)).copy()
    delta_rgb[material_accepted] = COLORS["accepted"]
    delta_rgb[removed] = COLORS["removed"]
    delta_rgb[registered_alias] = COLORS["alias"]
    delta_target = args.output_dir / "accepted-intervention-delta.png"
    write_png(delta_target, delta_rgb)
    outputs.append({"uri": str(delta_target), "sha256": sha_file(delta_target), "sourceUris": [str(material_accepted_path), str(h1_accepted_path), str(truth_path)], "sourceSha256": [sha_file(material_accepted_path), sha_file(h1_accepted_path), sha_file(truth_path)], "nearestScale": SCALE})

    sweep_shape = (103, 157)
    sweep_dir = args.formal_root / "consumers/python" / SWEEP / "R1" / "arrays"
    radius_path, support_path, risk_path, accepted_path = (sweep_dir / name for name in ("radius2-interior.u8", "support-rejected.u8", "risk-rejected.u8", "accepted.u8"))
    radius = load(radius_path, sweep_shape, "u1").astype(bool)
    support = load(support_path, sweep_shape, "u1").astype(bool)
    risk = load(risk_path, sweep_shape, "u1").astype(bool)
    accepted = load(accepted_path, sweep_shape, "u1").astype(bool)
    coverage_rgb = np.broadcast_to(COLORS["empty"], (*sweep_shape, 3)).copy()
    coverage_rgb[radius] = COLORS["radius"]
    coverage_rgb[accepted] = COLORS["accepted"]
    coverage_rgb[support] = COLORS["support"]
    coverage_rgb[risk] = COLORS["risk"]
    coverage_target = args.output_dir / "remaining-coverage-boundary.png"
    write_png(coverage_target, coverage_rgb)
    outputs.append({"uri": str(coverage_target), "sha256": sha_file(coverage_target), "sourceUris": [str(radius_path), str(accepted_path), str(support_path), str(risk_path)], "sourceSha256": [sha_file(radius_path), sha_file(accepted_path), sha_file(support_path), sha_file(risk_path)], "nearestScale": SCALE})

    body = {
        "schemaVersion": "bfs.blenderMaterialIndexOwnerIntegrationSiteProxyManifest.v0.1",
        "classification": "SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE",
        "formalResult": {"uri": str(args.formal_result), "sha256": sha_file(args.formal_result), "evidenceHash": formal["evidenceHash"]},
        "adversarialResult": {"uri": str(args.adversarial_result), "sha256": sha_file(args.adversarial_result), "adversarialAuditHash": adversarial["adversarialAuditHash"]},
        "criticalCounts": {"h1Accepted": int(h1_accepted.sum()), "materialAccepted": int(material_accepted.sum()), "removed": int(removed.sum()), "registeredAliases": int(registered_alias.sum()), "materialAcceptedAliases": int((material_accepted & registered_alias).sum())},
        "sweepCounts": {"radius2": int(radius.sum()), "accepted": int(accepted.sum()), "supportRejected": int(support.sum()), "riskRejected": int(risk.sum())},
        "mapping": {name: value.astype(int).tolist() for name, value in COLORS.items()},
        "outputs": outputs,
        "nonClaims": ["Colors are explanatory categorical mappings, not Blender display transforms.", "Nearest-neighbor enlargement preserves source samples but adds no evidence beyond the bound raw payloads."],
    }
    body["manifestHash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    (args.output_dir / "manifest.json").write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1211_SITE_PROXIES outputs={len(outputs)} aliases={int(registered_alias.sum())}->0 hash={body['manifestHash']}")


if __name__ == "__main__":
    main()
