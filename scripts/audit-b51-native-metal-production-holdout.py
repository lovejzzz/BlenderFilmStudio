"""Independent byte-exact analyzer replay for B51-H1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_hash(commit: str, uri: str, root: Path) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    analyzer = Path(__file__).with_name("analyze-b51-native-metal-production-holdout.py")
    with tempfile.TemporaryDirectory(prefix="bfs-b51-h1-audit-") as temporary:
        replay = Path(temporary) / "results.json"
        process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--receipt", str(args.receipt), "--output", str(replay)], cwd=root, capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"analyzer replay failed: {process.stderr}")
        exact = args.results.read_bytes() == replay.read_bytes()
        result = json.loads(args.results.read_text(encoding="utf-8"))
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        frozen = []
        for name, binding in receipt["tools"].items():
            observed = git_blob_hash(receipt["toolFreezeCommit"], binding["uri"], root)
            frozen.append({"name": name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})
        frozen_match = all(item["match"] for item in frozen)
        parent_match = all(item["match"] for item in receipt["parentObservations"])
        source_match = all(item["match"] for item in [*receipt["sourceObservations"], *receipt["sourcePostObservations"]])
        passed = exact and frozen_match and parent_match and source_match and result["verdict"] == "NATIVE_METAL_PRODUCTION_HOLDOUT_SUPPORTED" and result["attacksPassed"] == len(spec["attacks"])
        audit = {"schemaVersion": "bfs.nativeMetalProductionHoldoutAudit.v0.1", "status": "PASS" if passed else "FAIL", "resultsSha256": sha256_file(args.results), "replaySha256": sha256_file(replay), "byteExactReplay": exact, "verdict": result["verdict"], "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]), "evidenceCoreHash": result["evidenceCoreHash"], "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))}, "frozenToolChecks": frozen, "frozenToolsMatch": frozen_match, "parentIdentityMatch": parent_match, "sourceIdentityMatch": source_match, "replayStdout": process.stdout.strip(), "failures": [] if passed else ["RESULT_REPLAY_OR_GATE_MISMATCH"]}
        args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"BFS_B51_H1_AUDIT {audit['status']} replay={'MATCH' if exact else 'DIFF'}", flush=True)
        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
