# RC6 C5-C2 attempt-54 failure-closure preregistration

Date: 2026-09-02

Status: preregistered before append-only closure

Attempt-54 completed one C5F48 Blender/Bullet process and wrote a self-hashed
PASS result. The aggregate runner then rejected the log because its outer
wrapper expected a C5-C2 marker while the deliberately unchanged scene tool
emitted its frozen C5 marker. No later cell started and no aggregate receipt was
written.

The closure performs no Blender, Bullet, fluid, render, save, build or network
work. It independently recomputes the existing cell's response, surface,
subframe and hinge metrics, binds the process/log/result hashes, proves the
marker mismatch and appends only a failure receipt, failure audit and two root
manifests. Existing attempt-54 bytes are immutable.
