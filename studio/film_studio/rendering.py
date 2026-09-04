"""Addressable shot renders with exact snapshot/profile binding and frame resume."""
import hashlib,json,time,os,uuid
from pathlib import Path
import bpy
from . import core,scene

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def plan(sc,width=1920,samples=96,shot_ids=None):
    doc=scene.load_document(sc);frames=[]
    for shot in doc['shots']:
        if shot_ids and shot['id'] not in shot_ids:continue
        start,end=scene.shot_range(sc,shot)
        for f in range(start,end+1):frames.append({'index':len(frames)+1,'shot':shot['id'],'sourceFrame':f})
    return {'schema':'personal-film-render/1','documentHash':core.digest(doc),'blendSha256':sha(bpy.data.filepath),'width':width,'samples':samples,'fps':24,'frames':frames}

def render(sc,root,width=1920,samples=96,shot_ids=None,maximum_new_frames=None):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);manifest=root/'render-plan.json';p=plan(sc,width,samples,shot_ids)
    if manifest.exists():
        if json.loads(manifest.read_text())!=p:raise core.StudioError('This render belongs to another project version or quality profile. Choose a new output folder.')
    else:
        with manifest.open('x') as f:json.dump(p,f,indent=2)
    scene.configure_render(sc,width,samples);scene.update_look(sc,scene.load_document(sc));created=0;reused=0
    for spec in p['frames']:
        stem=f"frame-{spec['index']:05d}";target=root/(stem+'.png');receipt=root/(stem+'.json')
        if target.exists() and receipt.exists():
            r=json.loads(receipt.read_text())
            if r.get('sha256')!=sha(target) or r.get('frame')!=spec:raise core.StudioError('Completed frame changed: '+stem)
            reused+=1;continue
        if target.exists() or receipt.exists():
            retained=root/'interrupted'/uuid.uuid4().hex;retained.mkdir(parents=True)
            for partial in [target,receipt]:
                if partial.exists():os.replace(partial,retained/partial.name)
        if maximum_new_frames is not None and created>=maximum_new_frames:break
        sc.camera=bpy.data.objects['PF_CAMERA_'+spec['shot']];sc.frame_set(spec['sourceFrame'])
        temporary=root/(stem+'.partial.png');sc.render.filepath=str(temporary)
        if temporary.exists():
            retained=root/'interrupted'/uuid.uuid4().hex;retained.mkdir(parents=True);os.replace(temporary,retained/temporary.name)
        start=time.monotonic();bpy.ops.render.render(write_still=True);os.replace(temporary,target)
        with receipt.open('x') as f:json.dump({'frame':spec,'sha256':sha(target),'seconds':time.monotonic()-start},f)
        created+=1
        print('PF_FRAME '+str(spec['index'])+'/'+str(len(p['frames'])),flush=True)
    complete=all((root/f"frame-{f['index']:05d}.json").exists() for f in p['frames'])
    return {'created':created,'reused':reused,'complete':complete,'expected':len(p['frames']),'planHash':core.digest(p)}
