#!/usr/bin/env python3
"""F5 harness correction: preserve nested replacement newlines with a raw string."""

import hashlib
from pathlib import Path


BASE = Path(__file__).resolve().with_name("run-rc6-fluid-consequence-scene-f4.py")
EXPECTED_BASE_SHA256 = "ff53e111ddfd8b6e94a91703ed903903895d8b840747c22ef18cd79e451ce718"
if hashlib.sha256(BASE.read_bytes()).hexdigest() != EXPECTED_BASE_SHA256:
    raise RuntimeError("RC6 F5 base adapter identity mismatch")
source = BASE.read_text(encoding="utf-8")
before = "injected = '''f4_replacements = ("
after = "injected = r'''f4_replacements = ("
if source.count(before) != 1:
    raise RuntimeError("RC6 F5 raw-string correction target is not unique")
source = source.replace(before, after)
exec(compile(source, str(BASE) + "#F5_RAW_NESTED_REPLACEMENTS", "exec"), globals(), globals())
