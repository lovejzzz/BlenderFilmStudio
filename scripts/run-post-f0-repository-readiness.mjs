#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream, statfsSync } from 'node:fs';
import {
  access,
  mkdir,
  open,
  readFile,
  realpath,
  stat,
} from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import process from 'node:process';

const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const SPEC_RELATIVE = 'specs/ai-native-studio-repository-readiness.v0.2.json';
const PROTOCOL_RELATIVE = 'research/2026-08-30-post-f0-repository-readiness-protocol-v0.1.zh-CN.md';
const CORRECTION_RELATIVE = 'research/2026-08-30-post-f0-repository-readiness-c1-bundle-context.md';
const CHARTER_RELATIVE = 'research/2026-08-30-ai-native-film-studio-post-f0-repository-phase-b-charter-v0.1.zh-CN.md';
const POST_F0_CONTRACT_RELATIVE = 'specs/ai-native-studio-post-f0-phase-b.v0.1.json';
const STATE_RELATIVE = 'handoff/ai-native-studio-current-state.v0.1.json';
const MAX_CLONE_WALL_MS = 30 * 60 * 1000;

let activeEvidenceRoot = null;

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
  const record = structuredClone(value);
  delete record.receiptHash;
  record.receiptHash = sha256Bytes(canonicalJson(record));
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return record;
}

function frozenEnv(extra = {}) {
  return {
    ...process.env,
    PATH: FROZEN_PATH,
    LANG: 'C',
    LC_ALL: 'C',
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_TERMINAL_PROMPT: '0',
    GIT_LFS_SKIP_SMUDGE: '1',
    ...extra,
  };
}

function exec(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: 'utf8',
    env: frozenEnv(),
    stdio: ['ignore', 'pipe', 'pipe'],
    maxBuffer: 256 * 1024 * 1024,
  }).trim();
}

function execBuffer(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: null,
    env: frozenEnv(),
    stdio: ['ignore', 'pipe', 'pipe'],
    maxBuffer: 256 * 1024 * 1024,
  });
}

function execResult(command, args, cwd = undefined) {
  try {
    return {
      exitCode: 0,
      stdout: exec(command, args, cwd),
      stderr: '',
    };
  } catch (error) {
    return {
      exitCode: Number.isInteger(error.status) ? error.status : 1,
      stdout: Buffer.isBuffer(error.stdout) ? error.stdout.toString('utf8').trim() : String(error.stdout ?? '').trim(),
      stderr: Buffer.isBuffer(error.stderr) ? error.stderr.toString('utf8').trim() : String(error.stderr ?? '').trim(),
    };
  }
}

function git(root, args) {
  return exec('/usr/bin/git', ['-C', root, ...args]);
}

function gitBuffer(root, args) {
  return execBuffer('/usr/bin/git', ['-C', root, ...args]);
}

function freeBytes(path) {
  const stats = statfsSync(path, { bigint: true });
  return stats.bavail * stats.bsize;
}

function treeBytes(path) {
  return Number(exec('/usr/bin/du', ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function parseRemoteRoster(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^(\S+)\s+(\S+)\s+\((fetch|push)\)$/);
    if (!match) throw new Error(`Unexpected git remote line: ${line}`);
    return { name: match[1], url: match[2], direction: match[3] };
  });
}

function parseSubmodules(text) {
  const values = new Map();
  for (const line of text.split(/\r?\n/).filter(Boolean)) {
    const [key, value] = line.split(/\s+/, 2);
    const match = key.match(/^submodule\.(.+)\.(path|url)$/);
    if (!match) continue;
    const current = values.get(match[1]) ?? { name: match[1] };
    current[match[2]] = value;
    values.set(match[1], current);
  }
  return [...values.values()].sort((left, right) => left.name.localeCompare(right.name));
}

function parseLargestBlob(text) {
  let largest = { path: null, bytes: 0, oid: null };
  for (const line of text.split(/\r?\n/).filter(Boolean)) {
    const match = line.match(/^\d+\s+blob\s+([0-9a-f]+)\s+(\d+)\t(.+)$/);
    if (!match) continue;
    const bytes = Number(match[2]);
    if (bytes > largest.bytes) largest = { path: match[3], bytes, oid: match[1] };
  }
  return largest;
}

function secretMatchesForText(text, path) {
  const patterns = [
    ['PRIVATE_KEY_HEADER', /-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----/g],
    ['GITHUB_TOKEN', /\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b/g],
    ['AWS_ACCESS_KEY', /\bAKIA[0-9A-Z]{16}\b/g],
    ['CREDENTIALED_URL', /https?:\/\/[^\s/:@]+:[^\s/@]+@[^\s]+/g],
    ['SECRET_ASSIGNMENT', /\b(?:password|secret|token|api[_-]?key)\b\s*[:=]\s*["'][^"']{8,}["']/gi],
  ];
  const lines = text.split(/\r?\n/);
  const matches = [];
  for (let index = 0; index < lines.length; index += 1) {
    for (const [pattern, regex] of patterns) {
      regex.lastIndex = 0;
      if (regex.test(lines[index])) matches.push({ pattern, path, line: index + 1 });
    }
  }
  return matches;
}

function destinationFailures({
  destinationUrl,
  expectedDestination,
  allowedRoot,
  destinationExists,
}) {
  const failures = [];
  let parsed = null;
  try {
    parsed = new URL(destinationUrl);
  } catch {
    failures.push('DESTINATION_URL_INVALID');
  }
  if (parsed) {
    if (parsed.protocol !== 'file:') failures.push('DESTINATION_NOT_FILE_PROTOCOL');
    if (parsed.username || parsed.password) failures.push('DESTINATION_CONTAINS_CREDENTIALS');
    if (parsed.protocol === 'file:') {
      const destinationPath = resolve(fileURLToPath(parsed));
      const expectedPath = resolve(expectedDestination);
      const rootPath = resolve(allowedRoot);
      if (destinationPath !== expectedPath) failures.push('DESTINATION_PATH_MISMATCH');
      if (relative(rootPath, destinationPath).startsWith('..')) failures.push('DESTINATION_OUTSIDE_REHEARSAL_ROOT');
    }
  }
  if (destinationExists) failures.push('DESTINATION_NOT_FRESH');
  return failures;
}

