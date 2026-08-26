import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/quadrature-derivation-v0-1');
const evidence = resolve(root, 'evidence');
const work = resolve(root, 'work');
const b31Root = resolve(repositoryRoot, 'experiments/sampling-quality-derivation-v0-1');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b32_quadrature_derivation.py');
const analyzer = resolve(repositoryRoot, 'blender/analyze_b32_quadrature_derivation.py');
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
function run(command,args,env=process.env){return new Promise((ok,fail)=>{const child=spawn(command,args,{cwd:repositoryRoot,env,stdio:['ignore','pipe','pipe']});let output='';child.stdout.on('data',c=>output+=c);child.stderr.on('data',c=>output+=c);child.on('error',fail);child.on('close',code=>code===0?ok({pid:child.pid,output}):fail(new Error(`${command} failed (${code})\n${output}`)));});}

await rm(evidence,{recursive:true,force:true}); await rm(work,{recursive:true,force:true});
await mkdir(evidence,{recursive:true}); await mkdir(work,{recursive:true});
const review=JSON.parse(await readFile(reviewPath,'utf8'));
const receiptPath=resolve(repositoryRoot,review.source.receiptUri);
const receipt=JSON.parse(await readFile(receiptPath,'utf8'));
const scenePath=resolve(repositoryRoot,receipt.run.sceneBlend.uri);
const ocioPath=resolve(repositoryRoot,receipt.executionIdentity.configuration.ocio.uri);
const frames=[37,72,103]; const reports=[];
for(const replicate of ['A','B']) for(const point of ['Q1','Q2','Q3','Q4']){
  const id=`${point}_${replicate}`; const outputDir=resolve(work,id); const reportPath=resolve(evidence,`${id}.json`);
  const threadPath=resolve(evidence,`${id}.threads.json`); await mkdir(outputDir,{recursive:true});
  const launched=await run(blender,['--background',scenePath,'--disable-autoexec','--python-exit-code','1','--python',configurator,
    '--python',renderer,'--','--review-spec',reviewPath,'--receipt',receiptPath,'--output-dir',outputDir,'--report',reportPath,
    '--point',point,'--replicate',replicate,'--frames',...frames.map(String)],{...process.env,OCIO:ocioPath,BFS_B22_THREADS_MODE:'FIXED',BFS_B22_THREADS:'8',BFS_B22_CELL:'T08',BFS_B22_INTERVENTION_REPORT:threadPath});
  const report=JSON.parse(await readFile(reportPath,'utf8')); if(report.processId!==launched.pid)throw new Error(`${id} PID mismatch`);
  reports.push({id,point,replicate,processId:launched.pid,jitter:report.jitter,totalRenderSeconds:report.totalRenderSeconds,
    reportSha256:await sha256File(reportPath),outputHashes:report.outputs.map(item=>item.sha256)});
  process.stdout.write(`BFS_B32_QUADRATURE_PROCESS_OK ${id} pid=${launched.pid}\n`);
}
const result={documentType:'BFS_B32_QUADRATURE_DERIVATION_RESULT',version:'0.1.0',status:'EXPLORATORY_DERIVATION_ONLY_NOT_CONFIRMATION',
  executedAtUtc:new Date().toISOString(),question:'Can a deterministic equal-weight four-corner fixed-jitter ensemble reduce CENTER edge-reference cost while preserving exact repeatability?',
  design:{frames,points:[[-.25,-.25],[-.25,.25],[.25,-.25],[.25,.25]],weights:[.25,.25,.25,.25],processes:8,renderCalls:24},
  identities:{blenderSha256:await sha256File(blender),sceneBlendSha256:await sha256File(scenePath),ocioSha256:await sha256File(ocioPath),
    configuratorSha256:await sha256File(configurator),rendererSha256:await sha256File(renderer),analyzerSha256:await sha256File(analyzer),
    b31ResultsSha256:await sha256File(resolve(b31Root,'results.json')),b31AnalysisSha256:await sha256File(resolve(b31Root,'analysis.json'))},reports,
  nonClaims:['Derivation only; no unseen-frame confirmation.','Equal weights and offsets are candidates, not optimized production settings.','Four component renders imply an expected approximately fourfold render cost.']};
const resultPath=resolve(root,'results.json'); await writeFile(resultPath,serialize(result));
const analysisPath=resolve(root,'analysis.json'); const analyzed=await run(blender,['--factory-startup','--background','--disable-autoexec','--python-exit-code','1','--python',analyzer,'--',
  '--b32-work',work,'--b32-results',resultPath,'--b31-work',resolve(b31Root,'work'),'--b31-results',resolve(b31Root,'results.json'),'--output',analysisPath]);
process.stdout.write(analyzed.output); process.stdout.write('BFS_B32_QUADRATURE_DERIVATION_OK processes=8 renders=24\n');
