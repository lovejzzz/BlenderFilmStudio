#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""C2 audit launcher matching the corrected prereg self-hash verifier."""

import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path


source_path = Path(__file__).with_name("audit-pc8-measured-shutter.py")
source = source_path.read_text(encoding="utf-8")
insertion = '''
def javascript_number(value):
    if not math.isfinite(value):
        raise ValueError("nonfinite")
    if value == 0:
        return "0"
    absolute = abs(value)
    source = repr(value).lower()
    if 1e-6 <= absolute < 1e21:
        if "e" in source:
            fixed = format(Decimal(source), "f")
            return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
        return source[:-2] if source.endswith(".0") else source
    if "e" not in source:
        source = format(value, ".15e")
        mantissa, exponent = source.split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
    else:
        mantissa, exponent = source.split("e")
    exponent_value = int(exponent)
    sign = "+" if exponent_value >= 0 else "-"
    return f"{mantissa}e{sign}{abs(exponent_value)}"


def js_canonical(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return javascript_number(value)
    if isinstance(value, list):
        return "[" + ",".join(js_canonical(child) for child in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{js_canonical(key)}:{js_canonical(value[key])}" for key in sorted(value)) + "}"
    raise TypeError(type(value))


def valid_js_self(value, field):
    body = dict(value); expected = body.pop(field, None)
    return expected == hashlib.sha256(js_canonical(body).encode()).hexdigest()


'''
needle = "\ndef valid_self(value, field):\n"
if source.count(needle) != 1:
    raise RuntimeError("C2 audit insertion anchor differs")
source = source.replace(needle, "\n" + insertion + "def valid_self(value, field):\n", 1)
old_check = 'valid_self(prereg, "specHash") and valid_self(freeze, "freezeHash")'
new_check = 'valid_js_self(prereg, "specHash") and valid_self(freeze, "freezeHash")'
if source.count(old_check) != 1:
    raise RuntimeError("C2 audit prereg check anchor differs")
source = source.replace(old_check, new_check, 1)
old_freeze = "ai-native-studio-pc8-measured-shutter-tool-freeze.v0.1.json"
new_freeze = "ai-native-studio-pc8-measured-shutter-tool-freeze-c2.v0.2.json"
if source.count(old_freeze) != 1:
    raise RuntimeError("C2 audit freeze path anchor differs")
source = source.replace(old_freeze, new_freeze, 1)
source = source.replace("PC8_AUDIT", "PC8_C2_AUDIT", 1)
namespace = {"__file__": str(source_path), "__name__": "__main__", "Decimal": Decimal, "hashlib": hashlib, "json": json, "math": math}
exec(compile(source, str(source_path), "exec"), namespace)
