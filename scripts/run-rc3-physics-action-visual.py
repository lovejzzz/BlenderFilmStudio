#!/usr/bin/env python3
"""Run the frozen one-start RC3 direct visual packet render."""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_EVIDENCE = ROOT / "experiments/physics-native-action/RC3-2026-09-01-development-attempt-03"
WORK = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC3-visual-attempt-01")
EVIDENCE = ROOT / "experiments/physics-native-action/RC3-2026-09-01-visual-attempt-01"
BINARY = Path("/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC2-2026-09-01-attempt-01/build/bin/Film Studio Engine F0.app/Contents/MacOS/Blender")
TOOL = ROOT / "scripts/render-rc3-physics-action-review.py"
D1_BLEND = Path(json.loads((SOURCE_EVIDENCE / "D1-build.json").read_text())["blend"]["path"])
H1_BLEND = Path(json.loads((SOURCE_EVIDENCE / "H1-build.json").read_text())["blend"]["path"])


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): digest.update(chunk)
    return digest.hexdigest()


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value); body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def size(root): return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def command(index, name, argv):
    out, err = EVIDENCE / "logs" / f"{index:02d}-{name}.stdout.log", EVIDENCE / "logs" / f"{index:02d}-{name}.stderr.log"
    started = time.monotonic()
    env = dict(os.environ); env.update({"BLENDER_USER_CONFIG": str(WORK / "user/config"), "BLENDER_USER_SCRIPTS": str(WORK / "user/scripts"), "BLENDER_USER_DATAFILES": str(WORK / "user/datafiles"), "BLENDER_USER_EXTENSIONS": str(WORK / "user/extensions")})
    with out.open("wb") as stdout, err.open("wb") as stderr:
        done = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
    row = {"index": index, "name": name, "argv": [str(item) for item in argv], "exitCode": done.returncode, "wallSeconds": round(time.monotonic() - started, 6), "stdoutSha256": sha(out), "stderrSha256": sha(err)}
    row["processHash"] = self_hash(row, "processHash"); write(EVIDENCE / "processes" / f"{index:02d}-{name}.json", row)
    if done.returncode: raise RuntimeError(f"{name} failed")
    return row


def main():
    if WORK.exists() or EVIDENCE.exists(): raise RuntimeError("visual roots are not fresh")
    if sha(BINARY) != "9e24e64976e5747a415bff3633907c1612871b6220917621fbadebfa04005efb": raise RuntimeError("binary mismatch")
    expected = {case: json.loads((SOURCE_EVIDENCE / f"{case}-build.json").read_text())["blend"]["sha256"] for case in ("D1", "H1")}
    if sha(D1_BLEND) != expected["D1"] or sha(H1_BLEND) != expected["H1"]: raise RuntimeError("source blend mismatch")
    if shutil.disk_usage(WORK.parent).free < 100 * 1024**3: raise RuntimeError("free reserve")
    for path in (WORK, EVIDENCE, EVIDENCE / "logs", EVIDENCE / "processes", WORK / "user/config", WORK / "user/scripts", WORK / "user/datafiles", WORK / "user/extensions"):
        path.mkdir(parents=True, exist_ok=False)
    processes = [command(1, "render-both-cases", [str(BINARY), "--background", "--disable-autoexec", "--offline-mode", str(D1_BLEND), "--python", str(TOOL), "--", "--d1-blend", str(D1_BLEND), "--h1-blend", str(H1_BLEND), "--evidence-root", str(EVIDENCE)])]
    render = json.loads((EVIDENCE / "render.json").read_text())
    media = []
    index = 2
    for case in render["cases"]:
        name, start = case["case"], case["clip"]["startFrame"]
        clip_root = EVIDENCE / name / "clip"
        video, sheet = EVIDENCE / name / f"{name.lower()}-contact-clip.mp4", EVIDENCE / name / f"{name.lower()}-contact-sheet.png"
        processes.append(command(index, f"{name.lower()}-video", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "24", "-start_number", str(start), "-i", str(clip_root / "frame-%04d.png"), "-frames:v", "48", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)])); index += 1
        processes.append(command(index, f"{name.lower()}-sheet", ["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-start_number", str(start), "-i", str(clip_root / "frame-%04d.png"), "-vf", "select='not(mod(n,6))',scale=480:270,tile=4x2", "-frames:v", "1", str(sheet)])); index += 1
        media.append({"case": name, "video": {"path": str(video), "sha256": sha(video), "bytes": video.stat().st_size}, "contactSheet": {"path": str(sheet), "sha256": sha(sheet), "bytes": sheet.stat().st_size}})
    evidence_bytes = size(EVIDENCE)
    receipt = {"schemaVersion": "bfs.rc3PhysicsActionVisualReceipt.v0.1", "status": "PASS_RENDER_PACKET_READY", "sourceEvidence": str(SOURCE_EVIDENCE.relative_to(ROOT)), "sourceBlends": {"D1": expected["D1"], "H1": expected["H1"]}, "binarySha256": sha(BINARY), "toolSha256": sha(TOOL), "render": {"sha256": sha(EVIDENCE / "render.json"), "cases": [{"case": row["case"], "stillCount": len(row["stills"]), "clipFrameCount": row["clip"]["frameCount"]} for row in render["cases"]]}, "media": media, "processes": [{"index": row["index"], "name": row["name"], "processHash": row["processHash"]} for row in processes], "counts": {"productStarts": 1, "reviewStills": 6, "clipFrames": 96, "ffmpegProcesses": 4, "sceneMutations": 0, "blendSaves": 0, "networkCalls": 0}, "resources": {"evidenceBytes": evidence_bytes, "freeBytesAfter": shutil.disk_usage(WORK.parent).free}}
    receipt["receiptHash"] = self_hash(receipt, "receiptHash"); write(EVIDENCE / "receipt.json", receipt)
    print("RC3_VISUAL=" + canonical(receipt))


if __name__ == "__main__": main()
