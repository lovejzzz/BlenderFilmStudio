"""Classify formal B30 NATURAL/CENTER decoded-RGB outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

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


def decode(path: Path, expected_layout: list[Any]) -> tuple[str, list[Any]]:
    image = oiio.ImageBuf(str(path))
    if not image.initialized:
        raise RuntimeError(f"Cannot decode {path}: {image.geterror()}")
    image_spec = image.spec()
    layout = [image_spec.width, image_spec.height, list(image_spec.channelnames), str(image_spec.format)]
    if layout != expected_layout:
        raise RuntimeError(f"Layout mismatch for {path}: {layout!r} != {expected_layout!r}")
    pixels = image.get_pixels(oiio.UINT8)[:, :, :3]
    return hashlib.sha256(pixels.tobytes(order="C")).hexdigest(), layout


def main() -> None:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec["documentType"] != "BFS_FIXED_JITTER_INTERVENTION_SPEC":
        raise RuntimeError("B30 spec type mismatch")
    if index["documentType"] != "BFS_B30_CLASSIFICATION_INDEX":
        raise RuntimeError("B30 index type mismatch")
    if index["b30SpecSha256"] != sha256_file(args.spec):
        raise RuntimeError("B30 index/spec binding mismatch")
    if [item["replicate"] for item in index["processes"]] != spec["design"]["schedule"]:
        raise RuntimeError("B30 process schedule mismatch")

    hashes = spec["frozenDecodedRgbHashes"]
    expected_layout = [960, 540, ["R", "G", "B", "A"], "uint8"]
    processes = []
    cell_mode_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    ordinal_counts: defaultdict[str, defaultdict[int, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    novel_hashes: defaultdict[str, Counter[str]] = defaultdict(Counter)
    transition_counts: Counter[str] = Counter()
    switching_natural = []
    center_exact_pids = []

    for process in index["processes"]:
        replicate, cell = process["replicate"], process["cell"]
        expected_cell = "NATURAL" if replicate.startswith("N") else "CENTER"
        if cell != expected_cell or len(process["renders"]) != 12:
            raise RuntimeError(f"{replicate} cell/render-count mismatch")
        sequence = []
        public_renders = []
        for ordinal, item in enumerate(process["renders"], start=1):
            if item["callOrdinal"] != ordinal:
                raise RuntimeError(f"{replicate} call order mismatch")
            path = Path.cwd() / item["fileUri"]
            container_sha = sha256_file(path)
            if container_sha != item["containerSha256"]:
                raise RuntimeError(f"{replicate}/{ordinal} container mismatch")
            decoded_sha, layout = decode(path, expected_layout)
            if cell == "NATURAL":
                if decoded_sha == hashes["NATURAL_REFERENCE"]:
                    mode = "NATURAL_REFERENCE"
                elif decoded_sha == hashes["NATURAL_ALTERNATE"]:
                    mode = "NATURAL_ALTERNATE"
                else:
                    mode = "NATURAL_NOVEL"
            else:
                mode = "CENTER_EXPECTED" if decoded_sha == hashes["CENTER_DERIVATION"] else "CENTER_NOVEL"
            if mode.endswith("NOVEL"):
                novel_hashes[cell][decoded_sha] += 1
            sequence.append(mode)
            cell_mode_counts[cell][mode] += 1
            ordinal_counts[cell][ordinal][mode] += 1
            public_renders.append({**item, "decodedRgbSha256": decoded_sha, "mode": mode, "layout": layout})
        transitions = []
        for index_ in range(1, len(sequence)):
            if sequence[index_] != sequence[index_ - 1]:
                direction = f"{sequence[index_ - 1]}->{sequence[index_]}"
                transitions.append({"afterCallOrdinal": index_ + 1, "direction": direction})
                transition_counts[f"{cell}:{direction}"] += 1
        modes = set(sequence)
        natural_switch = cell == "NATURAL" and {"NATURAL_REFERENCE", "NATURAL_ALTERNATE"}.issubset(modes)
        center_exact = cell == "CENTER" and modes == {"CENTER_EXPECTED"}
        if natural_switch:
            switching_natural.append(replicate)
        if center_exact:
            center_exact_pids.append(replicate)
        processes.append({
            "replicate": replicate, "cell": cell, "processId": process["processId"],
            "manifestHash": process["manifestHash"], "sequence": sequence,
            "modeCounts": dict(sorted(Counter(sequence).items())),
            "withinPidNaturalSwitch": natural_switch, "centerExact": center_exact,
            "adjacentTransitionCount": len(transitions), "transitions": transitions, "renders": public_renders,
        })

    if len(processes) != 24 or sum(len(item["renders"]) for item in processes) != 288:
        raise RuntimeError("B30 fixed sample count mismatch")
    result = {
        "documentType": "BFS_B30_JITTER_INTERVENTION_CLASSIFICATION", "version": "0.1.0",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}", "b30SpecSha256": sha256_file(args.spec),
        "indexSha256": sha256_file(args.index),
        "layout": {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "uint8"},
        "primary": {
            "endpoint": spec["primaryEndpoint"]["name"],
            "naturalSupportThresholdProcesses": spec["primaryEndpoint"]["naturalSupportThresholdProcesses"],
            "naturalSwitchingProcessCount": len(switching_natural),
            "naturalSwitchingProcesses": switching_natural,
            "centerExactProcessCount": len(center_exact_pids), "centerExactProcesses": center_exact_pids,
        },
        "summary": {
            "processes": 24, "renders": 288, "naturalProcesses": 12, "centerProcesses": 12,
            "adjacentComparisons": 264,
            "cellModeOccurrences": {cell: dict(sorted(counts.items())) for cell, counts in sorted(cell_mode_counts.items())},
            "transitionDirections": dict(sorted(transition_counts.items())),
            "novelDecodedRgbHashes": {cell: [{"decodedRgbSha256": digest, "count": count} for digest, count in sorted(counts.items())]
                                       for cell, counts in sorted(novel_hashes.items())},
        },
        "ordinalModeCounts": {cell: [{"callOrdinal": ordinal, "counts": dict(sorted(ordinal_counts[cell][ordinal].items()))}
                                     for ordinal in range(1, 13)] for cell in ("NATURAL", "CENTER")},
        "processes": processes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    natural_novel = sum(item["count"] for item in result["summary"]["novelDecodedRgbHashes"].get("NATURAL", []))
    center_novel = sum(item["count"] for item in result["summary"]["novelDecodedRgbHashes"].get("CENTER", []))
    print(f"BFS_B30_CLASSIFY_OK natural_switch={len(switching_natural)} center_exact={len(center_exact_pids)} natural_novel={natural_novel} center_novel={center_novel}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B30_CLASSIFY_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
