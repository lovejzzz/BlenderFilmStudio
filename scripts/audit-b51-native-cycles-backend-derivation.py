"""Independent byte-exact analyzer replay for B51-D1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def sha256_file(path: Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_b49_combined_hash(path: Path) -> str:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror())
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        spec = image.spec()
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        if name.endswith(".Combined"):
            pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
            metadata = {"name": "Combined", "shape": list(pixels.shape), "channels": list(spec.channelnames), "dtype": "float32-le", "order": "C"}
            header = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            return hashlib.sha256(header + pixels.tobytes(order="C")).hexdigest()
    raise RuntimeError(f"Combined pass absent: {path}")


def git_blob_hash(commit: str, uri: str, repository_root: Path) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=repository_root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyzer = Path(__file__).with_name("analyze-b51-native-cycles-backend-derivation.py")
    repository_root = args.spec.resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="bfs-b51-d1-audit-") as temporary:
        replay = Path(temporary) / "results.json"
        process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--receipt", str(args.receipt), "--output", str(replay)], capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"analyzer replay failed: {process.stderr}")
        exact = args.results.read_bytes() == replay.read_bytes()
        result = json.loads(args.results.read_text(encoding="utf-8"))
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        qemu_checks = []
        for shot in spec["shots"]:
            parent = shot["qemuCpuParent"]
            path = repository_root / parent["exrUri"]
            qemu_checks.append({
                "shotId": shot["id"], "uri": parent["exrUri"],
                "expectedExrSha256": parent["exrSha256"], "observedExrSha256": sha256_file(path),
                "expectedB49CombinedCanonicalFloat32Sha256": parent["combinedCanonicalFloat32Sha256"],
                "observedB49CombinedCanonicalFloat32Sha256": canonical_b49_combined_hash(path),
            })
        qemu_identity = all(item["expectedExrSha256"] == item["observedExrSha256"] and item["expectedB49CombinedCanonicalFloat32Sha256"] == item["observedB49CombinedCanonicalFloat32Sha256"] for item in qemu_checks)
        frozen_tool_checks = []
        for name, binding in receipt["tools"].items():
            observed = git_blob_hash(receipt["toolFreezeCommit"], binding["uri"], repository_root)
            frozen_tool_checks.append({"name": name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})
        frozen_tools_match = all(item["match"] for item in frozen_tool_checks)
        passed = exact and qemu_identity and frozen_tools_match and result["verdict"] == "NATIVE_CYCLES_BACKEND_DERIVATION_USABLE" and result["attacksPassed"] == len(spec["attacks"])
        audit = {
            "schemaVersion": "bfs.nativeCyclesBackendDerivationAudit.v0.2", "status": "PASS" if passed else "FAIL",
            "resultsSha256": sha256_file(args.results), "replaySha256": sha256_file(replay), "byteExactReplay": exact,
            "verdict": result["verdict"], "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]),
            "evidenceCoreHash": result["evidenceCoreHash"], "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(__file__)},
            "frozenToolChecks": frozen_tool_checks, "frozenToolsMatch": frozen_tools_match,
            "qemuParentChecks": qemu_checks, "qemuParentIdentityMatch": qemu_identity,
            "replayStdout": process.stdout.strip(), "failures": [] if passed else ["RESULT_REPLAY_OR_GATE_MISMATCH"],
        }
        args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"BFS_B51_D1_AUDIT {audit['status']} replay={'MATCH' if exact else 'DIFF'}", flush=True)
        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
