#!/usr/bin/env python3
"""C2: bind attempt-15 and route corrected unchanged matrix to attempt 16."""

import hashlib
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("run-rc6-liquid-static-calibration-matrix.py")
EXPECTED_BASE_SHA256 = "5a90b25ae55db94bde4882a9c194388bf87fbb24c8960e3b929bd9db4e3cf9e0"
FAILURE_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-static-calibration-attempt-15/failure-audit.json"
EXPECTED_FAILURE_AUDIT_SHA256 = "7c74583ab83168c4fc98f834dc8d18916279518d6c84dee3faa719dd2003c208"


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if file_sha(BASE) != EXPECTED_BASE_SHA256:
    raise RuntimeError("static calibration C2 base identity mismatch")
if file_sha(FAILURE_AUDIT) != EXPECTED_FAILURE_AUDIT_SHA256:
    raise RuntimeError("static calibration C2 retained failure identity mismatch")

source = BASE.read_text(encoding="utf-8")
replacements = (
    ("RC6-2026-09-01-static-calibration-attempt-14", "RC6-2026-09-01-static-calibration-attempt-16", 2, "fresh roots"),
    ("ai-native-studio-rc6-liquid-static-calibration.v0.14.json", "ai-native-studio-rc6-liquid-static-calibration-c2.v0.16.json", 1, "spec route"),
    ("scripts/run-rc6-liquid-static-calibration-scene.py", "scripts/run-rc6-liquid-static-calibration-scene-c1.py", 1, "scene route"),
)
for before, after, expected_count, label in replacements:
    if source.count(before) != expected_count:
        raise RuntimeError(f"static calibration C2 {label} targets are not exact")
    source = source.replace(before, after)

except_anchor = "    except Exception as error:\n        failure = {"
except_expansion = """    except Exception as error:
        observed = []
        for process_path in sorted((EVIDENCE / "processes").glob("*.json")):
            observed.append(json.loads(process_path.read_text(encoding="utf-8")))
        failure = {"""
if source.count(except_anchor) != 1:
    raise RuntimeError("static calibration C2 failure observation anchor is not exact")
source = source.replace(except_anchor, except_expansion)
process_before = '"completedProcesses": [{"index": row["index"], "cellId": row["cellId"], "processHash": row["processHash"]} for row in completed],'
process_after = '"completedProcesses": [{"index": row["index"], "cellId": row["cellId"], "processHash": row["processHash"]} for row in observed],'
count_before = '"counts": {"blenderStartsCompleted": len(completed), "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},'
count_after = '"counts": {"blenderStartsCompleted": len(observed), "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0},'
for before, after, label in ((process_before, process_after, "process roster"), (count_before, count_after, "process count")):
    if source.count(before) != 1:
        raise RuntimeError(f"static calibration C2 {label} target is not exact")
    source = source.replace(before, after)
exec(compile(source, str(BASE) + "#C2_ATTEMPT16", "exec"), globals(), globals())
