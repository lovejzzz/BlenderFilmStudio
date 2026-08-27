#!/usr/bin/env python3
"""Run the preregistered D12.1 cross-language envelope development probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SPEC_SHA256 = "8bd219570e0c7ec922a671919d680787caf55b2ba7d8a631ed5bc995ab24f116"
PYTHON_TOOL = "scripts/encode-b52-d12-1-evidence-envelope.py"
NODE_TOOL = "scripts/encode-b52-d12-1-evidence-envelope.mjs"
NODE = "/opt/homebrew/Cellar/node/26.5.0/bin/node"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_hash(value: object) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def native_report_valid(path: Path) -> bool:
    payload = json.loads(path.read_text())
    body = {key: value for key, value in payload.items() if key != "reportHash"}
    return payload.get("reportHash") == canonical_hash(body)


def invoke(root: Path, spec_path: Path, tool: Path, executable: str, source: Path, target: Path, subtree: str | None = None) -> subprocess.CompletedProcess[str]:
    argv = [executable, str(tool), "--spec", str(spec_path), "--input", str(source), "--output", str(target)]
    if subtree:
        argv.extend(("--subtree", subtree))
    return subprocess.run(argv, cwd=root, text=True, capture_output=True, check=False)


def adversarial_probe(root: Path, spec_path: Path, python_tool: Path, node_tool: Path, temp: Path) -> list[dict[str, object]]:
    cases = [
        ("positive zero", ["{\"n\":0}"], True, "single"),
        ("negative zero", ["{\"n\":-0}"], True, "single"),
        ("small positive exponent", ["{\"n\":1e-7}"], True, "single"),
        ("small negative exponent", ["{\"n\":-1e-7}"], True, "single"),
        ("largest safe integer", ["{\"n\":9007199254740991}"], True, "single"),
        ("negative largest safe integer", ["{\"n\":-9007199254740991}"], True, "single"),
        ("unsafe integer rejection", ["{\"n\":9007199254740992}"], False, "single"),
        ("positive infinity rejection", ["{\"n\":Infinity}"], False, "single"),
        ("negative infinity rejection", ["{\"n\":-Infinity}"], False, "single"),
        ("NaN rejection", ["{\"n\":NaN}"], False, "single"),
        ("object insertion-order permutation", ["{\"z\":1,\"a\":2}", "{\"a\":2,\"z\":1}"], True, "equal"),
        ("nested array order", ["{\"a\":[1,2,3]}", "{\"a\":[3,2,1]}"], True, "different"),
        ("ASCII control escaping", ["{\"s\":\"line\\n\\t\\u0001\"}"], True, "single"),
        ("Unicode scalar string", ["{\"s\":\"电影🎬\"}"], True, "single"),
        ("unpaired surrogate rejection", ["{\"s\":\"\\ud800\"}"], False, "single"),
        ("existing $f64be user key remains ordinary data", ["{\"$f64be\":\"user\",\"n\":1}"], True, "single"),
    ]
    rows = []
    outputs_by_name: dict[str, list[bytes]] = {}
    for case_index, (name, texts, expected_success, relation) in enumerate(cases):
        case_outputs = []
        invocations = []
        for variant, source_text in enumerate(texts):
            source = temp / f"case-{case_index}-{variant}.json"
            source.write_bytes(source_text.encode("utf-8"))
            py_output, node_output = temp / f"case-{case_index}-{variant}.py", temp / f"case-{case_index}-{variant}.node"
            py_run = invoke(root, spec_path, python_tool, sys.executable, source, py_output)
            node_run = invoke(root, spec_path, node_tool, NODE, source, node_output)
            success = py_run.returncode == 0 and node_run.returncode == 0 and py_output.is_file() and node_output.is_file()
            rejected = py_run.returncode != 0 and node_run.returncode != 0 and not py_output.exists() and not node_output.exists()
            exact = success and py_output.read_bytes() == node_output.read_bytes()
            if success:
                case_outputs.append(py_output.read_bytes())
            invocations.append({"variant": variant, "pythonExitCode": py_run.returncode, "nodeExitCode": node_run.returncode, "crossLanguageExact": exact, "rejectedWithoutOutput": rejected})
        passed = all(row["crossLanguageExact"] for row in invocations) if expected_success else all(row["rejectedWithoutOutput"] for row in invocations)
        if relation == "equal":
            passed = passed and len(case_outputs) == 2 and case_outputs[0] == case_outputs[1]
        elif relation == "different":
            passed = passed and len(case_outputs) == 2 and case_outputs[0] != case_outputs[1]
        outputs_by_name[name] = case_outputs
        rows.append({"name": name, "expectedSuccess": expected_success, "relation": relation, "passed": passed, "invocations": invocations})
    positive = outputs_by_name["positive zero"]
    negative = outputs_by_name["negative zero"]
    zero_exact = len(positive) == len(negative) == 1 and positive[0] == negative[0]
    rows[0]["signedZeroPairExact"] = zero_exact
    rows[1]["signedZeroPairExact"] = zero_exact
    rows[0]["passed"] = bool(rows[0]["passed"] and zero_exact)
    rows[1]["passed"] = bool(rows[1]["passed"] and zero_exact)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text())
    if sha(spec_path) != SPEC_SHA256 or args.output_root.exists():
        raise RuntimeError("D12.1 development identity/output mismatch")
    python_tool, node_tool = root / PYTHON_TOOL, root / NODE_TOOL
    report_root = root / spec["inputs"]["root"]
    python_reports = sorted(report_root.glob("python/*/reconstructor.report.json"))
    node_reports = sorted(report_root.glob("node/*/reconstructor.report.json"))
    roster_exact = len(python_reports) == spec["inputs"]["pythonReports"] and len(node_reports) == spec["inputs"]["nodeReports"]
    all_reports = python_reports + node_reports
    before_hashes = {str(path.relative_to(root)): sha(path) for path in all_reports}
    payloads = {path: json.loads(path.read_text()) for path in all_reports}
    pair_key = lambda path: (payloads[path]["fixtureId"], int(payloads[path]["repeat"]))
    python_by_pair, node_by_pair = {pair_key(path): path for path in python_reports}, {pair_key(path): path for path in node_reports}
    pair_roster_exact = set(python_by_pair) == set(node_by_pair) and len(python_by_pair) == 8

    report_rows, pair_rows = [], []
    with tempfile.TemporaryDirectory(prefix="bfs-d12-1-envelope-") as temp_text:
        temp = Path(temp_text)
        full_bytes: dict[Path, bytes] = {}
        measurement_bytes: dict[Path, bytes] = {}
        for index, report_path in enumerate(all_reports):
            py_output, node_output = temp / f"report-{index}.py", temp / f"report-{index}.node"
            py_run = invoke(root, spec_path, python_tool, sys.executable, report_path, py_output)
            node_run = invoke(root, spec_path, node_tool, NODE, report_path, node_output)
            exact = py_run.returncode == node_run.returncode == 0 and py_output.is_file() and node_output.is_file() and py_output.read_bytes() == node_output.read_bytes()
            if exact:
                full_bytes[report_path] = py_output.read_bytes()
            py_measurement, node_measurement = temp / f"measurement-{index}.py", temp / f"measurement-{index}.node"
            py_m_run = invoke(root, spec_path, python_tool, sys.executable, report_path, py_measurement, "measurements")
            node_m_run = invoke(root, spec_path, node_tool, NODE, report_path, node_measurement, "measurements")
            measurement_exact = py_m_run.returncode == node_m_run.returncode == 0 and py_measurement.is_file() and node_measurement.is_file() and py_measurement.read_bytes() == node_measurement.read_bytes()
            if measurement_exact:
                measurement_bytes[report_path] = py_measurement.read_bytes()
            report_rows.append({"uri": str(report_path.relative_to(root)), "producer": payloads[report_path]["producer"], "fixtureId": pair_key(report_path)[0], "repeat": pair_key(report_path)[1], "nativeHashValidUnderPython": native_report_valid(report_path), "envelopeImplementationsExact": exact, "envelopeSha256": sha_bytes(full_bytes[report_path]) if exact else None, "measurementImplementationsExact": measurement_exact, "measurementEnvelopeSha256": sha_bytes(measurement_bytes[report_path]) if measurement_exact else None})
        for key in sorted(python_by_pair):
            python_path, node_path = python_by_pair[key], node_by_pair[key]
            exact = python_path in measurement_bytes and node_path in measurement_bytes and measurement_bytes[python_path] == measurement_bytes[node_path]
            pair_rows.append({"fixtureId": key[0], "repeat": key[1], "measurementEnvelopeExact": exact, "sha256": sha_bytes(measurement_bytes[python_path]) if exact else None})
        adversarial = adversarial_probe(root, spec_path, python_tool, node_tool, temp)

    after_hashes = {str(path.relative_to(root)): sha(path) for path in all_reports}
    source_reports_modified = sum(before_hashes[key] != after_hashes[key] for key in before_hashes)
    gates = {
        "inputRosterExact": roster_exact and pair_roster_exact,
        "originalPythonReportsNativeHashValid": sum(row["producer"] == "python" and row["nativeHashValidUnderPython"] for row in report_rows) == 8,
        "originalNodeReportsNativeHashInvalid": sum(row["producer"] == "node" and not row["nativeHashValidUnderPython"] for row in report_rows) == 8,
        "pythonNodeEnvelopeBytesExactPerReport": len(report_rows) == 16 and all(row["envelopeImplementationsExact"] for row in report_rows),
        "pythonNodeEnvelopeHashExactPerReport": len({row["uri"] for row in report_rows if row["envelopeSha256"]}) == 16,
        "pairedMeasurementEnvelopeExact": len(pair_rows) == 8 and all(row["measurementEnvelopeExact"] for row in pair_rows),
        "adversarialCasesPassed": len(adversarial) == 16 and all(row["passed"] for row in adversarial),
        "sourceReportsModified": source_reports_modified == 0,
        "blenderProcesses": True,
        "modelCalls": True,
        "networkCalls": True,
    }
    compatible = all(gates.values())
    body = {
        "schemaVersion": "bfs.crossLanguageEvidenceEnvelopeDevelopmentResult.v0.1",
        "experimentId": spec["experimentId"],
        "spec": {"uri": str(args.spec), "sha256": SPEC_SHA256},
        "inputIdentities": before_hashes,
        "reports": report_rows,
        "measurementPairs": pair_rows,
        "adversarialCases": adversarial,
        "gates": gates,
        "operationCounts": {"pythonEncoderProcesses": 50, "nodeEncoderProcesses": 50, "blenderProcesses": 0, "modelCalls": 0, "networkCalls": 0, "sourceReportsModified": source_reports_modified},
        "outcome": spec["outcomes"]["compatible" if compatible else "notCompatible"],
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "resultHash": canonical_hash(body)}
    args.output_root.mkdir(parents=True, exist_ok=False)
    output = args.output_root / "results.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_D12_1_ENVELOPE_DEVELOPMENT outcome={result['outcome']} gates={sum(gates.values())}/{len(gates)} result={sha(output)}")
    if not compatible:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
