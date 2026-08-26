"""Classify B28 renders against the two frozen decoded-RGB modes."""

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
    spec = image.spec()
    layout = [spec.width, spec.height, list(spec.channelnames), str(spec.format)]
    if layout != expected_layout:
        raise RuntimeError(f"Layout mismatch for {path}: {layout!r} != {expected_layout!r}")
    pixels = image.get_pixels(oiio.UINT8)[:, :, :3]
    return hashlib.sha256(pixels.tobytes(order="C")).hexdigest(), layout


def main() -> None:
    args = parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if spec["documentType"] != "BFS_REPEATED_FRAME_MODE_SWITCH_SPEC":
        raise RuntimeError("B28 spec type mismatch")
    if index["documentType"] != "BFS_B28_CLASSIFICATION_INDEX":
        raise RuntimeError("B28 index type mismatch")
    if index["b28SpecSha256"] != sha256_file(args.spec):
        raise RuntimeError("B28 index/spec binding mismatch")

    expected_layout = [960, 540, ["R", "G", "B", "A"], "uint8"]
    known_by_hash: dict[str, str] = {}
    anchors: dict[str, dict[str, Any]] = {}
    for label in ("REFERENCE", "ALTERNATE"):
        meta = spec["knownModes"][label]
        path = Path.cwd() / meta["anchorUri"]
        container_sha = sha256_file(path)
        decoded_sha, layout = decode(path, expected_layout)
        if container_sha != meta["anchorContainerSha256"]:
            raise RuntimeError(f"{label} anchor container mismatch")
        if decoded_sha != meta["decodedRgbSha256"]:
            raise RuntimeError(f"{label} anchor decoded RGB mismatch")
        known_by_hash[decoded_sha] = label
        anchors[label] = {**meta, "observedContainerSha256": container_sha, "observedDecodedRgbSha256": decoded_sha, "layout": layout}
    if len(known_by_hash) != 2:
        raise RuntimeError("Known modes are not distinct")

    processes = []
    mode_occurrences: Counter[str] = Counter()
    mode_pids: defaultdict[str, set[str]] = defaultdict(set)
    ordinal_counts: defaultdict[int, Counter[str]] = defaultdict(Counter)
    novel_hashes: Counter[str] = Counter()
    total_transitions = 0
    transition_directions: Counter[str] = Counter()
    if [item["replicate"] for item in index["processes"]] != spec["design"]["processOrder"]:
        raise RuntimeError("B28 process order mismatch")
    for process in index["processes"]:
        replicate = process["replicate"]
        if len(process["renders"]) != 12:
            raise RuntimeError(f"{replicate} render count mismatch")
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
            mode = known_by_hash.get(decoded_sha, "NOVEL")
            sequence.append(mode)
            mode_occurrences[mode] += 1
            mode_pids[mode].add(replicate)
            ordinal_counts[ordinal][mode] += 1
            if mode == "NOVEL":
                novel_hashes[decoded_sha] += 1
            public_renders.append({**item, "decodedRgbSha256": decoded_sha, "mode": mode, "layout": layout})
        transitions = []
        for ordinal in range(1, len(sequence)):
            if sequence[ordinal] != sequence[ordinal - 1]:
                direction = f"{sequence[ordinal - 1]}->{sequence[ordinal]}"
                transitions.append({"afterCallOrdinal": ordinal, "before": sequence[ordinal - 1], "after": sequence[ordinal], "direction": direction})
                transition_directions[direction] += 1
        total_transitions += len(transitions)
        modes = set(sequence)
        processes.append({
            "replicate": replicate,
            "processId": process["processId"],
            "manifestHash": process["manifestHash"],
            "sequence": sequence,
            "modeCounts": dict(sorted(Counter(sequence).items())),
            "withinPidKnownModeSwitch": "REFERENCE" in modes and "ALTERNATE" in modes,
            "adjacentTransitionCount": len(transitions),
            "transitions": transitions,
            "renders": public_renders,
        })

    if len(processes) != 12 or sum(len(item["renders"]) for item in processes) != 144:
        raise RuntimeError("B28 fixed sample count mismatch")
    switching = [item["replicate"] for item in processes if item["withinPidKnownModeSwitch"]]
    result = {
        "documentType": "BFS_B28_REPEATED_FRAME_MODE_CLASSIFICATION",
        "version": "0.1.0",
        "decoder": f"OpenImageIO {oiio.VERSION_STRING}",
        "b28SpecSha256": sha256_file(args.spec),
        "indexSha256": sha256_file(args.index),
        "layout": {"width": 960, "height": 540, "channels": ["R", "G", "B", "A"], "pixelFormat": "uint8"},
        "anchors": anchors,
        "primary": {
            "endpoint": spec["primaryEndpoint"]["name"],
            "supportThresholdProcesses": spec["primaryEndpoint"]["supportThresholdProcesses"],
            "switchingProcessCount": len(switching),
            "switchingProcesses": switching,
        },
        "summary": {
            "processes": len(processes),
            "renders": 144,
            "adjacentComparisons": 132,
            "observedAdjacentTransitions": total_transitions,
            "modeOccurrences": dict(sorted(mode_occurrences.items())),
            "modeProcessCounts": {mode: len(pids) for mode, pids in sorted(mode_pids.items())},
            "transitionDirections": dict(sorted(transition_directions.items())),
            "novelDecodedRgbHashes": [{"decodedRgbSha256": digest, "count": count} for digest, count in sorted(novel_hashes.items())],
        },
        "ordinalModeCounts": [{"callOrdinal": ordinal, "counts": dict(sorted(ordinal_counts[ordinal].items()))} for ordinal in range(1, 13)],
        "processes": processes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"BFS_B28_CLASSIFY_OK switches={len(switching)} transitions={total_transitions} novel={sum(novel_hashes.values())}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"BFS_B28_CLASSIFY_ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error
