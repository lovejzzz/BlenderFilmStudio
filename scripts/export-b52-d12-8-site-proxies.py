"""Export non-decisional ACES display and domain proxies for D12.8-C1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio
import PyOpenColorIO as ocio


REASONS = {
    "UNREGISTERED": 0,
    "INVALID_CURRENT_ORACLE": 1,
    "INVALID_BOUNDS": 2,
    "INVALID_OWNER": 3,
    "INVALID_ALPHA": 4,
    "INVALID_DEPTH": 5,
    "VALID": 6,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def combined(path: Path) -> np.ndarray:
    first = oiio.ImageBuf(str(path), 0, 0)
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if str(image.spec().getattribute("oiio:subimagename") or "").endswith(".Combined"):
            return np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)
    raise RuntimeError(f"Combined pass absent: {path}")


def read_array(path: Path, shape: tuple[int, ...], dtype: str) -> np.ndarray:
    values = np.fromfile(path, dtype=dtype)
    if values.size != int(np.prod(shape)):
        raise RuntimeError(f"array shape mismatch: {path}")
    return values.reshape(shape)


def write_png(path: Path, pixels: np.ndarray) -> None:
    encoded = np.rint(np.clip(pixels, 0, 1) * 255).astype(np.uint8)
    spec = oiio.ImageSpec(encoded.shape[1], encoded.shape[0], encoded.shape[2], oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(f"cannot open PNG: {path}")
    if not writer.write_image(encoded):
        raise RuntimeError(writer.geterror())
    writer.close()


def output_record(path: Path) -> dict:
    return {
        "uri": f"public/evidence/b52-d12-8/{path.name}",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def rgba(rgb: np.ndarray) -> np.ndarray:
    return np.concatenate((rgb, np.ones((*rgb.shape[:2], 1), dtype=np.float32)), axis=2)


def structural_overlay(display: np.ndarray, reason: np.ndarray) -> np.ndarray:
    output = display * np.float32(0.13)
    palette = {
        "VALID": np.asarray([0.25, 0.96, 0.57], dtype=np.float32),
        "INVALID_CURRENT_ORACLE": np.asarray([1.0, 0.20, 0.17], dtype=np.float32),
        "INVALID_BOUNDS": np.asarray([0.23, 0.65, 1.0], dtype=np.float32),
        "INVALID_OWNER": np.asarray([1.0, 0.53, 0.16], dtype=np.float32),
        "INVALID_ALPHA": np.asarray([1.0, 0.88, 0.18], dtype=np.float32),
        "INVALID_DEPTH": np.asarray([1.0, 0.10, 0.62], dtype=np.float32),
    }
    for name, color in palette.items():
        mask = reason == REASONS[name]
        output[mask] = display[mask] * np.float32(0.20) + color * np.float32(0.80)
    return rgba(output)


def adaptive_overlay(display: np.ndarray, radius2: np.ndarray, adaptive: np.ndarray, rejected: np.ndarray) -> np.ndarray:
    output = display * np.float32(0.11)
    output[radius2] = display[radius2] * np.float32(0.18) + np.asarray([0.18, 0.48, 0.72], dtype=np.float32) * np.float32(0.52)
    output[adaptive] = display[adaptive] * np.float32(0.18) + np.asarray([0.30, 1.0, 0.58], dtype=np.float32) * np.float32(0.82)
    output[rejected] = display[rejected] * np.float32(0.08) + np.asarray([1.0, 0.06, 0.56], dtype=np.float32) * np.float32(0.92)
    return rgba(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ocio", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    result_path = args.experiment_root / "results.json"
    result = json.loads(result_path.read_text())
    audit_path = args.experiment_root / "audit.c2.json"
    audit = json.loads(audit_path.read_text())
    if spec.get("experimentId") != "B52-D12.8-C1" or result.get("experimentId") != "B52-D12.8-C1":
        raise RuntimeError("D12.8-C1 identity mismatch")
    if audit.get("experimentId") != "B52-D12.8-AUDIT-C2" or audit.get("passed") is not True:
        raise RuntimeError("D12.8-C2 corrected audit is not accepted")

    config = ocio.Config.CreateFromFile(str(args.ocio))
    transform = ocio.DisplayViewTransform(
        src="ACEScg",
        display="sRGB - Display",
        view="ACES 2.0 - SDR 100 nits (Rec.709)",
    )
    processor = config.getProcessor(transform).getDefaultCPUProcessor()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    names = {
        "RIGID_OBJECT_SWEEP_DISOCCLUSION_149X97": "rigid-sweep-disocclusion",
        "CAMERA_DOLLY_YAW_PARALLAX_BOUNDS_163X101": "camera-parallax-bounds",
        "SAME_INDEX_DEPTH_REVEAL_173X107": "same-index-depth-reveal",
        "MULTI_OWNER_STATIC_CONTROL_127X83": "multi-owner-static-control",
    }
    measurements = {row["fixtureId"]: row for row in result["measurements"] if row["repeat"] == 1}
    artifacts: list[dict] = []

    for fixture in spec["fixtures"]:
        fixture_id = fixture["id"]
        width, height = fixture["resolution"]
        source = args.experiment_root / "sources" / fixture_id / "R1" / "frame-1" / "source.exr"
        beauty = combined(source)
        rgb = beauty[..., :3].reshape(-1, 3)
        display = np.asarray([processor.applyRGB(row.tolist()) for row in rgb], dtype=np.float32).reshape(height, width, 3)
        alpha = np.clip(beauty[..., 3:4], 0, 1)
        base = names[fixture_id]

        beauty_output = args.output_dir / f"{base}-beauty.png"
        write_png(beauty_output, np.concatenate((display, alpha), axis=2))
        artifacts.append(
            {
                "id": f"{base}-beauty",
                "kind": "ACES_DISPLAY_PROXY",
                "source": {"uri": str(source), "sha256": sha256_file(source)},
                "output": output_record(beauty_output),
            }
        )

        arrays = args.experiment_root / "consumers" / "python" / fixture_id / "R1" / "arrays"
        reason_path = arrays / "reason.u8"
        radius2_path = arrays / "radius2-interior.u8"
        adaptive_path = arrays / "adaptive-interior.u8"
        rejected_path = arrays / "adaptive-rejected.u8"
        reason = read_array(reason_path, (height, width), "u1")
        radius2 = read_array(radius2_path, (height, width), "u1").astype(bool)
        adaptive = read_array(adaptive_path, (height, width), "u1").astype(bool)
        rejected = read_array(rejected_path, (height, width), "u1").astype(bool)

        structural_output = args.output_dir / f"{base}-structural.png"
        write_png(structural_output, structural_overlay(display, reason))
        reason_counts = {name: int((reason == code).sum()) for name, code in REASONS.items()}
        artifacts.append(
            {
                "id": f"{base}-structural",
                "kind": "STRUCTURAL_REASON_DIAGNOSTIC",
                "legend": {
                    "green": "valid history",
                    "blue": "invalid bounds",
                    "orange": "invalid owner",
                    "magenta": "invalid depth",
                    "red": "invalid current oracle",
                    "yellow": "invalid alpha",
                    "dark": "unregistered",
                },
                "source": {"uri": str(reason_path), "sha256": sha256_file(reason_path)},
                "counts": reason_counts,
                "output": output_record(structural_output),
            }
        )

        adaptive_output = args.output_dir / f"{base}-adaptive.png"
        write_png(adaptive_output, adaptive_overlay(display, radius2, adaptive, rejected))
        artifacts.append(
            {
                "id": f"{base}-adaptive",
                "kind": "ADAPTIVE_DOMAIN_DIAGNOSTIC",
                "legend": {
                    "green": "adaptive accepted",
                    "magenta": "risk rejected from radius 2",
                    "blue": "radius-2 domain",
                    "dark": "outside radius-2 domain",
                },
                "sources": [
                    {"uri": str(path), "sha256": sha256_file(path)}
                    for path in (radius2_path, adaptive_path, rejected_path)
                ],
                "counts": {
                    "radius2": int(radius2.sum()),
                    "adaptive": int(adaptive.sum()),
                    "rejected": int(rejected.sum()),
                },
                "output": output_record(adaptive_output),
            }
        )

        measured = measurements[fixture_id]
        if measured["reasonCounts"] != reason_counts:
            raise RuntimeError(f"D12.8 reason-count mismatch: {fixture_id}")
        if measured["coverage"]["radius2"] != int(radius2.sum()):
            raise RuntimeError(f"D12.8 radius-2 count mismatch: {fixture_id}")
        if measured["coverage"]["adaptive"] != int(adaptive.sum()):
            raise RuntimeError(f"D12.8 adaptive count mismatch: {fixture_id}")
        if measured["adaptiveRejectedPixels"] != int(rejected.sum()):
            raise RuntimeError(f"D12.8 rejected count mismatch: {fixture_id}")

    manifest = {
        "schemaVersion": "bfs.b52D128SiteProxyManifest.v0.1",
        "decisionRole": "HUMAN_NAVIGATION_ONLY_FORMAL_DECISION_UNCHANGED",
        "experimentId": spec["experimentId"],
        "formalResult": {
            "uri": str(result_path),
            "sha256": sha256_file(result_path),
            "evidenceHash": result["evidenceHash"],
            "verdict": result["verdict"],
        },
        "correctedAudit": {
            "uri": str(audit_path),
            "sha256": sha256_file(audit_path),
            "auditHash": audit["auditHash"],
        },
        "sourceEncoding": "ACEScg scene-linear float32",
        "display": "sRGB - Display",
        "view": "ACES 2.0 - SDR 100 nits (Rec.709)",
        "ocio": {"uri": str(args.ocio), "sha256": sha256_file(args.ocio), "name": config.getName()},
        "artifacts": artifacts,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"BFS_B52_D128_SITE_PROXIES_OK count={len(artifacts)} manifest={sha256_file(manifest_path)}")


if __name__ == "__main__":
    main()
