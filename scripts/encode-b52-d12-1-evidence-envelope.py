#!/usr/bin/env python3
"""Python implementation of the preregistered D12.1 typed evidence envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


SPEC_SHA256 = "8bd219570e0c7ec922a671919d680787caf55b2ba7d8a631ed5bc995ab24f116"
MAX_SAFE_INTEGER = 2**53 - 1


def validate_string(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("unpaired surrogate is forbidden")


def encode_number(value: int | float) -> dict[str, str]:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite number is forbidden")
    if number.is_integer() and abs(number) > MAX_SAFE_INTEGER:
        raise ValueError("integer-valued number exceeds binary64 safe integer domain")
    if number == 0.0:
        number = 0.0
    return {"$f64be": struct.pack(">d", number).hex()}


def transform(value: object) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return encode_number(value)
    if isinstance(value, str):
        validate_string(value)
        return value
    if isinstance(value, list):
        return [transform(item) for item in value]
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise ValueError("JSON object key is not a string")
            validate_string(key)
        return {key: transform(value[key]) for key in sorted(value)}
    raise ValueError(f"unsupported JSON value type: {type(value).__name__}")


def envelope_bytes(value: object) -> bytes:
    normalized = transform(value)
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subtree")
    args = parser.parse_args()
    if hashlib.sha256(args.spec.read_bytes()).hexdigest() != SPEC_SHA256:
        raise RuntimeError("D12.1 development spec identity mismatch")
    if args.output.exists():
        raise RuntimeError("refusing to overwrite evidence envelope")
    payload = json.loads(args.input.read_text())
    if args.subtree:
        if not isinstance(payload, dict) or args.subtree not in payload:
            raise RuntimeError("requested subtree is absent")
        payload = payload[args.subtree]
    elif isinstance(payload, dict):
        payload = {key: value for key, value in payload.items() if key != "reportHash"}
    encoded = envelope_bytes(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print(f"BFS_D12_1_ENVELOPE_PY_OK bytes={len(encoded)} sha256={hashlib.sha256(encoded).hexdigest()}")


if __name__ == "__main__":
    main()
