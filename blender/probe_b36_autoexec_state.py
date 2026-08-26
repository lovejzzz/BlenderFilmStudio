import json
import os
from pathlib import Path

import bpy


report_path = Path(os.environ["BFS_B36_REPORT_PATH"]).resolve()
marker_path = Path(os.environ["BFS_B36_MARKER_PATH"]).resolve()
allowed_root = Path(os.environ["BFS_B36_ALLOWED_ROOT"]).resolve()
for candidate in (report_path, marker_path):
    try:
        candidate.relative_to(allowed_root)
    except ValueError as error:
        raise RuntimeError("B36 probe path escaped allowed work root") from error

text = bpy.data.texts.get("bfs_b36_registered_canary.py")
report = {
    "schemaVersion": "bfs.autoexecProbe.v0.1",
    "processId": os.getpid(),
    "blenderVersion": bpy.app.version_string,
    "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
    "autoexecFail": bool(getattr(bpy.app, "autoexec_fail", False)),
    "autoexecFailMessage": str(getattr(bpy.app, "autoexec_fail_message", "")),
    "registeredTextPresent": text is not None,
    "registeredTextUseModule": bool(text.use_module) if text else False,
    "markerExistsAtProbe": marker_path.is_file(),
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(
    "BFS_B36_PROBE "
    f"pid={report['processId']} marker={report['markerExistsAtProbe']} "
    f"autoexecFail={report['autoexecFail']}"
)
