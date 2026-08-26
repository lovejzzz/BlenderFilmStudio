"""Create a delivery-metadata-complete multipart EXR without changing pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import OpenImageIO as oiio


ACESCG_CHROMATICITIES = (
    0.713, 0.293,
    0.165, 0.830,
    0.128, 0.044,
    0.32168, 0.33767,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--frame-start", type=int, default=1)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--owner", default="BlenderFilmStudio research")
    parser.add_argument("--comments", default="BFS research master; generated from a verified SceneSpec and BuildPlan")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def packed_timecode(frame: int, frame_start: int, fps: int) -> tuple[int, int]:
    if fps > 30:
        raise ValueError("This v0.1 time-code packer supports integer frame rates up to 30")
    absolute = max(0, frame - frame_start)
    frames = absolute % fps
    seconds_total = absolute // fps
    seconds = seconds_total % 60
    minutes = (seconds_total // 60) % 60
    hours = (seconds_total // 3600) % 24
    value = (
        (frames % 10)
        | ((frames // 10) << 4)
        | ((seconds % 10) << 8)
        | ((seconds // 10) << 12)
        | ((minutes % 10) << 16)
        | ((minutes // 10) << 20)
        | ((hours % 10) << 24)
        | ((hours // 10) << 28)
    )
    return value, 0


def main() -> None:
    args = parse_args()
    if args.input.resolve() == args.output.resolve():
        raise RuntimeError("Master output must not overwrite its source")
    source = oiio.ImageInput.open(str(args.input))
    if source is None:
        raise RuntimeError(oiio.geterror() or f"Cannot open {args.input}")

    specs = []
    index = 0
    while source.seek_subimage(index, 0):
        spec = oiio.ImageSpec(source.spec())
        spec.attribute("chromaticities", oiio.TypeDesc("float[8]"), ACESCG_CHROMATICITIES)
        spec.attribute("framesPerSecond", oiio.TypeDesc("rational"), (args.fps, 1))
        spec.attribute("timeCode", oiio.TypeDesc("timecode"), packed_timecode(args.frame, args.frame_start, args.fps))
        spec.attribute("owner", args.owner)
        spec.attribute("comments", args.comments)
        spec.attribute("bfs:masteringTool", "BlenderFilmStudio master_exr.py v0.1.0")
        specs.append(spec)
        index += 1
    if not specs:
        raise RuntimeError("Source EXR contains no readable subimages")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = oiio.ImageOutput.create(str(args.output))
    if output is None:
        raise RuntimeError(oiio.geterror() or "Cannot create OpenEXR output")
    if not output.open(str(args.output), specs):
        raise RuntimeError(output.geterror() or "Cannot open multipart OpenEXR output")

    for part, spec in enumerate(specs):
        if not source.seek_subimage(part, 0):
            raise RuntimeError(source.geterror() or f"Cannot seek to source subimage {part}")
        if part > 0 and not output.open(str(args.output), spec, "AppendSubimage"):
            raise RuntimeError(output.geterror() or f"Cannot append output subimage {part}")
        if not output.copy_image(source):
            raise RuntimeError(output.geterror() or f"Cannot copy source subimage {part}")
    if not output.close():
        raise RuntimeError(output.geterror() or "Cannot close mastered OpenEXR")
    source.close()

    report = {
        "documentType": "BFS_EXR_MASTERING",
        "masteringVersion": "0.1.0",
        "input": {"path": str(args.input), "sha256": sha256_file(args.input)},
        "output": {"path": str(args.output), "sha256": sha256_file(args.output), "bytes": args.output.stat().st_size},
        "frame": args.frame,
        "frameRate": [args.fps, 1],
        "timeCodePacked": list(packed_timecode(args.frame, args.frame_start, args.fps)),
        "chromaticities": list(ACESCG_CHROMATICITIES),
        "owner": args.owner,
        "comments": args.comments,
        "parts": len(specs),
    }
    args.output.with_suffix(".master.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"BFS_MASTER_EXR_OK {args.frame} {report['output']['sha256']} {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_MASTER_EXR_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
