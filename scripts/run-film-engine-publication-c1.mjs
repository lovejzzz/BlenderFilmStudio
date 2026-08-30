#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  accessSync,
  constants,
  mkdirSync,
  openSync,
  closeSync,
  readFileSync,
  statfsSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const SCRIPT_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(SCRIPT_PATH), '..');
const SPEC_RELATIVE = 'specs/ai-native-studio-repository-publication-c1-execution.v0.4.json';
const DOCUMENT_RELATIVE = 'research/2026-08-30-film-engine-publication-c1-execution-authorization-v0.4.zh-CN.md';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const DOCUMENT_PATH = resolve(REPOSITORY_ROOT, DOCUMENT_RELATIVE);
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

function exists(path) {
  try {
    accessSync(path, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function frozenEnv(extra = {}) {
  return {
    ...process.env,
    PATH: FROZEN_PATH,
    LANG: 'C',
    LC_ALL: 'C',
    GH_PROMPT_DISABLED: '1',
    GIT_TERMINAL_PROMPT: '0',
    GIT_LFS_SKIP_SMUDGE: '1',
    ...extra,
  };
}

function execResult(command, args, options = {}) {
  try {
    const stdout = execFileSync(command, args, {
      cwd: options.cwd,
      encoding: options.encoding ?? 'utf8',
      env: frozenEnv(options.env),
      input: options.input,
      stdio: ['pipe', 'pipe', 'pipe'],
      maxBuffer: 512 * 1024 * 1024,
    });
    return { exitCode: 0, stdout, stderr: '' };
  } catch (error) {
    return {
      exitCode: Number.isInteger(error.status) ? error.status : 1,
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

function ghJson(args) {
  return JSON.parse(execRequired(GH, args));
}

function ghText(args) {
  return execRequired(GH, args);
}

function freeBytes(path) {
  const stats = statfsSync(path, { bigint: true });
  return stats.bavail * stats.bsize;
}

function receiptHash(value) {
  const copy = structuredClone(value);
  delete copy.receiptHash;
  return sha256Bytes(canonicalJson(copy));
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

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ls-remote line: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function readReceipt(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function receiptHashPass(record) {
  return record.receiptHash === receiptHash(record);
}

function executableFile(path) {
  try {
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function expectedAttributeLines(spec) {
  return spec.publicationCommit.attributeOverrides;
}

function makeGitAttributes(baseBytes, spec) {
  const base = baseBytes.toString('utf8');
  for (const line of expectedAttributeLines(spec)) {
    if (base.split(/\r?\n/).includes(line)) throw new Error(`Attribute override already exists: ${line}`);
  }
  const separator = base.endsWith('\n') ? '' : '\n';
  return Buffer.from(`${base}${separator}${expectedAttributeLines(spec).join('\n')}\n`, 'utf8');
}

function checkAttributes(root, paths) {
  const observations = [];
  for (const path of paths) {
    const output = git(root, ['check-attr', 'filter', 'diff', 'merge', 'text', '--', path]);
    const values = Object.fromEntries(output.split(/\r?\n/).map(line => {
      const match = line.match(/^(.+): (filter|diff|merge|text): (.+)$/);
      if (!match) throw new Error(`Unexpected check-attr output: ${line}`);
      return [match[2], match[3]];
    }));
    observations.push({ path, values, pass: ['filter', 'diff', 'merge', 'text'].every(name => values[name] === 'unset') });
  }
  return observations;
}

function verifyMaterializedFiles(root, ordinaryBlobs) {
  return ordinaryBlobs.map(item => {
    const path = resolve(root, item.path);
    const observedBytes = statSync(path).size;
    const observedSha256 = sha256File(path);
    const prefix = readFileSync(path).subarray(0, 42).toString('utf8');
    return {
      path: item.path,
      observedBytes,
      expectedBytes: item.bytes,
      observedSha256,
      expectedSha256: item.contentSha256,
      lfsPointerPrefix: prefix.startsWith('version https://git-lfs.github.com/spec/'),
      pass: observedBytes === item.bytes && observedSha256 === item.contentSha256 && !prefix.startsWith('version https://git-lfs.github.com/spec/'),
    };
  });
}

function collectRemote(spec) {
  const metadata = ghJson(['api', `repos/${spec.repository.fullName}`]);
  const branches = ghJson(['api', `repos/${spec.repository.fullName}/branches?per_page=100`]);
  const pulls = ghJson(['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]);
  const releases = ghJson(['api', `repos/${spec.repository.fullName}/releases?per_page=100`]);
  const heads = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--tags', spec.repository.url]));
  const main = heads.find(item => item.ref === 'refs/heads/main')?.oid ?? null;
  return {
    metadata: {
      id: metadata.id,
      fullName: metadata.full_name,
      fork: metadata.fork,
      parent: metadata.parent?.full_name,
      visibility: metadata.visibility,
      private: metadata.private,
      defaultBranch: metadata.default_branch,
      htmlUrl: metadata.html_url,
    },
    branchNames: branches.map(item => item.name).sort(),
    headRefs: heads,
    tagRefs: tags,
    mainOid: main,
    pullRequestCount: pulls.length,
    releaseCount: releases.length,
  };
}

function collectPreflight(spec) {
  const sourceRoot = spec.paths.sourceCheckout;
  const fullRoot = spec.paths.fullHistorySource;
  const evidenceRoot = resolve(REPOSITORY_ROOT, spec.evidence.root);
  const remote = collectRemote(spec);
  const fsck = execResult(GIT, ['-C', fullRoot, 'fsck', '--full', '--strict']);
  const baseAttributes = readFileSync(resolve(sourceRoot, '.gitattributes'));
  const sourceAssets = spec.publicationCommit.ordinaryBlobs.map(item => {
    const path = resolve(sourceRoot, item.path);
    return {
      path: item.path,
      bytes: statSync(path).size,
      sha256: sha256File(path),
      expectedBytes: item.bytes,
      expectedSha256: item.contentSha256,
    };
  });
  const failure = readReceipt(resolve(REPOSITORY_ROOT, spec.evidence.retainedFailureRoot, 'failure.json'));
  const failureAudit = readReceipt(resolve(REPOSITORY_ROOT, spec.evidence.retainedFailureRoot, 'audit-failure.json'));
  const fullHead = git(fullRoot, ['rev-parse', 'refs/heads/main']);
  const observed = {
    observedAt: new Date().toISOString(),
    researchHead: git(REPOSITORY_ROOT, ['rev-parse', 'HEAD']),
    researchUpstreamHead: git(REPOSITORY_ROOT, ['rev-parse', '@{upstream}']),
    researchClean: git(REPOSITORY_ROOT, ['status', '--porcelain=v1']) === '',
    activeGithubLogin: ghText(['api', 'user', '--jq', '.login']),
    specification: {
      path: SPEC_RELATIVE,
      sha256: sha256File(SPEC_PATH),
      authorizationDocument: DOCUMENT_RELATIVE,
      authorizationDocumentSha256: sha256File(DOCUMENT_PATH),
      runner: 'scripts/run-film-engine-publication-c1.mjs',
      runnerSha256: sha256File(SCRIPT_PATH),
    },
    authorizationGranted: spec.authorization.granted,
    source: {
      root: sourceRoot,
      clean: git(sourceRoot, ['status', '--porcelain=v1']) === '',
      head: git(sourceRoot, ['rev-parse', 'HEAD']),
      tree: git(sourceRoot, ['rev-parse', 'HEAD^{tree}']),
      parents: git(sourceRoot, ['show', '-s', '--format=%P', 'HEAD']).split(/\s+/),
      baseGitAttributesBlob: git(sourceRoot, ['rev-parse', 'HEAD:.gitattributes']),
      baseGitAttributesSha256: sha256Bytes(baseAttributes),
      assets: sourceAssets,
    },
    fullHistory: {
      root: fullRoot,
      bare: git(fullRoot, ['rev-parse', '--is-bare-repository']) === 'true',
      shallow: git(fullRoot, ['rev-parse', '--is-shallow-repository']) === 'true',
      head: fullHead,
      tree: git(fullRoot, ['rev-parse', `${fullHead}^{tree}`]),
      reachableCommits: Number(git(fullRoot, ['rev-list', '--count', fullHead])),
      refs: git(fullRoot, ['for-each-ref', '--format=%(refname)', 'refs/heads', 'refs/tags']).split(/\r?\n/).filter(Boolean),
      prePushHook: executableFile(resolve(fullRoot, 'hooks', 'pre-push')),
      fsckPass: fsck.exitCode === 0,
      fsckStderr: asText(fsck.stderr),
    },
    remote,
    retainedFailure: {
      receiptHash: failure.receiptHash,
      receiptHashPass: receiptHashPass(failure),
      auditReceiptHash: failureAudit.receiptHash,
      auditReceiptHashPass: receiptHashPass(failureAudit),
    },
    roots: {
      evidenceRoot,
      evidenceRootAbsent: !exists(evidenceRoot),
      externalRoot: spec.paths.publicationExternalRoot,
      externalRootAbsent: !exists(spec.paths.publicationExternalRoot),
    },
    disk: {
      freeBytes: freeBytes(REPOSITORY_ROOT).toString(),
      minimumFreeBytes: String(spec.acceptance.minimumFreeBytes),
    },
  };

  const failures = [];
  if (!observed.authorizationGranted) failures.push('OWNER_AUTHORIZATION_NOT_GRANTED');
  if (observed.activeGithubLogin !== spec.repository.owner) failures.push('ACTIVE_GITHUB_LOGIN_MISMATCH');
  if (!observed.researchClean) failures.push('RESEARCH_WORKTREE_NOT_CLEAN');
  if (observed.researchHead !== observed.researchUpstreamHead) failures.push('RESEARCH_HEAD_NOT_PUSHED');
  if (!observed.source.clean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (observed.source.head !== spec.source.publicationParent) failures.push('SOURCE_HEAD_MISMATCH');
  if (observed.source.tree !== spec.source.publicationParentTree) failures.push('SOURCE_TREE_MISMATCH');
  if (observed.source.parents.join(' ') !== spec.source.publicationParentParents.join(' ')) failures.push('SOURCE_PARENTS_MISMATCH');
  if (observed.source.baseGitAttributesBlob !== spec.publicationCommit.baseGitAttributes.gitBlobOidSha1) failures.push('BASE_GITATTRIBUTES_BLOB_MISMATCH');
  if (observed.source.baseGitAttributesSha256 !== spec.publicationCommit.baseGitAttributes.contentSha256) failures.push('BASE_GITATTRIBUTES_CONTENT_MISMATCH');
  if (observed.source.assets.some(item => item.bytes !== item.expectedBytes || item.sha256 !== item.expectedSha256)) failures.push('SOURCE_ASSET_CONTENT_MISMATCH');
  if (!observed.fullHistory.bare || observed.fullHistory.shallow) failures.push('FULL_HISTORY_SOURCE_INVALID');
  if (observed.fullHistory.head !== spec.source.publicationParent) failures.push('FULL_HISTORY_HEAD_MISMATCH');
  if (observed.fullHistory.tree !== spec.source.publicationParentTree) failures.push('FULL_HISTORY_TREE_MISMATCH');
  if (observed.fullHistory.reachableCommits !== spec.source.expectedFullHistoryReachableCommits) failures.push('FULL_HISTORY_COMMIT_COUNT_MISMATCH');
  if (observed.fullHistory.refs.join('\n') !== 'refs/heads/main') failures.push('FULL_HISTORY_REFS_MISMATCH');
  if (observed.fullHistory.prePushHook || !observed.fullHistory.fsckPass) failures.push('FULL_HISTORY_INTEGRITY_MISMATCH');
  if (observed.remote.metadata.id !== spec.repository.repositoryId || observed.remote.metadata.fullName !== spec.repository.fullName) failures.push('REMOTE_REPOSITORY_IDENTITY_MISMATCH');
  if (!observed.remote.metadata.fork || observed.remote.metadata.parent !== spec.repository.forkParent || observed.remote.metadata.visibility !== 'public' || observed.remote.metadata.private) failures.push('REMOTE_FORK_TOPOLOGY_MISMATCH');
  if (observed.remote.metadata.defaultBranch !== spec.repository.defaultBranch) failures.push('REMOTE_DEFAULT_BRANCH_MISMATCH');
  if (observed.remote.mainOid !== spec.repository.generatedMainOid) failures.push('REMOTE_MAIN_LEASE_MISMATCH');
  if (observed.remote.branchNames.join('\n') !== 'main' || observed.remote.headRefs.length !== 1) failures.push('REMOTE_BRANCH_SET_MISMATCH');
  if (observed.remote.tagRefs.length !== 0) failures.push('REMOTE_TAGS_PRESENT');
  if (observed.remote.pullRequestCount !== 0 || observed.remote.releaseCount !== 0) failures.push('REMOTE_PR_OR_RELEASE_PRESENT');
  if (!observed.retainedFailure.receiptHashPass || observed.retainedFailure.receiptHash !== spec.evidence.retainedFailureReceiptHash) failures.push('RETAINED_FAILURE_RECEIPT_MISMATCH');
  if (!observed.retainedFailure.auditReceiptHashPass || observed.retainedFailure.auditReceiptHash !== spec.evidence.retainedFailureAuditReceiptHash) failures.push('RETAINED_FAILURE_AUDIT_MISMATCH');
  if (!observed.roots.evidenceRootAbsent || !observed.roots.externalRootAbsent) failures.push('FRESH_ROOT_REQUIRED');
  if (BigInt(observed.disk.freeBytes) < BigInt(spec.acceptance.minimumFreeBytes)) failures.push('FREE_DISK_BELOW_110_GIB');
  return { ...observed, status: failures.length === 0 ? 'ACCEPTED' : 'REJECTED', failures };
}

function runSelfTest(spec) {
  const checks = [];
  const add = (id, pass) => checks.push({ id, pass: Boolean(pass) });
  add('AUTHORIZATION_GRANTED', spec.authorization.granted === true);
  add('PUBLIC_FORK_FIXED', spec.repository.fullName === 'lovejzzz/film-engine' && spec.repository.forkParent === 'blender/blender');
  add('PARENT_FIXED', spec.publicationCommit.onlyParent === spec.source.publicationParent);
  add('THREE_PATH_ALLOWLIST', spec.publicationCommit.changedPaths.length === 3 && new Set(spec.publicationCommit.changedPaths).size === 3);
  add('TWO_ORDINARY_BLOBS', spec.publicationCommit.ordinaryBlobs.length === 2);
  add('CONTENT_LIMITS', spec.publicationCommit.ordinaryBlobs.every(item => item.bytes <= spec.acceptance.maximumOrdinaryBlobBytes));
  add('EXACT_LEASE', spec.remoteUpdate.exactLeaseArgument === `--force-with-lease=refs/heads/main:${spec.repository.generatedMainOid}`);
  add('SINGLE_PUSH', spec.remoteUpdate.maximumPushAttempts === 1);
  add('NO_LFS_UPLOAD', spec.remoteUpdate.lfsUploadsAllowed === 0);
  add('FORBIDDEN_SURFACE', ['release creation', 'Phase B mutation'].every(value => spec.forbidden.includes(value)));
  const sample = { schemaVersion: 'test', status: 'PASS' };
  sample.receiptHash = receiptHash(sample);
  add('RECEIPT_HASH', receiptHashPass(sample));
  const fakeBase = Buffer.from('*.png filter=lfs diff=lfs merge=lfs -text\n*.icns filter=lfs diff=lfs merge=lfs -text\n');
  const derived = makeGitAttributes(fakeBase, spec).toString('utf8');
  add('ATTRIBUTE_OVERRIDES_EXACT', expectedAttributeLines(spec).every(line => derived.endsWith(`${expectedAttributeLines(spec).join('\n')}\n`) && derived.includes(line)));
  const failed = checks.filter(item => !item.pass);
  const result = { schemaVersion: 'bfs.repositoryPublicationC1SelfTest.v0.4', status: failed.length === 0 ? 'PASS' : 'FAIL', checksPassed: checks.length - failed.length, checksTotal: checks.length, checks, failures: failed.map(item => item.id) };
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (failed.length) process.exitCode = 1;
}

function trackedExec(commandLog, command, args, options = {}) {
  const startedAt = new Date().toISOString();
  const result = execResult(command, args, options);
  commandLog.push({
    startedAt,
    finishedAt: new Date().toISOString(),
    command,
    args,
    cwd: options.cwd ?? null,
    exitCode: result.exitCode,
    stdoutSha256: sha256Bytes(Buffer.isBuffer(result.stdout) ? result.stdout : String(result.stdout ?? '')),
    stderr: asText(result.stderr),
  });
  return result;
}

function trackedRequired(commandLog, command, args, options = {}) {
  const result = trackedExec(commandLog, command, args, options);
  if (result.exitCode !== 0) {
    const error = new Error(`Command failed (${result.exitCode}): ${command} ${args.join(' ')}`);
    error.command = [command, ...args];
    error.stdout = asText(result.stdout);
    error.stderr = asText(result.stderr);
    throw error;
  }
  return options.encoding === null ? result.stdout : asText(result.stdout);
}

function trackedGit(commandLog, root, args, options = {}) {
  return trackedRequired(commandLog, GIT, ['-C', root, ...args], options);
}

function execute(spec) {
  const evidenceRoot = resolve(REPOSITORY_ROOT, spec.evidence.root);
  const externalRoot = spec.paths.publicationExternalRoot;
  const commandLog = [];
  const counters = {
    repositoryCreates: 0,
    lfsUploads: 0,
    gitPushAttempts: 0,
    gitRefUpdates: 0,
    otherRefUpdates: 0,
    tagUpdates: 0,
    releases: 0,
    phaseBMutations: 0,
    deletions: 0,
    recreations: 0,
    renames: 0,
  };
  let failedStage = 'PREFLIGHT';
  let evidenceCreated = false;
  try {
    const preflight = collectPreflight(spec);
    mkdirSync(evidenceRoot);
    evidenceCreated = true;
    writeJsonExclusive(resolve(evidenceRoot, 'preflight.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1Preflight.v0.4',
      ...preflight,
      externalMutationCounts: counters,
    });
    if (preflight.status !== 'ACCEPTED') throw new Error(`C1 preflight rejected: ${preflight.failures.join(', ')}`);

    failedStage = 'CONSTRUCTION';
    mkdirSync(externalRoot);
    const candidateBare = resolve(externalRoot, 'candidate.git');
    const emptyHooks = resolve(externalRoot, 'empty-hooks');
    const localClone = resolve(externalRoot, 'fresh-local-no-smudge');
    const remoteClone = resolve(externalRoot, 'fresh-remote-no-smudge');
    const indexPath = resolve(externalRoot, 'candidate.index');
    mkdirSync(emptyHooks);
    trackedRequired(commandLog, GIT, ['clone', '--bare', '--no-hardlinks', spec.paths.fullHistorySource, candidateBare]);
    trackedGit(commandLog, candidateBare, ['config', 'core.hooksPath', emptyHooks]);
    if (executableFile(resolve(candidateBare, 'hooks', 'pre-push'))) throw new Error('Fresh candidate has executable pre-push hook');
    const baseAttributes = readFileSync(resolve(spec.paths.sourceCheckout, '.gitattributes'));
    const publicationAttributes = makeGitAttributes(baseAttributes, spec);
    const attributeBlob = trackedRequired(commandLog, GIT, ['-C', candidateBare, 'hash-object', '-w', '--stdin'], { input: publicationAttributes });
    const ordinaryOids = [];
    for (const item of spec.publicationCommit.ordinaryBlobs) {
      const oid = trackedGit(commandLog, candidateBare, ['hash-object', '-w', '--no-filters', resolve(spec.paths.sourceCheckout, item.path)]);
      ordinaryOids.push({ path: item.path, oid });
      if (oid !== item.gitBlobOidSha1) throw new Error(`Ordinary blob OID mismatch for ${item.path}`);
    }
    const indexEnv = { GIT_INDEX_FILE: indexPath };
    trackedGit(commandLog, candidateBare, ['read-tree', spec.source.publicationParent], { env: indexEnv });
    trackedGit(commandLog, candidateBare, ['update-index', '--add', '--cacheinfo', `100644,${attributeBlob},.gitattributes`], { env: indexEnv });
    for (const item of ordinaryOids) {
      trackedGit(commandLog, candidateBare, ['update-index', '--add', '--cacheinfo', `100644,${item.oid},${item.path}`], { env: indexEnv });
    }
    const candidateTree = trackedGit(commandLog, candidateBare, ['write-tree'], { env: indexEnv });
    const identityEnv = {
      GIT_AUTHOR_NAME: spec.source.authorName,
      GIT_AUTHOR_EMAIL: spec.source.authorEmail,
      GIT_COMMITTER_NAME: spec.source.authorName,
      GIT_COMMITTER_EMAIL: spec.source.authorEmail,
    };
    const candidateCommit = trackedGit(commandLog, candidateBare, ['commit-tree', candidateTree, '-p', spec.source.publicationParent], { input: `${spec.source.commitMessage}\n`, env: identityEnv });
    trackedGit(commandLog, candidateBare, ['update-ref', 'refs/heads/c1-candidate', candidateCommit]);
    const candidateParents = trackedGit(commandLog, candidateBare, ['show', '-s', '--format=%P', candidateCommit]).split(/\s+/);
    const changedPaths = trackedGit(commandLog, candidateBare, ['diff-tree', '--no-commit-id', '--name-only', '-r', spec.source.publicationParent, candidateCommit]).split(/\r?\n/).filter(Boolean).sort();
    const expectedPaths = [...spec.publicationCommit.changedPaths].sort();
    const treeOids = Object.fromEntries(spec.publicationCommit.changedPaths.map(path => {
      const line = trackedGit(commandLog, candidateBare, ['ls-tree', candidateCommit, '--', path]);
      const match = line.match(/^100644 blob ([0-9a-f]{40})\t/);
      if (!match) throw new Error(`Unexpected tree entry for ${path}: ${line}`);
      return [path, match[1]];
    }));
    const constructionPass = candidateParents.length === 1
      && candidateParents[0] === spec.source.publicationParent
      && changedPaths.join('\n') === expectedPaths.join('\n')
      && treeOids['.gitattributes'] === attributeBlob
      && spec.publicationCommit.ordinaryBlobs.every(item => treeOids[item.path] === item.gitBlobOidSha1);
    const construction = writeJsonExclusive(resolve(evidenceRoot, 'construction.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1Construction.v0.4',
      observedAt: new Date().toISOString(),
      status: constructionPass ? 'PASS' : 'FAIL',
      candidateCommit,
      candidateTree,
      parentOids: candidateParents,
      changedPaths,
      expectedChangedPaths: expectedPaths,
      treeOids,
      attributeBlob,
      attributeContentSha256: sha256Bytes(publicationAttributes),
      ordinaryOids,
      externalMutationCounts: counters,
    });
    if (construction.status !== 'PASS') throw new Error('Candidate construction verification failed');

    failedStage = 'LOCAL_NO_SMUDGE_VERIFICATION';
    trackedRequired(commandLog, GIT, ['clone', '--no-local', '--single-branch', '--branch', 'c1-candidate', candidateBare, localClone]);
    const localFiles = verifyMaterializedFiles(localClone, spec.publicationCommit.ordinaryBlobs);
    const localAttributes = checkAttributes(localClone, spec.publicationCommit.ordinaryBlobs.map(item => item.path));
    const localHead = trackedGit(commandLog, localClone, ['rev-parse', 'HEAD']);
    const localStatus = trackedGit(commandLog, localClone, ['status', '--porcelain=v1']);
    const localPass = localHead === candidateCommit && localStatus === '' && localFiles.every(item => item.pass) && localAttributes.every(item => item.pass);
    const localVerification = writeJsonExclusive(resolve(evidenceRoot, 'local-verification.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1LocalVerification.v0.4',
      observedAt: new Date().toISOString(),
      status: localPass ? 'PASS' : 'FAIL',
      cloneEnvironment: { GIT_LFS_SKIP_SMUDGE: '1' },
      head: localHead,
      clean: localStatus === '',
      files: localFiles,
      attributes: localAttributes,
      externalMutationCounts: counters,
    });
    if (localVerification.status !== 'PASS') throw new Error('Fresh local no-smudge clone verification failed');

    failedStage = 'LEASE_RECHECK';
    const beforePush = collectRemote(spec);
    const leasePass = beforePush.mainOid === spec.repository.generatedMainOid
      && beforePush.headRefs.length === 1
      && beforePush.tagRefs.length === 0
      && beforePush.pullRequestCount === 0
      && beforePush.releaseCount === 0;
    writeJsonExclusive(resolve(evidenceRoot, 'lease-recheck.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1LeaseRecheck.v0.4',
      observedAt: new Date().toISOString(),
      status: leasePass ? 'PASS' : 'FAIL',
      expectedMainOid: spec.repository.generatedMainOid,
      remote: beforePush,
      exactLeaseArgument: spec.remoteUpdate.exactLeaseArgument,
      externalMutationCounts: counters,
    });
    if (!leasePass) throw new Error('Remote lease or topology changed before push');

    failedStage = 'MAIN_UPDATE';
    const pushArgs = [
      '-c', `core.hooksPath=${emptyHooks}`,
      '-C', candidateBare,
      'push', '--porcelain',
      spec.remoteUpdate.exactLeaseArgument,
      spec.repository.url,
      `${candidateCommit}:refs/heads/main`,
    ];
    counters.gitPushAttempts += 1;
    const pushResult = trackedExec(commandLog, GIT, pushArgs);
    if (pushResult.exitCode === 0) counters.gitRefUpdates += 1;
    writeJsonExclusive(resolve(evidenceRoot, 'main-update.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1MainUpdate.v0.4',
      observedAt: new Date().toISOString(),
      status: pushResult.exitCode === 0 ? 'PASS' : 'FAIL',
      command: [GIT, ...pushArgs],
      sourceCommit: candidateCommit,
      destinationRef: 'refs/heads/main',
      leaseOid: spec.repository.generatedMainOid,
      exitCode: pushResult.exitCode,
      stdout: asText(pushResult.stdout),
      stderr: asText(pushResult.stderr),
      emptyHooksPath: emptyHooks,
      prePushHookExecutable: executableFile(resolve(emptyHooks, 'pre-push')),
      explicitGitLfsCommands: 0,
      externalMutationCounts: counters,
    });
    if (pushResult.exitCode !== 0) throw new Error(`Lease-protected main update failed: ${asText(pushResult.stderr)}`);

    failedStage = 'REMOTE_NO_SMUDGE_VERIFICATION';
    const afterPush = collectRemote(spec);
    trackedRequired(commandLog, GIT, ['clone', '--depth=2', '--single-branch', '--branch', 'main', spec.repository.url, remoteClone]);
    const remoteHead = trackedGit(commandLog, remoteClone, ['rev-parse', 'HEAD']);
    const remoteParents = trackedGit(commandLog, remoteClone, ['show', '-s', '--format=%P', 'HEAD']).split(/\s+/);
    const remoteChangedPaths = trackedGit(commandLog, remoteClone, ['diff-tree', '--no-commit-id', '--name-only', '-r', spec.source.publicationParent, 'HEAD']).split(/\r?\n/).filter(Boolean).sort();
    const remoteFiles = verifyMaterializedFiles(remoteClone, spec.publicationCommit.ordinaryBlobs);
    const remoteAttributes = checkAttributes(remoteClone, spec.publicationCommit.ordinaryBlobs.map(item => item.path));
    const remoteTreeOids = Object.fromEntries(spec.publicationCommit.changedPaths.map(path => {
      const line = trackedGit(commandLog, remoteClone, ['ls-tree', 'HEAD', '--', path]);
      const match = line.match(/^100644 blob ([0-9a-f]{40})\t/);
      if (!match) throw new Error(`Unexpected remote tree entry for ${path}`);
      return [path, match[1]];
    }));
    const remotePass = afterPush.mainOid === candidateCommit
      && afterPush.headRefs.length === 1
      && afterPush.branchNames.join('\n') === 'main'
      && afterPush.tagRefs.length === 0
      && afterPush.pullRequestCount === 0
      && afterPush.releaseCount === 0
      && remoteHead === candidateCommit
      && remoteParents.length === 1
      && remoteParents[0] === spec.source.publicationParent
      && remoteChangedPaths.join('\n') === expectedPaths.join('\n')
      && remoteFiles.every(item => item.pass)
      && remoteAttributes.every(item => item.pass)
      && spec.publicationCommit.ordinaryBlobs.every(item => remoteTreeOids[item.path] === item.gitBlobOidSha1);
    writeJsonExclusive(resolve(evidenceRoot, 'remote-verification.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1RemoteVerification.v0.4',
      observedAt: new Date().toISOString(),
      status: remotePass ? 'PASS' : 'FAIL',
      cloneEnvironment: { GIT_LFS_SKIP_SMUDGE: '1' },
      live: afterPush,
      cloneHead: remoteHead,
      parentOids: remoteParents,
      changedPaths: remoteChangedPaths,
      treeOids: remoteTreeOids,
      files: remoteFiles,
      attributes: remoteAttributes,
      externalMutationCounts: counters,
    });
    if (!remotePass) throw new Error('Fresh remote no-smudge clone verification failed');

    failedStage = 'VERDICT';
    const verdict = writeJsonExclusive(resolve(evidenceRoot, 'verdict.json'), {
      schemaVersion: 'bfs.repositoryPublicationC1Verdict.v0.4',
      observedAt: new Date().toISOString(),
      status: 'PASS',
      repository: spec.repository.fullName,
      repositoryUrl: afterPush.metadata.htmlUrl,
      publicationParent: spec.source.publicationParent,
      publicationCommit: candidateCommit,
      publicationTree: candidateTree,
      changedPaths,
      ordinaryBlobs: spec.publicationCommit.ordinaryBlobs,
      remoteMainBefore: spec.repository.generatedMainOid,
      remoteMainAfter: afterPush.mainOid,
      localNoSmudgeVerification: 'PASS',
      remoteNoSmudgeVerification: 'PASS',
      noLfsUpload: counters.lfsUploads === 0,
      commandLog,
      externalMutationCounts: counters,
      unauthorizedActionsPerformed: [],
      stopRulePreserved: true,
    });
    process.stdout.write(`${JSON.stringify(verdict, null, 2)}\n`);
  } catch (error) {
    if (evidenceCreated) {
      const failurePath = resolve(evidenceRoot, 'failure.json');
      if (!exists(failurePath)) {
        writeJsonExclusive(failurePath, {
          schemaVersion: 'bfs.repositoryPublicationC1Failure.v0.4',
          observedAt: new Date().toISOString(),
          status: 'FAIL',
          failedStage,
          message: error.message,
          command: error.command ?? null,
          stdout: error.stdout ?? '',
          stderr: error.stderr ?? '',
          commandLog,
          externalMutationCounts: counters,
          retryAttempted: false,
          deletionRecreationOrRenameAttempted: false,
          unauthorizedActionsPerformed: [],
          stopRulePreserved: true,
        });
      }
    }
    throw error;
  }
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));

if (selfTestRequested) {
  runSelfTest(spec);
} else if (executeRequested) {
  execute(spec);
} else {
  const result = collectPreflight(spec);
  process.stdout.write(`${JSON.stringify({ schemaVersion: 'bfs.repositoryPublicationC1ReadOnlyPreflight.v0.4', ...result }, null, 2)}\n`);
  if (result.status !== 'ACCEPTED') process.exitCode = 1;
}
