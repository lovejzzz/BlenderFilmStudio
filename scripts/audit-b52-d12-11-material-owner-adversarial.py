#!/usr/bin/env python3
"""Concrete in-memory semantic attack audit for B52-D12.11-I1-A1."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


SPEC_SHA256 = "bc1f6c9e171d009bedd6041e53aa7e3580185e72897800efe5b06e1ed25cad22"
INTERVENTION_SPEC_SHA256 = "89dd3637ffe5af3544e8cd8aca8869eedd8b1a1867d41e08a354e5cd0c3b2a0e"
ADAPTER_FILES = {
    "previousRgba": "previous.rgba32", "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32", "currentDepth": "current-depth.f32",
    "previousOwner": "previous-owner.f32", "currentOwner": "current-owner.f32",
    "previousObjectIndex": "previous-object-index.f32", "currentObjectIndex": "current-object-index.f32",
    "vector": "vector.xy32", "vectorNext": "vector-next.xy32",
}
CONSUMER_FILES = {
    "acceptedReconstructed": "accepted-reconstructed.rgba32", "reason": "reason.u8",
    "analyticOwner": "analytic-owner.u8", "structuralValid": "structural-valid.u8",
    "radius2Interior": "radius2-interior.u8", "supportEligible": "support-eligible.u8",
    "supportRejected": "support-rejected.u8", "accepted": "accepted.u8",
    "riskRejected": "risk-rejected.u8", "riskQ30": "risk.q30.u32",
}
PAIRED_MAP = {
    "previousRgba": "previous.rgba32", "currentRgba": "current.rgba32",
    "previousDepth": "previous-depth.f32", "currentDepth": "current-depth.f32",
    "vector": "vector.xy32", "vectorNext": "vector-next.xy32",
    "previousObjectIndex": "previous-owner.f32", "currentObjectIndex": "current-owner.f32",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def repair(value: dict, field_name: str) -> dict:
    value[field_name] = canon({key: item for key, item in value.items() if key != field_name})
    return value


def self_ok(value: dict, field_name: str) -> bool:
    return value.get(field_name) == canon({key: item for key, item in value.items() if key != field_name})


FILE_CACHE: dict[str, bytes] = {}


@dataclass
class State:
    byte_overrides: dict[str, bytes] = field(default_factory=dict)
    json_overrides: dict[str, dict] = field(default_factory=dict)
    token_overrides: dict[str, int] | None = None

    def clone(self) -> "State":
        return State(dict(self.byte_overrides), copy.deepcopy(self.json_overrides), copy.deepcopy(self.token_overrides))

    def bytes(self, path: Path | str) -> bytes:
        key = str(path)
        if key in self.json_overrides:
            return json_bytes(self.json_overrides[key])
        if key in self.byte_overrides:
            return self.byte_overrides[key]
        if key not in FILE_CACHE:
            FILE_CACHE[key] = Path(key).read_bytes()
        return FILE_CACHE[key]

    def json(self, path: Path | str) -> dict:
        key = str(path)
        if key in self.json_overrides:
            return copy.deepcopy(self.json_overrides[key])
        return json.loads(self.bytes(path))

    def set_bytes(self, path: Path | str, value: bytes) -> None:
        key = str(path)
        self.byte_overrides[key] = value
        self.json_overrides.pop(key, None)

    def set_json(self, path: Path | str, value: dict) -> None:
        key = str(path)
        self.json_overrides[key] = copy.deepcopy(value)
        self.byte_overrides.pop(key, None)


def flip_one(payload: bytes, index: int = 0) -> bytes:
    result = bytearray(payload)
    result[index] ^= 1
    return bytes(result)


def array_from(state: State, path: Path, dtype: str, shape: tuple[int, ...]) -> np.ndarray:
    payload = state.bytes(path)
    expected = math.prod(shape) * np.dtype(dtype).itemsize
    if len(payload) != expected:
        raise ValueError(f"length mismatch: {path}")
    return np.frombuffer(payload, dtype=dtype).reshape(shape).copy()


def safe_gate(function) -> bool:
    try:
        return bool(function())
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    spec_path = args.spec.resolve()
    spec = json.loads(spec_path.read_text())
    if sha_file(spec_path) != SPEC_SHA256:
        raise RuntimeError("D12.11-I1-A1 spec identity mismatch")
    expected_root = (repo / spec["freshness"]["outputRoot"]).resolve()
    if args.output_root.resolve() != expected_root or expected_root.exists():
        raise RuntimeError("D12.11-I1-A1 output root freshness rejected")
    prereg_commit = subprocess.check_output(["git", "log", "-1", "--format=%H", "--", str(spec_path.relative_to(repo))], cwd=repo, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    tool_rel = spec["freshness"]["newToolPath"]
    tool_path = repo / tool_rel
    tool_absent_at_prereg = subprocess.run(["git", "cat-file", "-e", f"{prereg_commit}:{tool_rel}"], cwd=repo, capture_output=True).returncode != 0
    tool_blob = subprocess.check_output(["git", "show", f"HEAD:{tool_rel}"], cwd=repo)
    tool_frozen = sha_bytes(tool_blob) == sha_file(tool_path) and prereg_commit != head and tool_absent_at_prereg
    root_rel = spec["boundFormalRoot"]["uri"]
    root = repo / root_rel
    root_tree_before = subprocess.check_output(["git", "rev-parse", f"HEAD:{root_rel}"], cwd=repo, text=True).strip()
    if root_tree_before != spec["boundFormalRoot"]["gitTree"] or not tool_frozen:
        raise RuntimeError("D12.11-I1-A1 Git identity/freeze rejected")

    intervention_path = repo / spec["parents"]["interventionSpec"]["uri"]
    if sha_file(intervention_path) != INTERVENTION_SPEC_SHA256:
        raise RuntimeError("D12.11-I1-A1 intervention identity mismatch")
    intervention = json.loads(intervention_path.read_text())
    h1_spec = json.loads((repo / spec["parents"]["h1Spec"]["uri"]).read_text())
    fixtures = h1_spec["fixtures"]
    fixture_by_id = {row["id"]: row for row in fixtures}
    cells = [(fixture["id"], repeat) for fixture in fixtures for repeat in (1, 2)]
    h1_root = (repo / spec["parents"]["h1Result"]["uri"]).parent
    localization_root = (repo / spec["parents"]["localizationResult"]["uri"]).parent
    localization = json.loads((repo / spec["parents"]["localizationResult"]["uri"]).read_text())
    localization_by_cell = {row["cell"]: row for row in localization["cells"]}
    result_path = repo / spec["boundFormalRoot"]["result"]["uri"]
    audit_path = repo / spec["boundFormalRoot"]["audit"]["uri"]
    execution_path = repo / spec["boundFormalRoot"]["execution"]["uri"]
    receipt_path = repo / spec["boundFormalRoot"]["receipt"]["uri"]

    def adapter_dir(fixture_id: str, repeat: int) -> Path:
        return root / "adapters" / fixture_id / f"R{repeat}"

    def consumer_dir(producer: str, fixture_id: str, repeat: int) -> Path:
        return root / "consumers" / producer / fixture_id / f"R{repeat}"

    def material_tokens(state: State) -> dict[str, int]:
        return state.token_overrides if state.token_overrides is not None else intervention["materialOwnerTokens"]["assignments"]

    def validate(state: State) -> dict[str, bool]:
        gates: dict[str, bool] = {}

        def parent_identity() -> bool:
            return all(sha_bytes(state.bytes(repo / row["uri"])) == row["sha256"] for row in spec["parents"].values())
        gates["PARENT_IDENTITY"] = safe_gate(parent_identity)
        gates["FORMAL_ROOT_GIT_IDENTITY"] = root_tree_before == spec["boundFormalRoot"]["gitTree"]

        def formal_self_hashes() -> bool:
            result = state.json(result_path); audit = state.json(audit_path); execution = state.json(execution_path); receipt = state.json(receipt_path)
            return self_ok(result, "evidenceHash") and self_ok(audit, "auditHash") and self_ok(execution, "executionHash") and self_ok(receipt, "receiptHash")
        gates["FORMAL_SELF_HASHES"] = safe_gate(formal_self_hashes)

        def source_identity() -> bool:
            for fixture_id, repeat in cells:
                for frame in (0, 1):
                    report_path = root / "sources" / fixture_id / f"R{repeat}" / f"frame-{frame}" / "report.json"
                    exr_path = report_path.with_name("source.exr")
                    report = state.json(report_path)
                    if not self_ok(report, "reportHash") or report.get("output", {}).get("sha256") != sha_bytes(state.bytes(exr_path)):
                        return False
            return True
        gates["SOURCE_REPORT_IDENTITY"] = safe_gate(source_identity)

        def adapter_identity() -> bool:
            for fixture_id, repeat in cells:
                directory = adapter_dir(fixture_id, repeat)
                report = state.json(directory / "report.json")
                if not self_ok(report, "reportHash"):
                    return False
                for name, filename in ADAPTER_FILES.items():
                    if report["arrays"][name]["sha256"] != sha_bytes(state.bytes(directory / "arrays" / filename)):
                        return False
            return True
        gates["ADAPTER_REPORT_IDENTITY"] = safe_gate(adapter_identity)

        def paired_identity() -> bool:
            for fixture_id, repeat in cells:
                new_dir = adapter_dir(fixture_id, repeat) / "arrays"
                old_dir = h1_root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
                for new_name, old_name in PAIRED_MAP.items():
                    if state.bytes(new_dir / ADAPTER_FILES[new_name]) != state.bytes(old_dir / old_name):
                        return False
            return True
        gates["PAIRED_H1_PAYLOAD_IDENTITY"] = safe_gate(paired_identity)

        def token_domain() -> bool:
            allowed = {0.0, *(float(value) for value in material_tokens(state).values())}
            for fixture_id, repeat in cells:
                width, height = fixture_by_id[fixture_id]["resolution"]
                for name in ("previousOwner", "currentOwner"):
                    values = array_from(state, adapter_dir(fixture_id, repeat) / "arrays" / ADAPTER_FILES[name], "<f4", (height, width))
                    if not np.isfinite(values).all() or not set(np.unique(values).astype(float)).issubset(allowed):
                        return False
            return True
        gates["MATERIAL_TOKEN_DOMAIN"] = safe_gate(token_domain)

        def token_assignment() -> bool:
            tokens = material_tokens(state)
            values = list(tokens.values())
            if set(tokens) != set(intervention["materialOwnerTokens"]["assignments"]) or any(value <= 0 or value > 32767 for value in values) or len(set(values)) != len(values):
                return False
            for fixture_id, repeat in cells:
                report = state.json(root / "sources" / fixture_id / f"R{repeat}" / "frame-0" / "report.json")
                expected = [tokens[owner["analyticOwnerId"]] for owner in fixture_by_id[fixture_id]["owners"]]
                if [owner["materialPassIndex"] for owner in report["sceneStructure"]["owners"]] != expected:
                    return False
            return True
        gates["MATERIAL_TOKEN_ASSIGNMENT"] = safe_gate(token_assignment)

        def object_control() -> bool:
            for fixture_id, repeat in cells:
                new_dir = adapter_dir(fixture_id, repeat) / "arrays"
                old_dir = h1_root / "adapters" / fixture_id / f"R{repeat}" / "arrays"
                if state.bytes(new_dir / "previous-object-index.f32") != state.bytes(old_dir / "previous-owner.f32") or state.bytes(new_dir / "current-object-index.f32") != state.bytes(old_dir / "current-owner.f32"):
                    return False
            critical = "SAME_INDEX_DEPTH_CROSSING_179X113"
            for repeat in (1, 2):
                report = state.json(root / "sources" / critical / f"R{repeat}" / "frame-0" / "report.json")
                if [row["passIndex"] for row in report["sceneStructure"]["owners"]] != [14555, 14555]:
                    return False
            return True
        gates["OBJECT_INDEX_NEGATIVE_CONTROL"] = safe_gate(object_control)

        def dual_identity() -> bool:
            for fixture_id, repeat in cells:
                for filename in CONSUMER_FILES.values():
                    if state.bytes(consumer_dir("python", fixture_id, repeat) / "arrays" / filename) != state.bytes(consumer_dir("node", fixture_id, repeat) / "arrays" / filename):
                        return False
            return True
        gates["DUAL_CONSUMER_IDENTITY"] = safe_gate(dual_identity)

        endpoints: dict[str, dict] = {}
        def endpoint_gates() -> tuple[bool, bool, bool, bool]:
            roster_ok = alias_ok = no_new_ok = True
            for fixture_id, repeat in cells:
                width, height = fixture_by_id[fixture_id]["resolution"]
                accepted = array_from(state, consumer_dir("python", fixture_id, repeat) / "arrays" / "accepted.u8", "u1", (height, width)).astype(bool)
                h1_accepted = array_from(state, h1_root / "consumers/python" / fixture_id / f"R{repeat}" / "arrays/accepted.u8", "u1", (height, width)).astype(bool)
                truth = array_from(state, localization_root / "payloads" / fixture_id / f"R{repeat}" / "true-owner-bilinear.u8", "u1", (height, width)).astype(bool)
                registered = h1_accepted & ~truth
                cell = f"{fixture_id}/R{repeat}"
                endpoints[cell] = {"registered": int(registered.sum()), "acceptedAlias": int((accepted & ~truth).sum()), "newAccepted": int((accepted & ~h1_accepted).sum())}
                roster_ok = roster_ok and int(registered.sum()) == int(localization_by_cell[cell]["acceptedOutsideTrueOwnerBilinear"])
                if fixture_id == spec["baselineValidator"]["rawEndpoint"]["fixture"]:
                    roster_ok = roster_ok and int(registered.sum()) == 15 and int(localization_by_cell[cell]["objectIndexBilinearAlias"]) == 17
                alias_ok = alias_ok and not (accepted & ~truth).any()
                no_new_ok = no_new_ok and not (accepted & ~h1_accepted).any()
            return roster_ok, alias_ok, no_new_ok, True
        roster_ok, alias_ok, no_new_ok, _ = endpoint_gates()
        gates["PRIMARY_ALIAS_ROSTER"] = roster_ok
        gates["PRIMARY_ALIAS_ELIMINATION"] = alias_ok
        gates["NO_NEW_ACCEPTED_COORDINATES"] = no_new_ok

        def fallback_exact() -> bool:
            for fixture_id, repeat in cells:
                width, height = fixture_by_id[fixture_id]["resolution"]
                accepted = array_from(state, consumer_dir("python", fixture_id, repeat) / "arrays/accepted.u8", "u1", (height, width)).astype(bool)
                reconstructed = array_from(state, consumer_dir("python", fixture_id, repeat) / "arrays/accepted-reconstructed.rgba32", "<f4", (height, width, 4))
                current = array_from(state, adapter_dir(fixture_id, repeat) / "arrays/current.rgba32", "<f4", (height, width, 4))
                if not np.array_equal(reconstructed[~accepted], current[~accepted]):
                    return False
            return True
        gates["FALLBACK_EXACT"] = safe_gate(fallback_exact)

        def q30_partition() -> bool:
            threshold = int(h1_spec["frozenGates"]["risk"]["riskThresholdQ30Inclusive"])
            for fixture_id, repeat in cells:
                width, height = fixture_by_id[fixture_id]["resolution"]
                directory = consumer_dir("python", fixture_id, repeat) / "arrays"
                eligible = array_from(state, directory / "support-eligible.u8", "u1", (height, width)).astype(bool)
                accepted = array_from(state, directory / "accepted.u8", "u1", (height, width)).astype(bool)
                rejected = array_from(state, directory / "risk-rejected.u8", "u1", (height, width)).astype(bool)
                risk = array_from(state, directory / "risk.q30.u32", "<u4", (height, width, 3))
                expected_accepted = eligible & (risk.max(axis=2) <= threshold)
                if not np.array_equal(accepted, expected_accepted) or not np.array_equal(rejected, eligible & ~expected_accepted):
                    return False
            return True
        gates["Q30_DECISION_PARTITION"] = safe_gate(q30_partition)

        def measurement_replay() -> bool:
            result = state.json(result_path)
            rows = {row["cell"]: row for row in result["measurements"]}
            for fixture_id, repeat in cells:
                width, height = fixture_by_id[fixture_id]["resolution"]
                directory = consumer_dir("python", fixture_id, repeat) / "arrays"
                accepted = array_from(state, directory / "accepted.u8", "u1", (height, width)).astype(bool)
                radius = array_from(state, directory / "radius2-interior.u8", "u1", (height, width)).astype(bool)
                analytic = array_from(state, directory / "analytic-owner.u8", "u1", (height, width))
                row = rows[f"{fixture_id}/R{repeat}"]
                if row["coverage"]["accepted"] != int(accepted.sum()) or row["coverage"]["radius2"] != int(radius.sum()):
                    return False
                for owner_index, owner in enumerate(fixture_by_id[fixture_id]["owners"], 1):
                    mask = analytic == owner_index
                    observed = row["coverage"]["owners"][owner["analyticOwnerId"]]
                    if observed["accepted"] != int((accepted & mask).sum()) or observed["radius2"] != int((radius & mask).sum()):
                        return False
                endpoint = endpoints[f"{fixture_id}/R{repeat}"]
                paired = row["pairedIntervention"]
                if paired["registeredH1AcceptedAliasPixels"] != endpoint["registered"] or paired["acceptedOutsideTrueOwnerBilinearPixels"] != endpoint["acceptedAlias"] or paired["newAcceptedPixelsRelativeToH1"] != endpoint["newAccepted"]:
                    return False
            return True
        gates["MEASUREMENT_RAW_REPLAY"] = safe_gate(measurement_replay)

        def verdict_mapping() -> bool:
            result = state.json(result_path)
            checks = {row["id"]: row["passed"] for row in result["checks"]}
            return result["verdict"] == spec["boundFormalRoot"]["result"]["verdict"] and result["passed"] is False and checks.get("COVERAGE") is False and sum(checks.values()) == 18 and len(checks) == 19
        gates["VERDICT_MAPPING"] = safe_gate(verdict_mapping)

        def receipt_binding() -> bool:
            result = state.json(result_path); audit = state.json(audit_path); execution = state.json(execution_path); receipt = state.json(receipt_path)
            return (
                self_ok(receipt, "receiptHash")
                and receipt["result"]["sha256"] == sha_bytes(state.bytes(result_path))
                and receipt["result"]["evidenceHash"] == result["evidenceHash"]
                and receipt["result"]["verdict"] == result["verdict"]
                and receipt["audit"]["sha256"] == sha_bytes(state.bytes(audit_path))
                and receipt["audit"]["auditHash"] == audit["auditHash"]
                and receipt["execution"]["sha256"] == sha_bytes(state.bytes(execution_path))
                and receipt["execution"]["executionHash"] == execution["executionHash"]
            )
        gates["RECEIPT_BINDING"] = safe_gate(receipt_binding)

        def zero_external() -> bool:
            execution = state.json(execution_path)
            counts = execution["operationCounts"]
            return counts["modelCalls"] == 0 and counts["networkCalls"] == 0 and counts["sourceRenders"] == 16
        gates["MODEL_NETWORK_RENDER_ZERO"] = safe_gate(zero_external)
        return gates

    def update_adapter_report(state: State, fixture_id: str, repeat: int, changed: dict[str, bytes]) -> None:
        directory = adapter_dir(fixture_id, repeat)
        report_path = directory / "report.json"
        report = state.json(report_path)
        for name, payload in changed.items():
            state.set_bytes(directory / "arrays" / ADAPTER_FILES[name], payload)
            report["arrays"][name]["sha256"] = sha_bytes(payload)
        state.set_json(report_path, repair(report, "reportHash"))

    def update_consumer_payload(state: State, fixture_id: str, repeat: int, name: str, payload: bytes) -> None:
        for producer in ("python", "node"):
            directory = consumer_dir(producer, fixture_id, repeat)
            state.set_bytes(directory / "arrays" / CONSUMER_FILES[name], payload)
            report_path = directory / "report.json"
            report = state.json(report_path)
            report["arrays"][name]["sha256"] = sha_bytes(payload)
            state.set_json(report_path, repair(report, "reportHash"))

    baseline_state = State()
    baseline_gates = validate(baseline_state)
    baseline_endpoint = {}
    for repeat in (1, 2):
        cell = f"SAME_INDEX_DEPTH_CROSSING_179X113/R{repeat}"
        row = next(item for item in baseline_state.json(result_path)["measurements"] if item["cell"] == cell)
        baseline_endpoint[cell] = row["pairedIntervention"]

    attacks: list[tuple[str, str, list[str], State]] = []
    attack_index = 1
    def register(description: str, expected: str | list[str], state: State) -> None:
        nonlocal attack_index
        attacks.append((f"A{attack_index:02d}", description, [expected] if isinstance(expected, str) else expected, state))
        attack_index += 1

    for name, row in spec["parents"].items():
        state = baseline_state.clone(); path = repo / row["uri"]
        state.set_bytes(path, flip_one(state.bytes(path), min(7, len(state.bytes(path)) - 1)))
        register(f"flip bound parent byte: {name}", "PARENT_IDENTITY", state)

    for fixture in fixtures:
        fixture_id = fixture["id"]
        state = baseline_state.clone(); path = root / "sources" / fixture_id / "R1/frame-0/report.json"
        report = state.json(path); report["repeat"] = 9; state.set_json(path, report)
        register(f"break source report self-hash: {fixture_id}", "SOURCE_REPORT_IDENTITY", state)

    for fixture_id, repeat in cells:
        state = baseline_state.clone(); path = adapter_dir(fixture_id, repeat) / "arrays/current.rgba32"
        state.set_bytes(path, flip_one(state.bytes(path), 0))
        register(f"flip paired adapter byte: {fixture_id}/R{repeat}", ["ADAPTER_REPORT_IDENTITY", "PAIRED_H1_PAYLOAD_IDENTITY"], state)

    critical = "SAME_INDEX_DEPTH_CROSSING_179X113"
    for repeat in (1, 2):
        state = baseline_state.clone(); directory = adapter_dir(critical, repeat) / "arrays"
        changed = {"previousOwner": state.bytes(directory / "previous-object-index.f32"), "currentOwner": state.bytes(directory / "current-object-index.f32")}
        update_adapter_report(state, critical, repeat, changed)
        register(f"substitute Object Index for Material Index: R{repeat}", "MATERIAL_TOKEN_DOMAIN", state)

    token_mutations = []
    original_tokens = intervention["materialOwnerTokens"]["assignments"]
    names = list(original_tokens)
    value = dict(original_tokens); value[names[0]] = 0; token_mutations.append(("zero token", value))
    value = dict(original_tokens); value[names[1]] = value[names[0]]; token_mutations.append(("reuse token", value))
    value = dict(original_tokens); value[names[2]] = 32768; token_mutations.append(("out-of-range token", value))
    value = dict(original_tokens); value[names[4]], value[names[5]] = value[names[5]], value[names[4]]; token_mutations.append(("swap critical tokens", value))
    for description, tokens in token_mutations:
        state = baseline_state.clone(); state.token_overrides = tokens
        register(description, "MATERIAL_TOKEN_ASSIGNMENT", state)

    for repeat in (1, 2):
        for name in ("previousObjectIndex", "currentObjectIndex"):
            state = baseline_state.clone(); fixture = fixture_by_id[critical]; width, height = fixture["resolution"]
            path = adapter_dir(critical, repeat) / "arrays" / ADAPTER_FILES[name]
            values = array_from(state, path, "<f4", (height, width)); y, x = np.argwhere(values == np.float32(14555))[0]
            values[y, x] = np.float32(14556)
            update_adapter_report(state, critical, repeat, {name: np.ascontiguousarray(values, dtype="<f4").tobytes()})
            register(f"alter critical {name}: R{repeat}", "OBJECT_INDEX_NEGATIVE_CONTROL", state)

    for repeat in (1, 2):
        state = baseline_state.clone(); width, height = fixture_by_id[critical]["resolution"]
        accepted_path = consumer_dir("python", critical, repeat) / "arrays/accepted.u8"
        accepted = array_from(state, accepted_path, "u1", (height, width))
        h1 = array_from(state, h1_root / "consumers/python" / critical / f"R{repeat}" / "arrays/accepted.u8", "u1", (height, width)).astype(bool)
        truth = array_from(state, localization_root / "payloads" / critical / f"R{repeat}" / "true-owner-bilinear.u8", "u1", (height, width)).astype(bool)
        y, x = np.argwhere(h1 & ~truth)[0]; accepted[y, x] = 1
        update_consumer_payload(state, critical, repeat, "accepted", accepted.tobytes())
        register(f"accept registered alias: R{repeat}", "PRIMARY_ALIAS_ELIMINATION", state)

    for fixture_id, repeat in cells:
        state = baseline_state.clone(); width, height = fixture_by_id[fixture_id]["resolution"]
        accepted_path = consumer_dir("python", fixture_id, repeat) / "arrays/accepted.u8"
        accepted = array_from(state, accepted_path, "u1", (height, width))
        h1 = array_from(state, h1_root / "consumers/python" / fixture_id / f"R{repeat}" / "arrays/accepted.u8", "u1", (height, width)).astype(bool)
        y, x = np.argwhere(~h1)[0]; accepted[y, x] = 1
        update_consumer_payload(state, fixture_id, repeat, "accepted", accepted.tobytes())
        register(f"create new accepted coordinate: {fixture_id}/R{repeat}", "NO_NEW_ACCEPTED_COORDINATES", state)

    for fixture in fixtures:
        fixture_id = fixture["id"]; repeat = 1; width, height = fixture["resolution"]
        state = baseline_state.clone(); directory = consumer_dir("python", fixture_id, repeat) / "arrays"
        accepted = array_from(state, directory / "accepted.u8", "u1", (height, width)).astype(bool)
        reconstructed = array_from(state, directory / "accepted-reconstructed.rgba32", "<f4", (height, width, 4))
        y, x = np.argwhere(~accepted)[0]; reconstructed[y, x, 0] = np.float32(reconstructed[y, x, 0] + np.float32(0.125))
        update_consumer_payload(state, fixture_id, repeat, "acceptedReconstructed", np.ascontiguousarray(reconstructed, dtype="<f4").tobytes())
        register(f"alter fallback pixel: {fixture_id}/R1", "FALLBACK_EXACT", state)

    for fixture in fixtures:
        fixture_id = fixture["id"]; state = baseline_state.clone(); result = state.json(result_path)
        row = next(item for item in result["measurements"] if item["cell"] == f"{fixture_id}/R1")
        row["coverage"]["accepted"] += 1
        state.set_json(result_path, repair(result, "evidenceHash"))
        register(f"hide coverage count change: {fixture_id}/R1", "MEASUREMENT_RAW_REPLAY", state)

    state = baseline_state.clone(); result = state.json(result_path); result["verdict"] = intervention["decision"]["supportedVerdict"]; result["passed"] = True; state.set_json(result_path, repair(result, "evidenceHash"))
    register("promote bounded verdict", "VERDICT_MAPPING", state)
    state = baseline_state.clone(); result = state.json(result_path); result["evidenceHash"] = "0" * 64; state.set_json(result_path, result)
    register("alter result evidence hash", "FORMAL_SELF_HASHES", state)
    state = baseline_state.clone(); audit = state.json(audit_path); audit["passed"] = False; state.set_json(audit_path, repair(audit, "auditHash"))
    register("alter audit and repair self-hash", "RECEIPT_BINDING", state)
    state = baseline_state.clone(); receipt = state.json(receipt_path); receipt["result"]["verdict"] = intervention["decision"]["supportedVerdict"]; state.set_json(receipt_path, repair(receipt, "receiptHash"))
    register("alter receipt verdict and repair self-hash", "RECEIPT_BINDING", state)

    for repeat in (1, 2):
        state = baseline_state.clone(); width, height = fixture_by_id[critical]["resolution"]
        directory = consumer_dir("python", critical, repeat) / "arrays"
        accepted = array_from(state, directory / "accepted.u8", "u1", (height, width)).astype(bool)
        risk = array_from(state, directory / "risk.q30.u32", "<u4", (height, width, 3))
        y, x = np.argwhere(accepted)[0]; risk[y, x, 0] = np.uint32(h1_spec["frozenGates"]["risk"]["riskThresholdQ30Inclusive"] + 1)
        update_consumer_payload(state, critical, repeat, "riskQ30", np.ascontiguousarray(risk, dtype="<u4").tobytes())
        register(f"raise accepted Q30 above threshold: R{repeat}", "Q30_DECISION_PARTITION", state)

    for repeat in (1, 2):
        state = baseline_state.clone(); width, height = fixture_by_id[critical]["resolution"]
        path = adapter_dir(critical, repeat) / "arrays/vector.xy32"
        vector = array_from(state, path, "<f4", (height, width, 2)); y, x = np.argwhere(np.abs(vector[..., 0]) > 0)[0]; vector[y, x, 0] = np.float32(-vector[y, x, 0])
        update_adapter_report(state, critical, repeat, {"vector": np.ascontiguousarray(vector, dtype="<f4").tobytes()})
        register(f"negate Vector X: R{repeat}", "PAIRED_H1_PAYLOAD_IDENTITY", state)

    if attack_index != 57 or len(attacks) != spec["attackRoster"]["total"]:
        raise RuntimeError(f"D12.11-I1-A1 attack roster mismatch: {len(attacks)}")
    attack_results = []
    for attack_id, description, expected, state in attacks:
        observed = validate(state)
        failed = sorted(name for name, passed in observed.items() if not passed)
        passed = all(name in failed for name in expected)
        attack_results.append({"id": attack_id, "description": description, "expectedFailedGates": expected, "observedFailedGates": failed, "passed": passed})

    root_tree_after = subprocess.check_output(["git", "rev-parse", f"HEAD:{root_rel}"], cwd=repo, text=True).strip()
    baseline_passed = all(baseline_gates.values()) and set(baseline_gates) == set(spec["baselineValidator"]["requiredGates"])
    attacks_passed = len(attack_results) == 56 and all(row["passed"] for row in attack_results)
    immutable = root_tree_before == root_tree_after == spec["boundFormalRoot"]["gitTree"]
    endpoint_passed = all(row["registeredH1AcceptedAliasPixels"] == 15 and row["acceptedOnRegisteredAliasPixels"] == 0 and row["acceptedOutsideTrueOwnerBilinearPixels"] == 0 for row in baseline_endpoint.values())
    accepted = baseline_passed and attacks_passed and immutable and endpoint_passed
    body = {
        "schemaVersion": "bfs.blenderMaterialIndexOwnerIntegrationAdversarialAuditResult.v0.1",
        "experimentId": spec["experimentId"],
        "auditPid": os.getpid(),
        "verdict": spec["decision"]["acceptedVerdict"] if accepted else spec["decision"]["rejectedVerdict"],
        "passed": accepted,
        "toolFreezeCommit": head,
        "preregistrationCommit": prereg_commit,
        "toolSha256": sha_file(tool_path),
        "formalRootGitTreeBefore": root_tree_before,
        "formalRootGitTreeAfter": root_tree_after,
        "formalRootImmutable": immutable,
        "baselineGates": [{"id": name, "passed": value} for name, value in baseline_gates.items()],
        "baselineGatePassed": sum(baseline_gates.values()),
        "baselineGateTotal": len(baseline_gates),
        "rawPrimaryEndpoint": baseline_endpoint,
        "rawPrimaryEndpointPassed": endpoint_passed,
        "attacks": attack_results,
        "attackPassed": sum(row["passed"] for row in attack_results),
        "attackTotal": len(attack_results),
        "operationCounts": {"auditProcesses": 1, "blenderProcesses": 0, "blenderRenderCalls": 0, "modelCalls": 0, "networkCalls": 0},
        "promotionEffect": spec["decision"]["promotionEffect"] if accepted else None,
        "nonClaims": spec["nonClaims"],
    }
    result = {**body, "adversarialAuditHash": canon(body)}
    expected_root.mkdir(parents=True, exist_ok=False)
    output = expected_root / "results.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"BFS_B52_D1211_A1_COMPLETE verdict={result['verdict']} baseline={result['baselineGatePassed']}/{result['baselineGateTotal']} attacks={result['attackPassed']}/{result['attackTotal']} hash={result['adversarialAuditHash']}")
    raise SystemExit(0 if accepted else 1)


if __name__ == "__main__":
    main()
