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

def difference(before,after):
    return [{'frame':f,'object':name,'index':i,'before':v,'after':after['poses'][f][name][i],'delta':after['poses'][f][name][i]-v} for f,objects in before['poses'].items() for name,mat in objects.items() for i,v in enumerate(mat) if v!=after['poses'][f][name][i]]


def exercise(sc,out):
    before=world_state(sc);original=copy.deepcopy(scene.load_document(sc));results=[]
    for note in ['closer','warmer','later cut']:
        d=scene.load_document(sc);p=core.quick_proposal(d,note,'S04' if note=='later cut' else 'S02');scene.revise(sc,p)
        after=world_state(sc)
        (Path(out)/('revision-'+note.replace(' ','-')+'.json')).write_text(json.dumps({'geometryEqual':after['geometry']==before['geometry'],'differences':difference(before,after),'pointCacheBaked':bool(sc.rigidbody_world and sc.rigidbody_world.point_cache.is_baked)},indent=2))
        if after!=before:raise AssertionError('Actual mesh state changed after '+note)
        results.append({'note':note,'worldPreserved':True})
    try:scene.revise(sc,p)
    except core.StudioError:results.append({'staleRejected':True})
    else:raise AssertionError('Stale proposal accepted')
    for _ in range(3):scene.undo(sc)
    restored=copy.deepcopy(scene.load_document(sc));restored['revision']=original['revision']
    if restored!=original or world_state(sc)!=before:raise AssertionError('Undo did not restore original semantics')
    for sweep in range(12):
        repeated=world_state(sc)
        if repeated!=before:
            (Path(out)/f'jump-sweep-{sweep}.json').write_text(json.dumps(difference(before,repeated),indent=2))
            raise AssertionError('Random-access solved-state sweep differs')
    results.append({'randomAccessSweeps':12,'allExact':True})
    # Register the actual native surface in a worker to catch Blender RNA errors.
    from . import ui
    ui.register();sc.pf_shot='S02';original_cameras={o.name for o in sc.objects if o.type=='CAMERA'}
    outcome=bpy.ops.pf.coverage()
    after=world_state(sc)
    differences=[]
    for frame,objects in before['poses'].items():
        for name,mat in objects.items():
            other=after['poses'][frame][name]
            if mat!=other:differences.append({'frame':frame,'object':name,'before':mat,'after':other})
    (Path(out)/'coverage-diagnostic.json').write_text(json.dumps({'operator':list(outcome),'shotCount':len(scene.load_document(sc)['shots']),'geometryEqual':before['geometry']==after['geometry'],'pointCacheBaked':bool(sc.rigidbody_world and sc.rigidbody_world.point_cache.is_baked),'poseDifferences':differences},indent=2))
    if outcome!={'FINISHED'} or len(scene.load_document(sc)['shots'])!=len(original['shots'])+1 or after!=before:raise AssertionError('New coverage changed world or failed')
    scene.undo(sc)
    if {o.name for o in sc.objects if o.type=='CAMERA'}!=original_cameras or world_state(sc)!=before:raise AssertionError('Coverage undo left a changed scene')
    if sc.camera is None:raise AssertionError('Undo left no active camera')
    results.append({'newCoverageAndUndo':True});ui.unregister()
    bpy.context.preferences.filepaths.file_preview_type='NONE';bpy.ops.wm.save_as_mainfile(filepath=str(Path(out)/'project.blend'),check_existing=False)
    return {'checks':results,'undoRestoresSemantics':True,'nativeUIRegisters':True,'world':before,'document':scene.load_document(sc),'pointCacheBaked':bool(sc.rigidbody_world and sc.rigidbody_world.point_cache.is_baked)}
