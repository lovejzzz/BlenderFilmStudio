#!/usr/bin/env python3
"""Independent mechanical binding of a manual source inspection; never imports Blender."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-conservation-observability-c32.v1.22.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def seal(value, field):
    return {**value, field: digest(encode(value))}


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def matches(blob, row):
    lines = blob.decode().splitlines()
    first, last = row["lines"]
    excerpt = "\n".join(lines[first - 1:last])
    return first >= 1 and last <= len(lines) and all(x in excerpt for x in row["contains"])


def main():
    spec_bytes = SPEC.read_bytes()
    spec = json.loads(spec_bytes)
    assert spec["status"] == "PREREGISTERED_READ_ONLY_SOURCE_AUDIT"
    assert not git(ROOT, "status", "--porcelain").strip(), "freeze first"
    commit = git(ROOT, "rev-parse", "HEAD").decode().strip()
    assert git(ROOT, "rev-parse", "HEAD^").decode().strip() == spec["researchParent"]
    assert git(ROOT, "show", f"HEAD:{SPEC.relative_to(ROOT)}") == spec_bytes
    assert digest(Path(__file__).read_bytes()) == spec["auditorSha256"]
    source = Path(spec["sourceRoot"])
    assert source.resolve() == source
    assert git(source, "rev-parse", "HEAD").decode().strip() == spec["sourceCommit"]
    assert not git(source, "status", "--porcelain").strip()
    data = {}
    for row in spec["sourceFiles"]:
        path = source / row["path"]
        assert path.resolve() == path
        blob = path.read_bytes()
        assert digest(blob) == row["sha256"]
        assert git(source, "show", f"{spec['sourceCommit']}:{row['path']}") == blob
        data[row["path"]] = blob
    for row in spec["inputs"]:
        path = ROOT / row["path"]
        assert path.resolve() == path and digest(path.read_bytes()) == row["sha256"]
    evidence = ROOT / spec["evidenceRoot"]
    assert not evidence.exists() and not evidence.is_symlink()
    assert evidence.parent.resolve() == evidence.parent
    assert shutil.disk_usage(ROOT).free >= spec["minimumReserveBytes"] + spec["maximumEvidenceBytes"]

    checks = {}
    excerpts = []
    for fact in spec["sourceFacts"]:
        blob = data[fact["path"]]
        checks[fact["id"]] = matches(blob, fact)
        first, last = fact["lines"]
        excerpt = "\n".join(blob.decode().splitlines()[first - 1:last])
        excerpts.append({**fact, "excerpt": excerpt, "excerptSha256": digest(excerpt.encode())})
    liquid = data["intern/mantaflow/intern/strings/liquid_script.h"].decode()
    step = liquid.split("const std::string liquid_step =", 1)[1].split("const std::string liquid_step_mesh", 1)[0]
    checks["stepOrderNativePhiThenResampling"] = step.index("unionParticleLevelset(") < step.index("phi_s$ID$.addConst(1.)") < step.index("adjustNumber(")
    checks["noDirectResumableBranchInLiquidStep"] = "resumable" not in step.lower()
    rna = data["source/blender/makesrna/intern/rna_fluid.cc"].decode()
    checks["noRnaPhiGridProperty"] = '"phi_grid"' not in rna and '"density_grid"' in rna
    for row in spec["inputs"]:
        assert digest((ROOT / row["path"]).read_bytes()) == row["sha256"]
    checks["retainedInputBytesUnchanged"] = True
    checks["sourceBytesUnchanged"] = all(digest((source / row["path"]).read_bytes()) == row["sha256"] for row in spec["sourceFiles"])
    checks["sourceWorktreeStillClean"] = not git(source, "status", "--porcelain").strip()
    checks["emptyOrCorruptedAnchorRejected"] = all(not matches(b"", row) for row in spec["sourceFacts"]) and not matches(b"changed", {"lines": [1, 1], "contains": ["original"]})
    checks["claimDoesNotPromotePhysicsOrPassivity"] = spec["conclusions"] == {
        "existingCachePath": "SOURCE_SUPPORTED_NOT_RUNTIME_VALIDATED",
        "passiveMeasurement": "UNPROVEN",
        "exactMass": "NOT_MEASURED",
        "impactPhysics": "RETAINED_FAIL",
        "nextBake": "SEPARATE_PREREGISTRATION_REQUIRED",
    }
    assert len(checks) == spec["expectedChecks"]
    status = "PASS_SOURCE_BINDING_ONLY" if all(checks.values()) else "FAIL"
    observation = seal({"schemaVersion": "bfs.rc6C32SourceObservation.v1.0", "researchExecutionCommit": commit, "sourceCommit": spec["sourceCommit"], "sourceFiles": spec["sourceFiles"], "excerpts": excerpts, "conclusions": spec["conclusions"]}, "observationHash")
    audit = seal({"schemaVersion": "bfs.rc6C32SourceAudit.v1.0", "status": status, "researchExecutionCommit": commit, "specFileSha256": digest(spec_bytes), "sourceObservationHash": observation["observationHash"], "checks": checks, "passCount": sum(checks.values()), "checkCount": len(checks), "operationCounts": spec["operationCounts"], "claimCeiling": spec["claimCeiling"]}, "auditHash")
    payloads = {"source-observations.json": observation, "independent-audit.json": audit}
    encoded = {name: (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode() for name, value in payloads.items()}
    assert sum(map(len, encoded.values())) <= spec["maximumEvidenceBytes"]
    evidence.mkdir()
    for name, blob in encoded.items():
        with (evidence / name).open("xb") as handle:
            handle.write(blob)
    print(json.dumps({"status": status, "checks": f"{sum(checks.values())}/{len(checks)}", "auditHash": audit["auditHash"]}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
