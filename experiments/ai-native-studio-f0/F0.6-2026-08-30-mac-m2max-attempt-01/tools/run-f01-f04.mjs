#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  readlinkSync,
  statfsSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, relative, resolve } from 'node:path';

const repository = resolve(process.argv[2]);
if (!repository) throw new Error('Usage: run-f01-f04.mjs <repository-root>');
const experimentRelative = 'experiments/ai-native-studio-f0/F0.6-2026-08-30-mac-m2max-attempt-01';
const experiment = resolve(repository, experimentRelative);
const regression = resolve(experiment, 'regression');
const source = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/blender-v5.2.0-src';
const product = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-f0.6-merge-drill/bin/Film Studio Engine F0.app/Contents/MacOS/Blender';
const app = dirname(dirname(dirname(product)));
const ocio = resolve(repository, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
const officialConfig = '/Users/mengyingli/Library/Application Support/Blender';
const expectedOfficialDigest = 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf';
const expectedSource = 'fa1b578bb421bbc82b3106b7d4223e11e65fae1d';
const expectedDependency = 'a76ef917b4849ba2b1b1deb1a643e131a884a63b';
const expectedBinary = '58d5c984c58d986d3cf44622ad5876052a67890d0b077dafd4977f6e2b24a71d';
const requiredFree = 160n * 1024n ** 3n;
const maxSeconds = 180;
const maxRss = 8 * 1024 ** 3;
let productStarts = 0;

const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
const now = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
const git = args => execFileSync('/usr/bin/git', ['-C', source, ...args], { encoding: 'utf8' }).trim();
const freeBytes = () => {
  const value = statfsSync(experiment, { bigint: true });
  return value.bavail * value.bsize;
};
const runningBlender = () => {
  try {
    return execFileSync('/usr/bin/pgrep', ['-x', 'Blender'], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean);
  } catch {
    return [];
  }
};
function mkdirExact(path) {
  mkdirSync(path, { recursive: false });
}
function writeJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, { flag: 'wx' });
}
function writeHashed(path, body, field) {
  const value = { ...body, [field]: prettyHash(body) };
  writeJson(path, value);
  return value;
}
function treeIdentity(root) {
  if (!existsSync(root)) return { root, state: 'ABSENT', entries: 0, digest: shaBytes('ABSENT') };
  const rows = [];
  const walk = (current, prefix = '') => {
    for (const name of readdirSync(current).sort((a, b) => a.localeCompare(b, 'en'))) {
      const path = resolve(current, name);
      const rel = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (stat.isDirectory()) {
        rows.push({ path: rel, type: 'directory', mode });
        walk(path, rel);
      } else if (stat.isSymbolicLink()) {
        rows.push({ path: rel, type: 'symlink', mode, target: readlinkSync(path) });
      } else if (stat.isFile()) {
        rows.push({ path: rel, type: 'file', mode, bytes: stat.size, sha256: shaFile(path) });
      } else {
        rows.push({ path: rel, type: 'other', mode, bytes: stat.size });
      }
    }
  };
  walk(root);
  return { root, state: 'PRESENT', entries: rows.length, digest: shaBytes(`${rows.map(row => JSON.stringify(row)).join('\n')}\n`) };
}
function parseTiming(text) {
  const seconds = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? Number.NaN);
  return {
    realSeconds: seconds('real'),
    userSeconds: seconds('user'),
    systemSeconds: seconds('sys'),
    maximumResidentSetSizeBytes: Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? Number.NaN),
  };
}
function sourceIdentity() {
  const status = git(['status', '--porcelain=v1']);
  const dependency = git(['submodule', 'status', '--', 'lib/macos_arm64']);
  return {
    branch: git(['branch', '--show-current']),
    head: git(['rev-parse', 'HEAD']),
    clean: status === '',
    status,
    dependency,
    dependencyExactAndClean: dependency === ` ${expectedDependency} lib/macos_arm64 (v5.2.1)`,
  };
}
function admission(id, expectedOutputs = []) {
  const sequence = productStarts + 1;
  const identity = sourceIdentity();
  const official = treeIdentity(officialConfig);
  const free = freeBytes();
  const running = runningBlender();
  const failures = [];
  if (identity.head !== expectedSource || !identity.clean) failures.push('SOURCE_IDENTITY');
  if (!identity.dependencyExactAndClean) failures.push('DEPENDENCY_IDENTITY');
  if (shaFile(product) !== expectedBinary) failures.push('PRODUCT_IDENTITY');
  if (official.digest !== expectedOfficialDigest) failures.push('OFFICIAL_CONFIG_DRIFT');
  if (free < requiredFree) failures.push('FREE_DISK_BELOW_160_GIB');
  if (running.length) failures.push('BLENDER_ALREADY_RUNNING');
  if (Object.keys(process.env).some(name => name.startsWith('BLENDER_USER_'))) failures.push('BLENDER_USER_OVERRIDE');
  for (const path of expectedOutputs) if (existsSync(path)) failures.push(`OUTPUT_EXISTS:${path}`);
  const body = {
    schemaVersion: 'bfs.f0.6.nativeStartAdmission.v0.1',
    id,
    formalProductStart: sequence,
    observedAtUtc: now(),
    status: failures.length ? 'REJECTED' : 'ACCEPTED',
    source: identity,
    product: { path: product, sha256: shaFile(product) },
    officialConfig,
    freeBytes: String(free),
    requiredFreeBytes: String(requiredFree),
    runningBlenderPids: running,
    expectedOutputsAbsent: expectedOutputs.map(path => ({ path, absent: !existsSync(path) })),
    maximumConcurrentNativeProcesses: 1,
    failures,
  };
  const path = resolve(regression, 'admissions', `${String(sequence).padStart(2, '0')}-${id}.json`);
  const record = writeHashed(path, body, 'admissionHash');
  if (failures.length) throw new Error(`Admission rejected for ${id}: ${failures.join(',')}`);
  productStarts = sequence;
  return record;
}
async function runProduct(id, args, { expectedOutputs = [], env = {}, maximumSeconds = maxSeconds } = {}) {
  const accepted = admission(id, expectedOutputs);
  const prefix = resolve(regression, 'processes', `${String(accepted.formalProductStart).padStart(2, '0')}-${id}`);
  const stdoutPath = `${prefix}.stdout.log`;
  const stderrPath = `${prefix}.stderr.log`;
  const timingPath = `${prefix}.timing.log`;
  const startedAtUtc = now();
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', ['-lp', '-o', timingPath, product, ...args], {
    cwd: repository,
    detached: true,
    env: { ...process.env, OCIO: ocio, LANG: 'C', LC_ALL: 'C', ...env },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
  }, maximumSeconds * 1000);
  const terminal = await new Promise((resolveResult, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolveResult({ exitCode, signal }));
  });
  clearTimeout(timer);
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  writeFileSync(stdoutPath, Buffer.concat(stdout), { flag: 'wx' });
  writeFileSync(stderrPath, Buffer.concat(stderr), { flag: 'wx' });
  const timing = parseTiming(readFileSync(timingPath, 'utf8'));
  const status = terminal.exitCode === 0 && !timedOut && timing.realSeconds <= maximumSeconds && timing.maximumResidentSetSizeBytes <= maxRss ? 'PASS' : 'FAIL';
  const body = {
    schemaVersion: 'bfs.f0.6.nativeProcessReceipt.v0.1',
    id,
    formalProductStart: accepted.formalProductStart,
    status,
    startedAtUtc,
    endedAtUtc: now(),
    command: product,
    args,
    exitCode: terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    timing: { ...timing, observedElapsedSeconds: elapsedSeconds },
    limits: { maximumSeconds, maximumResidentSetSizeBytes: maxRss },
    logs: {
      stdout: { uri: relative(regression, stdoutPath), bytes: statSync(stdoutPath).size, sha256: shaFile(stdoutPath) },
      stderr: { uri: relative(regression, stderrPath), bytes: statSync(stderrPath).size, sha256: shaFile(stderrPath) },
      timing: { uri: relative(regression, timingPath), bytes: statSync(timingPath).size, sha256: shaFile(timingPath) },
    },
  };
  const receipt = writeHashed(`${prefix}.json`, body, 'processHash');
  if (status !== 'PASS') throw new Error(`Product process failed: ${id} exit=${terminal.exitCode}`);
  return { receipt, stdout: Buffer.concat(stdout).toString('utf8'), stderr: Buffer.concat(stderr).toString('utf8') };
}
function marker(text, name) {
  const line = text.split('\n').find(row => row.startsWith(name));
  return line ? JSON.parse(line.slice(name.length)) : null;
}
function plist(key, path = resolve(app, 'Contents', 'Info.plist')) {
  return execFileSync('/usr/libexec/PlistBuddy', ['-c', `Print :${key}`, path], { encoding: 'utf8' }).trim();
}

