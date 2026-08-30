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
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const AUDITOR_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const SPEC_PATH = resolve(REPOSITORY_ROOT, 'specs/ai-native-studio-repository-authorization-request.v0.2.json');
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

function execResult(command, args, cwd = undefined) {
  try {
    const stdout = execFileSync(command, args, {
      cwd,
      encoding: 'utf8',
      env: {
        ...process.env,
        PATH: FROZEN_PATH,
        LANG: 'C',
        LC_ALL: 'C',
        GH_PROMPT_DISABLED: '1',
        GIT_TERMINAL_PROMPT: '0',
        GIT_LFS_SKIP_SMUDGE: '1',
      },
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

function execRequired(command, args, cwd = undefined) {
  const result = execResult(command, args, cwd);
  if (result.exitCode !== 0) throw new Error(`Command failed: ${command} ${args.join(' ')}\n${result.stderr}`);
  return result.stdout;
}

function ghJson(args) {
  return JSON.parse(execRequired(GH, args));
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected remote ref: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function receiptHashPass(record) {
  const copy = structuredClone(record);
  const expected = copy.receiptHash;
  delete copy.receiptHash;
  return expected === sha256Bytes(canonicalJson(copy));
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

function lfsPath(storageRoot, oid) {
  return resolve(storageRoot, 'objects', oid.slice(0, 2), oid.slice(2, 4), oid);
}

function auditLfsReadback(spec, storageRoot) {
  if (exists(storageRoot)) throw new Error(`Audit LFS storage already exists: ${storageRoot}`);
  mkdirSync(storageRoot, { recursive: false, mode: 0o700 });
  const remoteName = 'film-engine-audit-readonly';
  const remoteUrl = `https://github.com/${spec.repository.candidate}.git`;
  const args = [
    '-C', spec.paths.sourceCheckout,
    '-c', `remote.${remoteName}.url=${remoteUrl}`,
    '-c', `lfs.storage=${storageRoot}`,
    'lfs', 'fetch', '--object-id', remoteName,
    ...spec.forkOwnedLfsObjects.map(item => item.oid),
  ];
  const result = execResult(GIT, args);
  const objects = spec.forkOwnedLfsObjects.map(item => {
    const path = lfsPath(storageRoot, item.oid);
    return {
      oid: item.oid,
      exists: exists(path),
      expectedBytes: item.bytes,
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

function addCheck(checks, id, pass, actual, expected) {
  checks.push({ id, pass: Boolean(pass), actual, expected });
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.evidence.publicationEvidenceRoot);
const auditPath = resolve(evidenceRoot, 'audit.json');
if (exists(auditPath)) throw new Error(`Audit already exists: ${auditPath}`);

const requiredFiles = [
  'preflight.json',
  'creation.json',
  'fresh-fork.json',
  'lfs-dry-run.json',
  'lfs-upload.json',
  'lease-recheck.json',
  'main-update.json',
  'verdict.json',
];
for (const name of requiredFiles) {
  if (!exists(resolve(evidenceRoot, name))) throw new Error(`Required evidence missing: ${name}`);
}
if (exists(resolve(evidenceRoot, 'failure.json'))) throw new Error('Runner failure.json exists; accepted audit forbidden');

const records = Object.fromEntries(requiredFiles.map(name => [name, JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'))]));
const preflight = records['preflight.json'];
const creation = records['creation.json'];
const fresh = records['fresh-fork.json'];
const dryRun = records['lfs-dry-run.json'];
const lfsUpload = records['lfs-upload.json'];
const lease = records['lease-recheck.json'];
const update = records['main-update.json'];
const verdict = records['verdict.json'];
const checks = [];

for (const [name, record] of Object.entries(records)) {
  addCheck(checks, `RECEIPT_HASH_${name}`, receiptHashPass(record), record.receiptHash, 'self hash exact');
}

addCheck(checks, 'SPEC_AUTHORIZED', spec.authorization.granted, spec.authorization.granted, true);
addCheck(checks, 'SPEC_NAME', spec.repository.candidate === 'lovejzzz/film-engine', spec.repository.candidate, 'lovejzzz/film-engine');
addCheck(checks, 'PREFLIGHT_ACCEPTED', preflight.status === 'ACCEPTED', preflight.status, 'ACCEPTED');
addCheck(checks, 'PREFLIGHT_CANDIDATE_ABSENT', preflight.candidateAbsent, preflight.candidateAbsent, true);
addCheck(checks, 'PREFLIGHT_NO_PARENT_FORK', preflight.existingParentForks === 0, preflight.existingParentForks, 0);
addCheck(checks, 'PREFLIGHT_RUNNER_HASH', preflight.specification.runnerSha256 === sha256File(resolve(REPOSITORY_ROOT, preflight.specification.runner)), preflight.specification.runnerSha256, sha256File(resolve(REPOSITORY_ROOT, preflight.specification.runner)));
addCheck(checks, 'PREFLIGHT_SPEC_HASH', preflight.specification.sha256 === sha256File(SPEC_PATH), preflight.specification.sha256, sha256File(SPEC_PATH));
addCheck(checks, 'CREATION_EXACT_TARGET', creation.requested.candidate === spec.repository.candidate, creation.requested.candidate, spec.repository.candidate);
addCheck(checks, 'CREATION_DEFAULT_BRANCH_ONLY', creation.requested.defaultBranchOnly === true, creation.requested.defaultBranchOnly, true);
addCheck(checks, 'CREATION_RESPONSE_FORK', creation.response.fork === true, creation.response.fork, true);
addCheck(checks, 'CREATION_RESPONSE_PUBLIC', creation.response.private === false && creation.response.visibility === 'public', { private: creation.response.private, visibility: creation.response.visibility }, { private: false, visibility: 'public' });
addCheck(checks, 'FRESH_PARENT', fresh.repository.parent === spec.repository.forkParent, fresh.repository.parent, spec.repository.forkParent);
addCheck(checks, 'FRESH_GENERATED_EQUALS_UPSTREAM', fresh.generatedMainOid === fresh.upstreamMainObservedBeforeCreate, fresh.generatedMainOid, fresh.upstreamMainObservedBeforeCreate);
addCheck(checks, 'FRESH_BRANCH_SET', fresh.branchNames.length === 1 && fresh.branchNames[0] === 'main', fresh.branchNames, ['main']);
addCheck(checks, 'FRESH_NO_PR', fresh.pullRequestCount === 0, fresh.pullRequestCount, 0);
addCheck(checks, 'FRESH_NO_RELEASE', fresh.releaseCount === 0, fresh.releaseCount, 0);
addCheck(checks, 'LFS_DRY_RUN_PASS', dryRun.pass === true, dryRun.pass, true);
addCheck(checks, 'LFS_DRY_RUN_ALLOWLIST', dryRun.observedOids.slice().sort().join('\n') === spec.forkOwnedLfsObjects.map(item => item.oid).sort().join('\n'), dryRun.observedOids, spec.forkOwnedLfsObjects.map(item => item.oid));
addCheck(checks, 'LFS_UPLOAD_COUNT', lfsUpload.uploadedObjectCount === 2, lfsUpload.uploadedObjectCount, 2);
addCheck(checks, 'LFS_UPLOAD_BYTES', lfsUpload.uploadedBytes === 2701144, lfsUpload.uploadedBytes, 2701144);
addCheck(checks, 'LFS_PRE_REF_READBACK', lfsUpload.readBackBeforeRefUpdate.pass === true, lfsUpload.readBackBeforeRefUpdate.pass, true);
addCheck(checks, 'LEASE_RECHECK_PASS', lease.pass === true, lease.pass, true);
addCheck(checks, 'LEASE_OID_STABLE', lease.generatedMainOid === lease.immediatelyObservedMainOid, lease.immediatelyObservedMainOid, lease.generatedMainOid);
const forceLeaseArg = `--force-with-lease=refs/heads/main:${fresh.generatedMainOid}`;
addCheck(checks, 'UPDATE_EXPLICIT_FORCE_LEASE', update.command.includes(forceLeaseArg), update.command, forceLeaseArg);
addCheck(checks, 'UPDATE_NO_UNLEASED_FORCE', !update.command.includes('--force') && !update.command.includes('-f'), update.command, 'no --force or -f');
addCheck(checks, 'RUNNER_VERDICT_PASS', verdict.status === 'PASS', verdict.status, 'PASS');
addCheck(checks, 'RUNNER_FINAL_HEAD', verdict.finalMainOid === spec.repository.desiredHead, verdict.finalMainOid, spec.repository.desiredHead);
addCheck(checks, 'RUNNER_FINAL_TREE', verdict.finalTreeOid === spec.repository.desiredTree, verdict.finalTreeOid, spec.repository.desiredTree);
addCheck(checks, 'RUNNER_FINAL_PARENTS', verdict.finalParentOids.join(' ') === spec.repository.desiredParents.join(' '), verdict.finalParentOids, spec.repository.desiredParents);
addCheck(checks, 'RUNNER_MUTATION_COUNTS', canonicalJson(verdict.externalMutationCounts) === canonicalJson({ repositoryCreates: 1, lfsUploads: 2, gitRefUpdates: 1, releases: 0, phaseBMutations: 0 }), verdict.externalMutationCounts, { repositoryCreates: 1, lfsUploads: 2, gitRefUpdates: 1, releases: 0, phaseBMutations: 0 });

const activeLogin = execRequired(GH, ['api', 'user', '--jq', '.login']);
const metadata = ghJson(['api', `repos/${spec.repository.candidate}`]);
const refs = parseRemoteRefs(execRequired(GIT, ['ls-remote', '--heads', `https://github.com/${spec.repository.candidate}.git`]));
const main = refs.find(item => item.ref === 'refs/heads/main')?.oid ?? null;
const branches = ghJson(['api', `repos/${spec.repository.candidate}/branches?per_page=100`]);
const pulls = ghJson(['api', `repos/${spec.repository.candidate}/pulls?state=all&per_page=100`]);
const releases = ghJson(['api', `repos/${spec.repository.candidate}/releases?per_page=100`]);
const commit = ghJson(['api', `repos/${spec.repository.candidate}/git/commits/${spec.repository.desiredHead}`]);

addCheck(checks, 'LIVE_ACTIVE_OWNER', activeLogin === spec.repository.owner, activeLogin, spec.repository.owner);
addCheck(checks, 'LIVE_REPOSITORY_NAME', metadata.full_name === spec.repository.candidate, metadata.full_name, spec.repository.candidate);
addCheck(checks, 'LIVE_FORK_PARENT', metadata.fork === true && metadata.parent?.full_name === spec.repository.forkParent, { fork: metadata.fork, parent: metadata.parent?.full_name }, { fork: true, parent: spec.repository.forkParent });
addCheck(checks, 'LIVE_PUBLIC', metadata.private === false && metadata.visibility === 'public', { private: metadata.private, visibility: metadata.visibility }, { private: false, visibility: 'public' });
addCheck(checks, 'LIVE_DEFAULT_BRANCH', metadata.default_branch === 'main', metadata.default_branch, 'main');
addCheck(checks, 'LIVE_MAIN', main === spec.repository.desiredHead, main, spec.repository.desiredHead);
addCheck(checks, 'LIVE_BRANCH_SET', branches.length === 1 && branches[0]?.name === 'main', branches.map(item => item.name), ['main']);
addCheck(checks, 'LIVE_NO_PR', pulls.length === 0, pulls.length, 0);
addCheck(checks, 'LIVE_NO_RELEASE', releases.length === 0, releases.length, 0);
addCheck(checks, 'LIVE_TREE', commit.tree?.sha === spec.repository.desiredTree, commit.tree?.sha, spec.repository.desiredTree);
addCheck(checks, 'LIVE_PARENTS', (commit.parents ?? []).map(item => item.sha).join(' ') === spec.repository.desiredParents.join(' '), (commit.parents ?? []).map(item => item.sha), spec.repository.desiredParents);

const auditLfs = auditLfsReadback(spec, resolve(spec.paths.publicationExternalRoot, 'lfs-independent-audit'));
addCheck(checks, 'LIVE_LFS_READBACK', auditLfs.pass, auditLfs.objects, 'both exact');

const licenses = spec.licenseFiles.map(item => {
  const response = ghJson(['api', `repos/${spec.repository.candidate}/contents/${item.path}?ref=${spec.repository.desiredHead}`]);
  const bytes = Buffer.from(response.content.replace(/\s+/g, ''), 'base64');
  return { path: item.path, observedSha256: sha256Bytes(bytes), expectedSha256: item.sha256 };
});
addCheck(checks, 'LIVE_LICENSES', licenses.every(item => item.observedSha256 === item.expectedSha256), licenses, 'all exact');

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.repositoryPublicationAudit.v0.2',
  observedAt: new Date().toISOString(),
  status: failed.length === 0 ? 'PASS' : 'FAIL',
  auditor: {
    path: 'scripts/audit-authorized-film-engine-fork.mjs',
    sha256: sha256File(AUDITOR_PATH),
    importsRunner: false,
  },
  repository: spec.repository.candidate,
  live: {
    activeLogin,
    metadata: {
      fullName: metadata.full_name,
      htmlUrl: metadata.html_url,
      fork: metadata.fork,
      parent: metadata.parent?.full_name,
      private: metadata.private,
      visibility: metadata.visibility,
      defaultBranch: metadata.default_branch,
      createdAt: metadata.created_at,
      pushedAt: metadata.pushed_at,
    },
    refs,
    branches: branches.map(item => item.name),
    pullRequestCount: pulls.length,
    releaseCount: releases.length,
    commit: {
      oid: commit.sha,
      tree: commit.tree?.sha,
      parents: (commit.parents ?? []).map(item => item.sha),
    },
    lfs: auditLfs,
    licenses,
  },
  checksPassed: checks.length - failed.length,
  checksTotal: checks.length,
  checks,
  failures: failed.map(item => item.id),
  externalMutationsPerformedByAuditor: 0,
  claimCeiling: 'Independent read-only verification of the authorized public-fork first publication; local LFS audit cache creation only.',
});

process.stdout.write(`${JSON.stringify(audit, null, 2)}\n`);
if (audit.status !== 'PASS') process.exitCode = 1;
