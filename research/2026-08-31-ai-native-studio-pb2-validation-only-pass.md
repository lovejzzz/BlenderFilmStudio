# PB.2 validation-only PASS

Date: 2026-08-31
Mode: typed-contract inspection only; zero Blender and zero mutation

The exact C2 execution contract was committed as
`7237f8b99fb0e4548d016aee57c896fb2d92536f`, whose sole parent is the
preregistered `f3a8f86949462148935027008e89460f6b9033c4`. The committed
contract bytes have SHA-256
`25aa2519c658593effe9cb6ff46629758a8cc70e76fd30f3a90d42de4da69da9`.

Formal attempt-01 passed the two frozen positive inspections. B01 resolved to
plan hash `316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf`;
B02 resolved to
`a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687`.
All eight negative controls rejected before writes with their preregistered
reason: rejected proposal, tampered proposal, missing approval, wrong order,
unauthorized scope, unknown field, path escape and non-finite number.

The runner receipt is `PASS`, file SHA-256
`fb4c4100b9476f0ac37de35ec9c9a526438f0558c20df0b3e04a9ad57253018c`, self hash
`ffb845af421c79eca25e6374bf15578a25052a1f03a9862156ff059cc827d8d5`.
The independent auditor does not import or execute the product contract module
and passed 19/19; its file SHA-256 is
`3b5bc3fca3d879fb25cbf3704f020337b4fc77e0f7c6707be4d450b88de0967e` and self hash is
`0a57ccf75ea764db0e6fcf9a14e4730cbb84bc39a038f0816cf0046e01169396`.

Proposal executions, BuildPlan files, Blender starts, renders, scene mutations,
proposal-originated Python/shell/network authority, engine source edits and
engine remote writes were all zero. The retained engine source and public
`lovejzzz/film-engine` main both remained
`4061e12bd45a2bec83e68d0cf49abbf56d4738f6`; no tag was present.

This PASS proves only the frozen B01/B02 typed proposal-and-approval boundary
and eight pre-write fail-closed controls on this exact source. It does not start
Blender, build a scene, pass PB.3, validate arbitrary proposals, or prove model,
production or distribution readiness. The one-run PB.2 authorization is
consumed. PB.3–PB.7 remain unauthorized.
