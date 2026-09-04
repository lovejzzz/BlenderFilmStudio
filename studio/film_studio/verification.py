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


def verify_cache(sc,reference):
    from mathutils import Vector
    data=json.loads(Path(reference).read_text());objects={o.name:o for o in sc.objects if o.get('pf_solver_role')};max_position=0;max_rotation=0
    # A coprime permutation exercises large forward/backward jumps, not only playback.
    records=data['frames'];order=[(i*137)%len(records) for i in range(len(records))]
    for index in order:
        record=records[index];scene.set_frame(sc,record['frame']);dg=bpy.context.evaluated_depsgraph_get()
        for name,o in objects.items():
            mat=o.evaluated_get(dg).matrix_world;q=mat.to_quaternion();pos=mat.translation
            max_position=max(max_position,max(abs(pos[i]-record['positions'][name][i]) for i in range(3)))
            expected=record['rotations'][name];same=max(abs(q[i]-expected[i]) for i in range(4));neg=max(abs(q[i]+expected[i]) for i in range(4));max_rotation=max(max_rotation,min(same,neg))
    if max_position>1e-6 or max_rotation>1e-6:raise AssertionError(f'Original cached motion differs: position {max_position}, quaternion {max_rotation}')
    return {'frames':len(records),'bodies':len(objects),'randomAccessOrder':'i*137 modulo frame count','maxPositionErrorMeters':max_position,'maxQuaternionComponentError':max_rotation,'tolerance':1e-6,'pointCacheBaked':sc.rigidbody_world.point_cache.is_baked}
