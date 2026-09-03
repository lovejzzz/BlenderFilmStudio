#!/usr/bin/env python3
"""Close only C34's wrong-audit-interpreter defect against retained attempt115."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-phi-c34-c1.v1.27.json"
BASE_AUDITOR = ROOT / "scripts/audit-rc6-native-phi-c34.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    return digest(path.read_bytes())


def rows(root):
    result = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item)):
        if path.is_symlink():
            raise RuntimeError(f"retained symlink forbidden: {path}")
        if path.is_file():
            result.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": file_hash(path)})
    return result


def root_hash(root):
    return digest(canonical(rows(root)))


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def main():
    spec = json.loads(SPEC.read_text())
    body = dict(spec); expected = body.pop("specFileSha256")
    assert digest(canonical(body)) == expected
    for row in spec["inputs"] + spec["tools"]:
        path = Path(row["path"]) if row.get("absolute") else ROOT / row["path"]
        assert file_hash(path) == row["sha256"]
    retained_work = Path(spec["retainedRoots"][0]["root"])
    retained_evidence = Path(spec["retainedRoots"][1]["root"])
    retained_before = [root_hash(retained_work), root_hash(retained_evidence)]
    assert retained_before == [row["sha256"] for row in spec["retainedRoots"]]
    fresh = ROOT / spec["evidence"]
    assert not fresh.exists() and not fresh.is_symlink()
    fresh.mkdir(parents=True)
    for relative in ("admission.json", "result.json", "diagnostic-result.json", "work-manifest.json", "processes/blender.json"):
        destination = fresh / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with (retained_evidence / relative).open("rb") as source, destination.open("xb") as target:
            shutil.copyfileobj(source, target)
        assert file_hash(destination) == file_hash(retained_evidence / relative)

    audit_python = Path(spec["auditPython"])
    # Run in a fresh process so imported native modules and the interpreter are explicit evidence.
    wrapper = (
        "import importlib.util,pathlib,sys;"
        f"p=pathlib.Path({str(BASE_AUDITOR)!r});"
        "s=importlib.util.spec_from_file_location('a',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        f"m.SPEC=pathlib.Path({str(SPEC)!r});sys.exit(m.main())"
    )
    stdout = fresh / "logs/audit.stdout.txt"; stderr = fresh / "logs/audit.stderr.txt"
    stdout.parent.mkdir(parents=True)
    argv = [str(audit_python), "-c", wrapper]
    with stdout.open("x") as out, stderr.open("x") as err:
        completed = subprocess.run(argv, stdout=out, stderr=err, timeout=spec["resourceCeilings"]["auditTimeoutSeconds"], check=False)
    write_exclusive(fresh / "processes/audit.json", {"argv": argv, "exitCode": completed.returncode})
    if completed.returncode != 0:
        raise RuntimeError(f"C34 C1 audit exited {completed.returncode}")
    audit = json.loads((fresh / "independent-audit.json").read_text())
    assert audit["status"] == "PASS_NATIVE_EXPORT_STRONG_COMMON_FIELD_EQUIVALENCE"
    assert retained_before == [root_hash(retained_work), root_hash(retained_evidence)]
    receipt = {
        "schemaVersion": "bfs.rc6NativePhiC34C1Receipt.v1",
        "status": audit["status"], "auditHash": audit["auditHash"],
        "retainedAttempt115Unchanged": True, "retainedRootHashes": retained_before,
        "counts": {"systemPythonStarts": 1, "blenderStarts": 0, "bakes": 0, "renders": 0,
                   "cacheCopies": 0, "retainedWrites": 0, "engineBuilds": 0, "engineEdits": 0, "network": 0},
        "claimCeiling": spec["claimCeiling"],
    }
    receipt["receiptHash"] = digest(canonical(receipt))
    write_exclusive(fresh / "receipt.json", receipt)
    assert sum(path.stat().st_size for path in fresh.rglob("*") if path.is_file()) <= spec["resourceCeilings"]["maximumEvidenceBytes"]
    print(json.dumps({"status": receipt["status"], "auditHash": audit["auditHash"], "receiptHash": receipt["receiptHash"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
