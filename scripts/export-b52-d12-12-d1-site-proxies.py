#!/usr/bin/env python3
"""Export source-bound D12.12-D1 one-sided curvature visualizations."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SCALE = 4
SELECTED_FACTOR = 1
FIXTURES = {
    "ROTATED_SWEEP_HIGH_FREQUENCY_157X103": (103, 157),
    "CAMERA_TRUCK_PITCH_PARALLAX_167X109": (109, 167),
}
COLORS = {
    "empty": np.array([11, 17, 25], dtype=np.uint8),
    "radius": np.array([42, 76, 112], dtype=np.uint8),
    "baselineAccepted": np.array([54, 174, 116], dtype=np.uint8),
    "newAccepted": np.array([244, 188, 66], dtype=np.uint8),
    "remainingRisk": np.array([202, 64, 157], dtype=np.uint8),
    "opportunityRejected": np.array([239, 78, 77], dtype=np.uint8),
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_mask(path: Path, shape: tuple[int, int]) -> np.ndarray:
    raw = path.read_bytes()
    expected = shape[0] * shape[1]
    if len(raw) != expected:
        raise RuntimeError(f"unexpected mask size for {path}: {len(raw)} != {expected}")
    return np.frombuffer(raw, dtype="u1").reshape(shape).astype(bool).copy()


def write_png(path: Path, pixels: np.ndarray) -> None:
    enlarged = np.repeat(
        np.repeat(np.ascontiguousarray(pixels, dtype=np.uint8), SCALE, axis=0),
        SCALE,
        axis=1,
    )
    spec = oiio.ImageSpec(enlarged.shape[1], enlarged.shape[0], 3, oiio.UINT8)
    writer = oiio.ImageOutput.create(str(path))
    if writer is None or not writer.open(str(path), spec):
        raise RuntimeError(oiio.geterror() or "D12.12 site proxy PNG open failed")
    if not writer.write_image(enlarged) or not writer.close():
        raise RuntimeError(oiio.geterror() or "D12.12 site proxy PNG write failed")


def result_cell(results: dict, fixture_id: str) -> dict:
    candidates = [cell for cell in results["cells"] if cell["fixtureId"] == fixture_id and cell["repeat"] == 1]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one R1 result cell for {fixture_id}")
    factors = [entry for entry in candidates[0]["factors"] if entry["factor"] == SELECTED_FACTOR]
    if len(factors) != 1:
        raise RuntimeError(f"selected factor missing from {fixture_id}")
    return factors[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-root", type=Path, required=True)
    parser.add_argument("--derivation-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise RuntimeError("refusing to overwrite D12.12 site proxies")

    results = json.loads(args.result.read_text())
    audit = json.loads(args.audit.read_text())
    if results["verdict"] != "MATERIAL_OWNER_ONE_SIDED_CURVATURE_CANDIDATE_DERIVED":
        raise RuntimeError("accepted bounded D12.12-D1 result required")
    if results["selectedInflationFactor"] != SELECTED_FACTOR or results["checkPassed"] != results["checkTotal"]:
        raise RuntimeError("mechanically selected factor 1 with all analyzer gates required")
    if audit["verdict"] != "MATERIAL_OWNER_ONE_SIDED_CURVATURE_DERIVATION_AUDIT_ACCEPTED":
        raise RuntimeError("accepted D12.12-D1 independent audit required")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    outputs = []
    fixture_counts = {}

    for fixture_id, shape in FIXTURES.items():
        parent_dir = args.parent_root / "consumers" / "python" / fixture_id / "R1" / "arrays"
        candidate_dir = args.derivation_root / "consumers" / "python" / fixture_id / "R1" / "arrays"
        paths = {
            "parentAccepted": parent_dir / "accepted.u8",
            "radius": candidate_dir / "control" / "radius2-interior.u8",
            "opportunity": candidate_dir / "control" / "localized-opportunity.u8",
            "candidateAccepted": candidate_dir / "factor-01" / "accepted.u8",
            "candidateRisk": candidate_dir / "factor-01" / "risk.q30.u32",
        }
        parent_accepted = load_mask(paths["parentAccepted"], shape)
        radius = load_mask(paths["radius"], shape)
        opportunity = load_mask(paths["opportunity"], shape)
        candidate_accepted = load_mask(paths["candidateAccepted"], shape)
        new_accepted = candidate_accepted & ~parent_accepted
        remaining = radius & ~candidate_accepted
        opportunity_rejected = opportunity & ~candidate_accepted

        if np.any(parent_accepted & ~candidate_accepted):
            raise RuntimeError(f"factor 1 removed parent accepts in {fixture_id}")
        if np.any(new_accepted & ~opportunity):
            raise RuntimeError(f"factor 1 accepted outside localized opportunities in {fixture_id}")

        expected = result_cell(results, fixture_id)
        measured = {
            "radius": int(radius.sum()),
            "parentAccepted": int(parent_accepted.sum()),
            "candidateAccepted": int(candidate_accepted.sum()),
            "localizedOpportunity": int(opportunity.sum()),
            "newAccepted": int(new_accepted.sum()),
            "remainingRisk": int(remaining.sum()),
            "opportunityRejected": int(opportunity_rejected.sum()),
        }
        if measured["radius"] != expected["radius2"]:
            raise RuntimeError(f"radius count mismatch for {fixture_id}")
        if measured["candidateAccepted"] != expected["accepted"]:
            raise RuntimeError(f"accepted count mismatch for {fixture_id}")
        if measured["localizedOpportunity"] != expected["localizedOpportunity"]:
            raise RuntimeError(f"opportunity count mismatch for {fixture_id}")
        if measured["newAccepted"] != expected["additionalAccepted"]:
            raise RuntimeError(f"new accepted count mismatch for {fixture_id}")

        pixels = np.broadcast_to(COLORS["empty"], (*shape, 3)).copy()
        pixels[radius] = COLORS["radius"]
        pixels[remaining] = COLORS["remainingRisk"]
        pixels[parent_accepted] = COLORS["baselineAccepted"]
        pixels[new_accepted] = COLORS["newAccepted"]
        pixels[opportunity_rejected] = COLORS["opportunityRejected"]

        filename = "sweep-one-sided-recovery.png" if fixture_id.startswith("ROTATED") else "parallax-one-sided-recovery.png"
        target = args.output_dir / filename
        write_png(target, pixels)
        outputs.append(
            {
                "uri": str(target),
                "sha256": sha_file(target),
                "sourceUris": [str(path) for path in paths.values()],
                "sourceSha256": [sha_file(path) for path in paths.values()],
                "nearestScale": SCALE,
                "fixtureId": fixture_id,
            }
        )
        fixture_counts[fixture_id] = measured

    body = {
        "schemaVersion": "bfs.blenderMaterialOwnerOneSidedCurvatureSiteProxyManifest.v0.1",
        "classification": "SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE",
        "selectedInflationFactor": SELECTED_FACTOR,
        "formalResult": {
            "uri": str(args.result),
            "sha256": sha_file(args.result),
            "resultHash": results["resultHash"],
        },
        "independentAudit": {
            "uri": str(args.audit),
            "sha256": sha_file(args.audit),
            "auditHash": audit["auditHash"],
        },
        "fixtureCounts": fixture_counts,
        "mapping": {name: value.astype(int).tolist() for name, value in COLORS.items()},
        "outputs": outputs,
        "nonClaims": [
            "Colors are explanatory categorical mappings, not Blender display transforms.",
            "Nearest-neighbor enlargement preserves source samples but adds no evidence beyond the bound raw payloads.",
            "These post-hoc visualizations do not replace a fresh Blender 5.2 holdout.",
        ],
    }
    body["manifestHash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        "BFS_B52_D1212_D1_SITE_PROXIES "
        f"outputs={len(outputs)} factor={SELECTED_FACTOR} hash={body['manifestHash']}"
    )


if __name__ == "__main__":
    main()
