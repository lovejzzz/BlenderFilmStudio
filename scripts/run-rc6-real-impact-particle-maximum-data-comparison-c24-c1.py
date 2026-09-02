#!/usr/bin/env python3
"""Run corrected C24 comparison in fresh roots and bind attempt-102."""

import hashlib
import importlib.util
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-real-impact-particle-maximum-data-comparison-c24.py")
EXPECTED_BASE_SHA256 = "8b7d6189a19b22d62f9fcb26b757abf381f4916a49ea9a4b1e6262febcac2ef3"


def transformed_source():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
        raise RuntimeError("C24 C1 runner base identity mismatch")
    module_spec = importlib.util.spec_from_file_location("rc6_c24_runner_base", BASE)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    source = module.transformed_source()
    replacements = (
        ("RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102", "RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-c1-attempt-103", "fresh roots", 2),
        ('"scripts/analyze-rc6-real-impact-particle-maximum-data-comparison-c24.py"', '"scripts/analyze-rc6-real-impact-particle-maximum-data-comparison-c24-c1.py"', "analyzer path", 1),
        ('"scripts/audit-rc6-real-impact-particle-maximum-data-comparison-c24.py"', '"scripts/audit-rc6-real-impact-particle-maximum-data-comparison-c24-c1.py"', "auditor path", 1),
        ('"specs/ai-native-studio-rc6-real-impact-particle-maximum-data-comparison-c24.v1.13.json"', '"specs/ai-native-studio-rc6-real-impact-particle-maximum-data-comparison-c24-c1.v1.14.json"', "spec path", 1),
    )
    for before, after, label, expected in replacements:
        if source.count(before) != expected:
            raise RuntimeError(f"C24 C1 runner {label} target mismatch")
        source = source.replace(before, after)
    constant_anchor = 'SPEC = RESEARCH / "specs/ai-native-studio-rc6-real-impact-particle-maximum-data-comparison-c24-c1.v1.14.json"\n'
    constant_extension = constant_anchor + (
        'ATTEMPT102_WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102")\n'
        'ATTEMPT102_EVIDENCE = RESEARCH / "experiments/physical-richness/RC6-2026-09-02-real-impact-particle-maximum-data-comparison-c24-attempt-102"\n'
    )
    bind_anchor = 'if subprocess.run(["git", "status", "--porcelain"], cwd=RESEARCH, capture_output=True, text=True, check=True).stdout:\n'
    bind_extension = (
        'attempt102_work_before = manifest(ATTEMPT102_WORK)\n'
        'attempt102_evidence_before = manifest(ATTEMPT102_EVIDENCE)\n'
        'if attempt102_work_before["manifestHash"] != spec["retainedAttempt102"]["workManifestHash"] or attempt102_evidence_before["manifestHash"] != spec["retainedAttempt102"]["evidenceManifestHash"]:\n'
        '    raise RuntimeError("C24 C1 retained attempt-102 mismatch")\n'
        + bind_anchor
    )
    final_anchor = 'print("RC6_REAL_IMPACT_PARTICLE_MAXIMUM_DATA_COMPARISON_C24_RUN=" + canonical({"status": receipt["status"], "classification": receipt["classification"], "receiptHash": receipt["receiptHash"], "resultHash": result["resultHash"]}))\n'
    final_extension = (
        'if manifest(ATTEMPT102_WORK) != attempt102_work_before or manifest(ATTEMPT102_EVIDENCE) != attempt102_evidence_before:\n'
        '    raise RuntimeError("C24 C1 retained attempt-102 changed")\n'
        + final_anchor
    )
    for before, after, label in (
        (constant_anchor, constant_extension, "retained constants"),
        (bind_anchor, bind_extension, "retained pre-run binding"),
        (final_anchor, final_extension, "retained post-run binding"),
    ):
        if source.count(before) != 1:
            raise RuntimeError(f"C24 C1 runner {label} target mismatch")
        source = source.replace(before, after)
    return source


if __name__ == "__main__":
    exec(compile(transformed_source(), str(BASE) + "#RC6_REAL_IMPACT_PARTICLE_MAXIMUM_DATA_COMPARISON_C24_C1", "exec"), globals(), globals())