if (existsSync(regression)) {
  const existing = readdirSync(regression).sort();
  if (JSON.stringify(existing) !== JSON.stringify(['.gitkeep'])) throw new Error(`Regression evidence root is not pristine: ${existing}`);
} else {
  mkdirExact(regression);
}
for (const name of ['admissions', 'processes', 'f03', 'f04']) mkdirExact(resolve(regression, name));
mkdirExact(resolve(regression, 'f03', 'artifacts'));
for (const name of ['external', 'embedded', 'proposals', 'approvals', 'negative-inputs', 'negative-outputs', 'runtime-contract', 'b01', 'b02']) mkdirExact(resolve(regression, 'f04', name));

const collisionFailures = ['BLENDER_USER_CONFIG'].filter(name => Boolean({ ...process.env, BLENDER_USER_CONFIG: `${officialConfig}/5.2/config` }[name])).map(name => `UNEXPECTED_${name}`);
const collision = writeHashed(resolve(regression, 'f02-collision-negative.json'), {
  schemaVersion: 'bfs.f0.6.configurationCollisionNegative.v0.1',
  status: collisionFailures.includes('UNEXPECTED_BLENDER_USER_CONFIG') ? 'REJECTED' : 'UNEXPECTED_ACCEPT',
  injectedEnvironment: { BLENDER_USER_CONFIG: `${officialConfig}/5.2/config` },
  expectedReason: 'UNEXPECTED_BLENDER_USER_CONFIG',
  observedReasons: collisionFailures,
  productStartsBefore: productStarts,
  productStartsAfter: productStarts,
  additionalProductStarts: 0,
}, 'negativeHash');
if (collision.status !== 'REJECTED') throw new Error('Configuration collision negative failed');