function localPushAdmission(fixture) {
  const failures = [];
  if (fixture.fullHistorySourceShallow) failures.push('FULL_HISTORY_SOURCE_IS_SHALLOW');
  if (fixture.observedHead !== fixture.expectedHead) failures.push('SOURCE_HEAD_MISMATCH');
  failures.push(...destinationFailures(fixture));
  if (!fixture.copyingPresent) failures.push('COPYING_MISSING');
  if (fixture.secretFindings > 0) failures.push('FORK_SECRET_FINDINGS_PRESENT');
  if (fixture.maximumOrdinaryBlobBytes >= fixture.maximumAllowedOrdinaryBlobBytesExclusive) {
    failures.push('ORDINARY_BLOB_AT_OR_ABOVE_100_MIB');
  }
  if (fixture.requestedExternalMutation) failures.push('EXTERNAL_MUTATION_UNAUTHORIZED');
  return { accepted: failures.length === 0, failures };
}

async function queryCandidateRepository(candidate) {
  const ghPath = '/opt/homebrew/bin/gh';
  if (!await exists(ghPath)) {
    return { status: 'BLOCKED', exists: null, notFound: false, failure: 'GH_CLI_MISSING' };
  }
  const result = execResult(ghPath, ['api', `repos/${candidate}`, '--silent']);
  const notFound = result.exitCode !== 0 && /HTTP 404/.test(result.stderr);
  return {
    status: result.exitCode === 0 || notFound ? 'PASS' : 'BLOCKED',
    exists: result.exitCode === 0,
    notFound,
    failure: result.exitCode === 0 || notFound ? null : 'GITHUB_METADATA_QUERY_FAILED',
  };
}

