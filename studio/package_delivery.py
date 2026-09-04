"""Copy reviewed local movie masters into the prepared personal-studio package."""
import hashlib,json,shutil,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/'specs/ai-native-studio-personal-films-final.v0.1.json').read_text())
work=Path(contract['workRoot'])
review=work.parent/'PF-FINAL-review-2026-09-04-attempt-01'
output=ROOT/'output/personal-film-studio'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

if shutil.disk_usage(output).free<100*2**30:raise SystemExit('Delivery reserve is below 100 GiB')
if sha(Path(contract['binary']))!=contract['binarySha256']:raise SystemExit('Local engine identity changed')
films={}
for name,expected in contract['films'].items():
    source=work/name;audited=read(review/name/'audit.json');visual=read(review/name/'direct-review.json')
    production=read(ROOT/contract['evidenceRoot']/name/'receipt.json')
    delivery=read(source/'output/delivery/delivery.json');movie=Path(delivery['movie'])
    assert production['status']=='RENDERED_PENDING_FINAL_REVIEW' and production['frames']==expected['frames']
    assert audited['passed'] and audited['frameCount']==expected['frames']
    assert visual['status']=='ACCEPTED_FOR_PERSONAL_DEMO_DELIVERY'
    assert sha(movie)==delivery['sha256']==audited['movieSha256']==visual['movieSha256']
    assert sha(source/'project.blend')==expected['sha256']==sha(output/'projects'/f'{name}.blend')
    assert all(sha(source/rel)==digest for rel,digest in contract['code'].items())
    destination=output/'movies'/f'{name}.mp4'
    if destination.exists():raise SystemExit('Delivery movie already exists; do not overwrite it')
    films[name]={'sourceMovie':str(movie),'movie':str(destination.relative_to(output)),
        'movieSha256':delivery['sha256'],'project':f'projects/{name}.blend','projectSha256':expected['sha256'],
        'frames':expected['frames'],'seconds':expected['seconds'],'width':contract['width'],'height':contract['height'],
        'fps':contract['fps'],'samples':contract['samples'],'audioMetrics':audited['audioMetrics'],
        'productionSeconds':production['seconds'],'technicalReview':str(review/name/'audit.json'),
        'directReview':str(review/name/'direct-review.json')}

for name,record in films.items():
    destination=output/record['movie'];shutil.copyfile(record['sourceMovie'],destination)
    assert sha(destination)==record['movieSha256']

manifest={'status':'DELIVERED_LOCAL_PERSONAL_STUDIO_AND_TWO_REVIEWED_MICROFILMS',
    'productVersion':'0.1.3','productCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'formalPipelineCommit':'2c54543b','engine':contract['binary'],'engineSha256':contract['binarySha256'],
    'films':films,'files':{},'scope':'Local editable starter worlds, bounded AI camera/look direction and complete movie delivery using the existing engine.',
    'audioReviewLimit':'Complete decoding, measured loudness/true peak and cue synchronization were reviewed. This tool session has no audio perception; subjective listening is not claimed.'}
for f in sorted(output.rglob('*')):
    if f.is_file() and f.name!='provenance.json':manifest['files'][str(f.relative_to(output))]=sha(f)
target=output/'provenance.json'
with target.open('x') as f:json.dump(manifest,f,indent=2,ensure_ascii=False)
print(json.dumps({'status':manifest['status'],'package':str(output),'movies':[record['movie'] for record in films.values()]},indent=2))
