#!/usr/bin/env python3
"""C3 adoption: materialize verified Data only after scene reconstruction."""

import hashlib
from pathlib import Path

BASE=Path(__file__).resolve().with_name("run-rc6-liquid-final-effector-mesh-c1-adopt-scene.py")
EXPECTED_BASE_SHA256="cc17621e06e6d822e08a44d0b6ba965ffca9c682c786e44c632ea447d3c96c2f"
if hashlib.sha256(BASE.read_bytes()).hexdigest()!=EXPECTED_BASE_SHA256:raise RuntimeError("C3 adoption base identity mismatch")
source=BASE.read_text()
replacements=(
    ('"""Adopt an exact copied Mantaflow Data cache into a persisted scene state."""','"""Materialize exact staged Data after scene reconstruction, then persist state."""',"docstring"),
    ('import json\nimport sys','import json\nimport shutil\nimport sys',"shutil import"),
    ('parser = argparse.ArgumentParser(); parser.add_argument("--cell-id", required=True); parser.add_argument("--work-root", required=True); parser.add_argument("--evidence-root", required=True); parser.add_argument("--retained-data-manifest-hash", required=True)','parser = argparse.ArgumentParser(); parser.add_argument("--cell-id", required=True); parser.add_argument("--work-root", required=True); parser.add_argument("--evidence-root", required=True); parser.add_argument("--retained-data-manifest-hash", required=True); parser.add_argument("--staged-data-root", required=True)',"staged argument"),
    ('    if args.cell_id != "final-effector-mesh-c1": raise RuntimeError("Data adoption cell identity mismatch")','    if args.cell_id != "final-effector-mesh-c3": raise RuntimeError("C3 Data adoption cell identity mismatch")',"cell identity"),
    ('    work_root = Path(args.work_root).resolve(); evidence_root = Path(args.evidence_root).resolve(); cell_root = work_root / args.cell_id; cache_root = cell_root / "mantaflow-cache"; source_blend = cell_root / "source-state.blend"\n    if Path(bpy.data.filepath).resolve() != source_blend: raise RuntimeError("Data adoption source blend path mismatch")\n    if cache_roster(cache_root) != expected_data_files(): raise RuntimeError("Data adoption initial cache roster mismatch")\n    before_manifest = data_manifest(cache_root)','    work_root = Path(args.work_root).resolve(); evidence_root = Path(args.evidence_root).resolve(); cell_root = work_root / args.cell_id; cache_root = cell_root / "mantaflow-cache"; staged_root = Path(args.staged_data_root).resolve(); source_blend = cell_root / "source-state.blend"\n    if Path(bpy.data.filepath).resolve() != source_blend: raise RuntimeError("C3 Data adoption source blend path mismatch")\n    if cache_root.exists() and cache_roster(cache_root): raise RuntimeError("C3 final cache is not empty before reconstruction")\n    if cache_roster(staged_root) != expected_data_files(): raise RuntimeError("C3 staged Data roster mismatch")\n    before_manifest = data_manifest(staged_root)',"staged initial state"),
    ('    if cache_roster(cache_root) != expected_data_files() or data_manifest(cache_root) != before_manifest: raise RuntimeError("Data adoption reconstruction changed Data")\n    settings.has_cache_baked_data = True','    if cache_root.exists() and cache_roster(cache_root): raise RuntimeError("C3 reconstruction populated final cache before materialization")\n    if data_manifest(staged_root) != before_manifest: raise RuntimeError("C3 reconstruction changed staged Data")\n    shutil.copytree(staged_root, cache_root, dirs_exist_ok=True)\n    if cache_roster(cache_root) != expected_data_files() or data_manifest(cache_root) != before_manifest: raise RuntimeError("C3 post-configuration Data materialization mismatch")\n    settings.has_cache_baked_data = True',"post-configuration materialization"),
    ('"authority": {"cacheStateAdoptions": 1, "fluidDataBakes": 0,','"authority": {"stagedDataMaterializations": 1, "cacheStateAdoptions": 1, "fluidDataBakes": 0,',"authority"),
    ('bfs.rc6LiquidFinalEffectorMeshC1Adoption.v0.1','bfs.rc6LiquidFinalEffectorMeshC3Adoption.v0.1',"schema"),
)
for before,after,label in replacements:
    if source.count(before)!=1:raise RuntimeError(f"C3 adoption {label} target mismatch")
    source=source.replace(before,after)
exec(compile(source,str(BASE)+"#MESH_C3_ADOPT_V01","exec"),globals(),globals())
