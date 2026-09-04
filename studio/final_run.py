"""One frozen final-film production, with live disk/time/frame ceilings."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('film');a=p.parse_args();contract=ROOT/'specs/ai-native-studio-personal-films-final.v0.1.json';raw=contract.read_bytes();c=json.loads(raw);f=c['films'][a.film]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def total(p):return sum(x.stat().st_size for x in p.rglob('*') if x.is_file()) if p.exists() else 0
if subprocess.check_output(['git','show','HEAD:specs/ai-native-studio-personal-films-final.v0.1.json'],cwd=ROOT)!=raw:raise SystemExit('Final contract is not exactly committed')
for path,digest in c['code'].items():
 if sha(ROOT/path)!=digest:raise SystemExit('Frozen product code differs: '+path)
if sha(c['binary'])!=c['binarySha256'] or sha(f['input'])!=f['sha256']:raise SystemExit('Runtime or film input identity differs')
wd=Path(c['workRoot'])/a.film;ed=ROOT/c['evidenceRoot']/a.film
if wd.exists() or ed.exists():raise SystemExit('Final root exists; retain it and create a versioned continuation')
if shutil.disk_usage(ROOT).free<(c['reserveGiB']+c['aggregateProjectedGiB'])*2**30:raise SystemExit('Host admission rejected')
wd.mkdir(parents=True);ed.mkdir(parents=True);code=wd/'studio';code.mkdir()
for rel in c['code']:
 src=ROOT/rel;dst=wd/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
blend=wd/'project.blend';shutil.copy2(f['input'],blend)
job={'action':'render','output':str(wd/'output'),'stills':[],'width':c['width'],'samples':c['samples'],'maximum_new_frames':f['frames'],'encode':True}
jobpath=wd/'job.json';jobpath.write_text(json.dumps(job,indent=2));binary=Path(c['binary']);env=os.environ.copy();env['PF_MEDIA_PYTHON']=c['mediaPython'];env['HOME']=str(wd/'home');Path(env['HOME']).mkdir()
env['OCIO']=str(binary.parents[1]/'Resources/5.2/datafiles/colormanagement/config.ocio')
for k in ['CONFIG','SCRIPTS','DATAFILES','EXTENSIONS']:
 d=wd/('user_'+k.lower());d.mkdir();env['BLENDER_USER_'+k]=str(d)
argv=[str(binary),'--background','--factory-startup','--disable-autoexec','--python-exit-code','2',str(blend),'--python',str(code/'blender_entry.py'),'--',str(jobpath)]
admission={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'contractSha256':sha(contract),'inputSha256':sha(blend),'argv':argv,'time':time.time(),'expectedFrames':f['frames']}
(ed/'admission.json').write_text(json.dumps(admission,indent=2));start=time.monotonic();reason=None
with (ed/'stdout.log').open('x') as out,(ed/'stderr.log').open('x') as err:
 proc=subprocess.Popen(argv,env=env,stdout=out,stderr=err)
 while proc.poll() is None:
  if time.monotonic()-start>c['maximumSecondsPerFilm']:reason='TIME_CEILING'
  elif total(wd)>c['maximumGiBPerFilm']*2**30:reason='WORK_BYTE_CEILING'
  elif shutil.disk_usage(ROOT).free<c['reserveGiB']*2**30:reason='FREE_RESERVE_CEILING'
  elif len(list((wd/'output/frames').glob('frame-*.png')))>f['frames']:reason='FRAME_CEILING'
  if reason:
   proc.terminate()
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
   break
  time.sleep(2)
result=wd/'output/result.json';count=len(list((wd/'output/frames').glob('frame-*.png')))
passed=proc.returncode==0 and reason is None and count==f['frames'] and result.exists()
receipt={'status':'RENDERED_PENDING_FINAL_REVIEW' if passed else 'RETAINED_FAILURE','returncode':proc.returncode,'stopReason':reason,'seconds':time.monotonic()-start,'frames':count,'workBytes':total(wd),'resultSha256':sha(result) if result.exists() else None,'blendSha256After':sha(blend)}
(ed/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));raise SystemExit(0 if passed else 2)
