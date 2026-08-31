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
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { finished } from 'node:stream/promises';
import { dirname, relative, resolve } from 'node:path';
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
const REQUEST_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c1-authorization-request.v0.4.json';
const REQUEST_PATH = resolve(REPOSITORY_ROOT, REQUEST_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';

function argument(name, fallback = null) {
  const index = process.argv.indexOf(name);
  if (index < 0) return fallback;
  if (!process.argv[index + 1] || process.argv[index + 1].startsWith('--')) throw new Error(`Missing value for ${name}`);
  return process.argv[index + 1];
}

const executeRequested = process.argv.includes('--execute');
const selfTestRequested = process.argv.includes('--self-test');
const contractRelative = argument('--contract', REQUEST_RELATIVE);
const contractPath = resolve(REPOSITORY_ROOT, contractRelative);
if (relative(resolve(REPOSITORY_ROOT, 'specs'), contractPath).startsWith('..')) throw new Error('Contract must remain under specs/');

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)]));
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
  try { writeFileSync(descriptor, `${JSON.stringify(record, null, 2)}\n`); } finally { closeSync(descriptor); }
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
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: options.timeout ?? 20 * 60 * 1000,
      maxBuffer: options.maxBuffer ?? 512 * 1024 * 1024,
    });
    return { exitCode: 0, signal: null, stdout, stderr: '' };
  } catch (error) {
    return { exitCode: Number.isInteger(error.status) ? error.status : 1, signal: error.signal ?? null, stdout: error.stdout ?? '', stderr: error.stderr ?? String(error.message ?? error) };
  }
}

function asText(value) {
  return Buffer.isBuffer(value) ? value.toString('utf8').trim() : String(value ?? '').trim();
}

function execRequired(command, args, options = {}) {
  const observed = execResult(command, args, options);
  if (observed.exitCode !== 0) {
    const error = new Error(`Command failed (${observed.exitCode}): ${command} ${args.join(' ')}`);
    error.command = [command, ...args];
    error.stdout = asText(observed.stdout);
    error.stderr = asText(observed.stderr);
    throw error;
  }
  return options.encoding === null ? observed.stdout : asText(observed.stdout);
}

