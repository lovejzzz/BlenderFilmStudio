"""Independent artifact and byte-exact replay audit for B51-D3."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_hash(commit: str, uri: str, root: Path) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--output-root", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    root = args.spec.resolve().parent.parent; original = args.output_root.resolve(); result = json.loads((original / "results.json").read_text(encoding="utf-8")); receipt = json.loads((original / "localization.receipt.json").read_text(encoding="utf-8")); spec = json.loads(args.spec.read_text(encoding="utf-8")); analyzer = Path(__file__).with_name("analyze-b51-native-metal-pass-localization.py")
    with tempfile.TemporaryDirectory(prefix="bfs-b51-d3-audit-") as temporary:
        replay = Path(temporary) / "replay"
        process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--output-root", str(replay), "--replay-receipt", str(original / "localization.receipt.json")], cwd=root, capture_output=True, text=True, check=False)
        if process.returncode: raise RuntimeError(f"B51-D3 analyzer replay failed: {process.stderr}")
        names = ["localization.receipt.json", "results.json", *[item["uri"] for item in result["diagnosticArtifacts"]]]
        comparisons = [{"uri": name, "originalSha256": sha256_file(original / name), "replaySha256": sha256_file(replay / name), "byteExact": (original / name).read_bytes() == (replay / name).read_bytes()} for name in names]
        frozen = []
        for name, binding in receipt["tools"].items():
            observed = git_blob_hash(receipt["toolFreezeCommit"], binding["uri"], root); frozen.append({"name": name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})
        passed = all(item["byteExact"] for item in comparisons) and all(item["match"] for item in frozen) and result["verdict"] == "METAL_PASS_LOCALIZATION_USABLE" and result["attacksPassed"] == len(spec["attacks"])
        audit = {"schemaVersion": "bfs.nativeMetalPassLocalizationAudit.v0.1", "status": "PASS" if passed else "FAIL", "verdict": result["verdict"], "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]), "evidenceCoreHash": result["evidenceCoreHash"], "artifactReplay": comparisons, "allArtifactsByteExact": all(item["byteExact"] for item in comparisons), "frozenToolChecks": frozen, "frozenToolsMatch": all(item["match"] for item in frozen), "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))}, "replayStdout": process.stdout.strip(), "failures": [] if passed else ["REPLAY_OR_GATE_MISMATCH"]}
        args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"BFS_B51_D3_AUDIT {audit['status']} artifacts={sum(item['byteExact'] for item in comparisons)}/{len(comparisons)}", flush=True)
        if not passed: raise SystemExit(1)


if __name__ == "__main__": main()