async function collectPreflight({ repositoryRoot, spec, queryCandidate = true }) {
  const sourceRoot = await realpath(spec.paths.sourceRoot);
  const externalRoot = spec.paths.externalRehearsalRoot;
  const evidenceRoot = resolve(repositoryRoot, spec.paths.evidenceRoot);
  const researchHead = git(repositoryRoot, ['rev-parse', 'HEAD']);
  const sourceHead = git(sourceRoot, ['rev-parse', 'HEAD']);
  const sourceTree = git(sourceRoot, ['rev-parse', 'HEAD^{tree}']);
  const sourceParents = git(sourceRoot, ['show', '-s', '--format=%P', 'HEAD']).split(/\s+/);
  const sourceTreeListingSha256 = sha256Bytes(gitBuffer(sourceRoot, ['ls-tree', '-r', '-z', 'HEAD']));
  const sourceStatus = git(sourceRoot, ['status', '--porcelain=v1']);
  const sourceShallow = git(sourceRoot, ['rev-parse', '--is-shallow-repository']) === 'true';
  const currentCheckoutReachableCommitCount = Number(git(sourceRoot, ['rev-list', '--count', 'HEAD']));
  const dependencyLine = git(sourceRoot, ['submodule', 'status', '--', 'lib/macos_arm64']);
  const dependencyCommit = dependencyLine.replace(/^[ +-U]/, '').split(/\s+/)[0];
  const researchClean = git(repositoryRoot, ['status', '--porcelain=v1']) === '';
  const free = freeBytes(dirname(externalRoot));
  const candidate = queryCandidate
    ? await queryCandidateRepository(spec.network.candidateRepository)
    : { status: 'NOT_QUERIED', exists: null, notFound: null, failure: null };
  const charterPath = resolve(repositoryRoot, CHARTER_RELATIVE);
  const postF0ContractPath = resolve(repositoryRoot, POST_F0_CONTRACT_RELATIVE);
  const protocolPath = resolve(repositoryRoot, PROTOCOL_RELATIVE);
  const correctionPath = resolve(repositoryRoot, CORRECTION_RELATIVE);
  const specPath = resolve(repositoryRoot, SPEC_RELATIVE);
  const statePath = resolve(repositoryRoot, STATE_RELATIVE);
  const failures = [];
  if (!researchClean) failures.push('RESEARCH_WORKTREE_NOT_CLEAN');
  if (sourceStatus !== '') failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (sourceHead !== spec.bindings.sourceHead) failures.push('SOURCE_HEAD_MISMATCH');
  if (sourceTree !== spec.bindings.sourceTree) failures.push('SOURCE_TREE_MISMATCH');
  if (sourceTreeListingSha256 !== spec.bindings.sourceTreeListingSha256) failures.push('SOURCE_TREE_LISTING_MISMATCH');
  if (sourceParents.join(' ') !== `${spec.bindings.forkParent} ${spec.bindings.upstreamTarget}`) failures.push('SOURCE_PARENTS_MISMATCH');
  if (dependencyCommit !== spec.bindings.dependencyCommit) failures.push('DEPENDENCY_COMMIT_MISMATCH');
  if (!sourceShallow) failures.push('CURRENT_CHECKOUT_EXPECTED_SHALLOW');
  if (currentCheckoutReachableCommitCount !== spec.expectedInventory.currentCheckoutReachableCommitCount) failures.push('CURRENT_COMMIT_COUNT_MISMATCH');
  if (await sha256File(charterPath) !== spec.bindings.postF0CharterSha256) failures.push('POST_F0_CHARTER_HASH_MISMATCH');
  if (await sha256File(postF0ContractPath) !== spec.bindings.postF0ContractSha256) failures.push('POST_F0_CONTRACT_HASH_MISMATCH');
  if (free < BigInt(spec.acceptance.minimumFreeBytes)) failures.push('FREE_DISK_BELOW_110_GIB');
  if (await exists(externalRoot)) failures.push('EXTERNAL_REHEARSAL_ROOT_ALREADY_EXISTS');
  if (await exists(evidenceRoot)) failures.push('EVIDENCE_ROOT_ALREADY_EXISTS');
  if (candidate.status === 'BLOCKED') failures.push(candidate.failure);
  if (candidate.exists) failures.push('CANDIDATE_REPOSITORY_ALREADY_EXISTS');
  const authValues = [
    spec.network.candidateOwnerIsAuthorized,
    spec.network.candidateVisibilityIsAuthorized,
    spec.network.externalRepositoryCreateAuthorized,
    spec.network.externalGitPushAuthorized,
    spec.network.lfsUploadAuthorized,
  ];
  if (authValues.some(Boolean)) failures.push('EXTERNAL_AUTHORIZATION_SENTINEL_NOT_FALSE');
  let retainedInput = null;
  if (spec.correction?.reuseRetainedFullMirrorLocally) {
    const retainedFailurePath = resolve(repositoryRoot, spec.correction.retainedAttempt01EvidenceRoot, 'failure.json');
    const retainedInventoryPath = resolve(repositoryRoot, spec.correction.retainedAttempt01EvidenceRoot, 'source-inventory.json');
    const retainedMirrorExists = await exists(spec.paths.retainedFullMirror);
    const retainedBundleExists = await exists(spec.paths.retainedBundle);
    const retainedFailureExists = await exists(retainedFailurePath);
    const retainedInventoryExists = await exists(retainedInventoryPath);
    if (!retainedMirrorExists) failures.push('RETAINED_FULL_MIRROR_MISSING');
    if (!retainedBundleExists) failures.push('RETAINED_BUNDLE_MISSING');
    if (!retainedFailureExists) failures.push('RETAINED_FAILURE_EVIDENCE_MISSING');
    if (!retainedInventoryExists) failures.push('RETAINED_INVENTORY_EVIDENCE_MISSING');
    if (retainedMirrorExists && git(spec.paths.retainedFullMirror, ['rev-parse', '--is-shallow-repository']) !== 'false') failures.push('RETAINED_FULL_MIRROR_IS_SHALLOW');
    if (retainedMirrorExists && git(spec.paths.retainedFullMirror, ['remote', 'get-url', 'origin']) !== spec.network.readOnlyFullHistorySource) failures.push('RETAINED_FULL_MIRROR_ORIGIN_MISMATCH');
    if (retainedBundleExists && await sha256File(spec.paths.retainedBundle) !== spec.correction.retainedBundleSha256) failures.push('RETAINED_BUNDLE_HASH_MISMATCH');
    if (retainedFailureExists && await sha256File(retainedFailurePath) !== spec.correction.retainedFailureFileSha256) failures.push('RETAINED_FAILURE_FILE_HASH_MISMATCH');
    const retainedFailure = retainedFailureExists ? JSON.parse(await readFile(retainedFailurePath, 'utf8')) : null;
    const retainedInventory = retainedInventoryExists ? JSON.parse(await readFile(retainedInventoryPath, 'utf8')) : null;
    if (retainedFailure?.receiptHash !== spec.correction.retainedFailureReceiptHash) failures.push('RETAINED_FAILURE_RECEIPT_HASH_MISMATCH');
    if (retainedInventory?.receiptHash !== spec.correction.retainedSourceInventoryReceiptHash) failures.push('RETAINED_INVENTORY_RECEIPT_HASH_MISMATCH');
    retainedInput = {
      mirror: spec.paths.retainedFullMirror,
      mirrorExists: retainedMirrorExists,
      mirrorShallow: retainedMirrorExists ? git(spec.paths.retainedFullMirror, ['rev-parse', '--is-shallow-repository']) === 'true' : null,
      mirrorOrigin: retainedMirrorExists ? git(spec.paths.retainedFullMirror, ['remote', 'get-url', 'origin']) : null,
      mirrorShowRefSha256: retainedMirrorExists ? sha256Bytes(gitBuffer(spec.paths.retainedFullMirror, ['show-ref'])) : null,
      bundle: spec.paths.retainedBundle,
      bundleExists: retainedBundleExists,
      bundleSha256: retainedBundleExists ? await sha256File(spec.paths.retainedBundle) : null,
      failureFileSha256: retainedFailureExists ? await sha256File(retainedFailurePath) : null,
      failureReceiptHash: retainedFailure?.receiptHash ?? null,
      inventoryReceiptHash: retainedInventory?.receiptHash ?? null,
    };
  }
  const parentCommits = [spec.bindings.parentCharterCommit, spec.bindings.parentStateCommit];
  for (const commit of parentCommits) {
    const result = execResult('/usr/bin/git', ['-C', repositoryRoot, 'merge-base', '--is-ancestor', commit, researchHead]);
    if (result.exitCode !== 0) failures.push(`PARENT_COMMIT_NOT_ANCESTOR:${commit}`);
  }
  return {
    schemaVersion: 'bfs.repositoryReadinessAdmission.v0.1',
    observedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    research: {
      root: repositoryRoot,
      head: researchHead,
      clean: researchClean,
      protocolPath,
      protocolSha256: await sha256File(protocolPath),
      correctionPath,
      correctionSha256: await sha256File(correctionPath),
      specPath,
      specSha256: await sha256File(specPath),
      statePath,
      stateSha256: await sha256File(statePath),
    },
    source: {
      root: sourceRoot,
      head: sourceHead,
      tree: sourceTree,
      treeListingSha256: sourceTreeListingSha256,
      parents: sourceParents,
      clean: sourceStatus === '',
      shallow: sourceShallow,
      reachableCommitCount: currentCheckoutReachableCommitCount,
      dependencyLine,
      dependencyCommit,
    },
    resources: {
      requiredFreeBytes: String(spec.acceptance.minimumFreeBytes),
      observedFreeBytes: free.toString(),
      maximumProjectedWriteBytes: String(spec.acceptance.maximumProjectedWriteBytes),
    },
    candidate,
    retainedInput,
    authorization: {
      ownerAuthorized: spec.network.candidateOwnerIsAuthorized,
      visibilityAuthorized: spec.network.candidateVisibilityIsAuthorized,
      createAuthorized: spec.network.externalRepositoryCreateAuthorized,
      pushAuthorized: spec.network.externalGitPushAuthorized,
      lfsUploadAuthorized: spec.network.lfsUploadAuthorized,
      authorizedExternalMutations: 0,
    },
    roots: {
      evidenceRoot,
      evidenceRootAbsent: !await exists(evidenceRoot),
      externalRoot,
      externalRootAbsent: !await exists(externalRoot),
    },
    failures,
  };
}

async function runLogged({ command, args, cwd, stdoutPath, stderrPath, monitoredRoot, maximumBytes }) {
  const stdoutStream = createWriteStream(stdoutPath, { flags: 'wx', mode: 0o600 });
  const stderrStream = createWriteStream(stderrPath, { flags: 'wx', mode: 0o600 });
  const startedAt = new Date().toISOString();
  const started = process.hrtime.bigint();
  const child = spawn(command, args, {
    cwd,
    detached: true,
    env: frozenEnv(),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let spawnError = null;
  let timedOut = false;
  let resourceExceeded = false;
  let maximumObservedBytes = 0;
  let forceTimer = null;
  child.on('error', error => { spawnError = error; });
  child.stdout.on('data', chunk => stdoutStream.write(chunk));
  child.stderr.on('data', chunk => stderrStream.write(chunk));
  const interval = setInterval(() => {
    if (!monitoredRoot) return;
    try {
      const observed = treeBytes(monitoredRoot);
      maximumObservedBytes = Math.max(maximumObservedBytes, observed);
      if (observed > maximumBytes && !resourceExceeded) {
        resourceExceeded = true;
        try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
      }
    } catch {
      // The clone target can be absent during initial spawn.
    }
  }, 3000);
  const timeout = setTimeout(() => {
    timedOut = true;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
    forceTimer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
    }, 5000);
  }, MAX_CLONE_WALL_MS);
  const terminal = await new Promise(resolveClose => {
    child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal }));
  });
  clearInterval(interval);
  clearTimeout(timeout);
  if (forceTimer) clearTimeout(forceTimer);
  stdoutStream.end();
  stderrStream.end();
  await Promise.all([finished(stdoutStream), finished(stderrStream)]);
  if (await exists(monitoredRoot)) maximumObservedBytes = Math.max(maximumObservedBytes, treeBytes(monitoredRoot));
  return {
    startedAt,
    endedAt: new Date().toISOString(),
    elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    exitCode: spawnError ? 1 : terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    resourceExceeded,
    maximumObservedBytes,
    spawnError: spawnError?.message ?? null,
  };
}

