"""Assemble and verify B51-D4 Metal-beauty / CPU-data multipart OpenEXRs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_COMMIT = "8494459f1f18a00de9e0fb3dfb9aaf01e93b49cb"
SPEC_SHA256 = "553e613911bd9b46ce02ef539d635720095bf56400e7dfc8425e0f5bc2537368"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def git(*args: str) -> str:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or "git failed")
    return process.stdout.strip()


def normalize(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (tuple, list)):
        return [normalize(item) for item in value]
    if hasattr(value, "tolist"):
        return normalize(value.tolist())
    return str(value)


def spec_geometry(spec: oiio.ImageSpec, fields: list[str]) -> dict:
    row = {}
    for field in fields:
        if field == "channelnames":
            row[field] = list(spec.channelnames)
        elif field == "format":
            row[field] = str(spec.format)
        else:
            row[field] = int(getattr(spec, field))
    return row


def attributes(spec: oiio.ImageSpec, names: list[str]) -> dict:
    return {name: normalize(spec.getattribute(name)) for name in names}


def load_exr(path: Path) -> tuple[list[str], dict[str, dict]]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized:
        raise RuntimeError(first.geterror() or f"cannot read {path}")
    roster, parts = [], {}
    for index in range(first.nsubimages):
        image = oiio.ImageBuf(str(path), index, 0)
        if not image.initialized:
            raise RuntimeError(image.geterror() or f"cannot read subimage {index} in {path}")
        spec = oiio.ImageSpec(image.spec())
        name = str(spec.getattribute("oiio:subimagename") or f"subimage-{index}")
        pixels = np.ascontiguousarray(np.asarray(image.get_pixels(oiio.FLOAT), dtype="<f4"))
        roster.append(name)
        parts[name] = {
            "index": index,
            "spec": spec,
            "pixels": pixels,
            "pixelSha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
            "finite": bool(np.isfinite(pixels).all()),
        }
    return roster, parts


def top_level_differences(cpu_spec: oiio.ImageSpec, metal_spec: oiio.ImageSpec) -> list[dict]:
    cpu_names = {item.name for item in cpu_spec.extra_attribs}
    metal_names = {item.name for item in metal_spec.extra_attribs}
    rows = []
    for name in sorted(cpu_names | metal_names):
        cpu_value = normalize(cpu_spec.getattribute(name))
        metal_value = normalize(metal_spec.getattribute(name))
        if cpu_value != metal_value:
            rows.append({"name": name, "cpu": cpu_value, "metal": metal_value})
    return rows


def add_provenance(spec: oiio.ImageSpec, pair: dict, backend: str, source: dict, tool_hash: str, contract: str) -> None:
    spec.attribute("bfs:splitContract", contract)
    spec.attribute("bfs:passSourceBackend", backend)
    spec.attribute("bfs:passSourceRunId", source["runId"])
    spec.attribute("bfs:passSourceArtifactSha256", source["sha256"])
    spec.attribute("bfs:beautyArtifactSha256", pair["metal"]["sha256"])
    spec.attribute("bfs:dataArtifactSha256", pair["cpu"]["sha256"])
    spec.attribute("bfs:mergeToolGitBlobSha256", tool_hash)


def write_split_exr(path: Path, pair: dict, source_parts: dict, spec: dict, tool_hash: str) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=False)
    routing = {name: backend for backend, names in spec["passRouting"].items() if backend in {"CPU", "METAL"} for name in names}
    output_specs, arrays = [], []
    for name in spec["passRouting"]["orderedOutputRoster"]:
        backend = routing[name]
        selected = source_parts[backend][name]
        output_spec = oiio.ImageSpec(selected["spec"])
        add_provenance(output_spec, pair, backend, pair[backend.lower()], tool_hash, spec["outputContract"]["splitContractValue"])
        output_specs.append(output_spec)
        arrays.append(selected["pixels"])
    writer = oiio.ImageOutput.create(str(path))
    if writer is None:
        raise RuntimeError(oiio.geterror() or f"cannot create {path}")
    if not writer.open(str(path), output_specs):
        raise RuntimeError(writer.geterror() or f"cannot open multipart output {path}")
    for index, (output_spec, array) in enumerate(zip(output_specs, arrays)):
        if index > 0 and not writer.open(str(path), output_spec, "AppendSubimage"):
            raise RuntimeError(writer.geterror() or f"cannot append subimage {index}")
        if not writer.write_image(array):
            raise RuntimeError(writer.geterror() or f"cannot write subimage {index}")
    if not writer.close():
        raise RuntimeError(writer.geterror() or f"cannot close {path}")


def hash_payload(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key not in {"evidenceCoreHash", "baseFailure", "attacks", "attacksPassed", "verdict"}}


def validate(evidence: dict, spec: dict) -> str | None:
    if not all(item["match"] for item in evidence["parentObservations"]): return "PARENT_IDENTITY"
    if len(evidence["sourceObservations"]) != spec["evidenceGates"]["sourceExrs"] or not all(item["identityMatch"] for item in evidence["sourceObservations"]): return "SOURCE_IDENTITY"
    if not all(item["roleMatch"] for item in evidence["sourceObservations"]): return "SOURCE_ROLE_SWAP"
    expected_pairs = {(item["id"], item["cpu"]["runId"], item["metal"]["runId"]) for item in spec["pairs"]}
    observed_pairs = {(item["pairId"], item["cpuRunId"], item["metalRunId"]) for item in evidence["pairObservations"]}
    if expected_pairs != observed_pairs: return "PAIR_IDENTITY"
    if not all(item["imageGeometryAligned"] for item in evidence["pairObservations"]): return "IMAGE_GEOMETRY_ALIGNMENT"
    if not all(item["commonAttributesAligned"] for item in evidence["pairObservations"]): return "COMMON_ATTRIBUTE_ALIGNMENT"
    if not all(item["cryptomatteAttributesAligned"] for item in evidence["pairObservations"]): return "CRYPTOMATTE_MANIFEST_ALIGNMENT"
    if evidence["passRouting"] != spec["passRouting"]: return "PASS_ROUTING"
    if len(evidence["artifacts"]) != spec["evidenceGates"]["mergedExrs"] or not all(item["rosterMatch"] for item in evidence["artifacts"]): return "PASS_ROSTER"
    if not all(item["provenanceMatch"] for item in evidence["artifacts"]): return "PROVENANCE_METADATA"
    if not all(item["selectedPassesExact"] for item in evidence["artifacts"]): return "SELECTED_PASS_EXACTNESS"
    if not all(item["finite"] for item in evidence["sourceObservations"] + evidence["artifacts"]): return "NON_FINITE"
    if not all(item["byteExact"] for item in evidence["replicateComparisons"]): return "MERGE_REPLICATE_BYTE_IDENTITY"
    if evidence["operationCounts"] != spec["operationBoundary"]: return "OPERATION_BOUNDARY"
    if evidence.get("evidenceCoreHash") != canonical_hash(hash_payload(evidence)): return "EVIDENCE_SELF_HASH"
    return None


def run_attacks(evidence: dict, spec: dict) -> list[dict]:
    rows = []
    def add(identifier: str, reason: str, mutate) -> None:
        clone = copy.deepcopy(evidence); mutate(clone)
        clone["evidenceCoreHash"] = canonical_hash(hash_payload(clone)) if reason != "EVIDENCE_SELF_HASH" else "0" * 64
        observed = validate(clone, spec)
        rows.append({"id": identifier, "expectedReason": reason, "observedReason": observed, "passed": observed == reason})
    add("A01_PARENT", "PARENT_IDENTITY", lambda x: x["parentObservations"][0].update(match=False))
    add("A02_SOURCE", "SOURCE_IDENTITY", lambda x: x["sourceObservations"][0].update(identityMatch=False))
    add("A03_ROLE", "SOURCE_ROLE_SWAP", lambda x: x["sourceObservations"][0].update(roleMatch=False))
    add("A04_PAIR", "PAIR_IDENTITY", lambda x: x["pairObservations"][0].update(cpuRunId="SWAPPED"))
    add("A05_GEOMETRY", "IMAGE_GEOMETRY_ALIGNMENT", lambda x: x["pairObservations"][0].update(imageGeometryAligned=False))
    add("A06_COMMON_ATTR", "COMMON_ATTRIBUTE_ALIGNMENT", lambda x: x["pairObservations"][0].update(commonAttributesAligned=False))
    add("A07_CRYPTO_ATTR", "CRYPTOMATTE_MANIFEST_ALIGNMENT", lambda x: x["pairObservations"][0].update(cryptomatteAttributesAligned=False))
    add("A08_ROUTING", "PASS_ROUTING", lambda x: x["passRouting"]["METAL"].append("BFS_MASTER.Depth"))
    add("A09_ROSTER", "PASS_ROSTER", lambda x: x["artifacts"][0].update(rosterMatch=False))
    add("A10_PROVENANCE", "PROVENANCE_METADATA", lambda x: x["artifacts"][0].update(provenanceMatch=False))
    add("A11_EXACT", "SELECTED_PASS_EXACTNESS", lambda x: x["artifacts"][0].update(selectedPassesExact=False))
    add("A12_FINITE", "NON_FINITE", lambda x: x["artifacts"][0].update(finite=False))
    add("A13_REPLICATE", "MERGE_REPLICATE_BYTE_IDENTITY", lambda x: x["replicateComparisons"][0].update(byteExact=False))
    add("A14_OPERATION", "OPERATION_BOUNDARY", lambda x: x["operationCounts"].update(renders=1))
    add("A15_HASH", "EVIDENCE_SELF_HASH", lambda x: None)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--replay-receipt", type=Path)
    args = parser.parse_args()
    if sha256_file(args.spec) != SPEC_SHA256:
        raise RuntimeError("B51-D4 spec SHA differs")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("B51-D4 preregistration is not an ancestor")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    output = args.output_root.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("B51-D4 output root is not empty")
    output.mkdir(parents=True, exist_ok=True)

    parents = []
    for item in spec["parents"].values():
        path = ROOT / item["uri"]; actual = sha256_file(path) if path.is_file() else None
        parents.append({"uri": item["uri"], "expectedSha256": item["sha256"], "observedSha256": actual, "match": actual == item["sha256"]})
    if not all(item["match"] for item in parents):
        raise RuntimeError("B51-D4 parent identity differs")
    h1_receipt = json.loads((ROOT / spec["parents"]["h1Receipt"]["uri"]).read_text(encoding="utf-8"))
    h1_runs = {item["runId"]: item for item in h1_receipt["runs"]}

    source_observations, loaded = [], {}
    expected_roster = spec["passRouting"]["orderedOutputRoster"]
    for pair in spec["pairs"]:
        loaded[pair["id"]] = {}
        for backend in ("CPU", "METAL"):
            source = pair[backend.lower()]; path = ROOT / source["uri"]
            roster, parts = load_exr(path); report = h1_runs[source["runId"]]["report"]
            identity = path.is_file() and sha256_file(path) == source["sha256"] and path.stat().st_size == source["bytes"]
            role = report["deviceType"] == backend and report["variantId"] == pair["id"]
            source_observations.append({"pairId": pair["id"], "backend": backend, "runId": source["runId"], "uri": source["uri"], "expectedSha256": source["sha256"], "observedSha256": sha256_file(path), "expectedBytes": source["bytes"], "observedBytes": path.stat().st_size, "identityMatch": identity and roster == expected_roster, "roleMatch": role, "roster": roster, "finite": all(item["finite"] for item in parts.values())})
            loaded[pair["id"]][backend] = parts

    receipt_path = output / "assembly.receipt.json"
    if args.replay_receipt:
        frozen = json.loads(args.replay_receipt.read_text(encoding="utf-8"))
        if frozen["parentObservations"] != parents or frozen["sourceObservations"] != source_observations:
            raise RuntimeError("B51-D4 replay input observation differs")
        receipt_path.write_bytes(args.replay_receipt.read_bytes()); receipt = frozen
    else:
        disk = shutil.disk_usage(ROOT); projected = int(spec["evidenceGates"]["projectedWriteBytes"]); reserve = int(spec["evidenceGates"]["minimumDiskReserveBytes"])
        admission = {"availableBytes": disk.free, "projectedWriteBytes": projected, "minimumReserveBytes": reserve, "freeAfterProjectedBytes": disk.free - projected, "status": "ACCEPTED" if disk.free - projected >= reserve else "BLOCKED"}
        if admission["status"] != "ACCEPTED": raise RuntimeError("B51-D4 disk admission blocked")
        tool_freeze = git("rev-parse", "HEAD")
        tools = {"assembler": {"uri": "scripts/run-b51-native-split-backend-assembly-derivation.py", "sha256": sha256_file(Path(__file__))}, "audit": {"uri": "scripts/audit-b51-native-split-backend-assembly-derivation.py", "sha256": sha256_file(Path(__file__).with_name("audit-b51-native-split-backend-assembly-derivation.py"))}}
        receipt = {"schemaVersion": "bfs.nativeSplitBackendAssemblyReceipt.v0.1", "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": str(args.spec.resolve().relative_to(ROOT)), "specSha256": SPEC_SHA256}, "toolFreezeCommit": tool_freeze, "tools": tools, "parentObservations": parents, "sourceObservations": source_observations, "diskAdmission": admission}
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pair_observations, artifacts, replicate_comparisons = [], [], []
    geometry_fields = spec["alignmentContract"]["exactImageGeometryFields"]
    common_attrs = spec["alignmentContract"]["exactCommonAttributes"]
    crypto_attrs = spec["alignmentContract"]["exactCryptomatteAttributes"]
    allowed_differences = set(spec["alignmentContract"]["allowedTopLevelDifferences"])
    routing = {name: backend for backend, names in spec["passRouting"].items() if backend in {"CPU", "METAL"} for name in names}
    tool_hash = receipt["tools"]["assembler"]["sha256"]
    for pair in spec["pairs"]:
        parts = loaded[pair["id"]]
        geometry_rows = []
        for name in expected_roster:
            cpu_geometry = spec_geometry(parts["CPU"][name]["spec"], geometry_fields)
            metal_geometry = spec_geometry(parts["METAL"][name]["spec"], geometry_fields)
            geometry_rows.append({"pass": name, "cpu": cpu_geometry, "metal": metal_geometry, "match": cpu_geometry == metal_geometry})
        cpu_combined = parts["CPU"]["BFS_MASTER.Combined"]["spec"]
        metal_combined = parts["METAL"]["BFS_MASTER.Combined"]["spec"]
        common_cpu, common_metal = attributes(cpu_combined, common_attrs), attributes(metal_combined, common_attrs)
        crypto_cpu, crypto_metal = attributes(cpu_combined, crypto_attrs), attributes(metal_combined, crypto_attrs)
        top_diffs = top_level_differences(cpu_combined, metal_combined)
        unexpected = [item for item in top_diffs if item["name"] not in allowed_differences]
        pair_observations.append({"pairId": pair["id"], "cpuRunId": pair["cpu"]["runId"], "metalRunId": pair["metal"]["runId"], "imageGeometry": geometry_rows, "imageGeometryAligned": all(item["match"] for item in geometry_rows), "commonAttributes": {"cpu": common_cpu, "metal": common_metal}, "commonAttributesAligned": common_cpu == common_metal and not unexpected, "cryptomatteAttributes": {"cpu": crypto_cpu, "metal": crypto_metal}, "cryptomatteAttributesAligned": crypto_cpu == crypto_metal and all(value is not None for value in crypto_cpu.values()), "allowedTopLevelDifferencesObserved": [item for item in top_diffs if item["name"] in allowed_differences], "unexpectedTopLevelDifferences": unexpected})
        pair_paths = []
        for replicate in range(1, spec["outputContract"]["mergeReplicatesPerPair"] + 1):
            relative = Path(f"{pair['id']}_MERGE_R{replicate}") / "split-production.exr"; target = output / relative
            write_split_exr(target, pair, parts, spec, tool_hash); roster, merged = load_exr(target)
            pass_checks, provenance_checks = [], []
            for name in expected_roster:
                selected_backend = routing[name]; selected = parts[selected_backend][name]
                output_pixels = merged[name]["pixels"]
                pass_checks.append({"pass": name, "sourceBackend": selected_backend, "sourcePixelSha256": selected["pixelSha256"], "outputPixelSha256": merged[name]["pixelSha256"], "floatExact": bool(np.array_equal(output_pixels, selected["pixels"]))})
                expected_provenance = {"bfs:splitContract": spec["outputContract"]["splitContractValue"], "bfs:passSourceBackend": selected_backend, "bfs:passSourceRunId": pair[selected_backend.lower()]["runId"], "bfs:passSourceArtifactSha256": pair[selected_backend.lower()]["sha256"], "bfs:beautyArtifactSha256": pair["metal"]["sha256"], "bfs:dataArtifactSha256": pair["cpu"]["sha256"], "bfs:mergeToolGitBlobSha256": tool_hash}
                observed_provenance = attributes(merged[name]["spec"], list(expected_provenance))
                provenance_checks.append({"pass": name, "expected": expected_provenance, "observed": observed_provenance, "match": observed_provenance == expected_provenance})
            artifact = {"pairId": pair["id"], "replicate": replicate, "uri": str(relative), "sha256": sha256_file(target), "bytes": target.stat().st_size, "roster": roster, "rosterMatch": roster == expected_roster, "passChecks": pass_checks, "selectedPassesExact": all(item["floatExact"] for item in pass_checks), "provenanceChecks": provenance_checks, "provenanceMatch": all(item["match"] for item in provenance_checks), "finite": all(item["finite"] for item in merged.values())}
            artifacts.append(artifact); pair_paths.append(target)
        replicate_comparisons.append({"pairId": pair["id"], "left": str(pair_paths[0].relative_to(output)), "right": str(pair_paths[1].relative_to(output)), "leftSha256": sha256_file(pair_paths[0]), "rightSha256": sha256_file(pair_paths[1]), "byteExact": pair_paths[0].read_bytes() == pair_paths[1].read_bytes()})

    evidence = {"schemaVersion": "bfs.nativeSplitBackendAssemblyEvidence.v0.1", "experimentId": spec["experimentId"], "preregistration": receipt["preregistration"], "toolFreezeCommit": receipt["toolFreezeCommit"], "tools": receipt["tools"], "runtime": {"python": platform.python_version(), "openImageIO": oiio.VERSION_STRING, "numpy": np.__version__}, "parentObservations": receipt["parentObservations"], "sourceObservations": receipt["sourceObservations"], "diskAdmission": receipt["diskAdmission"], "passRouting": spec["passRouting"], "pairObservations": pair_observations, "artifacts": artifacts, "replicateComparisons": replicate_comparisons, "operationCounts": spec["operationBoundary"], "nonClaims": spec["nonClaims"]}
    evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); evidence["baseFailure"] = validate(evidence, spec); evidence["evidenceCoreHash"] = canonical_hash(hash_payload(evidence)); evidence["baseFailure"] = validate(evidence, spec)
    evidence["attacks"] = run_attacks(evidence, spec); evidence["attacksPassed"] = sum(item["passed"] for item in evidence["attacks"])
    evidence["verdict"] = "NATIVE_SPLIT_BACKEND_ASSEMBLY_DERIVATION_USABLE" if evidence["baseFailure"] is None and evidence["attacksPassed"] == len(spec["attacks"]) else "NATIVE_SPLIT_BACKEND_ASSEMBLY_DERIVATION_INVALID"
    (output / "results.json").write_text(json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"BFS_B51_D4_RESULT verdict={evidence['verdict']} attacks={evidence['attacksPassed']}/{len(spec['attacks'])} artifacts={len(artifacts)} failure={evidence['baseFailure'] or 'none'}", flush=True)
    for row in replicate_comparisons:
        print(f"BFS_B51_D4_PAIR {row['pairId']} byteExact={row['byteExact']} sha256={row['leftSha256']}", flush=True)


if __name__ == "__main__":
    main()
