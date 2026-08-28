"""Export human-navigation display and mask proxies for B52-D12.9-H1."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


REASONS = {"UNREGISTERED": 0, "INVALID_CURRENT_ORACLE": 1, "INVALID_BOUNDS": 2, "INVALID_OWNER": 3, "INVALID_ALPHA": 4, "INVALID_DEPTH": 5, "VALID": 6}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined(path: Path) -> np.ndarray:
    first = oiio.ImageBuf(str(path), 0, 0)
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if str(image.spec().getattribute("oiio:subimagename") or "").endswith(".Combined"):
            return np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)
    raise RuntimeError(f"D12.9-H1 Combined pass absent: {path}")


def read(path: Path, shape, dtype):
    values = np.fromfile(path, dtype=dtype)
    if values.size != int(np.prod(shape)):
        raise RuntimeError(f"D12.9-H1 proxy shape mismatch: {path}")
    return values.reshape(shape)


def write_png(path: Path, pixels: np.ndarray):
    encoded = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], encoded.shape[2], oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec) or not writer.write_image(encoded):
        raise RuntimeError(f"D12.9-H1 cannot write PNG: {path}")
    writer.close()


def rgba(rgb):
    return np.concatenate((rgb, np.ones((*rgb.shape[:2], 1), dtype=np.float32)), axis=2)


def record(path: Path):
    return {"uri": f"public/evidence/b52-d12-9-h1/{path.name}", "sha256": sha_file(path), "bytes": path.stat().st_size}


def structural_overlay(display, reason):
    output = display * np.float32(0.13)
    palette = {
        "VALID": np.asarray([0.25, 0.96, 0.57], np.float32),
        "INVALID_CURRENT_ORACLE": np.asarray([1.0, 0.20, 0.17], np.float32),
        "INVALID_BOUNDS": np.asarray([0.23, 0.65, 1.0], np.float32),
        "INVALID_OWNER": np.asarray([1.0, 0.53, 0.16], np.float32),
        "INVALID_ALPHA": np.asarray([1.0, 0.88, 0.18], np.float32),
        "INVALID_DEPTH": np.asarray([1.0, 0.10, 0.62], np.float32),
    }
    for name, color in palette.items():
        mask = reason == REASONS[name]
        output[mask] = display[mask] * np.float32(0.20) + color * np.float32(0.80)
    return rgba(output)


def candidate_overlay(display, radius2, support_rejected, risk_rejected, accepted):
    output = display * np.float32(0.10)
    output[radius2] = display[radius2] * np.float32(0.16) + np.asarray([0.17, 0.46, 0.78], np.float32) * np.float32(0.60)
    output[support_rejected] = display[support_rejected] * np.float32(0.12) + np.asarray([1.0, 0.68, 0.08], np.float32) * np.float32(0.88)
    output[risk_rejected] = display[risk_rejected] * np.float32(0.08) + np.asarray([1.0, 0.05, 0.57], np.float32) * np.float32(0.92)
    output[accepted] = display[accepted] * np.float32(0.18) + np.asarray([0.18, 1.0, 0.58], np.float32) * np.float32(0.82)
    return rgba(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ocio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    result_path = args.experiment_root / "results.json"
    audit_path = args.experiment_root / "audit.json"
    receipt_path = args.experiment_root / "receipt.json"
    result = json.loads(result_path.read_text())
    audit = json.loads(audit_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    if result.get("verdict") != "MOTION_AWARE_CURVATURE_RISK_SAFE_BUT_COVERAGE_NOT_SUPPORTED" or audit.get("passed") is not True or receipt.get("receiptHash") != "c794bd2c79a584b6ade138d8b09d4bc516f68778c1bf8f6c6d29926424cf3fe8":
        raise RuntimeError("D12.9-H1 formal evidence not accepted for proxy export")
    config = ocio.Config.CreateFromFile(str(args.ocio))
    transform = ocio.DisplayViewTransform(src="ACEScg", display="sRGB - Display", view="ACES 2.0 - SDR 100 nits (Rec.709)")
    processor = config.getProcessor(transform).getDefaultCPUProcessor()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    names = {
        "ROTATED_SWEEP_HIGH_FREQUENCY_157X103": "rotated-sweep-high-frequency",
        "CAMERA_TRUCK_PITCH_PARALLAX_167X109": "camera-truck-pitch-parallax",
        "SAME_INDEX_DEPTH_CROSSING_179X113": "same-index-depth-crossing",
        "STATIC_FREQUENCY_CONTROL_131X89": "static-frequency-control",
    }
    measurements = {row["fixtureId"]: row for row in result["measurements"] if row["repeat"] == 1}
    artifacts = []
    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        base = names[fixture_id]
        source = args.experiment_root / "sources" / fixture_id / "R1/frame-1/source.exr"
        beauty = combined(source)
        rgb = beauty[..., :3].reshape(-1, 3)
        display = np.asarray([processor.applyRGB(row.tolist()) for row in rgb], dtype=np.float32).reshape(height, width, 3)
        beauty_path = args.output_dir / f"{base}-beauty.png"
        write_png(beauty_path, np.concatenate((display, np.clip(beauty[..., 3:4], 0, 1)), axis=2))
        artifacts.append({"id": f"{base}-beauty", "kind": "ACES_DISPLAY_PROXY", "source": {"uri": str(source), "sha256": sha_file(source)}, "output": record(beauty_path)})
        arrays = args.experiment_root / "consumers/python" / fixture_id / "R1/arrays"
        reason_path = arrays / "reason.u8"
        radius_path = arrays / "radius2-interior.u8"
        support_path = arrays / "support-rejected.u8"
        risk_path = arrays / "risk-rejected.u8"
        accepted_path = arrays / "accepted.u8"
        reason = read(reason_path, (height, width), "u1")
        radius2 = read(radius_path, (height, width), "u1").astype(bool)
        support_rejected = read(support_path, (height, width), "u1").astype(bool)
        risk_rejected = read(risk_path, (height, width), "u1").astype(bool)
        accepted = read(accepted_path, (height, width), "u1").astype(bool)
        structural_path = args.output_dir / f"{base}-structural.png"
        write_png(structural_path, structural_overlay(display, reason))
        reason_counts = {name: int((reason == code).sum()) for name, code in REASONS.items()}
        artifacts.append({
            "id": f"{base}-structural",
            "kind": "STRUCTURAL_REASON_DIAGNOSTIC",
            "legend": {"green": "valid", "blue": "invalid bounds", "orange": "invalid owner", "magenta": "invalid depth", "red": "invalid current", "yellow": "invalid alpha"},
            "source": {"uri": str(reason_path), "sha256": sha_file(reason_path)},
            "counts": reason_counts,
            "output": record(structural_path),
        })
        candidate_path = args.output_dir / f"{base}-candidate.png"
        write_png(candidate_path, candidate_overlay(display, radius2, support_rejected, risk_rejected, accepted))
        counts = {"radius2": int(radius2.sum()), "supportRejected": int(support_rejected.sum()), "riskRejected": int(risk_rejected.sum()), "accepted": int(accepted.sum())}
        artifacts.append({
            "id": f"{base}-candidate",
            "kind": "Q30_CANDIDATE_DOMAIN_DIAGNOSTIC",
            "legend": {"green": "accepted", "magenta": "risk rejected", "yellow": "support rejected", "blue": "radius-2 domain", "dark": "outside radius-2"},
            "sources": [{"uri": str(path), "sha256": sha_file(path)} for path in (radius_path, support_path, risk_path, accepted_path)],
            "counts": counts,
            "output": record(candidate_path),
        })
        measured = measurements[fixture_id]
        if measured["reasonCounts"] != reason_counts or measured["coverage"]["radius2"] != counts["radius2"] or measured["coverage"]["accepted"] != counts["accepted"] or measured["supportRejectedPixels"] != counts["supportRejected"] or measured["riskRejectedPixels"] != counts["riskRejected"]:
            raise RuntimeError(f"D12.9-H1 proxy measurement mismatch: {fixture_id}")
    manifest = {
        "schemaVersion": "bfs.b52D129H1SiteProxyManifest.v0.1",
        "decisionRole": "HUMAN_NAVIGATION_ONLY_FORMAL_DECISION_UNCHANGED",
        "experimentId": spec["experimentId"],
        "formalResult": {"uri": str(result_path), "sha256": sha_file(result_path), "evidenceHash": result["evidenceHash"], "verdict": result["verdict"]},
        "audit": {"uri": str(audit_path), "sha256": sha_file(audit_path), "auditHash": audit["auditHash"], "passed": audit["passed"]},
        "receipt": {"uri": str(receipt_path), "sha256": sha_file(receipt_path), "receiptHash": receipt["receiptHash"]},
        "sourceEncoding": "ACEScg scene-linear float32",
        "display": "sRGB - Display",
        "view": "ACES 2.0 - SDR 100 nits (Rec.709)",
        "ocio": {"uri": str(args.ocio), "sha256": sha_file(args.ocio), "name": config.getName()},
        "artifacts": artifacts,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D129_H1_SITE_PROXIES_OK count={len(artifacts)} manifest={sha_file(manifest_path)}")


if __name__ == "__main__":
    main()
