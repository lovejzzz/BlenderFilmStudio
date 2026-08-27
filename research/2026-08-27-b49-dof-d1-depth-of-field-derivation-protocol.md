# B49-DOF-D1 — depth-of-field semantics and local-contrast derivation protocol

Date: 2026-08-27

Status: frozen before fixture renderer, runner, analyzer or output

## Question

B49-R closed the bounded resolution-scaling gate and B49-MB closed the bounded motion-blur machine gate. B49-DOF-D1 asks what Blender 5.2 Cycles actually does when aperture and focus distance are changed, whether an explicit focus object overrides the numeric distance, which production passes change, and which local metric is defensible enough to preregister for a later unseen holdout.

This is a derivation experiment. It deliberately does not select an artistic focus target or declare an image cinematic.

## Blender 5.2 semantics frozen before implementation

The Blender 5.2 camera manual defines focus by either an exact distance or the distance to a chosen focus object; choosing an object deactivates the distance control. It defines f-stop as the blur-strength control, with lower values producing stronger depth of field. Blender 5.2 RNA exposes `use_dof`, `focus_distance`, `focus_object`, `aperture_fstop`, `aperture_blades`, `aperture_rotation` and `aperture_ratio` under `Camera.dof`.

Read-only inspection of the already promoted worker scenes found:

- TABLETOP uses a 58 mm perspective camera with DOF enabled, f/4 and 8.2 m numeric focus. Instanced render geometry spans approximately 7.13–10.21 m in camera depth, so its configured focus lies inside the subject band.
- INTERIOR uses a 70 mm perspective camera with DOF enabled, f/4 and 3.2 m numeric focus. Window geometry spans approximately 2.74–4.89 m, while chair geometry spans approximately 5.71–6.98 m. The configured focus therefore favors the window region rather than the chair.
- Both cameras have no focus object. These observations show that “DOF is enabled” is not enough to establish correct focus intent.

## Frozen fixture and seven cells

Each cell starts in a fresh isolated Blender 5.2 Linux/amd64 Cycles CPU worker. A deterministic emission fixture places three equal projected-size, high-frequency stripe targets at camera depths 3 m, 5 m and 8 m. Target centers and sizes use explicit 0–1 camera-frame coordinates, and their disjoint frozen image ROIs lie inside those projected rectangles. A 50 mm perspective camera at the origin looks down local `-Z`; an empty focus marker lies on-axis at exactly 5 m. World emission is black, motion blur and denoising are off, and output is 256×144, 256 spp, float32 multilayer EXR under the fixed ACES 2 config.

Correction record: the first preregistration commit `c476e48` mixed centered target coordinates with 0–1 ROI coordinates. This was detected by geometry review before any fixture renderer, runner, analyzer or output existed. C1 changes only target-coordinate representation and nested ROIs. A second pre-tool review found that invalidators were named but their adversarial roster had no fixed denominator; C2 freezes 15 attack IDs and expected rejection reasons. Cells, interventions, measurements, resource gates and claims are unchanged. C2 is the operative preregistration.

The seven cells are:

1. DOF off, numeric distance 5 m, f/4;
2. DOF on, 5 m, f/16;
3. DOF on, 5 m, f/4;
4. DOF on, 5 m, f/1.4;
5. DOF on, 3 m, f/1.4;
6. DOF on, 8 m, f/1.4;
7. DOF on, focus object at 5 m, numeric distance deliberately set to 99 m, f/1.4.

The deliberately wrong 99 m value makes the override falsifiable. Exact equality between object-focus and numeric-focus output is measured, not assumed.

## Frozen measurements and relations

Within each target ROI the analyzer reports scene-linear p05, p95, a Michelson-like modulation measure, horizontal-gradient RMS and finite-pixel count. Across cells it reports canonical float32 pass hashes, changed-component counts, RMSE and maximum error, plus render time, fresh-worker wall, peak self RSS and EXR bytes.

Four relations are frozen:

- aperture dose response at fixed 5 m focus across OFF, f/16, f/4 and f/1.4;
- focus selectivity across 3 m, 5 m and 8 m at f/1.4;
- numeric 5 m versus focus-object 5 m with numeric distance poisoned to 99 m;
- pass-domain effects between DOF off and strong 5 m DOF.

No numerical quality threshold is selected in D1. A local contrast metric can advance only if the requested focus plane follows the 3/5/8 m intervention and the metric behaves coherently under the aperture dose. If that fails, the failure remains the result and no formal holdout threshold is invented from global image sharpness.

## Usability and claim boundary

D1 is usable only if all seven representations complete within the frozen boundary, fixture/RNA echoes match, all required pass pixels and ROIs are valid, every relation is emitted, cleanup is zero and an independent analyzer reproduces `results.json` byte for byte.

D1 cannot establish the artistically correct focus target, human cinematic preference, focus-pull quality, complete-shot temporal stability, anamorphic or polygonal bokeh, complex transparency/hair, 2K/4K cost, GPU/Eevee behavior, native x86/cloud throughput or dollar cost. A later formal holdout must use unseen focus configurations and independent high-sample references; subjective preference remains a separate blinded human gate.
