#!/usr/bin/env python3
"""Independent synthetic oracle plus Python/OpenVDB full velocity-grid cross-check."""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
import openvdb

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-reader-c33-readiness-c2.v1.25.json"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main():
    spec = json.loads(SPEC.read_text()); evidence = ROOT / spec["evidence"]; work = Path(spec["workspace"])
    result = json.loads((evidence / "result.json").read_text()); body = dict(result); rh = body.pop("resultHash")
    assert digest(canonical(body)) == rh and result["status"] == "OBSERVED_READER_OUTPUT_PENDING_INDEPENDENT_AUDIT"
    assert result["specFileSha256"] == digest(SPEC.read_bytes())
    for row in spec["tools"]+spec["inputs"]:
        assert digest((ROOT / row["path"]).read_bytes()) == row["sha256"]
    manifest = json.loads((evidence / "work-manifest.json").read_text())
    before = {(r["path"],r["sha256"]) for r in manifest["files"]}
    actual = {(str(p.relative_to(work)),digest(p.read_bytes())) for p in work.rglob("*") if p.is_file()}
    assert actual == before and all(not p.is_symlink() for p in work.rglob("*"))
    checks = {}; grids = lambda value:{g["name"]:g for g in value["grids"]}
    synthetic = {name:grids(value) for name,value in result["synthetic"].items() if "grids" in value}
    base = synthetic["base"]
    expected_rows = [[1,2,3,1,-2,.5,1],[4,5,6,1,-2,.5,1],[7,6,1,1,-2,.5,1]]
    expected_hash = digest(b"".join(struct.pack("<7d",*r) for r in expected_rows))
    checks["knownParticleRows"] = base["particles"]["sampleRows"] == expected_rows
    checks["independentParticleHash"] = base["particles"]["decodedValueSha256"] == expected_hash
    checks["truncatedParticleCodecKnownValues"] = synthetic["truncated"]["particles"]["decodedValueSha256"] == expected_hash and synthetic["truncated"]["particles"]["sampleRows"] == expected_rows and synthetic["truncated"]["particles"]["attributeTypesAndCodecs"] == ["int32:trnc", "vec3s:trnc"]
    checks["positionChangeDetected"] = synthetic["position"]["particles"]["decodedValueSha256"] != expected_hash
    checks["pointVelocityChangeDetected"] = synthetic["point_velocity"]["particles"]["decodedValueSha256"] != expected_hash
    checks["pointFlagChangeDetected"] = synthetic["flag"]["particles"]["decodedValueSha256"] != expected_hash
    checks["mutationsPreservePointCount"] = all(synthetic[n]["particles"]["particleCount"] == 3 for n in ("base","position","point_velocity","flag"))
    checks["gridVelocityChangeDetected"] = synthetic["grid_velocity"]["velocity"]["decodedValueSha256"] != base["velocity"]["decodedValueSha256"]
    checks["signedFiniteVolumeIncludesInactiveTile"] = base["phi"]["negativeCells"] == 1024 and base["phi"]["negativeLevelsetOccupiedVolume"] == 16
    checks["zeroBackgroundNotLiquid"] = base["phi"]["zeroCells"] == 3071 and base["phi"]["positiveCells"] == 1
    checks["singleSignChangeDetected"] = synthetic["phi_sign"]["phi"]["negativeCells"] == 1023
    checks["halfStorageExactRepresentableField"] = synthetic["half"]["phi"]["saveFloatAsHalf"] and synthetic["half"]["phi"]["decodedValueSha256"] == base["phi"]["decodedValueSha256"]
    for name in spec["rejectFixtures"]: checks["reject_"+name] = result["synthetic"][name] == {"rejected":True}
    # Full independent finite-grid scalar/vector decoding, not metadata/occupancy comparison.
    comparisons = []; precision = []
    for row in result["frames"]:
        path = work / "mantaflow-cache" / "data" / f"fluid_data_{row['frame']:04d}.vdb"
        metadata = {g.name:g for g in openvdb.readAllGridMetadata(str(path))}
        assert set(metadata) == {"particles","velocity"}
        velocity = openvdb.read(str(path),"velocity")
        dims = tuple(velocity.metadata["file_base_resolution"])
        array = np.zeros(dims+(3,),dtype=np.float32); velocity.copyToArray(array)
        assert np.isfinite(array).all(); array[array == 0] = 0
        actual_hash = digest(array.transpose(2,1,0,3).astype("<f8").tobytes())
        measured = grids(row)
        precision.append({"frame":row["frame"],"halfStorage":{name:bool(g.saveFloatAsHalf) for name,g in metadata.items()},"matches":all(bool(g.saveFloatAsHalf)==measured[name]["saveFloatAsHalf"] for name,g in metadata.items())})
        comparisons.append({"frame":row["frame"],"hash":actual_hash,"matches":actual_hash == measured["velocity"]["decodedValueSha256"]})
        assert dims == (96,53,62)
    phi = openvdb.read(str(work / "fixtures" / "base.vdb"),"phi")
    values = np.zeros((16,16,16),dtype=np.float32); phi.copyToArray(values)
    checks["independentSyntheticPhiHash"] = digest(values.transpose(2,1,0).astype("<f8").tobytes()) == base["phi"]["decodedValueSha256"]
    checks["all36VelocityGridsExactAcrossReaders"] = len(comparisons) == 36 and all(r["matches"] for r in comparisons)
    checks["all36PointAttributeRostersRead"] = len(result["frames"]) == 36 and all(grids(r)["particles"]["particleCount"]>0 and grids(r)["particles"]["attributes"] == ["P","U","particles_velocity"] for r in result["frames"])
    checks["noNativePhiInRetainedCache"] = all(set(grids(r)) == {"particles","velocity"} for r in result["frames"])
    checks["retainedExportPrecisionIndependentlyObserved"] = len(precision)==36 and all(r["matches"] for r in precision)
    checks["nativeLibraryVersion"] = tuple(openvdb.LIBRARY_VERSION)==(13,0,0) and openvdb.FILE_FORMAT_VERSION==225
    checks["exact36FrameSequence"] = [r["frame"] for r in result["frames"]] == list(range(1,37))
    checks["zeroSimulationOperations"] = all(v==0 for v in result["counts"].values())
    checks["helperBound"] = digest((work/"native-vdb-reader").read_bytes()) == result["helperSha256"]
    checks["workBytesUnchanged"] = actual == {(str(p.relative_to(work)),digest(p.read_bytes())) for p in work.rglob("*") if p.is_file()}
    retained = json.loads((ROOT / spec["cacheManifest"]).read_text())
    checks["retainedCacheStillExact"] = all(digest((Path(retained["root"])/r["path"]).read_bytes()) == r["sha256"] for r in retained["files"] if r["path"].startswith("mantaflow-cache/"))
    retained_roots_ok = True
    for row in spec["retainedRoots"]:
        root = Path(row["root"])
        rows = [{"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":digest(p.read_bytes())} for p in sorted(root.rglob("*"),key=lambda p:str(p)) if p.is_file()]
        retained_roots_ok &= digest(canonical(rows)) == row["sha256"]
    checks["retainedAttempt113Exact"] = retained_roots_ok
    audit = {"schemaVersion":"bfs.rc6C33ReadinessAudit.v1", "status":"PASS_READER_READINESS" if all(checks.values()) else "FAIL", "checks":checks,"passCount":sum(checks.values()),"checkCount":len(checks),"resultHash":rh,"specFileSha256":digest(SPEC.read_bytes()),"independentVelocityComparisons":comparisons,"observedPrecision":precision,"claimCeiling":"Reader readiness on synthetic data and copied C29 only; no new phi observation on real impact, passive cache equivalence, physical repair or render."}
    audit["auditHash"] = digest(canonical(audit))
    with (evidence / "independent-audit.json").open("x") as f: json.dump(audit,f,indent=2,sort_keys=True); f.write("\n")
    assert sum(p.stat().st_size for p in evidence.rglob("*") if p.is_file()) <= spec["maxEvidenceBytes"]
    print(json.dumps({"status":audit["status"],"checks":f"{sum(checks.values())}/{len(checks)}","auditHash":audit["auditHash"]}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
