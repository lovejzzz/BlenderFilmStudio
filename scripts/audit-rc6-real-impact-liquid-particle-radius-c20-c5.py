#!/usr/bin/env python3
"""Close only C20's two historical audit views in a fresh audit root."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-liquid-particle-radius-c20-c1.py")
EXPECTED_BASE_SHA256 = "886c4a6f942deef5a3be6805c9d4cfc9427babc9630631b6aa1afae28726af2e"
C5_SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-liquid-particle-radius-c20-c5.v1.09.json"
C5_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98"
C4_RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c4-audit-attempt-97"


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
        raise RuntimeError("C20 C5 audit base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c20_c1_audit_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    old_evidence = 'EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94"'
    new_evidence = '''RETAINED_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94"
EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98"
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
    check_extension = check_anchor + '''    "c5SpecSelfHash": c5_spec["specHash"] == self_hash(c5_spec, "specHash"),
    "c5ToolIdentity": sha(Path(__file__).resolve()) == c5_spec["toolSha256"],
    "c5FreezeCommitBound": c5_parent == c5_spec["researchParentBeforePreregistration"] and c5_freeze_paths == set(c5_spec["freezePaths"]),
    "retainedEvidenceRootExact": manifest(RETAINED_EVIDENCE)["manifestHash"] == c5_spec["retainedEvidenceManifestHash"],
    "retainedC4EvidenceRootExact": manifest(C4_RETAINED_EVIDENCE)["manifestHash"] == c5_spec["retainedC4EvidenceManifestHash"],
'''
    audit_schema_old = '"bfs.rc6RealImpactLiquidParticleRadiusC20C1IndependentAudit.v0.1"'
    audit_schema_new = '"bfs.rc6RealImpactLiquidParticleRadiusC20C5AuditOnly.v0.1"'
    audit_fields_anchor = '    "receiptHash": receipt["receiptHash"],\n'
    audit_fields_extension = audit_fields_anchor + '''    "metricReplayTolerances": {"volumeRatios": 1e-8, "centroidDistanceMeters": 2e-8},
    "centroidReplayAbsoluteDeltaMeters": abs(result["metrics"]["maximumLiquidCentroidShiftCupLocalMeters"] - centroid_shift),
    "counts": c5_spec["counts"],
    "claimCeiling": c5_spec["claimCeiling"],
'''
    output_old = 'with (RETAINED_EVIDENCE / "independent-audit.json").open("x", encoding="utf-8") as handle:'
    output_new = 'with (EVIDENCE / "audit.json").open("x", encoding="utf-8") as handle:'
    replacements = (
        (old_evidence, new_evidence, "retained/fresh evidence split", 1),
        ('EVIDENCE / "', 'RETAINED_EVIDENCE / "', "retained evidence reads", 9),
        ('manifest(EVIDENCE, exclude=("evidence-manifest.pre-audit.json",))', 'manifest(RETAINED_EVIDENCE, exclude=("evidence-manifest.pre-audit.json", "independent-audit.json", "logs/audit.stdout.log", "logs/audit.stderr.log"))', "historical pre-audit manifest view", 1),
        ('for root in (WORK, EVIDENCE)', 'for root in (WORK, RETAINED_EVIDENCE)', "media root", 1),
        ('tree_bytes(EVIDENCE)', 'tree_bytes(RETAINED_EVIDENCE)', "evidence ceiling root", 1),
        ('"--evidence-root", str(EVIDENCE), "--trajectory-json"', '"--evidence-root", str(RETAINED_EVIDENCE), "--trajectory-json"', "retained process argv evidence root", 1),
        (metric_old, metric_new, "centroid replay tolerance", 1),
        (identity_old, identity_new, "C1 auditor identity", 1),
        (head_old, head_new, "retained execution commit", 1),
        (check_anchor, check_extension, "C3 checks", 1),
        (audit_schema_old, audit_schema_new, "audit schema", 1),
        (audit_fields_anchor, audit_fields_extension, "C3 audit fields", 1),
        (output_old, output_new, "fresh audit output", 1),
        ("RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C1_AUDIT=", "RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C5_AUDIT=", "audit marker", 1),
        ("real-impact liquid C20 C1 independent audit failed", "real-impact liquid C20 C5 audit-only closure failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C20 C5 {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)
    return source


def main():
    c5_spec = json.loads(C5_SPEC.read_text())
    if c5_spec["specHash"] != self_hash(c5_spec, "specHash"):
        raise RuntimeError("C20 C5 spec self hash mismatch")
    if sha(Path(__file__).resolve()) != c5_spec["toolSha256"]:
        raise RuntimeError("C20 C5 tool identity mismatch")
    if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:
        raise RuntimeError("C20 C5 worktree is not clean")
    c5_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    c5_parent = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip()
    c5_freeze_paths = set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines())
    if c5_parent != c5_spec["researchParentBeforePreregistration"] or c5_freeze_paths != set(c5_spec["freezePaths"]):
        raise RuntimeError("C20 C5 freeze commit mismatch")
    retained = RESEARCH / c5_spec["retainedEvidenceRoot"]
    retained_manifest = manifest(retained)
    if retained_manifest["manifestHash"] != c5_spec["retainedEvidenceManifestHash"]:
        raise RuntimeError("C20 C5 retained evidence drift")
    c4_retained_manifest = manifest(C4_RETAINED_EVIDENCE)
    if c4_retained_manifest["manifestHash"] != c5_spec["retainedC4EvidenceManifestHash"]:
        raise RuntimeError("C20 C5 retained C4 evidence drift")
    if C5_EVIDENCE.exists():
        raise RuntimeError("C20 C5 evidence root is not fresh")
    C5_EVIDENCE.mkdir(parents=True, exist_ok=False)
    scope = {
        "schemaVersion": "bfs.rc6RealImpactLiquidParticleRadiusC20C5Admission.v0.1",
        "status": "PASS",
        "executionCommit": c5_head,
        "retainedEvidenceManifestHash": retained_manifest["manifestHash"],
        "retainedC4EvidenceManifestHash": c4_retained_manifest["manifestHash"],
        "counts": c5_spec["counts"],
    }
    write_exclusive(C5_EVIDENCE / "admission.json", scope)
    shared_environment = dict(globals())
    shared_environment.update(locals())
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C5", "exec"), shared_environment, shared_environment)
    audit = json.loads((C5_EVIDENCE / "audit.json").read_text())
    receipt = {
        "schemaVersion": "bfs.rc6RealImpactLiquidParticleRadiusC20C5Receipt.v0.1",
        "status": audit["status"],
        "executionCommit": c5_head,
        "auditHash": audit["auditHash"],
        "retainedResultHash": audit["resultHash"],
        "retainedReceiptHash": audit["receiptHash"],
        "counts": c5_spec["counts"],
        "claimCeiling": c5_spec["claimCeiling"],
    }
    receipt["receiptHash"] = self_hash(receipt, "receiptHash")
    write_exclusive(C5_EVIDENCE / "receipt.json", receipt)
    write_exclusive(C5_EVIDENCE / "evidence-manifest.json", manifest(C5_EVIDENCE))
    print("RC6_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20_C5_RECEIPT=" + canonical(receipt), flush=True)


if __name__ == "__main__":
    main()
