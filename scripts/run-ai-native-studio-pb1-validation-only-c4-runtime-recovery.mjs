#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, lstatSync, mkdirSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const SCRIPT = fileURLToPath(import.meta.url);
const REPO = resolve(dirname(SCRIPT), '..');
const SPEC_REL = 'specs/ai-native-studio-pb1-validation-only-c4-runtime-recovery.v0.10.json';
const SPEC = JSON.parse(readFileSync(resolve(REPO, SPEC_REL), 'utf8'));
const GIT = '/usr/bin/git';
const DU = '/usr/bin/du';
const PS = '/bin/ps';
const execute = process.argv.includes('--execute');

const canon = value => Array.isArray(value) ? value.map(canon) : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).sort(([a],[b]) => a.localeCompare(b)).map(([k,v]) => [k,canon(v)])) : value;
const sha = value => createHash('sha256').update(value).digest('hex');
const fileSha = path => sha(readFileSync(path));
const receiptHash = value => { const copy=structuredClone(value); delete copy.receiptHash; return sha(JSON.stringify(canon(copy))); };
function writeJson(path,value){const record={...value};record.receiptHash=receiptHash(record);const fd=openSync(path,'wx',0o600);try{writeFileSync(fd,JSON.stringify(record,null,2)+'\n')}finally{closeSync(fd)}return record}
function cmd(exe,args,options={}){try{return {exitCode:0,stdout:execFileSync(exe,args,{cwd:options.cwd,encoding:'utf8',env:options.env??process.env,stdio:['ignore','pipe','pipe'],timeout:options.timeout??120000,maxBuffer:64*1024*1024}),stderr:''}}catch(e){return {exitCode:Number.isInteger(e.status)?e.status:1,stdout:e.stdout??'',stderr:e.stderr??String(e.message??e)}}}
function required(exe,args){const r=cmd(exe,args);if(r.exitCode)throw new Error(r.stderr);return r.stdout.trim()}
function bytes(path){return existsSync(path)?Number(required(DU,['-sk',path]).split(/\s+/)[0])*1024:0}
function tree(root){if(!existsSync(root))return {state:'ABSENT',entries:0,digest:sha('ABSENT')};const rows=[];function walk(path,prefix=''){for(const name of readdirSync(path).sort((a,b)=>a.localeCompare(b,'en'))){const abs=resolve(path,name),rel=prefix?`${prefix}/${name}`:name,item=lstatSync(abs);if(item.isDirectory()){rows.push({path:rel,type:'directory',mode:item.mode&0o7777});walk(abs,rel)}else if(item.isFile())rows.push({path:rel,type:'file',mode:item.mode&0o7777,bytes:item.size,sha256:fileSha(abs)});else if(item.isSymbolicLink())rows.push({path:rel,type:'symlink',mode:item.mode&0o7777})}}walk(root);return {state:'PRESENT',entries:rows.length,digest:sha(JSON.stringify(canon(rows)))}}
function parseMarker(text){const line=text.split(/\r?\n/).find(x=>x.startsWith('PB1_C4_RUNTIME='));return line?JSON.parse(line.slice(15)):null}
const evidence=resolve(REPO,SPEC.paths.evidenceRoot);
const recovery=SPEC.paths.recoveryRoot;
const binary=SPEC.attempt04.binary;
const actualOfficial=resolve(process.env.HOME,'Library','Application Support','Blender');
const actualProduct=resolve(process.env.HOME,'Library','Application Support',SPEC.expected.configurationNamespace);
const preflight={
  schemaVersion:'bfs.pb1ValidationOnlyC4Preflight.v0.10',
  observedAt:new Date().toISOString(),
  status:'PENDING',
  research:{head:required(GIT,['-C',REPO,'rev-parse','HEAD']),upstream:required(GIT,['-C',REPO,'rev-parse','@{upstream}']),clean:required(GIT,['-C',REPO,'status','--porcelain=v1'])===''},
  roots:{recoveryAbsent:!existsSync(recovery),evidenceAbsent:!existsSync(evidence)},
  binary:{exists:existsSync(binary),bytes:existsSync(binary)?statSync(binary).size:null,sha256:existsSync(binary)?fileSha(binary):null},
  attempt04:{build:JSON.parse(readFileSync(resolve(REPO,SPEC.attempt04.evidenceRoot,'build.json'),'utf8')),audit:JSON.parse(readFileSync(resolve(REPO,SPEC.attempt04.evidenceRoot,'audit-failure.json'),'utf8'))},
  processes:required(PS,['-axo','pid=,comm=,args=']).split(/\r?\n/).filter(line=>/Film Studio Engine F0\.app\/Contents\/MacOS\/Blender/.test(line))
};
const failures=[];
if(!preflight.research.clean||preflight.research.head!==preflight.research.upstream)failures.push('RESEARCH_NOT_CLEAN_PUSHED');
if(!preflight.roots.recoveryAbsent||!preflight.roots.evidenceAbsent)failures.push('FRESH_ROOTS_REQUIRED');
if(!preflight.binary.exists||preflight.binary.bytes!==SPEC.attempt04.binaryBytes||preflight.binary.sha256!==SPEC.attempt04.binarySha256)failures.push('BINARY_MISMATCH');
if(preflight.attempt04.build.status!=='PASS'||preflight.attempt04.build.receiptHash!==SPEC.attempt04.buildReceiptHash||preflight.attempt04.audit.status!=='PASS'||preflight.attempt04.audit.receiptHash!==SPEC.attempt04.failureAuditReceiptHash)failures.push('ATTEMPT04_BINDING_MISMATCH');
if(preflight.processes.length)failures.push('PRODUCT_PROCESS_PRESENT');
preflight.failures=failures;preflight.status=failures.length?'BLOCKED':'ACCEPTED';
if(!execute){process.stdout.write(JSON.stringify(preflight,null,2)+'\n');process.exit(preflight.status==='ACCEPTED'?0:1)}
mkdirSync(evidence,{recursive:true});writeJson(resolve(evidence,'preflight.json'),preflight);
if(preflight.status!=='ACCEPTED')process.exit(1);
mkdirSync(recovery);
const paths={CONFIG:resolve(recovery,'config'),SCRIPTS:resolve(recovery,'scripts'),DATAFILES:resolve(recovery,'datafiles'),EXTENSIONS:resolve(recovery,'extensions')};
const env={...process.env,HOME:resolve(recovery,'home'),BLENDER_USER_CONFIG:paths.CONFIG,BLENDER_USER_SCRIPTS:paths.SCRIPTS,BLENDER_USER_DATAFILES:paths.DATAFILES,BLENDER_USER_EXTENSIONS:paths.EXTENSIONS};
const officialBefore=tree(actualOfficial),productBefore=tree(actualProduct);
const version=cmd(binary,['--version'],{env,timeout:SPEC.ceilings.maximumStartSeconds*1000});
const expr=['import bpy, json','events=[]','bpy.app.handlers.render_pre.append(lambda scene: events.append(scene.name))','decode=lambda v: v.decode("utf-8") if isinstance(v,bytes) else str(v)','paths={k:bpy.utils.user_resource(k,create=True) for k in ("CONFIG","SCRIPTS","DATAFILES","EXTENSIONS")}','saved=sorted(bpy.ops.wm.save_userpref())','print("PB1_C4_RUNTIME="+json.dumps({"version":bpy.app.version_string,"buildHash":decode(bpy.app.build_hash),"binaryPath":bpy.app.binary_path,"paths":paths,"save":saved,"renderCalls":len(events)},sort_keys=True),flush=True)'].join(';');
const runtime=cmd(binary,['--background','--factory-startup','--python-expr',expr],{env,timeout:SPEC.ceilings.maximumStartSeconds*1000});
writeFileSync(resolve(evidence,'version.stdout.log'),version.stdout,{flag:'wx'});writeFileSync(resolve(evidence,'version.stderr.log'),version.stderr,{flag:'wx'});writeFileSync(resolve(evidence,'runtime.stdout.log'),runtime.stdout,{flag:'wx'});writeFileSync(resolve(evidence,'runtime.stderr.log'),runtime.stderr,{flag:'wx'});
const payload=parseMarker(runtime.stdout+'\n'+runtime.stderr);
const officialAfter=tree(actualOfficial),productAfter=tree(actualProduct),recoveryAfter=tree(recovery);
const checks={versionExit:version.exitCode===0,versionIdentity:version.stdout.startsWith(`Film Studio Engine F0 ${SPEC.expected.version}`)&&version.stdout.includes(`build hash: ${SPEC.expected.buildHashPrefix}`),runtimeExit:runtime.exitCode===0,payloadPresent:Boolean(payload),payloadIdentity:payload?.version===SPEC.expected.version&&payload?.buildHash?.startsWith(SPEC.expected.buildHashPrefix)&&payload?.binaryPath===binary,pathsExact:Object.entries(paths).every(([k,v])=>payload?.paths?.[k]===v),preferenceSaved:payload?.save?.join(',')==='FINISHED',zeroRenders:payload?.renderCalls===0,officialUnchanged:officialBefore.digest===officialAfter.digest,realProductUnchanged:productBefore.digest===productAfter.digest,recoveryPresent:recoveryAfter.state==='PRESENT'&&existsSync(resolve(paths.CONFIG,'userpref.blend')),withinCeiling:bytes(recovery)<=SPEC.ceilings.maximumRecoveryRootBytes};
const runtimeReceipt=writeJson(resolve(evidence,'runtime-recovery.json'),{schemaVersion:'bfs.pb1ValidationOnlyC4RuntimeRecoveryReceipt.v0.10',observedAt:new Date().toISOString(),status:Object.values(checks).every(Boolean)?'PASS':'FAIL',productStarts:2,renders:0,payload,paths,configuration:{actualOfficial,officialBefore,officialAfter,actualProduct,productBefore,productAfter,recoveryAfter},logs:{versionStdout:fileSha(resolve(evidence,'version.stdout.log')),versionStderr:fileSha(resolve(evidence,'version.stderr.log')),runtimeStdout:fileSha(resolve(evidence,'runtime.stdout.log')),runtimeStderr:fileSha(resolve(evidence,'runtime.stderr.log'))},checks});
const counters={clones:0,lfsMaterializations:0,dependencyClones:0,nativeBuilds:0,productStarts:2,renders:0,engineRemoteWrites:0,releases:0,signing:0,notarization:0,dmg:0,pb2ThroughPb7:0};
const verdict=writeJson(resolve(evidence,'verdict.json'),{schemaVersion:'bfs.pb1ValidationOnlyC4Verdict.v0.10',gate:'PB.1',observedAt:new Date().toISOString(),status:runtimeReceipt.status,attempt04BuildReceiptHash:SPEC.attempt04.buildReceiptHash,runtimeRecoveryReceiptHash:runtimeReceipt.receiptHash,counters,checks:{runtimeRecoveryPass:runtimeReceipt.status==='PASS',zeroNewBuild:counters.nativeBuilds===0,forbiddenZero:Object.entries(counters).filter(([k])=>!['productStarts'].includes(k)).every(([,v])=>v===0),evidenceWithin:bytes(evidence)<=SPEC.ceilings.maximumEvidenceRootBytes},claimCeiling:'PB.1 validation-only repository/source/build/product-identity evidence only; PB.2-PB.7 remain unauthorized.',stopRulePreserved:true});
process.stdout.write(`PB1_C4_RUNTIME_RECOVERY_${verdict.status}\n`);
process.exit(verdict.status==='PASS'?0:1);
