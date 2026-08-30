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
  rmdirSync,
  statfsSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs';
import { basename, dirname, relative, resolve } from 'node:path';

const repository = resolve(process.argv[2]);
const evidenceRelative = process.argv[3];
if (!repository || !evidenceRelative) throw new Error('Usage: run-f07.mjs <repository-root> <evidence-root-relative>');
const evidence = resolve(repository, evidenceRelative);
const sourceApp = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-f0.6-merge-drill/bin/Film Studio Engine F0.app';
const sourceBinary = resolve(sourceApp, 'Contents/MacOS/Blender');
const packageRoot = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/F0.7-packages-attempt-02';
const stagingRoot = resolve(packageRoot, 'staging');
const stagingApp = resolve(stagingRoot, 'Film Studio Engine F0.app');
const dmg = resolve(packageRoot, 'Film-Studio-Engine-F0-5.2.1-unsigned.dmg');
const mountpoint = resolve(packageRoot, 'mount-audit');
const installApp = '/Users/mengyingli/Applications/Film Studio Engine F0.app';
const officialRuntime = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-a/bin/Blender.app/Contents/MacOS/Blender';
const officialApp = '/Applications/Blender.app';
const officialConfig = '/Users/mengyingli/Library/Application Support/Blender';
const officialCache = '/Users/mengyingli/Library/Caches/Blender';
const f0Config = '/Users/mengyingli/Library/Application Support/FilmStudioEngineF0';
const f0Cache = '/Users/mengyingli/Library/Caches/FilmStudioEngineF0';
const stageScript = resolve(evidence, 'tools/roundtrip-stage.py');
const auditScript = resolve(evidence, 'tools/audit-f07.mjs');
const expected = {
  sourceTree: 'c3a055c025bf8d8e20688447e17ca1fd0c583d555168fba62b3a583c050eddbe',
  sourceFiles: 6008,
  pycFiles: 521,
  pycacheDirectories: 70,
  normalizedFiles: 5487,
  productBinary: '58d5c984c58d986d3cf44622ad5876052a67890d0b077dafd4977f6e2b24a71d',
  officialRuntimeBinary: 'cf0fa6bb8cca9621d39637dfbcfa9990abcbf9ccaafc5edd8306967d9aaaad3e',
  officialAppTree: 'bdcf8064f0fae603eed3edabaddff2f5134e40ed49a24bd7ed23f4b36ac94743',
  officialAppBinary: 'e0b80264bea559673212e0afc819fb33f3cef8b3dcfcc8d994b195132857ac8a',
  officialConfig: 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf',
  officialCache: '43c285a9c90490923b3dcd068a15c2b72921c1c7bf76389ce7c1367695864818',
  f0Config: 'd77cc65db6f3577a028e1ab2895e8ecacbe9574a1b734ec0c091af275f51606d',
  f0Cache: 'e2e8c6da1214de5681a73eac7ce06e101111a0a94ec85787b8d2c3b160eceaba',
};
const requiredInitialFree = 160n * 1024n ** 3n;
const reserve = 100n * 1024n ** 3n;
const projectedPackageWrite = 2n * 1024n ** 3n;
const projectedRoundtripWrite = 64n * 1024n ** 2n;
const maxSeconds = 60;
const maxDmgCompressionSeconds = 180;
const maxRss = 2 * 1024 ** 3;
const maxBlendBytes = 16 * 1024 ** 2;
const maxEvidenceBytes = 64 * 1024 ** 2;
let productStarts = 0;

