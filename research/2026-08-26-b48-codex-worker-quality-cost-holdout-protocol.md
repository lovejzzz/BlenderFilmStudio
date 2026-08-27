# B48 — preregistered numerical quality/cost holdout

Date: 2026-08-26

Status: preregistered before formal renderer, runner, analyzer or audit

## Question

B47 proved that the production-pass representation is reproducible. B48-D1 showed that sampling and OIDN produce a multi-objective quality/cost trade rather than a single monotonic ladder. B48-D2 then measured the non-zero disagreement between independent 512-spp realizations. B48 asks which frozen candidate, if any, is the cheapest one that remains within a fixed multiple of the local high-sample Monte Carlo floor on two unseen frames.

## Holdout frames

The formal holdouts are TABLETOP frame 37 and INTERIOR frame 19. Neither frame was used by B48-D1 or D2. The two semantic scenes prevent selecting a point on one lighting/material arrangement alone.

Each shot receives seven fresh containers and empty output roots: three 512-spp raw references with offsets 314159/424243/535529, then 32 raw, 32 OIDN, 128 raw and 128 OIDN candidates sharing candidate offset 647647. All offsets are new relative to D1/D2. Matched raw/OIDN candidates intentionally share the same underlying Cycles seed.

## Fixed representation and runtime

Every cell opens the frozen B44 A1 `.blend` directly in the pinned Blender 5.2 Linux/amd64 image. Cycles CPU, 128×72, four fixed threads, fixed ACES 2 OCIO, animated seed off, motion blur off and persistent data off remain constant. Raw outputs must contain the seven B47 subimages. OIDN outputs must contain those seven plus `BFS_MASTER.Noisy Image`, as discovered before formal preregistration. Every Combined value must be finite.

The worker boundary is unchanged: read-only root and repository, one dedicated writable output mount, network none, non-root UID/GID, all capabilities dropped, no-new-privileges, fixed PID/RAM/CPU/shm limits and TERM→KILL timeout. Exactly 14 Docker runs and 14 host EXR analyses are allowed; build, pull, download, model and video-model calls are forbidden.

## Numerical gate

For each shot, decode the three references and compute their float64 arithmetic mean. Select the top 10% of pixels by the mean image's AP1 luminance-gradient magnitude using stable exact top-k. For each metric—linear RGB NRMSE by ensemble RMS, log2(1+positive AP1 luminance) RMSE and edge-mask linear RGB RMSE—define the local reference floor as the largest deviation of one reference from the three-reference mean.

A candidate passes one shot only when all three candidate-to-mean metrics are at most 3× their corresponding local floor. It passes B48 only when it passes both shots. No metric can compensate for another. The multiplier was chosen after D1/D2 and is frozen before holdout execution; it cannot be revised after seeing frames 37 or 19.

Among candidates passing both holdouts, select the lowest median Blender render-operator seconds across the two shots. Ties break by lower samples, then raw before OIDN, then lexical ID. If no candidate passes, the valid verdict is `B48_NO_NUMERICAL_POINT_WITHIN_FROZEN_CELLS`; the evidence is not called invalid merely because the candidate set fails. Invalid evidence is reserved for identity, execution, representation, metric, attack or audit failure.

## Cost boundary

Report observed render-operator seconds, fresh-container wall seconds and EXR bytes for every cell. For each candidate, make a mechanical 240-frame projection (10 seconds at 24 fps) from the two-frame mean. This is labelled as a projection and excludes scene loading amortization, full-shot temporal effects, retries, storage replication, electricity and cloud pricing. No dollar cost is permitted in B48.

## Promotion and audit

Formal evidence must bind the exact parent, spec, tools, image, source, OCIO, argv, reports and EXRs; pass all 18 frozen attacks; leave no experiment container; and survive an independent analyzer/audit replay. A selected operating point establishes only a bounded numerical quality/cost point for these two 128×72 still frames on the current worker boundary.

It does not establish human cinematic quality, perceptual preference, denoiser temporal stability, motion blur, depth of field, 2K/4K scaling, characters, hair, GPU/Eevee behavior, native x86 throughput, cloud price or complete-shot execution. Those remain separate later gates.
