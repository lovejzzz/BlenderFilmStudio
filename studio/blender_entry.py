"""Isolated worker. Every invocation receives one immutable job document."""
import sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import bpy
from film_studio import core,scene
job=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
out=Path(job['output']);out.mkdir(exist_ok=True)
try:
    result={}
    if job['action']=='build':
        doc=core.validate(json.loads(Path(job['project']).read_text()))
        result=scene.build(doc,out/'project.blend')
    elif job['action']=='editorial':
        sc=bpy.context.scene;old=scene.load_document(sc);new=core.validate(json.loads(Path(job['project']).read_text()))
        if core.protected_world(old)!=core.protected_world(new):raise core.StudioError('Editorial import changed world inputs')
        scene.ranges(new,json.loads(sc['pf_events']));scene.store_document(sc,new)
        for shot in new['shots']:scene.update_camera(sc,shot)
        scene.update_look(sc,new);scene.select_shot(sc,0)
        bpy.context.preferences.filepaths.file_preview_type='NONE';bpy.ops.wm.save_as_mainfile(filepath=str(out/'project.blend'),check_existing=False)
        result={'events':json.loads(sc['pf_events']),'ranges':scene.ranges(new,json.loads(sc['pf_events'])),'worldPreserved':True}
    elif job['action']=='inspect':
        from film_studio.verification import world_state
        result={'world':world_state(bpy.context.scene),'document':scene.load_document(bpy.context.scene)}
    elif job['action']=='exercise':
        from film_studio.verification import exercise
        result=exercise(bpy.context.scene,out)
    elif job['action']=='resume_test':
        from film_studio.rendering import render,sha
        sc=bpy.context.scene;root=out/'frames'
        first=render(sc,root,640,16,['S01'],1);h=sha(root/'frame-00001.png')
        second=render(sc,root,640,16,['S01'],2)
        if first['created']!=1 or second['created']!=2 or second['reused']!=1 or sha(root/'frame-00001.png')!=h:raise AssertionError('Resume prefix failed')
        try:render(sc,root,800,16,['S01'],0)
        except core.StudioError:pass
        else:raise AssertionError('Mismatched profile accepted')
        result={'first':first,'second':second,'completedFrameUnchanged':True,'mismatchedProfileRejected':True}
    elif job['action']=='render':
        from film_studio.rendering import render
        result=render(bpy.context.scene,out/'frames',job.get('width',640),job.get('samples',16),job.get('shots'),job.get('maximum_new_frames'))
    if job.get('stills'):
        sc=bpy.context.scene;doc=scene.load_document(sc)
        scene.configure_render(sc,job.get('width',1280),job.get('samples',48));scene.update_look(sc,doc)
        result['renders']=[]
        for sid in job['stills']:
            idx=next(i for i,s in enumerate(doc['shots']) if s['id']==sid)
            shot=scene.select_shot(sc,idx);start,end=scene.shot_range(sc,shot);frame=(start+end)//2;sc.frame_set(frame)
            target=out/(sid+'.png')
            if target.exists():raise RuntimeError('Output already exists')
            sc.render.filepath=str(target);bpy.ops.render.render(write_still=True)
            result['renders'].append({'shot':sid,'frame':frame,'path':str(target)})
    if job.get('encode'):
        from film_studio.delivery import encode
        result['delivery']=encode(bpy.context.scene,out/'frames',out/'delivery')
    result['status']='PASS'
    (out/'result.json').write_text(json.dumps(result,indent=2))
except Exception:
    (out/'failure.txt').write_text(traceback.format_exc())
    traceback.print_exc();sys.exit(2)