const runtimeExpression = [
  'import bpy,json',
  "kinds=('CONFIG','SCRIPTS','DATAFILES','EXTENSIONS')",
  'paths={kind:bpy.utils.user_resource(kind,create=True) for kind in kinds}',
  "runtime={'version':bpy.app.version_string,'buildHash':bpy.app.build_hash.decode(),'buildBranch':bpy.app.build_branch.decode(),'buildPlatform':bpy.app.build_platform.decode(),'binaryPath':bpy.app.binary_path,'paths':paths}",
  "print('F06_RUNTIME='+json.dumps(runtime,sort_keys=True),flush=True)",
  'bpy.context.preferences.view.show_splash=not bpy.context.preferences.view.show_splash',
  'saved=sorted(bpy.ops.wm.save_userpref())',
  'reset=sorted(bpy.ops.wm.read_factory_userpref())',
  'saved_after=sorted(bpy.ops.wm.save_userpref())',
  "print('F06_CONFIG_ACTIONS='+json.dumps({'saved':saved,'reset':reset,'savedAfterReset':saved_after},sort_keys=True),flush=True)",
].join(';');
const identityRun = await runProduct('f01-f02-runtime', ['--background', '--factory-startup', '--python-exit-code', '90', '--python-expr', runtimeExpression]);
const combinedIdentity = `${identityRun.stdout}\n${identityRun.stderr}`;
const runtime = marker(combinedIdentity, 'F06_RUNTIME=');
const actions = marker(combinedIdentity, 'F06_CONFIG_ACTIONS=');
const expectedConfigRoot = '/Users/mengyingli/Library/Application Support/FilmStudioEngineF0/5.2';
const identityChecks = {
  runtimeMarker: runtime !== null,
  version: runtime?.version === '5.2.1 LTS',
  buildHash: runtime?.buildHash === 'fa1b578bb421',
  buildBranch: runtime?.buildBranch === 'codex/f0.6-upstream-merge-drill',
  buildPlatform: runtime?.buildPlatform === 'Darwin',
  binaryPath: runtime?.binaryPath === product,
  bundleName: plist('CFBundleName') === 'Film Studio Engine F0',
  bundleIdentifier: plist('CFBundleIdentifier') === 'studio.ainativefilm.f0',
  configurationNamespace: runtime && Object.values(runtime.paths).every(path => path.startsWith(expectedConfigRoot)),
  preferenceActions: actions && ['saved', 'reset', 'savedAfterReset'].every(name => actions[name]?.includes('FINISHED')),
  officialConfigUnchanged: treeIdentity(officialConfig).digest === expectedOfficialDigest,
  collisionRejectedBeforeStart: collision.status === 'REJECTED' && collision.additionalProductStarts === 0,
};
writeHashed(resolve(regression, 'f01-f02.json'), {
  schemaVersion: 'bfs.f0.6.f01F02Regression.v0.1',
  status: Object.values(identityChecks).every(Boolean) ? 'PASS' : 'FAIL',
  runtime,
  actions,
  collisionNegativeHash: collision.negativeHash,
  processHash: identityRun.receipt.processHash,
  checks: identityChecks,
}, 'receiptHash');
if (!Object.values(identityChecks).every(Boolean)) throw new Error(`F0.1/F0.2 failed: ${JSON.stringify(identityChecks)}`);

