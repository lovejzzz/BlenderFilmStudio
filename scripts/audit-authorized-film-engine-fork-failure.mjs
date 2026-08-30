#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { openSync, closeSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
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

function receiptHashPass(record) {
  const copy = structuredClone(record);
  const expected = copy.receiptHash;
  delete copy.receiptHash;
  return expected === sha256Bytes(canonicalJson(copy));
}

function command(command, args) {
  return execFileSync(command, args, {
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
    maxBuffer: 64 * 1024 * 1024,
  }).trim();
}

function ghJson(args) {
  return JSON.parse(command(GH, args));
}

function add(checks, id, pass, actual, expected) {
  checks.push({ id, pass: Boolean(pass), actual, expected });
}

function writeExclusive(path, value) {
  const record = structuredClone(value);
  record.receiptHash = sha256Bytes(canonicalJson(record));
  const descriptor = openSync(path, 'wx', 0o600);
  try {
    writeFileSync(descriptor, `${JSON.stringify(record, null, 2)}\n`);
  } finally {
    closeSync(descriptor);
  }
  return record;
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const root = resolve(REPOSITORY_ROOT, spec.evidence.publicationEvidenceRoot);
const auditPath = resolve(root, 'audit-failure.json');
if (existsSync(auditPath)) throw new Error(`Failure audit already exists: ${auditPath}`);

const names = ['preflight.json', 'creation.json', 'fresh-fork.json', 'lfs-dry-run.json', 'failure.json'];
const receipts = Object.fromEntries(names.map(name => [name, JSON.parse(readFileSync(resolve(root, name), 'utf8'))]));
const preflight = receipts['preflight.json'];
const creation = receipts['creation.json'];
const fresh = receipts['fresh-fork.json'];
const dryRun = receipts['lfs-dry-run.json'];
const failure = receipts['failure.json'];
const checks = [];

for (const [name, receipt] of Object.entries(receipts)) {
  add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt), receipt.receiptHash, 'canonical self hash exact');
}

add(checks, 'PREFLIGHT_ACCEPTED', preflight.status === 'ACCEPTED' && preflight.failures.length === 0, { status: preflight.status, failures: preflight.failures }, { status: 'ACCEPTED', failures: [] });
add(checks, 'PRECREATE_ABSENT', preflight.candidateAbsent === true, preflight.candidateAbsent, true);
add(checks, 'CREATE_COUNT_ONE', creation.externalMutationCounts.repositoryCreates === 1, creation.externalMutationCounts.repositoryCreates, 1);
add(checks, 'CREATION_EXACT', creation.response.fullName === spec.repository.candidate && creation.response.parent === spec.repository.forkParent, creation.response, { fullName: spec.repository.candidate, parent: spec.repository.forkParent });
add(checks, 'CREATION_PUBLIC_FORK', creation.response.fork === true && creation.response.private === false && creation.response.visibility === 'public', { fork: creation.response.fork, private: creation.response.private, visibility: creation.response.visibility }, { fork: true, private: false, visibility: 'public' });
add(checks, 'FRESH_MAIN_EQUALS_UPSTREAM', fresh.generatedMainOid === fresh.upstreamMainObservedBeforeCreate, fresh.generatedMainOid, fresh.upstreamMainObservedBeforeCreate);
add(checks, 'FRESH_SINGLE_MAIN', fresh.branchNames.length === 1 && fresh.branchNames[0] === 'main', fresh.branchNames, ['main']);
add(checks, 'FRESH_NO_PR_RELEASE', fresh.pullRequestCount === 0 && fresh.releaseCount === 0, { pullRequests: fresh.pullRequestCount, releases: fresh.releaseCount }, { pullRequests: 0, releases: 0 });
add(checks, 'LFS_DRY_RUN_TWO', dryRun.pass === true && dryRun.observedOids.length === 2, { pass: dryRun.pass, oids: dryRun.observedOids }, { pass: true, count: 2 });
add(checks, 'FAILURE_STAGE_LFS_UPLOAD', failure.status === 'FAIL' && failure.failedStage === 'LFS_UPLOAD', { status: failure.status, stage: failure.failedStage }, { status: 'FAIL', stage: 'LFS_UPLOAD' });
add(checks, 'FAILURE_SERVER_POLICY_EXACT', failure.stderr === 'batch response: @lovejzzz can not upload new objects to public fork lovejzzz/film-engine', failure.stderr, 'exact GitHub public-fork LFS denial');
add(checks, 'FAILURE_ZERO_LFS_UPLOAD', failure.externalMutationCounts.lfsUploads === 0, failure.externalMutationCounts.lfsUploads, 0);
add(checks, 'FAILURE_ZERO_REF_UPDATE', failure.externalMutationCounts.gitRefUpdates === 0, failure.externalMutationCounts.gitRefUpdates, 0);
add(checks, 'FAILURE_ZERO_RELEASE_PHASE_B', failure.externalMutationCounts.releases === 0 && failure.externalMutationCounts.phaseBMutations === 0, { releases: failure.externalMutationCounts.releases, phaseB: failure.externalMutationCounts.phaseBMutations }, { releases: 0, phaseB: 0 });
add(checks, 'NO_DELETE_RECREATE', failure.deletionOrRecreationAttempted === false, failure.deletionOrRecreationAttempted, false);