const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
const now = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
const freeBytes = () => { const value = statfsSync(evidence, { bigint: true }); return value.bavail * value.bsize; };
const runningBlender = () => {
  try { return execFileSync('/usr/bin/pgrep', ['-x', 'Blender'], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean); } catch { return []; }
};
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function validSelf(path, field, canonicalHash = false) {
  const value = JSON.parse(readFileSync(path));
  const observed = value[field];
  delete value[field];
  return observed === (canonicalHash ? shaBytes(canonical(value)) : prettyHash(value));
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
  if (!existsSync(root)) return { root, state: 'ABSENT', entries: 0, files: 0, directories: 0, logicalBytes: 0, digest: shaBytes('ABSENT') };
  const rows = [];
  let files = 0;
  let directories = 0;
  let logicalBytes = 0;
  const walk = (current, prefix = '') => {
    for (const name of readdirSync(current).sort((a, b) => a.localeCompare(b, 'en'))) {
      const path = resolve(current, name);
      const rel = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (stat.isDirectory()) {
        directories += 1;
        rows.push({ path: rel, type: 'directory', mode });
        walk(path, rel);
      } else if (stat.isSymbolicLink()) {
        rows.push({ path: rel, type: 'symlink', mode, target: readlinkSync(path) });
      } else if (stat.isFile()) {
        files += 1;
        logicalBytes += stat.size;
        rows.push({ path: rel, type: 'file', mode, bytes: stat.size, sha256: shaFile(path) });
      } else {
        rows.push({ path: rel, type: 'other', mode, bytes: stat.size });
      }
    }
  };
  walk(root);
  return { root, state: 'PRESENT', entries: rows.length, files, directories, logicalBytes, digest: shaBytes(`${rows.map(row => JSON.stringify(row)).join('\n')}\n`) };
}
function parseTiming(text) {
  const number = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? Number.NaN);
  return {
    realSeconds: number('real'),
    userSeconds: number('user'),
    systemSeconds: number('sys'),
    maximumResidentSetSizeBytes: Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? Number.NaN),
  };
}
function ensureFrozenInputs() {
  const source = treeIdentity(sourceApp);
  const official = treeIdentity(officialApp);
  if (source.digest !== expected.sourceTree || source.files !== expected.sourceFiles) throw new Error('Frozen source app identity mismatch');
  if (shaFile(sourceBinary) !== expected.productBinary) throw new Error('Frozen product binary mismatch');
  if (shaFile(officialRuntime) !== expected.officialRuntimeBinary) throw new Error('Frozen official round-trip binary mismatch');
  if (official.digest !== expected.officialAppTree || shaFile(resolve(officialApp, 'Contents/MacOS/Blender')) !== expected.officialAppBinary) throw new Error('Installed official Blender identity mismatch');
  for (const [path, digest] of [[officialConfig, expected.officialConfig], [officialCache, expected.officialCache], [f0Config, expected.f0Config], [f0Cache, expected.f0Cache]]) {
    if (treeIdentity(path).digest !== digest) throw new Error(`Frozen configuration identity mismatch: ${path}`);
  }
  if (!validSelf(resolve(evidence, 'tool-freeze.json'), 'freezeHash') || !validSelf(resolve(evidence, 'formal-start.json'), 'formalStartHash')) throw new Error('Tool freeze or formal start is invalid');
  if (runningBlender().length) throw new Error('Blender already running before F0.7');
  return { source, official };
}
function packageAdmission(sequence, id, { projectedBytes, outputs = [], initial = false }) {
  const free = freeBytes();
  const running = runningBlender();
  const minimum = initial ? requiredInitialFree : reserve + projectedBytes;
  const failures = [];
  if (free < minimum) failures.push('INSUFFICIENT_FREE_SPACE');
  if (running.length) failures.push('BLENDER_ALREADY_RUNNING');
  for (const output of outputs) if (existsSync(output)) failures.push(`OUTPUT_EXISTS:${output}`);
  const body = {
    schemaVersion: 'bfs.f0.7.packageAdmission.v0.1', sequence, id, observedAtUtc: now(),
    status: failures.length ? 'REJECTED' : 'ACCEPTED', failures,
    freeBytes: String(free), minimumFreeBytes: String(minimum), reserveBytes: String(reserve), projectedWriteBytes: String(projectedBytes),
    projectedFreeAfterWriteBytes: String(free - projectedBytes), runningBlenderPidsBefore: running,
    outputs: outputs.map(path => ({ path, absentBefore: !existsSync(path) })), maximumConcurrentNativeProcesses: 1,
  };
  const receipt = writeHashed(resolve(evidence, 'package', `${String(sequence).padStart(2, '0')}-${id}-admission.json`), body, 'admissionHash');
  if (receipt.status !== 'ACCEPTED') throw new Error(`Package admission rejected: ${id}`);
  return receipt;
}
function nativeAdmission(sequence, id, runtime, output, report) {
  const free = freeBytes();
  const running = runningBlender();
  const failures = [];
  if (free - projectedRoundtripWrite < reserve) failures.push('INSUFFICIENT_FREE_SPACE');
  if (running.length) failures.push('BLENDER_ALREADY_RUNNING');
  if (!existsSync(runtime)) failures.push('RUNTIME_MISSING');
  for (const path of [output, report].filter(Boolean)) if (existsSync(path)) failures.push(`OUTPUT_EXISTS:${path}`);
  const body = {
    schemaVersion: 'bfs.f0.7.nativeStartAdmission.v0.1', sequence, id, observedAtUtc: now(),
    status: failures.length ? 'REJECTED' : 'ACCEPTED', failures,
    freeBytes: String(free), reserveBytes: String(reserve), projectedWriteBytes: String(projectedRoundtripWrite),
    projectedFreeAfterWriteBytes: String(free - projectedRoundtripWrite), runningBlenderPidsBefore: running,
    runtime, runtimeBinarySha256: shaFile(runtime), output: output ? { path: output, absentBefore: !existsSync(output) } : null,
    report: { path: report, absentBefore: !existsSync(report) }, maximumConcurrentNativeProcesses: 1,
  };
  const receipt = writeHashed(resolve(evidence, 'processes', `${String(sequence).padStart(2, '0')}-${id}-admission.json`), body, 'admissionHash');
  if (receipt.status !== 'ACCEPTED') throw new Error(`Native admission rejected: ${id}`);
  return receipt;
}
async function runTimed({ command, args, prefix, timeoutSeconds, env = process.env }) {
  const stdoutPath = `${prefix}.stdout.log`;
  const stderrPath = `${prefix}.stderr.log`;
  const timingPath = `${prefix}.timing.log`;
  const startedAtUtc = now();
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', ['-lp', '-o', timingPath, command, ...args], {
    cwd: repository, detached: true, env, stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  let timeout = false;
  const timer = setTimeout(() => { timeout = true; try { process.kill(-child.pid, 'SIGKILL'); } catch {} }, timeoutSeconds * 1000);
  const result = await new Promise((resolveResult, reject) => {
    child.on('error', reject);
    child.on('close', (exitCode, signal) => resolveResult({ exitCode, signal }));
  });
  clearTimeout(timer);
  writeFileSync(stdoutPath, Buffer.concat(stdout), { flag: 'wx' });
  writeFileSync(stderrPath, Buffer.concat(stderr), { flag: 'wx' });
  const timing = parseTiming(readFileSync(timingPath, 'utf8'));
  return {
    ...result, timeout, startedAtUtc,
    observedElapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    timing,
    logs: {
      stdout: { path: relative(evidence, stdoutPath), bytes: statSync(stdoutPath).size, sha256: shaFile(stdoutPath) },
      stderr: { path: relative(evidence, stderrPath), bytes: statSync(stderrPath).size, sha256: shaFile(stderrPath) },
      timing: { path: relative(evidence, timingPath), bytes: statSync(timingPath).size, sha256: shaFile(timingPath) },
    },
  };
}
function collect(root, predicate) {
  const rows = [];
  const walk = path => {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const candidate = resolve(path, name);
      const stat = lstatSync(candidate);
      if (stat.isDirectory()) walk(candidate);
      if (predicate(candidate, stat)) rows.push(candidate);
    }
  };
  walk(root);
  return rows;
}
function removeExactTree(root) {
  if (resolve(root) !== resolve(installApp) || dirname(resolve(root)) !== '/Users/mengyingli/Applications') throw new Error('Unsafe uninstall target');
  const walk = path => {
    for (const name of readdirSync(path)) {
      const candidate = resolve(path, name);
      const stat = lstatSync(candidate);
      if (stat.isDirectory() && !stat.isSymbolicLink()) { walk(candidate); rmdirSync(candidate); }
      else unlinkSync(candidate);
    }
  };
  walk(root);
  rmdirSync(root);
}
async function runRoundtrip({ sequence, id, runtime, stage, input, output, report, expectedCore, expectedMetadata }) {
  productStarts += 1;
  nativeAdmission(sequence, id, runtime, output, report);
  const scriptArgs = ['--repository-root', repository, '--stage', stage, '--report', relative(repository, report)];
  if (input) scriptArgs.push('--input', relative(repository, input));
  if (output) scriptArgs.push('--output', relative(repository, output));
  if (expectedCore) scriptArgs.push('--expected-core-hash', expectedCore);
  if (expectedMetadata) scriptArgs.push('--expected-metadata-hash', expectedMetadata);
  const blenderArgs = ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', stageScript, '--', ...scriptArgs];
  const prefix = resolve(evidence, 'processes', `${String(sequence).padStart(2, '0')}-${id}`);
  const result = await runTimed({
    command: runtime, args: blenderArgs, prefix, timeoutSeconds: maxSeconds,
    env: { ...process.env, LANG: 'C', LC_ALL: 'C', PYTHONDONTWRITEBYTECODE: '1' },
  });
  const finiteTiming = Object.values(result.timing).every(Number.isFinite);
  const status = result.exitCode === 0 && !result.timeout && finiteTiming && result.timing.realSeconds <= maxSeconds && result.timing.maximumResidentSetSizeBytes <= maxRss && existsSync(report) && (!output || existsSync(output)) ? 'PASS' : 'FAIL';
  const body = {
    schemaVersion: 'bfs.f0.7.processReceipt.v0.1', sequence, id, stage, status,
    runtime, runtimeBinarySha256: shaFile(runtime), command: runtime, args: blenderArgs,
    exitCode: result.exitCode, signal: result.signal, timeout: result.timeout,
    startedAtUtc: result.startedAtUtc, timing: { ...result.timing, observedElapsedSeconds: result.observedElapsedSeconds },
    report: existsSync(report) ? { path: relative(evidence, report), bytes: statSync(report).size, sha256: shaFile(report) } : null,
    output: output && existsSync(output) ? { path: relative(evidence, output), bytes: statSync(output).size, sha256: shaFile(output) } : null,
    logs: result.logs, renderCalls: 0, mouseInteractions: 0,
  };
  const receipt = writeHashed(`${prefix}.json`, body, 'processHash');
  if (status !== 'PASS') throw new Error(`Round-trip process failed: ${id}`);
  if (output && statSync(output).size > maxBlendBytes) throw new Error(`Blend output exceeds limit: ${id}`);
  if (!validSelf(report, 'reportHash', true)) throw new Error(`Stage report self hash invalid: ${id}`);
  const stageReport = JSON.parse(readFileSync(report));
  if (stageReport.status !== 'PASS' || stageReport.renderCalls !== 0 || stageReport.mouseInteractions !== 0) throw new Error(`Stage report invalid: ${id}`);
  return { receipt, report: stageReport };
}