const f03Script = resolve(repository, 'scripts/f0-workspace-audit.py');
const persistence = resolve(regression, 'f03/artifacts/workspace-persistence.blend');
const missing = resolve(regression, 'f03/artifacts/workspace-missing-optional.blend');
const stageRows = [];
for (const stage of ['create-save', 'reopen', 'missing-prepare', 'missing-reopen']) {
  const stageRoot = resolve(regression, 'f03', stage);
  mkdirExact(stageRoot);
  const output = resolve(stageRoot, 'result.json');
  const blend = stage.startsWith('missing-') ? missing : persistence;
  const input = stage === 'reopen' || stage === 'missing-prepare' ? persistence : stage === 'missing-reopen' ? missing : null;
  const args = ['--background'];
  if (input) args.push(input); else args.push('--factory-startup');
  args.push('--python-exit-code', '86', '--python', f03Script, '--', '--stage', stage, '--output', output, '--blend', blend);
  const process = await runProduct(`f03-${stage}`, args, { expectedOutputs: [output] });
  const result = JSON.parse(readFileSync(output));
  stageRows.push({ stage, status: result.status, checks: result.checks, operations: result.operations, processHash: process.receipt.processHash, resultSha256: shaFile(output) });
}
const expertOutput = resolve(regression, 'f03/expert-roundtrip.json');
const expertProcess = await runProduct('f03-expert-roundtrip', ['--background', persistence, '--python-exit-code', '86', '--python', resolve(experiment, 'tools/expert-roundtrip.py'), '--', '--output', expertOutput], { expectedOutputs: [expertOutput] });
const expert = JSON.parse(readFileSync(expertOutput));
const f03Checks = {
  allFourPersistenceStagesPassed: stageRows.every(row => row.status === 'PASS' && Object.values(row.checks).every(Boolean)),
  typedWorkspaceSchema: JSON.parse(readFileSync(resolve(regression, 'f03/create-save/result.json'))).after.schemaVersion === 'bfs.filmWorkspace.v0.1',
  createShotSemanticOperation: stageRows[0].operations.createShot?.includes('FINISHED'),
  independentReopen: stageRows[1].status === 'PASS',
  missingOptionalRecovery: stageRows[3].operations.createShot?.includes('FINISHED'),
  expertRoundTrip: expert.status === 'PASS' && Object.values(expert.checks).every(Boolean),
};
writeHashed(resolve(regression, 'f03/receipt.json'), {
  schemaVersion: 'bfs.f0.6.f03Regression.v0.1',
  status: Object.values(f03Checks).every(Boolean) ? 'PASS' : 'FAIL',
  stages: stageRows,
  expert: { fileSha256: shaFile(expertOutput), processHash: expertProcess.receipt.processHash, receiptHash: expert.receiptHash },
  checks: f03Checks,
}, 'receiptHash');
if (!Object.values(f03Checks).every(Boolean)) throw new Error('F0.3 regression failed');

