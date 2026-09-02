#!/usr/bin/env python3
"""Audit corrected C24 comparison and retained attempt-102."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("audit-rc6-real-impact-particle-maximum-data-comparison-c24.py")
EXPECTED_BASE_SHA256 = "dc36fe8caaf89301e626715dc85cca7f68db1ab6339f3fc180b153b147424eb0"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C24 C1 auditor base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c24_auditor_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102", "RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-c1-attempt-103", "fresh roots", 2),
        ('"scripts/analyze-rc6-real-impact-particle-maximum-data-comparison-c24.py"', '"scripts/analyze-rc6-real-impact-particle-maximum-data-comparison-c24-c1.py"', "analyzer path", 1),
        ('"scripts/run-rc6-real-impact-particle-maximum-data-comparison-c24.py"', '"scripts/run-rc6-real-impact-particle-maximum-data-comparison-c24-c1.py"', "runner path", 1),
        ('"specs/ai-native-studio-rc6-real-impact-particle-maximum-data-comparison-c24.v1.13.json"', '"specs/ai-native-studio-rc6-real-impact-particle-maximum-data-comparison-c24-c1.v1.14.json"', "spec path", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C24 C1 auditor {label} target mismatch")
        source = source.replace(before, after)
    constant_anchor = 'SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-particle-maximum-data-comparison-c24-c1.v1.14.json"\n'
    constant_extension = constant_anchor + (
        'ATTEMPT102_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102")\n'
        'ATTEMPT102_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102"\n'
    )
    check_anchor = '    "noSymlinksOrMedia": not any(path.is_symlink() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".exr", ".mov", ".mp4"} for root in (WORK, EVIDENCE) for path in root.rglob("*")),\n'
    check_extension = check_anchor + '    "retainedAttempt102Exact": manifest(ATTEMPT102_WORK)["manifestHash"] == spec["retainedAttempt102"]["workManifestHash"] and manifest(ATTEMPT102_EVIDENCE)["manifestHash"] == spec["retainedAttempt102"]["evidenceManifestHash"],\n'
    for before, after, label in (
        (constant_anchor, constant_extension, "retained constants"),
        (check_anchor, check_extension, "retained check"),
    ):
        if source.count(before) != 1:
            raise RuntimeError(f"C24 C1 auditor {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_MAXIMUM_DATA_COMPARISON_C24_C1", "exec"), globals(), globals())
