"""Free-form director notes through the user's already authenticated Codex CLI.
The model returns data only. Blender applies a bounded, revision-checked patch.
"""
import json,os,shutil,subprocess,time
from pathlib import Path
from . import core

SCHEMA={'type':'object','properties':{'revision':{'type':'integer'},'operation':{'type':'string','enum':sorted(core.OPERATIONS)},'shot':{'type':'string'},'value':{'type':'number'},'reason':{'type':'string'}},'required':['revision','operation','shot','value','reason'],'additionalProperties':False}

def propose(doc,note,shot,root):
    core.validate(doc)
    if not isinstance(note,str) or not 1<=len(note.strip())<=2000:raise core.StudioError('Write a note of 1-2000 characters')
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    cli=shutil.which('codex') or '/Applications/ChatGPT.app/Contents/Resources/codex'
    if not Path(cli).is_file():raise core.StudioError('Install and sign in to Codex to use AI Director')
    schema=root/'schema.json';schema.write_text(json.dumps(SCHEMA));output=root/'proposal.json'
    prompt='''You are a film director assistant translating a note into ONE bounded shot edit. All necessary project data follows. Do not call tools, inspect files, run code, browse, or delegate. Return only the JSON schema. Values are ABSOLUTE, not deltas. Copy the exact revision. Target the selected shot unless user specifies another valid shot. camera_distance is meters; camera_orbit is azimuth degrees; lens is mm; focus is focus_offset meters; cut_offset is an integer relative to the shot event anchor. warmth is [-1,1], exposure is stops [-4,4]; these require shot ALL. Moving a cut must remain inside simulation. Camera distance [.1,30], lens [18,135], focus [-3,3]. Preserve assets and physics. For unsupported scene changes or ambiguous requests return operation reject, value 0 and a helpful reason. Do not claim to have seen images or made the change. Reason should briefly explain the proposed cinematic effect in the note's language.\n'''+core.canonical({'project':doc,'selectedShot':shot,'directorNote':note})
    (root/'prompt.txt').write_text(prompt)
    argv=[cli,'exec','--ephemeral','--ignore-user-config','--skip-git-repo-check','--sandbox','read-only','--config','approval_policy="never"','--config','agents.enabled=false','--config','web_search="disabled"','--color','never','--output-schema',str(schema),'--output-last-message',str(output),'--json','-']
    env=os.environ.copy()
    # Explicit API credentials are never used by this local product adapter.
    env.pop('OPENAI_API_KEY',None);env.pop('CODEX_API_KEY',None)
    status=subprocess.run([cli,'login','status'],capture_output=True,text=True,env=env,timeout=20)
    if status.returncode or 'chatgpt' not in (status.stdout+status.stderr).lower():raise core.StudioError('AI Director requires your existing ChatGPT sign-in; API billing is not enabled')
    start=time.monotonic()
    with (root/'events.jsonl').open('x') as out,(root/'stderr.log').open('x') as err:
        proc=subprocess.run(argv,input=prompt,text=True,cwd=root,env=env,stdout=out,stderr=err,timeout=180)
    events=[]
    for line in (root/'events.jsonl').read_text().splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:raise core.StudioError('Invalid director event stream')
    forbidden=[e for e in events if e.get('item',{}).get('type') in {'command_execution','file_change','mcp_tool_call','web_search','collab_tool_call'}]
    receipt={'seconds':time.monotonic()-start,'returncode':proc.returncode,'forbiddenToolEvents':len(forbidden),'inputHash':core.digest(doc),'argv':argv}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2))
    if proc.returncode or forbidden or not output.exists():raise core.StudioError('AI Director could not produce a clean proposal; see its job log')
    proposal=json.loads(output.read_text());core.apply_patch(doc,proposal)
    return proposal
