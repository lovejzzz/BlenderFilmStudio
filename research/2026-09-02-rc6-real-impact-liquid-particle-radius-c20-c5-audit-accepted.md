# RC6 C20 C5 — audit-only closure accepted

Date: 2026-09-02
Status: `PASS 26/26`; retained physical result remains `FAIL 23/27`

C5 made only the two preregistered historical-view corrections. The retained
attempt-94 process argv now resolves its evidence argument to attempt-94, and
the retained pre-audit manifest replay excludes the independent audit and two
audit logs that did not yet exist when that snapshot was captured.

Fresh attempt-98 passes all26 audit checks. It independently verifies both the
attempt-94 and C4 attempt-97 manifests, all process hashes/argv/logs, both root
manifests, the C5 freeze and tool identities, and all27 physical booleans. The
centroid replay delta remains `1.0177317821824516e-8 m`, below the frozen
`2e-8 m` tolerance. Audit self hash is
`12bcab9ee0c255d33357b10866e70d88ed5da9fbfa6426cfdbbd8036f168b2c5`;
receipt self hash is
`6d8b5f2d779058a9208c1b9b9f813d0099b7305d664eebeb45996ec79ddc9d47`.

The run used one system-Python process and zero Blender starts, Bullet/Data/Mesh
bakes, renders, saves, builds, network calls, engine writes or retained-root
writes. C20 therefore closes as a well-audited physical regression, not an
accepted liquid result.

The next scientific step is one preregistered zero-Blender copied-cache C21
comparison of C20 attempt-94 against C18 attempt-90. It must locate velocity,
particle-support and Mesh expansion onset independently and compare peak
amplitude. It may not change a physical value, render, or reuse either retained
cache in place.