const frozenBefore = ensureFrozenInputs();
if (existsSync(packageRoot) || existsSync(installApp)) throw new Error('Fresh package root or install destination is not absent');

packageAdmission(1, 'stage-normalized-payload', { projectedBytes: projectedPackageWrite, outputs: [packageRoot], initial: true });
mkdirSync(packageRoot, { recursive: false });
mkdirSync(stagingRoot, { recursive: false });
execFileSync('/bin/cp', ['-cR', sourceApp, stagingApp], { timeout: maxSeconds * 1000 });
const pycFiles = collect(stagingApp, (path, stat) => stat.isFile() && path.endsWith('.pyc'));
const pycacheDirectories = collect(stagingApp, (path, stat) => stat.isDirectory() && basename(path) === '__pycache__').sort((a, b) => b.length - a.length);
if (pycFiles.length !== expected.pycFiles || pycacheDirectories.length !== expected.pycacheDirectories) throw new Error('Frozen runtime-cache count mismatch in staging clone');
for (const path of pycFiles) unlinkSync(path);
for (const path of pycacheDirectories) {
  if (readdirSync(path).length !== 0) throw new Error(`Normalized pycache directory is not empty: ${path}`);
  rmdirSync(path);
}
const normalized = treeIdentity(stagingApp);
const sourceAfterNormalize = treeIdentity(sourceApp);
if (normalized.files !== expected.normalizedFiles || sourceAfterNormalize.digest !== expected.sourceTree || shaFile(resolve(stagingApp, 'Contents/MacOS/Blender')) !== expected.productBinary) throw new Error('Normalized payload identity failed');
if (collect(stagingApp, path => path.endsWith('.pyc') || basename(path) === '__pycache__').length !== 0) throw new Error('Normalized payload still contains runtime cache');
writeHashed(resolve(evidence, 'package/01-normalization.json'), {
  schemaVersion: 'bfs.f0.7.normalizationReceipt.v0.1', status: 'PASS', sourceBefore: frozenBefore.source,
  sourceAfter: sourceAfterNormalize, staging: normalized, removedPycFiles: pycFiles.length,
  removedPycacheDirectories: pycacheDirectories.length, sourceProductMutated: false,
}, 'normalizationHash');

