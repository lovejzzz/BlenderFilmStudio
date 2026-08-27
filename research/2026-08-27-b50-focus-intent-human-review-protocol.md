# B50 viewable-resolution focus-intent human review protocol

Status: preregistered before B50 render, package, observer-interface or response tooling and before any B50 output exists.

## Why this gate exists

B49-DOF established that Blender 5.2 obeys the compiled depth-of-field controls and that the selected 128-spp representation remains within the frozen numerical reference floor. It also exposed a semantic contradiction: the frozen brief says “a restrained 24-frame locked-off portrait of a chair in an interior,” while the compiled 3.2 m focus lies inside the window-geometry depth range. Machine fidelity to a setting cannot establish that the setting expresses the director’s intent.

B50 therefore asks one bounded human question. At a viewable 960×540 resolution, do independent observers prefer the original compiled focus or a focus bound to the semantic chair object for fulfilling the exact frozen brief? “More cinematic” is recorded separately and cannot decide the primary result.

## Pre-render derivation

A read-only real-Blender 5.2 depsgraph inspection was completed before this preregistration. The camera focus distance was 3.2000000477 m. Window geometry occupied 2.7376143932–4.8920869827 m. The `PROP_CHAIR` object origin was 6.4520640373 m from the camera; the chair-back center was 6.4591784477 m and its depth range was 6.0422787666–6.8760781288 m.

This observation selects a semantic intervention, not a hand-tuned numeric winner: the candidate assigns the camera’s `focus_object` to the already compiled `PROP_CHAIR` root and retains the numeric 3.2 m field. B49-DOF-D1 already demonstrated that Blender gives the focus object authority over the numeric distance.

## Frozen render pair

Both cells load the byte-bound `INTERIOR-A1/scene.blend`, frame 23, in a fresh Linux/amd64 Blender 5.2 worker. Both use Cycles CPU, 960×540, 128 raw samples, four threads, identical seed offset, DOF on at f/4, a 70 mm lens, centered 0.5-frame motion blur, no denoising and no persistent data. One cell preserves the original null focus object and 3.2 m numeric distance. The other changes only `camera.data.dof.focus_object` to `PROP_CHAIR`.

Each cell must emit the seven-subimage scene-linear float32 production EXR contract and an unlabelled 8-bit review PNG through the pinned ACES 2 SDR transform. The images must be decodable, finite, 960×540, measurably different and free of condition-bearing metadata. Render roots start empty, disk reserve must pass, each cell has an 1,800-second timeout and no experiment container may remain.

## Delayed disclosure

The public repository may contain this protocol, tool source without output identities, a salted whole-package commitment and a leak-audit summary. Until collection closes, it must not contain condition-labelled output hashes, method filenames, observer-visible image hashes, IMAGE-to-condition mappings, salts, responses or ledgers.

Eighteen private observer sessions use `IMAGE-A` and `IMAGE-B`; nine present the original focus first and nine present the chair focus first. Every session receives a distinct salted mapping commitment. Before collection and immediately before every response acceptance, the complete tracked tree and public static build are scanned against a private sensitive-identity registry. Any pre-close condition-to-IMAGE join invalidates the study.

## Observer record

The primary question is which image better fulfills the exact frozen brief. A secondary question asks which feels more cinematic as a still. For each image the observer records where attention lands first: chair, window, room geometry, other or no clear subject. Confidence and remote viewing conditions are recorded. Developer/owner and synthetic responses are never eligible; a browser pilot validates only the interface.

Formal analysis requires exactly 18 unique eligible responses in the 9/9 schedule. Fifteen to seventeen responses remain incomplete, and fewer are informal only.

## Frozen decision

`CHAIR_FOCUS_INTENT_SUPPORT` requires at least 14/18 brief-fulfillment choices for the chair-focus condition, at least 14/18 CHAIR-attention reports for that condition, and no lower CHAIR-attention count than the original condition. `ORIGINAL_FOCUS_INTENT_SUPPORT` is exactly symmetric.

`NO_DIRECTIONAL_FOCUS_DIFFERENCE_OBSERVED` requires at least 14/18 indistinguishable brief choices, at least 14/18 indistinguishable cinematic choices and a difference of no more than two between condition-level CHAIR-attention counts. Every other complete valid result is `OBSERVER_DISAGREEMENT`. Cinematic preference is secondary and cannot overturn the primary decision.

## Claim boundary

Even a passing result applies only to this scene, still frame, focus pair, observers and recorded remote conditions. It cannot establish general cinematic quality, photorealism, acting, narrative, composition optimality, focus-pull quality, full-shot stability, 2K/4K adequacy, GPU throughput, cloud cost or delivery-master quality. Before 18 valid responses exist, the only permissible human status is pending, informal or incomplete.
