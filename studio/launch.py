"""Open the native personal studio with a project, preserving the RC5 install."""
import argparse,json,os,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('project',nargs='?');a=p.parse_args()
c=json.loads((ROOT/'specs/ai-native-studio-personal-films-program.v0.1.json').read_text())['developmentAdmission'];binary=Path(c['binary'])
if hashlib.sha256(binary.read_bytes()).hexdigest()!=c['binarySha256']:raise SystemExit('Engine identity differs from the validated runtime')
env=os.environ.copy();env['PF_MEDIA_PYTHON']=str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3');config=ROOT/'studio'/'user_settings';config.mkdir(exist_ok=True)
for key in ['CONFIG','SCRIPTS','DATAFILES','EXTENSIONS']:
    d=config/key.lower();d.mkdir(exist_ok=True);env['BLENDER_USER_'+key]=str(d)
env['OCIO']=str(binary.parents[1]/'Resources/5.2/datafiles/colormanagement/config.ocio')
cmd=[str(binary),'--factory-startup','--disable-autoexec']
if a.project:cmd.append(str(Path(a.project).resolve()))
cmd+=['--python',str(ROOT/'studio'/'ui_start.py')]
subprocess.Popen(cmd,env=env,start_new_session=True)