packageAdmission(2, 'create-dmg', { projectedBytes: projectedPackageWrite, outputs: [dmg] });
const createPrefix = resolve(evidence, 'package/02-create-dmg');
const createArgs = ['create', '-volname', 'Film Studio Engine F0 5.2.1', '-srcfolder', stagingRoot, '-format', 'UDZO', '-imagekey', 'zlib-level=9', dmg];
const createResult = await runTimed({ command: '/usr/bin/hdiutil', args: createArgs, prefix: createPrefix, timeoutSeconds: maxDmgCompressionSeconds });
const createStatus = createResult.exitCode === 0 && !createResult.timeout && existsSync(dmg) && createResult.timing.realSeconds <= maxDmgCompressionSeconds ? 'PASS' : 'FAIL';
writeHashed(`${createPrefix}.json`, {
  schemaVersion: 'bfs.f0.7.packageProcessReceipt.v0.1', id: 'CREATE_DMG', status: createStatus,
  command: '/usr/bin/hdiutil', args: createArgs, exitCode: createResult.exitCode, signal: createResult.signal,
  timeout: createResult.timeout, startedAtUtc: createResult.startedAtUtc,
  timing: { ...createResult.timing, observedElapsedSeconds: createResult.observedElapsedSeconds }, logs: createResult.logs,
  output: existsSync(dmg) ? { path: dmg, bytes: statSync(dmg).size, sha256: shaFile(dmg) } : null,
}, 'processHash');
if (createStatus !== 'PASS') throw new Error('DMG creation failed or exceeded the frozen time limit');

