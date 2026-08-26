# B09 source-physics blind human-review protocol

Status: pre-registered before rendering or opening the review clip.

## Question

Does the single B06 trajectory selected for B07 read as a visually plausible two-sided rigid-body support, vertical transport and release when shown with its declared colliders?

This is a visual pilot for one selected solve. It does not test Bullet reproducibility, real-world force accuracy, anatomy, final art direction or cinema quality.

## Blinding and clip contract

- Reviewers see an anonymous clip ID, not B06/B07/B08 labels or machine scores.
- The clip is generated from the hash-pinned B08 replay target plus the collider transforms in `B06.final-manifest.json`.
- Physics stays disabled during review rendering; this prevents a new Bullet solve from replacing the exact selected source trajectory.
- The clip covers frames 1–116 at 24 fps. It shows approach, closure, the full hold/transport window and the initial release fall. The later off-frame free fall is intentionally outside this visual pilot.
- Clip bytes are SHA-256 pinned in the response schema before the review page opens.
- The static page does not transmit responses. Reviewers download JSON and return it to the research owner.

## Questions

Three 1–5 scores:

1. two-sided support readability during hold;
2. prop/collider synchronization during vertical transport;
3. physical plausibility of release onset.

Two categorical defect checks:

- visible interpenetration or impossible separation;
- visible pop or teleport.

One overall verdict: `PASS`, `FAIL` or `UNSURE` for the narrow source-trajectory plausibility question.

## Frozen acceptance rule

At least three authentic, independent responses are required. No model-generated or researcher-invented response counts.

Pass requires all of:

- median of every 1–5 scale at least 4;
- zero `YES` responses for visible interpenetration/impossible separation;
- zero `YES` responses for visible pop/teleport;
- strict majority overall `PASS`;
- zero overall `FAIL`.

Until three valid responses exist, status is `PENDING_INSUFFICIENT_RESPONSES`. Once enough responses exist, failure of any gate yields `FAIL`; results are not tuned or discarded.

## Nonclaims

Even a human-review pass would approve only the visible selected trajectory in this technical proxy. B06 remains formally false on cross-process rigid-body reproducibility, and no result here validates realistic contact pressure, material coefficients or production-cinema quality.