function git(root, args, options = {}) {
  return execRequired(GIT, ['-C', root, ...args], options);
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

function freeBytes(path) {
  const stats = statfsSync(path, { bigint: true });
  return stats.bavail * stats.bsize;
}

function treeBytes(path) {
  if (!existsSync(path)) return 0;
  return Number(execRequired(DU, ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function treeIdentity(root, filter = () => true) {
  if (!existsSync(root)) return { state: 'ABSENT', files: 0, bytes: 0, manifestSha256: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute, { bigint: true });
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) walk(absolute, relativePath);
      else if (item.isFile() && filter(relativePath)) records.push(`${relativePath}\0${item.size}\0${item.mtimeNs}`);
      else if (item.isSymbolicLink() && filter(relativePath)) records.push(`${relativePath}\0SYMLINK`);
    }
  }
  walk(root);
  return {
    state: 'PRESENT',
    files: records.length,
    bytes: records.reduce((sum, line) => sum + (line.endsWith('\0SYMLINK') ? 0 : Number(line.split('\0')[1])), 0),
    manifestSha256: sha256Bytes(`${records.join('\n')}\n`),
  };
}

function contentTreeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', entries: 0, digest: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) { records.push({ path: relativePath, type: 'directory', mode: item.mode & 0o7777 }); walk(absolute, relativePath); }
      else if (item.isFile()) records.push({ path: relativePath, type: 'file', mode: item.mode & 0o7777, bytes: item.size, sha256: sha256File(absolute) });
      else if (item.isSymbolicLink()) records.push({ path: relativePath, type: 'symlink', mode: item.mode & 0o7777 });
    }
  }
  walk(root);
  return { state: 'PRESENT', entries: records.length, digest: sha256Bytes(canonicalJson(records)) };
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected remote ref: ${line}`);
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
    metadata: { id: metadata.id, fullName: metadata.full_name, fork: metadata.fork, parent: metadata.parent?.full_name ?? null, visibility: metadata.visibility, private: metadata.private, defaultBranch: metadata.default_branch },
    branches: branches.map(item => item.name).sort(),
    heads,
    tags,
    main: heads.find(item => item.ref === 'refs/heads/main')?.oid ?? null,
    pulls: pulls.length,
    releases: releases.length,
  };
}

function remoteChecks(remote, spec) {
  return {
    identityExact: remote.metadata.id === spec.repository.repositoryId && remote.metadata.fullName === spec.repository.fullName,
    publicForkExact: remote.metadata.fork && remote.metadata.parent === spec.repository.forkParent && remote.metadata.visibility === 'public' && !remote.metadata.private,
    onlyMainExact: remote.main === spec.publicationBaseline.head && remote.heads.length === 1 && remote.heads[0]?.ref === spec.repository.expectedOnlyRemoteHead && remote.branches.join('\n') === 'main',
    zeroTagPrRelease: remote.tags.length === 0 && remote.pulls === 0 && remote.releases === 0,
  };
}

function restrictedProcesses() {
  return execRequired('/bin/ps', ['-axo', 'pid=,comm=,args=']).split(/\r?\n/).map(line => line.trim()).filter(Boolean).filter(line => {
    const pid = Number(line.split(/\s+/, 1)[0]);
    if (pid === process.pid) return false;
    return /(?:Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|Blender\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line);
  });
}

function sourceIdentity(root) {
  return {
    head: git(root, ['rev-parse', 'HEAD']),
    tree: git(root, ['rev-parse', 'HEAD^{tree}']),
    parents: git(root, ['show', '-s', '--format=%P', 'HEAD']).split(/\s+/).filter(Boolean),
    clean: git(root, ['status', '--porcelain=v1']) === '',
    status: git(root, ['status', '--porcelain=v1']),
    shallow: git(root, ['rev-parse', '--is-shallow-repository']) === 'true',
    reachableCommits: Number(git(root, ['rev-list', '--count', 'HEAD'])),
  };
}

function collectPreflight(spec) {
  const request = JSON.parse(readFileSync(REQUEST_PATH, 'utf8'));
  const attemptSource = spec.bindings.attempt01.sourceRoot;
  const retainedStorage = spec.lfsCorrection.retainedStorageRoot;
  const retainedObjects = spec.lfsCorrection.retainedObjectsSubtree;
  const retainedDependency = spec.dependency.retainedCheckout;
  const remote = collectRemote(spec);
  const observed = {
    schemaVersion: 'bfs.pb1ValidationOnlyC1Preflight.v0.5',
    observedAt: new Date().toISOString(),
    status: 'PENDING',
    contract: { path: contractRelative, sha256: sha256File(contractPath) },
    request: { path: REQUEST_RELATIVE, sha256: sha256File(REQUEST_PATH) },
    runner: { path: 'scripts/run-ai-native-studio-pb1-validation-only-c1.mjs', sha256: sha256File(SCRIPT_PATH) },
    authorization: {
      granted: spec.authorization?.granted === true,
      exactTextMatchesRequest: spec.authorization?.exactTextZhCN === request.exactRequestedAuthorizationTextZhCN,
    },
    research: { head: git(REPOSITORY_ROOT, ['rev-parse', 'HEAD']), upstream: git(REPOSITORY_ROOT, ['rev-parse', '@{upstream}']), clean: git(REPOSITORY_ROOT, ['status', '--porcelain=v1']) === '' },
    host: { platform: os.platform(), architecture: os.arch(), cpuModel: os.cpus()[0]?.model ?? null, logicalCpuCount: os.cpus().length, memoryBytes: os.totalmem(), node: process.version },
    disk: { checkedPath: nearestExistingDirectory(dirname(spec.paths.externalRoot)), freeBytes: freeBytes(nearestExistingDirectory(dirname(spec.paths.externalRoot))).toString(), requiredBytes: String(spec.resources.minimumFreeBytesBeforeAnyFormalMutation) },
    roots: { externalAbsent: !existsSync(spec.paths.externalRoot), evidenceAbsent: !existsSync(resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot)) },
    attempt01Source: { path: attemptSource, ...sourceIdentity(attemptSource) },
    retainedLfs: { storage: retainedStorage, wholeTree: treeIdentity(retainedStorage), objects: treeIdentity(retainedStorage, path => path.startsWith('objects/')) },
    dependency: { path: retainedDependency, head: git(retainedDependency, ['rev-parse', 'HEAD']), clean: git(retainedDependency, ['status', '--porcelain=v1']) === '', origin: git(retainedDependency, ['remote', 'get-url', 'origin']) },
    restrictedProcesses: restrictedProcesses(),
    forbiddenBlenderOverrides: ['BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS', 'BLENDER_USER_DATAFILES', 'BLENDER_USER_EXTENSIONS'].filter(name => process.env[name]),
    remote,
    remoteChecks: remoteChecks(remote, spec),
  };
  const failures = [];
  if (!observed.authorization.granted) failures.push('OWNER_AUTHORIZATION_NOT_GRANTED');
  if (!observed.authorization.exactTextMatchesRequest) failures.push('AUTHORIZATION_TEXT_MISMATCH');
  if (!observed.research.clean || observed.research.head !== observed.research.upstream) failures.push('RESEARCH_NOT_CLEAN_AND_PUSHED');
  if (observed.host.platform !== 'darwin' || observed.host.architecture !== 'arm64' || !/Apple M2 Max/.test(observed.host.cpuModel ?? '')) failures.push('HOST_IDENTITY_MISMATCH');
  if (BigInt(observed.disk.freeBytes) < BigInt(observed.disk.requiredBytes)) failures.push('INSUFFICIENT_DISK');
  if (!observed.roots.externalAbsent || !observed.roots.evidenceAbsent) failures.push('FRESH_ATTEMPT02_ROOTS_REQUIRED');
  const expectedAttempt = spec.bindings.attempt01;
  if (observed.attempt01Source.head !== expectedAttempt.sourceHead || observed.attempt01Source.tree !== expectedAttempt.sourceTree || !observed.attempt01Source.clean || observed.attempt01Source.shallow || observed.attempt01Source.reachableCommits !== expectedAttempt.reachableCommits) failures.push('ATTEMPT01_SOURCE_IDENTITY_MISMATCH');
  if (observed.retainedLfs.objects.files !== spec.lfsCorrection.retainedObjectFiles || observed.retainedLfs.objects.bytes !== spec.lfsCorrection.retainedObjectBytes || observed.retainedLfs.objects.manifestSha256 !== spec.lfsCorrection.retainedObjectManifestSha256) failures.push('RETAINED_LFS_OBJECTS_MISMATCH');
  if (!existsSync(retainedObjects)) failures.push('RETAINED_LFS_OBJECTS_ABSENT');
  if (observed.dependency.head !== spec.dependency.commit || !observed.dependency.clean || observed.dependency.origin !== spec.dependency.origin) failures.push('RETAINED_DEPENDENCY_MISMATCH');
  if (observed.restrictedProcesses.length || observed.forbiddenBlenderOverrides.length) failures.push('NATIVE_PROCESS_OR_ENVIRONMENT_OVERRIDE_PRESENT');
  for (const [name, pass] of Object.entries(observed.remoteChecks)) if (!pass) failures.push(`REMOTE_${name.toUpperCase()}`);
  observed.failures = failures;
  observed.status = failures.length === 0 ? 'ACCEPTED' : 'BLOCKED';
  return observed;
}

function validationFailures(value, spec) {
  const failures = [];
  if (value.publicNetworkCloneRequested) failures.push('PUBLIC_NETWORK_CLONE_FORBIDDEN');
  if (!value.attemptSourceExact) failures.push('RETAINED_ATTEMPT_SOURCE_MISMATCH');
  if (value.attributeDependentMetric) failures.push('ATTRIBUTE_DEPENDENT_METRIC_FORBIDDEN');
  if (!value.freshStorage || !value.objectsSymlinkExact) failures.push('FRESH_LFS_STORAGE_OR_OBJECT_LINK_MISMATCH');
  if (!value.retainedStorageUnchanged) failures.push('RETAINED_LFS_STORAGE_DRIFT');
  if (value.lfsNetworkRequested) failures.push('LFS_NETWORK_FORBIDDEN');
  if (!value.dependencyExact) failures.push('DEPENDENCY_MISMATCH');
  if (BigInt(value.freeBytes) < BigInt(spec.resources.minimumFreeBytesBeforeAnyFormalMutation)) failures.push('INSUFFICIENT_DISK');
  if (!value.productIdentityExact || !value.officialConfigurationUnchanged) failures.push('PRODUCT_IDENTITY_OR_CONFIGURATION_DRIFT');
  return failures;
}

function negativeControls(spec) {
  const base = { publicNetworkCloneRequested: false, attemptSourceExact: true, attributeDependentMetric: false, freshStorage: true, objectsSymlinkExact: true, retainedStorageUnchanged: true, lfsNetworkRequested: false, dependencyExact: true, freeBytes: String(spec.resources.minimumFreeBytesBeforeAnyFormalMutation), productIdentityExact: true, officialConfigurationUnchanged: true };
  const cases = [
    ['PUBLIC_NETWORK_CLONE_REJECTED', { publicNetworkCloneRequested: true }, 'PUBLIC_NETWORK_CLONE_FORBIDDEN'],
    ['WRONG_RETAINED_SOURCE_REJECTED', { attemptSourceExact: false }, 'RETAINED_ATTEMPT_SOURCE_MISMATCH'],
    ['ATTRIBUTE_DEPENDENT_METRIC_REJECTED', { attributeDependentMetric: true }, 'ATTRIBUTE_DEPENDENT_METRIC_FORBIDDEN'],
    ['WRONG_OBJECT_LINK_REJECTED', { objectsSymlinkExact: false }, 'FRESH_LFS_STORAGE_OR_OBJECT_LINK_MISMATCH'],
    ['RETAINED_STORAGE_DRIFT_REJECTED', { retainedStorageUnchanged: false }, 'RETAINED_LFS_STORAGE_DRIFT'],
    ['LFS_NETWORK_REJECTED', { lfsNetworkRequested: true }, 'LFS_NETWORK_FORBIDDEN'],
    ['DEPENDENCY_MISMATCH_REJECTED', { dependencyExact: false }, 'DEPENDENCY_MISMATCH'],
    ['INSUFFICIENT_DISK_REJECTED', { freeBytes: String(BigInt(spec.resources.minimumFreeBytesBeforeAnyFormalMutation) - 1n) }, 'INSUFFICIENT_DISK'],
    ['IDENTITY_CONFIG_DRIFT_REJECTED', { productIdentityExact: false }, 'PRODUCT_IDENTITY_OR_CONFIGURATION_DRIFT'],
  ];
  return cases.map(([id, mutation, expectedFailure]) => {
    const failures = validationFailures({ ...base, ...mutation }, spec);
    return { id, expectedFailure, failures, accepted: failures.length === 0, pass: failures.includes(expectedFailure) };
  });
}

function tracked(log, stage, operation, command, args, options = {}) {
  const startedAt = new Date().toISOString();
  const observed = execResult(command, args, options);
  log.push({ stage, operation, command, args, cwd: options.cwd ?? null, network: options.network ?? 'NONE', externalWrite: false, startedAt, finishedAt: new Date().toISOString(), exitCode: observed.exitCode, stdoutSha256: sha256Bytes(observed.stdout), stderrSha256: sha256Bytes(observed.stderr) });
  if (observed.exitCode !== 0) {
    const error = new Error(`${stage} failed (${observed.exitCode}): ${command} ${args.join(' ')}`);
    error.stderr = asText(observed.stderr);
    throw error;
  }
  return asText(observed.stdout);
}

async function runLogged({ command, args, cwd, stdoutPath, stderrPath, timingPath = null, env = {}, timeoutMs, monitoredRoot = null, maximumBytes = null }) {
  const actualCommand = timingPath ? TIME : command;
  const actualArgs = timingPath ? ['-lp', '-o', timingPath, command, ...args] : args;
  const stdout = createWriteStream(stdoutPath, { flags: 'wx', mode: 0o600 });
  const stderr = createWriteStream(stderrPath, { flags: 'wx', mode: 0o600 });
  const startedAt = new Date().toISOString();
  const started = process.hrtime.bigint();
  let timedOut = false;
  let resourceExceeded = false;
  let spawnError = null;
  let maximumObservedRootBytes = monitoredRoot ? treeBytes(monitoredRoot) : 0;
  let forceTimer = null;
  const child = spawn(actualCommand, actualArgs, { cwd, detached: true, env: frozenEnv(env), stdio: ['ignore', 'pipe', 'pipe'] });
  child.on('error', error => { spawnError = error; });
  child.stdout.on('data', chunk => stdout.write(chunk));
  child.stderr.on('data', chunk => stderr.write(chunk));
  const terminate = reason => {
    if (reason === 'timeout') timedOut = true;
    if (reason === 'resource') resourceExceeded = true;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
    forceTimer = setTimeout(() => { try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); } }, 5000);
  };
  const timeout = setTimeout(() => terminate('timeout'), timeoutMs);
  const monitor = monitoredRoot && maximumBytes ? setInterval(() => {
    try {
      maximumObservedRootBytes = Math.max(maximumObservedRootBytes, treeBytes(monitoredRoot));
      if (maximumObservedRootBytes > maximumBytes && !resourceExceeded) terminate('resource');
    } catch { /* final check remains authoritative */ }
  }, 15_000) : null;
  const terminal = await new Promise(resolveClose => child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal })));
  clearTimeout(timeout);
  if (monitor) clearInterval(monitor);
  if (forceTimer) clearTimeout(forceTimer);
  stdout.end(); stderr.end();
  await Promise.all([finished(stdout), finished(stderr)]);
  if (monitoredRoot) maximumObservedRootBytes = Math.max(maximumObservedRootBytes, treeBytes(monitoredRoot));
  return { startedAt, finishedAt: new Date().toISOString(), elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9, pid: child.pid, exitCode: spawnError ? 1 : terminal.exitCode, signal: terminal.signal, timedOut, resourceExceeded, spawnError: spawnError?.message ?? null, maximumObservedRootBytes, command: { executable: command, args, cwd }, stdoutPath, stderrPath, timingPath };
}

function parseTiming(text) {
  const seconds = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? Number.NaN);
  return { realSeconds: seconds('real'), userSeconds: seconds('user'), systemSeconds: seconds('sys'), maximumResidentSetSizeBytes: Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? Number.NaN) };
}

function materializedLfs(source) {
  const files = JSON.parse(git(source, ['lfs', 'ls-files', '--json'])).files.sort((a, b) => a.name.localeCompare(b.name, 'en'));
  let bytes = 0;
  const mismatches = [];
  const manifest = [];
  for (const item of files) {
    const path = resolve(source, item.name);
    if (!existsSync(path)) { mismatches.push({ path: item.name, failure: 'MISSING' }); continue; }
    const observedBytes = statSync(path).size;
    const observedSha256 = sha256File(path);
    bytes += observedBytes;
    manifest.push(`${item.name}\0${observedBytes}\0${observedSha256}`);
    if (observedBytes !== item.size || observedSha256 !== item.oid) mismatches.push({ path: item.name, observedBytes, observedSha256 });
  }
  return { count: files.length, bytes, downloadedCount: files.filter(item => item.downloaded).length, checkoutCount: files.filter(item => item.checkout).length, manifestSha256: sha256Bytes(`${manifest.join('\n')}\n`), mismatches };
}

function parsePointer(text) {
  const match = text.match(/^version https:\/\/git-lfs\.github\.com\/spec\/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?$/);
  return match ? { sha256: match[1], bytes: Number(match[2]) } : null;
}

function correctedMetric(source, spec) {
  const correction = spec.metricCorrection.f0ParentRangeAttributeIndependent;
  const assets = correction.formerLfsAssetObjectTransitions;
  const allPaths = git(source, ['diff', '--name-only', `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`]).split(/\r?\n/).filter(Boolean).sort();
  const assetSet = new Set(assets.map(item => item.path));
  const textPaths = allPaths.filter(path => !assetSet.has(path));
  let additions = 0;
  let deletions = 0;
  for (const path of textPaths) {
    const line = git(source, ['diff', '--numstat', `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`, '--', path]);
    const [left, right] = line.split('\t');
    if (!/^\d+$/.test(left) || !/^\d+$/.test(right)) throw new Error(`Text path classified non-text: ${path}`);
    additions += Number(left); deletions += Number(right);
  }
  const transitions = assets.map(item => {
    const baseBlob = git(source, ['rev-parse', `${spec.publicationBaseline.mergeBase}:${item.path}`]);
    const parentBlob = git(source, ['rev-parse', `${spec.publicationBaseline.soleParent}:${item.path}`]);
    const basePointer = parsePointer(execRequired(GIT, ['-C', source, 'show', `${spec.publicationBaseline.mergeBase}:${item.path}`]));
    const parentPointer = parsePointer(execRequired(GIT, ['-C', source, 'show', `${spec.publicationBaseline.soleParent}:${item.path}`]));
    return { path: item.path, baseBlob, parentBlob, basePointer, parentPointer, expected: item, pass: baseBlob === item.mergeBasePointerGitBlobOidSha1 && parentBlob === item.f0ParentPointerGitBlobOidSha1 && basePointer?.sha256 === item.mergeBaseContentSha256 && basePointer?.bytes === item.mergeBaseContentBytes && parentPointer?.sha256 === item.f0ParentContentSha256 && parentPointer?.bytes === item.f0ParentContentBytes };
  });
  return { allPaths, textPaths, textPathListSha256: sha256Bytes(`${textPaths.join('\n')}\n`), textAdditions: additions, textDeletions: deletions, transitions };
}

function publicationStats(source, spec) {
  const range = `${spec.publicationBaseline.mergeBase}..HEAD`;
  const paths = git(source, ['diff', '--name-only', range]).split(/\r?\n/).filter(Boolean).sort();
  let additions = 0; let deletions = 0; let binaries = 0;
  for (const line of git(source, ['diff', '--numstat', range]).split(/\r?\n/).filter(Boolean)) {
    const [left, right] = line.split('\t');
    if (left === '-' || right === '-') binaries += 1;
    else { additions += Number(left); deletions += Number(right); }
  }
  return { paths, changedPaths: paths.length, textAdditions: additions, textDeletions: deletions, binaryPaths: binaries };
}

function secretFindings(text, path) {
  const patterns = [
    ['PRIVATE_KEY', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g],
    ['GITHUB_TOKEN', /\bgh[oprsu]_[A-Za-z0-9_]{20,}\b/g],
    ['AWS_ACCESS_KEY', /\bAKIA[0-9A-Z]{16}\b/g],
    ['SECRET_ASSIGNMENT', /\b(?:password|secret|token|api[_-]?key)\b\s*[:=]\s*["'][^"']{8,}["']/gi],
  ];
  const findings = [];
  for (const [kind, pattern] of patterns) for (const match of text.matchAll(pattern)) findings.push({ path, kind, offset: match.index });
  return findings;
}

function licenseInventory(source, spec) {
  const paths = git(source, ['ls-files', '-z']).split('\0').filter(Boolean).sort();
  const notices = paths.filter(path => /(^|\/)(?:copying|license|notice)(?:[._-]|$)/i.test(path)).sort();
  const generated = paths.filter(path => /(^|\/)CMakeCache\.txt$/.test(path) || /(^|\/)CMakeFiles\//.test(path) || /(^|\/)build-[^/]+\//.test(path) || /\.dmg$/i.test(path) || /\.app\/Contents\/MacOS\/Blender$/.test(path) || /\.(?:o|dylib|exe)$/i.test(path));
  const changed = git(source, ['diff', '--name-only', `${spec.publicationBaseline.mergeBase}..HEAD`]).split(/\r?\n/).filter(Boolean);
  const secrets = [];
  let scannedTextPaths = 0;
  for (const path of changed) {
    const absolute = resolve(source, path);
    if (!existsSync(absolute) || statSync(absolute).size > 2 * 1024 * 1024) continue;
    const bytes = readFileSync(absolute);
    if (bytes.includes(0)) continue;
    scannedTextPaths += 1;
    secrets.push(...secretFindings(bytes.toString('utf8'), path));
  }
  return { copyingSha256: sha256File(resolve(source, 'COPYING')), assetsLicenseSha256: sha256File(resolve(source, 'assets', 'LICENSE')), noticeCount: notices.length, noticeListSha256: sha256Bytes(`${notices.join('\n')}\n`), notices, generated, secretScan: { scope: 'fork-owned changed textual paths only', scannedTextPaths, findings: secrets, findingCount: secrets.length } };
}

function plistRaw(path, key) {
  const observed = execResult(PLUTIL, ['-extract', key, 'raw', path]);
  return observed.exitCode === 0 ? asText(observed.stdout) : null;
}

function parseMarker(text, prefix) {
  const line = text.split(/\r?\n/).find(value => value.startsWith(prefix));
  return line ? JSON.parse(line.slice(prefix.length)) : null;
}

function bind(evidenceRoot, name) {
  const path = resolve(evidenceRoot, name);
  const value = JSON.parse(readFileSync(path, 'utf8'));
  return { file: name, fileSha256: sha256File(path), receiptHash: value.receiptHash, receiptHashPass: receiptHashPass(value), status: value.status };
}

function selfTest(spec) {
  const checks = [];
  const add = (id, pass) => checks.push({ id, pass: Boolean(pass) });
  add('CONTRACT_SCHEMA', ['bfs.pb1ValidationOnlyC1AuthorizationRequest.v0.4', 'bfs.pb1ValidationOnlyC1Execution.v0.5'].includes(spec.schemaVersion));
  add('NO_PUBLIC_NETWORK_CLONE', spec.authorizedOperationsIfOwnerApproves.publicEngineNetworkClones === 0);
  add('ONE_LOCAL_SOURCE_AND_MATERIALIZATION', spec.authorizedOperationsIfOwnerApproves.localEngineClonesFromRetainedAttempt01 === 1 && spec.authorizedOperationsIfOwnerApproves.additionalLocalLfsMaterializations === 1);
  add('METRIC_CORRECTION_FIXED', spec.metricCorrection.f0ParentRangeAttributeIndependent.textPathCountExcludingFormerLfsAssets === 14 && spec.metricCorrection.f0ParentRangeAttributeIndependent.textAdditions === 837 && spec.metricCorrection.f0ParentRangeAttributeIndependent.textDeletions === 64 && spec.metricCorrection.f0ParentRangeAttributeIndependent.formerLfsAssetObjectTransitions.length === 2);
  add('FRESH_OBJECT_SYMLINK_FIXED', spec.lfsCorrection.freshObjectsSymlinkTargetMustBeRetainedObjectsSubtree === true && spec.lfsCorrection.retainedStorageWholeTreeMustRemainUnchangedDuringAttempt02 === true);
  add('ONE_BUILD_TWO_STARTS_ZERO_RENDER', spec.authorizedOperationsIfOwnerApproves.cleanNativeArm64Builds === 1 && spec.authorizedOperationsIfOwnerApproves.maximumProductStarts === 2 && spec.authorizedOperationsIfOwnerApproves.renderCalls === 0);
  add('ZERO_ENGINE_AND_LFS_NETWORK_WRITE', spec.authorizedOperationsIfOwnerApproves.engineNetworkWrites === 0 && spec.authorizedOperationsIfOwnerApproves.lfsNetworkDownloads === 0 && spec.authorizedOperationsIfOwnerApproves.lfsUploads === 0);
  add('NINE_NEGATIVE_CONTROLS', negativeControls(spec).length === 9 && negativeControls(spec).every(item => item.pass));
  const sample = { schemaVersion: 'sample', status: 'PASS' }; sample.receiptHash = receiptHash(sample);
  add('RECEIPT_HASH', receiptHashPass(sample));
  const failed = checks.filter(item => !item.pass);
  const output = { schemaVersion: 'bfs.pb1ValidationOnlyC1SelfTest.v0.5', status: failed.length ? 'FAIL' : 'PASS', checksPassed: checks.length - failed.length, checksTotal: checks.length, checks, failures: failed.map(item => item.id) };
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
  if (failed.length) process.exitCode = 1;
}

async function execute(spec) {
  const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
  const externalRoot = spec.paths.externalRoot;
  const source = spec.paths.sourceRoot;
  const buildRoot = spec.paths.buildRoot;
  const isolatedHome = spec.paths.isolatedHome;
  const attemptSource = spec.bindings.attempt01.sourceRoot;
  const retainedStorage = spec.lfsCorrection.retainedStorageRoot;
  const retainedObjects = spec.lfsCorrection.retainedObjectsSubtree;
  const retainedDependency = spec.dependency.retainedCheckout;
  const commands = [];
  const counters = { publicEngineNetworkClones: 0, localEngineClones: 0, freshObjectsSymlinks: 0, localLfsMaterializations: 0, localDependencyClones: 0, nativeBuilds: 0, productStarts: 0, renders: 0, engineRemoteWrites: 0, engineRefUpdates: 0, lfsNetworkDownloads: 0, lfsUploads: 0, releases: 0, signing: 0, notarization: 0, dmg: 0, pb2ThroughPb7: 0, modelCalls: 0 };
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
    const controls = negativeControls(spec);
    const negative = writeJsonExclusive(resolve(evidenceRoot, 'negative-controls.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1NegativeControls.v0.5', observedAt: new Date().toISOString(), status: controls.length === 9 && controls.every(item => item.pass) ? 'PASS' : 'FAIL', externalRootExisted: existsSync(externalRoot), checksPassed: controls.filter(item => item.pass).length, checksTotal: controls.length, controls, counters });
    if (negative.status !== 'PASS' || negative.externalRootExisted) throw new Error('NEGATIVE_CONTROLS_FAILED');

    stage = 'LOCAL_ENGINE_CLONE';
    mkdirSync(dirname(externalRoot), { recursive: true });
    mkdirSync(externalRoot);
    tracked(commands, stage, 'fresh local-only engine clone from retained attempt-01', GIT, ['clone', '--local', '--no-checkout', attemptSource, source]);
    counters.localEngineClones += 1;
    tracked(commands, stage, 'disable source push URL', GIT, ['-C', source, 'remote', 'set-url', '--push', 'origin', 'disabled://film-engine-writes-forbidden']);
    tracked(commands, stage, 'disable LFS network URL', GIT, ['-C', source, 'config', 'lfs.url', 'file:///PB1-C1-LFS-NETWORK-DISABLED']);
    tracked(commands, stage, 'checkout exact publication head with smudge skipped', GIT, ['-C', source, 'checkout', '--detach', spec.publicationBaseline.head]);

    stage = 'FRESH_LOCAL_LFS_MATERIALIZATION';
    const localLfs = resolve(source, '.git', 'lfs');
    mkdirSync(localLfs, { recursive: true });
    const localObjects = resolve(localLfs, 'objects');
    if (existsSync(localObjects)) throw new Error('FRESH_LFS_OBJECTS_PATH_NOT_ABSENT');
    symlinkSync(retainedObjects, localObjects, 'dir');
    counters.freshObjectsSymlinks += 1;
    tracked(commands, stage, 'single additional zero-network LFS checkout', GIT, ['-C', source, 'lfs', 'checkout']);
    counters.localLfsMaterializations += 1;
    const lfs = materializedLfs(source);
    const retainedAfterMaterialization = treeIdentity(retainedStorage);
    const lfsChecks = {
      objectsLinkExact: lstatSync(localObjects).isSymbolicLink() && execRequired('/usr/bin/readlink', [localObjects]) === retainedObjects,
      freshTmpLocal: !existsSync(resolve(retainedStorage, 'tmp')) || resolve(localLfs, 'tmp') !== resolve(retainedStorage, 'tmp'),
      retainedWholeTreeUnchanged: canonicalJson(preflight.retainedLfs.wholeTree) === canonicalJson(retainedAfterMaterialization),
      countExact: lfs.count === spec.lfsCorrection.trackedPathsAtPublicationHead,
      bytesExact: lfs.bytes === spec.lfsCorrection.contentBytesAtPublicationHead,
      allMaterializedExact: lfs.downloadedCount === lfs.count && lfs.checkoutCount === lfs.count && lfs.mismatches.length === 0,
      sourceClean: sourceIdentity(source).clean,
    };
    const lfsReceipt = writeJsonExclusive(resolve(evidenceRoot, 'lfs-materialization.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1LfsMaterialization.v0.5', observedAt: new Date().toISOString(), status: Object.values(lfsChecks).every(Boolean) ? 'PASS' : 'FAIL', localLfsRoot: localLfs, localObjects, retainedBefore: preflight.retainedLfs.wholeTree, retainedAfter: retainedAfterMaterialization, lfs, checks: lfsChecks });
    if (lfsReceipt.status !== 'PASS') throw new Error('LFS_MATERIALIZATION_CHECK_FAILED');

    stage = 'HISTORY_AND_CORRECTED_SOURCE_IDENTITY';
    const sourceNow = sourceIdentity(source);
    const fsck = execResult(GIT, ['-C', source, 'fsck', '--full', '--strict']);
    const metric = correctedMetric(source, spec);
    const publication = publicationStats(source, spec);
    const correction = spec.metricCorrection.f0ParentRangeAttributeIndependent;
    const graphChecks = {
      headTreeParentExact: sourceNow.head === spec.publicationBaseline.head && sourceNow.tree === spec.publicationBaseline.tree && sourceNow.parents.join(' ') === spec.publicationBaseline.soleParent,
      sourceCleanNonShallow: sourceNow.clean && !sourceNow.shallow,
      reachableExact: sourceNow.reachableCommits === spec.publicationBaseline.reachableCommitCount,
      mergeBaseExact: git(source, ['merge-base', spec.publicationBaseline.mergeBase, 'HEAD']) === spec.publicationBaseline.mergeBase,
      forkCommitsExact: Number(git(source, ['rev-list', '--count', `${spec.publicationBaseline.mergeBase}..HEAD`])) === spec.publicationBaseline.forkCommitCount,
      fsckPass: fsck.exitCode === 0,
      metricAllPathsExact: metric.allPaths.length === correction.allChangedPaths,
      textPathsExact: metric.textPaths.length === correction.textPathCountExcludingFormerLfsAssets && metric.textPathListSha256 === correction.textPathListSha256,
      textStatsExact: metric.textAdditions === correction.textAdditions && metric.textDeletions === correction.textDeletions,
      objectTransitionsExact: metric.transitions.every(item => item.pass),
      publicationStatsExact: publication.changedPaths === spec.metricCorrection.publicationRange.changedPaths && publication.textAdditions === spec.metricCorrection.publicationRange.textAdditions && publication.textDeletions === spec.metricCorrection.publicationRange.textDeletions && publication.binaryPaths === spec.metricCorrection.publicationRange.binaryPaths,
    };
    const historyReceipt = writeJsonExclusive(resolve(evidenceRoot, 'remote-and-history.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1RemoteHistory.v0.5', observedAt: new Date().toISOString(), status: Object.values(graphChecks).every(Boolean) ? 'PASS' : 'FAIL', remoteBefore: preflight.remote, source: sourceNow, metric, publication, fsckExitCode: fsck.exitCode, checks: graphChecks });
    if (historyReceipt.status !== 'PASS') throw new Error('CORRECTED_HISTORY_IDENTITY_FAILED');

    stage = 'LICENSE_AND_GENERATED_PATHS';
    const inventory = licenseInventory(source, spec);
    const v03 = JSON.parse(readFileSync(resolve(REPOSITORY_ROOT, 'specs/ai-native-studio-pb1-validation-only-execution.v0.3.json'), 'utf8'));
    const licenseChecks = { copyingExact: inventory.copyingSha256 === v03.sourceIdentity.licenses.copyingSha256, assetsLicenseExact: inventory.assetsLicenseSha256 === v03.sourceIdentity.licenses.assetsLicenseSha256, noticeCountExact: inventory.noticeCount === v03.sourceIdentity.licenses.noticePathCount, noticeListExact: inventory.noticeListSha256 === v03.sourceIdentity.licenses.noticePathListSha256, generatedAbsent: inventory.generated.length === 0, forkOwnedSecretFindingsZero: inventory.secretScan.findingCount === 0 };
    const licenseReceipt = writeJsonExclusive(resolve(evidenceRoot, 'license-and-generated-paths.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1LicenseGenerated.v0.5', observedAt: new Date().toISOString(), status: Object.values(licenseChecks).every(Boolean) ? 'PASS' : 'FAIL', inventory, checks: licenseChecks });
    if (licenseReceipt.status !== 'PASS') throw new Error('LICENSE_GENERATED_CHECK_FAILED');

    stage = 'LOCAL_DEPENDENCY_CLONE';
    const dependencyPath = resolve(source, 'lib', 'macos_arm64');
    if (existsSync(dependencyPath)) { if (readdirSync(dependencyPath).length) throw new Error('DEPENDENCY_TARGET_NOT_EMPTY'); rmdirSync(dependencyPath); }
    tracked(commands, stage, 'exact dependency local clone', GIT, ['clone', '--no-hardlinks', '--no-checkout', retainedDependency, dependencyPath]);
    counters.localDependencyClones += 1;
    tracked(commands, stage, 'checkout exact dependency', GIT, ['-C', dependencyPath, 'checkout', '--detach', spec.dependency.commit]);
    const dependency = { head: git(dependencyPath, ['rev-parse', 'HEAD']), clean: git(dependencyPath, ['status', '--porcelain=v1']) === '', origin: git(dependencyPath, ['remote', 'get-url', 'origin']), superprojectClean: sourceIdentity(source).clean, bytes: treeBytes(dependencyPath) };
    const dependencyChecks = { headExact: dependency.head === spec.dependency.commit, clean: dependency.clean, localOriginExact: dependency.origin === retainedDependency, superprojectClean: dependency.superprojectClean, retainedStillExact: git(retainedDependency, ['rev-parse', 'HEAD']) === spec.dependency.commit && git(retainedDependency, ['status', '--porcelain=v1']) === '' };
    const dependencyReceipt = writeJsonExclusive(resolve(evidenceRoot, 'dependency.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1Dependency.v0.5', observedAt: new Date().toISOString(), status: Object.values(dependencyChecks).every(Boolean) ? 'PASS' : 'FAIL', dependency, checks: dependencyChecks });
    if (dependencyReceipt.status !== 'PASS') throw new Error('DEPENDENCY_CHECK_FAILED');

    stage = 'CLEAN_NATIVE_BUILD';
    if (existsSync(buildRoot) || !sourceIdentity(source).clean) throw new Error('BUILD_ADMISSION_FAILED');
    if (freeBytes(externalRoot) < BigInt(spec.resources.minimumFreeBytesBeforeAnyFormalMutation)) throw new Error('INSUFFICIENT_DISK_BEFORE_BUILD');
    const buildStdout = resolve(evidenceRoot, 'build.stdout.log');
    const buildStderr = resolve(evidenceRoot, 'build.stderr.log');
    const buildTiming = resolve(evidenceRoot, 'build.timing.log');
    const build = await runLogged({ command: MAKE, args: [`BUILD_DIR=${buildRoot}`, 'NPROCS=12'], cwd: source, stdoutPath: buildStdout, stderrPath: buildStderr, timingPath: buildTiming, timeoutMs: spec.resources.maximumBuildWallSeconds * 1000, monitoredRoot: externalRoot, maximumBytes: spec.resources.maximumAttempt02ExternalRootBytes });
    counters.nativeBuilds += 1;
    commands.push({ stage, operation: 'single clean native arm64 build', command: MAKE, args: build.command.args, cwd: source, network: 'NONE', externalWrite: false, startedAt: build.startedAt, finishedAt: build.finishedAt, exitCode: build.exitCode });
    const timing = parseTiming(readFileSync(buildTiming, 'utf8'));
    const sourceApp = resolve(buildRoot, 'bin', 'Blender.app');
    const app = resolve(buildRoot, 'bin', spec.build.expectedApplicationName);
    let renamed = false;
    if (build.exitCode === 0 && existsSync(sourceApp) && !existsSync(app)) { renameSync(sourceApp, app); renamed = true; }
    const binary = resolve(app, 'Contents', 'MacOS', 'Blender');
    const plist = resolve(app, 'Contents', 'Info.plist');
    const binaryExists = existsSync(binary);
    const fileIdentity = binaryExists ? execRequired(FILE, [binary]) : '';
    const architectures = binaryExists ? execRequired(LIPO, ['-archs', binary]).split(/\s+/) : [];
    const buildChecks = { exitZero: build.exitCode === 0 && build.signal === null, noTimeoutOrResourceKill: !build.timedOut && !build.resourceExceeded, wallWithin: build.elapsedSeconds <= spec.resources.maximumBuildWallSeconds, rssWithin: timing.maximumResidentSetSizeBytes <= spec.resources.maximumBuildPeakRssBytes, appRenamed: renamed && existsSync(app), binaryExists, arm64Only: architectures.join(' ') === 'arm64' && /Mach-O 64-bit executable arm64/.test(fileIdentity), bundleIdExact: plistRaw(plist, 'CFBundleIdentifier') === spec.build.expectedBundleIdentifier, bundleNameExact: plistRaw(plist, 'CFBundleName') === 'Film Studio Engine F0', sourceClean: sourceIdentity(source).clean };
    const buildReceipt = writeJsonExclusive(resolve(evidenceRoot, 'build.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1Build.v0.5', observedAt: new Date().toISOString(), status: Object.values(buildChecks).every(Boolean) ? 'PASS' : 'FAIL', process: build, timing, artifact: binaryExists ? { app, binary, bytes: statSync(binary).size, sha256: sha256File(binary), fileIdentity, architectures, bundleId: plistRaw(plist, 'CFBundleIdentifier') } : null, logs: { stdout: { bytes: statSync(buildStdout).size, sha256: sha256File(buildStdout) }, stderr: { bytes: statSync(buildStderr).size, sha256: sha256File(buildStderr) }, timing: { bytes: statSync(buildTiming).size, sha256: sha256File(buildTiming) } }, checks: buildChecks });
    if (buildReceipt.status !== 'PASS') throw new Error('BUILD_FAILED');

    stage = 'RUNTIME_IDENTITY_CONFIGURATION';
    const actualOfficial = resolve(os.homedir(), 'Library', 'Application Support', 'Blender');
    const officialBefore = contentTreeIdentity(actualOfficial);
    mkdirSync(isolatedHome);
    const isolatedOfficial = resolve(isolatedHome, 'Library', 'Application Support', 'Blender');
    const productRoot = resolve(isolatedHome, 'Library', 'Application Support', spec.build.expectedConfigurationNamespace, '5.2');
    const version = execResult(binary, ['--version'], { timeout: 120_000, env: { HOME: isolatedHome } });
    counters.productStarts += 1;
    commands.push({ stage, operation: 'product version identity process', command: binary, args: ['--version'], cwd: buildRoot, network: 'NONE', externalWrite: false, exitCode: version.exitCode });
    const expression = ['import bpy, json', 'events=[]', 'bpy.app.handlers.render_pre.append(lambda scene: events.append(scene.name))', 'decode=lambda value: value.decode("utf-8") if isinstance(value, bytes) else str(value)', 'paths={kind: bpy.utils.user_resource(kind, create=True) for kind in ("CONFIG","SCRIPTS","DATAFILES","EXTENSIONS")}', 'saved=sorted(bpy.ops.wm.save_userpref())', 'payload={"version":bpy.app.version_string,"buildHash":decode(bpy.app.build_hash),"binaryPath":bpy.app.binary_path,"paths":paths,"save":saved,"renderCalls":len(events)}', 'print("PB1_C1_RUNTIME="+json.dumps(payload,sort_keys=True),flush=True)'].join('; ');
    const runtimeStdout = resolve(evidenceRoot, 'runtime.stdout.log');
    const runtimeStderr = resolve(evidenceRoot, 'runtime.stderr.log');
    const runtime = await runLogged({ command: binary, args: ['--background', '--factory-startup', '--python-expr', expression], cwd: buildRoot, stdoutPath: runtimeStdout, stderrPath: runtimeStderr, timeoutMs: 120_000, env: { HOME: isolatedHome } });
    counters.productStarts += 1;
    commands.push({ stage, operation: 'isolated product identity configuration process', command: binary, args: runtime.command.args, cwd: buildRoot, network: 'NONE', externalWrite: false, startedAt: runtime.startedAt, finishedAt: runtime.finishedAt, exitCode: runtime.exitCode });
    const payload = parseMarker(`${readFileSync(runtimeStdout, 'utf8')}\n${readFileSync(runtimeStderr, 'utf8')}`, 'PB1_C1_RUNTIME=');
    const officialAfter = contentTreeIdentity(actualOfficial);
    const isolatedOfficialAfter = contentTreeIdentity(isolatedOfficial);
    const productAfter = contentTreeIdentity(productRoot);
    const expectedPaths = { CONFIG: resolve(productRoot, 'config'), SCRIPTS: resolve(productRoot, 'scripts'), DATAFILES: resolve(productRoot, 'datafiles'), EXTENSIONS: resolve(productRoot, 'extensions') };
    const versionOutput = `${asText(version.stdout)}\n${asText(version.stderr)}`;
    const runtimeChecks = { twoStarts: counters.productStarts === 2, versionExit: version.exitCode === 0, versionIdentity: versionOutput.includes(`Film Studio Engine F0 ${spec.build.expectedVersion}`) && versionOutput.includes(spec.build.expectedBuildHashPrefix), runtimeExit: runtime.exitCode === 0 && !runtime.timedOut, payloadPresent: payload !== null, payloadIdentity: payload?.version === spec.build.expectedVersion && payload?.buildHash?.startsWith(spec.build.expectedBuildHashPrefix) && payload?.binaryPath === binary, pathsExact: payload && Object.entries(expectedPaths).every(([name, path]) => payload.paths?.[name] === path), preferenceSaved: payload?.save?.includes('FINISHED'), zeroRenders: payload?.renderCalls === 0 && counters.renders === 0, officialUnchanged: officialBefore.state === officialAfter.state && officialBefore.digest === officialAfter.digest, isolatedOfficialAbsent: isolatedOfficialAfter.state === 'ABSENT', productConfigPresent: productAfter.state === 'PRESENT', sourceClean: sourceIdentity(source).clean };
    const runtimeReceipt = writeJsonExclusive(resolve(evidenceRoot, 'runtime-identity.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1Runtime.v0.5', observedAt: new Date().toISOString(), status: Object.values(runtimeChecks).every(Boolean) ? 'PASS' : 'FAIL', productStarts: counters.productStarts, renders: counters.renders, version: { exitCode: version.exitCode, output: versionOutput.trim() }, runtime: { exitCode: runtime.exitCode, elapsedSeconds: runtime.elapsedSeconds, payload, stdoutSha256: sha256File(runtimeStdout), stderrSha256: sha256File(runtimeStderr) }, configuration: { actualOfficial, officialBefore, officialAfter, isolatedOfficial, isolatedOfficialAfter, productRoot, productAfter, expectedPaths }, checks: runtimeChecks });
    if (runtimeReceipt.status !== 'PASS') throw new Error('RUNTIME_IDENTITY_FAILED');

    stage = 'FINAL_ZERO_WRITE_CONFIRMATION';
    const remoteAfter = collectRemote(spec);
    const remoteAfterChecks = remoteChecks(remoteAfter, spec);
    const retainedFinal = treeIdentity(retainedStorage);
    const networkChecks = { remoteExact: Object.values(remoteAfterChecks).every(Boolean), mainUnchanged: remoteAfter.main === preflight.remote.main, retainedStorageUnchanged: canonicalJson(preflight.retainedLfs.wholeTree) === canonicalJson(retainedFinal), noForbiddenCounter: ['publicEngineNetworkClones','renders','engineRemoteWrites','engineRefUpdates','lfsNetworkDownloads','lfsUploads','releases','signing','notarization','dmg','pb2ThroughPb7','modelCalls'].every(name => counters[name] === 0) };
    const networkReceipt = writeJsonExclusive(resolve(evidenceRoot, 'network-and-mutation-log.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1NetworkMutation.v0.5', observedAt: new Date().toISOString(), status: Object.values(networkChecks).every(Boolean) ? 'PASS' : 'FAIL', commands, counters, remoteBefore: preflight.remote, remoteAfter, retainedStorageBefore: preflight.retainedLfs.wholeTree, retainedStorageAfter: retainedFinal, checks: networkChecks, unauthorizedActions: [] });
    if (networkReceipt.status !== 'PASS') throw new Error('ZERO_WRITE_CONFIRMATION_FAILED');

    const names = ['preflight.json','negative-controls.json','lfs-materialization.json','remote-and-history.json','license-and-generated-paths.json','dependency.json','build.json','runtime-identity.json','network-and-mutation-log.json'];
    const bindings = names.map(name => bind(evidenceRoot, name));
    const finalChecks = { receiptsPass: bindings.every(item => item.receiptHashPass && item.status !== 'FAIL'), operationsExact: counters.localEngineClones === 1 && counters.freshObjectsSymlinks === 1 && counters.localLfsMaterializations === 1 && counters.localDependencyClones === 1 && counters.nativeBuilds === 1 && counters.productStarts === 2, forbiddenZero: ['publicEngineNetworkClones','renders','engineRemoteWrites','engineRefUpdates','lfsNetworkDownloads','lfsUploads','releases','signing','notarization','dmg','pb2ThroughPb7','modelCalls'].every(name => counters[name] === 0), sourceExactClean: sourceIdentity(source).head === spec.publicationBaseline.head && sourceIdentity(source).tree === spec.publicationBaseline.tree && sourceIdentity(source).clean, remoteUnchanged: remoteAfter.main === spec.publicationBaseline.head, retainedStorageUnchanged: canonicalJson(preflight.retainedLfs.wholeTree) === canonicalJson(retainedFinal), externalWithin: treeBytes(externalRoot) <= spec.resources.maximumAttempt02ExternalRootBytes, evidenceWithin: treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes };
    const verdict = writeJsonExclusive(resolve(evidenceRoot, 'verdict.json'), { schemaVersion: 'bfs.pb1ValidationOnlyC1Verdict.v0.5', gate: 'PB.1', mode: 'VALIDATION_ONLY_C1', observedAt: new Date().toISOString(), status: Object.values(finalChecks).every(Boolean) ? 'PASS' : 'FAIL', publicationHead: spec.publicationBaseline.head, f0Parent: spec.publicationBaseline.soleParent, dependencyCommit: spec.dependency.commit, bindings, counters, resources: { externalBytes: treeBytes(externalRoot), evidenceBytesBeforeVerdict: treeBytes(evidenceRoot) }, checks: finalChecks, failures: Object.entries(finalChecks).filter(([, pass]) => !pass).map(([name]) => name), claimCeiling: 'PB.1 validation-only proves repository/source identity and one clean same-host arm64 build; it does not authorize PB.2-PB.7 or prove distribution, production readiness, cross-platform support, or autonomous filmmaking.', stopRulePreserved: true });
    if (verdict.status !== 'PASS') throw new Error(`VERDICT_FAILED:${verdict.failures.join(',')}`);
    process.stdout.write(`PB1_C1_VALIDATION_PASS receipt=${verdict.receiptHash} buildSeconds=${build.elapsedSeconds.toFixed(3)}\n`);
  } catch (error) {
    if (evidenceCreated) {
      const failurePath = resolve(evidenceRoot, 'failure.json');
      if (!existsSync(failurePath)) writeJsonExclusive(failurePath, { schemaVersion: 'bfs.pb1ValidationOnlyC1Failure.v0.5', gate: 'PB.1', status: 'FAIL', observedAt: new Date().toISOString(), failedStage: stage, error: String(error.message ?? error), stderr: error.stderr ?? null, counters, externalRootExists: existsSync(externalRoot), externalBytes: treeBytes(externalRoot), stopRulePreserved: true });
      const verdictPath = resolve(evidenceRoot, 'verdict.json');
      if (!existsSync(verdictPath)) writeJsonExclusive(verdictPath, { schemaVersion: 'bfs.pb1ValidationOnlyC1Verdict.v0.5', gate: 'PB.1', status: 'FAIL', observedAt: new Date().toISOString(), failedStage: stage, failureReceiptHash: JSON.parse(readFileSync(failurePath, 'utf8')).receiptHash, counters, stopRulePreserved: true });
    }
    process.stderr.write(`PB1_C1_VALIDATION_FAIL stage=${stage} error=${String(error.message ?? error)}\n`);
    process.exitCode = 1;
  }
}

const spec = JSON.parse(readFileSync(contractPath, 'utf8'));
if (selfTestRequested) selfTest(spec);
else if (executeRequested) await execute(spec);
else {
  const preflight = collectPreflight(spec);
  process.stdout.write(`${JSON.stringify(preflight, null, 2)}\n`);
  if (preflight.status !== 'ACCEPTED') process.exitCode = 2;
}
