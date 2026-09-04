"""Native director workspace. Blender changes stay on its main thread."""
import json,threading,queue,uuid,subprocess,os,time,shutil
from pathlib import Path
import bpy
from bpy.props import StringProperty,EnumProperty,IntProperty
from . import core,scene,director

_mailbox=queue.Queue();_busy=False;_render_job=None
_shot_cache={}

def shot_items(self,context):
    if not context or 'pf_document' not in context.scene:return [('NONE','Open a film','')]
    doc=scene.load_document(context.scene);key=core.digest(doc)
    if key not in _shot_cache:_shot_cache[key]=[(s['id'],s['id']+' · '+s['label'],'') for s in doc['shots']]
    return _shot_cache[key]

def workspace():
    path=Path.home()/'Movies'/'Personal Film Studio';path.mkdir(parents=True,exist_ok=True);return path

def set_status(text):bpy.context.scene.pf_status=text

def poll():
    global _busy,_render_job
    if _render_job:
        proc,root,started,log,err=_render_job;done=proc.poll()
        if time.monotonic()-started>7200 and done is None:proc.terminate();set_status('Render reached its two-hour limit; completed frames are retained')
        if done is not None:
            log.close();err.close();_render_job=None
            if done==0:set_status('Movie ready in '+str(root/'output/delivery'))
            else:set_status('Render stopped. Completed frames and job logs are retained.')
        else:
            count=len(list((root/'output/frames').glob('frame-*.json')))
            set_status(f'Rendering movie · {count} frames finished')
    try:
        ok,value=_mailbox.get_nowait();_busy=False
        if ok:bpy.context.scene.pf_pending=core.canonical(value);set_status(value['reason'])
        else:set_status(str(value))
        for screen in bpy.data.screens:
            for area in screen.areas:area.tag_redraw()
    except queue.Empty:pass
    return .3

class PF_OT_select(bpy.types.Operator):
    bl_idname='pf.select_shot';bl_label='Go to shot'
    def execute(self,context):
        try:
            doc=scene.load_document(context.scene);i=next(i for i,s in enumerate(doc['shots']) if s['id']==context.scene.pf_shot)
            scene.select_shot(context.scene,i);set_status('Shot ready · Space to play');return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_coverage(bpy.types.Operator):
    bl_idname='pf.coverage';bl_label='Add coverage shot';bl_description='Split this shot into two camera angles while preserving its duration and world'
    def execute(self,context):
        try:
            fresh=scene.add_coverage(context.scene,context.scene.pf_shot);context.scene.pf_shot=fresh['id']
            doc=scene.load_document(context.scene);scene.select_shot(context.scene,next(i for i,s in enumerate(doc['shots']) if s['id']==fresh['id']))
            set_status('New camera angle ready · direct it, or Undo revision');return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_quick(bpy.types.Operator):
    bl_idname='pf.quick';bl_label='Quick adjustment'
    note:StringProperty()
    def execute(self,context):
        try:
            doc=scene.load_document(context.scene);p=core.quick_proposal(doc,self.note,context.scene.pf_shot);scene.revise(context.scene,p);set_status('Applied: '+self.note);return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_direct(bpy.types.Operator):
    bl_idname='pf.direct';bl_label='Ask AI Director';bl_description='Use your existing Codex sign-in to propose one shot change'
    @classmethod
    def poll(cls,context):return not _busy
    def execute(self,context):
        global _busy
        doc=scene.load_document(context.scene);note=context.scene.pf_note;shot=context.scene.pf_shot
        if not note.strip():self.report({'ERROR'},'Write a director note first');return {'CANCELLED'}
        _busy=True;context.scene.pf_pending='';set_status('Director is considering the shot…')
        root=workspace()/'director-jobs'/uuid.uuid4().hex
        def work():
            try:_mailbox.put((True,director.propose(doc,note,shot,root)))
            except Exception as e:_mailbox.put((False,str(e)))
        threading.Thread(target=work,daemon=True).start();return {'FINISHED'}

