"""Export the pinned built-in ACES 2 CG config from Blender's OCIO 2.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import PyOpenColorIO as ocio


CONFIG_NAME = "cg-config-v4.0.0_aces-v2.0_ocio-v2.5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-record", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def main() -> None:
    args = parse_args()
    config = ocio.Config.CreateFromBuiltinConfig(CONFIG_NAME)
    serialized = config.serialize()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    record = {
        "documentType": "BFS_OCIO_SOURCE_RECORD",
        "configName": CONFIG_NAME,
        "configSha256": digest,
        "openColorIOVersion": ocio.GetVersion(),
        "defaultDisplay": config.getDefaultDisplay(),
        "defaultView": config.getDefaultView(config.getDefaultDisplay()),
        "upstreamRepository": "https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES",
        "upstreamRelease": "v4.0.0",
        "upstreamCommit": "97a4718",
        "license": "BSD-3-Clause",
        "licenseUrl": "https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/blob/v4.0.0/LICENSE",
    }
    args.source_record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_OCIO_EXPORTED {CONFIG_NAME} {digest} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_OCIO_EXPORT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