async function collectSourceInventory(sourceRoot, spec) {
  const lfs = JSON.parse(git(sourceRoot, ['lfs', 'ls-files', '--json']));
  const lfsBytes = lfs.files.reduce((sum, file) => sum + file.size, 0);
  const largestLfs = [...lfs.files].sort((left, right) => right.size - left.size)[0];
  const changedPaths = git(sourceRoot, ['diff', '--name-only', spec.bindings.upstreamTarget, spec.bindings.sourceHead]).split(/\r?\n/).filter(Boolean);
  const forkCommits = git(sourceRoot, ['rev-list', '--reverse', `${spec.bindings.upstreamTarget}..${spec.bindings.sourceHead}`]).split(/\r?\n/).filter(Boolean);
  const diffShort = git(sourceRoot, ['diff', '--shortstat', spec.bindings.upstreamTarget, spec.bindings.sourceHead]);
  const diffMatch = diffShort.match(/(\d+) files? changed, (\d+) insertions?\(\+\), (\d+) deletions?\(-\)/);
  if (!diffMatch) throw new Error(`Unable to parse diff shortstat: ${diffShort}`);
  const changedLfs = [];
  const secretFindings = [];
  for (const path of changedPaths) {
    const attr = git(sourceRoot, ['check-attr', 'filter', '--', path]);
    if (attr.endsWith(': lfs')) {
      const entry = lfs.files.find(file => file.name === path);
      changedLfs.push({ path, oid: entry?.oid ?? null, size: entry?.size ?? null, downloaded: entry?.downloaded ?? false });
    }
    const objectExists = execResult('/usr/bin/git', ['-C', sourceRoot, 'cat-file', '-e', `${spec.bindings.sourceHead}:${path}`]).exitCode === 0;
    if (!objectExists) continue;
    const content = gitBuffer(sourceRoot, ['show', `${spec.bindings.sourceHead}:${path}`]);
    if (content.includes(0)) continue;
    secretFindings.push(...secretMatchesForText(content.toString('utf8'), path));
  }
  const allPaths = git(sourceRoot, ['ls-tree', '-r', '--name-only', spec.bindings.sourceHead]).split(/\r?\n/).filter(Boolean);
  const noticePaths = allPaths.filter(path => /(^|\/)(?:copying|license|notice)(?:[._-]|$)/i.test(path)).sort();
  const submodules = parseSubmodules(git(sourceRoot, ['config', '-f', '.gitmodules', '--get-regexp', '^submodule\\..*\\.(path|url)$']));
  const remotes = parseRemoteRoster(git(sourceRoot, ['remote', '-v']));
  const largestOrdinaryBlob = parseLargestBlob(git(sourceRoot, ['ls-tree', '-rl', spec.bindings.sourceHead]));
  return {
    head: spec.bindings.sourceHead,
    tree: git(sourceRoot, ['rev-parse', `${spec.bindings.sourceHead}^{tree}`]),
    treeListingSha256: sha256Bytes(gitBuffer(sourceRoot, ['ls-tree', '-r', '-z', spec.bindings.sourceHead])),
    shallow: git(sourceRoot, ['rev-parse', '--is-shallow-repository']) === 'true',
    reachableCommitCount: Number(git(sourceRoot, ['rev-list', '--count', spec.bindings.sourceHead])),
    refs: Number(git(sourceRoot, ['for-each-ref', '--format=%(refname)']).split(/\r?\n/).filter(Boolean).length),
    remotes,
    submodules,
    sourceGitBytes: treeBytes(resolve(sourceRoot, '.git')),
    sourceGitObjectBytes: treeBytes(resolve(sourceRoot, '.git', 'objects')),
    sourceGitLfsBytes: treeBytes(resolve(sourceRoot, '.git', 'lfs')),
    sourceGitModuleBytes: treeBytes(resolve(sourceRoot, '.git', 'modules')),
    lfs: {
      count: lfs.files.length,
      bytes: lfsBytes,
      downloadedCount: lfs.files.filter(file => file.downloaded).length,
      largest: { path: largestLfs.name, oid: largestLfs.oid, bytes: largestLfs.size },
      changed: changedLfs,
    },
    fork: {
      commits: forkCommits,
      commitCount: forkCommits.length,
      changedPaths,
      changedPathCount: Number(diffMatch[1]),
      additions: Number(diffMatch[2]),
      deletions: Number(diffMatch[3]),
      changedLines: Number(diffMatch[2]) + Number(diffMatch[3]),
    },
    licenses: {
      copyingSha256: await sha256File(resolve(sourceRoot, 'COPYING')),
      assetsLicenseSha256: await sha256File(resolve(sourceRoot, 'assets', 'LICENSE')),
      noticePathCount: noticePaths.length,
      noticePathListSha256: sha256Bytes(`${noticePaths.join('\n')}\n`),
      paths: noticePaths,
    },
    largestOrdinaryBlob,
    secretScan: {
      scope: 'fork-owned changed textual paths only',
      scannedPathCount: changedPaths.length,
      findings: secretFindings,
      findingCount: secretFindings.length,
    },
  };
}

