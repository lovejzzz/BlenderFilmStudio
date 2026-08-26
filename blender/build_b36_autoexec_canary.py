import argparse
import json
from pathlib import Path

import bpy


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--allowed-root", required=True)
    argv = []
    if "--" in __import__("sys").argv:
        argv = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    return parser.parse_args(argv)


args = arguments()
output_path = Path(args.output).resolve()
allowed_root = Path(args.allowed_root).resolve()
output_path.parent.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)

script = f'''import json
import os
from pathlib import Path
import bpy

allowed_root = Path({json.dumps(str(allowed_root))}).resolve()
marker_value = os.environ.get("BFS_B36_MARKER_PATH")
if not marker_value:
    raise RuntimeError("BFS_B36_MARKER_PATH is required")
marker_path = Path(marker_value).resolve()
try:
    marker_path.relative_to(allowed_root)
except ValueError as error:
    raise RuntimeError("B36 marker escaped allowed work root") from error
marker_path.parent.mkdir(parents=True, exist_ok=True)
payload = {{
    "schemaVersion": "bfs.autoexecCanaryMarker.v0.1",
    "processId": os.getpid(),
    "token": os.environ.get("BFS_B36_FAKE_SECRET"),
    "blenderVersion": bpy.app.version_string,
    "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
}}
marker_path.write_text(json.dumps(payload, sort_keys=True) + "\\n", encoding="utf-8")
'''

text = bpy.data.texts.new("bfs_b36_registered_canary.py")
text.write(script)
text.use_module = True
bpy.context.scene["bfsExperiment"] = "B36"
bpy.context.scene["bfsCanary"] = "REGISTERED_TEXT_ONLY"
bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)
print(f"BFS_B36_CANARY_CREATED path={output_path} text={text.name} use_module={text.use_module}")
