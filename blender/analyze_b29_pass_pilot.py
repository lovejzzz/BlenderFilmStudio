"""Exploratory numeric localization for the B29 pass-domain pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def read_subimages(path: Path) -> dict[str, np.ndarray]:
    source = oiio.ImageInput.open(str(path))
    if source is None:
        raise RuntimeError(f"Cannot open {path}: {oiio.geterror()}")
    result = {}
    index = 0
    try:
        while True:
            spec = source.spec()
            pixels = source.read_image(oiio.FLOAT)
            if pixels is None:
                raise RuntimeError(f"Cannot read {path} subimage {index}: {source.geterror()}")
            result[spec.get_string_attribute("name", f"subimage-{index}")] = pixels
            index += 1
            if not source.seek_subimage(index, 0):
                break
    finally:
        source.close()
    return result


def cryptomatte_manifest(path: Path) -> dict[str, str]:
    source = oiio.ImageInput.open(str(path))
    if source is None:
        raise RuntimeError(f"Cannot open {path}: {oiio.geterror()}")
    try:
        for attribute in source.spec().extra_attribs:
            if attribute.name.endswith("/manifest") and "cryptomatte" in attribute.name:
                return json.loads(str(attribute.value))
    finally:
        source.close()
    raise RuntimeError("Cryptomatte manifest missing")


def crypto_id_hex(value: float) -> str:
    return f"{struct.unpack('<I', struct.pack('<f', float(value)))[0]:08x}"


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    delta = b.astype(np.float64) - a.astype(np.float64)
    mask = np.any(delta != 0.0, axis=2)
    ys, xs = np.where(mask)
    changed_values = delta[delta != 0.0]
    retain_details = int(mask.sum()) <= 1024
    return {
        "decodedFloatExact": not bool(mask.any()),
        "changedPixels": int(mask.sum()),
        "changedValues": int(np.count_nonzero(delta)),
        "maxAbsoluteError": float(np.max(np.abs(delta))) if mask.any() else 0.0,
        "rmsError": float(np.sqrt(np.mean(np.square(delta)))),
        "boundingBox": None if not mask.any() else {"xMin": int(xs.min()), "xMax": int(xs.max()), "yMin": int(ys.min()), "yMax": int(ys.max())},
        "changedValueRange": None if changed_values.size == 0 else {"minimum": float(changed_values.min()), "maximum": float(changed_values.max())},
        "detailsRetained": retain_details,
        "deltaValueFrequencies": None if not retain_details else [{"delta": float(value), "count": int(count)} for value, count in sorted(Counter(changed_values).items())],
        "changedPixelCoordinates": None if not retain_details else [[int(x), int(y)] for y, x in zip(ys, xs)],
        "deltaFloat64Sha256": hashlib.sha256(delta.tobytes(order="C")).hexdigest(),
    }


def main() -> None:
    args = parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if report["status"] != "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION":
        raise RuntimeError("Pilot status mismatch")
    images = {item["callOrdinal"]: read_subimages(args.work_dir / item["exr"]["name"]) for item in report["outputs"]}
    reference_call = 11
    reference = images[reference_call]
    comparisons = []
    for ordinal in range(1, 13):
        for name in sorted(reference):
            comparisons.append({"callOrdinal": ordinal, "referenceCallOrdinal": reference_call, "pass": name, **compare(reference[name], images[ordinal][name])})
    summary = []
    for name in sorted(reference):
        items = [item for item in comparisons if item["pass"] == name]
        summary.append({
            "pass": name,
            "nonExactCalls": [item["callOrdinal"] for item in items if not item["decodedFloatExact"]],
            "maximumChangedPixels": max(item["changedPixels"] for item in items),
            "maximumAbsoluteError": max(item["maxAbsoluteError"] for item in items),
        })
    manifest = cryptomatte_manifest(args.work_dir / report["outputs"][reference_call - 1]["exr"]["name"])
    names_by_id = {value: name for name, value in manifest.items()}
    crypto_reference = reference["BFS_MASTER.CryptoObject00"]
    crypto_alternate = images[12]["BFS_MASTER.CryptoObject00"]
    crypto_mask = np.any(crypto_reference != crypto_alternate, axis=2)
    crypto_ys, crypto_xs = np.where(crypto_mask)
    crypto_localization = []
    for y, x in zip(crypto_ys, crypto_xs):
        def slots(pixel: np.ndarray) -> list[dict]:
            result = []
            for offset in (0, 2):
                digest = crypto_id_hex(pixel[offset])
                result.append({"idHex": digest, "object": names_by_id.get(digest, "UNKNOWN"), "coverage": float(pixel[offset + 1])})
            return result
        crypto_localization.append({"x": int(x), "y": int(y), "reference": slots(crypto_reference[y, x]), "alternate": slots(crypto_alternate[y, x])})
    result = {
        "documentType": "BFS_B29_PASS_DOMAIN_EXPLORATORY_ANALYSIS",
        "version": "0.1.0",
        "status": "EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION",
        "pilotReportSha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
        "referenceCallOrdinal": reference_call,
        "summary": summary,
        "cryptomatteManifest": manifest,
        "cryptoObject00Localization": crypto_localization,
        "comparisons": comparisons,
        "nonClaim": "This one-process pilot selects a confirmatory B29 design; it does not estimate a population effect or promote a pass-domain mechanism.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BFS_B29_PASS_PILOT_ANALYZE_OK " + " ".join(f"{item['pass']}={item['nonExactCalls']}" for item in summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B29_PASS_PILOT_ANALYZE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
