# B62-T1 · Terminal ScenePackageSpec → BuildPlan → Blender result

Date: 2026-08-29  
Status: PASS  
Verdict: `B62_TERMINAL_SCENESPEC_BUILDPLAN_AND_SCENE_COMPILATION_SUPPORTED`

## Result

The C2 retry completed the full preregistered zero-render chain from a fresh output root:

1. two separate Node processes compiled the exact `bfs.b62TerminalScenePackageSpec.v0.1` input;
2. both produced the same canonical 96-sample immutable BuildPlan;
3. a fresh Blender 5.2 process opened the exact admitted Phase 0 master, added one terminal close camera/data/action, rerouted only the close-shot marker and saved a new production scene;
4. a second fresh Blender process reopened only that derived scene and independently checked all 96 poses, ID deltas, markers, assembled asset identity, existing actions, contact/core/light state, timeline, render settings and color contract;
5. an independent Node auditor passed all 20 gates and rejected all 12 preregistered semantic mutations.

No frame was rendered. No model, network, Docker or Colima process participated.

## Exact evidence

- Tool freeze: `59499ee5fb2ef48d0fc332f769691eb4a36f0412`
- Formal root: `experiments/b62-terminal-scene-package-v0-3`
- Final root identity: 12 files, 842,849 bytes, tree SHA-256 `b75190c6bdb3d7581acf4457b154ae831dcc2652d6ba626d4e98ab6e7f2f968e`
- BuildPlan file/self: `88b626acd826ffab4c3f3571419c711335ef6775c8bece56def28c7c3ad830be` / `87de2507affa85e59a29eb848a1db45cace98977f3bc64532465c7465bf957db`
- Derived scene: 337,411 bytes, SHA-256 `0acd4d135c9bac9a7928a9a38da1a0e2f4838fd052a87a9663cef83cb2c373dc`
- Compile report file/self: `879de07550bc55bc38f269614a3174cdad98252cc3a941ca8325953688dc9645` / `beae598ed030cac5d91c73a4ec2e2f4e840def1fa1c0e1636e6af5f47d90547a`
- Independent report file/self: `996a8cad9a37fef80249d943222680ed72d29785a347265327c6332451a717cb` / `720093c20e2252e60c0f53b8268794384681938849d768bcb242146b077e14fa`
- Audit file/self: `4b8b1dd0a7b80c277896814fab0cab8fabcca8e3cf276797ce042850fe524e8d` / `002244a4a0f1916dc347306e2587728e9bded965a53e1aca7ffcf4d827decd42`
- Receipt file/self: `a4294cddcde4ba48ef613605af10c961b9eb246251850f4adfafe465087d291f` / `62d6ddbb903331f930f6fd9c94887752e90bae022eb0048003254780841e1366`

## Reopen observations

- Maximum location/quaternion error across all 96 close-shot samples: `0.0`
- Lens: planned/compiled/reopened `65 / 65 / 65 mm`
- Clip start: planned `0.05`, compiled/reopened `0.05000000074505806`; plan error `7.450580569168253e-10`, compile-observation error `0`
- Clip end: planned/compiled/reopened `200 / 200 / 200 m`
- Blender compile: 633 ms, peak sampled RSS 262,799,360 bytes
- Independent Blender reopen: 575 ms, peak sampled RSS 252,231,680 bytes
- Total formal renders: 0
- Free space at audit: 303,449,231,360 bytes, above the 100 GiB reserve

## Retained failures

The result does not erase earlier failures:

- v0.1 remains invalidated because it conflated pre-assembly asset-library identities with the assembled master identity.
- v0.2 remains invalidated because it compared JSON binary64 `0.05` to Blender RNA float32 `0.05000000074505806` with decimal equality.

Both failures are hash-bound into the successful v0.3 admission and audit.

## Claim boundary and next authorization

T1 proves a narrow B62-specific scene-package bridge, not a universal SceneSpec v0.6 compiler. It proves no new pixels, temporal image continuity, delivery encoding, final Cycles cost or restart-safe render resume.

This PASS authorizes only the next preregistered stage: render the compiled scene as a low-cost 288-frame animatic, audit every timeline frame and all three cuts, and decide whether the expensive final Cycles sequence is admissible.
