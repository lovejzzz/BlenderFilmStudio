#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream, statfsSync } from 'node:fs';
import { access, mkdir, open, readFile, rename, stat } from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { relative, resolve } from 'node:path';
import process from 'node:process';

const WORKSPACE_COMMIT = '4f1446f780c2b7e23bc66f584b36f6254ecd985c';
const IDENTITY_COMMIT = '0a25790a1cd6feff4bae1b03d81e4c43ec55a0b5';
const DEPENDENCY_COMMIT = '5a140a8ccc8c070221b1b06e2c6f89f136c5758d';
const BRANCH = 'codex/f0.3-minimum-film-workspace';
const REQUIRED_FREE_BYTES = 160n * (1024n ** 3n);
const MAX_BUILD_MS = 12 * 60 * 60 * 1000;
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const PRODUCT_NAME = 'Film Studio Engine F0';

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

function sourceFailures(identity) {
  const failures = [];
  if (identity.head !== WORKSPACE_COMMIT) failures.push('SOURCE_HEAD_MISMATCH');
  if (identity.parent !== IDENTITY_COMMIT) failures.push('SOURCE_PARENT_MISMATCH');
  if (identity.branch !== BRANCH) failures.push('SOURCE_BRANCH_MISMATCH');
  if (!identity.clean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (!identity.dependency.includes(DEPENDENCY_COMMIT)) failures.push('DEPENDENCY_COMMIT_MISMATCH');
  return failures;
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
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', ['-lp', '-o', timingPath, command, ...args], {
    cwd,
    detached: true,
    env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let spawnError = null;
  let timedOut = false;
  let forceTimer = null;
  child.on('error', error => { spawnError = error; });
  child.stdout.on('data', chunk => {
    stdoutStream.write(chunk);
    process.stdout.write(chunk);
  });
  child.stderr.on('data', chunk => {
    stderrStream.write(chunk);
    process.stderr.write(chunk);
  });
  const timeout = setTimeout(() => {
    timedOut = true;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
    forceTimer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
    }, 5000);
  }, MAX_BUILD_MS);
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

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const repositoryRoot = resolve(args.repository);
  const evidenceRoot = resolve(args.evidence);
  const workspace = resolve(args.workspace);
  const source = resolve(args.source);
  const stageRoot = resolve(evidenceRoot, 'build');
  const buildRoot = resolve(workspace, 'build-f0.3-workspace');
  const builtApp = resolve(buildRoot, 'bin', 'Blender.app');
  const finalApp = resolve(buildRoot, 'bin', `${PRODUCT_NAME}.app`);

  await mkdir(stageRoot, { recursive: false });
  const identity = sourceIdentity(source);
  const observedFreeBytes = freeBytes(workspace);
  const processes = restrictedProcesses();
  const failures = sourceFailures(identity);
  if (observedFreeBytes < REQUIRED_FREE_BYTES) failures.push('FREE_DISK_BELOW_160_GIB');
  if (await exists(buildRoot)) failures.push('BUILD_ROOT_ALREADY_EXISTS');
  if (processes.length > 0) failures.push('RESTRICTED_NATIVE_PROCESS_ALREADY_RUNNING');

  const admission = await writeJsonExclusive(resolve(stageRoot, 'admission.json'), {
    schemaVersion: 'bfs.f0WorkspaceBuildAdmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    observedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: identity,
    buildRoot,
    buildRootExisted: await exists(buildRoot),
    restrictedProcesses: processes,
    failures,
    authorizedNativeJobStarts: failures.length === 0 ? 1 : 0,
  });
  if (failures.length > 0) {
    await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
      schemaVersion: 'bfs.f0WorkspaceBuildReceipt.v0.1',
      protocol: 'F0-SOURCE-FEASIBILITY',
      gate: 'F0.3',
      status: 'BLOCKED',
      admissionReceiptHash: admission.receiptHash,
      nativeJobStarts: 0,
      failures,
    });
    process.stdout.write(`F03_BUILD_BLOCKED failures=${failures.join(',')} native=0\n`);
    process.exitCode = 2;
    return;
  }

  const patch = git(source, ['diff', '--binary', `${IDENTITY_COMMIT}..${WORKSPACE_COMMIT}`]);
  await writeTextExclusive(resolve(evidenceRoot, 'workspace.patch'), `${patch}\n`);
  const startedAt = new Date().toISOString();
  const freeBytesBefore = freeBytes(workspace);
  const result = await runTimed({
    command: '/usr/bin/make',
    args: [`BUILD_DIR=${buildRoot}`, 'NPROCS=12'],
    cwd: source,
    stageRoot,
  });
  const endedAt = new Date().toISOString();
  const builtAppExists = await exists(builtApp);
  let packaged = false;
  if (result.exitCode === 0 && result.signal === null && !result.timedOut && builtAppExists && !(await exists(finalApp))) {
    await rename(builtApp, finalApp);
    packaged = true;
  }
  const finalIdentity = sourceIdentity(source);
  const timingText = await readFile(result.timingPath, 'utf8').catch(() => '');
  const timing = parseTiming(timingText);
  const finalAppExists = await exists(finalApp);
  const binary = resolve(finalApp, 'Contents', 'MacOS', 'Blender');
  const checks = {
    processExitZero: result.exitCode === 0 && result.signal === null && !result.timedOut,
    builtAppProduced: builtAppExists,
    finalBundleRenamed: packaged && finalAppExists,
    finalBinaryExists: await exists(binary),
    sourceHeadUnchanged: finalIdentity.head === WORKSPACE_COMMIT,
    sourceStillClean: finalIdentity.clean,
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  const fileRecord = async path => {
    const value = await stat(path);
    return { path: relative(repositoryRoot, path), bytes: value.size, sha256: await sha256File(path) };
  };
  const receipt = await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0WorkspaceBuildReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    status,
    startedAt,
    endedAt,
    admissionReceiptHash: admission.receiptHash,
    sourceBefore: identity,
    sourceAfter: finalIdentity,
    command: result.command,
    pid: result.pid,
    exitCode: result.exitCode,
    signal: result.signal,
    timedOut: result.timedOut,
    spawnError: result.spawnError,
    elapsedSeconds: result.elapsedSeconds,
    timing,
    disk: {
      freeBytesBefore: freeBytesBefore.toString(),
      freeBytesAfter: freeBytes(workspace).toString(),
    },
    artifacts: {
      app: finalApp,
      binary: await exists(binary) ? {
        path: binary,
        bytes: (await stat(binary)).size,
        sha256: await sha256File(binary),
      } : null,
      patch: await fileRecord(resolve(evidenceRoot, 'workspace.patch')),
      stdout: await fileRecord(result.stdoutPath),
      stderr: await fileRecord(result.stderrPath),
      timing: await fileRecord(result.timingPath),
    },
    checks,
    nativeJobStarts: 1,
    failures: Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name),
  });
  process.stdout.write(`F03_BUILD_${status} receipt=${receipt.receiptHash} wall=${result.elapsedSeconds.toFixed(3)}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

await main();