function runNegativeControls({ spec, localDestinationUrl }) {
  const base = {
    fullHistorySourceShallow: false,
    observedHead: spec.bindings.sourceHead,
    expectedHead: spec.bindings.sourceHead,
    destinationUrl: localDestinationUrl,
    expectedDestination: spec.paths.localDestination,
    allowedRoot: spec.paths.externalRehearsalRoot,
    destinationExists: false,
    copyingPresent: true,
    secretFindings: 0,
    maximumOrdinaryBlobBytes: spec.expectedInventory.headLargestOrdinaryBlobBytes,
    maximumAllowedOrdinaryBlobBytesExclusive: spec.acceptance.maximumOrdinaryBlobBytesExclusive,
    requestedExternalMutation: false,
  };
  const cases = [
    ['SHALLOW_SOURCE_REJECTED', { fullHistorySourceShallow: true }, 'FULL_HISTORY_SOURCE_IS_SHALLOW'],
    ['SOURCE_HEAD_MISMATCH_REJECTED', { observedHead: '0'.repeat(40) }, 'SOURCE_HEAD_MISMATCH'],
    ['NON_FILE_OR_CREDENTIALED_DESTINATION_REJECTED', { destinationUrl: 'https://user:synthetic-password@example.invalid/repository.git' }, 'DESTINATION_NOT_FILE_PROTOCOL'],
    ['NONEMPTY_DESTINATION_REJECTED', { destinationExists: true }, 'DESTINATION_NOT_FRESH'],
    ['MISSING_COPYING_REJECTED', { copyingPresent: false }, 'COPYING_MISSING'],
    ['SYNTHETIC_SECRET_REJECTED', { secretFindings: secretMatchesForText('-----BEGIN OPENSSH PRIVATE KEY-----\nghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890', 'synthetic.txt').length }, 'FORK_SECRET_FINDINGS_PRESENT'],
    ['ORDINARY_BLOB_100_MIB_REJECTED', { maximumOrdinaryBlobBytes: spec.acceptance.maximumOrdinaryBlobBytesExclusive }, 'ORDINARY_BLOB_AT_OR_ABOVE_100_MIB'],
    ['EXTERNAL_AUTHORIZATION_SENTINEL_REJECTED', { requestedExternalMutation: true }, 'EXTERNAL_MUTATION_UNAUTHORIZED'],
  ];
  return cases.map(([id, mutation, expectedFailure]) => {
    const result = localPushAdmission({ ...base, ...mutation });
    return {
      id,
      expectedFailure,
      accepted: result.accepted,
      failures: result.failures,
      passed: !result.accepted && result.failures.includes(expectedFailure),
    };
  });
}

async function evidenceBinding(path) {
  const record = JSON.parse(await readFile(path, 'utf8'));
  return {
    file: path.split('/').at(-1),
    fileSha256: await sha256File(path),
    receiptHash: record.receiptHash,
  };
}

