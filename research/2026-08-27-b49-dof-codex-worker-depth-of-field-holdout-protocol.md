# B49-DOF — two-scene depth-of-field operating-point holdout

Date: 2026-08-27

Status: frozen before formal renderer, runner, analyzer or output

## Question

B49-DOF-D1 established numeric focus selectivity, focus-object override behavior and pass-domain effects on a controlled depth fixture. B49-DOF now asks whether the compiled f/4 DOF settings on two promoted real scenes remain numerically adequate at the selected 128-spp raw point, and whether enabling DOF moves each candidate toward its own independent high-sample DOF reference rather than away from it.

The previously promoted CENTER 0.5-frame motion blur stays enabled in every cell. Only camera `use_dof` changes between each candidate and negative control.

## Frozen shots and cells

TABLETOP uses frame 43, a new DOF intervention point on the linear 58 mm camera push. Its compiled camera has f/4, numeric focus 8.2 m and no focus object. INTERIOR uses static frame 23 with a 70 mm camera, f/4, numeric focus 3.2 m and no focus object. Read-only D1 inspection already showed that TABLETOP's focus lies inside its subject depth band, while INTERIOR's focus favors the window region rather than the chair; the formal machine gate does not silently relabel that as correct narrative intent.

Each shot has five fresh Blender 5.2 Linux/amd64 Cycles CPU cells:

1. three 512-spp DOF-on references with independent frozen seed offsets;
2. one 128-spp DOF-on candidate using a fourth seed;
3. one same-seed 128-spp DOF-off negative control.

All ten cells render 128×72 raw multipart float32 EXR, denoising off, persistent data off, fixed four threads, ACES 2, motion blur on, centered shutter 0.5 and the exact seven production subimages.

## Frozen quality decision

For each shot, the analyzer averages the three scene-linear Combined references. The local reference floor for each metric is the maximum individual-reference error against that mean. The three metrics are linear RGB NRMSE normalized by ensemble RMS, log-luminance RMSE and exact-top-10%-ensemble-edge linear RMSE.

A shot passes numerical adequacy only when the 128-spp DOF candidate is no more than 3× its reference floor in all three metrics. The stronger supported verdict additionally requires the candidate to be strictly closer than the same-seed DOF-off control in all three metrics on both shots.

- both shots adequate and 3/3 closer: `B49_DEPTH_OF_FIELD_OPERATING_POINT_SUPPORTED`;
- both shots adequate but fewer than 3/3 closer on either shot: `B49_DEPTH_OF_FIELD_NUMERICALLY_ADEQUATE_EFFECT_INDETERMINATE`;
- either shot exceeds a 3× floor: `B49_DEPTH_OF_FIELD_OPERATING_POINT_REJECTED`;
- identity, setting, pass, resource, replay or audit failure: `B49_DEPTH_OF_FIELD_HOLDOUT_INVALID_EVIDENCE`.

No threshold may be changed after output.

## Frozen pass-domain gate

For DOF-on versus DOF-off within each shot:

- Combined must differ;
- Vector must remain exact because motion-blur mode and motion are held constant;
- at least one of Depth, Normal or the three Cryptomatte layers must differ, carrying D1's auxiliary-pass counterexample into real scenes.

Cryptomatte numeric RMSE is never interpreted as perceptual magnitude. Exact hashes and changed-component counts define the identifier-domain observation.

## Claim boundary

Passing establishes bounded numerical adequacy of the compiled DOF representation and a direction toward its own high-sample reference. It does not establish the artistically correct focus target, human-visible improvement, cinematic preference, focus-pull temporal quality, bokeh aesthetics, transparency/hair behavior, 2K/4K cost, GPU/Eevee performance, native x86/cloud throughput or dollar cost.

The next gate after a valid result is a viewable-resolution, delayed-disclosure human review that may reject a machine-supported setting on focus intent or cinematic preference.
