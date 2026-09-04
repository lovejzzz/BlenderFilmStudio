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
    elif job['action']=='inspect':result=scene.semantic_state(bpy.context.scene)
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
    result['status']='PASS'
    (out/'result.json').write_text(json.dumps(result,indent=2))
except Exception:
    (out/'failure.txt').write_text(traceback.format_exc())
    traceback.print_exc();sys.exit(2)
