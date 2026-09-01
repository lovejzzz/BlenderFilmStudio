# RC5 physical richness — breakable attachment preregistration

RC4 solved the primary curriculum problem: a recognizable basketball strikes
three differently filled bottles, and Blender Bullet owns every post-release
transform, response frame and final pose. Direct review accepted the causality,
but the action still contains only rigid bodies that remain structurally intact.

RC5 adds exactly one new physical degree of freedom: a separate bottle cap held
to the direct-hit bottle by Blender's native breakable fixed constraint. The
constraint may break only when Bullet reports an impulse above the frozen
threshold. The input cannot name a break frame, detached pose, landing pose or
detachment velocity.

This is deliberately not described as glass fracture. It teaches a reusable
attachment rule suitable for caps, latches, armor plates and breakaway prop
parts while keeping the physical claim narrow and observable.

The frozen fixture is
`specs/fixtures/physics-action/RC5_B1.basketball-three-bottles-breakaway-cap.physics-action-spec.v0.2.json`.
Its file SHA-256 is
`a0b00cb15d66db88a85a9918701baae08734023d76edc1871901d780524169c5`
and its self hash is
`bac28a88028ffaed0b09685059e63c1f4cf23c2ad1b2a79901f54e699d4b1e34`.

The machine contract is
`specs/ai-native-studio-rc5-breakable-attachment-preregistration.v0.1.json`
with self hash
`78157d4124bd3fa4aafd5a6e8bae8fa4ba12fd0a11f9491668c4005fc59039ae`.

## Frozen physical rule

- Five active bodies: one ball, three bottles and one cap.
- One fixed constraint with native Bullet breaking enabled.
- Cap mass is 0.012 kg; breaking impulse threshold is 0.02; solver iterations
  are 80; cap/body collision is disabled while constrained.
- The cap must remain attached through the frame before measured primary
  contact and detach between contact and contact + 12.
- Detachment must reach 35 mm but remain below 1.2 m, show at least 15 degrees
  of angular response, avoid floor penetration beyond 5 mm and enter the same
  ten-frame settled evidence discipline.
- Ball, bottles and cap must have zero post-release transform keys. No authored
  break, response or final frame is allowed.

The direct review asks whether the cap is visibly attached before contact,
separates only after the causal impact, follows a continuous readable path,
remains at believable cap scale, enriches rather than overwhelms the primary
collision and appears in the derived effect composition. Any visual `NO`
rejects the candidate even if machine thresholds pass.

Development may reuse the accepted RC4 binary and may not perform a clean
native build. Formal roots cannot be created until a fresh host admission
reaches 160 GiB. The current read-only check is 157 GiB, so the preregistration
is valid but formal construction remains closed.
