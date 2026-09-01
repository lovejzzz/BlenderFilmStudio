# RC3 development attempt-02 retained failure and C3

Attempt-02 completed both real physics mechanisms and both save/reopen checks.
D1 contacted and responded at frame 52, peaked at 98.80388412 degrees and
reopened within `3.26e-9` m. H1 contacted at frame 16; all three bottles
responded, two settled near 90 degrees and one returned upright. H1 reopened
within `7.68e-9` m / `5.0e-9` degrees. All post-release transform keys,
authored outcome fields, light animation and renders were zero.

The final negative-control process failed only because its helper attempted to
self-hash an in-memory Infinity before asking the product validator to reject
it. The canonicalizer correctly raised, but the tool did not record the expected
rejection. C3 changes only that test path, retains product/fixture bytes and
replays the five starts in fresh roots.
