# Personal Film Studio

A local filmmaking workspace on the existing Film Studio Engine / Blender runtime. It includes two editable films, reusable procedural assets, shot creation, bounded AI direction, versioned saves, native previews, resumable final rendering and original sound.

## Start

Double-click **Open Film Studio.command** for *The Last Signal*, or **Open Little Gravity.command** for *Little Gravity*. These launch the validated local engine with the separate studio modules. No new binary installation is involved.

On first launch, complete Blender's default quick setup. In the right side of the viewport, click the vertical **Film Studio** tab. Press **N** if the sidebar is hidden. The viewport is an interactive material preview; **Render this frame** shows the final Cycles look.

1. Select a shot and click **Go to shot**. Space plays its source range.
2. Use **Closer**, **Wider**, **Warmer**, or **Cooler** for immediate changes.
3. Write a director note, click **Ask AI Director**, review its proposal, then **Apply proposed change**. This uses your existing ChatGPT-authenticated Codex CLI. It does not use API billing. Examples: “Keep the lens, but move us a little closer”; “Give the whole film a warmer late-night feeling.”
4. **Add coverage shot** splits the current shot into two camera angles while keeping its total duration and physical world. Direct the new angle with the same controls.
5. **Undo revision** restores the preceding direction. **Save a new version** writes a separate `.blend` and `.film.json` under `~/Movies/Personal Film Studio/`; it does not replace a previous version.
6. **Render finished movie** captures the current project into a separate render job and makes a1920-wide,24fps movie with original stereo sound. Continue editing while that snapshot renders. **Resume last movie** reuses hash-verified completed frames and retains interrupted partial files. **Open movie folder** shows the files.

Use **Open another film…** to reopen your saved versions. If a film was opened directly without the launcher, run the launcher with its path so the studio panel is registered.

## Current scope

The two starter worlds are editable Blender scenes built with one procedural asset/compiler library. The tape transport uses authored mechanical animation; the kinetic sculpture's post-release motion is a baked native Bullet simulation. Director notes can change camera distance/orbit, lens, focus, cut offset, warmth and exposure. New arbitrary geometry, characters, fluids and unrestricted Python are not model-edit operations in this version.

Final movie delivery uses the installed FFmpeg and the existing local Pillow runtime. This version targets this Mac and its already validated engine installation. It is not a newly signed/distributed standalone application. Large film renders are local work, and Codex director requests use the limits of your existing account.

## Files and reproducibility

`projects/*.film.json` are the reusable typed starting documents. `film_studio/` contains the shared compiler, native controls, director adapter and render/delivery pipeline. `blender_entry.py` is the isolated worker. `dev_run.py` and `final_run.py` are bounded research runners; they preserve fresh candidates and do not modify old evidence.

The completed movies and editable starting blends are placed in `../output/personal-film-studio/`. Original development failures and formal provenance remain in the project's `experiments/personal-films/` records and corresponding bounded work roots.