class PF_OT_apply(bpy.types.Operator):
    bl_idname='pf.apply';bl_label='Apply proposed change'
    def execute(self,context):
        try:
            proposal=json.loads(context.scene.pf_pending);scene.revise(context.scene,proposal);context.scene.pf_pending='';set_status('Applied · compare the shot, or Undo revision');return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_undo(bpy.types.Operator):
    bl_idname='pf.undo';bl_label='Undo revision'
    def execute(self,context):
        try:scene.undo(context.scene);set_status('Previous direction restored');return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_save(bpy.types.Operator):
    bl_idname='pf.save_version';bl_label='Save a new version'
    def execute(self,context):
        try:
            doc=scene.load_document(context.scene);folder=workspace()/doc['id'];folder.mkdir(parents=True,exist_ok=True)
            filename=folder/f"{doc['id']}-r{doc['revision']:04d}-{uuid.uuid4().hex[:8]}.blend"
            bpy.context.preferences.filepaths.file_preview_type='NONE';bpy.ops.wm.save_as_mainfile(filepath=str(filename),check_existing=False)
            filename.with_suffix('.film.json').write_text(json.dumps(doc,indent=2));set_status('Saved '+filename.name);return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_preview(bpy.types.Operator):
    bl_idname='pf.preview';bl_label='Render this frame'
    def execute(self,context):
        scene.configure_render(context.scene,1280,48);scene.update_look(context.scene,scene.load_document(context.scene))
        bpy.ops.render.render('INVOKE_DEFAULT');return {'FINISHED'}

class PF_OT_movie(bpy.types.Operator):
    bl_idname='pf.movie';bl_label='Render finished movie';bl_description='Render all shots at 1920 pixels with original sound'
    @classmethod
    def poll(cls,context):return _render_job is None and 'pf_document' in context.scene
    def execute(self,context):
        global _render_job
        try:
            if shutil.disk_usage(workspace()).free<12*2**30:raise core.StudioError('Keep at least 12 GB free for the movie')
            root=workspace()/'renders'/uuid.uuid4().hex;root.mkdir(parents=True)
            snapshot=root/'project.blend';bpy.context.preferences.filepaths.file_preview_type='NONE'
            bpy.ops.wm.save_as_mainfile(filepath=str(snapshot),copy=True,check_existing=False)
            job={'action':'render','output':str(root/'output'),'stills':[],'width':1920,'samples':96,'maximum_new_frames':1200,'encode':True}
            path=root/'job.json';path.write_text(json.dumps(job))
            env=os.environ.copy()
            for key in ['CONFIG','SCRIPTS','DATAFILES','EXTENSIONS']:
                d=root/('user_'+key.lower());d.mkdir();env['BLENDER_USER_'+key]=str(d)
            log=(root/'stdout.log').open('x');err=(root/'stderr.log').open('x')
            argv=[bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec','--python-exit-code','2',str(snapshot),'--python',str(Path(__file__).parents[1]/'blender_entry.py'),'--',str(path)]
            proc=subprocess.Popen(argv,env=env,stdout=log,stderr=err);_render_job=(proc,root,time.monotonic(),log,err);context.scene['pf_last_render']=str(root)
            set_status('Rendering in the background · you can keep directing');return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_resume(bpy.types.Operator):
    bl_idname='pf.resume_movie';bl_label='Resume last movie'
    @classmethod
    def poll(cls,context):return _render_job is None and bool(context.scene.get('pf_last_render'))
    def execute(self,context):
        global _render_job
        try:
            root=Path(context.scene['pf_last_render']);snapshot=root/'project.blend';path=root/'job.json'
            if not snapshot.is_file() or not path.is_file():raise core.StudioError('Last render snapshot is unavailable')
            env=os.environ.copy()
            for key in ['CONFIG','SCRIPTS','DATAFILES','EXTENSIONS']:env['BLENDER_USER_'+key]=str(root/('user_'+key.lower()))
            attempt=uuid.uuid4().hex[:8];log=(root/f'resume-{attempt}.stdout.log').open('x');err=(root/f'resume-{attempt}.stderr.log').open('x')
            argv=[bpy.app.binary_path,'--background','--factory-startup','--disable-autoexec','--python-exit-code','2',str(snapshot),'--python',str(Path(__file__).parents[1]/'blender_entry.py'),'--',str(path)]
            proc=subprocess.Popen(argv,env=env,stdout=log,stderr=err);_render_job=(proc,root,time.monotonic(),log,err);return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}