async function formalRun({ repositoryRoot, spec, preflight }) {
  const evidenceRoot = resolve(repositoryRoot, spec.paths.evidenceRoot);
  const externalRoot = spec.paths.externalRehearsalRoot;
  const sourceRoot = spec.paths.sourceRoot;
  await mkdir(dirname(evidenceRoot), { recursive: true });
  await mkdir(evidenceRoot, { recursive: false });
  activeEvidenceRoot = evidenceRoot;
  const admissionPath = resolve(evidenceRoot, 'admission.json');
  const admission = await writeJsonExclusive(admissionPath, preflight);
  if (admission.status !== 'ACCEPTED') {
    process.stdout.write(`REPOSITORY_READINESS_BLOCKED ${admission.failures.join(',')}\n`);
    process.exitCode = 2;
    return;
  }
  await mkdir(externalRoot, { recursive: false });
  const commandLog = [
    {
      stage: 'RR.1',
      operation: 'authenticated repository metadata query',
      command: ['/opt/homebrew/bin/gh', 'api', `repos/${spec.network.candidateRepository}`, '--silent'],
      network: 'READ_ONLY',
      externalMutation: false,
    },
  ];
  const inventoryBefore = await collectSourceInventory(sourceRoot, spec);
  const inventoryBeforePath = resolve(evidenceRoot, 'source-inventory.json');
  const sourceChecks = {
    currentCheckoutCorrectlyClassifiedShallow: inventoryBefore.shallow === true,
    sourceHeadExact: inventoryBefore.head === spec.bindings.sourceHead,
    sourceTreeExact: inventoryBefore.tree === spec.bindings.sourceTree,
    sourceTreeListingExact: inventoryBefore.treeListingSha256 === spec.bindings.sourceTreeListingSha256,
    reachableCommitCountExact: inventoryBefore.reachableCommitCount === spec.expectedInventory.currentCheckoutReachableCommitCount,
    lfsCountExact: inventoryBefore.lfs.count === spec.expectedInventory.headLfsPathCount,
    lfsBytesExact: inventoryBefore.lfs.bytes === spec.expectedInventory.headLfsBytes,
    lfsObjectsDownloaded: inventoryBefore.lfs.downloadedCount === inventoryBefore.lfs.count,
    largestLfsExact: inventoryBefore.lfs.largest.bytes === spec.expectedInventory.headLargestLfsObjectBytes,
    largestOrdinaryBlobExact: inventoryBefore.largestOrdinaryBlob.bytes === spec.expectedInventory.headLargestOrdinaryBlobBytes,
    ordinaryBlobBelow100MiB: inventoryBefore.largestOrdinaryBlob.bytes < spec.acceptance.maximumOrdinaryBlobBytesExclusive,
    forkCommitCountExact: inventoryBefore.fork.commitCount === spec.expectedInventory.forkOnlyCommitCount,
    forkPathCountExact: inventoryBefore.fork.changedPathCount === spec.expectedInventory.forkChangedPathCount,
    forkAdditionsExact: inventoryBefore.fork.additions === spec.expectedInventory.forkAdditions,
    forkDeletionsExact: inventoryBefore.fork.deletions === spec.expectedInventory.forkDeletions,
    forkLinesWithinCeiling: inventoryBefore.fork.changedLines <= spec.acceptance.maximumForkNonGeneratedChangedLines,
    copyingExact: inventoryBefore.licenses.copyingSha256 === spec.bindings.copyingSha256,
    assetsLicenseExact: inventoryBefore.licenses.assetsLicenseSha256 === spec.bindings.assetsLicenseSha256,
    submodulesOfficialHttps: inventoryBefore.submodules.every(item => item.url?.startsWith('https://projects.blender.org/blender/')),
    sourceRemotesReadOnlyOfficial: inventoryBefore.remotes.every(item => item.url === 'https://projects.blender.org/blender/blender.git'),
    forkSecretFindingsZero: inventoryBefore.secretScan.findingCount === 0,
  };
  await writeJsonExclusive(inventoryBeforePath, {
    schemaVersion: 'bfs.repositoryReadinessSourceInventory.v0.1',
    observedAt: new Date().toISOString(),
    source: inventoryBefore,
    checks: sourceChecks,
    status: Object.values(sourceChecks).every(Boolean) ? 'PASS' : 'FAIL',
  });
  if (!Object.values(sourceChecks).every(Boolean)) throw new Error('SOURCE_INVENTORY_CHECK_FAILED');

  const mirrorRoot = spec.paths.fullMirror;
  const cloneStdout = resolve(evidenceRoot, 'mirror-clone.stdout.log');
  const cloneStderr = resolve(evidenceRoot, 'mirror-clone.stderr.log');
  const reuseRetainedMirror = spec.correction?.reuseRetainedFullMirrorLocally === true;
  const mirrorCloneSource = reuseRetainedMirror ? spec.paths.retainedFullMirror : spec.network.readOnlyFullHistorySource;
  const mirrorCloneArgs = reuseRetainedMirror
    ? ['clone', '--mirror', '--local', mirrorCloneSource, mirrorRoot]
    : ['clone', '--mirror', mirrorCloneSource, mirrorRoot];
  commandLog.push({
    stage: 'RR.4',
    operation: reuseRetainedMirror ? 'retained full mirror local clone' : 'full Git mirror acquisition',
    command: ['/usr/bin/git', ...mirrorCloneArgs],
    network: reuseRetainedMirror ? 'NONE' : 'READ_ONLY',
    externalMutation: false,
  });
  const clone = await runLogged({
    command: '/usr/bin/git',
    args: mirrorCloneArgs,
    cwd: externalRoot,
    stdoutPath: cloneStdout,
    stderrPath: cloneStderr,
    monitoredRoot: externalRoot,
    maximumBytes: spec.acceptance.maximumExternalRehearsalBytes,
  });
  if (clone.exitCode !== 0 || clone.timedOut || clone.resourceExceeded) {
    throw new Error(`FULL_MIRROR_CLONE_FAILED exit=${clone.exitCode} timeout=${clone.timedOut} resource=${clone.resourceExceeded}`);
  }
  if (reuseRetainedMirror) {
    commandLog.push({
      stage: 'RR.4',
      operation: 'restore official fetch origin on local work mirror',
      command: ['/usr/bin/git', '-C', mirrorRoot, 'remote', 'set-url', 'origin', spec.network.readOnlyFullHistorySource],
      network: 'NONE',
      externalMutation: false,
    });
    exec('/usr/bin/git', ['-C', mirrorRoot, 'remote', 'set-url', 'origin', spec.network.readOnlyFullHistorySource]);
  }
  const mirrorShallow = git(mirrorRoot, ['rev-parse', '--is-shallow-repository']) === 'true';
  const targetPresent = execResult('/usr/bin/git', ['-C', mirrorRoot, 'cat-file', '-e', `${spec.bindings.upstreamTarget}^{commit}`]).exitCode === 0;
  const baselinePresent = execResult('/usr/bin/git', ['-C', mirrorRoot, 'cat-file', '-e', 'fbe6228777e7d9afefcd61a413844e790ae75db7^{commit}']).exitCode === 0;
  if (mirrorShallow || !targetPresent || !baselinePresent) throw new Error('FULL_MIRROR_IDENTITY_FAILED');

  const bundlePath = resolve(externalRoot, 'f0-source.bundle');
  commandLog.push({
    stage: 'RR.5',
    operation: 'local F0 commit bundle',
    command: ['/usr/bin/git', '-C', sourceRoot, 'bundle', 'create', bundlePath, 'HEAD', `^${spec.bindings.upstreamTarget}`],
    network: 'NONE',
    externalMutation: false,
  });
  exec('/usr/bin/git', ['-C', sourceRoot, 'bundle', 'create', bundlePath, 'HEAD', `^${spec.bindings.upstreamTarget}`]);
  const bundleVerifyResult = execResult('/usr/bin/git', ['bundle', 'verify', bundlePath]);
  const bundleVerify = `${bundleVerifyResult.stdout}\n${bundleVerifyResult.stderr}`.trim();
  if (bundleVerifyResult.exitCode !== 0) throw new Error('F0_BUNDLE_VERIFY_FAILED');
  const candidateRef = 'refs/heads/film-studio-f0-candidate';
  commandLog.push({
    stage: 'RR.5',
    operation: 'local bundle fetch into full mirror',
    command: ['/usr/bin/git', '-C', mirrorRoot, 'fetch', bundlePath, `HEAD:${candidateRef}`],
    network: 'NONE',
    externalMutation: false,
  });
  exec('/usr/bin/git', ['-C', mirrorRoot, 'fetch', bundlePath, `HEAD:${candidateRef}`]);
  const candidateHead = git(mirrorRoot, ['rev-parse', candidateRef]);
  const candidateTree = git(mirrorRoot, ['rev-parse', `${candidateRef}^{tree}`]);
  const candidateTreeListingSha256 = sha256Bytes(gitBuffer(mirrorRoot, ['ls-tree', '-r', '-z', candidateRef]));
  if (candidateHead !== spec.bindings.sourceHead || candidateTree !== spec.bindings.sourceTree || candidateTreeListingSha256 !== spec.bindings.sourceTreeListingSha256) {
    throw new Error('CANDIDATE_GRAFT_IDENTITY_FAILED');
  }

  const destinationRoot = spec.paths.localDestination;
  const destinationUrl = pathToFileURL(destinationRoot).href;
  const positiveAdmission = localPushAdmission({
    fullHistorySourceShallow: mirrorShallow,
    observedHead: candidateHead,
    expectedHead: spec.bindings.sourceHead,
    destinationUrl,
    expectedDestination: destinationRoot,
    allowedRoot: externalRoot,
    destinationExists: await exists(destinationRoot),
    copyingPresent: inventoryBefore.licenses.copyingSha256 === spec.bindings.copyingSha256,
    secretFindings: inventoryBefore.secretScan.findingCount,
    maximumOrdinaryBlobBytes: inventoryBefore.largestOrdinaryBlob.bytes,
    maximumAllowedOrdinaryBlobBytesExclusive: spec.acceptance.maximumOrdinaryBlobBytesExclusive,
    requestedExternalMutation: false,
  });
  if (!positiveAdmission.accepted) throw new Error(`LOCAL_PUSH_ADMISSION_FAILED:${positiveAdmission.failures.join(',')}`);
  commandLog.push({
    stage: 'RR.5',
    operation: 'initialize local bare destination',
    command: ['/usr/bin/git', 'init', '--bare', '--initial-branch=main', destinationRoot],
    network: 'NONE',
    externalMutation: false,
  });
  exec('/usr/bin/git', ['init', '--bare', '--initial-branch=main', destinationRoot]);
  commandLog.push({
    stage: 'RR.5',
    operation: 'push exact candidate to local file destination',
    command: ['/usr/bin/git', '-C', mirrorRoot, 'push', '--porcelain', destinationUrl, `${candidateRef}:refs/heads/main`],
    network: 'NONE_FILE_ONLY',
    externalMutation: false,
  });
  const pushOutput = exec('/usr/bin/git', ['-C', mirrorRoot, 'push', '--porcelain', destinationUrl, `${candidateRef}:refs/heads/main`]);
  const fsckOutput = git(destinationRoot, ['fsck', '--full', '--no-dangling']);
  const destinationHead = git(destinationRoot, ['rev-parse', 'refs/heads/main']);
  const destinationTree = git(destinationRoot, ['rev-parse', 'refs/heads/main^{tree}']);
  const destinationTreeListingSha256 = sha256Bytes(gitBuffer(destinationRoot, ['ls-tree', '-r', '-z', 'refs/heads/main']));
  const destinationShallow = git(destinationRoot, ['rev-parse', '--is-shallow-repository']) === 'true';
  const destinationCommitCount = Number(git(destinationRoot, ['rev-list', '--count', 'refs/heads/main']));
  const destinationForkCommitCount = Number(git(destinationRoot, ['rev-list', '--count', `${spec.bindings.upstreamTarget}..refs/heads/main`]));
  const destinationMergeBase = git(destinationRoot, ['merge-base', spec.bindings.upstreamTarget, 'refs/heads/main']);
  const destinationParents = git(destinationRoot, ['show', '-s', '--format=%P', 'refs/heads/main']).split(/\s+/);
  const rehearsalChecks = {
    mirrorCloneExitZero: clone.exitCode === 0,
    mirrorWithinResourceCeiling: treeBytes(externalRoot) <= spec.acceptance.maximumExternalRehearsalBytes,
    mirrorNotShallow: !mirrorShallow,
    mirrorContainsUpstreamTarget: targetPresent,
    mirrorContainsPinnedBaseline: baselinePresent,
    bundleVerified: bundleVerifyResult.exitCode === 0,
    candidateHeadExact: candidateHead === spec.bindings.sourceHead,
    candidateTreeExact: candidateTree === spec.bindings.sourceTree,
    candidateTreeListingExact: candidateTreeListingSha256 === spec.bindings.sourceTreeListingSha256,
    localPushAdmissionAccepted: positiveAdmission.accepted,
    destinationNotShallow: !destinationShallow,
    destinationHeadExact: destinationHead === spec.bindings.sourceHead,
    destinationTreeExact: destinationTree === spec.bindings.sourceTree,
    destinationTreeListingExact: destinationTreeListingSha256 === spec.bindings.sourceTreeListingSha256,
    destinationParentsExact: destinationParents.join(' ') === `${spec.bindings.forkParent} ${spec.bindings.upstreamTarget}`,
    destinationMergeBaseExact: destinationMergeBase === spec.bindings.upstreamTarget,
    destinationForkCommitCountExact: destinationForkCommitCount === spec.expectedInventory.forkOnlyCommitCount,
    destinationHistoryExceedsShallowCheckout: destinationCommitCount > spec.expectedInventory.currentCheckoutReachableCommitCount,
    destinationFsckClean: fsckOutput === '',
  };
  const rehearsalPath = resolve(evidenceRoot, 'local-rehearsal.json');
  await writeJsonExclusive(rehearsalPath, {
    schemaVersion: 'bfs.repositoryReadinessLocalRehearsal.v0.1',
    observedAt: new Date().toISOString(),
    clone: {
      ...clone,
      mode: reuseRetainedMirror ? 'RETAINED_FULL_MIRROR_LOCAL_CLONE' : 'READ_ONLY_NETWORK_FULL_MIRROR_CLONE',
      source: mirrorCloneSource,
      stdoutSha256: await sha256File(cloneStdout),
      stderrSha256: await sha256File(cloneStderr),
    },
    mirror: {
      path: mirrorRoot,
      origin: git(mirrorRoot, ['remote', 'get-url', 'origin']),
      shallow: mirrorShallow,
      refs: Number(git(mirrorRoot, ['for-each-ref', '--format=%(refname)']).split(/\r?\n/).filter(Boolean).length),
      tags: Number(git(mirrorRoot, ['tag', '--list']).split(/\r?\n/).filter(Boolean).length),
      objectStats: git(mirrorRoot, ['count-objects', '-vH']),
      bytes: treeBytes(mirrorRoot),
      targetPresent,
      baselinePresent,
    },
    bundle: {
      path: bundlePath,
      bytes: (await stat(bundlePath)).size,
      sha256: await sha256File(bundlePath),
      verification: bundleVerify,
    },
    candidate: { ref: candidateRef, head: candidateHead, tree: candidateTree, treeListingSha256: candidateTreeListingSha256 },
    destination: {
      path: destinationRoot,
      url: destinationUrl,
      head: destinationHead,
      tree: destinationTree,
      treeListingSha256: destinationTreeListingSha256,
      shallow: destinationShallow,
      reachableCommitCount: destinationCommitCount,
      forkCommitCount: destinationForkCommitCount,
      mergeBase: destinationMergeBase,
      parents: destinationParents,
      bytes: treeBytes(destinationRoot),
      fsckOutput,
      pushOutput,
    },
    positiveAdmission,
    checks: rehearsalChecks,
    status: Object.values(rehearsalChecks).every(Boolean) ? 'PASS' : 'FAIL',
  });
  if (!Object.values(rehearsalChecks).every(Boolean)) throw new Error('LOCAL_REHEARSAL_CHECK_FAILED');

  const negativeControls = runNegativeControls({ spec, localDestinationUrl: destinationUrl });
  const negativePath = resolve(evidenceRoot, 'negative-controls.json');
  await writeJsonExclusive(negativePath, {
    schemaVersion: 'bfs.repositoryReadinessNegativeControls.v0.1',
    observedAt: new Date().toISOString(),
    controls: negativeControls,
    passed: negativeControls.filter(control => control.passed).length,
    expected: spec.acceptance.requiredNegativeControls.length,
    status: negativeControls.length === spec.acceptance.requiredNegativeControls.length && negativeControls.every(control => control.passed) ? 'PASS' : 'FAIL',
  });
  if (!negativeControls.every(control => control.passed)) throw new Error('NEGATIVE_CONTROL_FAILED');

  const networkPath = resolve(evidenceRoot, 'network-and-mutation-log.json');
  await writeJsonExclusive(networkPath, {
    schemaVersion: 'bfs.repositoryReadinessNetworkMutationLog.v0.1',
    observedAt: new Date().toISOString(),
    commands: commandLog,
    counters: {
      authenticatedMetadataQueries: 1,
      readOnlyFullMirrorClones: reuseRetainedMirror ? 0 : 1,
      retainedFullMirrorLocalClones: reuseRetainedMirror ? 1 : 0,
      externalRepositoryCreates: 0,
      externalGitPushes: 0,
      localFilePushes: 1,
      lfsUploads: 0,
      phaseBMutations: 0,
      dmgDistributions: 0,
      credentialMaterialReadsOrEmissions: 0,
      blenderStarts: 0,
      renders: 0,
      modelCalls: 0,
    },
    status: 'PASS',
  });

  const boundFiles = await Promise.all([
    admissionPath,
    inventoryBeforePath,
    rehearsalPath,
    negativePath,
    networkPath,
  ].map(evidenceBinding));
  const finalChecks = {
    admissionAccepted: admission.status === 'ACCEPTED',
    sourceInventoryPass: Object.values(sourceChecks).every(Boolean),
    localRehearsalPass: Object.values(rehearsalChecks).every(Boolean),
    allNegativeControlsPass: negativeControls.every(control => control.passed),
    candidateRepositoryAbsent: preflight.candidate.notFound === true,
    externalRepositoryCreatesZero: spec.acceptance.externalRepositoryCreates === 0,
    externalGitPushesZero: spec.acceptance.externalGitPushes === 0,
    lfsUploadsZero: spec.acceptance.lfsUploads === 0,
    phaseBMutationsZero: spec.acceptance.phaseBMutations === 0,
    externalRehearsalWithinCeiling: treeBytes(externalRoot) <= spec.acceptance.maximumExternalRehearsalBytes,
    evidenceWithinCeilingBeforeVerdict: treeBytes(evidenceRoot) <= spec.acceptance.maximumResearchEvidenceBytes,
  };
  const verdictPath = resolve(evidenceRoot, 'verdict.json');
  const verdict = await writeJsonExclusive(verdictPath, {
    schemaVersion: 'bfs.repositoryReadinessVerdict.v0.1',
    protocol: 'AI-NATIVE-STUDIO-REPOSITORY-READINESS-v0.2-C1',
    observedAt: new Date().toISOString(),
    status: Object.values(finalChecks).every(Boolean) ? 'PASS' : 'FAIL',
    claim: 'NO_EXTERNAL_WRITE_REPOSITORY_READINESS_REHEARSAL_SUPPORTED',
    researchToolFreezeCommit: preflight.research.head,
    sourceHead: spec.bindings.sourceHead,
    sourceTree: spec.bindings.sourceTree,
    evidenceBindings: boundFiles,
    checks: finalChecks,
    topologyVerdicts: {
      PUBLIC_GITHUB_FORK: 'READY_FOR_EXPLICIT_AUTHORIZATION',
      PRIVATE_STANDALONE_MIRROR: 'BLOCKED_PENDING_OWNER_VISIBILITY_LFS_COST_AND_FULL_LFS_TRANSFER_AUTHORIZATION',
    },
    authorizationStillFalse: {
      owner: false,
      visibility: false,
      createRepositoryOrFork: false,
      firstExternalPush: false,
      lfsUpload: false,
      phaseBMutation: false,
      signingOrNotarization: false,
      dmgDistribution: false,
    },
    exactNextAuthorization: `Authorize owner=lovejzzz, visibility=public, creation of a GitHub fork named film-studio-engine from blender/blender, and the first push of exact F0 head ${spec.bindings.sourceHead} as main; keep signing/notarization, unsigned-DMG distribution, and Phase B mutation unauthorized unless separately granted.`,
    claimCeiling: spec.claimCeiling,
  });
  if (verdict.status !== 'PASS') throw new Error('FORMAL_VERDICT_FAILED');
  process.stdout.write(`REPOSITORY_READINESS_PASS receiptHash=${verdict.receiptHash}\n`);
}