const priorF04 = resolve(repository, 'experiments/ai-native-studio-f0/F0.4-2026-08-30-mac-m2max-attempt-01');
const frozenFiles = {
  'external/B01.build-plan.json': 'b6ab475728481a7ff6850c2eee1585bab9ac532f49b875a6016cad4be1ffc8be',
  'external/B02.build-plan.json': '8595f30c78b3d2d0266c94d05e2e37b8d90c7864d2c904b6c2e58abc164f187d',
};
for (const [name, expected] of Object.entries(frozenFiles)) {
  const prior = resolve(priorF04, name);
  if (shaFile(prior) !== expected) throw new Error(`Frozen F0.4 fixture drift: ${name}`);
  writeFileSync(resolve(regression, 'f04', name), readFileSync(prior), { flag: 'wx' });
}
for (const id of ['B01', 'B02']) {
  const proposal = JSON.parse(readFileSync(resolve(priorF04, `proposals/${id}.proposal.json`)));
  proposal.proposalId = `F0.6-F0.4-${id}-COMPILE`;
  proposal.requestedOutput.uri = `${experimentRelative}/regression/f04/embedded/${id}.build-plan.json`;
  const proposalRelative = `${experimentRelative}/regression/f04/proposals/${id}.proposal.json`;
  const proposalPath = resolve(repository, proposalRelative);
  writeJson(proposalPath, proposal);
  const approval = JSON.parse(readFileSync(resolve(priorF04, `approvals/${id}.approval.json`)));
  approval.approvalId = `F0.6-F0.4-${id}-APPROVAL`;
  approval.authorizedAtUtc = now();
  approval.proposal = { uri: proposalRelative, fileSha256: shaFile(proposalPath) };
  approval.approvedOutput = { ...proposal.requestedOutput };
  writeJson(resolve(regression, `f04/approvals/${id}.approval.json`), approval);
}
const f04Relative = `${experimentRelative}/regression/f04`;
const contractRun = await runProduct('f04-contract', ['--background', '--factory-startup', '--python-exit-code', '86', '--python', resolve(priorF04, 'formal-contract-run.py'), '--', '--repository-root', repository, '--evidence-root', f04Relative]);
const comparison = JSON.parse(readFileSync(resolve(regression, 'f04/canonical-comparison.json')));
const negatives = JSON.parse(readFileSync(resolve(regression, 'f04/negative-fixtures.json')));
const proposalDiff = JSON.parse(readFileSync(resolve(regression, 'f04/proposal-diff.json')));
const planExpected = {
  B01: ['316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf', 'e8c55fb73737f1871ac0008faa705dc204ebfe5bac471323cbb0a2d31435b4f8'],
  B02: ['a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687', 'd197b024c3b1de19c7fa981912c584de51d6d4884ef78b10e29db598ce979954'],
};
const buildRows = [];
for (const id of ['B01', 'B02']) {
  const outputRelative = `${f04Relative}/${id.toLowerCase()}/artifacts`;
  const output = resolve(repository, outputRelative);
  const manifestPath = resolve(output, 'scene.manifest.json');
  const process = await runProduct(`f04-${id.toLowerCase()}-build`, ['--background', '--factory-startup', '--python-exit-code', '86', '--python', resolve(repository, 'blender/compile_scene.py'), '--', '--plan', resolve(regression, `f04/embedded/${id}.build-plan.json`), '--repository-root', repository, '--output-dir', outputRelative], { expectedOutputs: [manifestPath] });
  const manifest = JSON.parse(readFileSync(manifestPath));
  const checks = {
    planHash: manifest.execution.planHash === planExpected[id][0],
    semanticHash: manifest.structureHash === planExpected[id][1] && shaFile(resolve(output, 'scene.structure.canonical.json')) === planExpected[id][1],
    provenance: JSON.stringify(manifest.execution.blender) === JSON.stringify({ version: '5.2.1 LTS', buildHash: 'fa1b578bb421', buildBranch: 'codex/f0.6-upstream-merge-drill', buildPlatform: 'Darwin' }),
    sceneBlendPresent: existsSync(resolve(output, 'scene.blend')),
  };
  buildRows.push({ id, status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, processHash: process.receipt.processHash, manifestSha256: shaFile(manifestPath), blendSha256: shaFile(resolve(output, 'scene.blend')) });
}
const auditPath = resolve(regression, 'f04/audit.json');
const auditRun = await runProduct('f04-independent-audit', ['--background', '--factory-startup', '--python-exit-code', '86', '--python', resolve(experiment, 'tools/audit-f04.py'), '--', '--evidence', resolve(regression, 'f04'), '--output', auditPath], { expectedOutputs: [auditPath] });
const audit = JSON.parse(readFileSync(auditPath));
const f04Checks = {
  canonicalByteExact: comparison.status === 'PASS' && comparison.comparisons.every(row => row.byteExact),
  proposalInspectionBeforeExecution: proposalDiff.status === 'PASS',
  fourNegativesBeforeMutation: negatives.status === 'PASS' && negatives.cases.length === 4 && negatives.cases.every(row => row.passed && row.sceneMutations === 0),
  isolatedBuilds: buildRows.every(row => row.status === 'PASS'),
  mergedProvenanceSeparate: buildRows.every(row => row.checks.provenance && row.checks.semanticHash),
  independentAudit: audit.status === 'PASS' && audit.renderCalls === 0,
};
writeHashed(resolve(regression, 'f04/receipt.json'), {
  schemaVersion: 'bfs.f0.6.f04Regression.v0.1',
  status: Object.values(f04Checks).every(Boolean) ? 'PASS' : 'FAIL',
  contractProcessHash: contractRun.receipt.processHash,
  builds: buildRows,
  audit: { fileSha256: shaFile(auditPath), auditHash: audit.auditHash, processHash: auditRun.receipt.processHash },
  checks: f04Checks,
}, 'receiptHash');
if (!Object.values(f04Checks).every(Boolean)) throw new Error('F0.4 regression failed');

