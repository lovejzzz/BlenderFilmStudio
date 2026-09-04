"""Bounded development runner. Candidate roots and receipts are never overwritten."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--project',default='last-signal.film.json');p.add_argument('--blend');p.add_argument('--action',choices=['build','editorial','inspect','exercise','render','resume_test'],default='build');p.add_argument('--maximum-new-frames',type=int,default=0);p.add_argument('--shots');p.add_argument('--stills',default='S01,S02,S03,S04');p.add_argument('--width',type=int,default=1280);p.add_argument('--samples',type=int,default=48)
a=p.parse_args()
if not a.name.replace('-','').isalnum():raise SystemExit('Invalid candidate name')
contract=REPO/'specs/ai-native-studio-personal-films-program.v0.1.json';limits=json.loads(contract.read_text())['developmentAdmission']
work=Path(limits['workRoot']);ev=REPO/limits['evidenceRoot'];binary=Path(limits['binary'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def size(p):return sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) if p.exists() else 0
if sha(binary)!=limits['binarySha256']:raise SystemExit('Binary identity changed')
if shutil.disk_usage(REPO).free<(limits['minimumFreeReserveGiB']+limits['projectedWriteGiB'])*2**30:raise SystemExit('Free space admission rejected')
if size(work)>limits['maximumWorkGiB']*2**30 or size(ev)>limits['maximumEvidenceMiB']*2**20:raise SystemExit('Resource ceiling reached')
priors=list(ev.glob('*/admission.json')) if ev.exists() else []
stills=[s for s in a.stills.split(',') if s]
if len(priors)>=limits['maximumBlenderStarts']:raise SystemExit('Start ceiling reached')
if sum(len(json.loads(f.read_text())['job']['stills']) for f in priors)+len(stills)>limits['maximumStillRenderCalls']:raise SystemExit('Still ceiling reached')
wd=work/a.name;ed=ev/a.name
if wd.exists() or ed.exists():raise SystemExit('Candidate root already exists')
wd.mkdir(parents=True);ed.mkdir(parents=True)
code=wd/'code';shutil.copytree(REPO/'studio',code,ignore=shutil.ignore_patterns('__pycache__'))
project=code/'projects'/Path(a.project).name
if not project.exists():raise SystemExit('Project must be in studio/projects')
job={'action':a.action,'project':str(project),'output':str(wd/'output'),'stills':stills,'width':a.width,'samples':a.samples,'maximum_new_frames':a.maximum_new_frames,'shots':a.shots.split(',') if a.shots else None}
if a.maximum_new_frames<0 or sum(json.loads(f.read_text())['job'].get('maximum_new_frames',0) for f in priors)+a.maximum_new_frames>limits['maximumPreviewFrames']:raise SystemExit('Preview frame ceiling reached')
input_blend=None
if a.blend:
    input_blend=wd/'input.blend';shutil.copy2(Path(a.blend),input_blend)
if a.action!='build' and not input_blend:raise SystemExit('This action requires --blend')
jobpath=wd/'job.json';jobpath.write_text(json.dumps(job,indent=2))
resources=binary.parents[1]/'Resources'/'5.2';env=os.environ.copy();env['HOME']=str(wd/'home');env['OCIO']=str(resources/'datafiles/colormanagement/config.ocio')
for k in ['CONFIG','SCRIPTS','DATAFILES','EXTENSIONS']:
    dest=wd/('user_'+k.lower());dest.mkdir();env['BLENDER_USER_'+k]=str(dest)
Path(env['HOME']).mkdir()
argv=[str(binary),'--background','--factory-startup','--disable-autoexec','--python-exit-code','2']+([str(input_blend)] if input_blend else [])+['--python',str(code/'blender_entry.py'),'--',str(jobpath)]
admission={'candidate':a.name,'time':time.time(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'contractSha256':sha(contract),'binarySha256':sha(binary),'job':job,'argv':argv,'inputs':{str(f.relative_to(wd)):sha(f) for f in code.rglob('*') if f.is_file()}}
(ed/'admission.json').write_text(json.dumps(admission,indent=2))
start=time.monotonic();status='FAILED'
with (ed/'stdout.log').open('x') as stdout,(ed/'stderr.log').open('x') as stderr:
    try:
        proc=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr,timeout=limits['maximumSingleProcessSeconds']);rc=proc.returncode;status='PASS' if rc==0 else 'FAILED'
    except subprocess.TimeoutExpired:rc=-1;status='TIMEOUT'
receipt={'status':status,'returncode':rc,'seconds':time.monotonic()-start,'workBytes':size(work),'evidenceBytes':size(ev),'outputs':{str(f.relative_to(wd)):sha(f) for f in (wd/'output').rglob('*') if f.is_file()}}
if receipt['workBytes']>limits['maximumWorkGiB']*2**30 or receipt['evidenceBytes']>limits['maximumEvidenceMiB']*2**20:receipt['status']='RESOURCE_FAILURE'
(ed/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));raise SystemExit(rc)
