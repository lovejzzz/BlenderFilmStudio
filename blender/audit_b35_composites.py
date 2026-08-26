"""Independently recompute every B35 scene-linear composite from bound source EXRs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-spec", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--composite-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixels(path: Path) -> np.ndarray:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot read {path}")
    return np.asarray(image.get_pixels(oiio.FLOAT), dtype=np.float32)


def main() -> None:
    args = parse_args()
    spec = json.loads(args.study_spec.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if spec["documentType"] != "BFS_HUMAN_QUADRATURE_REVIEW_SPEC" or manifest["studySpecSha256"] != sha256_file(args.study_spec):
        raise RuntimeError("B35 audit binding mismatch")
    observations = []
    for method, record in manifest["methods"].items():
        for output in record["outputs"]:
            frame = output["frame"]
            source_arrays = [pixels(args.source_root / source["cell"] / f"frame-{frame:04d}.exr") for source in output["sources"]]
            weights = np.asarray([source["weight"] for source in output["sources"]], dtype=np.float64)
            recomputed = np.sum(np.stack(source_arrays, axis=0).astype(np.float64) * weights[:, None, None, None], axis=0).astype(np.float32)
            observed = pixels(args.composite_root / method / output["compositeName"])
            absolute = np.abs(observed - recomputed)
            maximum = float(absolute.max())
            changed_values = int(np.count_nonzero(absolute))
            if maximum != 0.0 or changed_values != 0:
                raise RuntimeError(f"Composite mismatch {method} frame {frame}: max={maximum} changed={changed_values}")
            observations.append({"method": method, "frame": frame, "maximumAbsoluteFloatError": maximum, "changedFloatValues": changed_values})
    report = {
        "documentType": "BFS_B35_INDEPENDENT_COMPOSITE_AUDIT", "version": spec["version"],
        "status": "COMPOSITE_FLOAT_EXACT", "studySpecSha256": sha256_file(args.study_spec),
        "compositeDisplayManifestSha256": sha256_file(args.manifest), "openImageIO": oiio.VERSION_STRING,
        "numpy": np.__version__, "frameCount": len(observations),
        "maximumAbsoluteFloatError": max(item["maximumAbsoluteFloatError"] for item in observations),
        "totalChangedFloatValues": sum(item["changedFloatValues"] for item in observations), "frames": observations,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B35_INDEPENDENT_COMPOSITE_AUDIT exact={report['frameCount']} max={report['maximumAbsoluteFloatError']} changed={report['totalChangedFloatValues']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B35_INDEPENDENT_COMPOSITE_AUDIT_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
