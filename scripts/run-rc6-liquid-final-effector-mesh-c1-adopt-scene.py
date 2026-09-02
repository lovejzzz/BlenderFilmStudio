#!/usr/bin/env python3
"""Adopt an exact copied Mantaflow Data cache into a persisted scene state."""

import argparse
import bmesh
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


EXPECTED_SOURCE_VOLUME = 0.0013283283766941
EXPECTED_SOURCE_DIMENSIONS = (0.1099999994, 0.1099999994, 0.1400000006)
CUP_INTERIOR_BOTTOM_LOCAL_Z = -0.16


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"))
def self_hash(value, field):
    body = dict(value); body.pop(field, None); return hashlib.sha256(canonical(body).encode()).hexdigest()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle: json.dump(value, handle, indent=2, sort_keys=True); handle.write("\n")


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:]
    parser = argparse.ArgumentParser(); parser.add_argument("--cell-id", required=True); parser.add_argument("--work-root", required=True); parser.add_argument("--evidence-root", required=True); parser.add_argument("--retained-data-manifest-hash", required=True)
    return parser.parse_args(values)


def expected_data_files(): return sorted([f"config/config_{frame:04d}.uni" for frame in range(1, 8)] + [f"data/fluid_data_{frame:04d}.vdb" for frame in range(1, 8)])
def cache_roster(root): return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def data_manifest(root):
    files = []
    for relative in expected_data_files():
        path = root / relative
        if not path.is_file() or path.is_symlink(): raise RuntimeError(f"Data adoption file missing or symlinked: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha(path)})
    value = {"schemaVersion": "bfs.rc6LiquidDataManifest.v0.1", "files": files}; value["manifestHash"] = self_hash(value, "manifestHash"); return value


def closed_volume(obj):
    mesh = bmesh.new()
    try:
        mesh.from_mesh(obj.data); mesh.transform(obj.matrix_world)
        if any(len(edge.link_faces) != 2 for edge in mesh.edges): raise RuntimeError("Data adoption source mesh is not closed")
        return abs(mesh.calc_volume(signed=True))
    finally: mesh.free()


def main():
    args = arguments()
    if args.cell_id != "final-effector-mesh-c1": raise RuntimeError("Data adoption cell identity mismatch")
    work_root = Path(args.work_root).resolve(); evidence_root = Path(args.evidence_root).resolve(); cell_root = work_root / args.cell_id; cache_root = cell_root / "mantaflow-cache"; source_blend = cell_root / "source-state.blend"
    if Path(bpy.data.filepath).resolve() != source_blend: raise RuntimeError("Data adoption source blend path mismatch")
    if cache_roster(cache_root) != expected_data_files(): raise RuntimeError("Data adoption initial cache roster mismatch")
    before_manifest = data_manifest(cache_root)
    if before_manifest["manifestHash"] != args.retained_data_manifest_hash: raise RuntimeError("Data adoption initial manifest mismatch")
    scene = bpy.context.scene; domain = bpy.data.objects.get("PHYS_LIQUID_DOMAIN"); cup = bpy.data.objects.get("PHYS_OPEN_TUMBLER"); source = bpy.data.objects.get("PHYS_INITIAL_LIQUID_VOLUME")
    if domain is None or cup is None or source is None: raise RuntimeError("Data adoption scene identity incomplete")
    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None); cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None); flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)
    if domain_modifier is None or cup_modifier is None or flow_modifier is None: raise RuntimeError("Data adoption fluid modifier identity incomplete")
    settings = domain_modifier.domain_settings; effector = cup_modifier.effector_settings; flow = flow_modifier.flow_settings
    if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow.flow_behavior != "GEOMETRY": raise RuntimeError("Data adoption semantic identity mismatch")
    domain.location = (0.32, 0.0, 0.25); domain.dimensions = (0.36, 0.36, 0.5); bpy.ops.object.select_all(action="DESELECT"); domain.select_set(True); bpy.context.view_layer.objects.active = domain; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    scene.frame_start = 1; scene.frame_end = 7; scene.frame_set(1); bpy.context.view_layer.update()
    if abs(closed_volume(source) - EXPECTED_SOURCE_VOLUME) > 1e-10 or any(abs(source.dimensions[index] - EXPECTED_SOURCE_DIMENSIONS[index]) > 1e-8 for index in range(3)): raise RuntimeError("Data adoption source geometry mismatch")
    inner_floor_world_z = (cup.matrix_world @ Vector((0.0, 0.0, CUP_INTERIOR_BOTTOM_LOCAL_Z))).z; source.location.z = inner_floor_world_z + source.dimensions.z * 0.5 + 0.035; bpy.context.view_layer.update(); measured_clearance = source.matrix_world.translation.z - source.dimensions.z * 0.5 - inner_floor_world_z
    if abs(measured_clearance - 0.035) > 1e-8: raise RuntimeError("Data adoption source clearance mismatch")
    initial_flip = bool(settings.use_flip_particles); initial_systems = len(domain.particle_systems)
    if not initial_flip or initial_systems != 1: raise RuntimeError("Data adoption FLIP roster mismatch")
    settings.cache_type = "MODULAR"; settings.cache_frame_start = 1; settings.cache_frame_end = 7; settings.resolution_max = 192; settings.use_adaptive_timesteps = True; settings.timesteps_min = 1; settings.timesteps_max = 4; settings.cfl_condition = 2.0; settings.particle_number = 2; settings.particle_radius = 1.6; settings.use_mesh = False; settings.use_fractions = True; settings.delete_in_obstacle = False; settings.use_viscosity = True; settings.viscosity_base = 1.0; settings.viscosity_exponent = 6; flow.surface_distance = 0.0; effector.surface_distance = 2.5; effector.use_plane_init = False; effector.use_effector = True; effector.subframes = 0
    settings.cache_directory = str(cache_root); bpy.context.view_layer.update()
    if Path(bpy.path.abspath(settings.cache_directory)).resolve() != cache_root or settings.has_cache_baked_data or settings.has_cache_baked_mesh: raise RuntimeError("Data adoption initial cache-state mismatch")
    if cache_roster(cache_root) != expected_data_files() or data_manifest(cache_root) != before_manifest: raise RuntimeError("Data adoption reconstruction changed Data")
    settings.has_cache_baked_data = True
    if not settings.has_cache_baked_data or settings.has_cache_baked_mesh: raise RuntimeError("Data adoption baked flag write/readback mismatch")
    if data_manifest(cache_root) != before_manifest: raise RuntimeError("Data adoption flag changed Data")
    output_blend = cell_root / "data-adopted-state.blend"; settings.cache_directory = "//mantaflow-cache"; bpy.context.preferences.filepaths.file_preview_type = "NONE"; scene.frame_set(1); bpy.ops.wm.save_as_mainfile(filepath=str(output_blend), check_existing=False)
    if not output_blend.is_file() or not settings.has_cache_baked_data or data_manifest(cache_root) != before_manifest: raise RuntimeError("Data adoption saved state mismatch")
    result = {"schemaVersion": "bfs.rc6LiquidFinalEffectorMeshC1Adoption.v0.1", "status": "ADOPTED", "cellId": args.cell_id, "configuration": {"frameStart": 1, "frameEnd": 7, "resolutionMax": 192, "particleNumber": 2, "particleRadius": 1.6, "useMesh": False, "cupEffectorSurfaceDistanceCells": 2.5, "sourceBottomClearanceMeters": round(measured_clearance, 10), "retainedDataManifestHash": before_manifest["manifestHash"]}, "authority": {"cacheStateAdoptions": 1, "fluidDataBakes": 0, "fluidMeshBakes": 0, "blendSaves": 1, "renderCalls": 0, "networkCalls": 0, "engineRemoteWrites": 0}, "adoptedState": {"uri": str(output_blend), "bytes": output_blend.stat().st_size, "sha256": sha(output_blend)}}; result["resultHash"] = self_hash(result, "resultHash")
    write_exclusive(evidence_root / "cells/adoption/result.json", result); print("RC6_FINAL_EFFECTOR_DATA_ADOPT=" + canonical({"status": result["status"], "resultHash": result["resultHash"]}), flush=True)


if __name__ == "__main__": main()
