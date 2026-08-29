#!/usr/bin/env node

import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import {
  access,
  mkdir,
  open,
  readFile,
  realpath,
  stat,
} from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import os from 'node:os';
import { dirname, isAbsolute, relative, resolve } from 'node:path';
import process from 'node:process';
import { statfsSync } from 'node:fs';

const PINNED_COMMIT = 'fbe6228777e7d9afefcd61a413844e790ae75db7';
const PINNED_TAG = 'v5.2.0';
const GiB = 1024n ** 3n;
const REQUIRED_FREE_BYTES = 160n * GiB;
const MAX_WALL_TIME_MS = 12 * 60 * 60 * 1000;
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--') || index + 1 >= argv.length) {
      throw new Error(`Expected --name value argument, observed ${key}`);
    }
    parsed[key.slice(2)] = argv[index + 1];
    index += 1;
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

function freeBytes(path) {
  const value = statfsSync(path, { bigint: true });
  return value.bavail * value.bsize;
}

function treeBytes(path) {
  return Number(exec('/usr/bin/du', ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

async function sha256File(path) {
  return sha256Bytes(await readFile(path));
}

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function writeJsonExclusive(path, value) {
  const bodyWithoutHash = `${JSON.stringify(value, null, 2)}\n`;
  const record = { ...value, receiptHash: sha256Bytes(Buffer.from(bodyWithoutHash)) };
  const body = `${JSON.stringify(record, null, 2)}\n`;
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(body);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return record;
}

function stageConfiguration(stage, workspace, source) {
  if (stage === 'dependencies') {
    return {
      command: '/usr/bin/make',
      args: ['update'],
      expectedArtifact: resolve(source, 'lib', 'macos_arm64'),
      buildRoot: null,
    };
  }
  const match = stage.match(/^build-([ab])$/);
  if (match) {
    const buildRoot = resolve(workspace, `build-${match[1]}`);
    return {
      command: '/usr/bin/make',
      args: [`BUILD_DIR=${buildRoot}`, `NPROCS=${os.cpus().length}`],
      expectedArtifact: resolve(buildRoot, 'bin', 'Blender.app', 'Contents', 'MacOS', 'Blender'),
      buildRoot,
    };
  }
  throw new Error(`Unsupported stage: ${stage}`);
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
    env: {
      PATH: FROZEN_PATH,
      LANG: 'C',
      LC_ALL: 'C',
      HOME: process.env.HOME,
      GIT_CONFIG_NOSYSTEM: '1',
      GIT_TERMINAL_PROMPT: '0',
      NPROCS: String(os.cpus().length),
    },
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
  }, MAX_WALL_TIME_MS);
  const terminal = await new Promise(resolveClose => {
    child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal }));
  });
  clearTimeout(timeout);
  if (forceTimer) clearTimeout(forceTimer);
  stdoutStream.end();
  stderrStream.end();
  await Promise.all([finished(stdoutStream), finished(stderrStream)]);
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  return {
    childPid: child.pid,
    exitCode: spawnError ? 1 : terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    spawnError: spawnError?.message ?? null,
    elapsedSeconds,
    stdoutPath,
    stderrPath,
    timingPath,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  for (const required of ['stage', 'source', 'workspace', 'evidence-root']) {
    if (!args[required]) throw new Error(`Missing --${required}`);
  }
  if (!isAbsolute(args.source) || !isAbsolute(args.workspace)) {
    throw new Error('Source and workspace must be absolute paths');
  }
  const repositoryRoot = exec('/usr/bin/git', ['rev-parse', '--show-toplevel'], process.cwd());
  const source = await realpath(args.source);
  const workspace = await realpath(args.workspace);
  const evidenceRoot = resolve(repositoryRoot, args['evidence-root']);
  const evidenceRootReal = await realpath(evidenceRoot);
  const evidenceBase = resolve(repositoryRoot, 'experiments', 'ai-native-studio-f0');
  if (relative(evidenceBase, evidenceRootReal).startsWith('..')) {
    throw new Error('Evidence root must remain under experiments/ai-native-studio-f0');
  }
  if (relative(repositoryRoot, workspace).startsWith('..') === false) {
    throw new Error('External workspace must remain outside the research repository');
  }
  if (relative(workspace, source).startsWith('..')) {
    throw new Error('Source must remain inside the external workspace');
  }
  const config = stageConfiguration(args.stage, workspace, source);
  const stageRoot = resolve(evidenceRootReal, args.stage);
  await mkdir(stageRoot, { recursive: false });

  const observedFreeBytes = freeBytes(workspace);
  const sourceHeadBefore = git(source, ['rev-parse', 'HEAD']);
  const sourceTagBefore = git(source, ['describe', '--tags', '--exact-match', 'HEAD']);
  const sourceStatusBefore = git(source, ['status', '--porcelain=v1']);
  const dependencyStatusBefore = args.stage === 'dependencies'
    ? git(source, ['submodule', 'status', '--', 'lib/macos_arm64'])
    : null;
  const failures = [];
  if (observedFreeBytes < REQUIRED_FREE_BYTES) failures.push('FREE_DISK_BELOW_160_GIB');
  if (sourceHeadBefore !== PINNED_COMMIT) failures.push('SOURCE_HEAD_MISMATCH');
  if (sourceTagBefore !== PINNED_TAG) failures.push('SOURCE_TAG_MISMATCH');
  if (sourceStatusBefore !== '') failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (config.buildRoot && await exists(config.buildRoot)) failures.push('BUILD_ROOT_ALREADY_EXISTS');
  if (args.stage === 'dependencies' && !dependencyStatusBefore.startsWith('-')) {
    failures.push('DEPENDENCY_SUBMODULE_ALREADY_INITIALIZED');
  }

  const admission = {
    schemaVersion: 'bfs.f0SourceStageAdmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    stage: args.stage,
    observedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: { path: source, head: sourceHeadBefore, tag: sourceTagBefore, clean: sourceStatusBefore === '' },
    workspace,
    expectedArtifact: config.expectedArtifact,
    failures,
    authorizedNativeProcessStarts: failures.length === 0 ? 1 : 0,
  };
  await writeJsonExclusive(resolve(stageRoot, 'admission.json'), admission);
  if (failures.length > 0) {
    await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
      schemaVersion: 'bfs.f0SourceStageReceipt.v0.1',
      protocol: 'F0-SOURCE-FEASIBILITY',
      gate: 'F0.1',
      stage: args.stage,
      status: 'BLOCKED',
      nativeProcessStarts: 0,
      failures,
    });
    process.stdout.write(`F0_SOURCE_STAGE_BLOCKED stage=${args.stage} failures=${failures.join(',')} native=0\n`);
    process.exitCode = 2;
    return;
  }

  const workspaceBytesBefore = treeBytes(workspace);
  const freeBytesBefore = freeBytes(workspace);
  const startedAt = new Date().toISOString();
  const result = await runTimed({ ...config, cwd: source, stageRoot });
  const endedAt = new Date().toISOString();
  const freeBytesAfter = freeBytes(workspace);
  const workspaceBytesAfter = treeBytes(workspace);
  const sourceHeadAfter = git(source, ['rev-parse', 'HEAD']);
  const sourceStatusAfter = git(source, ['status', '--porcelain=v1']);
  const dependencyStatusAfter = args.stage === 'dependencies'
    ? git(source, ['submodule', 'status', '--', 'lib/macos_arm64'])
    : null;
  const artifactExists = args.stage === 'dependencies'
    ? !dependencyStatusAfter.startsWith('-')
    : await exists(config.expectedArtifact);
  const artifactStat = artifactExists ? await stat(config.expectedArtifact) : null;
  const timingText = await readFile(result.timingPath, 'utf8').catch(() => '');
  const timing = parseTiming(timingText);
  const checks = {
    processExitZero: result.exitCode === 0 && result.signal === null && !result.timedOut,
    sourceHeadPinned: sourceHeadAfter === PINNED_COMMIT,
    sourceWorktreeClean: sourceStatusAfter === '',
    expectedArtifactExists: artifactExists,
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  const receipt = {
    schemaVersion: 'bfs.f0SourceStageReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    stage: args.stage,
    status,
    startedAt,
    endedAt,
    command: { executable: config.command, args: config.args, cwd: source },
    process: {
      pid: result.childPid,
      exitCode: result.exitCode,
      signal: result.signal,
      timedOut: result.timedOut,
      spawnError: result.spawnError,
      elapsedSeconds: result.elapsedSeconds,
      timing,
    },
    resources: {
      freeBytesBefore: freeBytesBefore.toString(),
      freeBytesAfter: freeBytesAfter.toString(),
      consumedFreeBytes: (freeBytesBefore - freeBytesAfter).toString(),
      workspaceBytesBefore,
      workspaceBytesAfter,
      workspaceGrowthBytes: workspaceBytesAfter - workspaceBytesBefore,
    },
    source: {
      path: source,
      headBefore: sourceHeadBefore,
      headAfter: sourceHeadAfter,
      cleanBefore: sourceStatusBefore === '',
      cleanAfter: sourceStatusAfter === '',
    },
    artifact: {
      path: config.expectedArtifact,
      exists: artifactExists,
      bytes: artifactStat?.isFile() ? artifactStat.size : null,
      dependencyStatusBefore,
      dependencyStatusAfter,
    },
    logs: {
      stdout: { path: relative(repositoryRoot, result.stdoutPath), sha256: await sha256File(result.stdoutPath), bytes: (await stat(result.stdoutPath)).size },
      stderr: { path: relative(repositoryRoot, result.stderrPath), sha256: await sha256File(result.stderrPath), bytes: (await stat(result.stderrPath)).size },
      timing: { path: relative(repositoryRoot, result.timingPath), sha256: await sha256File(result.timingPath), bytes: (await stat(result.timingPath)).size },
    },
    checks,
  };
  await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), receipt);
  process.stdout.write(`F0_SOURCE_STAGE_${status} stage=${args.stage} seconds=${result.elapsedSeconds.toFixed(3)} artifact=${artifactExists}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
