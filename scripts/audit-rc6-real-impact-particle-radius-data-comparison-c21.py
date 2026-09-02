#!/usr/bin/env python3
"""Independently audit copied C20 Data/Mesh against retained C18/C19."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-fractions-threshold-data-comparison-c19.py")
EXPECTED_BASE_SHA256 = "98951286ccea830da4070e21be4c7152303eb8704dbd9ce98ae5434f3a057159"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C21 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c19_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ('"""Independently audit copied C18 Data/Mesh against retained C14/C15."""', '"""Independently audit copied C20 Data/Mesh against retained C18/C19."""', "docstring", 1),
        ("RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92", "RC6-2026-09-02-real-impact-particle-radius-data-comparison-c21-attempt-99", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-attempt-90", "RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c1-attempt-94", "C20 cache/evidence", 2),
        ('C15_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-c14-transition-c15-attempt-87"', 'C19_ROOT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-fractions-threshold-data-comparison-c19-attempt-92"', "C19 root", 1),
        ('C18_C1_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-fractions-threshold-c18-audit-c1-attempt-91/audit.json"', 'C20_C5_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/audit.json"', "C20 C5 audit", 1),
        ('"scripts/analyze-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', '"scripts/analyze-rc6-real-impact-particle-radius-data-comparison-c21.py"', "analyzer", 1),
        ('"scripts/run-rc6-real-impact-fractions-threshold-data-comparison-c19.py"', '"scripts/run-rc6-real-impact-particle-radius-data-comparison-c21.py"', "runner", 1),
        ('"specs/ai-native-studio-rc6-real-impact-fractions-threshold-data-comparison-c19.v1.03.json"', '"specs/ai-native-studio-rc6-real-impact-particle-radius-data-comparison-c21.v1.10.json"', "spec", 1),
        ("attempt90", "attempt94", "C20 result keys", 19),
        ("ATTEMPT90", "ATTEMPT94", "C20 result constant", 8),
        ("C15_ROOT", "C19_ROOT", "C19 constant uses", 7),
        ("c15", "c19", "C19 baseline values", 18),
        ("c14", "c18", "C18 sample fields", 6),
        ("C18_C1_AUDIT", "C20_C5_AUDIT", "C20 audit uses", 2),
        ("c18_c1_audit", "c20_c5_audit", "C20 audit value", 3),
        ("attempt94C1", "attempt94C5", "C20 C5 baseline keys", 2),
        ('"PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED"', '"PASS"', "C20 C5 audit status", 1),
        ('"MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON"', '"MEASURED_PARTICLE_RADIUS_DATA_MESH_COMPARISON"', "result status", 1),
        ('"bfs.rc6RealImpactFractionsThresholdDataComparisonC19IndependentAudit.v0.1"', '"bfs.rc6RealImpactParticleRadiusDataComparisonC21IndependentAudit.v0.1"', "audit schema", 1),
        ("RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19_AUDIT=", "RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21_AUDIT=", "audit marker", 1),
        ("C19 independent audit failed", "C21 independent audit failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C21 auditor {label} target mismatch: {source.count(before)} != {expected}")
        source = source.replace(before, after)

    sample_anchor = '''        "c18ParticleOccupiedVoxelCount": prior["particleOccupiedVoxelCount"],
        "c18MeshVolumeCubicMeters": prior["meshVolumeCubicMeters"],
'''
    sample_extension = '''        "c18ParticleOccupiedVoxelCount": prior["particleOccupiedVoxelCount"],
        "c18VelocityOccupiedVoxelCount": prior["velocityOccupiedVoxelCount"],
        "c18MeshVolumeCubicMeters": prior["meshVolumeCubicMeters"],
        "c18ParticleOccupancyDriftFromBaselineFraction": prior["particleOccupancyDriftFromBaselineFraction"],
        "c18VelocityOccupancyDriftFromBaselineFraction": prior["velocityOccupancyDriftFromBaselineFraction"],
        "c18MeshVolumeDriftFromBaselineFraction": prior["meshVolumeDriftFromBaselineFraction"],
'''
    rules_anchor = '''rules = spec["classificationRules"]
first_data = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > rules["expansionThresholdFraction"])
first_mesh = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > rules["expansionThresholdFraction"])
'''
    rules_extension = '''rules = spec["classificationRules"]
expansion = rules["expansionThresholdFraction"]
c18_window = [row for row in c19["samples"] if row["frame"] >= measurement["comparisonFrameStart"]]
first_velocity = first_frame(window, lambda row: row["velocityOccupancyDriftFromBaselineFraction"] > expansion)
first_data = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > expansion)
first_mesh = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)
c18_first_velocity = first_frame(c18_window, lambda row: row["velocityOccupancyDriftFromBaselineFraction"] > expansion)
c18_first_data = first_frame(c18_window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > expansion)
c18_first_mesh = first_frame(c18_window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)
'''
    classification_old = '''if first_intrusion is not None and first_data is not None and first_mesh is not None and first_intrusion < first_data <= first_mesh and particle_corr >= rules["minimumStrongCorrelation"]:
    classification = "CUP_INTRUSION_PRECEDES_LATER_DATA_MESH_EXPANSION"
elif first_data is not None and first_mesh is not None and first_data <= first_mesh and particle_corr >= rules["minimumStrongCorrelation"]:
    classification = "DATA_MESH_EXPANSION_WITHOUT_PRIOR_CUP_INTRUSION"
elif first_data is None and first_mesh is not None:
    classification = "DATA_SUPPORT_STABLE_MESH_RECONSTRUCTION_SUSPECTED"
else:
    classification = "TRANSITION_ORDER_INCONCLUSIVE"
'''
    classification_new = '''current_onsets = (first_velocity, first_data, first_mesh)
c18_onsets = (c18_first_velocity, c18_first_data, c18_first_mesh)
current_amplitudes = (
    max(row["velocityOccupancyDriftFromBaselineFraction"] for row in window),
    max(row["particleOccupancyDriftFromBaselineFraction"] for row in window),
    max(row["meshVolumeDriftFromBaselineFraction"] for row in window),
)
c18_amplitudes = (
    max(row["velocityOccupancyDriftFromBaselineFraction"] for row in c18_window),
    max(row["particleOccupancyDriftFromBaselineFraction"] for row in c18_window),
    max(row["meshVolumeDriftFromBaselineFraction"] for row in c18_window),
)
if all(value is not None for value in current_onsets + c18_onsets) and all(a <= b for a, b in zip(current_onsets, c18_onsets)) and any(a < b for a, b in zip(current_onsets, c18_onsets)) and all(a > b for a, b in zip(current_amplitudes, c18_amplitudes)):
    classification = "C20_EARLIER_AND_MORE_SEVERE_THAN_C18"
elif current_onsets == c18_onsets and all(a > b for a, b in zip(current_amplitudes, c18_amplitudes)):
    classification = "C20_SAME_ONSET_MORE_SEVERE_THAN_C18"
elif all(a <= b for a, b in zip(current_amplitudes, c18_amplitudes)):
    classification = "C20_NO_MORE_SEVERE_THAN_C18"
else:
    classification = "MIXED_ONSET_AMPLITUDE_RESPONSE"
'''
    metrics_anchor = '''    "firstCupSolidIntrusionFrame": first_intrusion,
    "firstDataExpansionFrame": first_data,
    "firstMeshExpansionFrame": first_mesh,
'''
    metrics_extension = '''    "firstCupSolidIntrusionFrame": first_intrusion,
    "firstVelocityExpansionFrame": first_velocity,
    "firstDataExpansionFrame": first_data,
    "firstMeshExpansionFrame": first_mesh,
    "c18FirstVelocityExpansionFrame": c18_first_velocity,
    "c18FirstDataExpansionFrame": c18_first_data,
    "c18FirstMeshExpansionFrame": c18_first_mesh,
'''
    metrics_tail_old = '''    "c18FirstDataExpansionFrame": c19["metrics"]["firstDataExpansionFrame"],
    "c18FirstMeshExpansionFrame": c19["metrics"]["firstMeshExpansionFrame"],
'''
    metrics_tail_new = '''    "c18MaximumParticleOccupancyExpansionFraction": c19["metrics"]["maximumParticleOccupancyExpansionFraction"],
    "c18MaximumVelocityOccupancyExpansionFraction": c19["metrics"]["maximumVelocityOccupancyExpansionFraction"],
    "c18MaximumMeshVolumeExpansionFraction": c19["metrics"]["maximumMeshVolumeExpansionFraction"],
'''
    for before, after, label in (
        (sample_anchor, sample_extension, "C18 prior sample extension"),
        (rules_anchor, rules_extension, "velocity and C18 onset derivation"),
        (classification_old, classification_new, "comparative classification"),
        (metrics_anchor, metrics_extension, "onset metrics"),
        (metrics_tail_old, metrics_tail_new, "C18 amplitude metrics"),
    ):
        if source.count(before) != 1:
            raise RuntimeError(f"C21 auditor {label} target mismatch: {source.count(before)}")
        source = source.replace(before, after)
    constant_anchor = 'C20_C5_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/audit.json"\n'
    constant_extension = constant_anchor + 'C20_C5_RECEIPT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-particle-radius-c20-c5-audit-attempt-98/receipt.json"\n'
    load_anchor = 'c20_c5_audit = json.loads(C20_C5_AUDIT.read_text())\n'
    load_extension = load_anchor + 'c20_c5_receipt = json.loads(C20_C5_RECEIPT.read_text())\n'
    evidence_anchor = 'and sha(C20_C5_AUDIT) == spec["baseline"]["attempt94C5AuditFileSha256"] and c20_c5_audit["auditHash"] == spec["baseline"]["attempt94C5AuditHash"] and c20_c5_audit["status"] == "PASS"'
    evidence_extension = evidence_anchor + ' and sha(C20_C5_RECEIPT) == spec["baseline"]["attempt94C5ReceiptFileSha256"] and c20_c5_receipt["receiptHash"] == spec["baseline"]["attempt94C5ReceiptHash"] and c20_c5_receipt["status"] == "PASS"'
    check_anchor = '    "classificationRecomputed": result["status"] == "MEASURED_PARTICLE_RADIUS_DATA_MESH_COMPARISON" and result["classification"] == classification == receipt["classification"],\n'
    check_extension = '''    "resultChecksExact": result["checks"] == {
        "openVdbIdentityExact": True,
        "all36FramesMeasured": True,
        "exactGridRosterEveryFrame": True,
        "exactVoxelSizeEveryFrame": True,
        "attempt94FailureBound": True,
        "c19DiagnosticBound": True,
        "comparisonOnsetsDerived": True,
        "coherentBaselineFrameExact": True,
    },
''' + check_anchor
    execution_check_old = '    "executionCommitExact": receipt["researchExecutionCommit"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip(),\n'
    execution_check_new = '    "executionCommitExact": receipt["researchExecutionCommit"] == subprocess.run(["git", "rev-parse", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip() and subprocess.run(["git", "rev-parse", "HEAD^"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.strip() == spec["researchParentBeforePreregistration"] and set(subprocess.run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout.splitlines()) == set(spec["freezePaths"]),\n'
    for before, after, label in (
        (constant_anchor, constant_extension, "C5 receipt constant"),
        (load_anchor, load_extension, "C5 receipt load"),
        (evidence_anchor, evidence_extension, "C5 closure evidence"),
        (check_anchor, check_extension, "result checks"),
        (execution_check_old, execution_check_new, "freeze execution commit"),
    ):
        if source.count(before) != 1:
            raise RuntimeError(f"C21 auditor {label} target mismatch: {source.count(before)}")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21", "exec"), globals(), globals())
