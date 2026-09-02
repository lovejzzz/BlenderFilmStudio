# RC6 real-impact Bullet speed screen C2 attempt-73 result

Date: 2026-09-02

## Verdict

`FAIL_REAL_IMPACT_BULLET_TRAJECTORY`, retained.

All three frozen Blender processes and Bullet bakes completed successfully.
There were zero liquid bakes, renders, saves, native builds, network calls and
engine writes. The receipt is self-hashed at `daa64082…`.

## Physical result

| Cell | Contact | Peak tilt | Max cup-surface step | Derived subframes | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| I08 | 17 | 90.15° | 96.84 mm | 11 | too fast; leaves domain and penetrates floor threshold |
| I10 | 21 | 9.97° | 42.26 mm | 5 | too weak to tip |
| I12 | 25 | 10.14° | 37.22 mm | 4 | too weak to tip |

I08 proves the free cup can be knocked over by the real basketball cause, but
not within the accepted Preview fluid cost/space envelope. I10/I12 prove that
the same exact scene can cut surface sampling cost to 5/4 subframes and remain
within the accepted domain, but the impulse falls below the tipping transition.
The response is therefore nonlinear and the smallest evidence-led next physical
test is the single midpoint `driveEndFrame=9`, not a wider parameter scan.

## Audit status

The first independent audit is retained at 22/23. Its only failure is
`cellRosterAndConfigurationExact`: Blender emitted the Vector-backed domain
center/dimensions as float32 (`0.449999988…`, `0.899999976…`,
`0.579999983…`) while the auditor required exact decimal equality to
`0.45/0.9/0.58`. Every result hash, recomputed metric, verdict, process/log,
baseline, root manifest, resource and zero-side-effect check passed.

A versioned audit-only C3 must validate the same retained bytes with a bounded
`1e-6` representation tolerance before any new Bullet run. Attempt-73 must not
be repaired or rerun.
