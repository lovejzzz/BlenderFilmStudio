# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent F0.6 Expert/Film mode round-trip check."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import bpy


parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
scene = bpy.context.scene
state = scene.film_studio


def snapshot():
    return {
        "expertMode": state.expert_mode,
        "sceneCount": len(bpy.data.scenes),
        "shotCount": len(state.shots),
        "shotIds": [shot.identifier for shot in state.shots],
        "shotCameras": [shot.camera.name if shot.camera else None for shot in state.shots],
        "sceneCamera": scene.camera.name if scene.camera else None,
    }


before = snapshot()
expert_result = sorted(bpy.ops.film_studio.set_mode(mode="EXPERT"))
expert = snapshot()
film_result = sorted(bpy.ops.film_studio.set_mode(mode="FILM"))
after = snapshot()
checks = {
    "startedInFilmMode": before["expertMode"] is False,
    "expertOperatorFinished": expert_result == ["FINISHED"],
    "enteredExpertMode": expert["expertMode"] is True,
    "filmOperatorFinished": film_result == ["FINISHED"],
    "returnedToFilmMode": after["expertMode"] is False,
    "sceneCountExact": before["sceneCount"] == expert["sceneCount"] == after["sceneCount"] == 1,
    "shotCountExact": before["shotCount"] == expert["shotCount"] == after["shotCount"] == 1,
    "shotStateExact": before["shotIds"] == expert["shotIds"] == after["shotIds"] == ["SH010"],
    "cameraStateExact": before["shotCameras"] == expert["shotCameras"] == after["shotCameras"] == ["SHOT_SH010_WIDE"],
    "sceneCameraExact": before["sceneCamera"] == expert["sceneCamera"] == after["sceneCamera"] == "SHOT_SH010_WIDE",
}
body = {
    "schemaVersion": "bfs.f0.6.expertModeRoundTrip.v0.1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "before": before,
    "expert": expert,
    "after": after,
    "operations": {"expert": expert_result, "film": film_result},
    "checks": checks,
}
body["receiptHash"] = hashlib.sha256((json.dumps(body, indent=2) + "\n").encode()).hexdigest()
descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
try:
    os.write(descriptor, (json.dumps(body, indent=2) + "\n").encode())
    os.fsync(descriptor)
finally:
    os.close(descriptor)
if body["status"] != "PASS":
    raise RuntimeError("Expert/Film mode round-trip failed")
print("F06_EXPERT_ROUNDTRIP PASS scenes=1 shots=1", flush=True)
