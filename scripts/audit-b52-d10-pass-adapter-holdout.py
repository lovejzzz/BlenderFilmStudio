#!/usr/bin/env python3
"""Independent artifact and array replay audit for B52-D10."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


SPEC_SHA256 = "147338ae39b9c025a8f2a4921da55b15f8c16f339f34c711502dc3c94ca03566"
FILES = {
    "previousRgba": "previous.rgba32",
    "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32",
    "currentDepth": "current-depth.f32",
    "previousLayer": "previous-layer.f32",
    "currentLayer": "current-layer.f32",
    "motion": "motion.xy32",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def array_bytes(value: np.ndarray) -> bytes:
    return np.ascontiguousarray(value, dtype="<f4").tobytes(order="C")


def load_multipart(path: Path) -> dict[str, np.ndarray]:
    first = oiio.ImageBuf(str(path), 0, 0)
    parts = {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        name = str(image.spec().getattribute("oiio:subimagename") or index)
        parts[name] = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
    return parts


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--formal-root", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if args.output.exists():
        raise RuntimeError("refusing to overwrite D10 audit")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    result_path = args.formal_root / "results.json"
    receipt_path = args.formal_root / "run.receipt.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result_body = {key: value for key, value in result.items() if key != "resultHash"}
    receipt_body = {key: value for key, value in receipt.items() if key != "receiptHash"}
    result_self = result.get("resultHash") == canonical_hash(result_body)
    receipt_self = receipt.get("receiptHash") == canonical_hash(receipt_body)

    parent_match = all(sha256_file(Path(value["uri"])) == value["sha256"] for value in spec["parents"].values())
    tool_match = all(sha256_file(Path(item["uri"])) == item["currentSha256"] for item in preflight["frozenTools"])
    source_artifacts = []
    source_map = {}
    for record in receipt["sourceRuns"]:
        exr, report = Path(record["exrUri"]), Path(record["reportUri"])
        passed = exr.is_file() and report.is_file() and sha256_file(exr) == record["exrSha256"] and sha256_file(report) == record["reportSha256"]
        source_artifacts.append({"cellId": record["cellId"], "passed": passed})
        source_map[(record["fixtureId"], record["frame"], record["repeat"])] = load_multipart(exr)

    adapter_replay = []
    for record in receipt["adapterRuns"]:
        fixture, repeat = record["fixtureId"], record["repeat"]
        previous = source_map[(fixture, 0, repeat)]
        current = source_map[(fixture, 1, repeat)]
        expected = {
            "previousRgba": previous["BFS_MASTER.Combined"],
            "currentRgba": current["BFS_MASTER.Combined"],
            "previousDepth": previous["BFS_MASTER.Depth"][..., 0],
            "currentDepth": current["BFS_MASTER.Depth"][..., 0],
            "previousLayer": previous["BFS_MASTER.Object Index"][..., 0],
            "currentLayer": current["BFS_MASTER.Object Index"][..., 0],
            "motion": np.negative(current["BFS_MASTER.Vector"][..., :2], dtype=np.float32),
        }
        arrays = {}
        for name, filename in FILES.items():
            actual = (Path(record["arraysUri"]) / filename).read_bytes()
            wanted = array_bytes(expected[name])
            arrays[name] = {"actualSha256": sha256_bytes(actual), "expectedSha256": sha256_bytes(wanted), "exact": actual == wanted}
        adapter_replay.append({"cellId": record["cellId"], "arrays": arrays, "passed": all(item["exact"] for item in arrays.values())})

    diagnostics = []
    for item in result["diagnostics"]:
        png, sidecar = Path(item["pngUri"]), Path(item["sidecarUri"])
        image = oiio.ImageBuf(str(png))
        decoded = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.UINT8), dtype=np.uint8))
        passed = bool(png.is_file() and sidecar.is_file() and sha256_file(png) == item["pngSha256"] and sha256_file(sidecar) == item["sidecarSha256"] and sha256_bytes(decoded.tobytes()) == item["decodedPixelSha256"] and item["reopenExact"])
        diagnostics.append({"fixtureId": item["fixtureId"], "kind": item["kind"], "passed": passed})

    attacks = result["attackAudit"]
    attacks_ok = len(attacks) == len(spec["attacks"]) and [item["id"] for item in attacks] == spec["attacks"] and all(item["passed"] and item["expectedReason"] == item["observedReason"] == item["id"] for item in attacks)
    counts_ok = result["operationCounts"] == {"sourceBlenderProcesses": 12, "sourceRenderCalls": 12, "cyclesRayRenders": 12, "adapterPythonProcesses": 6, "analysisPythonProcesses": 1, "totalChildProcesses": 19, "uniqueChildPids": 19, "sourceBlendFilesOpened": 0, "externalAssetsOpened": 0}
    passed = all([
        sha256_file(args.spec) == SPEC_SHA256,
        preflight.get("status") == "ACCEPTED",
        result_self,
        receipt_self,
        parent_match,
        tool_match,
        result["verdict"] == spec["decisionRule"]["passVerdict"],
        result["baseFailure"] is None,
        all(result["checks"].values()),
        all(item["passed"] for item in source_artifacts),
        all(item["passed"] for item in adapter_replay),
        len(diagnostics) == spec["diagnostics"]["expectedPngs"],
        all(item["passed"] for item in diagnostics),
        attacks_ok,
        counts_ok,
    ])
    body = {
        "schemaVersion": "bfs.blenderMultipartTemporalAdapterAudit.v0.1",
        "experimentId": spec["experimentId"],
        "status": "PASS" if passed else "FAIL",
        "pid": os.getpid(),
        "specSha256": sha256_file(args.spec),
        "preflightSha256": sha256_file(args.preflight),
        "receiptSha256": sha256_file(receipt_path),
        "resultSha256": sha256_file(result_path),
        "resultSelfHashPassed": result_self,
        "receiptSelfHashPassed": receipt_self,
        "parentsPassed": parent_match,
        "frozenToolsPassed": tool_match,
        "sourceArtifacts": source_artifacts,
        "adapterReplay": adapter_replay,
        "diagnostics": diagnostics,
        "attackReplay": {"passed": attacks_ok, "count": len(attacks)},
        "operationBoundaryPassed": counts_ok,
        "runtime": {"python": sys.version.split()[0], "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__},
    }
    audit = {**body, "auditHash": canonical_hash(body)}
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B52_D10_AUDIT status={audit['status']} sources={sum(item['passed'] for item in source_artifacts)}/12 adapters={sum(item['passed'] for item in adapter_replay)}/6 diagnostics={sum(item['passed'] for item in diagnostics)}/12 attacks={len(attacks)} output={sha256_file(args.output)}")
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