class PF_OT_render_folder(bpy.types.Operator):
    bl_idname='pf.render_folder';bl_label='Open movie folder'
    def execute(self,context):
        root=context.scene.get('pf_last_render')
        if root:subprocess.Popen(['/usr/bin/open',root])
        else:self.report({'INFO'},'Render a movie first')
        return {'FINISHED'}

class PF_PT_director(bpy.types.Panel):
    bl_label='Personal Film Studio';bl_idname='PF_PT_director';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Film Studio'
    def draw(self,context):
        lay=self.layout;sc=context.scene
        if 'pf_document' not in sc:
            lay.label(text='Open one of your film projects.',icon='FILE_FOLDER');lay.operator('wm.open_mainfile',text='Open film…');return
        doc=scene.load_document(sc);lay.operator('wm.open_mainfile',text='Open another film…',icon='FILE_FOLDER');lay.label(text=doc['title'],icon='SEQUENCE');lay.label(text=f"Revision {doc['revision']} · {sum(s['duration'] for s in doc['shots'])/24:.0f} seconds")
        box=lay.box();box.label(text='Shots');box.prop(sc,'pf_shot',text='');box.operator('pf.select_shot',icon='CAMERA_DATA');box.operator('pf.coverage',icon='ADD')
        row=box.row(align=True)
        for label,note in [('Closer','closer'),('Wider','wider')]:op=row.operator('pf.quick',text=label);op.note=note
        row=box.row(align=True)
        for label,note in [('Warmer','warmer'),('Cooler','cooler')]:op=row.operator('pf.quick',text=label);op.note=note
        box=lay.box();box.label(text='Direct the shot');box.prop(sc,'pf_note',text='');box.operator('pf.direct',icon='LIGHT')
        if sc.pf_pending:
            p=json.loads(sc.pf_pending);box.label(text=f"{p['shot']} · {p['operation']} → {p['value']:g}")
            box.operator('pf.apply',icon='CHECKMARK')
        if sc.pf_status:
            import textwrap
            for line in textwrap.wrap(sc.pf_status,38):box.label(text=line)
        lay.operator('pf.undo',icon='LOOP_BACK');lay.separator();lay.operator('pf.preview',icon='RENDER_STILL');lay.operator('pf.save_version',icon='FILE_TICK');lay.operator('pf.movie',icon='RENDER_ANIMATION');lay.operator('pf.resume_movie',icon='FILE_REFRESH');lay.operator('pf.render_folder',icon='FILE_FOLDER')
        lay.label(text='Space: playback · N: hide this panel')

CLASSES=[PF_OT_select,PF_OT_coverage,PF_OT_quick,PF_OT_direct,PF_OT_apply,PF_OT_undo,PF_OT_save,PF_OT_preview,PF_OT_movie,PF_OT_resume,PF_OT_render_folder,PF_PT_director]
def register():
    for c in CLASSES:bpy.utils.register_class(c)
    bpy.types.Scene.pf_shot=EnumProperty(name='Shot',items=shot_items)
    bpy.types.Scene.pf_note=StringProperty(name='Director note',default='',maxlen=2000)
    bpy.types.Scene.pf_pending=StringProperty(default='')
    bpy.types.Scene.pf_status=StringProperty(default='')
    bpy.app.timers.register(poll,persistent=True)
    if 'pf_document' in bpy.context.scene:bpy.context.scene.pf_shot=scene.load_document(bpy.context.scene)['shots'][0]['id']
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.show_region_ui=True;space.region_3d.view_perspective='CAMERA';space.region_3d.view_camera_zoom=24;space.overlay.show_overlays=False
                space.shading.type='MATERIAL';space.shading.use_scene_world=True;space.shading.use_scene_lights=True

def unregister():
    if bpy.app.timers.is_registered(poll):bpy.app.timers.unregister(poll)
    for c in reversed(CLASSES):bpy.utils.unregister_class(c)
    for name in ['pf_shot','pf_note','pf_pending','pf_status']:
        if hasattr(bpy.types.Scene,name):delattr(bpy.types.Scene,name)
