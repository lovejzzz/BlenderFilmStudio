# RC6 C32 — Native liquid observability, before another bake

Date: 2026-09-02
Scope: read-only source inspection; source-binding audit pending at freeze.

## Decision

The bound RC5 engine has an existing cache path for native liquid level sets:
`cache_resumable=True` includes `phi`, `phi_particles` and `phi_previous` in
Data export. This is a feasible observation path, **not a demonstrated passive
measurement intervention**. It changes cache import as well as export, and
the Mesh stage consumes `phi`. No Blender process, cache copy/mount, bake,
render, source edit or native build is part of C32.

C29 remains physical FAIL 25/27. C30's particle-and-Mesh support loss remains
a support diagnosis, not exact mass loss. Neither this inspection nor a later
native-field diagnostic can clear the frozen physical gate by itself.

## Bound implementation

Source is RC5 commit `8e18c82548f8716c415e6e1b69fdbbdeef1f1900` in the
retained RC5 source root. Exact paths, file hashes and line-ranged anchors are
in `specs/ai-native-studio-rc6-native-conservation-observability-c32.v1.22.json`.
The audit checks source bytes against that commit, independently extracts
anchors, and binds retained C29/C30/C31 evidence. These are mechanical source
checks, not a second human interpretation or runtime equivalence proof.

### What can be observed

- `liquid_script.h:70–96` allocates the three level sets. Final liquid data
  contains particles and particle velocity; resumable liquid data adds the
  three level sets. `DNA_fluid_types.h:343–345` supplies their actual VDB names.
- `fluid_script.h:286–287` adds velocity to final data and obstacle/inflow/
  outflow level sets, flags and previous velocity to resumable data. Dynamic
  obstacle/outflow fields can extend the roster; a reader must check actual
  names, types, dimensions and metadata, not assume a fixed file count.
- `phi` is the current numerical liquid boundary. `phi_particles` is the
  particle-union boundary constructed before `adjustNumber` reseeding/deletion
  in that substep. `phi_previous` is copied at the beginning of an adaptive
  frame, after that frame's pre-step source/obstacle handling; it is not
  necessarily the preceding saved terminal field. These are not three
  interchangeable measurements of the same instantaneous mass.
- The generated Data export skips intermediate subframes. Saved fields cannot
  identify which individual substep or operation caused a change.
- RNA exposes smoke density and velocity arrays, but this bound RNA file has
  no `phi_grid` property. Smoke density is not a liquid volume measurement.
  No private-pointer access or engine rebuild is proposed.

### Why the switch is not automatically passive

RNA updates `cache_resumable` through `rna_Fluid_datacache_reset`. Both
`liquid_load_data` and `liquid_save_data` select the extended dictionaries.
During a modular Mesh bake, `fluid.cc:3954–3963` makes `read_partial` false and
loads the extended dictionary when the switch is on. `liquid_step_mesh`
copies/interpolates `phi` before shrinking/joining the particle-derived field.
Thus comparing new resumable Mesh to old non-resumable Mesh would confound
observation with a changed input path. C32 demonstrates the source dependency,
not a measured magnitude or direction of a resulting Mesh change.

For fresh, uninterrupted Data-only baking there is a narrower hypothesis:
the current frame's cache is initially absent, `MANTA::readData` returns before
import when `hasData` is false, and the frame then advances and exports its
state. No resumable branch occurs inside the bound `liquid_step` itself.
This supports testing an export-only effect under that lifecycle; it does
**not** prove bitwise repeatability, absence of every indirect effect, or
equivalence after reopening/resuming. No pause/reopen/resume should be used in
that diagnostic. The exact lifecycle and common output fields must be checked.

### Measurement traps the reader must reject

1. VDB active voxel count is not negative liquid volume. The writer copies a
   dense level set into a zero-background VDB; positive exterior values can be
   active and constant regions can be tiles. Count field signs over the finite
   `file_base_resolution`, accounting for tiles/inactive values. Never count
   the unbounded background or equate stored entries with liquid cells.
2. The level-set constructor uses a non-sparse base grid; export then uses
   zero clipping tolerance for that grid. This does not remove float-storage
   quantization. VDB options can store half precision; observe the actual
   precision rather than assuming a full-float diagnostic.
3. The writer sets a world-space voxel transform and `file_voxel_size`, but
   copies scalar phi samples directly. Source operations use cell units
   (`addConst(1.)`, narrow-band widths). Do not assume scalar distances are
   meters merely because the VDB transform is in meters. Any library
   level-set-volume/SDF routine needs its assumptions validated first.
4. A bounded primary descriptor can be `count(phi < 0) * voxelSize^3`, named
   **negative-levelset occupied volume**, with a separately frozen subcell
   estimator/sensitivity check if needed. This is a numerical occupancy
   estimate, not exact fluid mass or a replacement for source/Mesh checks.
5. The solver advects phi, subtracts obstacles, shrinks it and joins a particle
   level set. Native does not mean analytically conservative. An observed phi
   decrease alone would not isolate advection, resampling or boundary handling.
6. Cache import/export helpers catch errors and log them. A zero process exit
   is insufficient: missing fields, nonfinite samples, invalid dimensions,
   unexpected formats and incomplete frames must reject the observation.

## Next gate — C33, not executed or authorized by this document

Preregister a fresh **Data-only native-field diagnostic** of exact C29's R40
impact, using the accepted RC5 binary and the same 1–36 window. The intended
physical configuration, geometry, Bullet-derived trajectory, APIC, bandwidth3,
resolution96 and all other solver settings stay unchanged. The candidate
observation change is resumable cache false-to-true, but the retained actual
cache policy and export precision must first be established from bound
evidence; do not silently assume missing settings. Record and allowlist all
operational differences, including omitted Mesh execution and fresh paths.

Before any bake, freeze the reader, field units, finite-grid measurement,
negative controls, common-field equivalence test/tolerances, resources, exact
roots and one-run stop rule. Common-field validation must cover particle
positions/attributes and velocity values or an equivalently strong canonical
representation; matching bounding boxes/occupied counts alone is insufficient.
If the available reader cannot expose these, stop at reader readiness rather
than weakening the equivalence claim. Compare only common decoded fields,
not whole VDB bytes containing intentionally different field rosters.

Use no Mesh bake, render, source mutation, native build, retained-cache mount,
pause or resume. Retained data can be inspected only under the separately
frozen read/copy strategy. A mismatch makes measurement passivity unproven;
retain it, do not adjust physics or claim conservation was repaired.

C33 must first determine whether native phi support contracts along with the
particle/Mesh evidence, or whether their discrepancies point toward a
representation/reconstruction issue. Both outcomes are diagnostic, not a
physical PASS or permission to render. The rectangular-vessel holdout remains
unexecuted and is not a replacement for the user's R40 impact film.

## Resource and claim ceiling

Host preflight at `2026-09-02T20:00:51.847Z` reports 154 GiB free versus the
160 GiB clean-build threshold. No clean build is admitted. C32 writes at most
1 MiB of fresh research evidence while retaining the 100 GiB reserve.

C32 establishes source-level observability and its confounds only. Native
volume, passive export equivalence, repaired impact physics, product
integration, cache speedup and improved film quality remain unmeasured.
