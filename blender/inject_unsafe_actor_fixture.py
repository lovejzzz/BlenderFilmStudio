"""Create a negative actor fixture containing a non-simple scripted Driver.

The expression is intentionally harmless but requires the full Python driver
path. This trusted test harness is never called by an ActorSpec runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    head = bpy.data.objects.get("HEAD")
    if not head or not head.data.shape_keys:
        raise RuntimeError("HEAD shape-key data is missing")
    jaw = head.data.shape_keys.key_blocks.get("jawOpen")
    if not jaw:
        raise RuntimeError("jawOpen shape key is missing")
    curve = jaw.driver_add("value")
    curve.driver.type = "SCRIPTED"
    curve.driver.expression = "[frame][0]"
    if curve.driver.is_simple_expression:
        raise RuntimeError("Negative fixture expression unexpectedly classified as simple")
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True, relative_remap=True)
    report = {
        "documentType": "BFS_UNSAFE_ACTOR_FIXTURE",
        "input": str(args.input),
        "output": str(args.output),
        "sha256": sha256_file(args.output),
        "driver": {
            "owner": head.data.shape_keys.name,
            "dataPath": curve.data_path,
            "type": curve.driver.type,
            "expression": curve.driver.expression,
            "isSimpleExpression": curve.driver.is_simple_expression,
        },
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_UNSAFE_ACTOR_FIXTURE_OK {report['sha256']} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_UNSAFE_ACTOR_FIXTURE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
