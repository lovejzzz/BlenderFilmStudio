#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, openSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const AUDITOR_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const SPEC_RELATIVE = 'specs/ai-native-studio-repository-publication-c1-execution.v0.4.json';
const RUNNER_RELATIVE = 'scripts/run-film-engine-publication-c1.mjs';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const RUNNER_PATH = resolve(REPOSITORY_ROOT, RUNNER_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, child]) => [key, canonicalize(child)]));
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

function receiptHash(record) {
  const copy = structuredClone(record);
  delete copy.receiptHash;
  return sha256Bytes(canonicalJson(copy));
}

function command(commandPath, args, options = {}) {
  return execFileSync(commandPath, args, {
    cwd: options.cwd,
    encoding: 'utf8',
    env: {
      ...process.env,
      PATH: FROZEN_PATH,
      LANG: 'C',
      LC_ALL: 'C',
      GH_PROMPT_DISABLED: '1',
      GIT_TERMINAL_PROMPT: '0',
      GIT_LFS_SKIP_SMUDGE: '1',
      ...options.env,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    maxBuffer: 512 * 1024 * 1024,
  }).trim();
}

function git(root, args) {
  return command(GIT, ['-C', root, ...args]);
}

function ghJson(args) {
  return JSON.parse(command(GH, args));
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ls-remote line: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function writeExclusive(path, value) {
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

function checkAttributeValues(root, paths) {
  return paths.map(path => {
    const output = git(root, ['check-attr', 'filter', 'diff', 'merge', 'text', '--', path]);
    const values = Object.fromEntries(output.split(/\r?\n/).map(line => {
      const match = line.match(/^(.+): (filter|diff|merge|text): (.+)$/);
      if (!match) throw new Error(`Unexpected attribute output: ${line}`);
      return [match[2], match[3]];
    }));
    return { path, values };
  });
}

function add(checks, id, pass, actual, expected) {
  checks.push({ id, pass: Boolean(pass), actual, expected });
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.evidence.root);
const auditPath = resolve(evidenceRoot, 'audit.json');
if (existsSync(auditPath)) throw new Error(`Audit already exists: ${auditPath}`);

const receiptNames = [
  'preflight.json',
  'construction.json',
  'local-verification.json',
  'lease-recheck.json',
  'main-update.json',
  'remote-verification.json',
  'verdict.json',
];
const receipts = Object.fromEntries(receiptNames.map(name => [name, JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'))]));
const preflight = receipts['preflight.json'];
const construction = receipts['construction.json'];
const localVerification = receipts['local-verification.json'];
const lease = receipts['lease-recheck.json'];
const update = receipts['main-update.json'];
const remoteVerification = receipts['remote-verification.json'];
const verdict = receipts['verdict.json'];
const candidate = construction.candidateCommit;
const candidateBare = resolve(spec.paths.publicationExternalRoot, 'candidate.git');
const localClone = resolve(spec.paths.publicationExternalRoot, 'fresh-local-no-smudge');
const remoteClone = resolve(spec.paths.publicationExternalRoot, 'fresh-remote-no-smudge');
const checks = [];

for (const [name, record] of Object.entries(receipts)) {
  add(checks, `RECEIPT_SELF_HASH_${name}`, record.receiptHash === receiptHash(record), record.receiptHash, 'canonical self hash exact');
}

add(checks, 'PREFLIGHT_ACCEPTED', preflight.status === 'ACCEPTED' && preflight.failures.length === 0, { status: preflight.status, failures: preflight.failures }, { status: 'ACCEPTED', failures: [] });
add(checks, 'CONSTRUCTION_PASS', construction.status === 'PASS', construction.status, 'PASS');
add(checks, 'LOCAL_NO_SMUDGE_PASS', localVerification.status === 'PASS', localVerification.status, 'PASS');
add(checks, 'LEASE_RECHECK_PASS', lease.status === 'PASS', lease.status, 'PASS');
add(checks, 'MAIN_UPDATE_PASS', update.status === 'PASS' && update.exitCode === 0, { status: update.status, exitCode: update.exitCode }, { status: 'PASS', exitCode: 0 });
add(checks, 'REMOTE_NO_SMUDGE_PASS', remoteVerification.status === 'PASS', remoteVerification.status, 'PASS');
add(checks, 'RUNNER_VERDICT_PASS', verdict.status === 'PASS', verdict.status, 'PASS');
add(checks, 'NO_FAILURE_RECEIPT', !existsSync(resolve(evidenceRoot, 'failure.json')), existsSync(resolve(evidenceRoot, 'failure.json')), false);
add(checks, 'SPEC_AUTHORIZED', spec.authorization.granted === true, spec.authorization.granted, true);
add(checks, 'SPEC_SHA_BOUND', preflight.specification.sha256 === sha256File(SPEC_PATH), preflight.specification.sha256, sha256File(SPEC_PATH));
add(checks, 'RUNNER_SHA_BOUND', preflight.specification.runnerSha256 === sha256File(RUNNER_PATH), preflight.specification.runnerSha256, sha256File(RUNNER_PATH));

const parents = git(candidateBare, ['show', '-s', '--format=%P', candidate]).split(/\s+/);
const tree = git(candidateBare, ['rev-parse', `${candidate}^{tree}`]);
const changedPaths = git(candidateBare, ['diff-tree', '--no-commit-id', '--name-only', '-r', spec.source.publicationParent, candidate]).split(/\r?\n/).filter(Boolean).sort();
const expectedPaths = [...spec.publicationCommit.changedPaths].sort();
const reachableCommits = Number(git(candidateBare, ['rev-list', '--count', candidate]));
const candidateMessage = git(candidateBare, ['show', '-s', '--format=%s', candidate]);
add(checks, 'CANDIDATE_ONLY_PARENT', parents.length === 1 && parents[0] === spec.source.publicationParent, parents, [spec.source.publicationParent]);
add(checks, 'CANDIDATE_TREE_BOUND', tree === construction.candidateTree && tree === verdict.publicationTree, tree, construction.candidateTree);
add(checks, 'CANDIDATE_ONLY_THREE_PATHS', changedPaths.length === 3 && changedPaths.join('\n') === expectedPaths.join('\n'), changedPaths, expectedPaths);
add(checks, 'CANDIDATE_REACHABLE_COMMIT_INCREMENT', reachableCommits === spec.source.expectedFullHistoryReachableCommits + 1, reachableCommits, spec.source.expectedFullHistoryReachableCommits + 1);
add(checks, 'CANDIDATE_MESSAGE_EXACT', candidateMessage === spec.source.commitMessage, candidateMessage, spec.source.commitMessage);

const baseAttributes = command(GIT, ['-C', candidateBare, 'show', `${spec.source.publicationParent}:.gitattributes`]);
const candidateAttributes = command(GIT, ['-C', candidateBare, 'show', `${candidate}:.gitattributes`]);
const expectedAttributes = `${baseAttributes}\n${spec.publicationCommit.attributeOverrides.join('\n')}`;
add(checks, 'GITATTRIBUTES_ONLY_APPENDS_OVERRIDES', candidateAttributes === expectedAttributes, sha256Bytes(candidateAttributes), sha256Bytes(expectedAttributes));

for (const item of spec.publicationCommit.ordinaryBlobs) {
  const oid = git(candidateBare, ['rev-parse', `${candidate}:${item.path}`]);
  const parentOid = git(candidateBare, ['rev-parse', `${spec.source.publicationParent}:${item.path}`]);
  const localPath = resolve(localClone, item.path);
  const remotePath = resolve(remoteClone, item.path);
  add(checks, `ORDINARY_OID_${item.path}`, oid === item.gitBlobOidSha1, oid, item.gitBlobOidSha1);
  add(checks, `PARENT_POINTER_OID_${item.path}`, parentOid === item.parentPointerGitBlobOidSha1, parentOid, item.parentPointerGitBlobOidSha1);
  add(checks, `LOCAL_BYTES_${item.path}`, statSync(localPath).size === item.bytes, statSync(localPath).size, item.bytes);
  add(checks, `LOCAL_SHA_${item.path}`, sha256File(localPath) === item.contentSha256, sha256File(localPath), item.contentSha256);
  add(checks, `REMOTE_BYTES_${item.path}`, statSync(remotePath).size === item.bytes, statSync(remotePath).size, item.bytes);
  add(checks, `REMOTE_SHA_${item.path}`, sha256File(remotePath) === item.contentSha256, sha256File(remotePath), item.contentSha256);
}

for (const observation of checkAttributeValues(localClone, spec.publicationCommit.ordinaryBlobs.map(item => item.path))) {
  add(checks, `LOCAL_ATTRIBUTES_UNSET_${observation.path}`, ['filter', 'diff', 'merge', 'text'].every(name => observation.values[name] === 'unset'), observation.values, { filter: 'unset', diff: 'unset', merge: 'unset', text: 'unset' });
}
for (const observation of checkAttributeValues(remoteClone, spec.publicationCommit.ordinaryBlobs.map(item => item.path))) {
  add(checks, `REMOTE_ATTRIBUTES_UNSET_${observation.path}`, ['filter', 'diff', 'merge', 'text'].every(name => observation.values[name] === 'unset'), observation.values, { filter: 'unset', diff: 'unset', merge: 'unset', text: 'unset' });
}

const metadata = ghJson(['api', `repos/${spec.repository.fullName}`]);
const branches = ghJson(['api', `repos/${spec.repository.fullName}/branches?per_page=100`]);
const pulls = ghJson(['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]);
const releases = ghJson(['api', `repos/${spec.repository.fullName}/releases?per_page=100`]);
const liveHeads = parseRemoteRefs(command(GIT, ['ls-remote', '--heads', spec.repository.url]));
const liveTags = parseRemoteRefs(command(GIT, ['ls-remote', '--tags', spec.repository.url]));
const liveMain = liveHeads.find(item => item.ref === 'refs/heads/main')?.oid ?? null;
const apiCommit = ghJson(['api', `repos/${spec.repository.fullName}/git/commits/${candidate}`]);
add(checks, 'LIVE_REPOSITORY_ID', metadata.id === spec.repository.repositoryId && metadata.full_name === spec.repository.fullName, { id: metadata.id, fullName: metadata.full_name }, { id: spec.repository.repositoryId, fullName: spec.repository.fullName });
add(checks, 'LIVE_PUBLIC_FORK_PARENT', metadata.fork === true && metadata.parent?.full_name === spec.repository.forkParent && metadata.private === false && metadata.visibility === 'public', { fork: metadata.fork, parent: metadata.parent?.full_name, private: metadata.private, visibility: metadata.visibility }, { fork: true, parent: spec.repository.forkParent, private: false, visibility: 'public' });
add(checks, 'LIVE_MAIN_CANDIDATE', liveMain === candidate, liveMain, candidate);
add(checks, 'LIVE_SINGLE_MAIN', branches.length === 1 && branches[0]?.name === 'main' && liveHeads.length === 1, { branches: branches.map(item => item.name), refs: liveHeads }, ['main']);
add(checks, 'LIVE_ZERO_TAGS', liveTags.length === 0, liveTags, []);
add(checks, 'LIVE_ZERO_PR_RELEASE', pulls.length === 0 && releases.length === 0, { pullRequests: pulls.length, releases: releases.length }, { pullRequests: 0, releases: 0 });
add(checks, 'LIVE_API_ONLY_PARENT', apiCommit.parents.length === 1 && apiCommit.parents[0]?.sha === spec.source.publicationParent, apiCommit.parents.map(item => item.sha), [spec.source.publicationParent]);
add(checks, 'LIVE_API_TREE', apiCommit.tree.sha === tree, apiCommit.tree.sha, tree);

const expectedPushCommand = [
  GIT,
  '-c', `core.hooksPath=${resolve(spec.paths.publicationExternalRoot, 'empty-hooks')}`,
  '-C', candidateBare,
  'push', '--porcelain',
  spec.remoteUpdate.exactLeaseArgument,
  spec.repository.url,
  `${candidate}:refs/heads/main`,
];
add(checks, 'PUSH_COMMAND_EXACT', JSON.stringify(update.command) === JSON.stringify(expectedPushCommand), update.command, expectedPushCommand);
add(checks, 'PUSH_LEASE_EXACT', update.leaseOid === spec.repository.generatedMainOid && update.destinationRef === 'refs/heads/main', { lease: update.leaseOid, ref: update.destinationRef }, { lease: spec.repository.generatedMainOid, ref: 'refs/heads/main' });
add(checks, 'EMPTY_HOOKS_BOUND', update.prePushHookExecutable === false && update.emptyHooksPath === resolve(spec.paths.publicationExternalRoot, 'empty-hooks'), { executable: update.prePushHookExecutable, path: update.emptyHooksPath }, { executable: false, path: resolve(spec.paths.publicationExternalRoot, 'empty-hooks') });
add(checks, 'NO_EXPLICIT_LFS_COMMAND', update.explicitGitLfsCommands === 0 && verdict.commandLog.every(item => !(item.command.endsWith('/git-lfs') || item.args[0] === 'lfs')), { update: update.explicitGitLfsCommands }, 0);
add(checks, 'ONE_PUSH_ONE_REF_UPDATE', verdict.externalMutationCounts.gitPushAttempts === 1 && verdict.externalMutationCounts.gitRefUpdates === 1, verdict.externalMutationCounts, { gitPushAttempts: 1, gitRefUpdates: 1 });
add(checks, 'ZERO_FORBIDDEN_MUTATIONS', ['repositoryCreates', 'lfsUploads', 'otherRefUpdates', 'tagUpdates', 'releases', 'phaseBMutations', 'deletions', 'recreations', 'renames'].every(name => verdict.externalMutationCounts[name] === 0), verdict.externalMutationCounts, 'all forbidden counters zero');
add(checks, 'UNAUTHORIZED_ACTIONS_EMPTY', verdict.unauthorizedActionsPerformed.length === 0, verdict.unauthorizedActionsPerformed, []);
add(checks, 'STOP_RULE_PRESERVED', verdict.stopRulePreserved === true, verdict.stopRulePreserved, true);

const sourceHead = git(spec.paths.sourceCheckout, ['rev-parse', 'HEAD']);
const sourceStatus = git(spec.paths.sourceCheckout, ['status', '--porcelain=v1']);
const fullHead = git(spec.paths.fullHistorySource, ['rev-parse', 'refs/heads/main']);
add(checks, 'RETAINED_SOURCE_UNCHANGED', sourceHead === spec.source.publicationParent && sourceStatus === '', { head: sourceHead, status: sourceStatus }, { head: spec.source.publicationParent, status: '' });
add(checks, 'RETAINED_FULL_HISTORY_UNCHANGED', fullHead === spec.source.publicationParent, fullHead, spec.source.publicationParent);
add(checks, 'RETAINED_FAILURE_PRESERVED', existsSync(resolve(REPOSITORY_ROOT, spec.evidence.retainedFailureRoot, 'failure.json')) && existsSync(resolve(REPOSITORY_ROOT, spec.evidence.retainedFailureRoot, 'audit-failure.json')), true, true);

const failed = checks.filter(item => !item.pass);
const audit = writeExclusive(auditPath, {
  schemaVersion: 'bfs.repositoryPublicationC1Audit.v0.4',
  observedAt: new Date().toISOString(),
  status: failed.length === 0 ? 'PASS' : 'FAIL',
  auditor: {
    path: 'scripts/audit-film-engine-publication-c1.mjs',
    sha256: sha256File(AUDITOR_PATH),
    importsRunner: false,
  },
  specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  repository: spec.repository.fullName,
  publicationParent: spec.source.publicationParent,
  publicationCommit: candidate,
  publicationTree: tree,
  liveMain,
  checksPassed: checks.length - failed.length,
  checksTotal: checks.length,
  checks,
  failures: failed.map(item => item.id),
  externalMutationCounts: verdict.externalMutationCounts,
  externalMutationsPerformedByAuditor: 0,
  stopRulePreserved: true,
});

process.stdout.write(`${JSON.stringify(audit, null, 2)}\n`);
if (audit.status !== 'PASS') process.exitCode = 1;