for (const name of ['lfs-upload.json', 'lease-recheck.json', 'main-update.json', 'verdict.json', 'audit.json']) {
  add(checks, `LATER_STAGE_ABSENT_${name}`, !existsSync(resolve(root, name)), existsSync(resolve(root, name)), false);
}

const metadata = ghJson(['api', `repos/${spec.repository.candidate}`]);
const branches = ghJson(['api', `repos/${spec.repository.candidate}/branches?per_page=100`]);
const pulls = ghJson(['api', `repos/${spec.repository.candidate}/pulls?state=all&per_page=100`]);
const releases = ghJson(['api', `repos/${spec.repository.candidate}/releases?per_page=100`]);
const refsText = command(GIT, ['ls-remote', '--heads', `https://github.com/${spec.repository.candidate}.git`]);
const refMatch = refsText.match(/^([0-9a-f]{40})\s+refs\/heads\/main$/m);
const liveMain = refMatch?.[1] ?? null;

add(checks, 'LIVE_REPOSITORY_EXACT', metadata.full_name === spec.repository.candidate, metadata.full_name, spec.repository.candidate);
add(checks, 'LIVE_PUBLIC_FORK_PARENT', metadata.fork === true && metadata.parent?.full_name === spec.repository.forkParent && metadata.private === false && metadata.visibility === 'public', { fork: metadata.fork, parent: metadata.parent?.full_name, private: metadata.private, visibility: metadata.visibility }, { fork: true, parent: spec.repository.forkParent, private: false, visibility: 'public' });
add(checks, 'LIVE_MAIN_UNCHANGED', liveMain === fresh.generatedMainOid, liveMain, fresh.generatedMainOid);
add(checks, 'LIVE_SINGLE_MAIN', branches.length === 1 && branches[0]?.name === 'main', branches.map(item => item.name), ['main']);
add(checks, 'LIVE_NO_PR', pulls.length === 0, pulls.length, 0);
add(checks, 'LIVE_NO_RELEASE', releases.length === 0, releases.length, 0);
add(checks, 'SOURCE_HEAD_UNCHANGED', command(GIT, ['-C', spec.paths.sourceCheckout, 'rev-parse', 'HEAD']) === spec.repository.desiredHead, command(GIT, ['-C', spec.paths.sourceCheckout, 'rev-parse', 'HEAD']), spec.repository.desiredHead);
add(checks, 'SOURCE_WORKTREE_CLEAN', command(GIT, ['-C', spec.paths.sourceCheckout, 'status', '--porcelain=v1']) === '', command(GIT, ['-C', spec.paths.sourceCheckout, 'status', '--porcelain=v1']), '');

const failed = checks.filter(item => !item.pass);
const audit = writeExclusive(auditPath, {
  schemaVersion: 'bfs.repositoryPublicationFailureAudit.v0.2',
  observedAt: new Date().toISOString(),
  status: failed.length === 0 ? 'PASS' : 'FAIL',
  disposition: 'RETAINED_EXPECTED_SERVER_POLICY_FAILURE',
  auditor: {
    path: 'scripts/audit-authorized-film-engine-fork-failure.mjs',
    sha256: sha256File(AUDITOR_PATH),
    importsRunner: false,
  },
  live: {
    repository: metadata.full_name,
    htmlUrl: metadata.html_url,
    fork: metadata.fork,
    parent: metadata.parent?.full_name,
    visibility: metadata.visibility,
    defaultBranch: metadata.default_branch,
    mainOid: liveMain,
    branches: branches.map(item => item.name),
    pullRequestCount: pulls.length,
    releaseCount: releases.length,
  },
  externalMutationCounts: failure.externalMutationCounts,
  checksPassed: checks.length - failed.length,
  checksTotal: checks.length,
  checks,
  failures: failed.map(item => item.id),
  externalMutationsPerformedByAuditor: 0,
  stopRulePreserved: true,
});

process.stdout.write(`${JSON.stringify(audit, null, 2)}\n`);
if (audit.status !== 'PASS') process.exitCode = 1;
