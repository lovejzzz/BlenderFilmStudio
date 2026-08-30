#!/usr/bin/env python3

"""Frozen Blender-side persistence and negative-control checks for F0.3."""

import json
import sys
from datetime import datetime, timezone

import bpy


SCHEMA_VERSION = "bfs.filmWorkspace.v0.1"


def parse_args(argv):
    try:
        separator = argv.index("--")
    except ValueError as error:
        raise RuntimeError("Missing Blender argument separator") from error
    values = argv[separator + 1:]
    if len(values) % 2:
        raise RuntimeError("Expected paired audit arguments")
    parsed = {}
    for index in range(0, len(values), 2):
        key = values[index]
        if not key.startswith("--"):
            raise RuntimeError(f"Expected --name, observed {key}")
        parsed[key[2:]] = values[index + 1]
    return parsed


def operation_result(value):
    return sorted(value)


def workspace_snapshot():
    scene = bpy.context.scene
    state = scene.film_studio
    active = bpy.context.view_layer.objects.active
    return {
        "schemaVersion": state.schema_version,
        "project": {
            "identifier": state.project.identifier,
            "name": state.project.name,
        },
        "scene": {
            "identifier": state.story_scene.identifier,
            "name": state.story_scene.name,
        },
        "character": {
            "identifier": state.character.identifier,
            "name": state.character.name,
        },
        "shots": [
            {
                "identifier": shot.identifier,
                "name": shot.name,
                "camera": shot.camera.name if shot.camera else None,
            }
            for shot in state.shots
        ],
        "activeShotIndex": state.active_shot_index,
        "expertMode": state.expert_mode,
        "sceneCamera": scene.camera.name if scene.camera else None,
        "activeObject": active.name if active else None,
        "selectedObjects": sorted(obj.name for obj in bpy.context.selected_objects),
        "operatorAvailable": hasattr(bpy.ops.film_studio, "create_shot"),
        "filepath": bpy.data.filepath,
    }


def default_checks(snapshot):
    return {
        "schemaExact": snapshot["schemaVersion"] == SCHEMA_VERSION,
        "projectExact": snapshot["project"] == {
            "identifier": "PRJ_REMAINDER",
            "name": "Remainder",
        },
        "sceneExact": snapshot["scene"] == {
            "identifier": "SC01",
            "name": "The Room",
        },
        "characterExact": snapshot["character"] == {
            "identifier": "CHR_GUARDIAN",
            "name": "Guardian",
        },
        "operatorAvailable": snapshot["operatorAvailable"],
    }


def shot_checks(snapshot):
    return {
        "oneShot": snapshot["shots"] == [{
            "identifier": "SH010",
            "name": "WIDE",
            "camera": "SHOT_SH010_WIDE",
        }],
        "activeShotExact": snapshot["activeShotIndex"] == 0,
        "sceneCameraExact": snapshot["sceneCamera"] == "SHOT_SH010_WIDE",
        "activeObjectExact": snapshot["activeObject"] == "SHOT_SH010_WIDE",
        "cameraSelected": snapshot["selectedObjects"] == ["SHOT_SH010_WIDE"],
    }


def require(checks, label):
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"{label} failed: {','.join(failed)}")


def write_exclusive(path, value):
    with open(path, "x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main():
    args = parse_args(sys.argv)
    stage = args["stage"]
    output = args["output"]
    blend_path = args["blend"]
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    before = workspace_snapshot()
    operations = {}

    if stage == "create-save":
        initial = default_checks(before)
        initial.update({
            "noShotsInitially": before["shots"] == [],
            "noActiveShotInitially": before["activeShotIndex"] == -1,
            "filmModeInitially": before["expertMode"] is False,
        })
        require(initial, "initial workspace")
        operations["createShot"] = operation_result(bpy.ops.film_studio.create_shot())
        require({"createFinished": operations["createShot"] == ["FINISHED"]}, "create operator")
        after = workspace_snapshot()
        created = default_checks(after)
        created.update(shot_checks(after))
        require(created, "created workspace")
        operations["save"] = operation_result(bpy.ops.wm.save_as_mainfile(filepath=blend_path))
        require({"saveFinished": operations["save"] == ["FINISHED"]}, "save operator")
        final = workspace_snapshot()
        checks = {**initial, **created, "savedAtExactPath": final["filepath"] == blend_path}
    elif stage == "reopen":
        final = workspace_snapshot()
        checks = default_checks(final)
        checks.update(shot_checks(final))
        checks.update({
            "reopenedExactPath": final["filepath"] == blend_path,
            "filmModePersisted": final["expertMode"] is False,
        })
        require(checks, "reopened workspace")
    elif stage == "missing-prepare":
        loaded = default_checks(before)
        loaded.update(shot_checks(before))
        require(loaded, "negative-control source")
        cameras = [shot.camera for shot in bpy.context.scene.film_studio.shots if shot.camera]
        bpy.context.scene.film_studio.shots.clear()
        bpy.context.scene.film_studio.active_shot_index = -1
        bpy.context.scene.camera = None
        for camera in cameras:
            if camera and camera.name in bpy.data.objects:
                bpy.data.objects.remove(camera, do_unlink=True)
        operations["save"] = operation_result(bpy.ops.wm.save_as_mainfile(filepath=blend_path))
        require({"saveFinished": operations["save"] == ["FINISHED"]}, "negative-control save")
        final = workspace_snapshot()
        checks = default_checks(final)
        checks.update({
            "shotsRemoved": final["shots"] == [],
            "activeShotCleared": final["activeShotIndex"] == -1,
            "sceneCameraCleared": final["sceneCamera"] is None,
            "savedAtExactPath": final["filepath"] == blend_path,
        })
        require(checks, "missing optional state preparation")
    elif stage == "missing-reopen":
        missing = default_checks(before)
        missing.update({
            "reopenedExactPath": before["filepath"] == blend_path,
            "shotsRemainMissing": before["shots"] == [],
            "activeShotRemainsMissing": before["activeShotIndex"] == -1,
            "sceneCameraRemainsMissing": before["sceneCamera"] is None,
        })
        require(missing, "missing optional state reopen")
        operations["createShot"] = operation_result(bpy.ops.film_studio.create_shot())
        require({"createFinished": operations["createShot"] == ["FINISHED"]}, "recovery operator")
        final = workspace_snapshot()
        recovered = default_checks(final)
        recovered.update(shot_checks(final))
        require(recovered, "missing optional state recovery")
        checks = {**missing, **{f"recovery{name[0].upper()}{name[1:]}": value for name, value in recovered.items()}}
    else:
        raise RuntimeError(f"Unsupported stage: {stage}")

    result = {
        "schemaVersion": "bfs.f0WorkspaceBlenderAudit.v0.1",
        "protocol": "F0-SOURCE-FEASIBILITY",
        "gate": "F0.3",
        "stage": stage,
        "status": "PASS",
        "startedAt": started_at,
        "endedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "blendPath": blend_path,
        "before": before,
        "after": final,
        "operations": operations,
        "checks": checks,
        "failures": [],
    }
    write_exclusive(output, result)
    print(f"F03_WORKSPACE_{stage.upper().replace('-', '_')}_PASS")


if __name__ == "__main__":
    main()
