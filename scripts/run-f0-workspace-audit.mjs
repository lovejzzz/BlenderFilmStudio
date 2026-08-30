#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream, statfsSync } from 'node:fs';
import { access, lstat, mkdir, open, readFile, readdir, readlink, stat } from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { relative, resolve } from 'node:path';
import process from 'node:process';

const SOURCE_COMMIT = '4f1446f780c2b7e23bc66f584b36f6254ecd985c';
const IDENTITY_COMMIT = '0a25790a1cd6feff4bae1b03d81e4c43ec55a0b5';
const DEPENDENCY_COMMIT = '5a140a8ccc8c070221b1b06e2c6f89f136c5758d';
const BRANCH = 'codex/f0.3-minimum-film-workspace';
const BINARY_SHA256 = 'eedf94e75571b78d83e916f2530630b83ab59927173d784e615392c528107695';
const BUILD_RECEIPT_HASH = '7a0fd8b6d2c4dee792e084acca359f9f6eb2f3d758ca6619ea74d63effab038b';
const OFFICIAL_CONFIG_DIGEST = 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf';
const REQUIRED_FREE_BYTES = 160n * (1024n ** 3n);
const MAX_RUNTIME_MS = 10 * 60 * 1000;
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const OFFICIAL_CONFIG_ROOT = '/Users/mengyingli/Library/Application Support/Blender';
const STAGES = new Set(['create-save', 'reopen', 'missing-prepare', 'missing-reopen']);

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) {
      throw new Error(`Expected --name value argument, observed ${key ?? '<missing>'}`);
    }
    parsed[key.slice(2)] = value;
  }
  return parsed;
}

function exec(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C' },
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

function git(source, args) {
  return exec('/usr/bin/git', ['-C', source, ...args]);
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

async function sha256File(path) {
  const hash = createHash('sha256');
  const input = createReadStream(path);
  input.on('data', chunk => hash.update(chunk));
  await finished(input);
  return hash.digest('hex');
}

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function writeTextExclusive(path, body) {
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(body);
    await handle.sync();
  } finally {
    await handle.close();
  }
}

async function writeJsonExclusive(path, value) {
  const bodyWithoutHash = `${JSON.stringify(value, null, 2)}\n`;
  const record = { ...value, receiptHash: sha256Bytes(Buffer.from(bodyWithoutHash)) };
  await writeTextExclusive(path, `${JSON.stringify(record, null, 2)}\n`);
  return record;
}

function freeBytes(path) {
  const value = statfsSync(path, { bigint: true });
  return value.bavail * value.bsize;
}

function sourceIdentity(source) {
  const status = git(source, ['status', '--porcelain=v1']);
  return {
    path: source,
    head: git(source, ['rev-parse', 'HEAD']),
    parent: git(source, ['rev-parse', 'HEAD^']),
    branch: git(source, ['branch', '--show-current']),
    dependency: git(source, ['submodule', 'status', '--', 'lib/macos_arm64']),
    clean: status === '',
    status,
  };
}

function restrictedProcesses() {
  const ownPid = process.pid;
  return exec('/bin/ps', ['-axo', 'pid=,ppid=,comm=,args='])
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .filter(line => {
      const pid = Number(line.split(/\s+/, 1)[0]);
      if (pid === ownPid) return false;
      return /(?:Blender\.app\/Contents\/MacOS\/Blender|Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line);
    });
}

async function walkTree(root, current = '') {
  const absolute = resolve(root, current);
  const names = await readdir(absolute);
  names.sort((left, right) => left.localeCompare(right, 'en'));
  const records = [];
  for (const name of names) {
    const relativePath = current ? `${current}/${name}` : name;
    const path = resolve(root, relativePath);
    const value = await lstat(path);
    const mode = value.mode & 0o7777;
    if (value.isDirectory()) {
      records.push({ path: relativePath, type: 'directory', mode });
      records.push(...await walkTree(root, relativePath));
    } else if (value.isSymbolicLink()) {
      records.push({ path: relativePath, type: 'symlink', mode, target: await readlink(path) });
    } else if (value.isFile()) {
      records.push({ path: relativePath, type: 'file', mode, bytes: value.size, sha256: await sha256File(path) });
    } else {
      records.push({ path: relativePath, type: 'other', mode, bytes: value.size });
    }
  }
  return records;
}

async function treeIdentity(root) {
  if (!(await exists(root))) {
    return { root, state: 'ABSENT', entries: 0, digest: sha256Bytes(Buffer.from('ABSENT')) };
  }
  const records = await walkTree(root);
  const manifest = `${records.map(record => JSON.stringify(record)).join('\n')}\n`;
  return {
    root,
    state: 'PRESENT',
    entries: records.length,
    digest: sha256Bytes(Buffer.from(manifest)),
  };
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

async function runTimed({ command, args, cwd, stageRoot }) {
  const stdoutPath = resolve(stageRoot, 'stdout.log');
  const stderrPath = resolve(stageRoot, 'stderr.log');
  const timingPath = resolve(stageRoot, 'timing.log');
  const stdoutStream = createWriteStream(stdoutPath, { flags: 'wx', mode: 0o600 });
  const stderrStream = createWriteStream(stderrPath, { flags: 'wx', mode: 0o600 });
  const child = spawn('/usr/bin/time', ['-lp', '-o', timingPath, command, ...args], {
    cwd,
    detached: true,
    env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const started = process.hrtime.bigint();
  let spawnError = null;
  let timedOut = false;
  let forceTimer = null;
  child.on('error', error => { spawnError = error; });
  child.stdout.on('data', chunk => { stdoutStream.write(chunk); process.stdout.write(chunk); });
  child.stderr.on('data', chunk => { stderrStream.write(chunk); process.stderr.write(chunk); });
  const timeout = setTimeout(() => {
    timedOut = true;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
    forceTimer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
    }, 5000);
  }, MAX_RUNTIME_MS);
  const terminal = await new Promise(resolveClose => {
    child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal }));
  });
  clearTimeout(timeout);
  if (forceTimer) clearTimeout(forceTimer);
  stdoutStream.end();
  stderrStream.end();
  await Promise.all([finished(stdoutStream), finished(stderrStream)]);
  return {
    pid: child.pid,
    exitCode: spawnError ? 1 : terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    spawnError: spawnError?.message ?? null,
    elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    command: { executable: command, args, cwd },
    stdoutPath,
    stderrPath,
    timingPath,
  };
}

