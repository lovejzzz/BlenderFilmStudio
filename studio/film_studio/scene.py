"""Compile a validated personal-film document into one editable Blender world."""

from __future__ import annotations

import json
import math
from pathlib import Path
import bpy
from mathutils import Vector
from . import core, assets, physics


def store_document(scene,doc):
    scene['pf_document']=core.canonical(doc);scene['pf_revision']=doc['revision'];scene['pf_document_hash']=core.digest(doc)


def load_document(scene):
    return core.validate(json.loads(scene['pf_document']))


def configure_render(scene,width=1280,samples=48,engine='CYCLES'):
    scene.render.engine=engine;scene.render.resolution_x=width;scene.render.resolution_y=round(width/2.35/2)*2;scene.render.resolution_percentage=100
    scene.render.fps=24;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
    if engine=='CYCLES':
        scene.cycles.samples=samples;scene.cycles.use_denoising=True;scene.cycles.use_adaptive_sampling=True;scene.cycles.adaptive_threshold=.025
        scene.cycles.max_bounces=8;scene.cycles.diffuse_bounces=3;scene.cycles.glossy_bounces=4;scene.cycles.transmission_bounces=6
        scene.render.use_persistent_data=True
        prefs=bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type='METAL';prefs.get_devices()
            devices=[d for d in prefs.devices if d.type=='METAL']
            if devices:
                for d in prefs.devices:d.use=d.type=='METAL'
                scene.cycles.device='GPU'
        except (TypeError,RuntimeError):pass
    scene.render.use_file_extension=True;scene.render.film_transparent=False
    if hasattr(scene.render,'use_motion_blur'):scene.render.use_motion_blur=True;scene.render.motion_blur_shutter=.35
    scene.render.use_compositing=False
    # Use the installed display transform; color identity is recorded in receipts.
    candidates=[x.identifier for x in scene.view_settings.bl_rna.properties['view_transform'].enum_items]
    for name in ['AgX','ACES 2.0','Standard']:
        try:scene.view_settings.view_transform=name;break
        except TypeError:continue
    scene.view_settings.exposure=0;scene.view_settings.gamma=1


def shot_range(scene,shot):
    events=json.loads(scene.get('pf_events','{"start":1}'))
    if shot['anchor'] not in events:raise core.StudioError('This world has no measured '+shot['anchor']+' event')
    start=events[shot['anchor']]+shot['offset'];end=start+shot['duration']-1
    doc=load_document(scene)
    if start<1 or end>doc['simulation_end']:raise core.StudioError(f'{shot["id"]} exceeds simulated frame range ({start}-{end})')
    return start,end


def update_camera(scene,shot):
    name='PF_CAMERA_'+shot['id'];obj=bpy.data.objects.get(name)
    if obj is None:
        data=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    obj.animation_data_clear();obj['pf_shot']=shot['id'];obj.data.lens=shot['lens'];obj.data.sensor_width=36
    target=bpy.data.objects[shot['target']]
    bpy.context.view_layer.update();aim=target.matrix_world@Vector(shot['aim_offset'])
    a=math.radians(shot['azimuth']);e=math.radians(shot['elevation']);direction=Vector((math.sin(a)*math.cos(e),-math.cos(a)*math.cos(e),math.sin(e)))
    start,end=shot_range(scene,shot)
    for f,dist in [(start,shot['distance']),(end,shot['distance']*(1-shot['travel']))]:
        obj.location=aim+direction*dist;obj.rotation_euler=(aim-obj.location).to_track_quat('-Z','Y').to_euler();obj.keyframe_insert('location',frame=f);obj.keyframe_insert('rotation_euler',frame=f)
    obj.data.dof.use_dof=True;obj.data.dof.focus_object=None;obj.data.dof.focus_distance=max(.05,shot['distance']+shot['focus_offset']);obj.data.dof.aperture_fstop=shot['fstop'];obj.data.dof.aperture_blades=8
    # Animate focus with the dolly, maintaining its declared subject offset.
    obj.data.animation_data_clear()
    for f,dist in [(start,shot['distance']),(end,shot['distance']*(1-shot['travel']))]:
        obj.data.dof.focus_distance=max(.05,dist+shot['focus_offset']);obj.data.keyframe_insert('dof.focus_distance',frame=f)
    return obj


def update_look(scene,doc):
    scene.view_settings.exposure=doc['world']['exposure']
    for record in doc['lights']:
        o=bpy.data.objects[record['id']];col=list(record['color']);warm=doc['world']['warmth']
        o.data.color=(min(1,max(0,col[0]*(1+.18*warm))),min(1,max(0,col[1])),min(1,max(0,col[2]*(1-.28*warm))))


