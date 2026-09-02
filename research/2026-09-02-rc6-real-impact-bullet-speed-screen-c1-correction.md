# RC6 real-impact Bullet speed screen C1 correction

Date: 2026-09-02

The committed v0.82 runner stopped before creating either attempt-71 root and
before starting Blender. Its stored spec hash was computed with JavaScript JSON
number serialization, which writes `0.0` as `0`; the frozen Python runner
preserves `0.0`. Stored hash `f7530aaa…` therefore differed from the Python-
canonical hash `bb78abb8…` for the same retained bytes.

The v0.82 spec and tools remain immutable. C1 moves execution to unique fresh
attempt-72 roots and uses three versioned adapters plus a Python-canonical v0.83
spec. The physical question, exact scene logic, `I08/I10/I12` cells, every
acceptance threshold, all process ceilings and all resource ceilings are
unchanged. Attempt-71 counts are exactly zero Blender starts, Bullet bakes,
liquid bakes, renders and saves.

This correction is protocol-only. It does not select a physical trajectory or
permit a liquid bake.
