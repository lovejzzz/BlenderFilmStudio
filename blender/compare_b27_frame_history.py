"""Compare B27 frame-38 targets with a fixed B25 reference and with each other."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
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


def decoded_rgb_sha256(image: oiio.ImageBuf) -> str:
    pixels = image.get_pixels(oiio.UINT8)[:, :, :3]
    return hashlib.sha256(pixels.tobytes(order="C")).hexdigest()


def load_image(path: Path, expected_layout: list[Any]) -> tuple[oiio.ImageBuf, list[Any]]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    spec = image.spec()
    layout = [spec.width, spec.height, list(spec.channelnames), str(spec.format)]
    if layout != expected_layout:
        raise RuntimeError(f"Layout mismatch for {path}: {layout!r} != {expected_layout!r}")
    return image, layout


def metrics(a: oiio.ImageBuf, b: oiio.ImageBuf, envelope: dict[str, Any]) -> dict[str, Any]:
    numeric = oiio.ImageBufAlgo.compare(a, b, 0.0, 0.0)
    checks = {
        "maximumAbsoluteError": float(numeric.maxerror) <= float(envelope["maximumAbsoluteErrorAtMost"]),
        "rmsError": float(numeric.rms_error) <= float(envelope["rmsErrorAtMost"]),
        "zeroThresholdFailurePixels": int(numeric.nfail) <= int(envelope["zeroThresholdFailurePixelsAtMost"]),
    }
    return {
        "decodedPixelExact": float(numeric.maxerror) == 0.0 and int(numeric.nfail) == 0,
        "maxAbsoluteError": float(numeric.maxerror),
        "rmsError": float(numeric.rms_error),
        "failurePixels": int(numeric.nfail),
        "staticEnvelopeChecks": checks,
        "staticEnvelopePass": all(checks.values()),
    }


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    row_h = a + b
    row_d = c + d
    failures = a + c
    total = row_h + row_d
    denominator = math.comb(total, failures)

    def probability(h_failures: int) -> float:
        return math.comb(row_h, h_failures) * math.comb(row_d, failures - h_failures) / denominator

    observed = probability(a)
    lower = max(0, failures - row_d)
    upper = min(row_h, failures)
    return min(1.0, sum(probability(value) for value in range(lower, upper + 1) if probability(value) <= observed + 1e-15))


def pair_record(a: dict[str, Any], b: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        "a": a["replicate"],
        "b": b["replicate"],
        "aSha256": a["containerSha256"],
        "bSha256": b["containerSha256"],
        **metrics(a["image"], b["image"], envelope),
    }


def summarize_pairs(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "comparisons": len(items),
        "decodedPixelExact": sum(item["decodedPixelExact"] for item in items),
        "staticEnvelopePass": sum(item["staticEnvelopePass"] for item in items),
        "maximumAbsoluteError": max((item["maxAbsoluteError"] for item in items), default=0.0),
        "maximumRmsError": max((item["rmsError"] for item in items), default=0.0),
        "maximumFailurePixels": max((item["failurePixels"] for item in items), default=0),
    }


def main() -> None:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if index["documentType"] != "BFS_B27_COMPARISON_INDEX":
        raise RuntimeError("Comparison index type mismatch")
    if spec["documentType"] != "BFS_FRAME_HISTORY_ISOLATION_SPEC":
        raise RuntimeError("B27 spec type mismatch")
    if index["b27SpecSha256"] != sha256_file(args.spec):
        raise RuntimeError("Comparison index/spec binding mismatch")

    reference_meta = spec["evidenceBasis"]["reference"]
    reference_path = Path.cwd() / reference_meta["uri"]
    expected_layout = [960, 540, ["R", "G", "B", "A"], "uint8"]
    reference, layout = load_image(reference_path, expected_layout)
    reference_container = sha256_file(reference_path)
    reference_decoded = decoded_rgb_sha256(reference)
    if reference_container != reference_meta["containerSha256"]:
        raise RuntimeError("Reference container SHA mismatch")
    if reference_decoded != reference_meta["decodedRgbSha256"]:
        raise RuntimeError("Reference decoded RGB SHA mismatch")

    envelope = spec["frozenStaticEnvelope"]
    samples = []
    for item in index["samples"]:
        path = Path.cwd() / item["fileUri"]
        if sha256_file(path) != item["containerSha256"]:
            raise RuntimeError(f"Sample container SHA mismatch: {item['replicate']}")
        image, observed_layout = load_image(path, expected_layout)
        sample = {
            **item,
            "layout": observed_layout,
            "decodedRgbSha256": decoded_rgb_sha256(image),
            "image": image,
        }
        sample["referenceComparison"] = metrics(reference, image, envelope)
        samples.append(sample)

    if len(samples) != 24 or sum(item["cell"] == "HISTORY" for item in samples) != 12 or sum(item["cell"] == "DIRECT" for item in samples) != 12:
        raise RuntimeError("B27 sample/cell count mismatch")

    history = [item for item in samples if item["cell"] == "HISTORY"]
    direct = [item for item in samples if item["cell"] == "DIRECT"]
    h_fail = sum(not item["referenceComparison"]["staticEnvelopePass"] for item in history)
    d_fail = sum(not item["referenceComparison"]["staticEnvelopePass"] for item in direct)
    table = {"historyFail": h_fail, "historyPass": 12 - h_fail, "directFail": d_fail, "directPass": 12 - d_fail}
    p_value = fisher_two_sided(table["historyFail"], table["historyPass"], table["directFail"], table["directPass"])

    within_history = [pair_record(history[a], history[b], envelope) for a in range(12) for b in range(a + 1, 12)]
    within_direct = [pair_record(direct[a], direct[b], envelope) for a in range(12) for b in range(a + 1, 12)]
    cross = [pair_record(h, d, envelope) for h in history for d in direct]
    variants = {}
    for cell, members in (("HISTORY", history), ("DIRECT", direct)):
        counts = Counter(item["decodedRgbSha256"] for item in members)
        variants[cell] = {
            "uniqueDecodedRgbVariants": len(counts),
            "frequencies": [{"decodedRgbSha256": digest, "count": count} for digest, count in sorted(counts.items())],
        }

    public_samples = []
    for item in samples:
        public_samples.append({key: value for key, value in item.items() if key != "image"})
    result = {
        "documentType": "BFS_B27_FRAME_HISTORY_COMPARISON",
        "version": "0.1.0",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "numpy": np.__version__,
        "b27SpecSha256": sha256_file(args.spec),
        "indexSha256": sha256_file(args.index),
        "layout": {"width": layout[0], "height": layout[1], "channels": layout[2], "pixelFormat": layout[3]},
        "reference": {
            "uri": reference_meta["uri"],
            "containerSha256": reference_container,
            "decodedRgbSha256": reference_decoded,
        },
        "frozenStaticEnvelope": envelope,
        "primary": {
            "endpoint": spec["primaryEndpoint"]["name"],
            "alpha": spec["primaryEndpoint"]["alpha"],
            "test": spec["primaryEndpoint"]["test"],
            "table": table,
            "twoSidedFisherExactP": p_value,
            "riskDifferenceHistoryMinusDirect": h_fail / 12 - d_fail / 12,
            "significant": p_value <= float(spec["primaryEndpoint"]["alpha"]),
        },
        "referenceComparisonSummary": {
            "HISTORY": {
                "samples": 12,
                "decodedPixelExact": sum(item["referenceComparison"]["decodedPixelExact"] for item in history),
                "staticEnvelopePass": 12 - h_fail,
                "staticEnvelopeFail": h_fail,
            },
            "DIRECT": {
                "samples": 12,
                "decodedPixelExact": sum(item["referenceComparison"]["decodedPixelExact"] for item in direct),
                "staticEnvelopePass": 12 - d_fail,
                "staticEnvelopeFail": d_fail,
            },
        },
        "variants": variants,
        "samples": public_samples,
        "withinCell": {
            "HISTORY": {"summary": summarize_pairs(within_history), "pairs": within_history},
            "DIRECT": {"summary": summarize_pairs(within_direct), "pairs": within_direct},
        },
        "crossCell": {"summary": summarize_pairs(cross), "pairs": cross},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B27_COMPARE_OK history_fail={h_fail}/12 direct_fail={d_fail}/12 p={p_value:.12g}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B27_COMPARE_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
