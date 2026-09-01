#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""C2 launcher: use JavaScript-number canonicalization for the C1 prereg self hash."""

import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path


source_path = Path(__file__).with_name("run-pc8-measured-shutter.py")
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
    expected = value.get(field)
    body = dict(value); body.pop(field, None)
    return expected == hashlib.sha256(js_canonical(body).encode()).hexdigest()


'''
needle = "\ndef valid_self(value, field):\n"
if source.count(needle) != 1:
    raise RuntimeError("C2 valid_self insertion anchor differs")
source = source.replace(needle, "\n" + insertion + "def valid_self(value, field):\n", 1)
old_gate = 'if not valid_self(prereg, "specHash") or not valid_self(freeze, "freezeHash"):'
new_gate = 'if not valid_js_self(prereg, "specHash") or not valid_self(freeze, "freezeHash"):'
if source.count(old_gate) != 1:
    raise RuntimeError("C2 prereg gate anchor differs")
source = source.replace(old_gate, new_gate, 1)
old_freeze = "ai-native-studio-pc8-measured-shutter-tool-freeze.v0.1.json"
new_freeze = "ai-native-studio-pc8-measured-shutter-tool-freeze-c2.v0.2.json"
if source.count(old_freeze) != 1:
    raise RuntimeError("C2 freeze path anchor differs")
source = source.replace(old_freeze, new_freeze, 1)
source = source.replace("PC8_EXECUTION_PASS", "PC8_C2_EXECUTION_PASS", 1)
namespace = {"__file__": str(source_path), "__name__": "__main__", "Decimal": Decimal, "hashlib": hashlib, "json": json, "math": math}
exec(compile(source, str(source_path), "exec"), namespace)