packageAdmission(3, 'mount-audit', { projectedBytes: 8n * 1024n ** 2n, outputs: [mountpoint] });
mkdirSync(mountpoint, { recursive: false });
let attachStdout = '';
let detachStdout = '';
let mounted = false;
let mountedIdentity;
try {
  attachStdout = execFileSync('/usr/bin/hdiutil', ['attach', '-readonly', '-nobrowse', '-mountpoint', mountpoint, dmg], { encoding: 'utf8', timeout: maxSeconds * 1000 });
  mounted = true;
  const mountedApp = resolve(mountpoint, basename(stagingApp));
  mountedIdentity = treeIdentity(mountedApp);
  if (mountedIdentity.digest !== normalized.digest || mountedIdentity.files !== normalized.files) throw new Error('Read-only mounted DMG payload differs from staging');
} finally {
  if (mounted) detachStdout = execFileSync('/usr/bin/hdiutil', ['detach', mountpoint], { encoding: 'utf8', timeout: maxSeconds * 1000 });
  if (existsSync(mountpoint)) rmdirSync(mountpoint);
}
const verifyOutput = execFileSync('/usr/bin/hdiutil', ['verify', dmg], { encoding: 'utf8', timeout: maxSeconds * 1000 });
writeFileSync(resolve(evidence, 'package/03-attach.stdout.log'), attachStdout, { flag: 'wx' });
writeFileSync(resolve(evidence, 'package/03-detach.stdout.log'), detachStdout, { flag: 'wx' });
writeFileSync(resolve(evidence, 'package/03-verify.stdout.log'), verifyOutput, { flag: 'wx' });

