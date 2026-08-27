"""Independent B51-D2 analyzer replay and cache-safety audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    path = Path(path); digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def tree_manifest(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"unsafe cache tree root: {root}")
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"cache symlink rejected: {path}")
        if stat.S_ISREG(info.st_mode):
            records.append({"relativePath": path.relative_to(root).as_posix(), "mode": stat.S_IMODE(info.st_mode), "bytes": info.st_size, "sha256": sha256_file(path)})
    return {"fileCount": len(records), "bytes": sum(item["bytes"] for item in records), "treeSha256": canonical_hash(records)}


def git_blob_hash(commit: str, uri: str, repository_root: Path) -> str | None:
    process = subprocess.run(["git", "show", f"{commit}:{uri}"], cwd=repository_root, capture_output=True, check=False)
    return hashlib.sha256(process.stdout).hexdigest() if process.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--spec", type=Path, required=True); parser.add_argument("--receipt", type=Path, required=True); parser.add_argument("--results", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    analyzer = Path(__file__).with_name("analyze-b51-cycles-cache-state-derivation.py")
    with tempfile.TemporaryDirectory(prefix="bfs-b51-d2-audit-") as temporary:
        replay = Path(temporary) / "results.json"; process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--receipt", str(args.receipt), "--output", str(replay)], capture_output=True, text=True, check=False)
        if process.returncode: raise RuntimeError(process.stderr)
        exact = args.results.read_bytes() == replay.read_bytes(); result = json.loads(args.results.read_text()); spec = json.loads(args.spec.read_text()); receipt = json.loads(args.receipt.read_text())
        restore = receipt["cacheRestore"]
        repository_root = args.spec.resolve().parent.parent
        original = Path(spec["cacheContract"]["originalPath"])
        quarantine = Path(spec["cacheContract"]["quarantinePath"])
        retained = repository_root / spec["cacheContract"]["generatedRetentionPath"]
        current_original = tree_manifest(original)
        current_retained = tree_manifest(retained)
        retained_receipt = next(item["retainedManifest"] for item in receipt["cacheEvents"] if item["event"] == "RETAIN_GENERATED")
        frozen_tool_checks = []
        for name, binding in receipt["tools"].items():
            observed = git_blob_hash(receipt["toolFreezeCommit"], binding["uri"], repository_root)
            frozen_tool_checks.append({"name": name, "uri": binding["uri"], "expectedSha256": binding["sha256"], "observedGitBlobSha256": observed, "match": observed == binding["sha256"]})
        frozen_tools_match = all(item["match"] for item in frozen_tool_checks)
        safe = restore["status"] == "PASS" and restore["matchesPreflight"] and restore["originalExists"] and not restore["originalIsSymlink"] and not restore["quarantineExists"] and restore["generatedRetentionExists"] and receipt["executionError"] is None and not quarantine.exists() and current_original["treeSha256"] == receipt["cachePreflight"]["original"]["treeSha256"] and current_retained["treeSha256"] == retained_receipt["treeSha256"]
        passed = exact and safe and frozen_tools_match and result["verdict"] == "CYCLES_CACHE_STATE_DERIVATION_USABLE" and result["attacksPassed"] == len(spec["attacks"])
        audit = {"schemaVersion": "bfs.cyclesCacheStateDerivationAudit.v0.2", "status": "PASS" if passed else "FAIL", "analysisCorrection": result["analysisCorrection"], "resultsSha256": sha256_file(args.results), "replaySha256": sha256_file(replay), "byteExactReplay": exact, "cacheSafetyPass": safe, "frozenToolChecks": frozen_tool_checks, "frozenToolsMatch": frozen_tools_match, "originalCacheTreeSha256": receipt["cachePreflight"]["original"]["treeSha256"], "restoredCacheTreeSha256": restore["restoredManifest"]["treeSha256"], "currentOriginalCacheTreeSha256": current_original["treeSha256"], "currentRetainedGeneratedCacheTreeSha256": current_retained["treeSha256"], "verdict": result["verdict"], "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]), "evidenceCoreHash": result["evidenceCoreHash"], "toolHashes": {"correctedAnalyzer": sha256_file(analyzer), "correctedAudit": sha256_file(__file__)}, "replayStdout": process.stdout.strip(), "failures": [] if passed else ["REPLAY_OR_CACHE_SAFETY_MISMATCH"]}
        args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n"); print(f"BFS_B51_D2_AUDIT {audit['status']} replay={'MATCH' if exact else 'DIFF'} cacheSafety={safe}", flush=True)
        if not passed: raise SystemExit(1)


if __name__ == "__main__": main()
