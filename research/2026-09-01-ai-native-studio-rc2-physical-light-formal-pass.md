# RC2 physical-light transfer formal pass

Date: 2026-09-01

RC2 formal attempt-01 is accepted. One local-only source clone, one clean native
arm64 build and three offline product starts produced a solver-owned rolling
sphere, hinged shutter, static-light reveal, saved workspace, three formal
stills and a 48-frame contact clip.

The accepted evidence root is
`experiments/physical-light-transfer/RC2-2026-09-01-attempt-01`. Machine receipt,
independent audit, direct visual review, acceptance and root manifest hashes are
`85fe1ec3…`, `4e61abe6…`, `38cca8d8…`, `5d8d08b6…` and `feb6b6ea…` respectively.
Independent audit is 40/40 `PASS`; direct review is 9/9 `YES`; all 117 manifest
entries verify exactly.

Measured contact and first response both occur at frame 51. The sphere travels
4.1908872 m with `1.48e-6` median rolling slip. The shutter peaks at
98.80388412° and settles from frame 76 against a passive collision stop. Actor
pose keys, shutter pose keys and reveal-light animation channels are all zero.
The fixed 1050 W light produces an actual/closed receiver luminance ratio of
2.663735624. Reopened maximum deltas are `3.725290298461914e-9` m and
`4.300723333017231e-9`°.

The formal binary SHA-256 is
`9e24e64976e5747a415bff3633907c1612871b6220917621fbadebfa04005efb`.
The validated product commit
`636f42f28f781f3e858fd5b6bf641910a549c91b` was published to
`lovejzzz/film-engine/main` by one ordinary fast-forward from `0e84ef3b...`.
Git, the GitHub API and both public raw source paths independently returned the
exact new OID and validated source hashes. No force, other public ref, tag,
release, LFS upload, binary distribution, signing or notarization occurred.
The publication receipt is retained outside the sealed formal root at
`experiments/physical-light-transfer/RC2-publication-2026-09-01-attempt-01/receipt.json`.

The accepted claim remains narrow: one clean-native, deliberately simple
physical-light transfer on this M2 Max. It does not establish photoreal assets,
complex acting, sound design, cross-platform behavior or finished-film quality.
