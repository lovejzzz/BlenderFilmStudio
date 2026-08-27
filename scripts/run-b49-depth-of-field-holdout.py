"""Run ten isolated B49-DOF formal holdout workers and write a receipt."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_COMMIT = "7b5ed4d75cdfd428fdf816ca30d328844e216988"
SPEC_URI = "specs/codex-worker-depth-of-field-holdout.v0.1.json"
SPEC_SHA256 = "c486eb6666b462a4dd0ce115fab1ddb13f9e15d4af4f90a904bbeb84206821d3"
DOCKER_BASE = ["docker", "--host", "unix:///Users/tianxing/.colima/default/docker.sock"]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(args, label, timeout=120):
    process = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"{label} failed ({process.returncode}): {(process.stderr or process.stdout).strip()[-5000:]}")
    return process.stdout.strip()


def observe(uri, expected):
    path = ROOT / uri
    actual = sha256_file(path) if path.exists() else None
    return {"uri": uri, "expectedSha256": expected, "observedSha256": actual, "match": actual == expected}


def docker_args(spec, name, cell, shot, output):
    contract = spec["containerContract"]
    args = [*DOCKER_BASE, "run", "--rm", "--name", name, "--platform", contract["platform"], "--pull", "never", "--read-only", "--network", contract["network"], "--user", contract["user"], "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--pids-limit", str(contract["pidsLimit"]), "--memory", str(contract["memoryBytes"]), "--cpus", str(contract["cpus"]), "--shm-size", str(contract["shmBytes"]), "--mount", f"type=bind,src={ROOT},dst=/repo,readonly", "--mount", f"type=bind,src={output},dst=/repo/worker-output", "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=536870912,uid=65532,gid=65532", "--tmpfs", "/work:rw,noexec,nosuid,nodev,size=1073741824,uid=65532,gid=65532"]
    env = {"HOME": "/work/home", "TMPDIR": "/work/tmp", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "BLENDER_USER_CONFIG": "/work/blender-config", "BLENDER_USER_SCRIPTS": "/work/blender-scripts", "OCIO": f"/repo/{spec['ocio']['uri']}"}
    for key, value in sorted(env.items()):
        args.extend(["--env", f"{key}={value}"])
    return [*args, spec["image"]["id"], "--background", "--disable-autoexec", "--offline-mode", f"/repo/{shot['blendUri']}", "--python-exit-code", "1", "--python", "/repo/blender/render_b49_depth_of_field_holdout.py", "--", "--cell-id", cell["id"], "--source-sha256", shot["blendSha256"], "--plan-hash", shot["planHash"], "--scene-hash", shot["sceneHash"], "--structure-hash", shot["structureHash"], "--ocio-sha256", spec["ocio"]["sha256"], "--output-dir", "/repo/worker-output"]


def run_timed(spec, name, args):
    started = time.monotonic()
    process = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timeout_triggered = term_sent = kill_sent = False
    try:
        stdout, stderr = process.communicate(timeout=spec["containerContract"]["wallTimeMs"] / 1000)
    except subprocess.TimeoutExpired:
        timeout_triggered = True
        term = subprocess.run([*DOCKER_BASE, "kill", "--signal", "TERM", name], capture_output=True, text=True, check=False)
        term_sent = term.returncode == 0
        try:
            stdout, stderr = process.communicate(timeout=spec["containerContract"]["killGraceMs"] / 1000)
        except subprocess.TimeoutExpired:
            killed = subprocess.run([*DOCKER_BASE, "kill", "--signal", "KILL", name], capture_output=True, text=True, check=False)
            kill_sent = killed.returncode == 0
            stdout, stderr = process.communicate()
    return {"exitCode": process.returncode, "signal": None if process.returncode is None or process.returncode >= 0 else signal.Signals(-process.returncode).name, "elapsedMs": round((time.monotonic() - started) * 1000), "stdout": stdout, "stderr": stderr, "timeoutTriggered": timeout_triggered, "termSent": term_sent, "killSent": kill_sent}


def main():
    spec_path = ROOT / SPEC_URI
    if sha256_file(spec_path) != SPEC_SHA256: raise RuntimeError("B49-DOF spec SHA differs")
    spec = json.loads(spec_path.read_text())
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT).returncode != 0: raise RuntimeError("B49-DOF preregistration is not an ancestor")
    tool_freeze = probe(["git", "rev-parse", "HEAD"], "B49-DOF tool freeze")
    output_root = ROOT / spec["outputRoot"]
    if output_root.exists() and any(output_root.iterdir()): raise RuntimeError("B49-DOF output root is not empty")
    parents = spec["parents"]
    parent_observations = [observe(item["uri"], item["sha256"]) for item in parents.values()]
    if not all(item["match"] for item in parent_observations): raise RuntimeError("B49-DOF parent identity differs")
    source_pairs = [(shot["blendUri"], shot["blendSha256"]) for shot in spec["shots"]] + [(spec["ocio"]["uri"], spec["ocio"]["sha256"]), (SPEC_URI, SPEC_SHA256)]
    source_observations = [observe(uri, digest) for uri, digest in source_pairs]
    if not all(item["match"] for item in source_observations): raise RuntimeError("B49-DOF source identity differs")
    for shot in spec["shots"]:
        if (ROOT / shot["blendUri"]).stat().st_size != shot["blendBytes"]: raise RuntimeError(f"B49-DOF source size differs: {shot['id']}")
    image = json.loads(probe([*DOCKER_BASE, "image", "inspect", spec["image"]["id"]], "B49-DOF image inspect"))[0]
    if (image["Id"], image["Os"], image["Architecture"], image["Size"]) != (spec["image"]["id"], spec["image"]["os"], spec["image"]["architecture"], spec["image"]["dockerReportedSizeBytes"]): raise RuntimeError("B49-DOF image identity differs")
    inspector = {"pythonExecutable": sys.executable, "pythonVersion": platform.python_version(), "pythonExecutableSha256": sha256_file(sys.executable), "packages": {"openImageIO": __import__("OpenImageIO").VERSION_STRING, "numpy": __import__("numpy").__version__}}
    disk = shutil.disk_usage(ROOT)
    free_after = disk.free - int(spec["diskAdmission"]["projectedWriteBytes"])
    disk_admission = {"availableBytes": str(disk.free), "projectedWriteBytes": spec["diskAdmission"]["projectedWriteBytes"], "minimumReserveBytes": spec["diskAdmission"]["minimumReserveBytes"], "freeAfterProjectedBytes": str(free_after), "status": "ACCEPTED" if free_after >= int(spec["diskAdmission"]["minimumReserveBytes"]) else "BLOCKED"}
    if disk_admission["status"] != "ACCEPTED": raise RuntimeError("B49-DOF disk admission blocked")
    output_root.mkdir(parents=True, exist_ok=True)
    runs, operations = [], []
    for cell in spec["cells"]:
        shot = next(item for item in spec["shots"] if item["id"] == cell["shot"])
        output = output_root / cell["id"]
        output.mkdir()
        output.chmod(0o777)
        name = f"bfs-b49-dof-h-{cell['id'].lower().replace('_', '-')}"
        argv = docker_args(spec, name, cell, shot, output)
        operations.append(f"DOCKER_RUN_{cell['id']}")
        result = run_timed(spec, name, argv)
        (output / "stdout.log").write_text(result["stdout"])
        (output / "stderr.log").write_text(result["stderr"])
        try: report = json.loads((output / "render.report.json").read_text())
        except Exception: report = None
        runs.append({"runId": cell["id"], "shotId": cell["shot"], "containerName": name, "imageId": spec["image"]["id"], "argv": argv, **result, "report": report})
        print(f"BFS_B49_DOF_HOLDOUT_RUN {cell['id']} completed={result['exitCode'] == 0 and bool(report and report.get('passed'))} elapsedMs={result['elapsedMs']}", flush=True)
        if result["exitCode"] != 0 or result["timeoutTriggered"] or not report or not report.get("passed"): raise RuntimeError(f"B49-DOF {cell['id']} failed")
    operations.append("DOCKER_RUNNING_CONTAINER_CHECK")
    running = [name for name in probe([*DOCKER_BASE, "ps", "--format", "{{.Names}}"], "B49-DOF running check").splitlines() if name.startswith("bfs-b49-dof-h-")]
    for run in runs: operations.append(f"HOST_EXR_ANALYSIS_{run['runId']}")
    tool_paths = {"runner": "scripts/run-b49-depth-of-field-holdout.py", "renderer": "blender/render_b49_depth_of_field_holdout.py", "analyzer": "scripts/analyze-b49-depth-of-field-holdout.py", "audit": "scripts/audit-b49-depth-of-field-holdout.py", "metricLibrary": "scripts/analyze-b49-motion-blur-holdout.py"}
    tools = {key: {"uri": uri, "sha256": sha256_file(ROOT / uri)} for key, uri in tool_paths.items()}
    receipt = {"schemaVersion": "bfs.depthOfFieldHoldoutRunReceipt.v0.1", "preregistration": {"commit": PREREGISTRATION_COMMIT, "specUri": SPEC_URI, "specSha256": SPEC_SHA256}, "toolFreezeCommit": tool_freeze, "tools": tools, "parents": parents, "parentObservations": parent_observations, "sourceObservations": source_observations, "image": {"id": image["Id"], "os": image["Os"], "architecture": image["Architecture"], "sizeBytes": image["Size"]}, "hostInspectorObservation": inspector, "diskAdmission": disk_admission, "securityBoundary": spec["containerContract"], "operationBoundary": spec["operationBoundary"], "runtimeOperations": operations, "runs": runs, "cleanup": {"experimentContainersRunningAfter": len(running)}}
    receipt_path = output_root / "run.receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    analysis = subprocess.run([sys.executable, str(ROOT / "scripts/analyze-b49-depth-of-field-holdout.py"), "--spec", str(spec_path), "--receipt", str(receipt_path), "--output", str(output_root / "results.json")], cwd=ROOT, text=True, check=False)
    if analysis.returncode != 0: raise RuntimeError(f"B49-DOF analysis failed ({analysis.returncode})")


if __name__ == "__main__":
    main()
