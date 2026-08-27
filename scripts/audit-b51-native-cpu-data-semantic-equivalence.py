"""Independent frozen-tool, input-identity and byte-exact replay audit for B51-D6."""

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
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.spec.resolve().parent.parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    analyzer = root / result["tools"]["analyzer"]["uri"]

    with tempfile.TemporaryDirectory(prefix="bfs-b51-d6-audit-") as temporary:
        replay = Path(temporary) / "results.json"
        process = subprocess.run([
            sys.executable, str(analyzer), "--spec", str(args.spec), "--output", str(replay),
            "--preregistration-commit", result["preregistration"]["commit"],
            "--tool-freeze-commit", result["toolFreezeCommit"],
        ], cwd=root, capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"B51-D6 analyzer replay failed: {process.stdout}\n{process.stderr}")
        replay_exact = args.result.read_bytes() == replay.read_bytes()
        replay_observation = {"uri": str(args.result.resolve().relative_to(root)), "originalSha256": sha256_file(args.result), "replaySha256": sha256_file(replay), "byteExact": replay_exact}

    frozen_tools = []
    for name, binding in result["tools"].items():
        observed = git_blob_hash(result["toolFreezeCommit"], binding["uri"], root)
        frozen_tools.append({"name": name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})

    bound_inputs = []
    for item in result["d5BindingObservations"]:
        path = root / item["uri"]
        observed = sha256_file(path) if path.is_file() else None
        bound_inputs.append({"kind": item["name"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed, "match": observed == item["expectedSha256"]})
    artifacts = []
    for item in result["artifactObservations"]:
        path = root / item["uri"]
        observed_hash = sha256_file(path) if path.is_file() else None
        observed_bytes = path.stat().st_size if path.is_file() else None
        artifacts.append({"runId": item["runId"], "uri": item["uri"], "expectedSha256": item["expectedSha256"], "observedSha256": observed_hash, "expectedBytes": item["expectedBytes"], "observedBytes": observed_bytes, "match": observed_hash == item["expectedSha256"] and observed_bytes == item["expectedBytes"]})

    passed = (
        replay_exact
        and all(item["match"] for item in frozen_tools + bound_inputs + artifacts)
        and result["verdict"] in spec["validVerdicts"]
        and result["attacksPassed"] == len(spec["attacks"])
        and result["operationCounts"] == spec["operationBoundary"]
    )
    audit = {
        "schemaVersion": "bfs.nativeCpuDataPassSemanticEquivalenceAudit.v0.1",
        "status": "PASS" if passed else "FAIL",
        "verdict": result["verdict"],
        "semanticDataSampleFloor": result["semanticDataSampleFloor"],
        "attacksPassed": result["attacksPassed"],
        "attackCount": len(result["attacks"]),
        "evidenceCoreHash": result["evidenceCoreHash"],
        "analysisReplay": replay_observation,
        "frozenToolChecks": frozen_tools,
        "frozenToolsMatch": all(item["match"] for item in frozen_tools),
        "boundInputChecks": bound_inputs,
        "boundInputsMatch": all(item["match"] for item in bound_inputs),
        "artifactChecks": artifacts,
        "artifactsMatch": all(item["match"] for item in artifacts),
        "operationCounts": spec["operationBoundary"],
        "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(Path(__file__))},
        "replayStdout": process.stdout.strip(),
        "failures": [] if passed else ["REPLAY_OR_GATE_MISMATCH"],
    }
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B51_D6_AUDIT {audit['status']} replayExact={replay_exact} artifacts={sum(item['match'] for item in artifacts)}/{len(artifacts)}", flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