def build(doc,output):
    core.validate(doc)
    # Called only for a fresh project process or an explicitly new project.
    if bpy.data.filepath:raise core.StudioError('Build a new project in a fresh process to protect the open project')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.name=doc['title'];scene.frame_start=1;scene.frame_end=doc['simulation_end'];scene.render.fps=doc['fps']
    m=assets.palette()
    for a in doc['assets']:assets.build_asset(a,m,doc['simulation_end'])
    w=bpy.data.worlds.new('PF World');w.use_nodes=True;scene.world=w;w.node_tree.nodes['Background'].inputs['Color'].default_value=(*doc['world']['color'],1);w.node_tree.nodes['Background'].inputs['Strength'].default_value=doc['world']['strength']
    for spec in doc['lights']:
        data=bpy.data.lights.new(spec['id'],spec['type']);o=bpy.data.objects.new(spec['id'],data);scene.collection.objects.link(o);o.location=spec['position'];o.rotation_euler=(Vector(spec['target'])-o.location).to_track_quat('-Z','Y').to_euler()
        data.energy=spec['power'];data.color=spec['color'];o['pf_light_role']=spec['role']
        if spec['type']=='AREA':data.shape='DISK';data.size=spec['size']
        elif spec['type']=='SPOT':data.spot_size=math.radians(70);data.spot_blend=.45;data.shadow_soft_size=spec['size']
        else:data.shadow_soft_size=spec['size']
    bpy.context.view_layer.update();events,physical=physics.bake_and_measure(scene,doc['simulation_end'])
    scene['pf_events']=core.canonical(events);store_document(scene,doc)
    scene['pf_history']='[]';scene['pf_project_directory']=str(Path(output).parent)
    for shot in doc['shots']:update_camera(scene,shot)
    scene.camera=bpy.data.objects['PF_CAMERA_'+doc['shots'][0]['id']]
    configure_render(scene);update_look(scene,doc);scene.frame_set(shot_range(scene,doc['shots'][0])[0])
    bpy.context.preferences.filepaths.file_preview_type='NONE'
    bpy.ops.wm.save_as_mainfile(filepath=str(output),check_existing=False)
    return {'documentHash':core.digest(doc),'protectedWorld':core.protected_world(doc),'events':events,'physics':physical,'objects':len(scene.objects),'materials':len(bpy.data.materials),'colorManagement':{'view':scene.view_settings.view_transform,'display':scene.display_settings.display_device}}


def revise(scene,proposal):
    doc=load_document(scene);new=core.apply_patch(doc,proposal)
    # Validate all ranges before changing Blender state.
    events=json.loads(scene['pf_events'])
    for s in new['shots']:
        start=events[s['anchor']]+s['offset']
        if start<1 or start+s['duration']-1>new['simulation_end']:raise core.StudioError('Revision exceeds source timeline')
    history=json.loads(scene.get('pf_history','[]'));history.append(doc);history=history[-24:]
    store_document(scene,new)
    if proposal['operation'] in {'warmth','exposure'}:update_look(scene,new)
    else:update_camera(scene,next(s for s in new['shots'] if s['id']==proposal['shot']))
    scene['pf_history']=core.canonical(history)
    return {'revision':new['revision'],'before':core.digest(doc),'after':core.digest(new),'worldPreserved':core.protected_world(doc)==core.protected_world(new)}


def undo(scene):
    history=json.loads(scene.get('pf_history','[]'))
    if not history:raise core.StudioError('No studio revision to undo')
    old=history.pop();current=load_document(scene);old['revision']=current['revision']+1
    store_document(scene,old);scene['pf_history']=core.canonical(history)
    for shot in old['shots']:update_camera(scene,shot)
    update_look(scene,old);return old


def select_shot(scene,index):
    doc=load_document(scene);shot=doc['shots'][index];start,end=shot_range(scene,shot)
    scene.camera=bpy.data.objects['PF_CAMERA_'+shot['id']];scene.frame_preview_start=start;scene.frame_preview_end=end;scene.use_preview_range=True;scene.frame_set(start)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
    return shot


def semantic_state(scene,frames=None):
    doc=load_document(scene);states={}
    for frame in (frames or [1,doc['simulation_end']//2,doc['simulation_end']]):
        scene.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
        states[str(frame)]={o.name:[round(x,7) for row in o.evaluated_get(dg).matrix_world for x in row] for o in scene.objects if o.type in {'MESH','CAMERA','LIGHT'}}
    return {'document':doc,'events':json.loads(scene['pf_events']),'states':states,'worldHash':core.protected_world(doc)}
