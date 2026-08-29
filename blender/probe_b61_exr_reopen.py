import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import bpy


def canonical_json(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contained_file(root, spelling):
    path = (root / spelling).resolve(strict=True)
    if path == root or root not in path.parents or not path.is_file():
        raise RuntimeError(f"Input escapes repository or is not a file: {spelling}")
    return path


def find_combined_quartets(inventory):
    quartets = []
    for item in inventory:
        names = item["channelNames"]
        positions = {name: index for index, name in enumerate(names)}
        for name in names:
            if not name.endswith(".R"):
                continue
            prefix = name[:-2]
            if prefix.split(".")[-1] != "Combined":
                continue
            wanted = [f"{prefix}.{component}" for component in "RGBA"]
            if all(channel in positions for channel in wanted):
                quartets.append({
                    "subimage": item["subimage"],
                    "prefix": prefix,
                    "channelNames": wanted,
                    "channelIndices": [positions[channel] for channel in wanted],
                })
    return quartets


def inventory_input(oiio, exr_path):
    image_input = oiio.ImageInput.open(str(exr_path))
    if image_input is None:
        raise RuntimeError(f"OpenImageIO could not open retained EXR: {oiio.geterror()}")
    inventory = []
    try:
        subimage = 0
        while image_input.seek_subimage(subimage, 0):
            spec = image_input.spec()
            inventory.append({
                "subimage": subimage,
                "width": spec.width,
                "height": spec.height,
                "depth": spec.depth,
                "channels": spec.nchannels,
                "channelNames": list(spec.channelnames),
                "format": str(spec.format),
                "deep": bool(spec.deep),
            })
            subimage += 1
    finally:
        image_input.close()
    return inventory


def decode_projection(oiio, numpy, exr_path, quartet, inventory):
    item = inventory[quartet["subimage"]]
    image_input = oiio.ImageInput.open(str(exr_path))
    if image_input is None:
        raise RuntimeError("OpenImageIO repeat open failed")
    try:
        pixels = image_input.read_image(
            quartet["subimage"], 0, 0, item["channels"], oiio.FLOAT
        )
        if pixels is None:
            raise RuntimeError(f"OpenImageIO read_image failed: {image_input.geterror()}")
        array = numpy.asarray(pixels)
        expected_shape = (item["height"], item["width"], item["channels"])
        if tuple(array.shape) != expected_shape:
            raise RuntimeError(f"Unexpected decoded shape {array.shape}, expected {expected_shape}")
        rgba = numpy.ascontiguousarray(array[..., quartet["channelIndices"]], dtype=numpy.dtype("<f4"))
        finite = numpy.isfinite(rgba)
        channel_axes = (0, 1)
        return {
            "width": item["width"],
            "height": item["height"],
            "channels": 4,
            "valueCount": int(rgba.size),
            "byteCount": int(rgba.nbytes),
            "byteOrder": "float32-little-endian",
            "sha256": sha256_bytes(rgba.tobytes(order="C")),
            "finiteValueCount": int(finite.sum()),
            "allValuesFinite": bool(finite.all()),
            "minimums": [float(value) for value in rgba.min(axis=channel_axes)],
            "maximums": [float(value) for value in rgba.max(axis=channel_axes)],
            "means": [float(value) for value in rgba.mean(axis=channel_axes, dtype=numpy.float64)],
        }
    finally:
        image_input.close()


def write_hashed_result(path, body):
    record = dict(body)
    record["resultHash"] = sha256_bytes(canonical_json(body).encode("utf-8"))
    encoded = (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve(strict=True)
    spec_path = contained_file(repository_root, args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    exr = contained_file(repository_root, spec["failedRun"]["retainedExr"]["uri"])
    if sha256_file(exr) != spec["failedRun"]["retainedExr"]["sha256"]:
        raise RuntimeError("Retained EXR SHA-256 mismatch")

    output = (repository_root / args.output).resolve()
    if repository_root not in output.parents or output.exists() or not output.parent.is_dir():
        raise RuntimeError("Diagnostic output must be a fresh repository-contained file")

    bpy_image = bpy.data.images.load(str(exr), check_existing=False)
    try:
        bpy_probe = {
            "name": bpy_image.name,
            "source": bpy_image.source,
            "type": bpy_image.type,
            "size": list(bpy_image.size),
            "channels": bpy_image.channels,
            "depth": bpy_image.depth,
            "pixelValueCount": len(bpy_image.pixels),
            "rnaProperties": sorted(prop.identifier for prop in bpy.types.Image.bl_rna.properties),
        }
    finally:
        bpy.data.images.remove(bpy_image)

    import numpy
    import OpenImageIO as oiio

    inventory = inventory_input(oiio, exr)
    quartets = find_combined_quartets(inventory)
    if len(quartets) != 1:
        raise RuntimeError(f"Expected one Combined RGBA quartet, found {len(quartets)}")
    first = decode_projection(oiio, numpy, exr, quartets[0], inventory)
    second = decode_projection(oiio, numpy, exr, quartets[0], inventory)
    repeat_exact = first == second
    success = (
        bpy_probe["pixelValueCount"] == 0
        and len(quartets) == 1
        and first["width"] == 1920
        and first["height"] == 1080
        and first["channels"] == 4
        and first["valueCount"] == 8294400
        and first["allValuesFinite"]
        and repeat_exact
    )
    body = {
        "schemaVersion": "bfs.b61ExrReopenDiagnosticResult.v0.1",
        "status": "PASS" if success else "FAIL",
        "input": {
            "uri": spec["failedRun"]["retainedExr"]["uri"],
            "bytes": exr.stat().st_size,
            "sha256": sha256_file(exr),
        },
        "runtime": {
            "blenderVersion": bpy.app.version_string,
            "blenderBuildHash": bpy.app.build_hash.decode("utf-8"),
            "openImageIoVersion": oiio.VERSION_STRING,
            "numpyVersion": numpy.__version__,
        },
        "bpyImageProbe": bpy_probe,
        "openImageIoInventory": inventory,
        "combinedRgba": quartets[0],
        "firstProjection": first,
        "secondProjection": second,
        "repeatDigestExact": repeat_exact,
        "operations": {
            "blenderProcesses": 1,
            "renderCalls": 0,
            "modelCalls": 0,
            "networkCalls": 0,
            "dockerProcesses": 0,
        },
        "verdict": "BLENDER_BUNDLED_OPENIMAGEIO_COMBINED_RGBA_DECODER_SUPPORTED" if success else None,
    }
    record = write_hashed_result(output, body)
    if record["status"] != "PASS":
        raise RuntimeError("D1 success criteria failed")
    print(f"BFS_B61_D1 PASS {record['firstProjection']['sha256']} {record['resultHash']}")


if __name__ == "__main__":
    main()
