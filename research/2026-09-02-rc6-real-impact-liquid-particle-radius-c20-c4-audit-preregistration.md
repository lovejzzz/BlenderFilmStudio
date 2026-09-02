# RC6 C20 C4 preregistration — shared audit execution environment

Date: 2026-09-02
Status: preregistered before attempt-97 evidence-root creation

C3 verified its parent and retained evidence, then failed because generated
audit code used separate globals/locals namespaces. C4 changes exactly that
outer call: copy current globals and locals into one dictionary and pass the
same dictionary for both execution namespaces. It uses versioned C4 names and a
fresh attempt-97 root.

The expanded audit program itself is exact C3 after normalizing C3/C4 names and
roots. The `2e-8` centroid replay, two `1e-8` volume replays, all27 physical
checks, retained manifests/hashes, claim and zero-Blender ceilings are unchanged.
Attempts93/94/96 remain immutable and attempt-95 remains absent.
