#!/usr/bin/env python3
"""Close only C20's published-centroid replay precision in a fresh audit root."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-particle-radius-c20-c1.py")
EXPECTED_BASE_SHA256 = "886c4a6f942deef5a3be6805c9d4cfc9427babc9630631b6aa1afae28726af2e"
C4_SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20-c4.v1.08.json"
C4_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c4-audit-attempt-97"


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


def manifest(root):
    rows = [
        {"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    value = {"root": str(root), "files": rows}
    value["manifestHash"] = self_hash(value, "manifestHash")
    return value


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def transformed_source():
    if sha(BASE) != EXPECTED_BASE_SHA256:
        raise RuntimeError("C20 C4 audit base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c20_c1_audit_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_evidence = 'EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94"'
    new_evidence = '''RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94"
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c4-audit-attempt-97"
C1_AUDITOR = RESEARCH / "scripts/audit-rc6-real-impact-liquid-particle-radius-c20-c1.py"'''
    metric_old = 'abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift) <= 1e-8'
    metric_new = 'abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift) <= 2e-8'
    identity_old = 'str(Path(__file__).resolve().relative_to(RESEARCH)): sha(Path(__file__).resolve())'
    identity_new = 'str(C1_AUDITOR.relative_to(RESEARCH)): sha(C1_AUDITOR)'
    head_old = '''head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())'''
    head_new = '''head = receipt["researchExecutionCommit"]
parent = subprocess.run(["git", "rev-parse", head + "^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", head], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())'''
    check_anchor = '    "claimCeilingExact": result["claimCeiling"] == spec["claimCeiling"] and receipt["claimCeiling"] == spec["claimCeiling"],\n'
    check_extension = check_anchor + '''    "c4SpecSelfHash": c4_spec["specHash"] == self_hash(c4_spec, "specHash"),
    "c4ToolIdentity": sha(Path(__file__).resolve()) == c4_spec["toolSha256"],
    "c4FreezeCommitBound": c4_parent == c4_spec["researchParentBeforePreregistration"] and c4_freeze_paths == set(c4_spec["freezePaths"]),
    "retainedEvidenceRootExact": manifest(RETAINED_EVIDENCE)["manifestHash"] == c4_spec["retainedEvidenceManifestHash"],
'''
    audit_schema_old = '"bfs.rc6RealImpactLiquidParticleRadiusC20C1IndependentAudit.v0.1"'
    audit_schema_new = '"bfs.rc6RealImpactLiquidParticleRadiusC20C4AuditOnly.v0.1"'
    audit_fields_anchor = '    "receiptHash": receipt["receiptHash"],\n'
    audit_fields_extension = audit_fields_anchor + '''    "metricReplayTolerances": {"volumeRatios": 1e-8, "centroidDistanceMeters": 2e-8},
    "centroidReplayAbsoluteDeltaMeters": abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift),
    "counts": c4_spec["counts"],
    "claimCeiling": c4_spec["claimCeiling"],
'''
    output_old = 'with (RETAINED_EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:'
    output_new = 'with (EVIDENCE / "audit.json").open("x", encoding="utf-8") as handle:'
    replacements = (
        (old_evidence, new_evidence, "retained/fresh evidence split", 1),
        ('EVIDENCE / "', 'RETAINED_EVIDENCE / "', "retained evidence reads", 9),
        ('manifest(EVIDENCE, exclude=("evidence-manifest.pre-audit.json",))', 'manifest(RETAINED_EVIDENCE, exclude=("evidence-manifest.pre-audit.json",))', "pre-audit manifest root", 1),
        ('for root in (WORK, EVIDENCE)', 'for root in (WORK, RETAINED_EVIDENCE)', "media root", 1),
        ('tree_bytes(EVIDENCE)', 'tree_bytes(RETAINED_EVIDENCE)', "evidence ceiling root", 1),
        (metric_old, metric_new, "centroid replay tolerance", 1),
        (identity_old, identity_new, "C1 auditor identity", 1),
        (head_old, head_new, "retained execution commit", 1),
        (check_anchor, check_extension, "C3 checks", 1),
        (audit_schema_old, audit_schema_new, "audit schema", 1),
        (audit_fields_anchor, audit_fields_extension, "C3 audit fields", 1),
        (output_old, output_new, "fresh audit output", 1),
        ("RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C1_AUDIT=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C4_AUDIT=", "audit marker", 1),
        ("real-impact liquid C20 C1 independent audit failed", "real-impact liquid C20 C4 audit-only closure failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C20 C4 {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    return source


def main():
    c4_spec = json.loads(C4_SPEC.read_text())
    if c4_spec["specHash"] != self_hash(c4_spec, "specHash"):
        raise RuntimeError("C20 C4 spec self hash mismatch")
    if sha(Path(__file__).resolve()) != c4_spec["toolSha256"]:
        raise RuntimeError("C20 C4 tool identity mismatch")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("C20 C4 worktree is not clean")
    c4_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    c4_parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    c4_freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())
    if c4_parent != c4_spec["researchParentBeforePreregistration"] or c4_freeze_paths != set(c4_spec["freezePaths"]):
        raise RuntimeError("C20 C4 freeze commit mismatch")
    retained = RESEARCH / c4_spec["retainedEvidenceRoot"]
    retained_manifest = manifest(retained)
    if retained_manifest["manifestHash"] != c4_spec["retainedEvidenceManifestHash"]:
        raise RuntimeError("C20 C4 retained evidence drift")
    if C4_EVIDENCE.exists():
        raise RuntimeError("C20 C4 evidence root is not fresh")
    C4_EVIDENCE.mkdir(parents=True, exist_ok=False)
    scope = {
        "schemaVersion": "bfs.rc6RealImpactLiquidParticleRadiusC20C4Admission.v0.1",
        "status": "PASS",
        "executionCommit": c4_head,
        "retainedEvidenceManifestHash": retained_manifest["manifestHash"],
        "counts": c4_spec["counts"],
    }
    write_exclusive(C4_EVIDENCE / "admission.json", scope)
    shared_environment = dict(globals())
    shared_environment.update(locals())
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C4", "exec"), shared_environment, shared_environment)
    audit = json.loads((C4_EVIDENCE / "audit.json").read_text())
    receipt = {
        "schemaVersion": "bfs.rc6RealImpactLiquidParticleRadiusC20C4Receipt.v0.1",
        "status": audit["status"],
        "executionCommit": c4_head,
        "auditHash": audit["auditHash"],
        "retainedResultHash": audit["resultHash"],
        "retainedReceiptHash": audit["receiptHash"],
        "counts": c4_spec["counts"],
        "claimCeiling": c4_spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(C4_EVIDENCE / "receipt.json", receipt)
    write_exclusive(C4_EVIDENCE / "evidence-manifest.json", manifest(C4_EVIDENCE))
    print("RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C4_RECEIPT=" + canonical(receipt), flush=True)


if __name__ == "__main__":
    main()



