"""Encode completed, hash-verified frames and original sound into a movie."""
import json,subprocess,shutil,math
from pathlib import Path
import bpy
from . import core,scene,rendering,sound

def responses(sc):
    targets=[o for o in sc.objects if o.get('pf_solver_role')=='target'];found={};initial={}
    for f in range(1,scene.load_document(sc)['simulation_end']+1):
        sc.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        for o in targets:
            q=o.evaluated_get(dg).matrix_world.to_quaternion()
            if f==1:initial[o.name]=q
            if o.name not in found and math.degrees(initial[o.name].rotation_difference(q).angle)>1:found[o.name]=f
        if len(found)==len(targets):break
    return found

def encode(sc,frames,output):
    frames=Path(frames);output=Path(output);output.mkdir(parents=True,exist_ok=True);p=json.loads((frames/'render-plan.json').read_text());doc=scene.load_document(sc)
    if p['documentHash']!=core.digest(doc):raise core.StudioError('Movie and open project versions differ')
    for frame in p['frames']:
        image=frames/f"frame-{frame['index']:05d}.png";receipt=image.with_suffix('.json')
        if not image.exists() or not receipt.exists() or json.loads(receipt.read_text())['sha256']!=rendering.sha(image):raise core.StudioError('Incomplete or altered movie frame')
    wav=output/'soundtrack.wav';movie=output/(doc['id']+'.mp4')
    existing=output/'delivery.json'
    if existing.exists():
        receipt=json.loads(existing.read_text())
        if receipt.get('planHash')==core.digest(p) and movie.exists() and receipt['sha256']==rendering.sha(movie):return receipt
        raise core.StudioError('Completed delivery changed; choose a fresh output folder')
    if wav.exists() or movie.exists():raise core.StudioError('Delivery exists; choose a fresh output folder')
    audio=sound.soundtrack(doc,p,wav,responses(sc));ffmpeg=shutil.which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'
    # Finish with gentle fades, maintaining native 24 fps and scope composition.
    dur=len(p['frames'])/24
    title=output/'title.png';height=round(p['width']/2.35/2)*2
    color='#e6dfcd' if doc['sound']['style']=='tape' else '#262a2a'
    python=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
    # Isolated Blender workers receive the explicit host runtime from their job environment.
    import os
    python=Path(os.environ.get('PF_MEDIA_PYTHON',str(python)))
    if not python.is_file():raise core.StudioError('Local Pillow media runtime is unavailable; set PF_MEDIA_PYTHON')
    subprocess.run([str(python),str(Path(__file__).parents[1]/'title_card.py'),json.dumps({'width':p['width'],'height':height,'title':doc['title'],'color':color,'output':str(title)})],check=True,timeout=30)
    filters=f"[0:v][2:v]overlay=0:0:enable='between(t,0.8,3.1)',fade=t=in:st=0:d=0.4,fade=t=out:st={dur-.8}:d=0.8[v]"
    argv=[ffmpeg,'-nostdin','-n','-framerate','24','-i',str(frames/'frame-%05d.png'),'-i',str(wav),'-loop','1','-framerate','24','-i',str(title),'-filter_complex',filters,'-map','[v]','-map','1:a','-frames:v',str(len(p['frames'])),'-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-af','loudnorm=I=-20:TP=-2:LRA=7','-ar','48000','-c:a','aac','-b:a','256k','-movflags','+faststart','-shortest',str(movie)]
    with (output/'encode.stdout.log').open('x') as out,(output/'encode.stderr.log').open('x') as err:subprocess.run(argv,stdout=out,stderr=err,check=True,timeout=300)
    probe=subprocess.check_output([shutil.which('ffprobe') or '/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(movie)],text=True)
    data=json.loads(probe);video=next(s for s in data['streams'] if s['codec_type']=='video')
    if int(video['nb_read_frames'])!=len(p['frames']) or int(video['width'])!=p['width']:raise core.StudioError('Encoded frame count or width differs')
    receipt={'planHash':core.digest(p),'movie':str(movie),'sha256':rendering.sha(movie),'sound':audio,'ffprobe':data,'argv':argv}
    (output/'delivery.json').write_text(json.dumps(receipt,indent=2));return receipt
