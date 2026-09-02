#!/usr/bin/env python3
"""Adapt frozen C27 analyzer for C29 band width versus C18."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("analyze-rc6-real-impact-water-diffusion-data-comparison-c27.py")
EXPECTED_BASE_SHA256 = "084525c9547d96e4c953398e79b6095a9007fd73cfb4d3c92328af58b834c54f"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C30 analyzer base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c27_analyzer_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("attempt104", "attempt108", "current attempt", 8),
        ("C26", "C29", "current experiment", 6),
        ("C27", "C30", "diagnostic gate", 7),
        ("WATER_DIFFUSION", "PARTICLE_BAND_WIDTH", "status tokens", 4),
        ("WaterDiffusion", "ParticleBandWidth", "schema token", 1),
    )
    for before, after, label, expected in replacements:
        count = source.count(before)
        if count != expected:
            raise RuntimeError(f"C30 analyzer {label} target mismatch: {count} != {expected}")
        source = source.replace(before, after)
    old = "C29-versus-C18 onset and amplitude test whether Water-preset velocity diffusion changes failure timing, severity or both without proving one internal operation."
    new = "C29-versus-C18 onset and amplitude test whether the one-cell narrower continuing particle band changes Data support and Mesh loss timing, severity or both without treating occupied support as exact mass."
    if source.count(old) != 1:
        raise RuntimeError("C30 analyzer interpretation target mismatch")
    source = source.replace(old, new)
    source = source.replace(
        'expansion = rules["expansionThresholdFraction"]\nintrusion = rules["cupIntrusionThresholdFraction"]',
        'expansion = rules["expansionThresholdFraction"]\nloss = rules["lossThresholdFraction"]\nintrusion = rules["cupIntrusionThresholdFraction"]',
        1,
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
    source = source.replace(loss_anchor, loss_extension, 1)
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
    if source.count(old_classification) != 1:
        raise RuntimeError("C30 analyzer loss-classification target mismatch")
    source = source.replace(old_classification, new_classification)
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
    if source.count(metrics_anchor) != 1:
        raise RuntimeError("C30 analyzer loss-metrics target mismatch")
    return source.replace(metrics_anchor, metrics_extension)


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_BAND_WIDTH_DATA_COMPARISON_C30", "exec"), globals(), globals())
