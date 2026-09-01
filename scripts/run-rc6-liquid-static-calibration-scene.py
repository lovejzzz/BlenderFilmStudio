#!/usr/bin/env python3
"""Measure pre-contact Mantaflow volume drift from a retained RC6 scene."""

import argparse
import bmesh
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def self_hash(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def write_exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def arguments():
    values = sys.argv[sys.argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--resolution", type=int, required=True)
    parser.add_argument("--frame-end", type=int, required=True)
    parser.add_argument("--particle-radius", type=float, required=True)
    parser.add_argument("--particle-number", type=int, required=True)
    return parser.parse_args(values)


def fluid_quality(domain):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = domain.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        vertex_count = len(mesh.vertices)
        if not vertex_count:
            return {
                "vertexCount": 0,
                "connectedComponentCount": 0,
                "largestComponentFraction": 0.0,
                "meshVolumeCubicMeters": 0.0,
                "meshSurfaceAreaSquareMeters": 0.0,
                "nonManifoldEdgeCount": 0,
            }
        parent = list(range(vertex_count))
        sizes = [1] * vertex_count

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(a, b):
            root_a, root_b = find(a), find(b)
            if root_a == root_b:
                return
            if sizes[root_a] < sizes[root_b]:
                root_a, root_b = root_b, root_a
            parent[root_b] = root_a
            sizes[root_a] += sizes[root_b]

        for edge in mesh.edges:
            union(edge.vertices[0], edge.vertices[1])
        components = {}
        for index in range(vertex_count):
            root = find(index)
            components[root] = components.get(root, 0) + 1

        bm = bmesh.new()
        bm.from_mesh(mesh)
        non_manifold = sum(1 for edge in bm.edges if len(edge.link_faces) != 2)
        volume = abs(bm.calc_volume(signed=True)) if non_manifold == 0 else 0.0
        bm.free()
        return {
            "vertexCount": vertex_count,
            "connectedComponentCount": len(components),
            "largestComponentFraction": round(max(components.values()) / vertex_count, 8),
            "meshVolumeCubicMeters": round(volume, 10),
            "meshSurfaceAreaSquareMeters": round(sum(face.area for face in mesh.polygons), 10),
            "nonManifoldEdgeCount": non_manifold,
        }
    finally:
        evaluated.to_mesh_clear()


def main():
    args = arguments()
    work_root = Path(args.work_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    cache_root = work_root / args.cell_id / "mantaflow-cache"
    result_path = evidence_root / "cells" / args.cell_id / "result.json"
    if cache_root.exists() or result_path.exists():
        raise RuntimeError("calibration cell roots are not fresh")
    if args.frame_end != 7 or args.resolution != 96 or args.particle_number != 2:
        raise RuntimeError("calibration cell configuration is outside frozen matrix")
    if args.particle_radius not in {1.0, 1.1, 1.2, 1.3}:
        raise RuntimeError("particle radius is outside frozen matrix")

    scene = bpy.context.scene
    domain = bpy.data.objects.get("PHYS_LIQUID_DOMAIN")
    cup = bpy.data.objects.get("PHYS_OPEN_TUMBLER")
    source = bpy.data.objects.get("PHYS_INITIAL_LIQUID_VOLUME")
    if domain is None or cup is None or source is None:
        raise RuntimeError("retained RC6 scene identity is incomplete")
    domain_modifier = next((item for item in domain.modifiers if item.type == "FLUID" and item.fluid_type == "DOMAIN"), None)
    cup_modifier = next((item for item in cup.modifiers if item.type == "FLUID" and item.fluid_type == "EFFECTOR"), None)
    flow_modifier = next((item for item in source.modifiers if item.type == "FLUID" and item.fluid_type == "FLOW"), None)
    if domain_modifier is None or cup_modifier is None or flow_modifier is None:
        raise RuntimeError("retained RC6 fluid modifier identity is incomplete")
    settings = domain_modifier.domain_settings
    if settings.domain_type != "LIQUID" or settings.simulation_method != "APIC" or flow_modifier.flow_settings.flow_behavior != "GEOMETRY":
        raise RuntimeError("retained RC6 fluid semantic identity mismatch")

    started = time.monotonic()
    scene.frame_start = 1
    scene.frame_end = args.frame_end
    settings.cache_type = "MODULAR"
    settings.cache_directory = str(cache_root)
    settings.cache_frame_start = 1
    settings.cache_frame_end = args.frame_end
    settings.resolution_max = args.resolution
    settings.use_adaptive_timesteps = True
    settings.timesteps_min = 1
    settings.timesteps_max = 4
    settings.cfl_condition = 2.0
    settings.particle_number = args.particle_number
    settings.particle_radius = args.particle_radius
    settings.use_mesh = True
    settings.mesh_scale = 2
    settings.mesh_particle_radius = 2.0
    settings.use_fractions = True
    settings.use_viscosity = True
    settings.viscosity_base = 1.0
    settings.viscosity_exponent = 6
    cup_modifier.effector_settings.subframes = 0

    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    domain.select_set(True)
    bpy.context.view_layer.objects.active = domain
    with bpy.context.temp_override(object=domain, active_object=domain, selected_objects=[domain], selected_editable_objects=[domain]):
        bpy.ops.fluid.bake_data()
        bpy.ops.fluid.bake_mesh()

    samples = []
    for frame in range(1, args.frame_end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        row = fluid_quality(domain)
        row["frame"] = frame
        samples.append(row)
    initial_volume = samples[0]["meshVolumeCubicMeters"]
    if initial_volume <= 0.0:
        raise RuntimeError("static calibration produced no closed initial liquid volume")
    drift = [row["meshVolumeCubicMeters"] / initial_volume - 1.0 for row in samples]
    result = {
        "schemaVersion": "bfs.rc6LiquidStaticCalibrationCell.v0.1",
        "status": "MEASURED",
        "cellId": args.cell_id,
        "configuration": {
            "frameStart": 1,
            "frameEnd": args.frame_end,
            "preContactOnly": true,
            "resolutionMax": args.resolution,
            "particleNumber": args.particle_number,
            "particleRadius": args.particle_radius,
            "meshScale": 2,
            "meshParticleRadius": 2.0,
            "simulationMethod": "APIC",
            "timestepsMin": 1,
            "timestepsMax": 4,
            "cflCondition": 2.0,
            "waterViscosityBase": 1.0,
            "waterViscosityExponent": 6,
            "cupEffectorSubframes": 0
        },
        "metrics": {
            "initialVolumeCubicMeters": initial_volume,
            "finalVolumeCubicMeters": samples[-1]["meshVolumeCubicMeters"],
            "maximumAbsoluteVolumeDriftFraction": round(max(abs(value) for value in drift), 8),
            "maximumConnectedComponentCount": max(row["connectedComponentCount"] for row in samples),
            "minimumLargestComponentFraction": min(row["largestComponentFraction"] for row in samples),
            "maximumNonManifoldEdgeCount": max(row["nonManifoldEdgeCount"] for row in samples),
            "wallSeconds": round(time.monotonic() - started, 6)
        },
        "samples": samples,
        "authority": {
            "renderCalls": 0,
            "networkCalls": 0,
            "authoredCupOutcomeKeys": 0,
            "sourceFlowBehavior": "GEOMETRY"
        }
    }
    result["resultHash"] = self_hash(result, "resultHash")
    write_exclusive(result_path, result)
    print("RC6_STATIC_CALIBRATION=" + canonical({"cellId": args.cell_id, "resultHash": result["resultHash"], "metrics": result["metrics"]}), flush=True)


if __name__ == "__main__":
    main()
