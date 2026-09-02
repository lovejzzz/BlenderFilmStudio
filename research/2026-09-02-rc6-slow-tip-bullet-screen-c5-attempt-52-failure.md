# RC6 slow-tip Bullet screen C5 attempt-52 failure

Date: 2026-09-02
Verdict: `FAIL_EXECUTION`; no motorized physical result available

Attempt-52 passed admission and completed one 120-frame Bullet bake for C5F48.
The Blender process then raised `NameError: name 'separation' is not defined`
inside the measurement loop. C5 intentionally removed the old pusher/cup
separation calculation but left the base loop's contact-frame conditional
referencing that name.

No cell result, aggregate receipt or audit was written. C5F60, C5F72 and C5F96
were skipped. Counts are one Blender start, one Bullet bake and zero fluid,
render, save, network or engine-write operations. The process exited zero at
the Blender host level, but the runner correctly rejected the traceback.

This is a harness failure and provides no evidence for or against the motorized
slow-tip mechanism. C5-C1 may only define the removed legacy separation value
as `math.inf` before the unreachable old contact conditional. Motor axis,
maximum impulse, target speeds, hinge, limits, damping, domain, thresholds and
all process ceilings remain exact.
