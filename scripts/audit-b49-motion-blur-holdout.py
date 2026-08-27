"""Independent deterministic replay audit for formal B49-MB."""

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
    parser=argparse.ArgumentParser();parser.add_argument("--spec",type=Path,required=True);parser.add_argument("--receipt",type=Path,required=True);parser.add_argument("--results",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();analyzer=Path(__file__).with_name("analyze-b49-motion-blur-holdout.py")
    with tempfile.TemporaryDirectory(prefix="bfs-b49-mb-audit-") as temporary:
        replay=Path(temporary)/"results.json";process=subprocess.run([sys.executable,str(analyzer),"--spec",str(args.spec),"--receipt",str(args.receipt),"--output",str(replay)],capture_output=True,text=True,check=False)
        if process.returncode!=0:raise RuntimeError(f"analyzer replay failed: {process.stderr}")
        exact=args.results.read_bytes()==replay.read_bytes();result=json.loads(args.results.read_text());replayed=json.loads(replay.read_text());spec=json.loads(args.spec.read_text());valid_verdicts={spec["acceptedVerdict"],spec["indistinguishableVerdict"],spec["rejectedVerdict"]};passed=exact and result["verdict"] in valid_verdicts and result["attacksPassed"]==len(spec["attacks"]) and result["evidenceCoreHash"]==replayed["evidenceCoreHash"]
        audit={"schemaVersion":"bfs.motionBlurHoldoutAudit.v0.1","status":"PASS" if passed else "FAIL","resultsSha256":sha256_file(args.results),"replaySha256":sha256_file(replay),"byteExactReplay":exact,"verdict":result["verdict"],"candidatePassed":result["quality"]["candidatePassed"],"candidateCloserMetricCount":result["quality"]["candidateCloserMetricCount"],"attacksPassed":result["attacksPassed"],"attackCount":len(result["attacks"]),"evidenceCoreHash":result["evidenceCoreHash"],"toolHashes":{"analyzer":sha256_file(analyzer),"audit":sha256_file(__file__)},"replayStdout":process.stdout.strip(),"failures":[] if passed else ["RESULT_REPLAY_OR_GATE_MISMATCH"]};args.output.write_text(json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(f"BFS_B49_MB_AUDIT {audit['status']} verdict={audit['verdict']} replay={'MATCH' if exact else 'DIFF'}",flush=True)
        if not passed:raise SystemExit(1)


if __name__=="__main__":main()
