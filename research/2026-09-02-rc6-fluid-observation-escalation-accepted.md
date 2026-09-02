# RC6 fluid observation escalation policy accepted

The one-path product candidate
`031793e09e60532b7406009ad47c06afef77876b` extends the existing pure-Python
liquid iteration module with product-owned, self-hashed tier observations and
one cross-tier escalation decision. It has no `bpy` dependency and cannot
start a bake, render or build.

Three positive cases passed: a contained REVIEW result against an accepted
FINAL defect remains `INCONCLUSIVE_LOWER_TIER_CONTAINED`; a contained
same-tier candidate becomes only `CANDIDATE_SAME_TIER_SIGNAL`; and a same-tier
threshold exceedance becomes `DEFECT_REPRODUCED`. The next actions are,
respectively, a same-tier single-variable probe, dependent-stage verification,
and causal-input audit. Every decision fixes `clearsAcceptedDefect=false`.

All twelve fail-closed attacks passed, including unknown tier and field,
tier/resolution mismatch, forged observation hash, physics/metric/threshold
identity drift, a candidate above the accepted defect tier, zero or multiple
changed parameters, caller-authored next action and a non-finite value. The
validation receipt self hash is
`3f425ddebf7f40a8b905371a183e72c025111a7c1030d5e2a759c925a88cb4d6`.
The independent audit passed 12/12 with self hash
`0f1301a7f93b6dcd08bbb2321b6a95945d35b7a900aa10ee01171bdd2c2acf63`.

This accepts the decision policy only. It does not prove Blender UI wiring,
cache execution, the current reconstructed liquid surface, slow tip, impact,
render quality or finished-film quality.
