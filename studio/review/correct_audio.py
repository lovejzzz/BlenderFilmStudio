"""Fresh audio-only correction, retaining the encoded video packets exactly."""
import argparse, hashlib, json, shutil, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from film_studio.audio_master import measured_filter

p=argparse.ArgumentParser();p.add_argument('work');p.add_argument('audit');p.add_argument('output');a=p.parse_args()
work=Path(a.work);out=Path(a.output);audit=json.loads(Path(a.audit).read_text())
source=work/'output/delivery';receipt_path=source/'delivery.json';receipt=json.loads(receipt_path.read_text())
movie=Path(receipt['movie']);wav=source/'soundtrack.wav';ffmpeg='/opt/homebrew/bin/ffmpeg'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def video_hash(path):
    return subprocess.check_output([ffmpeg,'-v','error','-i',str(path),'-map','0:v:0','-c','copy',
                                    '-f','hash','-hash','sha256','-'],text=True,timeout=120).strip()
assert audit['movieSha256']==receipt['sha256']==sha(movie)
assert not audit['checks']['encoded_loudness']
assert all(v for k,v in audit['checks'].items() if k!='encoded_loudness')
assert shutil.disk_usage(out.parent).free>100*2**30
before={str(p):sha(p) for p in [receipt_path,movie,wav]};start=time.monotonic()
out.mkdir(exist_ok=False)
filt=measured_filter(ffmpeg,wav,out);destination=out/movie.name
argv=[ffmpeg,'-nostdin','-n','-i',str(movie),'-i',str(wav),'-map','0:v:0','-map','1:a:0',
      '-c:v','copy','-af',filt,'-ar','48000','-c:a','aac','-b:a','256k','-movflags','+faststart',
      '-shortest',str(destination)]
with (out/'encode.stdout.log').open('x') as stdout,(out/'encode.stderr.log').open('x') as stderr:
    subprocess.run(argv,stdout=stdout,stderr=stderr,check=True,timeout=300)
original_video=video_hash(movie);corrected_video=video_hash(destination)
assert original_video==corrected_video
assert before=={path:sha(Path(path)) for path in before}
assert time.monotonic()-start<600
assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<256*2**20
receipt.update({'movie':str(destination),'sha256':sha(destination),'argv':argv,
    'correction':{'kind':'AUDIO_NORMALIZATION_C1','sourceDelivery':str(receipt_path),
      'sourceHashes':before,'sourceVideoStreamHash':original_video,'videoStreamHash':corrected_video,
      'videoUnchanged':True,'seconds':time.monotonic()-start,'blenderStarts':0,'renders':0}})
receipt['ffprobe']=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error',
    '-count_frames','-show_streams','-show_format','-of','json',str(destination)],text=True))
(out/'delivery.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps({'movie':str(destination),'sha256':receipt['sha256'],'correction':receipt['correction']},indent=2))
