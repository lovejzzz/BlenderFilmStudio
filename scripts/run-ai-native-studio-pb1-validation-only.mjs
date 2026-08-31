#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  closeSync,
  createWriteStream,
  existsSync,
  lstatSync,
  mkdirSync,
  openSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmdirSync,
  statfsSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { finished } from 'node:stream/promises';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const MAKE = '/usr/bin/make';
const TIME = '/usr/bin/time';
const PLUTIL = '/usr/bin/plutil';
const FILE = '/usr/bin/file';
const LIPO = '/usr/bin/lipo';
const DU = '/usr/bin/du';
const SCRIPT_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(SCRIPT_PATH), '..');
const SPEC_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-execution.v0.3.json';
const DOCUMENT_RELATIVE = 'research/2026-08-31-ai-native-studio-pb1-validation-only-execution-authorization-v0.3.zh-CN.md';
const REQUEST_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-authorization-request.v0.2.json';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const DOCUMENT_PATH = resolve(REPOSITORY_ROOT, DOCUMENT_RELATIVE);
const REQUEST_PATH = resolve(REPOSITORY_ROOT, REQUEST_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const executeRequested = process.argv.includes('--execute');
const selfTestRequested = process.argv.includes('--self-test');

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [key, canonicalize(child)]),
    );
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

function sha256File(path) {
  return sha256Bytes(readFileSync(path));
}

function receiptHash(value) {
  const copy = structuredClone(value);
  delete copy.receiptHash;
  return sha256Bytes(canonicalJson(copy));
}

function receiptHashPass(value) {
  return value.receiptHash === receiptHash(value);
}

function writeJsonExclusive(path, value) {
  const record = structuredClone(value);
  record.receiptHash = receiptHash(record);
  const descriptor = openSync(path, 'wx', 0o600);
  try {
    writeFileSync(descriptor, `${JSON.stringify(record, null, 2)}\n`);
  } finally {
    closeSync(descriptor);
  }
  return record;
}

function frozenEnv(extra = {}) {
  const value = {
    ...process.env,
    PATH: FROZEN_PATH,
    LANG: 'C',
    LC_ALL: 'C',
    GH_PROMPT_DISABLED: '1',
    GIT_TERMINAL_PROMPT: '0',
    GIT_LFS_SKIP_SMUDGE: '1',
    ...extra,
  };
  for (const [name, item] of Object.entries(value)) if (item === undefined || item === null) delete value[name];
  return value;
}

function execResult(command, args, options = {}) {
  try {
    const stdout = execFileSync(command, args, {
      cwd: options.cwd,
      encoding: options.encoding ?? 'utf8',
      env: frozenEnv(options.env),
      input: options.input,
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: options.timeout ?? 300_000,
      maxBuffer: options.maxBuffer ?? 512 * 1024 * 1024,
    });
    return { exitCode: 0, signal: null, stdout, stderr: '' };
  } catch (error) {
    return {
      exitCode: Number.isInteger(error.status) ? error.status : 1,
      signal: error.signal ?? null,
      stdout: error.stdout ?? '',
      stderr: error.stderr ?? String(error.message ?? error),
    };
  }
}

function asText(value) {
  return Buffer.isBuffer(value) ? value.toString('utf8').trim() : String(value ?? '').trim();
}

function execRequired(command, args, options = {}) {
  const result = execResult(command, args, options);
  if (result.exitCode !== 0) {
    const error = new Error(`Command failed (${result.exitCode}): ${command} ${args.join(' ')}`);
    error.command = [command, ...args];
    error.stdout = asText(result.stdout);
    error.stderr = asText(result.stderr);
    throw error;
  }
  return options.encoding === null ? result.stdout : asText(result.stdout);
}

function git(root, args, options = {}) {
  return execRequired(GIT, ['-C', root, ...args], options);
}

function freeBytes(path) {
  const stats = statfsSync(path, { bigint: true });
  return stats.bavail * stats.bsize;
}

function nearestExistingDirectory(path) {
  let current = resolve(path);
  while (!existsSync(current)) {
    const parent = dirname(current);
    if (parent === current) throw new Error(`No existing ancestor for ${path}`);
    current = parent;
  }
  return current;
}

function treeBytes(path) {
  if (!existsSync(path)) return 0;
  return Number(execRequired(DU, ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ls-remote line: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function ghJson(args) {
  return JSON.parse(execRequired(GH, args));
}

function collectRemote(spec) {
  const metadata = ghJson(['api', `repos/${spec.repository.fullName}`]);
  const branches = ghJson(['api', `repos/${spec.repository.fullName}/branches?per_page=100`]);
  const pulls = ghJson(['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]);
  const releases = ghJson(['api', `repos/${spec.repository.fullName}/releases?per_page=100`]);
  const heads = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--tags', spec.repository.url]));
  return {
    observedAt: new Date().toISOString(),
    metadata: {
      id: metadata.id,
      fullName: metadata.full_name,
      fork: metadata.fork,
      parent: metadata.parent?.full_name ?? null,
      visibility: metadata.visibility,
      private: metadata.private,
      defaultBranch: metadata.default_branch,
      htmlUrl: metadata.html_url,
    },
    branchNames: branches.map(item => item.name).sort(),
    headRefs: heads,
    tagRefs: tags,
    mainOid: heads.find(item => item.ref === 'refs/heads/main')?.oid ?? null,
    pullRequestCount: pulls.length,
    releaseCount: releases.length,
  };
}

function remoteChecks(remote, spec) {
  return {
    repositoryIdentityExact:
      remote.metadata.id === spec.repository.repositoryId &&
      remote.metadata.fullName === spec.repository.fullName,
    publicForkTopologyExact:
      remote.metadata.fork === true &&
      remote.metadata.parent === spec.repository.forkParent &&
      remote.metadata.visibility === spec.repository.visibility &&
      remote.metadata.private === false,
    defaultBranchExact: remote.metadata.defaultBranch === spec.repository.defaultBranch,
    mainExact: remote.mainOid === spec.publicationBaseline.head,
    onlyMain:
      remote.branchNames.join('\n') === 'main' &&
      remote.headRefs.length === 1 &&
      remote.headRefs[0]?.ref === spec.repository.expectedOnlyRemoteHead,
    zeroTags: remote.tagRefs.length === spec.repository.expectedRemoteTags,
    zeroPullRequests: remote.pullRequestCount === spec.repository.expectedPullRequests,
    zeroReleases: remote.releaseCount === spec.repository.expectedReleases,
  };
}

function listRestrictedProcesses() {
  const ownPid = process.pid;
  const result = execRequired('/bin/ps', ['-axo', 'pid=,comm=,args=']);
  return result.split(/\r?\n/).map(line => line.trim()).filter(Boolean).filter(line => {
    const pid = Number(line.split(/\s+/, 1)[0]);
    if (pid === ownPid) return false;
    return /(?:Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|Blender\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line);
  });
}

function storageIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', files: 0, bytes: 0, manifestSha256: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    const names = readdirSync(path).sort((left, right) => left.localeCompare(right, 'en'));
    for (const name of names) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute, { bigint: true });
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) walk(absolute, relativePath);
      else if (item.isFile()) records.push(`${relativePath}\0${item.size}\0${item.mtimeNs}`);
    }
  }
  walk(root);
  const bytes = records.reduce((sum, line) => sum + Number(line.split('\0')[1]), 0);
  return {
    state: 'PRESENT',
    files: records.length,
    bytes,
    manifestSha256: sha256Bytes(`${records.join('\n')}\n`),
  };
}

function treeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', entries: 0, digest: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    const names = readdirSync(path).sort((left, right) => left.localeCompare(right, 'en'));
    for (const name of names) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) {
        records.push({ path: relativePath, type: 'directory', mode: item.mode & 0o7777 });
        walk(absolute, relativePath);
      } else if (item.isFile()) {
        records.push({ path: relativePath, type: 'file', mode: item.mode & 0o7777, bytes: item.size, sha256: sha256File(absolute) });
      } else if (item.isSymbolicLink()) {
        records.push({ path: relativePath, type: 'symlink', mode: item.mode & 0o7777 });
      }
    }
  }
  walk(root);
  return { state: 'PRESENT', entries: records.length, digest: sha256Bytes(canonicalJson(records)) };
}

function collectPreflight(spec) {
  const request = JSON.parse(readFileSync(REQUEST_PATH, 'utf8'));
  const retainedDependency = spec.dependency.retainedCheckout;
  const retainedSource = resolve(retainedDependency, '..', '..');
  const retainedLfsStorage = resolve(retainedSource, '.git', 'lfs');
  const remote = collectRemote(spec);
  const observed = {
    schemaVersion: 'bfs.pb1ValidationOnlyPreflight.v0.3',
    observedAt: new Date().toISOString(),
    status: 'PENDING',
    specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
    authorizationDocument: { path: DOCUMENT_RELATIVE, sha256: sha256File(DOCUMENT_PATH) },
    authorizationRequest: { path: REQUEST_RELATIVE, sha256: sha256File(REQUEST_PATH) },
    runner: { path: 'scripts/run-ai-native-studio-pb1-validation-only.mjs', sha256: sha256File(SCRIPT_PATH) },
    authorization: {
      granted: spec.authorization.granted,
      exactTextMatchesRequest: spec.authorization.exactTextZhCN === request.exactRequestedAuthorizationTextZhCN,
    },
    research: {
      root: REPOSITORY_ROOT,
      head: git(REPOSITORY_ROOT, ['rev-parse', 'HEAD']),
      upstreamHead: git(REPOSITORY_ROOT, ['rev-parse', '@{upstream}']),
      clean: git(REPOSITORY_ROOT, ['status', '--porcelain=v1']) === '',
    },
    host: {
      hostname: os.hostname(),
      platform: os.platform(),
      release: os.release(),
      architecture: os.arch(),
      cpuModel: os.cpus()[0]?.model ?? null,
      logicalCpuCount: os.cpus().length,
      memoryBytes: os.totalmem(),
      node: process.version,
    },
    disk: {
      checkedPath: nearestExistingDirectory(dirname(spec.paths.externalRoot)),
      freeBytes: freeBytes(nearestExistingDirectory(dirname(spec.paths.externalRoot))).toString(),
      requiredBytes: String(spec.resources.minimumFreeBytesBeforeAnyFormalMutation),
    },
    roots: {
      externalRoot: spec.paths.externalRoot,
      externalRootAbsent: !existsSync(spec.paths.externalRoot),
      evidenceRoot: spec.paths.evidenceRoot,
      evidenceRootAbsent: !existsSync(resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot)),
    },
    retainedSource: {
      root: retainedSource,
      head: git(retainedSource, ['rev-parse', 'HEAD']),
      clean: git(retainedSource, ['status', '--porcelain=v1']) === '',
      lfsStorage: retainedLfsStorage,
      lfsStorageIdentity: storageIdentity(retainedLfsStorage),
    },
    retainedDependency: {
      root: retainedDependency,
      head: git(retainedDependency, ['rev-parse', 'HEAD']),
      clean: git(retainedDependency, ['status', '--porcelain=v1']) === '',
      origin: git(retainedDependency, ['remote', 'get-url', 'origin']),
    },
    restrictedProcesses: listRestrictedProcesses(),
    forbiddenRuntimeEnvironmentPresent: ['BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_DATAFILES', 'BLENDER_USER_EXTENSIONS'].filter(name => process.env[name]),
    remote,
    remoteChecks: remoteChecks(remote, spec),
  };
  const failures = [];
  if (!observed.authorization.granted) failures.push('OWNER_AUTHORIZATION_NOT_GRANTED');
  if (!observed.authorization.exactTextMatchesRequest) failures.push('AUTHORIZATION_TEXT_MISMATCH');
  if (!observed.research.clean) failures.push('RESEARCH_WORKTREE_NOT_CLEAN');
  if (observed.research.head !== observed.research.upstreamHead) failures.push('RESEARCH_HEAD_NOT_PUSHED');
  if (observed.host.platform !== 'darwin' || observed.host.architecture !== 'arm64') failures.push('HOST_ARCHITECTURE_MISMATCH');
  if (!/Apple M2 Max/.test(observed.host.cpuModel ?? '')) failures.push('HOST_MODEL_MISMATCH');
  if (BigInt(observed.disk.freeBytes) < BigInt(observed.disk.requiredBytes)) failures.push('INSUFFICIENT_DISK');
  if (!observed.roots.externalRootAbsent || !observed.roots.evidenceRootAbsent) failures.push('FRESH_ROOT_REQUIRED');
  if (observed.retainedSource.head !== spec.publicationBaseline.soleParent || !observed.retainedSource.clean) failures.push('RETAINED_SOURCE_IDENTITY_MISMATCH');
  if (observed.retainedSource.lfsStorageIdentity.state !== 'PRESENT' || observed.retainedSource.lfsStorageIdentity.files === 0) failures.push('RETAINED_LFS_STORAGE_MISSING');
  if (observed.retainedDependency.head !== spec.dependency.commit || !observed.retainedDependency.clean || observed.retainedDependency.origin !== spec.dependency.origin) failures.push('RETAINED_DEPENDENCY_MISMATCH');
  if (observed.restrictedProcesses.length !== 0) failures.push('RESTRICTED_NATIVE_PROCESS_RUNNING');
  if (observed.forbiddenRuntimeEnvironmentPresent.length !== 0) failures.push('BLENDER_USER_OVERRIDE_ENVIRONMENT_PRESENT');
  for (const [name, pass] of Object.entries(observed.remoteChecks)) if (!pass) failures.push(`REMOTE_${name.toUpperCase()}`);
  observed.failures = failures;
  observed.status = failures.length === 0 ? 'ACCEPTED' : 'BLOCKED';
  return observed;
}

