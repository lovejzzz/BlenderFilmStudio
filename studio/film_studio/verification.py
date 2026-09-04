"""Behavior checks on the actual Blender world, not only input hashes."""
import copy,json
from pathlib import Path
import bpy
from . import core,scene

def world_state(sc):
    doc=scene.load_document(sc);frames=[1,73,150,177,300,doc['simulation_end']]
    poses=scene.semantic_state(sc,frames)['states']
    poses={f:{name:mat for name,mat in objects.items() if bpy.data.objects[name].type=='MESH'} for f,objects in poses.items()}
    geometry={o.name:core.digest([[round(v.co.x,8),round(v.co.y,8),round(v.co.z,8)] for v in o.data.vertices]) for o in sc.objects if o.type=='MESH'}
    return {'poses':poses,'geometry':geometry}

def exercise(sc,out):
    before=world_state(sc);original=copy.deepcopy(scene.load_document(sc));results=[]
    for note in ['closer','warmer','later cut']:
        d=scene.load_document(sc);p=core.quick_proposal(d,note,'S04' if note=='later cut' else 'S02');scene.revise(sc,p)
        if world_state(sc)!=before:raise AssertionError('Actual mesh state changed after '+note)
        results.append({'note':note,'worldPreserved':True})
    try:scene.revise(sc,p)
    except core.StudioError:results.append({'staleRejected':True})
    else:raise AssertionError('Stale proposal accepted')
    for _ in range(3):scene.undo(sc)
    restored=copy.deepcopy(scene.load_document(sc));restored['revision']=original['revision']
    if restored!=original or world_state(sc)!=before:raise AssertionError('Undo did not restore original semantics')
    # Register the actual native surface in a worker to catch Blender RNA errors.
    from . import ui
    ui.register();ui.unregister()
    bpy.context.preferences.filepaths.file_preview_type='NONE';bpy.ops.wm.save_as_mainfile(filepath=str(Path(out)/'project.blend'),check_existing=False)
    return {'checks':results,'undoRestoresSemantics':True,'nativeUIRegisters':True,'world':before,'document':scene.load_document(sc),'pointCacheBaked':bool(sc.rigidbody_world and sc.rigidbody_world.point_cache.is_baked)}