async function fileRecord(repositoryRoot, path) {
  const value = await stat(path);
  return { path: relative(repositoryRoot, path), bytes: value.size, sha256: await sha256File(path) };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const stage = args.stage;
  if (!STAGES.has(stage)) throw new Error(`Unsupported stage: ${stage}`);
  const repositoryRoot = resolve(args.repository);
  const evidenceRoot = resolve(args.evidence);
  const workspace = resolve(args.workspace);
  const source = resolve(args.source);
  const script = resolve(repositoryRoot, 'scripts', 'f0-workspace-audit.py');
  const app = resolve(workspace, 'build-f0.3-workspace', 'bin', 'Film Studio Engine F0.app');
  const binary = resolve(app, 'Contents', 'MacOS', 'Blender');
  const stageRoot = resolve(evidenceRoot, `runtime-${stage}`);
  const artifactRoot = resolve(evidenceRoot, 'artifacts');
  const persistenceBlend = resolve(artifactRoot, 'f0.3-workspace-persistence.blend');
  const missingBlend = resolve(artifactRoot, 'f0.3-workspace-missing-optional.blend');
  const blend = stage.startsWith('missing-') ? missingBlend : persistenceBlend;
  const inputBlend = stage === 'reopen' || stage === 'missing-prepare' ? persistenceBlend
    : stage === 'missing-reopen' ? missingBlend : null;

  await mkdir(stageRoot, { recursive: false });
  await mkdir(artifactRoot, { recursive: true });
  const identity = sourceIdentity(source);
  const officialBefore = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const processes = restrictedProcesses();
  const observedFreeBytes = freeBytes(workspace);
  const failures = [];
  if (identity.head !== SOURCE_COMMIT) failures.push('SOURCE_HEAD_MISMATCH');
  if (identity.parent !== IDENTITY_COMMIT) failures.push('SOURCE_PARENT_MISMATCH');
  if (identity.branch !== BRANCH) failures.push('SOURCE_BRANCH_MISMATCH');
  if (!identity.clean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (!identity.dependency.includes(DEPENDENCY_COMMIT)) failures.push('DEPENDENCY_COMMIT_MISMATCH');
  if (observedFreeBytes < REQUIRED_FREE_BYTES) failures.push('FREE_DISK_BELOW_160_GIB');
  if (processes.length > 0) failures.push('RESTRICTED_NATIVE_PROCESS_ALREADY_RUNNING');
  if (!(await exists(binary))) failures.push('BINARY_MISSING');
  if (await exists(binary) && await sha256File(binary) !== BINARY_SHA256) failures.push('BINARY_HASH_MISMATCH');
  if (officialBefore.digest !== OFFICIAL_CONFIG_DIGEST) failures.push('OFFICIAL_CONFIG_DRIFT');
  if (Object.keys(process.env).some(name => name.startsWith('BLENDER_USER_'))) failures.push('BLENDER_USER_OVERRIDE_PRESENT');
  if (inputBlend && !(await exists(inputBlend))) failures.push('INPUT_BLEND_MISSING');
  if (stage === 'create-save' && await exists(persistenceBlend)) failures.push('PERSISTENCE_BLEND_ALREADY_EXISTS');
  if (stage === 'missing-prepare' && await exists(missingBlend)) failures.push('MISSING_BLEND_ALREADY_EXISTS');

  const admission = await writeJsonExclusive(resolve(stageRoot, 'admission.json'), {
    schemaVersion: 'bfs.f0WorkspaceRuntimeAdmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    stage,
    observedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: identity,
    binary: { path: binary, expectedSha256: BINARY_SHA256 },
    buildReceiptHash: BUILD_RECEIPT_HASH,
    officialConfiguration: officialBefore,
    restrictedProcesses: processes,
    inputBlend,
    outputBlend: blend,
    failures,
    authorizedNativeJobStarts: failures.length === 0 ? 1 : 0,
  });
  if (failures.length > 0) {
    await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
      schemaVersion: 'bfs.f0WorkspaceRuntimeReceipt.v0.1',
      protocol: 'F0-SOURCE-FEASIBILITY',
      gate: 'F0.3',
      stage,
      status: 'BLOCKED',
      admissionReceiptHash: admission.receiptHash,
      nativeJobStarts: 0,
      failures,
    });
    process.stdout.write(`F03_WORKSPACE_${stage.toUpperCase().replaceAll('-', '_')}_BLOCKED\n`);
    process.exitCode = 2;
    return;
  }

  const resultPath = resolve(stageRoot, 'blender-result.json');
  const blenderArgs = ['--background'];
  if (inputBlend) blenderArgs.push(inputBlend);
  else blenderArgs.push('--factory-startup');
  blenderArgs.push(
    '--python-exit-code', '86',
    '--python', script,
    '--', '--stage', stage, '--output', resultPath, '--blend', blend,
  );
  const startedAt = new Date().toISOString();
  const result = await runTimed({ command: binary, args: blenderArgs, cwd: repositoryRoot, stageRoot });
  const endedAt = new Date().toISOString();
  const officialAfter = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const identityAfter = sourceIdentity(source);
  const blenderResult = await readFile(resultPath, 'utf8').then(JSON.parse).catch(() => null);
  const timingText = await readFile(result.timingPath, 'utf8').catch(() => '');
  const checks = {
    processExitZero: result.exitCode === 0 && result.signal === null && !result.timedOut,
    blenderResultPass: blenderResult?.status === 'PASS' && blenderResult?.stage === stage,
    officialConfigUnchanged: officialAfter.digest === officialBefore.digest && officialAfter.digest === OFFICIAL_CONFIG_DIGEST,
    sourceHeadUnchanged: identityAfter.head === SOURCE_COMMIT,
    sourceStillClean: identityAfter.clean,
    expectedBlendExists: await exists(blend),
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  const receipt = await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0WorkspaceRuntimeReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    stage,
    status,
    startedAt,
    endedAt,
    admissionReceiptHash: admission.receiptHash,
    command: result.command,
    pid: result.pid,
    exitCode: result.exitCode,
    signal: result.signal,
    timedOut: result.timedOut,
    spawnError: result.spawnError,
    elapsedSeconds: result.elapsedSeconds,
    timing: parseTiming(timingText),
    officialConfigurationBefore: officialBefore,
    officialConfigurationAfter: officialAfter,
    sourceAfter: identityAfter,
    blenderResult,
    artifacts: {
      blenderResult: await exists(resultPath) ? await fileRecord(repositoryRoot, resultPath) : null,
      blend: await exists(blend) ? await fileRecord(repositoryRoot, blend) : null,
      stdout: await fileRecord(repositoryRoot, result.stdoutPath),
      stderr: await fileRecord(repositoryRoot, result.stderrPath),
      timing: await fileRecord(repositoryRoot, result.timingPath),
    },
    checks,
    nativeJobStarts: 1,
    failures: Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name),
  });
  process.stdout.write(`F03_WORKSPACE_${stage.toUpperCase().replaceAll('-', '_')}_${status} receipt=${receipt.receiptHash}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

await main();
