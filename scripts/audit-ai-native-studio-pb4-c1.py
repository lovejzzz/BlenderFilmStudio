#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BlenderFilmStudio Authors
# SPDX-License-Identifier: GPL-2.0-or-later

"""PB.4 C1 audit-only correction for Python/Node JSON number spelling."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parent.parent
SPEC_URI = "specs/ai-native-studio-pb4-c1-canonical-audit.v0.2.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root differs: {path}")
    return value


def valid_self(value, field):
    expected = value.get(field)
    body = dict(value)
    body.pop(field, None)
    return isinstance(expected, str) and sha256_bytes(canonical(body)) == expected


def self_hashed(value, field):
    body = dict(value)
    body.pop(field, None)
    body[field] = sha256_bytes(canonical(body))
    return body


def write_json_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def file_manifest(root):
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append({
            "uri": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return rows


def git(*args):
    result = subprocess.run(
        ["/usr/bin/git", *args],
        cwd=REPOSITORY,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def execute():
    spec_path = REPOSITORY / SPEC_URI
    spec = read_json(spec_path)
    if not valid_self(spec, "specHash"):
        raise RuntimeError("C1 spec self hash differs")
    if sha256_file(Path(__file__).resolve()) != spec["tool"]["auditorSha256"]:
        raise RuntimeError("C1 auditor identity differs")
    retained = (REPOSITORY / spec["retainedAttempt"]["root"]).resolve(strict=True)
    output = (REPOSITORY / spec["freshEvidenceRoot"]).resolve(strict=False)
    if output.exists():
        raise RuntimeError("C1 evidence root is not fresh")
    if git("diff", "--name-only", spec["retainedAttempt"]["commit"], "HEAD", "--", spec["retainedAttempt"]["root"]):
        raise RuntimeError("Retained attempt changed after its freeze commit")
    retained_manifest = file_manifest(retained)
    retained_manifest_hash = sha256_bytes(canonical(retained_manifest))
    if retained_manifest_hash != spec["retainedAttempt"]["rootManifestSha256"]:
        raise RuntimeError("Retained attempt full-root manifest differs")

    receipt = read_json(retained / "receipt.json")
    pixel_audit = read_json(retained / "pixel-pass-audit.json")
    preview_receipt = read_json(retained / "preview/receipt.json")
    final_receipt = read_json(retained / "final/receipt.json")
    cost = read_json(retained / "cost.json")
    processes = [read_json(path) for path in sorted((retained / "processes").glob("*.json"))]
    failures = [read_json(path) for path in sorted((retained / "failures").glob("*.json"))]
    preview = retained / preview_receipt["output"]["uri"]
    final = retained / final_receipt["output"]["uri"]
    source = Path(spec["source"]["absolutePath"]).resolve(strict=True)
    binary = Path(spec["binary"]["absolutePath"]).resolve(strict=True)
    png_header = preview.read_bytes()[:24]
    png_dimensions = struct.unpack(">II", png_header[16:24]) if png_header[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)

    receipt_false = sorted(name for name, passed in receipt["checks"].items() if not passed)
    embedded_groups = (
        pixel_audit["sourceChecks"],
        pixel_audit["receiptChecks"],
        pixel_audit["processChecks"],
        pixel_audit["pixelChecks"],
        pixel_audit["failureChecks"],
    )
    checks = {
        "retainedCommitAncestor": subprocess.run(
            ["/usr/bin/git", "merge-base", "--is-ancestor", spec["retainedAttempt"]["commit"], "HEAD"],
            cwd=REPOSITORY,
            check=False,
        ).returncode == 0,
        "retainedRootManifestExact": retained_manifest_hash == spec["retainedAttempt"]["rootManifestSha256"] and len(retained_manifest) == spec["retainedAttempt"]["files"],
        "retainedFinalReceiptExact": sha256_file(retained / "receipt.json") == spec["retainedAttempt"]["receiptFileSha256"] and receipt["receiptHash"] == spec["retainedAttempt"]["receiptHash"],
        "retainedReceiptSelfHash": valid_self(receipt, "receiptHash"),
        "onlyWrapperCheckFailed": receipt["status"] == "FAIL" and receipt["verdict"] == "FAIL" and receipt_false == ["pixelPassAudit"],
        "pythonProducerAuditExact": sha256_file(retained / "pixel-pass-audit.json") == spec["retainedAttempt"]["pixelAuditFileSha256"] and pixel_audit["auditHash"] == spec["retainedAttempt"]["pixelAuditHash"],
        "pythonProducerAuditSelfHash": valid_self(pixel_audit, "auditHash"),
        "pixelAuditStatusPass": pixel_audit["status"] == "PASS" and pixel_audit["renderCalls"] == 0,
        "allEmbeddedAuditChecksTrue": all(all(group.values()) for group in embedded_groups),
        "fourProcessReceipts": len(processes) == 4 and all(valid_self(row, "processHash") and row["status"] == "PASS" and row["exitCode"] == 0 for row in processes),
        "eightProcessLogsBound": all(
            sha256_file(retained / "logs" / f"0{index}-{name}.stdout.log") == row["stdoutSha256"]
            and sha256_file(retained / "logs" / f"0{index}-{name}.stderr.log") == row["stderrSha256"]
            for index, (name, row) in enumerate(zip(("inspect-negative", "preview", "final", "independent-audit"), processes), 1)
        ),
        "productStartsAndRenderCallsExact": len(processes) == 4 and sum(row["payload"]["renderCalls"] for row in processes) == 2,
        "threeFailureReceipts": len(failures) == 3 and all(valid_self(row, "failureHash") and row["status"] == "REJECTED" and row["process"]["renderCalls"] == 0 and row["source"]["unchanged"] is True for row in failures),
        "previewReceiptSelfHash": valid_self(preview_receipt, "receiptHash") and preview_receipt["status"] == "PASS",
        "finalReceiptSelfHash": valid_self(final_receipt, "receiptHash") and final_receipt["status"] == "PASS",
        "previewArtifactExact": sha256_file(preview) == spec["artifacts"]["previewSha256"] == preview_receipt["output"]["sha256"] and preview.stat().st_size == preview_receipt["output"]["bytes"],
        "previewPngDimensions": png_dimensions == (640, 360),
        "finalArtifactExact": sha256_file(final) == spec["artifacts"]["finalSha256"] == final_receipt["output"]["sha256"] and final.stat().st_size == final_receipt["output"]["bytes"],
        "finalExrMagic": final.read_bytes()[:4] == b"v/1\x01",
        "costReceipt": valid_self(cost, "costHash") and cost["monetaryCostUsd"] == 0 and cost["productStarts"] == 4 and cost["renderCalls"] == 2,
        "sourceBlendExact": sha256_file(source) == spec["source"]["sha256"],
        "binaryExact": sha256_file(binary) == spec["binary"]["sha256"],
        "officialConfigurationUnchanged": receipt["checks"]["officialConfigUnchanged"] is True and receipt["officialConfiguration"]["before"] == receipt["officialConfiguration"]["after"],
        "resourcesWithinFrozenCeilings": receipt["checks"]["workCeiling"] is True and receipt["checks"]["evidenceCeiling"] is True,
        "zeroNewBuildStartRenderOrMutation": all(spec["counters"][name] == 0 for name in spec["counters"]),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    output.mkdir(parents=False)
    audit_body = {
        "schemaVersion": "bfs.pb4C1CanonicalAudit.v0.2",
        "status": status,
        "correction": "Validate the Python-produced audit using its declared Python canonical JSON number spelling instead of Node parse/reserialize spelling.",
        "retainedRoot": spec["retainedAttempt"]["root"],
        "retainedRootManifestSha256": retained_manifest_hash,
        "checksPassed": sum(checks.values()),
        "checksTotal": len(checks),
        "checks": checks,
        "counters": spec["counters"],
        "claim": "PB.4 attempt-01 product output and independent audit are accepted as a composite result; the retained wrapper receipt remains FAIL and is not rewritten.",
    }
    audit = self_hashed(audit_body, "auditHash")
    write_json_exclusive(output / "audit.json", audit)
    output_manifest_rows = file_manifest(output)
    root_manifest = self_hashed({
        "schemaVersion": "bfs.pb4C1RootManifest.v0.2",
        "status": "PASS",
        "scope": "Fresh C1 evidence files before this manifest and final receipt.",
        "entries": output_manifest_rows,
    }, "manifestHash")
    write_json_exclusive(output / "root-manifest.json", root_manifest)
    receipt_body = {
        "schemaVersion": "bfs.pb4C1ValidationReceipt.v0.2",
        "status": status,
        "verdict": status,
        "retainedAttemptReceiptHash": receipt["receiptHash"],
        "retainedPixelAuditHash": pixel_audit["auditHash"],
        "auditHash": audit["auditHash"],
        "rootManifestHash": root_manifest["manifestHash"],
        "counters": spec["counters"],
        "claimCeiling": "One B01 workspace, one admitted arm64 host, frozen preview/final profiles; no distribution, production, cross-platform or autonomous-filmmaking claim.",
    }
    correction_receipt = self_hashed(receipt_body, "receiptHash")
    write_json_exclusive(output / "receipt.json", correction_receipt)
    if status != "PASS":
        raise RuntimeError("PB.4 C1 audit failed: " + ",".join(name for name, passed in checks.items() if not passed))
    print(f"PB4_C1_PASS checks={sum(checks.values())}/{len(checks)} receiptHash={correction_receipt['receiptHash']}")


def self_test():
    sample = self_hashed({"schemaVersion": "sample", "value": 0.0}, "sampleHash")
    checks = {
        "pythonFloatSpellingRetained": canonical({"value": 0.0}) == b'{"value":0.0}',
        "selfHash": valid_self(sample, "sampleHash"),
        "freshRootAbsent": not (REPOSITORY / "experiments/ai-native-studio-phase-b/PB.4-2026-08-31-mac-m2max-attempt-02").exists(),
        "noProductImport": "film_studio_render" not in globals(),
    }
    print(json.dumps({"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if "--self-test" in sys.argv:
    self_test()
elif "--execute" in sys.argv:
    execute()
else:
    raise SystemExit("Use --self-test or --execute")
