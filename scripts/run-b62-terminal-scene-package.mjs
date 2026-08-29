#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstat, mkdir, open, readFile, realpath, readdir, statfs } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';

const execFileAsync = promisify(execFile);
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const PREREGISTRATION_COMMIT = '1043af5d7b0767e87d851ea882d859bcacb61bf0';
const EXPERIMENT_URI = 'specs/b62-terminal-scene-package-compiler.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b62-terminal-scene-package-compiler-protocol.md';
const SCENE_SPEC_URI = 'specs/b62-terminal-proof.scene-package.v0.1.json';
const ROOT_URI = 'experiments/b62-terminal-scene-package-v0-1';
const OCIO_URI = 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio';
const OCIO_SHA256 = '24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15';
const TOOLS = [
  'scripts/compile-b62-terminal-build-plan.mjs',
  'blender/compile_b62_terminal_scene.py',
  'blender/audit_b62_terminal_scene.py',
  'scripts/run-b62-terminal-scene-package.mjs',
  'scripts/audit-b62-terminal-scene-package.mjs',
];

function req(condition, message) { if (!condition) throw new Error(message); }
function normalize(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (typeof value === 'number' && Number.isFinite(value)) { const bytes = Buffer.alloc(8); bytes.writeDoubleBE(value); return { $f64be: bytes.toString('hex') }; } if (Array.isArray(value)) return value.map(normalize); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalize(child)])); return value; }
function normalizeLegacy(value) { if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) return value; if (Array.isArray(value)) return value.map(normalizeLegacy); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, normalizeLegacy(child)])); return value; }
const canonicalJson = value => JSON.stringify(normalize(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => hashBytes(await readFile(path));
function validSelf(value, field, mode = 'f64') { if (!value || !/^[0-9a-f]{64}$/.test(value[field] ?? '')) return false; const copy = structuredClone(value), expected = copy[field]; delete copy[field]; return hashBytes(mode === 'legacy' ? JSON.stringify(normalizeLegacy(copy)) : canonicalJson(copy)) === expected; }
function pathFor(uri) { req(typeof uri === 'string' && uri.length > 0 && !uri.startsWith('/') && !uri.split('/').includes('..') && !uri.includes('\\'), `unsafe ${uri}`); const path = resolve(repositoryRoot, uri); req(!relative(repositoryRoot, path).startsWith('../'), `escaped ${uri}`); return path; }
async function checkedExistingPath(uri) { const path = pathFor(uri), resolved = await realpath(path); req(path === resolved && !relative(repositoryRoot, resolved).startsWith('../'), `symlink or realpath escape ${uri}`); return path; }
async function exists(path) { try { await lstat(path); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; } }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function committedHash(commit, uri) { return hashBytes(await git(['show', `${commit}:${uri}`], null)); }
async function writeHashed(path, value, field) { const body = structuredClone(value); body[field] = hashBytes(canonicalJson(body)); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(body, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return body; }
async function treeIdentity(uri) { const root = pathFor(uri), files = []; async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(`special file ${path}`); } } await walk(root); files.sort(); let bytes = 0, material = ''; for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${hashBytes(content)}\n`; } return { files: files.length, bytes, treeSha256: hashBytes(Buffer.from(material)) }; }
function parse() { const args = process.argv.slice(2); req(args.length === 2 && args[0] === '--tool-freeze-commit' && /^[0-9a-f]{40}$/.test(args[1]), 'usage: --tool-freeze-commit <sha>'); return args[1]; }

async function processReceipt(root, id, command, args, result) {
  return writeHashed(resolve(root, 'processes', `${id}.json`), { schemaVersion: 'bfs.b62TerminalProcessReceipt.v0.1', experimentId: 'B62-T1-E1', processId: id, command, args, result }, 'processHash');
}

let experiment;
async function runChild({ root, id, command, args, wallSeconds, maxRssBytes }) {
  const result = await runBudgetedProcess({ command, args, cwd: repositoryRoot, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' }, outputRoot: root, budgets: { wallTimeMs: wallSeconds * 1000, maxRssBytes, maxLogBytes: experiment.processBudget.maximumCombinedLogBytesPerChild, maxOutputFiles: 96, maxOutputBytes: experiment.processBudget.maximumOutputBytes, sampleIntervalMs: 100 } });
  const receipt = await processReceipt(root, id, command, args.map(value => typeof value === 'string' && value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
  req(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `${id} failed`);
  return receipt;
}

async function runBlender({ root, id, scene, tool, args, wallSeconds }) {
  const command = experiment.runtime.blender.executable;
  const fullArgs = ['--background', '--factory-startup', '--disable-autoexec', scene, '--python-exit-code', '1', '--python', pathFor(tool), '--', ...args];
  const ocio = pathFor(OCIO_URI);
  const result = await runBudgetedProcess({ command, args: fullArgs, cwd: repositoryRoot, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: ocio }, outputRoot: root, budgets: { wallTimeMs: wallSeconds * 1000, maxRssBytes: experiment.processBudget.maximumPeakResidentSetSizeBytesPerBlender, maxLogBytes: experiment.processBudget.maximumCombinedLogBytesPerChild, maxOutputFiles: 96, maxOutputBytes: experiment.processBudget.maximumOutputBytes, sampleIntervalMs: 100 } });
  const receipt = await processReceipt(root, id, command, fullArgs.map(value => value.startsWith(repositoryRoot) ? relative(repositoryRoot, value).split('\\').join('/') : value), result);
  req(result.outcome === 'PASS' && result.child.exitCode === 0 && result.breach === null, `${id} failed`);
  return receipt;
}

async function validateBound(binding, field, mode, semantic) {
  const path = await checkedExistingPath(binding.uri);
  req(await hashFile(path) === binding.sha256, `parent file drift ${binding.uri}`);
  const document = JSON.parse(await readFile(path, 'utf8'));
  req(validSelf(document, field, mode) && document[field] === binding[field], `parent self hash invalid ${binding.uri}`);
  semantic(document);
  return document;
}

async function main() {
  const freeze = parse();
  experiment = JSON.parse(await readFile(await checkedExistingPath(EXPERIMENT_URI), 'utf8'));
  req(experiment.experimentId === 'B62-T1-E1' && experiment.statusBeforeToolCreation === 'PREREGISTERED' && experiment.output.formalRoot === ROOT_URI, 'experiment mismatch');
  req(experiment.toolFreeze.requiredNewTools.join('\0') === TOOLS.join('\0'), 'tool roster mismatch');
  req(!await exists(pathFor(ROOT_URI)), 'formal root exists');
  const head = (await git(['rev-parse', 'HEAD'])).trim(), origin = (await git(['rev-parse', 'origin/main'])).trim();
  req(head === freeze && origin === freeze, 'tool freeze is not pushed HEAD');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  for (const uri of [EXPERIMENT_URI, PROTOCOL_URI, SCENE_SPEC_URI]) req(await hashFile(await checkedExistingPath(uri)) === await committedHash(PREREGISTRATION_COMMIT, uri), `preregistration drift ${uri}`);
  const toolHashes = {};
  for (const uri of TOOLS) { toolHashes[uri] = await hashFile(await checkedExistingPath(uri)); req(toolHashes[uri] === await committedHash(freeze, uri), `tool drift ${uri}`); }
  const scoped = [EXPERIMENT_URI, PROTOCOL_URI, SCENE_SPEC_URI, ROOT_URI, OCIO_URI, ...TOOLS, ...Object.values(experiment.parentEvidence.phase0).map(value => value.uri), ...Object.values(experiment.parentEvidence.d6).map(value => value.uri)];
  req((await git(['status', '--porcelain=v1', '--', ...scoped])).trim() === '', 'scoped worktree dirty');
  const sceneSpecPath = await checkedExistingPath(SCENE_SPEC_URI);
  req(await hashFile(sceneSpecPath) === experiment.inputSceneSpec.sha256, 'ScenePackageSpec drift');
  const phase0Generation = await validateBound(experiment.parentEvidence.phase0.generation, 'reportHash', 'legacy', value => req(value.status === 'PASS', 'Phase 0 generation not PASS'));
  await validateBound(experiment.parentEvidence.phase0.audit, 'auditHash', 'legacy', value => req(value.status === 'PASS' && value.verdict === experiment.parentEvidence.phase0.audit.verdict, 'Phase 0 audit not admitted'));
  await validateBound(experiment.parentEvidence.phase0.receipt, 'receiptHash', 'legacy', value => req(value.status === 'PASS', 'Phase 0 receipt not PASS'));
  const d6Build = await validateBound(experiment.parentEvidence.d6.build, 'reportHash', 'f64', value => req(value.status === 'PASS' && value.bake.length === 96, 'D6 build invalid'));
  await validateBound(experiment.parentEvidence.d6.audit, 'auditHash', 'f64', value => req(value.status === 'PASS' && value.scientificVerdict === experiment.parentEvidence.d6.audit.scientificVerdict, 'D6 audit not admitted'));
  await validateBound(experiment.parentEvidence.d6.receipt, 'receiptHash', 'f64', value => req(value.status === 'PASS' && value.scientificVerdict === experiment.parentEvidence.d6.audit.scientificVerdict, 'D6 receipt not admitted'));
  await validateBound(experiment.parentEvidence.d6.humanReview, 'reviewHash', 'f64', value => req(value.status === 'PASS' && value.scope === experiment.parentEvidence.d6.humanReview.scope, 'D6 human review invalid'));
  req(phase0Generation.timeline.frameStart === 1 && phase0Generation.timeline.frameEnd === 288 && phase0Generation.timeline.fps === 24 && d6Build.bake.every((row, index) => row.frame === 193 + index), 'parent timeline/bake roster drift');
  const master = await checkedExistingPath(experiment.parentEvidence.phase0.master.uri);
  req(await hashFile(master) === experiment.parentEvidence.phase0.master.sha256, 'master drift');
  req(await hashFile(experiment.runtime.blender.executable) === experiment.runtime.blender.sha256, 'Blender binary drift');
  req(await hashFile(await checkedExistingPath(OCIO_URI)) === OCIO_SHA256, 'OCIO config drift');
  req(Number.parseInt(process.versions.node.split('.')[0], 10) >= 22, 'Node runtime too old');
  const filesystem = await statfs(repositoryRoot), available = Number(filesystem.bavail) * Number(filesystem.bsize);
  req(available - experiment.processBudget.projectedWriteBytes >= experiment.processBudget.minimumFreeReserveBytes, 'disk reserve admission failed');

  const root = pathFor(ROOT_URI);
  await mkdir(resolve(root, 'processes'), { recursive: true, mode: 0o700 });
  await mkdir(resolve(root, 'reports'), { recursive: true, mode: 0o700 });
  await mkdir(resolve(root, 'scene'), { recursive: true, mode: 0o700 });
  const admission = await writeHashed(resolve(root, 'admission.json'), {
    schemaVersion: 'bfs.b62TerminalScenePackageAdmission.v0.1', experimentId: 'B62-T1-E1', status: 'ADMITTED', preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: freeze,
    bindings: { experiment: { uri: EXPERIMENT_URI, sha256: await hashFile(pathFor(EXPERIMENT_URI)) }, protocol: { uri: PROTOCOL_URI, sha256: await hashFile(pathFor(PROTOCOL_URI)) }, sceneSpec: { uri: SCENE_SPEC_URI, sha256: await hashFile(sceneSpecPath) }, phase0: experiment.parentEvidence.phase0, d6: experiment.parentEvidence.d6, master: experiment.parentEvidence.phase0.master, blender: { ...experiment.runtime.blender, observedSha256: await hashFile(experiment.runtime.blender.executable) }, ocio: { uri: OCIO_URI, sha256: OCIO_SHA256 }, tools: toolHashes },
    resources: { availableBytesBefore: available, projectedWriteBytes: experiment.processBudget.projectedWriteBytes, maximumOutputBytes: experiment.processBudget.maximumOutputBytes, minimumFreeReserveBytes: experiment.processBudget.minimumFreeReserveBytes },
    operations: { nativeProcessesBeforeAdmission: 0, blenderStartsBeforeAdmission: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'admissionHash');

  try {
    const planUri = `${ROOT_URI}/${experiment.output.buildPlan}`;
    const planPath = pathFor(planUri);
    const planArgsA = [pathFor(TOOLS[0]), '--spec', SCENE_SPEC_URI, '--tool-freeze-commit', freeze, '--output', planUri];
    const planA = await runChild({ root, id: 'BUILDPLAN_A', command: process.execPath, args: planArgsA, wallSeconds: 60, maxRssBytes: 536870912 });
    const planArgsB = [pathFor(TOOLS[0]), '--spec', SCENE_SPEC_URI, '--tool-freeze-commit', freeze, '--verify', planUri];
    const planB = await runChild({ root, id: 'BUILDPLAN_B', command: process.execPath, args: planArgsB, wallSeconds: 60, maxRssBytes: 536870912 });
    const plan = JSON.parse(await readFile(planPath, 'utf8'));
    req(validSelf(plan, 'planHash', 'f64') && plan.status === 'COMPILED' && plan.camera.samples.length === 96, 'BuildPlan invalid after dual compile');
    const derived = resolve(root, experiment.output.scene), compileReportPath = resolve(root, experiment.output.compileReport);
    const compile = await runBlender({ root, id: 'BLENDER_COMPILE', scene: master, tool: TOOLS[1], args: ['--build-plan', planPath, '--output-scene', derived, '--report', compileReportPath], wallSeconds: experiment.processBudget.maximumCompileWallSeconds });
    const compileReport = JSON.parse(await readFile(compileReportPath, 'utf8'));
    req(validSelf(compileReport, 'reportHash', 'f64') && compileReport.status === 'PASS' && await hashFile(derived) === compileReport.derived.sha256, 'compile report invalid');
    const independentPath = resolve(root, experiment.output.independentReport);
    const independent = await runBlender({ root, id: 'BLENDER_INDEPENDENT', scene: derived, tool: TOOLS[2], args: ['--build-plan', planPath, '--compile-report', compileReportPath, '--derived-sha256', compileReport.derived.sha256, '--output', independentPath], wallSeconds: experiment.processBudget.maximumIndependentWallSeconds });
    const independentReport = JSON.parse(await readFile(independentPath, 'utf8'));
    req(validSelf(independentReport, 'reportHash', 'f64') && independentReport.status === 'PASS', 'independent report invalid');
    req(await hashFile(master) === experiment.parentEvidence.phase0.master.sha256, 'source master changed after compile');
    const auditorArgs = [pathFor(TOOLS[4]), '--root', ROOT_URI, '--tool-freeze-commit', freeze];
    const auditor = await runChild({ root, id: 'NODE_AUDITOR', command: process.execPath, args: auditorArgs, wallSeconds: 60, maxRssBytes: 1073741824 });
    const auditPath = resolve(root, experiment.output.audit), audit = JSON.parse(await readFile(auditPath, 'utf8'));
    req(validSelf(audit, 'auditHash', 'f64') && audit.status === 'PASS' && audit.scientificVerdict === experiment.decision.supportedVerdict, 'Node audit invalid');
    const preReceiptTree = await treeIdentity(ROOT_URI);
    const receipt = await writeHashed(resolve(root, experiment.output.receipt), {
      schemaVersion: 'bfs.b62TerminalScenePackageReceipt.v0.1', experimentId: 'B62-T1-E1', status: 'PASS', scientificVerdict: audit.scientificVerdict, preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: freeze,
      admission: { uri: `${ROOT_URI}/admission.json`, sha256: await hashFile(resolve(root, 'admission.json')), admissionHash: admission.admissionHash },
      buildPlan: { uri: planUri, sha256: await hashFile(planPath), planHash: plan.planHash },
      compile: { uri: `${ROOT_URI}/${experiment.output.compileReport}`, sha256: await hashFile(compileReportPath), reportHash: compileReport.reportHash, derivedSha256: compileReport.derived.sha256 },
      independent: { uri: `${ROOT_URI}/${experiment.output.independentReport}`, sha256: await hashFile(independentPath), reportHash: independentReport.reportHash, maximumPoseError: independentReport.maximumPoseError },
      audit: { uri: `${ROOT_URI}/${experiment.output.audit}`, sha256: await hashFile(auditPath), auditHash: audit.auditHash },
      processes: {
        buildPlanA: { uri: `${ROOT_URI}/processes/BUILDPLAN_A.json`, sha256: await hashFile(resolve(root, 'processes/BUILDPLAN_A.json')), processHash: planA.processHash },
        buildPlanB: { uri: `${ROOT_URI}/processes/BUILDPLAN_B.json`, sha256: await hashFile(resolve(root, 'processes/BUILDPLAN_B.json')), processHash: planB.processHash },
        blenderCompile: { uri: `${ROOT_URI}/processes/BLENDER_COMPILE.json`, sha256: await hashFile(resolve(root, 'processes/BLENDER_COMPILE.json')), processHash: compile.processHash },
        blenderIndependent: { uri: `${ROOT_URI}/processes/BLENDER_INDEPENDENT.json`, sha256: await hashFile(resolve(root, 'processes/BLENDER_INDEPENDENT.json')), processHash: independent.processHash },
        nodeAuditor: { uri: `${ROOT_URI}/processes/NODE_AUDITOR.json`, sha256: await hashFile(resolve(root, 'processes/NODE_AUDITOR.json')), processHash: auditor.processHash },
      },
      preReceiptRoot: preReceiptTree,
      operations: { runnerProcesses: 1, buildPlanCompilerProcesses: 2, blenderStarts: 2, sceneSaves: 1, renderCalls: 0, nodeAuditorProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
      nextAuthorization: experiment.nextAuthorization, nonClaims: experiment.nonClaims,
    }, 'receiptHash');
    console.log(`BFS_B62_T1 PASS ${receipt.scientificVerdict} ${receipt.receiptHash}`);
  } catch (error) {
    if (!await exists(resolve(root, 'failure.json'))) await writeHashed(resolve(root, 'failure.json'), { schemaVersion: 'bfs.b62TerminalScenePackageFailure.v0.1', experimentId: 'B62-T1-E1', status: 'INVALIDATED', scientificVerdict: null, preregistrationCommit: PREREGISTRATION_COMMIT, toolFreezeCommit: freeze, reason: error.message }, 'failureHash');
    throw error;
  }
}

main().catch(error => { console.error(error.stack ?? error.message); process.exitCode = 1; });
