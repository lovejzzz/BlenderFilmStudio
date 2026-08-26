"""Produce a hash-valid PROP_B08 library whose declared target object is missing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    bpy.data.objects["B06_PROP"].name = "B08_OTHER_PROP"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), check_existing=False, compress=True)
    print(f"BFS_B08_NEGATIVE_ASSET_OK {args.output}")


if __name__ == "__main__":
    main()
