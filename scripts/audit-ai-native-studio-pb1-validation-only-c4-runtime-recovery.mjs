#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, lstatSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const SELF=fileURLToPath(import.meta.url),REPO=resolve(dirname(SELF),'..'),SPEC_REL='specs/ai-native-studio-pb1-validation-only-c4-runtime-recovery.v0.10.json',SPEC=JSON.parse(readFileSync(resolve(REPO,SPEC_REL),'utf8')),GIT='/usr/bin/git',GH='/opt/homebrew/bin/gh',DU='/usr/bin/du';
const canon=v=>Array.isArray(v)?v.map(canon):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,canon(x)])):v;
const sha=v=>createHash('sha256').update(v).digest('hex'),fileSha=p=>sha(readFileSync(p)),receiptHash=v=>{const c=structuredClone(v);delete c.receiptHash;return sha(JSON.stringify(canon(c)))};
function cmd(e,a){return execFileSync(e,a,{encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:120000,maxBuffer:64*1024*1024}).trim()}
function tree(root){if(!existsSync(root))return {state:'ABSENT',entries:0,digest:sha('ABSENT')};const rows=[];function w(p,x=''){for(const n of readdirSync(p).sort((a,b)=>a.localeCompare(b,'en'))){const q=resolve(p,n),r=x?`${x}/${n}`:n,s=lstatSync(q);if(s.isDirectory()){rows.push({path:r,type:'directory',mode:s.mode&0o7777});w(q,r)}else if(s.isFile())rows.push({path:r,type:'file',mode:s.mode&0o7777,bytes:s.size,sha256:fileSha(q)});else if(s.isSymbolicLink())rows.push({path:r,type:'symlink',mode:s.mode&0o7777})}}w(root);return {state:'PRESENT',entries:rows.length,digest:sha(JSON.stringify(canon(rows)))}}
const root=resolve(REPO,SPEC.paths.evidenceRoot),auditPath=resolve(root,'audit.json');if(existsSync(auditPath))throw new Error('audit exists');
const preflight=JSON.parse(readFileSync(resolve(root,'preflight.json'),'utf8')),runtime=JSON.parse(readFileSync(resolve(root,'runtime-recovery.json'),'utf8')),verdict=JSON.parse(readFileSync(resolve(root,'verdict.json'),'utf8')),build=JSON.parse(readFileSync(resolve(REPO,SPEC.attempt04.evidenceRoot,'build.json'),'utf8')),failureAudit=JSON.parse(readFileSync(resolve(REPO,SPEC.attempt04.evidenceRoot,'audit-failure.json'),'utf8'));
const checks=[];const add=(id,pass)=>checks.push({id,pass:Boolean(pass)});
add('INDEPENDENT',!readFileSync(SELF,'utf8').includes("from './run-ai-native"));
add('RECEIPTS_HASH',receiptHash(preflight)===preflight.receiptHash&&receiptHash(runtime)===runtime.receiptHash&&receiptHash(verdict)===verdict.receiptHash);
add('PREFLIGHT_ACCEPTED',preflight.status==='ACCEPTED'&&preflight.failures.length===0);
add('ATTEMPT04_BINDINGS',build.status==='PASS'&&build.receiptHash===SPEC.attempt04.buildReceiptHash&&failureAudit.status==='PASS'&&failureAudit.receiptHash===SPEC.attempt04.failureAuditReceiptHash);
add('BINARY_EXACT',statSync(SPEC.attempt04.binary).size===SPEC.attempt04.binaryBytes&&fileSha(SPEC.attempt04.binary)===SPEC.attempt04.binarySha256);
add('RUNTIME_PASS',runtime.status==='PASS'&&Object.values(runtime.checks).every(Boolean)&&runtime.productStarts===2&&runtime.renders===0);
add('PATHS_EXACT',Object.entries(runtime.paths).every(([k,v])=>runtime.payload.paths[k]===v));
add('IDENTITY_EXACT',runtime.payload.version===SPEC.expected.version&&runtime.payload.buildHash.startsWith(SPEC.expected.buildHashPrefix)&&runtime.payload.binaryPath===SPEC.attempt04.binary);
add('CONFIG_ISOLATION',runtime.configuration.officialBefore.digest===runtime.configuration.officialAfter.digest&&runtime.configuration.productBefore.digest===runtime.configuration.productAfter.digest&&tree(SPEC.paths.recoveryRoot).digest===runtime.configuration.recoveryAfter.digest);
add('LOG_HASHES',runtime.logs.versionStdout===fileSha(resolve(root,'version.stdout.log'))&&runtime.logs.versionStderr===fileSha(resolve(root,'version.stderr.log'))&&runtime.logs.runtimeStdout===fileSha(resolve(root,'runtime.stdout.log'))&&runtime.logs.runtimeStderr===fileSha(resolve(root,'runtime.stderr.log')));
add('VERDICT_PASS',verdict.status==='PASS'&&verdict.runtimeRecoveryReceiptHash===runtime.receiptHash);
add('COUNTERS_EXACT',verdict.counters.productStarts===2&&Object.entries(verdict.counters).filter(([k])=>k!=='productStarts').every(([,v])=>v===0));
const meta=JSON.parse(cmd(GH,['api',`repos/lovejzzz/film-engine`]));const heads=cmd(GIT,['ls-remote','--heads','https://github.com/lovejzzz/film-engine.git']).split(/\r?\n/);
add('LIVE_REMOTE_UNCHANGED',meta.id===1351574987&&heads.length===1&&heads[0].startsWith('4061e12bd45a2bec83e68d0cf49abbf56d4738f6'));
add('ROOT_CEILINGS',Number(cmd(DU,['-sk',SPEC.paths.recoveryRoot]).split(/\s+/)[0])*1024<=SPEC.ceilings.maximumRecoveryRootBytes&&Number(cmd(DU,['-sk',root]).split(/\s+/)[0])*1024<=SPEC.ceilings.maximumEvidenceRootBytes);
const failed=checks.filter(x=>!x.pass),record={schemaVersion:'bfs.pb1ValidationOnlyC4IndependentAudit.v0.10',gate:'PB.1',observedAt:new Date().toISOString(),status:failed.length?'FAIL':'PASS',auditor:{path:'scripts/audit-ai-native-studio-pb1-validation-only-c4-runtime-recovery.mjs',sha256:fileSha(SELF),importsRunner:false},checksPassed:checks.length-failed.length,checksTotal:checks.length,checks,failures:failed.map(x=>x.id),runtimeReceiptHash:runtime.receiptHash,verdictReceiptHash:verdict.receiptHash,externalMutationsPerformedByAuditor:0,stopRulePreserved:true};record.receiptHash=receiptHash(record);const fd=openSync(auditPath,'wx',0o600);try{writeFileSync(fd,JSON.stringify(record,null,2)+'\n')}finally{closeSync(fd)}process.stdout.write(JSON.stringify(record,null,2)+'\n');process.exit(record.status==='PASS'?0:1);
