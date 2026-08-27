"""Independent byte-exact analyzer replay for B51-D1."""

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyzer = Path(__file__).with_name("analyze-b51-native-cycles-backend-derivation.py")
    with tempfile.TemporaryDirectory(prefix="bfs-b51-d1-audit-") as temporary:
        replay = Path(temporary) / "results.json"
        process = subprocess.run([sys.executable, str(analyzer), "--spec", str(args.spec), "--receipt", str(args.receipt), "--output", str(replay)], capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"analyzer replay failed: {process.stderr}")
        exact = args.results.read_bytes() == replay.read_bytes()
        result = json.loads(args.results.read_text(encoding="utf-8"))
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        passed = exact and result["verdict"] == "NATIVE_CYCLES_BACKEND_DERIVATION_USABLE" and result["attacksPassed"] == len(spec["attacks"])
        audit = {
            "schemaVersion": "bfs.nativeCyclesBackendDerivationAudit.v0.1", "status": "PASS" if passed else "FAIL",
            "resultsSha256": sha256_file(args.results), "replaySha256": sha256_file(replay), "byteExactReplay": exact,
            "verdict": result["verdict"], "attacksPassed": result["attacksPassed"], "attackCount": len(result["attacks"]),
            "evidenceCoreHash": result["evidenceCoreHash"], "toolHashes": {"analyzer": sha256_file(analyzer), "audit": sha256_file(__file__)},
            "replayStdout": process.stdout.strip(), "failures": [] if passed else ["RESULT_REPLAY_OR_GATE_MISMATCH"],
        }
        args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"BFS_B51_D1_AUDIT {audit['status']} replay={'MATCH' if exact else 'DIFF'}", flush=True)
        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
