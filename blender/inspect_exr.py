"""Inspect and optionally compare Blender multi-layer EXR files with OIIO."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--pixel-spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    try:
        return [json_value(item) for item in value]  # type: ignore[arg-type]
    except TypeError:
        return str(value)


def attributes_from_spec(spec) -> dict[str, object]:
    result = {}
    for attribute in spec.extra_attribs:
        name = str(attribute.name)
        try:
            value = attribute.value
        except Exception:
            value = spec.getattribute(name)
        result[name] = json_value(value)
    return dict(sorted(result.items()))


def inspect_subimages(path: Path) -> list[dict]:
    first = oiio.ImageBuf(str(path), 0, 0)
    if not first.initialized and first.has_error:
        raise RuntimeError(first.geterror())
    count = first.nsubimages
    if count <= 0:
        count = 1
        while oiio.ImageBuf(str(path), count, 0).initialized:
            count += 1

    result = []
    for index in range(count):
        image = oiio.ImageBuf(str(path), index, 0)
        if not image.initialized:
            raise RuntimeError(image.geterror() or f"Cannot initialize subimage {index}")
        spec = image.spec()
        stats = oiio.ImageBufAlgo.computePixelStats(image)
        channels = list(spec.channelnames)
        result.append({
            "index": index,
            "name": str(spec.getattribute("oiio:subimagename") or spec.getattribute("name") or f"subimage-{index}"),
            "width": spec.width,
            "height": spec.height,
            "depth": spec.depth,
            "channels": channels,
            "channelFormats": [str(item) for item in spec.channelformats] if spec.channelformats else [str(spec.format)] * spec.nchannels,
            "attributes": attributes_from_spec(spec),
            "statistics": {
                "min": [float(value) for value in stats.min],
                "max": [float(value) for value in stats.max],
                "average": [float(value) for value in stats.avg],
                "standardDeviation": [float(value) for value in stats.stddev],
                "nanCount": [int(value) for value in stats.nancount],
                "infinityCount": [int(value) for value in stats.infcount],
                "finiteCount": [int(value) for value in stats.finitecount],
            },
        })
    return result


def normalized_tokens(subimages: list[dict]) -> set[str]:
    tokens = set()
    for subimage in subimages:
        tokens.add(subimage["name"].lower())
        for channel in subimage["channels"]:
            lower = channel.lower()
            tokens.add(lower)
            tokens.update(part for part in lower.replace("/", ".").split(".") if part)
    return tokens


def pass_status(subimages: list[dict], required: list[str]) -> dict[str, bool]:
    tokens = normalized_tokens(subimages)
    aliases = {
        "alpha": {"alpha", "a"},
        "depth": {"depth", "z"},
        "cryptomatte": {"cryptomatte", "cryptoobject", "cryptoasset", "cryptomaterial"},
    }
    status = {}
    for item in required:
        expected = aliases.get(item.lower(), {item.lower()})
        status[item] = any(any(token == alias or alias in token for alias in expected) for token in tokens)
    return status


def attribute_status(subimages: list[dict], required: list[str]) -> dict[str, bool]:
    names = {name.lower() for subimage in subimages for name in subimage["attributes"]}
    aliases = {
        "framespersecond": {"framespersecond"},
        "timecode": {"timecode", "smpte:timecode"},
        "owner": {"owner", "copyright", "artist"},
        "comments": {"comments", "imagedescription"},
    }
    return {item: bool(aliases.get(item.lower(), {item.lower()}) & names) for item in required}


def compare_subimages(left: Path, right: Path, left_info: list[dict], right_info: list[dict]) -> dict:
    compatible = len(left_info) == len(right_info)
    comparisons = []
    for index in range(min(len(left_info), len(right_info))):
        a_info = left_info[index]
        b_info = right_info[index]
        layout_equal = (
            a_info["width"] == b_info["width"]
            and a_info["height"] == b_info["height"]
            and a_info["channels"] == b_info["channels"]
        )
        compatible = compatible and layout_equal
        if layout_equal:
            a = oiio.ImageBuf(str(left), index, 0)
            b = oiio.ImageBuf(str(right), index, 0)
            comparison = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
            record = {
                "index": index,
                "layoutEqual": True,
                "meanError": float(comparison.meanerror),
                "rmsError": float(comparison.rms_error),
                "maxAbsoluteError": float(comparison.maxerror),
                "warningCount": int(comparison.nwarn),
                "failureCount": int(comparison.nfail),
                "largestDifference": {
                    "x": int(comparison.maxx), "y": int(comparison.maxy),
                    "z": int(comparison.maxz), "channel": int(comparison.maxc),
                },
            }
        else:
            record = {"index": index, "layoutEqual": False}
        comparisons.append(record)
    exact = compatible and all(
        item.get("failureCount") == 0 and item.get("maxAbsoluteError") == 0.0
        for item in comparisons
    )
    return {"layoutCompatible": compatible, "subimages": comparisons, "pixelExact": exact}


def main() -> None:
    args = parse_args()
    spec = json.loads(args.pixel_spec.read_text(encoding="utf-8"))
    image_spec = spec["image"]
    left_info = inspect_subimages(args.input)
    passes = pass_status(left_info, image_spec["requiredPasses"])
    attributes = attribute_status(left_info, image_spec["requiredAttributes"])
    finite = all(
        sum(subimage["statistics"]["nanCount"]) == 0
        and sum(subimage["statistics"]["infinityCount"]) == 0
        for subimage in left_info
    )
    resolution = all(
        subimage["width"] == image_spec["width"] and subimage["height"] == image_spec["height"]
        for subimage in left_info
    )
    report = {
        "documentType": "BFS_EXR_INSPECTION",
        "inspectionVersion": "0.1.0",
        "openImageIOVersion": oiio.VERSION_STRING,
        "input": {"path": str(args.input), "sha256": sha256_file(args.input), "subimages": left_info},
        "conformance": {
            "resolutionExact": resolution,
            "finiteValues": finite,
            "requiredPasses": passes,
            "allRequiredPassesPresent": all(passes.values()),
            "requiredAttributes": attributes,
            "allRequiredAttributesPresent": all(attributes.values()),
        },
    }
    if args.compare:
        right_info = inspect_subimages(args.compare)
        report["comparisonInput"] = {"path": str(args.compare), "sha256": sha256_file(args.compare)}
        report["comparison"] = compare_subimages(args.input, args.compare, left_info, right_info)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_EXR_INSPECTION_OK {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_EXR_INSPECTION_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
