"""Classify formal B29 PNG/EXR pass tuples against frozen pilot hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_rgb_hash(path: Path) -> tuple[str, dict[str, Any]]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    layout = {"width": spec.width, "height": spec.height, "channels": list(spec.channelnames), "pixelFormat": str(spec.format)}
    if layout != {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "uint8"}:
        raise RuntimeError(f"PNG layout mismatch: {path}: {layout}")
    pixels = image.get_pixels(oiio.UINT8)[:, :, :3]
    return hashlib.sha256(pixels.tobytes(order="C")).hexdigest(), layout


def exr_passes(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    source = oiio.ImageInput.open(str(path))
    if source is None:
        raise RuntimeError(f"Cannot open {path}: {oiio.geterror()}")
    passes = {}
    manifest = {}
    index = 0
    try:
        while True:
            spec = source.spec()
            pixels = source.read_image(oiio.FLOAT)
            if pixels is None:
                raise RuntimeError(f"Cannot read {path} subimage {index}: {source.geterror()}")
            name = spec.get_string_attribute("name", "")
            passes[name] = {"decodedFloatSha256": hashlib.sha256(pixels.tobytes(order="C")).hexdigest(), "layout": {"width": spec.width, "height": spec.height, "channels": list(spec.channelnames), "pixelFormat": str(spec.format)}, "pixels": pixels}
            for attribute in spec.extra_attribs:
                if attribute.name.endswith("/manifest") and "cryptomatte" in attribute.name:
                    manifest = json.loads(str(attribute.value))
            index += 1
            if not source.seek_subimage(index, 0):
                break
    finally:
        source.close()
    return passes, manifest


def numeric_compare(reference: np.ndarray, alternate: np.ndarray) -> dict[str, Any]:
    delta = alternate.astype(np.float64) - reference.astype(np.float64)
    mask = np.any(delta != 0.0, axis=2)
    ys, xs = np.where(mask)
    return {"changedPixels": int(mask.sum()), "changedValues": int(np.count_nonzero(delta)), "maxAbsoluteError": float(np.max(np.abs(delta))) if mask.any() else 0.0, "rmsError": float(np.sqrt(np.mean(np.square(delta)))), "boundingBox": None if not mask.any() else {"xMin": int(xs.min()), "xMax": int(xs.max()), "yMin": int(ys.min()), "yMax": int(ys.max())}}


def id_hex(value: float) -> str:
    return f"{struct.unpack('<I', struct.pack('<f', float(value)))[0]:08x}"


def main() -> None:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    index = json.loads(args.index.read_text(encoding="utf-8"))
    if spec["documentType"] != "BFS_PASS_DOMAIN_LOCALIZATION_SPEC" or index["documentType"] != "BFS_B29_CLASSIFICATION_INDEX":
        raise RuntimeError("B29 document type mismatch")
    if index["b29SpecSha256"] != sha256_file(args.spec):
        raise RuntimeError("Index/spec binding mismatch")
    if [item["replicate"] for item in index["processes"]] != spec["design"]["processOrder"]:
        raise RuntimeError("Process order mismatch")
    known = spec["knownHashes"]
    png_labels = {value: label for label, value in known["pngDecodedRgb"].items()}
    combined_labels = {value: label for label, value in known["BFS_MASTER.Combined"].items()}
    crypto_labels = {value: label for label, value in known["BFS_MASTER.CryptoObject00"].items()}
    stable = known["stableClosestSamplePasses"]
    expected_channels = {
        "BFS_MASTER.Combined": ["BFS_MASTER.Combined.R", "BFS_MASTER.Combined.G", "BFS_MASTER.Combined.B", "BFS_MASTER.Combined.A"],
        "BFS_MASTER.Depth": ["BFS_MASTER.Depth.Z"],
        "BFS_MASTER.Normal": ["BFS_MASTER.Normal.X", "BFS_MASTER.Normal.Y", "BFS_MASTER.Normal.Z"],
        "BFS_MASTER.Position": ["BFS_MASTER.Position.X", "BFS_MASTER.Position.Y", "BFS_MASTER.Position.Z"],
        "BFS_MASTER.Vector": ["BFS_MASTER.Vector.X", "BFS_MASTER.Vector.Y", "BFS_MASTER.Vector.Z", "BFS_MASTER.Vector.W"],
        "BFS_MASTER.CryptoObject00": ["BFS_MASTER.CryptoObject00.r", "BFS_MASTER.CryptoObject00.g", "BFS_MASTER.CryptoObject00.b", "BFS_MASTER.CryptoObject00.a"],
        "BFS_MASTER.CryptoObject01": ["BFS_MASTER.CryptoObject01.r", "BFS_MASTER.CryptoObject01.g", "BFS_MASTER.CryptoObject01.b", "BFS_MASTER.CryptoObject01.a"],
        "BFS_MASTER.CryptoObject02": ["BFS_MASTER.CryptoObject02.r", "BFS_MASTER.CryptoObject02.g", "BFS_MASTER.CryptoObject02.b", "BFS_MASTER.CryptoObject02.a"],
    }
    representatives: dict[str, dict[str, np.ndarray]] = {}
    processes = []
    category_counts: Counter[str] = Counter()
    ordinal_counts: defaultdict[int, Counter[str]] = defaultdict(Counter)
    novel_hashes = []
    manifests = []
    for process in index["processes"]:
        if len(process["renders"]) != 12:
            raise RuntimeError(f"{process['replicate']} render count mismatch")
        calls = []
        for ordinal, item in enumerate(process["renders"], start=1):
            if item["callOrdinal"] != ordinal:
                raise RuntimeError("Call order mismatch")
            png_path, exr_path = Path.cwd() / item["pngUri"], Path.cwd() / item["exrUri"]
            if sha256_file(png_path) != item["pngContainerSha256"] or sha256_file(exr_path) != item["exrContainerSha256"]:
                raise RuntimeError("Container hash mismatch")
            png_hash, png_layout = png_rgb_hash(png_path)
            passes, manifest = exr_passes(exr_path)
            manifests.append(manifest)
            if set(passes) != set(expected_channels):
                raise RuntimeError(f"EXR pass set mismatch: {sorted(passes)}")
            for name, channels in expected_channels.items():
                layout = passes[name]["layout"]
                if layout["width"] != 960 or layout["height"] != 540 or layout["channels"] != channels or layout["pixelFormat"] != "float":
                    raise RuntimeError(f"EXR layout mismatch: {name}: {layout}")
            pass_hashes = {name: value["decodedFloatSha256"] for name, value in passes.items()}
            png_label = png_labels.get(png_hash)
            combined_label = combined_labels.get(pass_hashes["BFS_MASTER.Combined"])
            crypto_label = crypto_labels.get(pass_hashes["BFS_MASTER.CryptoObject00"])
            data_stable = all(pass_hashes[name] == digest for name, digest in stable.items())
            if png_label is None or combined_label is None or crypto_label is None:
                category = "PASS_SPACE_EXPANDED"
                for domain, digest, label_map in (("pngDecodedRgb", png_hash, png_labels), ("BFS_MASTER.Combined", pass_hashes["BFS_MASTER.Combined"], combined_labels), ("BFS_MASTER.CryptoObject00", pass_hashes["BFS_MASTER.CryptoObject00"], crypto_labels)):
                    if digest not in label_map:
                        novel_hashes.append({"replicate": process["replicate"], "callOrdinal": ordinal, "domain": domain, "sha256": digest})
            elif not data_stable:
                category = "CLOSEST_SAMPLE_PASS_VARIATION"
            elif png_label == combined_label == crypto_label == "REFERENCE":
                category = "COUPLED_REFERENCE"
            elif png_label == combined_label == crypto_label == "ALTERNATE":
                category = "COUPLED_ALTERNATE"
            else:
                category = "DECOUPLED_PASS_PATTERN"
            if png_label in ("REFERENCE", "ALTERNATE") and png_label not in representatives:
                representatives[png_label] = {name: passes[name]["pixels"].copy() for name in ("BFS_MASTER.Combined", "BFS_MASTER.CryptoObject00")}
            category_counts[category] += 1
            ordinal_counts[ordinal][category] += 1
            calls.append({"callOrdinal": ordinal, "category": category, "pngDecodedRgbSha256": png_hash, "pngMode": png_label or "NOVEL", "passHashes": pass_hashes, "pngLayout": png_layout, "manifestHash": process["manifestHash"], "pngContainerSha256": item["pngContainerSha256"], "exrContainerSha256": item["exrContainerSha256"]})
        categories = {item["category"] for item in calls}
        processes.append({"replicate": process["replicate"], "processId": process["processId"], "manifestHash": process["manifestHash"], "supportingProcess": "COUPLED_REFERENCE" in categories and "COUPLED_ALTERNATE" in categories, "categoryCounts": dict(sorted(Counter(item["category"] for item in calls).items())), "calls": calls})
    if len(processes) != 12 or sum(len(item["calls"]) for item in processes) != 144:
        raise RuntimeError("Fixed sample count mismatch")
    manifest = manifests[0]
    if any(item != manifest for item in manifests):
        raise RuntimeError("Cryptomatte manifest changed across renders")
    numeric = None
    crypto_localization = []
    if set(representatives) == {"REFERENCE", "ALTERNATE"}:
        numeric = {name: numeric_compare(representatives["REFERENCE"][name], representatives["ALTERNATE"][name]) for name in representatives["REFERENCE"]}
        ref = representatives["REFERENCE"]["BFS_MASTER.CryptoObject00"]
        alt = representatives["ALTERNATE"]["BFS_MASTER.CryptoObject00"]
        names = {value: key for key, value in manifest.items()}
        ys, xs = np.where(np.any(ref != alt, axis=2))
        for y, x in zip(ys, xs):
            def slots(pixel: np.ndarray) -> list[dict[str, Any]]:
                return [{"idHex": (digest := id_hex(pixel[offset])), "object": names.get(digest, "UNKNOWN"), "coverage": float(pixel[offset + 1])} for offset in (0, 2)]
            crypto_localization.append({"x": int(x), "y": int(y), "reference": slots(ref[y, x]), "alternate": slots(alt[y, x])})
    supporting = [item["replicate"] for item in processes if item["supportingProcess"]]
    secondary = known["secondaryPasses"]
    vector_pattern = []
    crypto_secondary_stable = []
    for process in processes:
        calls = process["calls"]
        vector_ok = calls[0]["passHashes"]["BFS_MASTER.Vector"] == secondary["BFS_MASTER.Vector_CALL_1"] and all(item["passHashes"]["BFS_MASTER.Vector"] == secondary["BFS_MASTER.Vector_CALL_2_TO_12"] for item in calls[1:])
        crypto_ok = all(item["passHashes"]["BFS_MASTER.CryptoObject01"] == secondary["BFS_MASTER.CryptoObject01"] and item["passHashes"]["BFS_MASTER.CryptoObject02"] == secondary["BFS_MASTER.CryptoObject02"] for item in calls)
        vector_pattern.append({"replicate": process["replicate"], "frozenPatternMatch": vector_ok})
        crypto_secondary_stable.append({"replicate": process["replicate"], "frozenPatternMatch": crypto_ok})
    result = {"documentType": "BFS_B29_PASS_DOMAIN_CLASSIFICATION", "version": "0.1.0", "b29SpecSha256": sha256_file(args.spec), "indexSha256": sha256_file(args.index), "decoder": f"OpenImageIO {oiio.VERSION_STRING}", "primary": {"endpoint": spec["primaryEndpoint"]["name"], "supportThresholdProcesses": spec["primaryEndpoint"]["supportThresholdProcesses"], "supportingProcessCount": len(supporting), "supportingProcesses": supporting}, "summary": {"processes": 12, "renders": 144, "categoryCounts": dict(sorted(category_counts.items())), "novelPrimaryHashes": novel_hashes}, "ordinalCategoryCounts": [{"callOrdinal": ordinal, "counts": dict(sorted(ordinal_counts[ordinal].items()))} for ordinal in range(1, 13)], "numericReferenceToAlternate": numeric, "cryptoObject00Localization": crypto_localization, "cryptomatteManifest": manifest, "secondary": {"vectorFirstCallPattern": vector_pattern, "cryptoObject01And02Stable": crypto_secondary_stable}, "processes": processes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B29_CLASSIFY_OK supporting={len(supporting)} categories={dict(category_counts)} novel={len(novel_hashes)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B29_CLASSIFY_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