packageAdmission(4, 'install', { projectedBytes: projectedPackageWrite, outputs: [installApp] });
execFileSync('/bin/cp', ['-cR', stagingApp, installApp], { timeout: maxSeconds * 1000 });
const installed = treeIdentity(installApp);
if (installed.digest !== normalized.digest || shaFile(resolve(installApp, 'Contents/MacOS/Blender')) !== expected.productBinary) throw new Error('Installed payload identity mismatch');
const codesign = await runTimed({ command: '/usr/bin/codesign', args: ['-dv', '--verbose=4', installApp], prefix: resolve(evidence, 'package/04-codesign'), timeoutSeconds: maxSeconds });
const spctl = await runTimed({ command: '/usr/sbin/spctl', args: ['--assess', '--type', 'execute', '--verbose=4', installApp], prefix: resolve(evidence, 'package/04-spctl'), timeoutSeconds: maxSeconds });
if (codesign.exitCode !== 0 || spctl.exitCode === 0 || spctl.timeout) throw new Error('Expected ad-hoc signature and Gatekeeper rejection were not observed');
const packageManifest = writeHashed(resolve(evidence, 'package-manifest.json'), {
  schemaVersion: 'bfs.f0.7.packageManifest.v0.1', status: 'PASS_UNSIGNED_RESEARCH_PACKAGE',
  source: frozenBefore.source, normalizedPayload: normalized,
  normalization: { removedPycFiles: pycFiles.length, removedPycacheDirectories: pycacheDirectories.length, sourceProductMutated: false },
  dmg: { path: dmg, bytes: statSync(dmg).size, sha256: shaFile(dmg), volumeName: 'Film Studio Engine F0 5.2.1', format: 'UDZO', hdiutilVerified: true, mountedReadOnlyPayload: mountedIdentity },
  installedPayloadBeforeRoundtrip: installed,
  signature: { codesignExitCode: codesign.exitCode, codesignStdoutSha256: codesign.logs.stdout.sha256, codesignStderrSha256: codesign.logs.stderr.sha256, classification: 'ADHOC_LINKER_SIGNED' },
  gatekeeper: { spctlExitCode: spctl.exitCode, spctlStdoutSha256: spctl.logs.stdout.sha256, spctlStderrSha256: spctl.logs.stderr.sha256, classification: 'EXPECTED_REJECTION_RETAINED' },
  publicDistributionClaimed: false, developerIdUsed: false, notarizationSubmitted: false, gatekeeperBypassed: false,
}, 'manifestHash');