function validationFailures(value, spec) {
  const failures = [];
  if (value.head !== spec.publicationBaseline.head) failures.push('PUBLICATION_HEAD_MISMATCH');
  if (value.shallow || value.reachableCommits !== spec.publicationBaseline.reachableCommitCount) failures.push('HISTORY_INCOMPLETE');
  if (!value.licensesExact) failures.push('LICENSE_OR_NOTICE_MISMATCH');
  if (value.generatedTrackedPaths !== 0) failures.push('GENERATED_PRODUCT_TRACKED');
  if (value.dependencyHead !== spec.dependency.commit || !value.dependencyClean) failures.push('DEPENDENCY_IDENTITY_MISMATCH');
  if (!value.sourceClean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (value.remoteWriteRequested || value.lfsNetworkRequested) failures.push('FORBIDDEN_NETWORK_MUTATION_REQUESTED');
  if (BigInt(value.freeBytes) < BigInt(spec.resources.minimumFreeBytesBeforeAnyFormalMutation)) failures.push('INSUFFICIENT_DISK');
  if (!value.productIdentityExact || !value.officialConfigurationUnchanged) failures.push('PRODUCT_IDENTITY_OR_CONFIGURATION_DRIFT');
  return failures;
}

function runNegativeControls(spec) {
  const base = {
    head: spec.publicationBaseline.head,
    shallow: false,
    reachableCommits: spec.publicationBaseline.reachableCommitCount,
    licensesExact: true,
    generatedTrackedPaths: 0,
    dependencyHead: spec.dependency.commit,
    dependencyClean: true,
    sourceClean: true,
    remoteWriteRequested: false,
    lfsNetworkRequested: false,
    freeBytes: String(spec.resources.minimumFreeBytesBeforeAnyFormalMutation),
    productIdentityExact: true,
    officialConfigurationUnchanged: true,
  };
  const cases = [
    ['WRONG_HEAD_REJECTED', { head: '0'.repeat(40) }, 'PUBLICATION_HEAD_MISMATCH'],
    ['SHALLOW_HISTORY_REJECTED', { shallow: true }, 'HISTORY_INCOMPLETE'],
    ['CHANGED_LICENSE_REJECTED', { licensesExact: false }, 'LICENSE_OR_NOTICE_MISMATCH'],
    ['GENERATED_PRODUCT_REJECTED', { generatedTrackedPaths: 1 }, 'GENERATED_PRODUCT_TRACKED'],
    ['DIRTY_DEPENDENCY_REJECTED', { dependencyClean: false }, 'DEPENDENCY_IDENTITY_MISMATCH'],
    ['DIRTY_SOURCE_REJECTED', { sourceClean: false }, 'SOURCE_WORKTREE_NOT_CLEAN'],
    ['REMOTE_LFS_NETWORK_REJECTED', { lfsNetworkRequested: true }, 'FORBIDDEN_NETWORK_MUTATION_REQUESTED'],
    ['INSUFFICIENT_DISK_REJECTED', { freeBytes: String(BigInt(spec.resources.minimumFreeBytesBeforeAnyFormalMutation) - 1n) }, 'INSUFFICIENT_DISK'],
    ['IDENTITY_CONFIG_DRIFT_REJECTED', { officialConfigurationUnchanged: false }, 'PRODUCT_IDENTITY_OR_CONFIGURATION_DRIFT'],
  ];
  return cases.map(([id, mutation, expectedFailure]) => {
    const failures = validationFailures({ ...base, ...mutation }, spec);
    return { id, expectedFailure, failures, accepted: failures.length === 0, pass: failures.includes(expectedFailure) && failures.length >= 1 };
  });
}

function tracked(commandLog, stage, operation, command, args, options = {}) {
  const startedAt = new Date().toISOString();
  const result = execResult(command, args, options);
  commandLog.push({
    stage,
    operation,
    command,
    args,
    cwd: options.cwd ?? null,
    network: options.network ?? 'NONE',
    externalWrite: false,
    startedAt,
    finishedAt: new Date().toISOString(),
    exitCode: result.exitCode,
    stdoutSha256: sha256Bytes(Buffer.isBuffer(result.stdout) ? result.stdout : String(result.stdout ?? '')),
    stderrSha256: sha256Bytes(Buffer.isBuffer(result.stderr) ? result.stderr : String(result.stderr ?? '')),
  });
  return result;
}

function trackedRequired(commandLog, stage, operation, command, args, options = {}) {
  const result = tracked(commandLog, stage, operation, command, args, options);
  if (result.exitCode !== 0) {
    const error = new Error(`${stage} failed (${result.exitCode}): ${command} ${args.join(' ')}`);
    error.stdout = asText(result.stdout);
    error.stderr = asText(result.stderr);
    throw error;
  }
  return options.encoding === null ? result.stdout : asText(result.stdout);
}

async function runLoggedProcess({ command, args, cwd, stdoutPath, stderrPath, timingPath = null, env = {}, timeoutMs, monitoredRoot = null, maximumBytes = null }) {
  const actualCommand = timingPath ? TIME : command;
  const actualArgs = timingPath ? ['-lp', '-o', timingPath, command, ...args] : args;
  const stdoutStream = createWriteStream(stdoutPath, { flags: 'wx', mode: 0o600 });
  const stderrStream = createWriteStream(stderrPath, { flags: 'wx', mode: 0o600 });
  const startedAt = new Date().toISOString();
  const started = process.hrtime.bigint();
  let spawnError = null;
  let timedOut = false;
  let resourceExceeded = false;
  let maximumObservedRootBytes = monitoredRoot ? treeBytes(monitoredRoot) : 0;
  let forceTimer = null;
  const child = spawn(actualCommand, actualArgs, {
    cwd,
    detached: true,
    env: frozenEnv(env),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.on('error', error => { spawnError = error; });
  child.stdout.on('data', chunk => stdoutStream.write(chunk));
  child.stderr.on('data', chunk => stderrStream.write(chunk));
  const terminate = reason => {
    if (reason === 'timeout') timedOut = true;
    if (reason === 'resource') resourceExceeded = true;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
    forceTimer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
    }, 5000);
  };
  const timeout = setTimeout(() => terminate('timeout'), timeoutMs);
  const monitor = monitoredRoot && maximumBytes ? setInterval(() => {
    try {
      maximumObservedRootBytes = Math.max(maximumObservedRootBytes, treeBytes(monitoredRoot));
      if (maximumObservedRootBytes > maximumBytes && !resourceExceeded) terminate('resource');
    } catch {
      // The final resource check remains authoritative if a transient sample fails.
    }
  }, 15_000) : null;
  const terminal = await new Promise(resolveClose => child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal })));
  clearTimeout(timeout);
  if (monitor) clearInterval(monitor);
  if (forceTimer) clearTimeout(forceTimer);
  stdoutStream.end();
  stderrStream.end();
  await Promise.all([finished(stdoutStream), finished(stderrStream)]);
  if (monitoredRoot) maximumObservedRootBytes = Math.max(maximumObservedRootBytes, treeBytes(monitoredRoot));
  return {
    startedAt,
    finishedAt: new Date().toISOString(),
    elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    pid: child.pid,
    exitCode: spawnError ? 1 : terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    resourceExceeded,
    spawnError: spawnError?.message ?? null,
    maximumObservedRootBytes,
    command: { executable: command, args, cwd },
    stdoutPath,
    stderrPath,
    timingPath,
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

function sourceStatus(source) {
  return {
    head: git(source, ['rev-parse', 'HEAD']),
    tree: git(source, ['rev-parse', 'HEAD^{tree}']),
    parents: git(source, ['show', '-s', '--format=%P', 'HEAD']).split(/\s+/).filter(Boolean),
    clean: git(source, ['status', '--porcelain=v1']) === '',
    status: git(source, ['status', '--porcelain=v1']),
    shallow: git(source, ['rev-parse', '--is-shallow-repository']) === 'true',
    reachableCommits: Number(git(source, ['rev-list', '--count', 'HEAD'])),
  };
}

function materializedLfsInventory(source) {
  const parsed = JSON.parse(git(source, ['lfs', 'ls-files', '--json'], { timeout: 300_000 }));
  const files = [...parsed.files].sort((left, right) => left.name.localeCompare(right.name, 'en'));
  const mismatches = [];
  let bytes = 0;
  const manifest = [];
  for (const item of files) {
    const path = resolve(source, item.name);
    if (!existsSync(path)) {
      mismatches.push({ path: item.name, failure: 'MISSING' });
      continue;
    }
    const observedBytes = statSync(path).size;
    const observedSha256 = sha256File(path);
    bytes += observedBytes;
    manifest.push(`${item.name}\0${observedBytes}\0${observedSha256}`);
    if (observedBytes !== item.size || observedSha256 !== item.oid) {
      mismatches.push({ path: item.name, expectedBytes: item.size, observedBytes, expectedSha256: item.oid, observedSha256 });
    }
  }
  return {
    count: files.length,
    bytes,
    downloadedCount: files.filter(item => item.downloaded).length,
    checkoutCount: files.filter(item => item.checkout).length,
    manifestSha256: sha256Bytes(`${manifest.join('\n')}\n`),
    mismatches,
  };
}

function parseDiffStats(source, range) {
  const paths = git(source, ['diff', '--name-only', '-z', range]).split('\0').filter(Boolean).sort();
  const numstat = git(source, ['diff', '--numstat', range]).split(/\r?\n/).filter(Boolean);
  let additions = 0;
  let deletions = 0;
  let binaryPaths = 0;
  for (const line of numstat) {
    const [left, right] = line.split('\t', 3);
    if (left === '-' || right === '-') binaryPaths += 1;
    else {
      additions += Number(left);
      deletions += Number(right);
    }
  }
  return { paths, changedPaths: paths.length, additions, deletions, binaryPaths };
}

function checkAttributes(source, paths) {
  return paths.map(path => {
    const output = git(source, ['check-attr', 'filter', 'diff', 'merge', 'text', '--', path]);
    const values = Object.fromEntries(output.split(/\r?\n/).map(line => {
      const match = line.match(/^(.+): (filter|diff|merge|text): (.+)$/);
      if (!match) throw new Error(`Unexpected check-attr output: ${line}`);
      return [match[2], match[3]];
    }));
    return { path, values, pass: ['filter', 'diff', 'merge', 'text'].every(name => values[name] === 'unset') };
  });
}

function secretMatchesForText(text, path) {
  const patterns = [
    ['PRIVATE_KEY', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g],
    ['GITHUB_TOKEN', /\bgh[oprsu]_[A-Za-z0-9_]{20,}\b/g],
    ['AWS_ACCESS_KEY', /\bAKIA[0-9A-Z]{16}\b/g],
    ['SECRET_ASSIGNMENT', /\b(?:password|secret|token|api[_-]?key)\b\s*[:=]\s*["'][^"']{8,}["']/gi],
  ];
  const findings = [];
  for (const [kind, pattern] of patterns) {
    for (const match of text.matchAll(pattern)) findings.push({ path, kind, offset: match.index });
  }
  return findings;
}

function inspectLicensesGeneratedAndSecrets(source, spec) {
  const allPaths = git(source, ['ls-files', '-z']).split('\0').filter(Boolean).sort();
  const noticePaths = allPaths.filter(path => /(^|\/)(?:copying|license|notice)(?:[._-]|$)/i.test(path)).sort();
  const generatedPaths = allPaths.filter(path =>
    /(^|\/)CMakeCache\.txt$/.test(path) ||
    /(^|\/)CMakeFiles\//.test(path) ||
    /(^|\/)build-[^/]+\//.test(path) ||
    /\.dmg$/i.test(path) ||
    /\.app\/Contents\/MacOS\/Blender$/.test(path) ||
    /\.(?:o|dylib|exe)$/i.test(path));
  const changedPaths = parseDiffStats(source, `${spec.publicationBaseline.mergeBase}..HEAD`).paths;
  const secretFindings = [];
  let scannedTextPaths = 0;
  for (const path of changedPaths) {
    const absolute = resolve(source, path);
    if (!existsSync(absolute) || statSync(absolute).size > 2 * 1024 * 1024) continue;
    const bytes = readFileSync(absolute);
    if (bytes.includes(0)) continue;
    scannedTextPaths += 1;
    secretFindings.push(...secretMatchesForText(bytes.toString('utf8'), path));
  }
  return {
    copyingSha256: sha256File(resolve(source, 'COPYING')),
    assetsLicenseSha256: sha256File(resolve(source, 'assets', 'LICENSE')),
    noticePathCount: noticePaths.length,
    noticePathListSha256: sha256Bytes(`${noticePaths.join('\n')}\n`),
    noticePaths,
    generatedPaths,
    secretScan: { scope: 'fork-owned changed textual paths only', scannedTextPaths, findings: secretFindings, findingCount: secretFindings.length },
  };
}

function plistRaw(path, key) {
  const result = execResult(PLUTIL, ['-extract', key, 'raw', path]);
  return result.exitCode === 0 ? asText(result.stdout) : null;
}

function parseMarker(text, prefix) {
  const line = text.split(/\r?\n/).find(value => value.startsWith(prefix));
  return line ? JSON.parse(line.slice(prefix.length)) : null;
}

function evidenceBinding(evidenceRoot, name) {
  const path = resolve(evidenceRoot, name);
  const record = JSON.parse(readFileSync(path, 'utf8'));
  return { file: name, fileSha256: sha256File(path), receiptHash: record.receiptHash, receiptHashPass: receiptHashPass(record), status: record.status };
}

function runSelfTest(spec) {
  const checks = [];
  const add = (id, pass) => checks.push({ id, pass: Boolean(pass) });
  add('AUTHORIZATION_GRANTED', spec.authorization.granted === true);
  add('AUTHORIZATION_TEXT_BOUND', spec.authorization.exactTextZhCN === JSON.parse(readFileSync(REQUEST_PATH, 'utf8')).exactRequestedAuthorizationTextZhCN);
  add('PUBLICATION_HEAD_FIXED', spec.publicationBaseline.head === '4061e12bd45a2bec83e68d0cf49abbf56d4738f6');
  add('F0_PARENT_FIXED', spec.publicationBaseline.soleParent === 'fa1b578bb421bbc82b3106b7d4223e11e65fae1d');
  add('ONE_BUILD_TWO_STARTS_ZERO_RENDERS', spec.operations.cleanNativeArm64Builds === 1 && spec.operations.maximumProductStarts === 2 && spec.operations.renderCalls === 0);
  add('ZERO_ENGINE_WRITES', spec.operations.engineNetworkWrites === 0 && spec.authorization.engineSourceMutation === false);
  add('ZERO_LFS_NETWORK', spec.operations.lfsNetworkDownloads === 0 && spec.operations.lfsUploads === 0);
  add('PB2_PB7_LOCKED', spec.authorization.beginPb2ThroughPb7 === false);
  add('NINE_NEGATIVE_CONTROLS', runNegativeControls(spec).length === 9 && runNegativeControls(spec).every(item => item.pass));
  const sample = { schemaVersion: 'test', status: 'PASS' };
  sample.receiptHash = receiptHash(sample);
  add('RECEIPT_HASH', receiptHashPass(sample));
  const failed = checks.filter(item => !item.pass);
  const result = { schemaVersion: 'bfs.pb1ValidationOnlySelfTest.v0.3', status: failed.length === 0 ? 'PASS' : 'FAIL', checksPassed: checks.length - failed.length, checksTotal: checks.length, checks, failures: failed.map(item => item.id) };
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (failed.length) process.exitCode = 1;
}

async function execute(spec) {
  const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
  const externalRoot = spec.paths.externalRoot;
  const source = spec.paths.sourceRoot;
  const buildRoot = spec.paths.buildRoot;
  const isolatedHome = spec.paths.isolatedHome;
  const retainedDependency = spec.dependency.retainedCheckout;
  const retainedSource = resolve(retainedDependency, '..', '..');
  const retainedLfsStorage = resolve(retainedSource, '.git', 'lfs');
  const commandLog = [];
  const counters = {
    publicEngineNetworkClones: 0,
    localLfsMaterializations: 0,
    localDependencyClones: 0,
    cleanNativeArm64Builds: 0,
    productStarts: 0,
    renderCalls: 0,
    engineRemoteWrites: 0,
    engineRefUpdates: 0,
    lfsNetworkDownloads: 0,
    lfsUploads: 0,
    releases: 0,
    signingOperations: 0,
    notarizationOperations: 0,
    dmgOperations: 0,
    pb2ThroughPb7Mutations: 0,
    modelCalls: 0,
  };
  let stage = 'PREFLIGHT';
  let evidenceCreated = false;
  try {
    const preflight = collectPreflight(spec);
    mkdirSync(dirname(evidenceRoot), { recursive: true });
    mkdirSync(evidenceRoot);
    evidenceCreated = true;
    writeJsonExclusive(resolve(evidenceRoot, 'preflight.json'), { ...preflight, counters });
    if (preflight.status !== 'ACCEPTED') throw new Error(`PREFLIGHT_BLOCKED:${preflight.failures.join(',')}`);

    stage = 'NEGATIVE_CONTROLS';
    const controls = runNegativeControls(spec);
    const negative = writeJsonExclusive(resolve(evidenceRoot, 'negative-controls.json'), {
      schemaVersion: 'bfs.pb1ValidationOnlyNegativeControls.v0.3',
      observedAt: new Date().toISOString(),
      status: controls.length === spec.requiredNegativeControls.length && controls.every(item => item.pass) ? 'PASS' : 'FAIL',
      externalRootExistedDuringControls: existsSync(externalRoot),
      controls,
      checksPassed: controls.filter(item => item.pass).length,
      checksTotal: controls.length,
      productStarts: 0,
      nativeBuilds: 0,
    });
    if (negative.status !== 'PASS' || negative.externalRootExistedDuringControls) throw new Error('NEGATIVE_CONTROLS_FAILED_OR_MUTATED');

    stage = 'PUBLIC_ENGINE_CLONE';
    mkdirSync(dirname(externalRoot), { recursive: true });
    mkdirSync(externalRoot);
    const cloneStdout = resolve(evidenceRoot, 'engine-clone.stdout.log');
    const cloneStderr = resolve(evidenceRoot, 'engine-clone.stderr.log');
    const clone = await runLoggedProcess({
      command: GIT,
      args: ['clone', '--no-checkout', '--progress', spec.repository.url, source],
      cwd: externalRoot,
      stdoutPath: cloneStdout,
      stderrPath: cloneStderr,
      timeoutMs: 20 * 60 * 1000,
      monitoredRoot: externalRoot,
      maximumBytes: spec.resources.maximumExternalRootBytes,
    });
    counters.publicEngineNetworkClones += 1;
    commandLog.push({ stage, operation: 'public engine read-only clone', command: GIT, args: clone.command.args, cwd: externalRoot, network: 'READ_ONLY_CLONE', externalWrite: false, exitCode: clone.exitCode, startedAt: clone.startedAt, finishedAt: clone.finishedAt });
    if (clone.exitCode !== 0 || clone.timedOut || clone.resourceExceeded) throw new Error(`PUBLIC_ENGINE_CLONE_FAILED:${clone.exitCode}`);
    trackedRequired(commandLog, stage, 'disable push URL in fresh clone', GIT, ['-C', source, 'remote', 'set-url', '--push', 'origin', 'disabled://film-engine-writes-forbidden']);
    trackedRequired(commandLog, stage, 'bind retained local LFS storage', GIT, ['-C', source, 'config', 'lfs.storage', retainedLfsStorage]);
    trackedRequired(commandLog, stage, 'disable LFS network endpoint', GIT, ['-C', source, 'config', 'lfs.url', 'file:///PB1-LFS-NETWORK-DISABLED']);
    trackedRequired(commandLog, stage, 'checkout exact publication head with smudge disabled', GIT, ['-C', source, 'checkout', '--detach', spec.publicationBaseline.head]);

    stage = 'LOCAL_LFS_MATERIALIZATION';
    const lfsStorageBefore = preflight.retainedSource.lfsStorageIdentity;
    trackedRequired(commandLog, stage, 'single local-only LFS checkout', GIT, ['-C', source, 'lfs', 'checkout'], { timeout: 20 * 60 * 1000 });
    counters.localLfsMaterializations += 1;
    const lfsInventory = materializedLfsInventory(source);
    const lfsStorageAfter = storageIdentity(retainedLfsStorage);

    stage = 'HISTORY_AND_SOURCE_IDENTITY';
    const initialSource = sourceStatus(source);
    const fsck = tracked(commandLog, stage, 'full strict local graph verification', GIT, ['-C', source, 'fsck', '--full', '--strict'], { timeout: 20 * 60 * 1000 });
    const mergeBase = git(source, ['merge-base', spec.publicationBaseline.mergeBase, 'HEAD']);
    const forkCommits = Number(git(source, ['rev-list', '--count', `${spec.publicationBaseline.mergeBase}..HEAD`]));
    const c1Diff = parseDiffStats(source, `${spec.publicationBaseline.soleParent}..HEAD`);
    const f0Diff = parseDiffStats(source, `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`);
    const headDiff = parseDiffStats(source, `${spec.publicationBaseline.mergeBase}..HEAD`);
    const brandAttributes = checkAttributes(source, spec.sourceIdentity.ordinaryBrandBlobs.map(item => item.path));
    const brandAssets = spec.sourceIdentity.ordinaryBrandBlobs.map(item => {
      const path = resolve(source, item.path);
      return { path: item.path, gitBlobOidSha1: git(source, ['rev-parse', `HEAD:${item.path}`]), bytes: statSync(path).size, sha256: sha256File(path), expected: item };
    });
    const historyChecks = {
      headExact: initialSource.head === spec.publicationBaseline.head,
      treeExact: initialSource.tree === spec.publicationBaseline.tree,
      soleParentExact: initialSource.parents.join(' ') === spec.publicationBaseline.soleParent,
      nonShallow: !initialSource.shallow,
      reachableCommitCountExact: initialSource.reachableCommits === spec.publicationBaseline.reachableCommitCount,
      mergeBaseExact: mergeBase === spec.publicationBaseline.mergeBase,
      forkCommitCountExact: forkCommits === spec.publicationBaseline.forkCommitCount,
      fullFsckPass: fsck.exitCode === 0,
      c1PathsExact: c1Diff.paths.join('\n') === [...spec.publicationBaseline.c1ChangedPaths].sort().join('\n'),
      f0PatchExact: f0Diff.changedPaths === spec.sourceIdentity.f0PatchBeforeC1.changedPaths && f0Diff.additions === spec.sourceIdentity.f0PatchBeforeC1.additions && f0Diff.deletions === spec.sourceIdentity.f0PatchBeforeC1.deletions,
      publicationPatchExact: headDiff.changedPaths === spec.sourceIdentity.changedPathsFromMergeBase && headDiff.additions === spec.sourceIdentity.textAdditionsFromMergeBase && headDiff.deletions === spec.sourceIdentity.textDeletionsFromMergeBase && headDiff.binaryPaths === spec.sourceIdentity.binaryPathsFromMergeBase,
    };
    const remoteBefore = preflight.remote;
    const remoteHistory = writeJsonExclusive(resolve(evidenceRoot, 'remote-and-history.json'), {
      schemaVersion: 'bfs.pb1RemoteAndHistory.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(historyChecks).every(Boolean) ? 'PASS' : 'FAIL',
      remoteBefore,
      remoteChecks: preflight.remoteChecks,
      clone: {
        command: clone.command,
        exitCode: clone.exitCode,
        elapsedSeconds: clone.elapsedSeconds,
        timedOut: clone.timedOut,
        resourceExceeded: clone.resourceExceeded,
        stdoutSha256: sha256File(cloneStdout),
        stderrSha256: sha256File(cloneStderr),
      },
      history: { ...initialSource, mergeBase, forkCommits, fsckExitCode: fsck.exitCode, c1Diff, f0Diff, headDiff },
      checks: historyChecks,
    });
    if (remoteHistory.status !== 'PASS') throw new Error('REMOTE_OR_HISTORY_CHECK_FAILED');
    const sourceChecks = {
      sourceCleanAfterMaterialization: sourceStatus(source).clean,
      lfsCountExact: lfsInventory.count === spec.sourceIdentity.lfs.trackedPathsAtPublicationHead,
      lfsBytesExact: lfsInventory.bytes === spec.sourceIdentity.lfs.contentBytesAtPublicationHead,
      allLfsDownloaded: lfsInventory.downloadedCount === lfsInventory.count,
      allLfsCheckout: lfsInventory.checkoutCount === lfsInventory.count,
      allLfsHashesExact: lfsInventory.mismatches.length === 0,
      retainedLfsStorageUnchanged: canonicalJson(lfsStorageBefore) === canonicalJson(lfsStorageAfter),
      ordinaryBrandAssetsExact: brandAssets.every(item => item.gitBlobOidSha1 === item.expected.gitBlobOidSha1 && item.bytes === item.expected.bytes && item.sha256 === item.expected.sha256),
      brandAttributesUnset: brandAttributes.every(item => item.pass),
    };
    const sourceIdentityReceipt = writeJsonExclusive(resolve(evidenceRoot, 'source-identity.json'), {
      schemaVersion: 'bfs.pb1SourceIdentity.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(sourceChecks).every(Boolean) ? 'PASS' : 'FAIL',
      source: sourceStatus(source),
      lfs: lfsInventory,
      retainedLfsStorage: { before: lfsStorageBefore, after: lfsStorageAfter },
      brandAssets,
      brandAttributes,
      checks: sourceChecks,
    });
    if (sourceIdentityReceipt.status !== 'PASS') throw new Error('SOURCE_IDENTITY_CHECK_FAILED');

    stage = 'LICENSE_GENERATED_SECRET';
    const licenseInventory = inspectLicensesGeneratedAndSecrets(source, spec);
    const licenseChecks = {
      copyingExact: licenseInventory.copyingSha256 === spec.sourceIdentity.licenses.copyingSha256,
      assetsLicenseExact: licenseInventory.assetsLicenseSha256 === spec.sourceIdentity.licenses.assetsLicenseSha256,
      noticePathCountExact: licenseInventory.noticePathCount === spec.sourceIdentity.licenses.noticePathCount,
      noticePathListExact: licenseInventory.noticePathListSha256 === spec.sourceIdentity.licenses.noticePathListSha256,
      generatedProductsAbsentFromGit: licenseInventory.generatedPaths.length === spec.sourceIdentity.generatedBuildOrDmgPathsAllowedInGit,
      forkOwnedSecretFindingsZero: licenseInventory.secretScan.findingCount === spec.sourceIdentity.expectedForkOwnedSecretFindings,
    };
    const licenseReceipt = writeJsonExclusive(resolve(evidenceRoot, 'license-and-generated-paths.json'), {
      schemaVersion: 'bfs.pb1LicenseGeneratedPaths.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(licenseChecks).every(Boolean) ? 'PASS' : 'FAIL',
      inventory: licenseInventory,
      checks: licenseChecks,
    });
    if (licenseReceipt.status !== 'PASS') throw new Error('LICENSE_GENERATED_SECRET_CHECK_FAILED');

    stage = 'LOCAL_DEPENDENCY_CLONE';
    const dependencyPath = resolve(source, 'lib', 'macos_arm64');
    if (existsSync(dependencyPath)) {
      if (readdirSync(dependencyPath).length !== 0) throw new Error('DEPENDENCY_TARGET_NOT_EMPTY');
      rmdirSync(dependencyPath);
    }
    trackedRequired(commandLog, stage, 'exact retained dependency local clone', GIT, ['clone', '--no-hardlinks', '--no-checkout', retainedDependency, dependencyPath], { timeout: 20 * 60 * 1000 });
    counters.localDependencyClones += 1;
    trackedRequired(commandLog, stage, 'checkout exact dependency commit', GIT, ['-C', dependencyPath, 'checkout', '--detach', spec.dependency.commit]);
    const dependencyObserved = {
      path: dependencyPath,
      head: git(dependencyPath, ['rev-parse', 'HEAD']),
      clean: git(dependencyPath, ['status', '--porcelain=v1']) === '',
      origin: git(dependencyPath, ['remote', 'get-url', 'origin']),
      sourceSuperprojectStatus: git(source, ['status', '--porcelain=v1']),
      bytes: treeBytes(dependencyPath),
    };
    const dependencyChecks = {
      retainedDependencyStillExact: git(retainedDependency, ['rev-parse', 'HEAD']) === spec.dependency.commit && git(retainedDependency, ['status', '--porcelain=v1']) === '',
      clonedDependencyExact: dependencyObserved.head === spec.dependency.commit,
      clonedDependencyClean: dependencyObserved.clean,
      localOriginExact: dependencyObserved.origin === retainedDependency,
      superprojectClean: dependencyObserved.sourceSuperprojectStatus === '',
    };
    const dependencyReceipt = writeJsonExclusive(resolve(evidenceRoot, 'dependency.json'), {
      schemaVersion: 'bfs.pb1Dependency.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(dependencyChecks).every(Boolean) ? 'PASS' : 'FAIL',
      retained: preflight.retainedDependency,
      observed: dependencyObserved,
      checks: dependencyChecks,
    });
    if (dependencyReceipt.status !== 'PASS') throw new Error('DEPENDENCY_CHECK_FAILED');

    stage = 'CLEAN_NATIVE_BUILD';
    if (existsSync(buildRoot)) throw new Error('BUILD_ROOT_NOT_FRESH');
    if (!sourceStatus(source).clean) throw new Error('SOURCE_DIRTY_BEFORE_BUILD');
    if (freeBytes(externalRoot) < BigInt(spec.resources.minimumFreeBytesBeforeAnyFormalMutation)) throw new Error('INSUFFICIENT_DISK_BEFORE_BUILD');
    const buildStdout = resolve(evidenceRoot, 'build.stdout.log');
    const buildStderr = resolve(evidenceRoot, 'build.stderr.log');
    const buildTiming = resolve(evidenceRoot, 'build.timing.log');
    const build = await runLoggedProcess({
      command: MAKE,
      args: [`BUILD_DIR=${buildRoot}`, 'NPROCS=12'],
      cwd: source,
      stdoutPath: buildStdout,
      stderrPath: buildStderr,
      timingPath: buildTiming,
      timeoutMs: spec.resources.maximumBuildWallSeconds * 1000,
      monitoredRoot: externalRoot,
      maximumBytes: spec.resources.maximumExternalRootBytes,
    });
    counters.cleanNativeArm64Builds += 1;
    commandLog.push({ stage, operation: 'single clean native arm64 build', command: MAKE, args: build.command.args, cwd: source, network: 'NONE', externalWrite: false, startedAt: build.startedAt, finishedAt: build.finishedAt, exitCode: build.exitCode });
    const timing = parseTiming(readFileSync(buildTiming, 'utf8'));
    const sourceApp = resolve(buildRoot, 'bin', 'Blender.app');
    const finalApp = resolve(buildRoot, 'bin', spec.build.expectedApplicationName);
    let bundleRenamed = false;
    if (build.exitCode === 0 && existsSync(sourceApp) && !existsSync(finalApp)) {
      renameSync(sourceApp, finalApp);
      bundleRenamed = true;
    }
    const binary = resolve(finalApp, 'Contents', 'MacOS', 'Blender');
    const plist = resolve(finalApp, 'Contents', 'Info.plist');
    const binaryExists = existsSync(binary);
    const fileIdentity = binaryExists ? execRequired(FILE, [binary]) : '';
    const architectures = binaryExists ? execRequired(LIPO, ['-archs', binary]).split(/\s+/).filter(Boolean) : [];
    const buildChecks = {
      processExitZero: build.exitCode === 0 && build.signal === null,
      notTimedOut: !build.timedOut,
      externalResourceCeilingHeld: !build.resourceExceeded && build.maximumObservedRootBytes <= spec.resources.maximumExternalRootBytes,
      wallWithinCeiling: build.elapsedSeconds <= spec.resources.maximumBuildWallSeconds,
      peakRssWithinCeiling: Number.isFinite(timing.maximumResidentSetSizeBytes) && timing.maximumResidentSetSizeBytes <= spec.resources.maximumBuildPeakRssBytes,
      sourceBundleProduced: existsSync(sourceApp) || bundleRenamed,
      productBundleRenamed: bundleRenamed && existsSync(finalApp) && basename(finalApp) === spec.build.expectedApplicationName,
      binaryExists,
      nativeArm64Only: architectures.join(' ') === 'arm64' && /Mach-O 64-bit executable arm64/.test(fileIdentity),
      bundleIdentifierExact: existsSync(plist) && plistRaw(plist, 'CFBundleIdentifier') === spec.build.expectedBundleIdentifier,
      bundleNameExact: existsSync(plist) && plistRaw(plist, 'CFBundleName') === 'Film Studio Engine F0',
      sourceStillClean: sourceStatus(source).clean,
      sourceHeadStillExact: sourceStatus(source).head === spec.publicationBaseline.head,
    };
    const buildReceipt = writeJsonExclusive(resolve(evidenceRoot, 'build.json'), {
      schemaVersion: 'bfs.pb1CleanNativeBuild.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(buildChecks).every(Boolean) ? 'PASS' : 'FAIL',
      process: build,
      timing,
      artifact: binaryExists ? {
        app: finalApp,
        binary,
        binaryBytes: statSync(binary).size,
        binarySha256: sha256File(binary),
        fileIdentity,
        architectures,
        plist: {
          CFBundleName: plistRaw(plist, 'CFBundleName'),
          CFBundleDisplayName: plistRaw(plist, 'CFBundleDisplayName'),
          CFBundleIdentifier: plistRaw(plist, 'CFBundleIdentifier'),
          CFBundleShortVersionString: plistRaw(plist, 'CFBundleShortVersionString'),
        },
      } : null,
      logs: {
        stdout: { path: basename(buildStdout), bytes: statSync(buildStdout).size, sha256: sha256File(buildStdout) },
        stderr: { path: basename(buildStderr), bytes: statSync(buildStderr).size, sha256: sha256File(buildStderr) },
        timing: { path: basename(buildTiming), bytes: statSync(buildTiming).size, sha256: sha256File(buildTiming) },
      },
      checks: buildChecks,
    });
    if (buildReceipt.status !== 'PASS') throw new Error('CLEAN_NATIVE_BUILD_FAILED');

    stage = 'RUNTIME_IDENTITY_CONFIGURATION';
    if (!sourceStatus(source).clean) throw new Error('SOURCE_DIRTY_BEFORE_PRODUCT_START');
    const actualOfficialRoot = resolve(os.homedir(), 'Library', 'Application Support', 'Blender');
    const officialBefore = treeIdentity(actualOfficialRoot);
    mkdirSync(isolatedHome);
    const isolatedOfficialRoot = resolve(isolatedHome, 'Library', 'Application Support', 'Blender');
    const expectedProductRoot = resolve(isolatedHome, 'Library', 'Application Support', spec.build.expectedConfigurationNamespace, '5.2');
    const versionResult = execResult(binary, ['--version'], { timeout: 120_000, env: { HOME: isolatedHome } });
    counters.productStarts += 1;
    commandLog.push({ stage, operation: 'product identity version process', command: binary, args: ['--version'], cwd: buildRoot, network: 'NONE', externalWrite: false, exitCode: versionResult.exitCode });
    const versionOutput = `${asText(versionResult.stdout)}\n${asText(versionResult.stderr)}`.trim();
    const expression = [
      'import bpy, json',
      'events = []',
      'bpy.app.handlers.render_pre.append(lambda scene: events.append(scene.name))',
      'decode = lambda value: value.decode("utf-8") if isinstance(value, bytes) else str(value)',
      'paths = {kind: bpy.utils.user_resource(kind, create=True) for kind in ("CONFIG", "SCRIPTS", "DATAFILES", "EXTENSIONS")}',
      'saved = sorted(bpy.ops.wm.save_userpref())',
      'payload = {"version": bpy.app.version_string, "buildHash": decode(bpy.app.build_hash), "buildBranch": decode(bpy.app.build_branch), "binaryPath": bpy.app.binary_path, "paths": paths, "saveUserPref": saved, "renderCalls": len(events)}',
      'print("PB1_RUNTIME=" + json.dumps(payload, sort_keys=True), flush=True)',
    ].join('; ');
    const runtimeStdout = resolve(evidenceRoot, 'runtime.stdout.log');
    const runtimeStderr = resolve(evidenceRoot, 'runtime.stderr.log');
    const runtimeProcess = await runLoggedProcess({
      command: binary,
      args: ['--background', '--factory-startup', '--python-expr', expression],
      cwd: buildRoot,
      stdoutPath: runtimeStdout,
      stderrPath: runtimeStderr,
      timeoutMs: 120_000,
      env: { HOME: isolatedHome },
    });
    counters.productStarts += 1;
    commandLog.push({ stage, operation: 'isolated identity and configuration process', command: binary, args: runtimeProcess.command.args, cwd: buildRoot, network: 'NONE', externalWrite: false, startedAt: runtimeProcess.startedAt, finishedAt: runtimeProcess.finishedAt, exitCode: runtimeProcess.exitCode });
    const runtimeOutput = `${readFileSync(runtimeStdout, 'utf8')}\n${readFileSync(runtimeStderr, 'utf8')}`;
    const runtimePayload = parseMarker(runtimeOutput, 'PB1_RUNTIME=');
    const officialAfter = treeIdentity(actualOfficialRoot);
    const isolatedOfficialAfter = treeIdentity(isolatedOfficialRoot);
    const productConfigAfter = treeIdentity(expectedProductRoot);
    const expectedPaths = {
      CONFIG: resolve(expectedProductRoot, 'config'),
      SCRIPTS: resolve(expectedProductRoot, 'scripts'),
      DATAFILES: resolve(expectedProductRoot, 'datafiles'),
      EXTENSIONS: resolve(expectedProductRoot, 'extensions'),
    };
    const runtimeChecks = {
      exactlyTwoProductStarts: counters.productStarts === spec.operations.maximumProductStarts,
      versionProcessExitZero: versionResult.exitCode === 0,
      versionExact: versionOutput.includes(`Film Studio Engine F0 ${spec.build.expectedVersion}`),
      versionBuildHashExact: versionOutput.includes(spec.build.expectedBuildHashPrefix),
      configurationProcessExitZero: runtimeProcess.exitCode === 0 && runtimeProcess.signal === null && !runtimeProcess.timedOut,
      runtimePayloadPresent: runtimePayload !== null,
      runtimeVersionExact: runtimePayload?.version === spec.build.expectedVersion,
      runtimeBuildHashExact: runtimePayload?.buildHash?.startsWith(spec.build.expectedBuildHashPrefix),
      runtimeBinaryExact: runtimePayload?.binaryPath === binary,
      runtimePathsExact: runtimePayload !== null && Object.entries(expectedPaths).every(([name, path]) => runtimePayload.paths?.[name] === path),
      userPreferenceSaved: runtimePayload?.saveUserPref?.includes('FINISHED'),
      zeroRenderCalls: runtimePayload?.renderCalls === 0 && counters.renderCalls === 0,
      officialConfigurationUnchanged: officialBefore.state === officialAfter.state && officialBefore.digest === officialAfter.digest,
      isolatedOfficialConfigurationAbsent: isolatedOfficialAfter.state === 'ABSENT',
      productConfigurationCreated: productConfigAfter.state === 'PRESENT',
      sourceStillClean: sourceStatus(source).clean,
    };
    const runtimeReceipt = writeJsonExclusive(resolve(evidenceRoot, 'runtime-identity.json'), {
      schemaVersion: 'bfs.pb1RuntimeIdentityConfiguration.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(runtimeChecks).every(Boolean) ? 'PASS' : 'FAIL',
      productStarts: counters.productStarts,
      renders: counters.renderCalls,
      versionProcess: { exitCode: versionResult.exitCode, signal: versionResult.signal, output: versionOutput },
      configurationProcess: {
        exitCode: runtimeProcess.exitCode,
        signal: runtimeProcess.signal,
        timedOut: runtimeProcess.timedOut,
        elapsedSeconds: runtimeProcess.elapsedSeconds,
        payload: runtimePayload,
        stdout: { path: basename(runtimeStdout), bytes: statSync(runtimeStdout).size, sha256: sha256File(runtimeStdout) },
        stderr: { path: basename(runtimeStderr), bytes: statSync(runtimeStderr).size, sha256: sha256File(runtimeStderr) },
      },
      configuration: { actualOfficialRoot, officialBefore, officialAfter, isolatedOfficialRoot, isolatedOfficialAfter, expectedProductRoot, productConfigAfter, expectedPaths },
      checks: runtimeChecks,
    });
    if (runtimeReceipt.status !== 'PASS') throw new Error('RUNTIME_IDENTITY_CONFIGURATION_FAILED');

    stage = 'FINAL_ZERO_WRITE_CONFIRMATION';
    const remoteAfter = collectRemote(spec);
    const remoteAfterChecks = remoteChecks(remoteAfter, spec);
    const networkReceipt = writeJsonExclusive(resolve(evidenceRoot, 'network-and-mutation-log.json'), {
      schemaVersion: 'bfs.pb1NetworkMutationLog.v0.3',
      observedAt: new Date().toISOString(),
      status: Object.values(remoteAfterChecks).every(Boolean) && remoteAfter.mainOid === remoteBefore.mainOid ? 'PASS' : 'FAIL',
      commands: commandLog,
      counters,
      remoteBefore,
      remoteAfter,
      remoteAfterChecks,
      remoteMainUnchanged: remoteAfter.mainOid === remoteBefore.mainOid,
      unauthorizedActionsPerformed: [],
    });
    if (networkReceipt.status !== 'PASS') throw new Error('REMOTE_CHANGED_DURING_VALIDATION');

    const boundNames = [
      'preflight.json',
      'negative-controls.json',
      'remote-and-history.json',
      'source-identity.json',
      'license-and-generated-paths.json',
      'dependency.json',
      'build.json',
      'runtime-identity.json',
      'network-and-mutation-log.json',
    ];
    const bindings = boundNames.map(name => evidenceBinding(evidenceRoot, name));
    const finalSource = sourceStatus(source);
    const finalChecks = {
      allBoundReceiptsPass: bindings.every(item => item.receiptHashPass && item.status !== 'FAIL'),
      allRequiredOperationsExact:
        counters.publicEngineNetworkClones === spec.operations.publicEngineNetworkClones &&
        counters.localLfsMaterializations === spec.operations.localLfsMaterializations &&
        counters.localDependencyClones === spec.operations.localDependencyClones &&
        counters.cleanNativeArm64Builds === spec.operations.cleanNativeArm64Builds &&
        counters.productStarts === spec.operations.maximumProductStarts,
      allForbiddenCountersZero: [
        'renderCalls', 'engineRemoteWrites', 'engineRefUpdates', 'lfsNetworkDownloads', 'lfsUploads', 'releases',
        'signingOperations', 'notarizationOperations', 'dmgOperations', 'pb2ThroughPb7Mutations', 'modelCalls',
      ].every(name => counters[name] === 0),
      sourceHeadExact: finalSource.head === spec.publicationBaseline.head,
      sourceTreeExact: finalSource.tree === spec.publicationBaseline.tree,
      sourceClean: finalSource.clean,
      remoteMainUnchanged: remoteAfter.mainOid === spec.publicationBaseline.head,
      externalRootWithinCeiling: treeBytes(externalRoot) <= spec.resources.maximumExternalRootBytes,
      evidenceRootWithinCeilingBeforeVerdict: treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes,
    };
    const verdict = writeJsonExclusive(resolve(evidenceRoot, 'verdict.json'), {
      schemaVersion: 'bfs.pb1ValidationOnlyVerdict.v0.3',
      gate: 'PB.1',
      mode: 'VALIDATION_ONLY',
      observedAt: new Date().toISOString(),
      status: Object.values(finalChecks).every(Boolean) ? 'PASS' : 'FAIL',
      publicationHead: spec.publicationBaseline.head,
      f0CodeIdentityParent: spec.publicationBaseline.soleParent,
      dependencyCommit: spec.dependency.commit,
      evidenceBindings: bindings,
      counters,
      resources: { externalRootBytes: treeBytes(externalRoot), evidenceRootBytesBeforeVerdict: treeBytes(evidenceRoot) },
      checks: finalChecks,
      failures: Object.entries(finalChecks).filter(([, pass]) => !pass).map(([name]) => name),
      claimCeiling: 'PB.1 validation-only proves repository/source identity and one clean same-host arm64 build; it does not authorize PB.2-PB.7 or prove distribution, production readiness, cross-platform support, or autonomous filmmaking.',
      stopRulePreserved: true,
    });
    if (verdict.status !== 'PASS') throw new Error(`PB1_VERDICT_FAILED:${verdict.failures.join(',')}`);
    process.stdout.write(`PB1_VALIDATION_ONLY_PASS receipt=${verdict.receiptHash} buildSeconds=${build.elapsedSeconds.toFixed(3)}\n`);
  } catch (error) {
    if (evidenceCreated) {
      const failurePath = resolve(evidenceRoot, 'failure.json');
      if (!existsSync(failurePath)) {
        writeJsonExclusive(failurePath, {
          schemaVersion: 'bfs.pb1ValidationOnlyFailure.v0.3',
          gate: 'PB.1',
          mode: 'VALIDATION_ONLY',
          status: 'FAIL',
          observedAt: new Date().toISOString(),
          failedStage: stage,
          error: String(error.message ?? error),
          command: error.command ?? null,
          stderr: error.stderr ?? null,
          counters,
          externalRootExists: existsSync(externalRoot),
          externalRootBytes: treeBytes(externalRoot),
          engineRemoteWrites: counters.engineRemoteWrites,
          stopRulePreserved: true,
        });
      }
      const verdictPath = resolve(evidenceRoot, 'verdict.json');
      if (!existsSync(verdictPath)) {
        writeJsonExclusive(verdictPath, {
          schemaVersion: 'bfs.pb1ValidationOnlyVerdict.v0.3',
          gate: 'PB.1',
          mode: 'VALIDATION_ONLY',
          status: 'FAIL',
          observedAt: new Date().toISOString(),
          failedStage: stage,
          failureReceiptHash: JSON.parse(readFileSync(failurePath, 'utf8')).receiptHash,
          counters,
          stopRulePreserved: true,
        });
      }
    }
    process.stderr.write(`PB1_VALIDATION_ONLY_FAIL stage=${stage} error=${String(error.message ?? error)}\n`);
    process.exitCode = 1;
  }
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
if (selfTestRequested) {
  runSelfTest(spec);
} else if (executeRequested) {
  await execute(spec);
} else {
  const preflight = collectPreflight(spec);
  process.stdout.write(`${JSON.stringify(preflight, null, 2)}\n`);
  if (preflight.status !== 'ACCEPTED') process.exitCode = 2;
}
