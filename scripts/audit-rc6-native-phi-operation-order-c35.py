#!/usr/bin/env python3
"""Bind C34 curves to exact Mantaflow operation order and choose only the next diagnostic layer."""

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-phi-operation-order-c35.v1.28.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    return digest(path.read_bytes())


def self_hash(value, field):
    body = dict(value); body.pop(field, None)
    return digest(canonical(body))


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root).decode().strip()


def excerpt_matches(blob, row):
    lines = blob.splitlines()
    first, last = row["lines"]
    text = "\n".join(lines[first - 1:last])
    return 1 <= first <= last <= len(lines) and all(value in text for value in row["contains"]), text


def pearson(first, second):
    mean_a = sum(first) / len(first); mean_b = sum(second) / len(second)
    da = [value - mean_a for value in first]; db = [value - mean_b for value in second]
    return sum(a * b for a, b in zip(da, db)) / math.sqrt(sum(a * a for a in da) * sum(b * b for b in db))


def write_exclusive(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main():
    spec_bytes = SPEC.read_bytes(); spec = json.loads(spec_bytes)
    body = dict(spec); expected_spec_hash = body.pop("specFileSha256")
    assert digest(canonical(body)) == expected_spec_hash
    assert not git(ROOT, "status", "--porcelain")
    assert git(ROOT, "rev-parse", "HEAD^") == spec["researchParent"]
    assert subprocess.check_output(["git", "show", f"HEAD:{SPEC.relative_to(ROOT)}"], cwd=ROOT) == spec_bytes
    assert file_hash(Path(__file__)) == spec["auditorSha256"]
    source = Path(spec["sourceRoot"])
    assert git(source, "rev-parse", "HEAD") == spec["sourceCommit"]
    assert not git(source, "status", "--porcelain")
    sources = {}
    for row in spec["sourceFiles"]:
        path = source / row["path"]
        assert file_hash(path) == row["sha256"]
        assert subprocess.check_output(["git", "show", f"{spec['sourceCommit']}:{row['path']}"], cwd=source) == path.read_bytes()
        sources[row["path"]] = path.read_text()
    for row in spec["inputs"]:
        assert file_hash(ROOT / row["path"]) == row["sha256"]
    evidence = ROOT / spec["evidence"]
    assert not evidence.exists() and not evidence.is_symlink()
    assert shutil.disk_usage(ROOT).free >= spec["minimumReserveBytes"] + spec["maximumEvidenceBytes"]

    checks = {}; excerpts = []
    for row in spec["sourceFacts"]:
        ok, text = excerpt_matches(sources[row["path"]], row)
        checks[row["id"]] = ok
        excerpts.append({**row, "excerpt": text, "excerptSha256": digest(text.encode())})
    liquid = sources["intern/mantaflow/intern/strings/liquid_script.h"]
    step = liquid.split("const std::string liquid_step =", 1)[1].split("const std::string liquid_step_mesh", 1)[0]
    order = [
        "pp_s$ID$.advectInGrid", "pushOutofObs(parts=pp_s$ID$", "phiTmp_s$ID$.copyFrom",
        "advectSemiLagrange(flags=flags_s$ID$, vel=vel_s$ID$, grid=phi_s$ID$",
        "unionParticleLevelset(parts=pp_s$ID$", "phi_s$ID$.addConst(1.)", "phi_s$ID$.join(phiParts_s$ID$)",
        "solvePressure(", "adjustNumber(parts=pp_s$ID$", "apicMapMACGridToParts(",
    ]
    indices = [step.index(value) for value in order]
    checks["exactStepOrder"] = indices == sorted(indices)
    checks["particlePhiPrecedesResampling"] = step.index("unionParticleLevelset(parts=pp_s$ID$") < step.index("adjustNumber(parts=pp_s$ID$")
    checks["currentPhiPrecedesResampling"] = step.index("phi_s$ID$.join(phiParts_s$ID$)") < step.index("adjustNumber(parts=pp_s$ID$")
    second_apic_branch = step.index("if using_apic_s$ID$", step.index("if using_apic_s$ID$") + 1)
    checks["flipRatioNotUsedOnApicBranch"] = second_apic_branch < step.index("apicMapMACGridToParts(") < step.index("else:", second_apic_branch) < step.index("flipVelocityUpdate(")
    checks["cellScaledSupport"] = "narrowBandWidth_s$ID$         = 3" in liquid and "calculateRadiusFactor(phi, radiusFactor)" in sources["extern/mantaflow/preprocessed/plugin/flip.cpp"]

    c34 = json.loads((ROOT / spec["c34Result"]).read_text())
    c29 = json.loads((ROOT / spec["c29Result"]).read_text())
    c30 = json.loads((ROOT / spec["c30Result"]).read_text())
    phi = [row["nativeFields"]["phi"]["negativeLevelsetOccupiedVolumeCubicMeters"] for row in c34["frames"]]
    particle_phi = [row["nativeFields"]["phi_particles"]["negativeLevelsetOccupiedVolumeCubicMeters"] for row in c34["frames"]]
    mesh = [row["meshVolumeCubicMeters"] for row in c29["fluidSamples"]]
    particle_count = [next(grid for grid in row["readerOutput"]["grids"] if grid["name"] == "particles")["particleCount"] for row in c34["frames"]]
    occupied = [row["particleOccupiedVoxelCount"] for row in c30["samples"]]
    first_loss = lambda values: next((index + 1 for index, value in enumerate(values) if value / values[0] - 1 <= -0.15), None)
    metrics = {
        "phiFrame36Drift": phi[-1] / phi[0] - 1,
        "particlePhiFrame36Drift": particle_phi[-1] / particle_phi[0] - 1,
        "meshFrame36Drift": mesh[-1] / mesh[0] - 1,
        "particleCountFrame36Drift": particle_count[-1] / particle_count[0] - 1,
        "particleOccupiedSupportFrame36Drift": occupied[-1] / occupied[0] - 1,
        "phiFirst15PercentLossFrame": first_loss(phi),
        "particlePhiFirst15PercentLossFrame": first_loss(particle_phi),
        "meshFirst15PercentLossFrame": first_loss(mesh),
        "phiMeshCorrelation": pearson(phi, mesh),
        "phiOccupiedSupportCorrelation": pearson(phi, occupied),
    }
    expected = spec["expectedMetrics"]
    checks["c34MetricsExact"] = all(abs(metrics[key] - expected[key]) <= 1e-12 if isinstance(expected[key], float) else metrics[key] == expected[key] for key in expected)
    checks["commonFieldsExactBeforeInterpretation"] = c34["strongCommonFieldEquivalence"] is True and c34["status"] == "PASS_NATIVE_EXPORT_STRONG_COMMON_FIELD_EQUIVALENCE"
    checks["meshOnlyExplanationRejected"] = metrics["phiFrame36Drift"] <= -0.15 and metrics["phiMeshCorrelation"] >= 0.8
    checks["transitionOrderNotSameFrame"] = metrics["phiFirst15PercentLossFrame"] != metrics["meshFirst15PercentLossFrame"]

    policy = json.loads((ROOT / spec["policySpec"]).read_text())
    checks["review128AlreadyPolicyBound"] = policy["qualityTiers"]["PREVIEW"]["resolutionMax"] == 96 and policy["qualityTiers"]["REVIEW"]["resolutionMax"] == 128
    checks["selectionExact"] = spec["selection"] == {
        "gate": "C36_DATA_ONLY_RESOLUTION_CONVERGENCE",
        "singleChange": "resolution_max 96 to 128",
        "reason": "native occupancy is numerical and fixed-cell levelset/particle support changes world scale with resolution; test convergence before another physical scalar",
        "notARecipe": True,
        "meshAndRender": "FORBIDDEN",
    }
    checks["sourceAndInputsUnchanged"] = not git(source, "status", "--porcelain") and all(file_hash(source / row["path"]) == row["sha256"] for row in spec["sourceFiles"]) and all(file_hash(ROOT / row["path"]) == row["sha256"] for row in spec["inputs"])
    checks["claimCeilingExact"] = spec["claimCeiling"].startswith("Read-only operation-order") and "not exact mass" in spec["claimCeiling"]
    assert len(checks) == spec["expectedChecks"]
    status = "PASS_SOURCE_ORDER_SELECT_REVIEW128_DATA_ONLY" if all(checks.values()) else "FAIL"
    observation = {
        "schemaVersion": "bfs.rc6NativePhiOperationOrderC35.v1", "status": status,
        "researchExecutionCommit": git(ROOT, "rev-parse", "HEAD"), "sourceCommit": spec["sourceCommit"],
        "excerpts": excerpts, "operationOrder": order, "metrics": metrics,
        "interpretation": {
            "currentPhi": "advected, shrunk and joined with pre-resampling particle phi within each substep",
            "particlePhi": "built before adjustNumber in the same substep",
            "previousPhi": "beginning-of-adaptive-frame copy; not current or necessarily prior saved terminal phi",
            "savedParticles": "post-adjustNumber and post-APIC update; count is not same-stage mass",
        },
        "selection": spec["selection"], "claimCeiling": spec["claimCeiling"],
    }
    observation["observationHash"] = self_hash(observation, "observationHash")
    audit = {
        "schemaVersion": "bfs.rc6NativePhiOperationOrderC35Audit.v1", "status": status,
        "checks": checks, "passCount": sum(checks.values()), "checkCount": len(checks),
        "observationHash": observation["observationHash"], "specFileSha256": expected_spec_hash,
        "counts": spec["counts"], "claimCeiling": spec["claimCeiling"],
    }
    audit["auditHash"] = self_hash(audit, "auditHash")
    encoded = [("source-observation.json", observation), ("independent-audit.json", audit)]
    assert sum(len(json.dumps(value, indent=2, sort_keys=True).encode()) + 1 for _, value in encoded) <= spec["maximumEvidenceBytes"]
    evidence.mkdir()
    for name, value in encoded:
        write_exclusive(evidence / name, value)
    print(json.dumps({"status": status, "checks": f"{audit['passCount']}/{audit['checkCount']}", "auditHash": audit["auditHash"]}, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