const otf = resolve(evidence, 'roundtrip/official-to-f0');
const fto = resolve(evidence, 'roundtrip/f0-to-official');
const installedRuntime = resolve(installApp, 'Contents/MacOS/Blender');
const stages = [];
stages.push(await runRoundtrip({ sequence: 1, id: 'official-create', runtime: officialRuntime, stage: 'official-create', output: resolve(otf, '01-official.blend'), report: resolve(otf, '01-official-report.json') }));
const expectedCore = stages[0].report.coreSemanticSha256;
stages.push(await runRoundtrip({ sequence: 2, id: 'f0-open-official', runtime: installedRuntime, stage: 'f0-open-official', input: resolve(otf, '01-official.blend'), output: resolve(otf, '02-f0.blend'), report: resolve(otf, '02-f0-report.json'), expectedCore }));
stages.push(await runRoundtrip({ sequence: 3, id: 'official-reopen-f0', runtime: officialRuntime, stage: 'official-reopen-f0', input: resolve(otf, '02-f0.blend'), output: resolve(otf, '03-official-resave.blend'), report: resolve(otf, '03-official-report.json'), expectedCore }));
stages.push(await runRoundtrip({ sequence: 4, id: 'f0-create', runtime: installedRuntime, stage: 'f0-create', output: resolve(fto, '04-f0.blend'), report: resolve(fto, '04-f0-report.json'), expectedCore }));
const expectedMetadata = stages[3].report.optionalMetadataBeforeSave.metadataSha256;
if (!expectedMetadata) throw new Error('F0 did not create typed Film Studio metadata');
stages.push(await runRoundtrip({ sequence: 5, id: 'official-open-f0', runtime: officialRuntime, stage: 'official-open-f0', input: resolve(fto, '04-f0.blend'), output: resolve(fto, '05-official.blend'), report: resolve(fto, '05-official-report.json'), expectedCore, expectedMetadata }));
stages.push(await runRoundtrip({ sequence: 6, id: 'f0-reopen-official', runtime: installedRuntime, stage: 'f0-reopen-official', input: resolve(fto, '05-official.blend'), report: resolve(fto, '06-f0-reopen-report.json'), expectedCore, expectedMetadata }));
if (productStarts !== 6) throw new Error('Round-trip product start count mismatch');
const coreHashes = stages.map(row => row.report.coreSemanticSha256);
if (!coreHashes.every(value => value === expectedCore)) throw new Error('Core semantic hash changed across round trip');
if (!stages[1].report.missingOptionalMetadataGraceful) throw new Error('Missing optional metadata was not explicitly graceful');
const metadataDisposition = stages[4].report.optionalMetadataBeforeSave.metadataSha256 === expectedMetadata && stages[5].report.optionalMetadataBeforeSave.metadataSha256 === expectedMetadata ? 'PRESERVED_EXACT' : 'DROPPED_GRACEFULLY';
const roundtrip = writeHashed(resolve(evidence, 'roundtrip.json'), {
  schemaVersion: 'bfs.f0.7.roundtripReceipt.v0.1', status: 'PASS', formalProductStarts: productStarts,
  maximumFormalProductStarts: 6, coreSemanticSha256: expectedCore, coreSemanticExactAtAllSixBoundaries: true,
  officialToF0ToOfficial: { status: 'PASS', missingOptionalMetadataGraceful: true, stages: stages.slice(0, 3).map(row => ({ stage: row.report.stage, runtime: row.report.runtime, reportHash: row.report.reportHash, output: row.report.output })) },
  f0ToOfficial: { status: 'PASS', createdMetadataSha256: expectedMetadata, metadataDisposition, stages: stages.slice(3).map(row => ({ stage: row.report.stage, runtime: row.report.runtime, reportHash: row.report.reportHash, output: row.report.output })) },
  zeroRenderCalls: stages.every(row => row.report.renderCalls === 0), zeroMouseInteractions: stages.every(row => row.report.mouseInteractions === 0),
  networkCalls: 0, modelCalls: 0,
}, 'roundtripHash');

const configurationBeforeUninstall = {
  officialApplicationSupport: treeIdentity(officialConfig), officialCache: treeIdentity(officialCache),
  f0ApplicationSupport: treeIdentity(f0Config), f0Cache: treeIdentity(f0Cache), officialInstalledApp: treeIdentity(officialApp),
};
if (configurationBeforeUninstall.officialApplicationSupport.digest !== expected.officialConfig || configurationBeforeUninstall.officialCache.digest !== expected.officialCache || configurationBeforeUninstall.officialInstalledApp.digest !== expected.officialAppTree) throw new Error('Official Blender or official configuration changed before uninstall');
if (configurationBeforeUninstall.f0ApplicationSupport.digest !== expected.f0Config || configurationBeforeUninstall.f0Cache.digest !== expected.f0Cache) throw new Error('Independent F0 configuration roots changed unexpectedly');

