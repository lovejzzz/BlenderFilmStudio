# RC6 real-impact Bullet speed screen C2 correction

Date: 2026-09-02

C1 passed its Python-canonical identity check, then stopped before root creation
because its preregistration parent was transcribed from a short OID into the
wrong full OID. The immutable C1 spec contains
`7fdd49332e4057ce53de77a11d366673fa260416`; Git proves the actual parent is
`7fdd49330a3627b12d9e0d487ad5daeecf890429`.

Attempt-72 therefore has zero roots, Blender starts, Bullet bakes, liquid bakes,
renders and saves. C2 binds the actual current parent
`e871f3c2a10d696687a593b200d7a29049c7d38f`, uses versioned adapters and moves
to fresh attempt-73 roots. The physical question, exact scene code, candidate
values, thresholds and resource/process ceilings remain unchanged.

This correction is protocol-only and does not permit a liquid bake.
