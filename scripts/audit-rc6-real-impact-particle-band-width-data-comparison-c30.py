#!/usr/bin/env python3
"""Independently audit copied C29 Data/Mesh against retained C18/C19."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-water-diffusion-data-comparison-c27.py")
EXPECTED_BASE_SHA256 = "f161a8ad28f40582623a48d8960d64105c5481c8bf18ee30d629181d52172cea"


def replace_exact(source, before, after, label, expected=1):
    count = source.count(before)
    if count != expected:
        raise RuntimeError(f"C30 auditor {label} target mismatch: {count} != {expected}")
    return source.replace(before, after)


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C30 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c27_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()

    source = replace_exact(source, 'C26_C2_AUDIT = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-audit-c2-attempt-106/audit.json"\n', '', "remove inapplicable C2 constant")
    source = replace_exact(source, 'c26_c2_audit = json.loads(C26_C2_AUDIT.read_text())\n', '', "remove C2 load")
    old_evidence = 'sha(ATTEMPT104_ROOT / "result.json") == spec["baseline"]["attempt104ResultFileSha256"] and attempt104["resultHash"] == spec["baseline"]["attempt104ResultHash"] and sha(ATTEMPT104_ROOT / "receipt.json") == spec["baseline"]["attempt104ReceiptFileSha256"] and attempt104_receipt["receiptHash"] == spec["baseline"]["attempt104ReceiptHash"] and sha(ATTEMPT104_ROOT / "independent-audit.json") == spec["baseline"]["attempt104AuditFileSha256"] and attempt104_audit["auditHash"] == spec["baseline"]["attempt104AuditHash"] and attempt104_audit["status"] == "FAIL" and sha(C26_C2_AUDIT) == spec["baseline"]["attempt104C2AuditFileSha256"] and c26_c2_audit["auditHash"] == spec["baseline"]["attempt104C2AuditHash"] and c26_c2_audit["status"] == "PASS_AUDIT_ONLY_PHYSICAL_FAIL_RETAINED"'
    new_evidence = 'sha(ATTEMPT104_ROOT / "result.json") == spec["baseline"]["attempt104ResultFileSha256"] and attempt104["resultHash"] == spec["baseline"]["attempt104ResultHash"] and sha(ATTEMPT104_ROOT / "receipt.json") == spec["baseline"]["attempt104ReceiptFileSha256"] and attempt104_receipt["receiptHash"] == spec["baseline"]["attempt104ReceiptHash"] and sha(ATTEMPT104_ROOT / "independent-audit.json") == spec["baseline"]["attempt104AuditFileSha256"] and attempt104_audit["auditHash"] == spec["baseline"]["attempt104AuditHash"] and attempt104_audit["status"] == "PASS"'
    source = replace_exact(source, old_evidence, new_evidence, "C29 accepted evidence")

    replacements = (
        ("RC6-2026-09-02-real-impact-water-diffusion-data-comparison-c27-attempt-107", "RC6-2026-09-02-real-impact-particle-band-width-data-comparison-c30-attempt-109", "fresh roots", 2),
        ("RC6-2026-09-02-real-impact-liquid-water-diffusion-c26-attempt-104", "RC6-2026-09-02-real-impact-liquid-particle-band-width-c29-attempt-108", "C29 cache/evidence", 2),
        ("scripts/analyze-rc6-real-impact-water-diffusion-data-comparison-c27.py", "scripts/analyze-rc6-real-impact-particle-band-width-data-comparison-c30.py", "analyzer path", 1),
        ("scripts/run-rc6-real-impact-water-diffusion-data-comparison-c27.py", "scripts/run-rc6-real-impact-particle-band-width-data-comparison-c30.py", "runner path", 1),
        ("specs/ai-native-studio-rc6-real-impact-water-diffusion-data-comparison-c27.v1.18.json", "specs/ai-native-studio-rc6-real-impact-particle-band-width-data-comparison-c30.v1.20.json", "spec path", 1),
        ("ATTEMPT104", "ATTEMPT108", "attempt constant", 8),
        ("attempt104", "attempt108", "attempt fields", 18),
        ("C26", "C29", "experiment labels", 4),
        ("C27", "C30", "diagnostic labels", 3),
        ("WATER_DIFFUSION", "PARTICLE_BAND_WIDTH", "status tokens", 2),
        ("WaterDiffusion", "ParticleBandWidth", "schema token", 1),
    )
    for before, after, label, expected in replacements:
        source = replace_exact(source, before, after, label, expected)
    source = replace_exact(
        source,
        'expansion = rules["expansionThresholdFraction"]\n',
        'expansion = rules["expansionThresholdFraction"]\nloss = rules["lossThresholdFraction"]\n',
        "loss threshold",
    )
    loss_anchor = 'c18_first_mesh = first_frame(c18_window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)\n'
    loss_extension = loss_anchor + (
        'first_velocity_loss = first_frame(window, lambda row: row["velocityOccupancyDriftFromBaselineFraction"] < -loss)\n'
        'first_data_loss = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] < -loss)\n'
        'first_mesh_loss = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] < -loss)\n'
        'c18_first_velocity_loss = first_frame(c18_window, lambda row: row["velocityOccupancyDriftFromBaselineFraction"] < -loss)\n'
        'c18_first_data_loss = first_frame(c18_window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] < -loss)\n'
        'c18_first_mesh_loss = first_frame(c18_window, lambda row: row["meshVolumeDriftFromBaselineFraction"] < -loss)\n'
    )
    source = replace_exact(source, loss_anchor, loss_extension, "loss onsets")
    old_classification = '''if all(value is not None for value in current_onsets + c18_onsets) and all(a <= b for a, b in zip(current_onsets, c18_onsets)) and any(a < b for a, b in zip(current_onsets, c18_onsets)) and all(a > b for a, b in zip(current_amplitudes, c18_amplitudes)):
    classification = "C29_EARLIER_AND_MORE_SEVERE_THAN_C18"
elif current_onsets == c18_onsets and all(a > b for a, b in zip(current_amplitudes, c18_amplitudes)):
    classification = "C29_SAME_ONSET_MORE_SEVERE_THAN_C18"
elif all(a <= b for a, b in zip(current_amplitudes, c18_amplitudes)):
    classification = "C29_NO_MORE_SEVERE_THAN_C18"
else:
    classification = "MIXED_ONSET_AMPLITUDE_RESPONSE"'''
    new_classification = '''if first_data_loss is not None and first_mesh_loss is not None:
    classification = "PARTICLE_AND_MESH_SUPPORT_LOSS"
elif first_mesh_loss is not None:
    classification = "MESH_LOSS_WITHOUT_PARTICLE_SUPPORT_LOSS"
elif first_data_loss is not None:
    classification = "PARTICLE_SUPPORT_LOSS_WITHOUT_MESH_LOSS"
else:
    classification = "NO_FIFTEEN_PERCENT_DATA_OR_MESH_LOSS"'''
    source = replace_exact(source, old_classification, new_classification, "loss classification")
    metrics_anchor = '    "c18FirstMeshExpansionFrame": c18_first_mesh,\n'
    metrics_extension = metrics_anchor + (
        '    "firstVelocityLossFrame": first_velocity_loss,\n'
        '    "firstDataLossFrame": first_data_loss,\n'
        '    "firstMeshLossFrame": first_mesh_loss,\n'
        '    "c18FirstVelocityLossFrame": c18_first_velocity_loss,\n'
        '    "c18FirstDataLossFrame": c18_first_data_loss,\n'
        '    "c18FirstMeshLossFrame": c18_first_mesh_loss,\n'
        '    "minimumParticleOccupancyDriftFraction": min(row["particleOccupancyDriftFromBaselineFraction"] for row in window),\n'
        '    "minimumVelocityOccupancyDriftFraction": min(row["velocityOccupancyDriftFromBaselineFraction"] for row in window),\n'
        '    "minimumMeshVolumeDriftFraction": min(row["meshVolumeDriftFromBaselineFraction"] for row in window),\n'
    )
    return replace_exact(source, metrics_anchor, metrics_extension, "loss metrics")


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_BAND_WIDTH_DATA_COMPARISON_C30", "exec"), globals(), globals())