packageAdmission(5, 'uninstall-exact-generated-target', { projectedBytes: 0n, outputs: [] });
const installedBeforeUninstall = treeIdentity(installApp);
if (installedBeforeUninstall.digest !== normalized.digest) throw new Error('Installed target drifted before safe uninstall');
removeExactTree(installApp);
if (existsSync(installApp)) throw new Error('Exact generated install target remains after uninstall');
const configurationAfterUninstall = {
  officialApplicationSupport: treeIdentity(officialConfig), officialCache: treeIdentity(officialCache),
  f0ApplicationSupport: treeIdentity(f0Config), f0Cache: treeIdentity(f0Cache), officialInstalledApp: treeIdentity(officialApp),
};
for (const [row, digest] of [
  [configurationAfterUninstall.officialApplicationSupport, expected.officialConfig], [configurationAfterUninstall.officialCache, expected.officialCache],
  [configurationAfterUninstall.f0ApplicationSupport, expected.f0Config], [configurationAfterUninstall.f0Cache, expected.f0Cache],
  [configurationAfterUninstall.officialInstalledApp, expected.officialAppTree],
]) if (row.digest !== digest) throw new Error(`Post-uninstall identity mismatch: ${row.root}`);
const installUninstall = writeHashed(resolve(evidence, 'install-uninstall.json'), {
  schemaVersion: 'bfs.f0.7.installUninstallReceipt.v0.1', status: 'PASS',
  installDestination: installApp, absentBeforeInstall: true, installedPayload: installed,
  installedPayloadBeforeUninstall, exactGeneratedDestinationRemoved: true, absentAfterUninstall: !existsSync(installApp),
  officialBlenderUnchanged: configurationAfterUninstall.officialInstalledApp.digest === expected.officialAppTree,
}, 'installUninstallHash');
const configuration = writeHashed(resolve(evidence, 'configuration-isolation.json'), {
  schemaVersion: 'bfs.f0.7.configurationIsolationReceipt.v0.1', status: 'PASS',
  beforeUninstall: configurationBeforeUninstall, afterUninstall: configurationAfterUninstall,
  officialRootsExact: true, independentF0RootsExact: true,
  observedF0ResourcePaths: stages.filter((_, index) => [1, 3, 5].includes(index)).map(row => row.report.resourcePaths),
}, 'configurationHash');

const evidenceBeforeAudit = treeIdentity(evidence);
if (evidenceBeforeAudit.logicalBytes > maxEvidenceBytes) throw new Error('Formal evidence exceeds frozen size limit before audit');
execFileSync(process.execPath, [auditScript, repository, evidenceRelative], { cwd: repository, timeout: maxSeconds * 1000, stdio: 'inherit' });
const auditPath = resolve(evidence, 'audit.json');
if (!validSelf(auditPath, 'auditHash') || JSON.parse(readFileSync(auditPath)).status !== 'PASS') throw new Error('Independent F0.7 audit failed');
const evidenceAfterAudit = treeIdentity(evidence);
if (evidenceAfterAudit.logicalBytes > maxEvidenceBytes) throw new Error('Formal evidence exceeds frozen size limit after audit');
writeHashed(resolve(evidence, 'verdict.json'), {
  schemaVersion: 'bfs.f0.7.verdict.v0.1', gate: 'F0.7', experimentId: basename(evidence), status: 'PASS',
  packageManifestHash: packageManifest.manifestHash, roundtripHash: roundtrip.roundtripHash,
  installUninstallHash: installUninstall.installUninstallHash, configurationHash: configuration.configurationHash,
  auditFileSha256: shaFile(auditPath), auditHash: JSON.parse(readFileSync(auditPath)).auditHash,
  productStarts, coreSemanticSha256: expectedCore, metadataDisposition,
  sourceProductUnchanged: treeIdentity(sourceApp).digest === expected.sourceTree,
  installedOfficialBlenderUnchanged: treeIdentity(officialApp).digest === expected.officialAppTree,
  installedResearchTargetAbsent: !existsSync(installApp), retainedUnsignedDmg: { path: dmg, bytes: statSync(dmg).size, sha256: shaFile(dmg) },
  claimCeiling: 'Unsigned local research package and two frozen same-host .blend round trips only; no public distribution, signing, notarization, production-support, cross-version-generalization, or legal-sufficiency claim.',
}, 'verdictHash');
console.log(`F0.7 PASS core=${expectedCore} metadata=${metadataDisposition} dmg=${shaFile(dmg)}`);