const finalSource = sourceIdentity();
const finalOfficial = treeIdentity(officialConfig);
const checks = {
  F01F02: JSON.parse(readFileSync(resolve(regression, 'f01-f02.json'))).status === 'PASS',
  F03: JSON.parse(readFileSync(resolve(regression, 'f03/receipt.json'))).status === 'PASS',
  F04: JSON.parse(readFileSync(resolve(regression, 'f04/receipt.json'))).status === 'PASS',
  productStartsExact: productStarts === 10,
  maximumConcurrentProductProcesses: runningBlender().length === 0,
  sourceUnchangedAndClean: finalSource.head === expectedSource && finalSource.clean && finalSource.dependencyExactAndClean,
  officialConfigUnchanged: finalOfficial.digest === expectedOfficialDigest,
};
const partial = writeHashed(resolve(regression, 'f01-f04.json'), {
  schemaVersion: 'bfs.f0.6.regressionPartial.v0.1',
  status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
  productStarts,
  maximumConcurrentNativeProcesses: 1,
  sourceAfter: finalSource,
  officialConfigAfter: finalOfficial,
  checks,
}, 'receiptHash');
if (partial.status !== 'PASS') throw new Error('F0.1-F0.4 partial regression failed');
console.log(`F06_F01_F04 PASS starts=${productStarts} source=${finalSource.head.slice(0, 12)}`);
