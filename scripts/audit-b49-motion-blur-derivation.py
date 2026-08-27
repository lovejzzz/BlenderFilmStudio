"""Independent deterministic replay audit for B49-MB-D1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--spec",type=Path,required=True);parser.add_argument("--receipt",type=Path,required=True);parser.add_argument("--analysis",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();analyzer=Path(__file__).with_name("analyze-b49-motion-blur-derivation.py")
    with tempfile.TemporaryDirectory(prefix="bfs-b49-mb-d1-audit-") as temporary:
        replay=Path(temporary)/"analysis.json";process=subprocess.run([sys.executable,str(analyzer),"--spec",str(args.spec),"--receipt",str(args.receipt),"--output",str(replay)],capture_output=True,text=True,check=False)
        if process.returncode!=0:raise RuntimeError(f"analyzer replay failed: {process.stderr}")
        exact=args.analysis.read_bytes()==replay.read_bytes();analysis=json.loads(args.analysis.read_text());replayed=json.loads(replay.read_text());spec=json.loads(args.spec.read_text());passed=exact and analysis["status"]==spec["usableStatus"] and len(analysis["observations"])==len(spec["cells"]) and len(analysis["relations"])==len(spec["frozenRelations"]) and analysis["evidenceCoreHash"]==replayed["evidenceCoreHash"]
        audit={"schemaVersion":"bfs.motionBlurDerivationAudit.v0.1","status":"PASS" if passed else "FAIL","analysisSha256":sha256_file(args.analysis),"replaySha256":sha256_file(replay),"byteExactReplay":exact,"derivationStatus":analysis["status"],"cellCount":len(analysis["observations"]),"relationCount":len(analysis["relations"]),"evidenceCoreHash":analysis["evidenceCoreHash"],"toolHashes":{"analyzer":sha256_file(analyzer),"audit":sha256_file(__file__)},"replayStdout":process.stdout.strip(),"failures":[] if passed else ["ANALYSIS_REPLAY_OR_USABILITY_MISMATCH"]};args.output.write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(f"BFS_B49_MB_D1_AUDIT {audit['status']} replay={'MATCH' if exact else 'DIFF'}",flush=True)
        if not passed:raise SystemExit(1)


if __name__=="__main__":main()
