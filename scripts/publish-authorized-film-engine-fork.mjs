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
const SPEC_RELATIVE = 'specs/ai-native-studio-repository-authorization-request.v0.2.json';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const DOCUMENT_RELATIVE = 'research/2026-08-30-film-engine-public-fork-execution-authorization-v0.2.zh-CN.md';
const DOCUMENT_PATH = resolve(REPOSITORY_ROOT, DOCUMENT_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';

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

function execResult(command, args, cwd = undefined, extraEnv = {}) {
  try {
    const stdout = execFileSync(command, args, {
      cwd,
      encoding: 'utf8',
      env: frozenEnv(extraEnv),
      stdio: ['ignore', 'pipe', 'pipe'],
      maxBuffer: 256 * 1024 * 1024,
    });
    return { exitCode: 0, stdout: stdout.trim(), stderr: '' };
  } catch (error) {
    return {
      exitCode: Number.isInteger(error.status) ? error.status : 1,
      stdout: Buffer.isBuffer(error.stdout) ? error.stdout.toString('utf8').trim() : String(error.stdout ?? '').trim(),
      stderr: Buffer.isBuffer(error.stderr) ? error.stderr.toString('utf8').trim() : String(error.stderr ?? '').trim(),
    };
  }
}

function execRequired(command, args, cwd = undefined, extraEnv = {}) {
  const result = execResult(command, args, cwd, extraEnv);
  if (result.exitCode !== 0) {
    const error = new Error(`Command failed (${result.exitCode}): ${command} ${args.join(' ')}`);
    error.command = [command, ...args];
    error.stdout = result.stdout;
    error.stderr = result.stderr;
    throw error;
  }
  return result.stdout;
}

function git(root, args) {
  return execRequired(GIT, ['-C', root, ...args]);
}

function ghJson(args) {
  const text = execRequired(GH, args);
  return JSON.parse(text);
}

function ghText(args) {
  return execRequired(GH, args);
}

function writeJsonExclusive(path, value) {
  const record = structuredClone(value);
  delete record.receiptHash;
  record.receiptHash = sha256Bytes(canonicalJson(record));
  const descriptor = openSync(path, 'wx', 0o600);
  try {
    writeFileSync(descriptor, `${JSON.stringify(record, null, 2)}\n`);
  } finally {
    closeSync(descriptor);
  }
  return record;
}

function freeBytes(path) {
  const stats = statfsSync(path, { bigint: true });
  return stats.bavail * stats.bsize;
}

function localLfsObjectPath(sourceRoot, oid) {
  return resolve(sourceRoot, '.git', 'lfs', 'objects', oid.slice(0, 2), oid.slice(2, 4), oid);
}

function storageLfsObjectPath(storageRoot, oid) {
  return resolve(storageRoot, 'objects', oid.slice(0, 2), oid.slice(2, 4), oid);
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ls-remote line: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function parseLfsDryRun(text) {
  return text.split(/\r?\n/)
    .filter(line => /\bpush\b/i.test(line))
    .map(line => line.match(/\b([0-9a-f]{64})\b/i)?.[1]?.toLowerCase() ?? null)
    .filter(Boolean);
}

function sameSet(left, right) {
  return left.length === right.length
    && [...new Set(left)].sort().join('\n') === [...new Set(right)].sort().join('\n');
}

function admissionFailures(observed, spec) {
  const failures = [];
  const expectedOids = spec.forkOwnedLfsObjects.map(item => item.oid);
  if (!spec.authorization.granted) failures.push('OWNER_AUTHORIZATION_NOT_GRANTED');
  if (spec.repository.owner !== 'lovejzzz') failures.push('OWNER_CONTRACT_MISMATCH');
  if (spec.repository.requestedName !== 'film-engine') failures.push('NAME_CONTRACT_MISMATCH');
  if (spec.repository.visibility !== 'public') failures.push('VISIBILITY_CONTRACT_MISMATCH');
  if (observed.activeLogin !== spec.repository.owner) failures.push('ACTIVE_GITHUB_LOGIN_MISMATCH');
  if (!observed.candidateAbsent) failures.push('CANDIDATE_REPOSITORY_NOT_ABSENT');
  if (observed.existingParentForks !== 0) failures.push('OWNER_ALREADY_HAS_PARENT_FORK');
  if (!observed.researchClean) failures.push('RESEARCH_WORKTREE_NOT_CLEAN');
  if (!observed.sourceClean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (observed.sourceHead !== spec.repository.desiredHead) failures.push('SOURCE_HEAD_MISMATCH');
  if (observed.sourceTree !== spec.repository.desiredTree) failures.push('SOURCE_TREE_MISMATCH');
  if (observed.sourceParents.join(' ') !== spec.repository.desiredParents.join(' ')) failures.push('SOURCE_PARENTS_MISMATCH');
  if (observed.fullHistoryShallow) failures.push('FULL_HISTORY_SOURCE_IS_SHALLOW');
  if (!observed.fullHistoryBare) failures.push('FULL_HISTORY_SOURCE_NOT_BARE');
  if (observed.fullHistoryHead !== spec.repository.desiredHead) failures.push('FULL_HISTORY_HEAD_MISMATCH');
  if (observed.fullHistoryTree !== spec.repository.desiredTree) failures.push('FULL_HISTORY_TREE_MISMATCH');
  if (observed.fullHistoryCommitCount !== spec.acceptance.expectedFullHistoryReachableCommits) failures.push('FULL_HISTORY_COMMIT_COUNT_MISMATCH');
  if (observed.fullHistoryRefCount !== spec.acceptance.expectedFullHistoryRefCount) failures.push('FULL_HISTORY_REF_COUNT_MISMATCH');
  if (observed.fullHistoryPrePushHook) failures.push('FULL_HISTORY_PRE_PUSH_HOOK_PRESENT');
  if (!observed.fullHistoryFsckPass) failures.push('FULL_HISTORY_FSCK_FAILED');
  if (!sameSet(observed.localLfsOids, expectedOids)) failures.push('LOCAL_LFS_ALLOWLIST_MISMATCH');
  if (!observed.localLfsExact) failures.push('LOCAL_LFS_OBJECT_MISMATCH');
  if (observed.freeBytes < BigInt(spec.acceptance.minimumFreeBytes)) failures.push('FREE_DISK_BELOW_110_GIB');
  if (!observed.evidenceRootAbsent) failures.push('EVIDENCE_ROOT_ALREADY_EXISTS');
  if (!observed.externalRootAbsent) failures.push('PUBLICATION_EXTERNAL_ROOT_ALREADY_EXISTS');
  return failures;
}

function queryCandidate(candidate) {
  const result = execResult(GH, ['api', `repos/${candidate}`]);
  return {
    absent: result.exitCode !== 0 && /HTTP 404/.test(result.stderr),
    exitCode: result.exitCode,
    stderr: result.stderr,
  };
}

function queryOwnerForks(owner) {
  const query = 'query($login:String!){user(login:$login){repositories(first:100,ownerAffiliations:OWNER,isFork:true){nodes{nameWithOwner parent{nameWithOwner}} pageInfo{hasNextPage endCursor}}}}';
  const response = ghJson(['api', 'graphql', '-f', `query=${query}`, '-F', `login=${owner}`]);
  const repositories = response.data.user.repositories;
  if (repositories.pageInfo.hasNextPage) throw new Error('Owner fork inventory exceeds one page; fail closed');
  return repositories.nodes;
}

function collectPreflight(spec) {
  const sourceRoot = spec.paths.sourceCheckout;
  const fullRoot = spec.paths.fullHistorySource;
  const evidenceRoot = resolve(REPOSITORY_ROOT, spec.evidence.publicationEvidenceRoot);
  const externalRoot = spec.paths.publicationExternalRoot;
  const candidateQuery = queryCandidate(spec.repository.candidate);
  const ownerForks = queryOwnerForks(spec.repository.owner);
  const parentForks = ownerForks.filter(item => item.parent?.nameWithOwner === spec.repository.forkParent);
  const lfs = spec.forkOwnedLfsObjects.map(item => {
    const objectPath = localLfsObjectPath(sourceRoot, item.oid);
    return {
      ...item,
      objectPath,
      exists: exists(objectPath),
      observedBytes: exists(objectPath) ? statSync(objectPath).size : null,
      observedSha256: exists(objectPath) ? sha256File(objectPath) : null,
    };
  });
  const fsck = execResult(GIT, ['-C', fullRoot, 'fsck', '--full', '--no-dangling']);
  const observed = {
    observedAt: new Date().toISOString(),
    researchHead: git(REPOSITORY_ROOT, ['rev-parse', 'HEAD']),
    researchClean: git(REPOSITORY_ROOT, ['status', '--porcelain=v1']) === '',
    specification: {
      path: SPEC_RELATIVE,
      sha256: sha256File(SPEC_PATH),
      authorizationDocument: DOCUMENT_RELATIVE,
      authorizationDocumentSha256: sha256File(DOCUMENT_PATH),
      runner: 'scripts/publish-authorized-film-engine-fork.mjs',
      runnerSha256: sha256File(SCRIPT_PATH),
    },
    activeLogin: ghText(['api', 'user', '--jq', '.login']),
    candidateAbsent: candidateQuery.absent,
    candidateQueryExitCode: candidateQuery.exitCode,
    ownerForks,
    existingParentForks: parentForks.length,
    upstreamMain: ghText(['api', `repos/${spec.repository.forkParent}/commits/main`, '--jq', '.sha']),
    sourceRoot,
    sourceClean: git(sourceRoot, ['status', '--porcelain=v1']) === '',
    sourceHead: git(sourceRoot, ['rev-parse', 'HEAD']),
    sourceTree: git(sourceRoot, ['rev-parse', 'HEAD^{tree}']),
    sourceParents: git(sourceRoot, ['show', '-s', '--format=%P', 'HEAD']).split(/\s+/),
    fullHistoryRoot: fullRoot,
    fullHistoryBare: git(fullRoot, ['rev-parse', '--is-bare-repository']) === 'true',
    fullHistoryShallow: git(fullRoot, ['rev-parse', '--is-shallow-repository']) === 'true',
    fullHistoryHead: git(fullRoot, ['rev-parse', 'refs/heads/main']),
    fullHistoryTree: git(fullRoot, ['rev-parse', 'refs/heads/main^{tree}']),
    fullHistoryCommitCount: Number(git(fullRoot, ['rev-list', '--count', 'refs/heads/main'])),
    fullHistoryRefCount: git(fullRoot, ['for-each-ref', '--format=%(refname)']).split(/\r?\n/).filter(Boolean).length,
    fullHistoryPrePushHook: exists(resolve(fullRoot, 'hooks', 'pre-push')),
    fullHistoryFsckPass: fsck.exitCode === 0,
    fullHistoryFsckStdout: fsck.stdout,
    fullHistoryFsckStderr: fsck.stderr,
    localLfsOids: lfs.map(item => item.oid),
    localLfsExact: lfs.every(item => item.exists && item.observedBytes === item.bytes && item.observedSha256 === item.oid),
    localLfsObjects: lfs,
    freeBytes: freeBytes(dirname(externalRoot)),
    evidenceRoot,
    evidenceRootAbsent: !exists(evidenceRoot),
    externalRoot,
    externalRootAbsent: !exists(externalRoot),
  };
  const failures = admissionFailures(observed, spec);
  return {
    schemaVersion: 'bfs.repositoryPublicationPreflight.v0.2',
    ...observed,
    freeBytes: observed.freeBytes.toString(),
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    failures,
    externalMutationCounts: {
      repositoryCreates: 0,
      lfsUploads: 0,
      gitRefUpdates: 0,
      releases: 0,
      phaseBMutations: 0,
    },
  };
}

function publicationFailures({ metadata, branches, pulls, releases, generatedMain, upstreamMain }, spec) {
  const failures = [];
  if (metadata.full_name !== spec.repository.candidate) failures.push('CREATED_REPOSITORY_NAME_MISMATCH');
  if (!metadata.fork) failures.push('CREATED_REPOSITORY_NOT_FORK');
  if (metadata.parent?.full_name !== spec.repository.forkParent) failures.push('CREATED_REPOSITORY_PARENT_MISMATCH');
  if (metadata.owner?.login !== spec.repository.owner) failures.push('CREATED_REPOSITORY_OWNER_MISMATCH');
  if (metadata.private || metadata.visibility !== 'public') failures.push('CREATED_REPOSITORY_NOT_PUBLIC');
  if (metadata.default_branch !== 'main') failures.push('CREATED_DEFAULT_BRANCH_MISMATCH');
  if (branches.length !== spec.acceptance.expectedRemoteBranchCountBeforeAndAfter) failures.push('FRESH_FORK_BRANCH_COUNT_MISMATCH');
  if (branches[0]?.name !== 'main') failures.push('FRESH_FORK_MAIN_MISSING');
  if (pulls.length !== spec.acceptance.expectedRemotePullRequestCountBeforePush) failures.push('FRESH_FORK_PULL_REQUEST_PRESENT');
  if (releases.length !== spec.acceptance.expectedRemoteReleaseCountBeforeAndAfter) failures.push('FRESH_FORK_RELEASE_PRESENT');
  if (generatedMain !== upstreamMain) failures.push('GENERATED_MAIN_NOT_EXACT_UPSTREAM_MAIN');
  return failures;
}

async function waitForFreshFork(spec, upstreamMain) {
  let last = null;
  for (let attempt = 1; attempt <= 40; attempt += 1) {
    const metadataResult = execResult(GH, ['api', `repos/${spec.repository.candidate}`]);
    const remoteResult = execResult(GIT, ['ls-remote', '--heads', `https://github.com/${spec.repository.candidate}.git`]);
    if (metadataResult.exitCode === 0 && remoteResult.exitCode === 0) {
      const metadata = JSON.parse(metadataResult.stdout);
      const refs = parseRemoteRefs(remoteResult.stdout);
      const main = refs.find(item => item.ref === 'refs/heads/main')?.oid ?? null;
      if (main) {
        const branches = ghJson(['api', `repos/${spec.repository.candidate}/branches?per_page=100`]);
        const pulls = ghJson(['api', `repos/${spec.repository.candidate}/pulls?state=all&per_page=100`]);
        const releases = ghJson(['api', `repos/${spec.repository.candidate}/releases?per_page=100`]);
        const failures = publicationFailures({ metadata, branches, pulls, releases, generatedMain: main, upstreamMain }, spec);
        return { attempt, metadata, refs, branches, pulls, releases, generatedMain: main, failures };
      }
      last = { metadataReady: true, refs };
    } else {
      last = { metadataExitCode: metadataResult.exitCode, remoteExitCode: remoteResult.exitCode };
    }
    await new Promise(resolveWait => setTimeout(resolveWait, 3000));
  }
  throw new Error(`Fresh fork did not become ready: ${JSON.stringify(last)}`);
}

function verifyFetchedLfs(spec, storageRoot) {
  const remoteName = 'authorized-film-engine-publication';
  const remoteUrl = `https://github.com/${spec.repository.candidate}.git`;
  mkdirSync(storageRoot, { recursive: false, mode: 0o700 });
  const args = [
    '-C', spec.paths.sourceCheckout,
    '-c', `remote.${remoteName}.url=${remoteUrl}`,
    '-c', `lfs.storage=${storageRoot}`,
    'lfs', 'fetch', '--object-id', remoteName,
    ...spec.forkOwnedLfsObjects.map(item => item.oid),
  ];
  const result = execResult(GIT, args);
  const objects = spec.forkOwnedLfsObjects.map(item => {
    const path = storageLfsObjectPath(storageRoot, item.oid);
    return {
      oid: item.oid,
      expectedBytes: item.bytes,
      exists: exists(path),
      observedBytes: exists(path) ? statSync(path).size : null,
      observedSha256: exists(path) ? sha256File(path) : null,
    };
  });
  return {
    command: [GIT, ...args],
    exitCode: result.exitCode,
    stdout: result.stdout,
    stderr: result.stderr,
    objects,
    pass: result.exitCode === 0 && objects.every(item => item.exists && item.expectedBytes === item.observedBytes && item.oid === item.observedSha256),
  };
}

function remoteLicenseReceipts(spec) {
  return spec.licenseFiles.map(item => {
    const response = ghJson(['api', `repos/${spec.repository.candidate}/contents/${item.path}?ref=${spec.repository.desiredHead}`]);
    const bytes = Buffer.from(response.content.replace(/\s+/g, ''), 'base64');
    return {
      path: item.path,
      expectedSha256: item.sha256,
      observedSha256: sha256Bytes(bytes),
      bytes: bytes.length,
      pass: sha256Bytes(bytes) === item.sha256,
    };
  });
}

async function executePublication(spec) {
  const preflight = collectPreflight(spec);
  if (preflight.status !== 'ACCEPTED') {
    process.stdout.write(`${JSON.stringify(preflight, null, 2)}\n`);
    process.exitCode = 2;
    return;
  }

  const evidenceRoot = preflight.evidenceRoot;
  const externalRoot = preflight.externalRoot;
  mkdirSync(evidenceRoot, { recursive: false, mode: 0o700 });
  mkdirSync(externalRoot, { recursive: false, mode: 0o700 });
  writeJsonExclusive(resolve(evidenceRoot, 'preflight.json'), preflight);
  const mutationCounts = { repositoryCreates: 0, lfsUploads: 0, gitRefUpdates: 0, releases: 0, phaseBMutations: 0 };
  let stage = 'CREATE_FORK';
  try {
    process.stdout.write('PUBLICATION_STAGE create-fork\n');
    const createCommand = [
      GH, 'api', '--method', 'POST', `repos/${spec.repository.forkParent}/forks`,
      '-f', `name=${spec.repository.requestedName}`,
      '-F', `default_branch_only=${spec.repository.forkDefaultBranchOnly}`,
    ];
    const created = ghJson(createCommand.slice(1));
    mutationCounts.repositoryCreates = 1;
    const creationReceipt = writeJsonExclusive(resolve(evidenceRoot, 'creation.json'), {
      schemaVersion: 'bfs.repositoryPublicationCreation.v0.2',
      observedAt: new Date().toISOString(),
      command: createCommand,
      requested: {
        parent: spec.repository.forkParent,
        candidate: spec.repository.candidate,
        visibility: spec.repository.visibility,
        defaultBranchOnly: spec.repository.forkDefaultBranchOnly,
      },
      response: {
        id: created.id,
        nodeId: created.node_id,
        fullName: created.full_name,
        htmlUrl: created.html_url,
        fork: created.fork,
        private: created.private,
        visibility: created.visibility,
        defaultBranch: created.default_branch,
        parent: created.parent?.full_name ?? null,
        createdAt: created.created_at,
      },
      externalMutationCounts: mutationCounts,
    });
    process.stdout.write(`PUBLICATION_CREATED ${creationReceipt.response.htmlUrl}\n`);

    stage = 'VERIFY_FRESH_FORK';
    const fresh = await waitForFreshFork(spec, preflight.upstreamMain);
    const freshReceipt = writeJsonExclusive(resolve(evidenceRoot, 'fresh-fork.json'), {
      schemaVersion: 'bfs.repositoryPublicationFreshFork.v0.2',
      observedAt: new Date().toISOString(),
      pollingAttempt: fresh.attempt,
      repository: {
        id: fresh.metadata.id,
        nodeId: fresh.metadata.node_id,
        fullName: fresh.metadata.full_name,
        fork: fresh.metadata.fork,
        parent: fresh.metadata.parent?.full_name ?? null,
        owner: fresh.metadata.owner?.login ?? null,
        private: fresh.metadata.private,
        visibility: fresh.metadata.visibility,
        defaultBranch: fresh.metadata.default_branch,
        createdAt: fresh.metadata.created_at,
        updatedAt: fresh.metadata.updated_at,
        pushedAt: fresh.metadata.pushed_at,
      },
      upstreamMainObservedBeforeCreate: preflight.upstreamMain,
      generatedMainOid: fresh.generatedMain,
      remoteRefs: fresh.refs,
      branchNames: fresh.branches.map(item => item.name),
      pullRequestCount: fresh.pulls.length,
      releaseCount: fresh.releases.length,
      ownerAuthoredCommitSinceCreation: false,
      ownerAuthoredCommitBasis: 'generated main exact equals upstream main observed immediately before fork creation',
      failures: fresh.failures,
      externalMutationCounts: mutationCounts,
    });
    if (freshReceipt.failures.length) throw new Error(`Fresh-fork gates failed: ${freshReceipt.failures.join(',')}`);

    stage = 'LFS_DRY_RUN';
    process.stdout.write('PUBLICATION_STAGE lfs-dry-run\n');
    const remoteUrl = `https://github.com/${spec.repository.candidate}.git`;
    const dryRunArgs = [
      '-C', spec.paths.sourceCheckout,
      'lfs', 'push', '--dry-run', '--object-id', remoteUrl,
      ...spec.forkOwnedLfsObjects.map(item => item.oid),
    ];
    const dryRun = execResult(GIT, dryRunArgs);
    const dryRunCombined = [dryRun.stdout, dryRun.stderr].filter(Boolean).join('\n');
    const dryRunOids = parseLfsDryRun(dryRunCombined);
    const expectedOids = spec.forkOwnedLfsObjects.map(item => item.oid);
    const dryRunReceipt = writeJsonExclusive(resolve(evidenceRoot, 'lfs-dry-run.json'), {
      schemaVersion: 'bfs.repositoryPublicationLfsDryRun.v0.2',
      observedAt: new Date().toISOString(),
      command: [GIT, ...dryRunArgs],
      exitCode: dryRun.exitCode,
      stdout: dryRun.stdout,
      stderr: dryRun.stderr,
      expectedOids,
      observedOids: dryRunOids,
      pass: dryRun.exitCode === 0 && sameSet(dryRunOids, expectedOids),
      externalMutationCounts: mutationCounts,
    });
    if (!dryRunReceipt.pass) throw new Error('LFS dry-run did not list exactly the two authorized OIDs');

    stage = 'LFS_UPLOAD';
    process.stdout.write('PUBLICATION_STAGE lfs-upload\n');
    const lfsPushArgs = [
      '-C', spec.paths.sourceCheckout,
      'lfs', 'push', '--object-id', remoteUrl,
      ...expectedOids,
    ];
    const lfsPush = execResult(GIT, lfsPushArgs);
    if (lfsPush.exitCode !== 0) {
      const error = new Error('Authorized LFS upload failed');
      error.command = [GIT, ...lfsPushArgs];
      error.stdout = lfsPush.stdout;
      error.stderr = lfsPush.stderr;
      throw error;
    }
    mutationCounts.lfsUploads = 2;
    const beforePushFetch = verifyFetchedLfs(spec, resolve(externalRoot, 'lfs-verify-before-ref-update'));
    const lfsReceipt = writeJsonExclusive(resolve(evidenceRoot, 'lfs-upload.json'), {
      schemaVersion: 'bfs.repositoryPublicationLfsUpload.v0.2',
      observedAt: new Date().toISOString(),
      command: [GIT, ...lfsPushArgs],
      exitCode: lfsPush.exitCode,
      stdout: lfsPush.stdout,
      stderr: lfsPush.stderr,
      uploadedOids: expectedOids,
      uploadedObjectCount: 2,
      uploadedBytes: spec.lfsUploadBytes,
      readBackBeforeRefUpdate: beforePushFetch,
      pass: beforePushFetch.pass,
      externalMutationCounts: mutationCounts,
    });
    if (!lfsReceipt.pass) throw new Error('LFS read-back before ref update failed');

    stage = 'RECHECK_LEASE';
    const leaseRefs = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--heads', remoteUrl]));
    const leaseMain = leaseRefs.find(item => item.ref === 'refs/heads/main')?.oid ?? null;
    const metadataBeforePush = ghJson(['api', `repos/${spec.repository.candidate}`]);
    const branchesBeforePush = ghJson(['api', `repos/${spec.repository.candidate}/branches?per_page=100`]);
    const pullsBeforePush = ghJson(['api', `repos/${spec.repository.candidate}/pulls?state=all&per_page=100`]);
    const releasesBeforePush = ghJson(['api', `repos/${spec.repository.candidate}/releases?per_page=100`]);
    const leaseFailures = publicationFailures({
      metadata: metadataBeforePush,
      branches: branchesBeforePush,
      pulls: pullsBeforePush,
      releases: releasesBeforePush,
      generatedMain: leaseMain,
      upstreamMain: fresh.generatedMain,
    }, spec);
    const leaseReceipt = writeJsonExclusive(resolve(evidenceRoot, 'lease-recheck.json'), {
      schemaVersion: 'bfs.repositoryPublicationLeaseRecheck.v0.2',
      observedAt: new Date().toISOString(),
      generatedMainOid: fresh.generatedMain,
      immediatelyObservedMainOid: leaseMain,
      branchNames: branchesBeforePush.map(item => item.name),
      pullRequestCount: pullsBeforePush.length,
      releaseCount: releasesBeforePush.length,
      failures: leaseFailures,
      pass: leaseFailures.length === 0 && leaseMain === fresh.generatedMain,
      externalMutationCounts: mutationCounts,
    });
    if (!leaseReceipt.pass) throw new Error(`Lease recheck failed: ${leaseFailures.join(',')}`);

    stage = 'LEASE_PROTECTED_REF_UPDATE';
    process.stdout.write('PUBLICATION_STAGE lease-protected-main-update\n');
    const pushArgs = [
      '-C', spec.paths.fullHistorySource,
      'push',
      `--force-with-lease=refs/heads/main:${fresh.generatedMain}`,
      remoteUrl,
      'refs/heads/main:refs/heads/main',
    ];
    const push = execResult(GIT, pushArgs);
    if (push.exitCode !== 0) {
      const error = new Error('Lease-protected main update failed');
      error.command = [GIT, ...pushArgs];
      error.stdout = push.stdout;
      error.stderr = push.stderr;
      throw error;
    }
    mutationCounts.gitRefUpdates = 1;
    writeJsonExclusive(resolve(evidenceRoot, 'main-update.json'), {
      schemaVersion: 'bfs.repositoryPublicationMainUpdate.v0.2',
      observedAt: new Date().toISOString(),
      command: [GIT, ...pushArgs],
      generatedMainLeaseOid: fresh.generatedMain,
      desiredMainOid: spec.repository.desiredHead,
      exitCode: push.exitCode,
      stdout: push.stdout,
      stderr: push.stderr,
      externalMutationCounts: mutationCounts,
    });

    stage = 'FINAL_VERIFICATION';
    process.stdout.write('PUBLICATION_STAGE final-verification\n');
    const finalRefs = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--heads', remoteUrl]));
    const finalMain = finalRefs.find(item => item.ref === 'refs/heads/main')?.oid ?? null;
    const finalMetadata = ghJson(['api', `repos/${spec.repository.candidate}`]);
    const finalBranches = ghJson(['api', `repos/${spec.repository.candidate}/branches?per_page=100`]);
    const finalReleases = ghJson(['api', `repos/${spec.repository.candidate}/releases?per_page=100`]);
    const finalPulls = ghJson(['api', `repos/${spec.repository.candidate}/pulls?state=all&per_page=100`]);
    const commit = ghJson(['api', `repos/${spec.repository.candidate}/git/commits/${spec.repository.desiredHead}`]);
    const finalLfs = verifyFetchedLfs(spec, resolve(externalRoot, 'lfs-verify-after-ref-update'));
    const licenses = remoteLicenseReceipts(spec);
    const mergeBase = git(spec.paths.fullHistorySource, ['merge-base', spec.repository.mergeBase, spec.repository.desiredHead]);
    const finalFailures = [];
    if (finalMain !== spec.repository.desiredHead) finalFailures.push('FINAL_MAIN_MISMATCH');
    if (commit.sha !== spec.repository.desiredHead) finalFailures.push('FINAL_COMMIT_MISMATCH');
    if (commit.tree?.sha !== spec.repository.desiredTree) finalFailures.push('FINAL_TREE_MISMATCH');
    if ((commit.parents ?? []).map(item => item.sha).join(' ') !== spec.repository.desiredParents.join(' ')) finalFailures.push('FINAL_PARENTS_MISMATCH');
    if (mergeBase !== spec.repository.mergeBase) finalFailures.push('FINAL_MERGE_BASE_MISMATCH');
    if (finalBranches.length !== 1 || finalBranches[0]?.name !== 'main') finalFailures.push('FINAL_BRANCH_SET_MISMATCH');
    if (finalReleases.length !== 0) finalFailures.push('FINAL_RELEASE_PRESENT');
    if (finalPulls.length !== 0) finalFailures.push('FINAL_PULL_REQUEST_PRESENT');
    if (!finalMetadata.fork || finalMetadata.parent?.full_name !== spec.repository.forkParent) finalFailures.push('FINAL_FORK_METADATA_MISMATCH');
    if (finalMetadata.private || finalMetadata.visibility !== 'public') finalFailures.push('FINAL_VISIBILITY_MISMATCH');
    if (!finalLfs.pass) finalFailures.push('FINAL_LFS_READBACK_FAILED');
    if (!licenses.every(item => item.pass)) finalFailures.push('FINAL_LICENSE_HASH_MISMATCH');
    if (mutationCounts.repositoryCreates !== 1 || mutationCounts.lfsUploads !== 2 || mutationCounts.gitRefUpdates !== 1) finalFailures.push('MUTATION_COUNT_MISMATCH');
    if (mutationCounts.releases !== 0 || mutationCounts.phaseBMutations !== 0) finalFailures.push('UNAUTHORIZED_MUTATION_RECORDED');

    const verdict = writeJsonExclusive(resolve(evidenceRoot, 'verdict.json'), {
      schemaVersion: 'bfs.repositoryPublicationVerdict.v0.2',
      observedAt: new Date().toISOString(),
      status: finalFailures.length === 0 ? 'PASS' : 'FAIL',
      repository: {
        fullName: finalMetadata.full_name,
        htmlUrl: finalMetadata.html_url,
        fork: finalMetadata.fork,
        parent: finalMetadata.parent?.full_name ?? null,
        owner: finalMetadata.owner?.login ?? null,
        visibility: finalMetadata.visibility,
        private: finalMetadata.private,
        defaultBranch: finalMetadata.default_branch,
        createdAt: finalMetadata.created_at,
        pushedAt: finalMetadata.pushed_at,
      },
      generatedMainLeaseOid: fresh.generatedMain,
      finalMainOid: finalMain,
      finalTreeOid: commit.tree?.sha ?? null,
      finalParentOids: (commit.parents ?? []).map(item => item.sha),
      mergeBase,
      finalRemoteRefs: finalRefs,
      branchNames: finalBranches.map(item => item.name),
      pullRequestCount: finalPulls.length,
      releaseCount: finalReleases.length,
      lfs: finalLfs,
      licenses,
      externalMutationCounts: mutationCounts,
      stillUnauthorized: spec.stillUnauthorized,
      failures: finalFailures,
      claimCeiling: 'Exact authorized public-fork first publication only; no release, distribution, signing, notarization, Phase B mutation, production-readiness or legal-sufficiency claim.',
    });
    process.stdout.write(`${JSON.stringify(verdict, null, 2)}\n`);
    if (verdict.status !== 'PASS') process.exitCode = 3;
  } catch (error) {
    const failure = {
      schemaVersion: 'bfs.repositoryPublicationFailure.v0.2',
      observedAt: new Date().toISOString(),
      status: 'FAIL',
      failedStage: stage,
      error: error.message,
      command: error.command ?? null,
      stdout: error.stdout ?? '',
      stderr: error.stderr ?? '',
      externalMutationCounts: mutationCounts,
      candidate: spec.repository.candidate,
      deletionOrRecreationAttempted: false,
      stopRule: 'Retain the fresh fork and evidence; do not delete or recreate it.',
    };
    if (!exists(resolve(evidenceRoot, 'failure.json'))) writeJsonExclusive(resolve(evidenceRoot, 'failure.json'), failure);
    process.stderr.write(`${JSON.stringify(failure, null, 2)}\n`);
    process.exitCode = 4;
  }
}

function selfTest(spec) {
  const expectedOids = spec.forkOwnedLfsObjects.map(item => item.oid);
  const fixture = {
    activeLogin: 'lovejzzz',
    candidateAbsent: true,
    existingParentForks: 0,
    researchClean: true,
    sourceClean: true,
    sourceHead: spec.repository.desiredHead,
    sourceTree: spec.repository.desiredTree,
    sourceParents: spec.repository.desiredParents,
    fullHistoryShallow: false,
    fullHistoryBare: true,
    fullHistoryHead: spec.repository.desiredHead,
    fullHistoryTree: spec.repository.desiredTree,
    fullHistoryCommitCount: spec.acceptance.expectedFullHistoryReachableCommits,
    fullHistoryRefCount: 1,
    fullHistoryPrePushHook: false,
    fullHistoryFsckPass: true,
    localLfsOids: expectedOids,
    localLfsExact: true,
    freeBytes: BigInt(spec.acceptance.minimumFreeBytes),
    evidenceRootAbsent: true,
    externalRootAbsent: true,
  };
  const cases = [
    ['ACTIVE_GITHUB_LOGIN_MISMATCH', { activeLogin: 'someone-else' }],
    ['CANDIDATE_REPOSITORY_NOT_ABSENT', { candidateAbsent: false }],
    ['OWNER_ALREADY_HAS_PARENT_FORK', { existingParentForks: 1 }],
    ['SOURCE_HEAD_MISMATCH', { sourceHead: '0'.repeat(40) }],
    ['FULL_HISTORY_SOURCE_IS_SHALLOW', { fullHistoryShallow: true }],
    ['FULL_HISTORY_PRE_PUSH_HOOK_PRESENT', { fullHistoryPrePushHook: true }],
    ['LOCAL_LFS_ALLOWLIST_MISMATCH', { localLfsOids: [...expectedOids, 'f'.repeat(64)] }],
    ['LOCAL_LFS_OBJECT_MISMATCH', { localLfsExact: false }],
    ['FREE_DISK_BELOW_110_GIB', { freeBytes: BigInt(spec.acceptance.minimumFreeBytes) - 1n }],
    ['EVIDENCE_ROOT_ALREADY_EXISTS', { evidenceRootAbsent: false }],
  ].map(([expectedFailure, changes]) => {
    const failures = admissionFailures({ ...fixture, ...changes }, spec);
    return { expectedFailure, failures, passed: failures.includes(expectedFailure) };
  });
  const dryRunFixture = expectedOids.map(oid => `push ${oid}`).join('\n');
  const dryRunParsed = parseLfsDryRun(dryRunFixture);
  const result = {
    status: admissionFailures(fixture, spec).length === 0 && cases.every(item => item.passed) && sameSet(dryRunParsed, expectedOids) ? 'PASS' : 'FAIL',
    positiveAdmissionFailures: admissionFailures(fixture, spec),
    negativeControls: cases,
    lfsDryRunParser: { fixture: dryRunFixture, parsed: dryRunParsed, pass: sameSet(dryRunParsed, expectedOids) },
  };
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (result.status !== 'PASS') process.exitCode = 1;
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
if (process.argv.includes('--self-test')) {
  selfTest(spec);
} else if (process.argv.includes('--execute')) {
  await executePublication(spec);
} else {
  const preflight = collectPreflight(spec);
  process.stdout.write(`${JSON.stringify(preflight, null, 2)}\n`);
  if (preflight.status !== 'ACCEPTED') process.exitCode = 2;
}
