#!/usr/bin/env python3
"""Adapt C19 analysis to compare copied C20 Data/Mesh with retained C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-fractions-threshold-data-comparison-c19.py")
EXPECTED_BASE_SHA256 = "d28b55e9d22a8d2f4762bb3947ef262fb35ece85ac7ce5793152d55e4ae3463d"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C21 analyzer base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c19_analyzer_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ('"""Measure copied C18 Data support and transition order against retained C14/C15."""', '"""Measure copied C20 Data support and transition order against retained C18/C19."""', "docstring", 1),
        ("attempt90", "attempt94", "C20 result binding", 8),
        ("c15", "c19", "C19 baseline binding", 10),
        ("C15", "C21", "C21 diagnostics", 4),
        ("c14", "c18", "C18 sample fields", 6),
        ("C14", "C18", "C18 labels", 1),
        ('"FAIL_REAL_IMPACT_LIQUID_FRACTIONS_THRESHOLD_C18"', '"FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20"', "C20 verdict", 1),
        ('"bfs.rc6RealImpactFractionsThresholdDataComparisonC19Result.v0.1"', '"bfs.rc6RealImpactParticleRadiusDataComparisonC21Result.v0.1"', "result schema", 1),
        ('"MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON"', '"MEASURED_PARTICLE_RADIUS_DATA_MESH_COMPARISON"', "result status", 2),
        ('"Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. C18-versus-C18 transition order measures where the threshold response begins without proving a mechanism or repair."', '"Saved terminal substep is diagnostic metadata, not a solver-step count. Occupied Data support is not exact liquid mass. C20-versus-C18 onset and amplitude test whether the smaller simulation radius changes failure timing, severity or both without proving one internal operation."', "interpretation", 1),
        ("RC6_REAL_IMPACT_FRACTIONS_THRESHOLD_DATA_COMPARISON_C19=", "RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21=", "result marker", 1),
        ("C19 analysis harness failed", "C21 analysis harness failed", "failure marker", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C21 analyzer {label} target mismatch: {source.count(before)} != {expected}")
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
expansion = rules["expansionThresholdFraction"]
intrusion = rules["cupIntrusionThresholdFraction"]
first_data = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > expansion)
first_mesh = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)
'''
    rules_extension = '''rules = spec["classificationRules"]
expansion = rules["expansionThresholdFraction"]
intrusion = rules["cupIntrusionThresholdFraction"]
c18_window = [row for row in c19["samples"] if row["frame"] >= measurement["comparisonFrameStart"]]
first_velocity = first_frame(window, lambda row: row["velocityOccupancyDriftFromBaselineFraction"] > expansion)
first_data = first_frame(window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > expansion)
first_mesh = first_frame(window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)
c18_first_velocity = first_frame(c18_window, lambda row: row["velocityOccupancyDriftFromBaselineFraction"] > expansion)
c18_first_data = first_frame(c18_window, lambda row: row["particleOccupancyDriftFromBaselineFraction"] > expansion)
c18_first_mesh = first_frame(c18_window, lambda row: row["meshVolumeDriftFromBaselineFraction"] > expansion)
'''
    classification_old = '''if (
    first_intrusion is not None
    and first_data is not None
    and first_mesh is not None
    and first_intrusion < first_data <= first_mesh
    and particle_mesh_correlation >= rules["minimumStrongCorrelation"]
):
    classification = "CUP_INTRUSION_PRECEDES_LATER_DATA_MESH_EXPANSION"
elif (
    first_data is not None
    and first_mesh is not None
    and first_data <= first_mesh
    and particle_mesh_correlation >= rules["minimumStrongCorrelation"]
):
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
    check_old = '''    "attempt94FailureBound": attempt94["resultHash"] == spec["baseline"]["attempt94ResultHash"] and attempt94["verdict"] == "FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20",
    "c19DiagnosticBound": c19["resultHash"] == spec["baseline"]["c19ResultHash"] and c19["classification"] == "TRANSITION_ORDER_INCONCLUSIVE",
'''
    check_new = '''    "attempt94FailureBound": attempt94["resultHash"] == spec["baseline"]["attempt94ResultHash"] and attempt94["verdict"] == "FAIL_REAL_IMPACT_LIQUID_PARTICLE_RADIUS_C20",
    "c19DiagnosticBound": c19["resultHash"] == spec["baseline"]["c19ResultHash"] and c19["status"] == "MEASURED_FRACTIONS_THRESHOLD_DATA_MESH_COMPARISON" and c19["classification"] == "TRANSITION_ORDER_INCONCLUSIVE",
    "comparisonOnsetsDerived": all(value is None or measurement["comparisonFrameStart"] <= value <= measurement["frameEnd"] for value in current_onsets + c18_onsets),
'''
    for before, after, label in (
        (sample_anchor, sample_extension, "C18 prior sample extension"),
        (rules_anchor, rules_extension, "velocity and C18 onset derivation"),
        (classification_old, classification_new, "comparative classification"),
        (metrics_anchor, metrics_extension, "onset metrics"),
        (metrics_tail_old, metrics_tail_new, "C18 amplitude metrics"),
        (check_old, check_new, "bound comparison checks"),
    ):
        if source.count(before) != 1:
            raise RuntimeError(f"C21 analyzer {label} target mismatch: {source.count(before)}")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_RADIUS_DATA_COMPARISON_C21", "exec"), globals(), globals())
