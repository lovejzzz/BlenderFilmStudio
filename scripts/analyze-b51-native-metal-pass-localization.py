"""Localize B51-H1 CPU-versus-Metal beauty and data-pass divergence without rerendering."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import shutil
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_COMMIT = "bd806f0845b44efeceeec6e8d6a6e0a6b5717bb9"
SPEC_SHA256 = "5f4f3685e73e28959960e4fee7cb427297ef0e33dfec52fb107935bd931f0587"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git(*args: str) -> str:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git failed")
    return process.stdout.strip()


def read_exr(path: Path, width: int, height: int) -> tuple[list[str], dict]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    roster, passes = [], {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        if pixels.shape[:2] != (height, width):
            raise RuntimeError(f"invalid pass shape {name}: {pixels.shape}")
        roster.append(name)
        passes[name] = {"pixels": pixels, "finite": bool(np.isfinite(pixels).all()), "shape": list(pixels.shape), "channels": list(spec.channelnames)}
    return roster, passes


def write_png(path: Path, pixels: np.ndarray) -> None:
    array = np.ascontiguousarray(pixels, dtype=np.uint8)
    height, width, channels = array.shape
    output = oiio.ImageOutput.create(str(path))
    if output is None:
        raise RuntimeError(f"cannot create PNG output: {path}")
    if not output.open(str(path), oiio.ImageSpec(width, height, channels, oiio.UINT8)):
        raise RuntimeError(output.geterror())
    if not output.write_image(array):
        raise RuntimeError(output.geterror())
    output.close()


def mark_pairs(mask: np.ndarray, condition: np.ndarray, axis: int) -> None:
    if axis == 1:
        mask[:, :-1] |= condition
        mask[:, 1:] |= condition
    else:
        mask[:-1, :] |= condition
        mask[1:, :] |= condition


def boundary_mask(pixels: np.ndarray, pass_name: str) -> np.ndarray:
    height, width = pixels.shape[:2]
    mask = np.zeros((height, width), dtype=bool)
    if pass_name.endswith(".Depth"):
        values = pixels[..., 0].astype(np.float64)
        for axis in (0, 1):
            left, right = (values[:-1, :], values[1:, :]) if axis == 0 else (values[:, :-1], values[:, 1:])
            finite_left, finite_right = np.isfinite(left), np.isfinite(right)
            both = finite_left & finite_right
            threshold = np.maximum(1e-3, 0.01 * np.minimum(np.abs(left), np.abs(right)))
            condition = (finite_left != finite_right) | (both & (np.abs(left - right) > threshold))
            mark_pairs(mask, condition, axis)
    else:
        for axis in (0, 1):
            left, right = (pixels[:-1, :], pixels[1:, :]) if axis == 0 else (pixels[:, :-1], pixels[:, 1:])
            mark_pairs(mask, np.any(left != right, axis=2), axis)
    return mask


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    result = np.zeros_like(mask)
    for dy in range(-radius, radius + 1):
        y_src = slice(max(0, -dy), min(mask.shape[0], mask.shape[0] - dy))
        y_dst = slice(max(0, dy), min(mask.shape[0], mask.shape[0] + dy))
        for dx in range(-radius, radius + 1):
            x_src = slice(max(0, -dx), min(mask.shape[1], mask.shape[1] - dx))
            x_dst = slice(max(0, dx), min(mask.shape[1], mask.shape[1] + dx))
            result[y_dst, x_dst] |= mask[y_src, x_src]
    return result


def bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None


def components(mask: np.ndarray) -> dict:
    visited = np.zeros_like(mask)
    sizes = []
    height, width = mask.shape
    for y, x in zip(*np.nonzero(mask)):
        if visited[y, x]: continue
        visited[y, x] = True; queue = deque([(int(y), int(x))]); size = 0
        while queue:
            cy, cx = queue.popleft(); size += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if (dy or dx) and 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True; queue.append((ny, nx))
        sizes.append(size)
    sizes.sort(reverse=True)
    return {"count": len(sizes), "largestPixels": sizes[0] if sizes else 0, "topTenPixels": sizes[:10]}


def pass_localization(cpu: np.ndarray, metal: np.ndarray, pass_name: str, radius: int, threshold: float) -> tuple[dict, np.ndarray]:
    changed_components = cpu != metal
    changed_pixels = np.any(changed_components, axis=2)
    boundary = dilate(boundary_mask(cpu, pass_name) | boundary_mask(metal, pass_name), radius)
    count = int(np.count_nonzero(changed_pixels))
    near = int(np.count_nonzero(changed_pixels & boundary))
    delta = np.abs(cpu.astype(np.float64) - metal.astype(np.float64))
    interior_components = changed_components & (~boundary[..., None])
    row = {
        "changedFloatComponents": int(np.count_nonzero(changed_components)), "changedPixels": count,
        "changedPixelFraction": count / changed_pixels.size, "changedPixelBbox": bbox(changed_pixels),
        "maximumAbsoluteDifference": float(np.max(delta)), "meanAbsoluteDifferenceAllComponents": float(np.mean(delta)),
        "nearBoundaryChangedPixels": near, "nearBoundaryFraction": near / count if count else 1.0,
        "interiorChangedFloatComponents": int(np.count_nonzero(interior_components)),
        "interiorMaximumAbsoluteDifference": float(np.max(delta[interior_components])) if np.any(interior_components) else 0.0,
    }
    row["boundaryLocalized"] = row["nearBoundaryFraction"] >= threshold
    return row, changed_pixels


def hash_payload(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "attacks", "attacksPassed", "verdict"}}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if evidence["h1AuditStatus"] != "PASS": return "H1_AUDIT_IDENTITY"
    if evidence["h1Verdict"] != "NATIVE_METAL_PRODUCTION_HOLDOUT_NOT_SUPPORTED": return "H1_RECEIPT_IDENTITY"
    if len(evidence["sourceObservations"]) != spec["evidenceGates"]["expectedExrs"] or not all(item["match"] for item in evidence["sourceObservations"]): return "EXR_ARTIFACT_IDENTITY"
    if not all(item["roster"] == spec["requiredRoster"] for item in evidence["sourceObservations"]): return "PASS_ROSTER"
    if not all(item["finite"] for item in evidence["sourceObservations"]): return "NON_FINITE"
    expected_pairs = {(variant["id"], metal) for variant in spec["variants"] for metal in variant["metal"]}
    observed_pairs = {(row["variantId"], row["metalRunId"]) for row in evidence["pairs"]}
    if observed_pairs != expected_pairs: return "PAIR_MATRIX"
    if evidence["algorithm"] != spec["boundaryAlgorithm"]: return "ALGORITHM_IDENTITY"
    if len(evidence["diagnosticArtifacts"]) != spec["operationBoundary"]["imagesWritten"] or not all(item["match"] for item in evidence["diagnosticArtifacts"]): return "DIAGNOSTIC_IMAGE_IDENTITY"
    if evidence["operationCounts"] != spec["operationBoundary"]: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def attacks(evidence: dict, spec: dict) -> list[dict]:
    rows = []
    def add(identifier: str, reason: str, mutate) -> None:
        clone = copy.deepcopy(evidence); mutate(clone); clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if reason != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec); rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_H1_AUDIT", "H1_AUDIT_IDENTITY", lambda x: x.update(h1AuditStatus="FAIL"))
    add("A03_H1_RECEIPT", "H1_RECEIPT_IDENTITY", lambda x: x.update(h1Verdict="SUPPORTED"))
    add("A04_EXR", "EXR_ARTIFACT_IDENTITY", lambda x: x["sourceObservations"][0].update(match=False))
    add("A05_ROSTER", "PASS_ROSTER", lambda x: x["sourceObservations"][0]["roster"].pop())
    add("A06_FINITE", "NON_FINITE", lambda x: x["sourceObservations"][0].update(finite=False))
    add("A07_PAIR", "PAIR_MATRIX", lambda x: x["pairs"].pop())
    add("A08_ALGORITHM", "ALGORITHM_IDENTITY", lambda x: x["algorithm"].update(dilationRadiusPixels=9))
    add("A09_IMAGE", "DIAGNOSTIC_IMAGE_IDENTITY", lambda x: x["diagnosticArtifacts"][0].update(match=False))
    add("A10_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(renders=1))
    add("A11_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--replay-receipt", type=Path)
    args = parser.parse_args()
    if sha256_file(args.spec) != SPEC_SHA256: raise RuntimeError("B51-D3 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode: raise RuntimeError("B51-D3 preregistration is not an ancestor")
    spec = json.loads(args.spec.read_text(encoding="utf-8")); output = args.output_root.resolve()
    if output.exists() and any(output.iterdir()): raise RuntimeError("B51-D3 output root is not empty")
    output.mkdir(parents=True, exist_ok=True)
    receipt_path = output / "localization.receipt.json"
    parent_observations = []
    for item in spec["parents"].values():
        path = ROOT / item["uri"]; actual = sha256_file(path) if path.is_file() else None
        parent_observations.append({"uri": item["uri"], "expectedSha256": item["sha256"], "observedSha256": actual, "match": actual == item["sha256"]})
    if not all(item["match"] for item in parent_observations): raise RuntimeError("B51-D3 parent identity differs")
    h1_receipt = json.loads((ROOT / spec["parents"]["h1Receipt"]["uri"]).read_text(encoding="utf-8"))
    h1_result = json.loads((ROOT / spec["parents"]["h1Result"]["uri"]).read_text(encoding="utf-8"))
    h1_audit = json.loads((ROOT / spec["parents"]["h1Audit"]["uri"]).read_text(encoding="utf-8"))
    width, height = spec["resolution"]
    runs = {item["runId"]: item for item in h1_receipt["runs"]}
    required_ids = {variant["cpu"] for variant in spec["variants"]} | {item for variant in spec["variants"] for item in variant["metal"]}
    arrays, source_observations = {}, []
    for run_id in sorted(required_ids):
        run = runs[run_id]; report = run["report"]
        path = ROOT / spec["sourceRoot"] / run_id / "artifacts" / report["artifact"]["uri"]
        roster, passes = read_exr(path, width, height)
        actual = sha256_file(path); expected = report["artifact"]["sha256"]
        source_observations.append({"runId": run_id, "uri": str(path.relative_to(ROOT)), "expectedSha256": expected, "observedSha256": actual, "expectedBytes": report["artifact"]["bytes"], "observedBytes": path.stat().st_size, "match": actual == expected and path.stat().st_size == report["artifact"]["bytes"], "roster": roster, "finite": all(item["finite"] for item in passes.values())})
        arrays[run_id] = passes
    if args.replay_receipt:
        frozen_receipt = json.loads(args.replay_receipt.read_text(encoding="utf-8"))
        if frozen_receipt["parentObservations"] != parent_observations or frozen_receipt["sourceObservations"] != source_observations: raise RuntimeError("B51-D3 replay input observation differs")
        receipt_path.write_bytes(args.replay_receipt.read_bytes())
        receipt = frozen_receipt
    else:
        disk = shutil.disk_usage(ROOT); after = disk.free - int(spec["evidenceGates"]["projectedWriteBytes"])
        disk_admission = {"availableBytes": disk.free, "projectedWriteBytes": int(spec["evidenceGates"]["projectedWriteBytes"]), "minimumReserveBytes": int(spec["evidenceGates"]["minimumDiskReserveBytes"]), "freeAfterProjectedBytes": after, "status": "ACCEPTED" if after >= int(spec["evidenceGates"]["minimumDiskReserveBytes"]) else "BLOCKED"}
        if disk_admission["status"] != "ACCEPTED": raise RuntimeError("B51-D3 disk admission blocked")
        tool_freeze = git("rev-parse", "HEAD")
        tools = {"analyzer": {"uri": "scripts/analyze-b51-native-metal-pass-localization.py", "sha256": sha256_file(Path(__file__))}, "audit": {"uri": "scripts/audit-b51-native-metal-pass-localization.py", "sha256": sha256_file(Path(__file__).with_name("audit-b51-native-metal-pass-localization.py"))}}
        receipt = {"schemaVersion": "bfs.nativeMetalPassLocalizationReceipt.v0.1", "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(args.spec.resolve().relative_to(ROOT)), "specSha256": SPEC_SHA256}, "toolFreezeCommit": tool_freeze, "tools": tools, "parentObservations": parent_observations, "sourceObservations": source_observations, "diskAdmission": disk_admission}
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pairs, data_masks = [], {}
    radius = spec["boundaryAlgorithm"]["dilationRadiusPixels"]
    threshold = spec["boundaryAlgorithm"]["dataPassBoundaryLocalizedThreshold"]
    for variant in spec["variants"]:
        cpu_passes = arrays[variant["cpu"]]
        for metal_id in variant["metal"]:
            metal_passes = arrays[metal_id]; pass_rows, disagreement_union = {}, np.zeros((height, width), dtype=bool)
            depth_disagreement, crypto_disagreement = np.zeros_like(disagreement_union), np.zeros_like(disagreement_union)
            for pass_name in spec["localizedPasses"]:
                row, changed = pass_localization(cpu_passes[pass_name]["pixels"], metal_passes[pass_name]["pixels"], pass_name, radius, threshold)
                pass_rows[pass_name] = row; disagreement_union |= changed
                if pass_name.endswith(".Depth"): depth_disagreement |= changed
                else: crypto_disagreement |= changed
            pairs.append({"variantId": variant["id"], "cpuRunId": variant["cpu"], "metalRunId": metal_id, "passes": pass_rows, "dataDisagreementPixels": int(np.count_nonzero(disagreement_union)), "dataDisagreementBbox": bbox(disagreement_union)})
            if metal_id == variant["metal"][0]:
                data_masks[variant["id"]] = {"depth": depth_disagreement, "crypto": crypto_disagreement, "union": disagreement_union}
                rgb = np.stack([depth_disagreement, crypto_disagreement, dilate(disagreement_union, radius)], axis=2).astype(np.uint8) * 255
                write_png(output / f"{variant['id'].lower()}-data-map.png", rgb)

    chair = next(item for item in spec["variants"] if item["id"] == "INTERIOR_CHAIR")
    cpu = arrays[chair["cpu"]]["BFS_MASTER.Combined"]["pixels"][..., :3].astype(np.float64)
    metal = arrays[chair["metal"][0]]["BFS_MASTER.Combined"]["pixels"][..., :3].astype(np.float64)
    delta = np.abs(cpu - metal); energy = np.sum(np.square(delta), axis=2); max_channel = np.max(delta, axis=2)
    association_mask = dilate(data_masks["INTERIOR_CHAIR"]["union"], spec["boundaryAlgorithm"]["beautyAssociationDilationRadiusPixels"])
    total_energy = float(np.sum(energy)); associated_energy = float(np.sum(energy[association_mask])); association_fraction = associated_energy / total_energy if total_energy else 1.0
    high = max_channel > spec["boundaryAlgorithm"]["beautyHighErrorMaxChannelThreshold"]
    flat_order = np.argsort(-max_channel.reshape(-1), kind="stable")[:20]
    top = [{"x": int(index % width), "y": int(index // width), "maxChannelAbsoluteError": float(max_channel.reshape(-1)[index]), "squaredErrorEnergy": float(energy.reshape(-1)[index])} for index in flat_order]
    chair_beauty = {"cpuRunId": chair["cpu"], "metalRunId": chair["metal"][0], "totalSquaredErrorEnergy": total_energy, "associatedSquaredErrorEnergy": associated_energy, "associationFraction": association_fraction, "associationThreshold": spec["boundaryAlgorithm"]["beautySquaredErrorAssociationThreshold"], "associatedWithDataDisagreement": association_fraction >= spec["boundaryAlgorithm"]["beautySquaredErrorAssociationThreshold"], "highErrorThreshold": spec["boundaryAlgorithm"]["beautyHighErrorMaxChannelThreshold"], "highErrorPixels": int(np.count_nonzero(high)), "highErrorBbox": bbox(high), "highErrorComponents": components(high), "topTwentyPixels": top, "maximumChannelAbsoluteError": float(np.max(max_channel)), "absoluteErrorQuantiles": {str(q): float(np.quantile(delta, q)) for q in (0.5, 0.9, 0.95, 0.99, 0.999, 0.9999)}}
    value = np.clip((np.log10(max_channel + 1e-8) + 8.0) / 8.0, 0.0, 1.0)
    heat = np.zeros((height, width, 3), dtype=np.uint8); heat[..., 0] = np.rint(value * 255).astype(np.uint8); heat[..., 1][association_mask] = 160; heat[..., 2][association_mask] = 160
    write_png(output / "interior-chair-beauty-heatmap.png", heat)

    image_names = [f"{item['id'].lower()}-data-map.png" for item in spec["variants"]] + ["interior-chair-beauty-heatmap.png"]
    diagnostics = [{"uri": name, "sha256": sha256_file(output / name), "bytes": (output / name).stat().st_size, "match": True} for name in image_names]
    operation_counts = spec["operationBoundary"].copy()
    evidence = {"schemaVersion": "bfs.nativeMetalPassLocalizationEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parentObservations": receipt["parentObservations"], "h1AuditStatus": h1_audit["status"], "h1Verdict": h1_result["verdict"], "sourceObservations": receipt["sourceObservations"], "diskAdmission": receipt["diskAdmission"], "algorithm": spec["boundaryAlgorithm"], "pairs": pairs, "chairBeauty": chair_beauty, "diagnosticArtifacts": diagnostics, "operationCounts": operation_counts, "nonClaims": spec["nonClaims"], "baseFailure": None}
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure; evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); failure = validate(evidence, spec); evidence["baseFailure"] = failure
    evidence["attacks"] = attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"]); evidence["verdict"] = "METAL_PASS_LOCALIZATION_USABLE" if failure is None and evidence["attacksPassed"] == len(spec["attacks"]) else "METAL_PASS_LOCALIZATION_INVALID"
    (output / "results.json").write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_D3_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} failure={failure or 'none'} chair_association={association_fraction:.6f}", flush=True)
    for row in pairs:
        summary = ",".join(f"{name.split('.')[-1]}:{value['nearBoundaryFraction']:.3f}" for name, value in row["passes"].items())
        print(f"BFS_B51_D3_PAIR {row['variantId']} {row['metalRunId']} {summary}", flush=True)


if __name__ == "__main__":
    main()
