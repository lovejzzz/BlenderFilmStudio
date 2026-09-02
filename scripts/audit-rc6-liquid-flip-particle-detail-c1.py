#!/usr/bin/env python3
"""C1 audit-only correction for eight-decimal derived particle penetrations."""

import hashlib
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
ATTEMPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-flip-particle-detail-attempt-37"
AUDIT_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-01-flip-particle-detail-audit-c1-attempt-38"
SPEC = RESEARCH / "specs/ai-native-studio-rc6-liquid-flip-particle-detail-audit-c1.v0.40.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def file_entries(root, exclusions=()):
    excluded = set(exclusions)
    return [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and str(path.relative_to(root)) not in excluded
    ]


def manifest(root, exclusions=()):
    value = {"schemaVersion": "bfs.rootManifest.v0.1", "root": str(root), "files": file_entries(root, exclusions)}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def check(label, condition, checks):
    checks[label] = bool(condition)


def main():
    if AUDIT_ROOT.exists():
        raise RuntimeError("C1 audit root is not fresh")
    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True
    ).stdout:
        raise RuntimeError("research worktree must be clean before C1 audit")

    spec = read_json(SPEC)
    retained_before = manifest(ATTEMPT)
    failed = read_json(ATTEMPT / "independent-audit.json")
    result = read_json(ATTEMPT / "cells/axis-control/result.json")
    receipt = read_json(ATTEMPT / "receipt.json")
    axis_spec = read_json(RESEARCH / spec["priorParticleAxisSpec"]["path"])
    axis_result = read_json(RESEARCH / axis_spec["priorParticleAxis"]["resultPath"])
    source_code = Path(axis_spec["sourceCodeBinding"]["path"])
    checks = {}

    check(
        "specAndToolExact",
        spec.get("status") == "FROZEN"
        and spec.get("specHash") == self_hash(spec, "specHash")
        and spec.get("tools") == {str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())},
        checks,
    )
    check(
        "retainedFailedAuditExact",
        sha(ATTEMPT / "independent-audit.json") == spec["retainedAttempt"]["failedAuditFileSha256"]
        and failed.get("auditHash") == spec["retainedAttempt"]["failedAuditHash"]
        and failed.get("status") == "FAIL"
        and failed.get("checksPassed") == 26
        and failed.get("checksTotal") == 27
        and [name for name, passed in failed.get("checks", {}).items() if not passed]
        == ["activeOutlierDetailsRecomputed"],
        checks,
    )
    check(
        "retainedResultAndReceiptExact",
        sha(ATTEMPT / "cells/axis-control/result.json") == spec["retainedAttempt"]["resultFileSha256"]
        and result.get("resultHash") == spec["retainedAttempt"]["resultHash"]
        and result.get("resultHash") == self_hash(result, "resultHash")
        and sha(ATTEMPT / "receipt.json") == spec["retainedAttempt"]["receiptFileSha256"]
        and receipt.get("receiptHash") == spec["retainedAttempt"]["receiptHash"]
        and receipt.get("receiptHash") == self_hash(receipt, "receiptHash")
        and receipt.get("status") == "PASS_EXECUTION",
        checks,
    )
    check(
        "priorParticleAxisSpecExact",
        sha(RESEARCH / spec["priorParticleAxisSpec"]["path"])
        == spec["priorParticleAxisSpec"]["fileSha256"]
        and axis_spec.get("specHash") == spec["priorParticleAxisSpec"]["specHash"]
        and axis_spec.get("specHash") == self_hash(axis_spec, "specHash"),
        checks,
    )
    projected = lambda sample: {
        key: sample.get(key)
        for key in ("frame", "aggregate", "strictInterior", "components", "boundsMinCupLocal", "boundsMaxCupLocal")
    }
    check(
        "priorParticleAxisResultExact",
        sha(RESEARCH / axis_spec["priorParticleAxis"]["resultPath"])
        == axis_spec["priorParticleAxis"]["resultFileSha256"]
        and [projected(sample) for sample in result.get("samples", [])]
        == [projected(sample) for sample in axis_result.get("samples", [])],
        checks,
    )
    check(
        "activeParticleSourceExact",
        sha(source_code) == axis_spec["sourceCodeBinding"]["fileSha256"]
        and axis_spec["sourceCodeBinding"]["commit"] == "8e18c82548f8716c415e6e1b69fdbbdeef1f1900",
        checks,
    )

    tolerance = spec["correction"]["derivedPenetrationAbsoluteToleranceMeters"]
    detail_exact = True
    unique_positions = set()
    regions = set()
    speeds = set()
    observations = 0
    for sample in result.get("samples", []):
        details = sample.get("outliersOneVoxel", [])
        aggregate = sample.get("aggregate", {})
        strict = sample.get("strictInterior", {})
        detail_exact = detail_exact and len(details) == aggregate.get("outsideUnionCount")
        detail_exact = detail_exact and strict.get("outsideUnionCount", -1) >= aggregate.get("outsideUnionCount", -1)
        for detail in details:
            observations += 1
            local = detail.get("locationCupLocal", [])
            if len(local) != 3:
                detail_exact = False
                continue
            unique_positions.add(tuple(local))
            regions.add(detail.get("physicalRegion"))
            speeds.add(detail.get("speedRna"))
            radial = (local[0] * local[0] + local[1] * local[1]) ** 0.5
            radial_out = radial > 0.0926041667
            below_out = local[2] < -0.1626041667
            above_out = local[2] > 0.2226041667
            expected_region = (
                "INSIDE_CUP_SOLID_FLOOR"
                if radial <= 0.15 and -0.22 <= local[2] < -0.16
                else (
                    "BELOW_CUP_OUTER_BOTTOM"
                    if local[2] < -0.22
                    else (
                        "INSIDE_CUP_SOLID_WALL"
                        if 0.09 < radial <= 0.15 and -0.22 <= local[2] <= 0.22
                        else "OUTSIDE_MODELED_CUP_SOLID"
                    )
                )
            )
            expected_floor = round(max(0.0, -0.16 - local[2]), 8)
            expected_voxel = round(max(0.0, -0.16260416666666666 - local[2]), 8)
            detail_exact = (
                detail_exact
                and detail.get("detailHash") == self_hash(detail, "detailHash")
                and detail.get("aliveState") == "ALIVE"
                and detail.get("physicalRegion") == expected_region
                and detail.get("radialOutsideOneVoxel") == radial_out
                and detail.get("belowFloorOneVoxel") == below_out
                and detail.get("aboveRimOneVoxel") == above_out
                and (radial_out or below_out or above_out)
                and abs(detail.get("interiorFloorPenetrationMeters") - expected_floor) <= tolerance
                and abs(detail.get("oneVoxelEnvelopePenetrationMeters") - expected_voxel) <= tolerance
            )
    check("activeOutlierDetailsRecomputedC1", detail_exact, checks)
    check(
        "measuredClusterExact",
        observations == 36
        and len(unique_positions) == 9
        and regions == {"INSIDE_CUP_SOLID_FLOOR"}
        and speeds == {0.0}
        and [sample["aggregate"]["outsideUnionCount"] for sample in result["samples"]] == [0, 0, 0, 9, 9, 9, 9],
        checks,
    )
    check(
        "correctionNarrow",
        tolerance == 0.00000001
        and spec["correction"]["changedCheck"] == "activeOutlierDetailsRecomputed"
        and spec["correction"]["blenderReruns"] == 0,
        checks,
    )

    retained_after = manifest(ATTEMPT)
    check("retainedAttemptImmutable", retained_after == retained_before, checks)
    committed = subprocess.run(
        ["git", "show", f"HEAD:{Path(__file__).resolve().relative_to(RESEARCH)}"],
        cwd=RESEARCH,
        capture_output=True,
        check=False,
    )
    committed_spec = subprocess.run(
        ["git", "show", f"HEAD:{SPEC.relative_to(RESEARCH)}"],
        cwd=RESEARCH,
        capture_output=True,
        check=False,
    )
    check(
        "committedBytesExact",
        committed.returncode == 0
        and hashlib.sha256(committed.stdout).hexdigest() == sha(Path(__file__).resolve())
        and committed_spec.returncode == 0
        and hashlib.sha256(committed_spec.stdout).hexdigest() == sha(SPEC),
        checks,
    )

    audit = {
        "schemaVersion": "bfs.rc6LiquidFlipParticleDetailAuditC1.v0.1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "retainedAttemptManifestHash": retained_before["manifestHash"],
        "retainedResultHash": result["resultHash"],
        "retainedReceiptHash": receipt["receiptHash"],
        "failedAuditHash": failed["auditHash"],
        "derivedPenetrationAbsoluteToleranceMeters": tolerance,
        "observations": observations,
        "uniqueActiveOutlierPositions": len(unique_positions),
        "physicalRegions": sorted(regions),
        "reportedSpeeds": sorted(speeds),
        "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    write_exclusive(AUDIT_ROOT / "independent-audit-c1.json", audit)
    root_manifest = manifest(AUDIT_ROOT, exclusions=("root-manifest.json",))
    write_exclusive(AUDIT_ROOT / "root-manifest.json", root_manifest)
    print(canonical({
        "status": audit["status"],
        "checks": f"{audit['checksPassed']}/{audit['checksTotal']}",
        "auditHash": audit["auditHash"],
        "uniqueActiveOutlierPositions": audit["uniqueActiveOutlierPositions"],
    }))
    if audit["status"] != "PASS":
        raise RuntimeError("FLIP particle detail C1 audit failed")


if __name__ == "__main__":
    main()
