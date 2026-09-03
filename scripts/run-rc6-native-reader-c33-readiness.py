#!/usr/bin/env python3
"""One bounded helper build and copied-cache observation. No Blender imports."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/ai-native-studio-rc6-native-reader-c33-readiness.v1.23.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def seal(value, field):
    return {**value, field: hashlib.sha256(canonical(value)).hexdigest()}


def write(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def tree(root):
    rows = []
    for p in sorted(root.rglob("*")):
        assert not p.is_symlink(), f"symlink rejected: {p}"
        if p.is_file():
            rows.append({"path": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": sha(p)})
    return rows


def main():
    spec = json.loads(SPEC.read_text())
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()
    assert not git("status", "--porcelain")
    commit = git("rev-parse", "HEAD")
    assert git("rev-parse", "HEAD^") == spec["researchParent"]
    assert subprocess.check_output(["git", "show", f"HEAD:{SPEC.relative_to(ROOT)}"], cwd=ROOT) == SPEC.read_bytes()
    for row in spec["inputs"] + spec["tools"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
    for row in spec["headerTrees"]:
        assert hashlib.sha256(canonical(tree(Path(row["path"])))).hexdigest() == row["sha256"]
    work, evidence = Path(spec["workspace"]), ROOT / spec["evidence"]
    for p in (work, evidence):
        assert not p.exists() and not p.is_symlink() and p.parent.resolve() == p.parent
    assert shutil.disk_usage(ROOT).free >= spec["reserveBytes"] + spec["maxWorkspaceBytes"] + spec["maxEvidenceBytes"]
    retained_manifest = json.loads((ROOT / spec["cacheManifest"]).read_text())
    retained = Path(retained_manifest["root"])
    cache_rows = [r for r in retained_manifest["files"] if r["path"].startswith("mantaflow-cache/")]
    assert len(cache_rows) == 108 and sum(r["bytes"] for r in cache_rows) == 14050289
    def retained_ok():
        return all((retained / r["path"]).resolve() == retained / r["path"] and sha(retained / r["path"]) == r["sha256"] for r in cache_rows)
    assert retained_ok()
    work.mkdir(); evidence.mkdir(); (work / "tmp").mkdir(); (work / "fixtures").mkdir(); (evidence / "logs").mkdir()
    started = time.monotonic(); processes = []; result = {"status": "FAIL", "researchExecutionCommit": commit}
    env = {**os.environ, "TMPDIR": str(work / "tmp"), "PYTHONDONTWRITEBYTECODE": "1"}
    def sizes():
        assert sum(r["bytes"] for r in tree(work)) <= spec["maxWorkspaceBytes"]
        assert sum(r["bytes"] for r in tree(evidence)) <= spec["maxEvidenceBytes"]
    def run(name, argv, timeout, expected=0):
        assert time.monotonic() - started < spec["totalTimeoutSeconds"]
        before = time.monotonic()
        with (evidence / "logs" / (name + ".stdout")).open("xb") as out, (evidence / "logs" / (name + ".stderr")).open("xb") as err:
            p = subprocess.run(argv, cwd=ROOT, env=env, stdout=out, stderr=err, timeout=timeout)
        processes.append({"name": name, "argv": [str(a) for a in argv], "returncode": p.returncode, "seconds": time.monotonic()-before})
        sizes()
        assert p.returncode == expected, f"{name} exit {p.returncode}, expected {expected}"
        output = (evidence / "logs" / (name + ".stdout")).read_text()
        if expected:
            assert output == "" and "NATIVE_VDB_REJECT:" in (evidence / "logs" / (name + ".stderr")).read_text()
            return {"rejected": True}
        return json.loads(output) if name != "compile" else None
    try:
        helper = work / "native-vdb-reader"
        argv = [spec["compiler"], "-std=c++17", "-O1", "-Wno-deprecated-declarations"]
        argv += ["-I" + r["path"] for r in spec["headerTrees"]]
        argv += [str(ROOT / spec["readerSource"]), "-L" + spec["libraryRoot"], "-Wl,-rpath," + spec["libraryRoot"], "-lopenvdb", "-ltbb", "-o", str(helper)]
        run("compile", argv, 180)
        run("fixtures", [helper, "--fixtures", work / "fixtures"], 60)
        synthetic = {}
        for name in spec["fixtureNames"]:
            synthetic[name] = run("synthetic-"+name, [helper, work / "fixtures" / (name+".vdb")], 60, 2 if name in spec["rejectFixtures"] else 0)
        # Copy only after the helper has passed format/rejection execution checks.
        for row in cache_rows:
            destination = work / row["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            with (retained / row["path"]).open("rb") as src, destination.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            assert sha(destination) == row["sha256"]
        frames = []
        for frame in range(1, 37):
            value = run(f"frame-{frame:04d}", [helper, work / "mantaflow-cache" / "data" / f"fluid_data_{frame:04d}.vdb"], 60)
            frames.append({"frame": frame, **value})
        assert retained_ok()
        assert all(sha(work / row["path"]) == row["sha256"] for row in cache_rows)
        result.update(status="OBSERVED_READER_OUTPUT_PENDING_INDEPENDENT_AUDIT", synthetic=synthetic, frames=frames, helperSha256=sha(helper), cacheFiles=108, cacheBytes=14050289, retainedCacheUnchanged=True)
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    result.update(schemaVersion="bfs.rc6C33Readiness.v1", specFileSha256=sha(SPEC), processes=processes, elapsedSeconds=time.monotonic()-started, peakChildRssBytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, counts={"blenderStarts":0,"bakes":0,"renders":0,"engineBuilds":0,"engineEdits":0,"network":0})
    result = seal(result, "resultHash")
    write(evidence / "result.json", result)
    write(evidence / "work-manifest.json", seal({"root":str(work),"files":tree(work)},"manifestHash"))
    sizes()
    print(json.dumps({"status":result["status"],"resultHash":result["resultHash"],"error":result.get("error")}))
    return 0 if result["status"].startswith("OBSERVED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