async function main() {
  const repositoryRoot = exec('/usr/bin/git', ['rev-parse', '--show-toplevel'], process.cwd());
  const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_RELATIVE), 'utf8'));
  if (process.argv.includes('--self-test')) {
    const destinationUrl = pathToFileURL(spec.paths.localDestination).href;
    const controls = runNegativeControls({ spec, localDestinationUrl: destinationUrl });
    const positive = localPushAdmission({
      fullHistorySourceShallow: false,
      observedHead: spec.bindings.sourceHead,
      expectedHead: spec.bindings.sourceHead,
      destinationUrl,
      expectedDestination: spec.paths.localDestination,
      allowedRoot: spec.paths.externalRehearsalRoot,
      destinationExists: false,
      copyingPresent: true,
      secretFindings: 0,
      maximumOrdinaryBlobBytes: spec.expectedInventory.headLargestOrdinaryBlobBytes,
      maximumAllowedOrdinaryBlobBytesExclusive: spec.acceptance.maximumOrdinaryBlobBytesExclusive,
      requestedExternalMutation: false,
    });
    const passed = positive.accepted && controls.length === spec.acceptance.requiredNegativeControls.length && controls.every(control => control.passed);
    process.stdout.write(`${JSON.stringify({ status: passed ? 'PASS' : 'FAIL', positive, controls }, null, 2)}\n`);
    process.exitCode = passed ? 0 : 1;
    return;
  }
  const preflight = await collectPreflight({ repositoryRoot, spec, queryCandidate: true });
  if (process.argv.includes('--preflight-only')) {
    process.stdout.write(`${JSON.stringify(preflight, null, 2)}\n`);
    process.exitCode = preflight.status === 'ACCEPTED' ? 0 : 2;
    return;
  }
  await formalRun({ repositoryRoot, spec, preflight });
}

main().catch(async error => {
  if (activeEvidenceRoot && await exists(activeEvidenceRoot)) {
    const failurePath = resolve(activeEvidenceRoot, 'failure.json');
    if (!await exists(failurePath)) {
      await writeJsonExclusive(failurePath, {
        schemaVersion: 'bfs.repositoryReadinessFailure.v0.1',
        observedAt: new Date().toISOString(),
        status: 'FAIL',
        error: error.message,
        externalRepositoryCreates: 0,
        externalGitPushes: 0,
        lfsUploads: 0,
        phaseBMutations: 0,
      });
    }
  }
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
