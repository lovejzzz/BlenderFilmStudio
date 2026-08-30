#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { statfsSync } from 'node:fs';
import {
  access,
  open,
  readFile,
  readdir,
  realpath,
} from 'node:fs/promises';
import { resolve } from 'node:path';
import process from 'node:process';

const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const SPEC_RELATIVE = 'specs/ai-native-studio-repository-readiness.v0.2.json';

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

function exec(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: 'utf8',
    env: {
      ...process.env,
      PATH: FROZEN_PATH,
      LANG: 'C',
      LC_ALL: 'C',
      GIT_CONFIG_NOSYSTEM: '1',
      GIT_TERMINAL_PROMPT: '0',
      GIT_LFS_SKIP_SMUDGE: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    maxBuffer: 256 * 1024 * 1024,
  }).trim();
}

function execBuffer(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: null,
    env: {
      ...process.env,
      PATH: FROZEN_PATH,
      LANG: 'C',
      LC_ALL: 'C',
      GIT_CONFIG_NOSYSTEM: '1',
      GIT_TERMINAL_PROMPT: '0',
      GIT_LFS_SKIP_SMUDGE: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    maxBuffer: 256 * 1024 * 1024,
  });
}

function git(root, args) {
  return exec('/usr/bin/git', ['-C', root, ...args]);
}

function gitBuffer(root, args) {
  return execBuffer('/usr/bin/git', ['-C', root, ...args]);
}

function treeBytes(path) {
  return Number(exec('/usr/bin/du', ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function freeBytes(path) {
  const stats = statfsSync(path, { bigint: true });
  return stats.bavail * stats.bsize;
}

function receiptHash(record) {
  const unhashed = structuredClone(record);
  delete unhashed.receiptHash;
  return sha256Bytes(canonicalJson(unhashed));
}

async function readHashedJson(path) {
  const record = JSON.parse(await readFile(path, 'utf8'));
  return {
    record,
    fileSha256: await sha256File(path),
    receiptHashValid: typeof record.receiptHash === 'string' && receiptHash(record) === record.receiptHash,
  };
}

async function writeAuditExclusive(path, value) {
  const record = structuredClone(value);
  record.receiptHash = receiptHash(record);
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return record;
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
  const matches = [];
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    for (const [pattern, regex] of patterns) {
      regex.lastIndex = 0;
      if (regex.test(lines[index])) matches.push({ pattern, path, line: index + 1 });
    }
  }
  return matches;
}

async function listFiles(root, current = root) {
  const output = [];
  for (const entry of await readdir(current, { withFileTypes: true })) {
    const path = resolve(current, entry.name);
    if (entry.isSymbolicLink()) {
      output.push({ path, type: 'symlink' });
    } else if (entry.isDirectory()) {
      output.push(...await listFiles(root, path));
    } else if (entry.isFile()) {
      output.push({ path, type: 'file' });
    } else {
      output.push({ path, type: 'other' });
    }
  }
  return output;
}

function addCheck(checks, id, passed, observed, expected) {
  checks.push({ id, passed: Boolean(passed), observed, expected });
}

async function main() {
  const repositoryRoot = exec('/usr/bin/git', ['rev-parse', '--show-toplevel'], process.cwd());
  const spec = JSON.parse(await readFile(resolve(repositoryRoot, SPEC_RELATIVE), 'utf8'));
  const evidenceRoot = await realpath(resolve(repositoryRoot, spec.paths.evidenceRoot));
  const sourceRoot = await realpath(spec.paths.sourceRoot);
  const mirrorRoot = await realpath(spec.paths.fullMirror);
  const destinationRoot = await realpath(spec.paths.localDestination);
  const auditPath = resolve(evidenceRoot, 'audit.json');
  if (await exists(auditPath)) throw new Error('AUDIT_FILE_ALREADY_EXISTS');

  const requiredFiles = [
    'admission.json',
    'source-inventory.json',
    'local-rehearsal.json',
    'negative-controls.json',
    'network-and-mutation-log.json',
    'verdict.json',
  ];
  const records = {};
  for (const file of requiredFiles) records[file] = await readHashedJson(resolve(evidenceRoot, file));
  const admission = records['admission.json'].record;
  const inventory = records['source-inventory.json'].record;
  const rehearsal = records['local-rehearsal.json'].record;
  const negative = records['negative-controls.json'].record;
  const network = records['network-and-mutation-log.json'].record;
  const verdict = records['verdict.json'].record;
  const checks = [];

  for (const file of requiredFiles) {
    addCheck(checks, `receipt-hash:${file}`, records[file].receiptHashValid, records[file].record.receiptHash, 'canonical receipt hash recomputes');
  }
  addCheck(checks, 'admission-status', admission.status === 'ACCEPTED', admission.status, 'ACCEPTED');
  addCheck(checks, 'runner-verdict-status', verdict.status === 'PASS', verdict.status, 'PASS');
  addCheck(checks, 'runner-claim', verdict.claim === 'NO_EXTERNAL_WRITE_REPOSITORY_READINESS_REHEARSAL_SUPPORTED', verdict.claim, 'NO_EXTERNAL_WRITE_REPOSITORY_READINESS_REHEARSAL_SUPPORTED');

  const retainedFailurePath = resolve(repositoryRoot, spec.correction.retainedAttempt01EvidenceRoot, 'failure.json');
  const retainedInventoryPath = resolve(repositoryRoot, spec.correction.retainedAttempt01EvidenceRoot, 'source-inventory.json');
  const retainedFailure = await readHashedJson(retainedFailurePath);
  const retainedInventory = await readHashedJson(retainedInventoryPath);
  addCheck(checks, 'retained-failure-file-hash', retainedFailure.fileSha256 === spec.correction.retainedFailureFileSha256, retainedFailure.fileSha256, spec.correction.retainedFailureFileSha256);
  addCheck(checks, 'retained-failure-receipt-hash', retainedFailure.record.receiptHash === spec.correction.retainedFailureReceiptHash && retainedFailure.receiptHashValid, retainedFailure.record.receiptHash, spec.correction.retainedFailureReceiptHash);
  addCheck(checks, 'retained-inventory-receipt-hash', retainedInventory.record.receiptHash === spec.correction.retainedSourceInventoryReceiptHash && retainedInventory.receiptHashValid, retainedInventory.record.receiptHash, spec.correction.retainedSourceInventoryReceiptHash);
  addCheck(checks, 'retained-bundle-hash', await sha256File(spec.paths.retainedBundle) === spec.correction.retainedBundleSha256, await sha256File(spec.paths.retainedBundle), spec.correction.retainedBundleSha256);
  const retainedMirrorShallow = git(spec.paths.retainedFullMirror, ['rev-parse', '--is-shallow-repository']) === 'true';
  const retainedMirrorOrigin = git(spec.paths.retainedFullMirror, ['remote', 'get-url', 'origin']);
  addCheck(checks, 'retained-mirror-not-shallow', !retainedMirrorShallow, retainedMirrorShallow, false);
  addCheck(checks, 'retained-mirror-origin', retainedMirrorOrigin === spec.network.readOnlyFullHistorySource, retainedMirrorOrigin, spec.network.readOnlyFullHistorySource);

  const sourceHead = git(sourceRoot, ['rev-parse', 'HEAD']);
  const sourceTree = git(sourceRoot, ['rev-parse', 'HEAD^{tree}']);
  const sourceTreeListingSha256 = sha256Bytes(gitBuffer(sourceRoot, ['ls-tree', '-r', '-z', 'HEAD']));
  const sourceParents = git(sourceRoot, ['show', '-s', '--format=%P', 'HEAD']);
  const sourceShallow = git(sourceRoot, ['rev-parse', '--is-shallow-repository']) === 'true';
  const sourceCommitCount = Number(git(sourceRoot, ['rev-list', '--count', 'HEAD']));
  const sourceStatus = git(sourceRoot, ['status', '--porcelain=v1']);
  addCheck(checks, 'source-head', sourceHead === spec.bindings.sourceHead, sourceHead, spec.bindings.sourceHead);
  addCheck(checks, 'source-tree', sourceTree === spec.bindings.sourceTree, sourceTree, spec.bindings.sourceTree);
  addCheck(checks, 'source-tree-listing', sourceTreeListingSha256 === spec.bindings.sourceTreeListingSha256, sourceTreeListingSha256, spec.bindings.sourceTreeListingSha256);
  addCheck(checks, 'source-parents', sourceParents === `${spec.bindings.forkParent} ${spec.bindings.upstreamTarget}`, sourceParents, `${spec.bindings.forkParent} ${spec.bindings.upstreamTarget}`);
  addCheck(checks, 'source-clean', sourceStatus === '', sourceStatus || '<clean>', '<clean>');
  addCheck(checks, 'source-is-shallow', sourceShallow, sourceShallow, true);
  addCheck(checks, 'source-shallow-count', sourceCommitCount === spec.expectedInventory.currentCheckoutReachableCommitCount, sourceCommitCount, spec.expectedInventory.currentCheckoutReachableCommitCount);

  const copyingSha256 = await sha256File(resolve(sourceRoot, 'COPYING'));
  const assetsLicenseSha256 = await sha256File(resolve(sourceRoot, 'assets', 'LICENSE'));
  addCheck(checks, 'copying-hash', copyingSha256 === spec.bindings.copyingSha256, copyingSha256, spec.bindings.copyingSha256);
  addCheck(checks, 'assets-license-hash', assetsLicenseSha256 === spec.bindings.assetsLicenseSha256, assetsLicenseSha256, spec.bindings.assetsLicenseSha256);

  const lfs = JSON.parse(git(sourceRoot, ['lfs', 'ls-files', '--json']));
  const lfsBytes = lfs.files.reduce((sum, file) => sum + file.size, 0);
  const lfsLargest = Math.max(...lfs.files.map(file => file.size));
  addCheck(checks, 'lfs-count', lfs.files.length === spec.expectedInventory.headLfsPathCount, lfs.files.length, spec.expectedInventory.headLfsPathCount);
  addCheck(checks, 'lfs-bytes', lfsBytes === spec.expectedInventory.headLfsBytes, lfsBytes, spec.expectedInventory.headLfsBytes);
  addCheck(checks, 'lfs-largest', lfsLargest === spec.expectedInventory.headLargestLfsObjectBytes, lfsLargest, spec.expectedInventory.headLargestLfsObjectBytes);
  addCheck(checks, 'lfs-all-local', lfs.files.every(file => file.downloaded), lfs.files.filter(file => file.downloaded).length, lfs.files.length);

  const largestBlob = parseLargestBlob(git(sourceRoot, ['ls-tree', '-rl', 'HEAD']));
  addCheck(checks, 'ordinary-blob-exact', largestBlob.bytes === spec.expectedInventory.headLargestOrdinaryBlobBytes, largestBlob.bytes, spec.expectedInventory.headLargestOrdinaryBlobBytes);
  addCheck(checks, 'ordinary-blob-below-100-mib', largestBlob.bytes < spec.acceptance.maximumOrdinaryBlobBytesExclusive, largestBlob.bytes, `<${spec.acceptance.maximumOrdinaryBlobBytesExclusive}`);

  const changedPaths = git(sourceRoot, ['diff', '--name-only', spec.bindings.upstreamTarget, spec.bindings.sourceHead]).split(/\r?\n/).filter(Boolean);
  const forkCommits = git(sourceRoot, ['rev-list', `${spec.bindings.upstreamTarget}..${spec.bindings.sourceHead}`]).split(/\r?\n/).filter(Boolean);
  const diffShort = git(sourceRoot, ['diff', '--shortstat', spec.bindings.upstreamTarget, spec.bindings.sourceHead]);
  const diffMatch = diffShort.match(/(\d+) files? changed, (\d+) insertions?\(\+\), (\d+) deletions?\(-\)/);
  addCheck(checks, 'fork-commit-count', forkCommits.length === spec.expectedInventory.forkOnlyCommitCount, forkCommits.length, spec.expectedInventory.forkOnlyCommitCount);
  addCheck(checks, 'fork-path-count', changedPaths.length === spec.expectedInventory.forkChangedPathCount, changedPaths.length, spec.expectedInventory.forkChangedPathCount);
  addCheck(checks, 'fork-shortstat-parsed', Boolean(diffMatch), diffShort, 'parseable exact shortstat');
  if (diffMatch) {
    const changedLines = Number(diffMatch[2]) + Number(diffMatch[3]);
    addCheck(checks, 'fork-lines-exact', changedLines === spec.expectedInventory.forkChangedLines, changedLines, spec.expectedInventory.forkChangedLines);
    addCheck(checks, 'fork-lines-within-ceiling', changedLines <= spec.acceptance.maximumForkNonGeneratedChangedLines, changedLines, `<=${spec.acceptance.maximumForkNonGeneratedChangedLines}`);
  }
  const secretFindings = [];
  for (const path of changedPaths) {
    const content = gitBuffer(sourceRoot, ['show', `${spec.bindings.sourceHead}:${path}`]);
    if (!content.includes(0)) secretFindings.push(...secretMatchesForText(content.toString('utf8'), path));
  }
  addCheck(checks, 'independent-fork-secret-scan', secretFindings.length === 0, secretFindings, []);
  addCheck(checks, 'runner-fork-secret-scan', inventory.source.secretScan.findingCount === 0, inventory.source.secretScan.findingCount, 0);

  const mirrorShallow = git(mirrorRoot, ['rev-parse', '--is-shallow-repository']) === 'true';
  const mirrorOrigin = git(mirrorRoot, ['remote', 'get-url', 'origin']);
  const candidateRef = rehearsal.candidate.ref;
  const mirrorCandidateHead = git(mirrorRoot, ['rev-parse', candidateRef]);
  const mirrorCandidateTree = git(mirrorRoot, ['rev-parse', `${candidateRef}^{tree}`]);
  addCheck(checks, 'mirror-not-shallow', !mirrorShallow, mirrorShallow, false);
  addCheck(checks, 'mirror-origin-exact', mirrorOrigin === spec.network.readOnlyFullHistorySource, mirrorOrigin, spec.network.readOnlyFullHistorySource);
  addCheck(checks, 'mirror-candidate-head', mirrorCandidateHead === spec.bindings.sourceHead, mirrorCandidateHead, spec.bindings.sourceHead);
  addCheck(checks, 'mirror-candidate-tree', mirrorCandidateTree === spec.bindings.sourceTree, mirrorCandidateTree, spec.bindings.sourceTree);
  addCheck(checks, 'mirror-target-present', git(mirrorRoot, ['cat-file', '-t', spec.bindings.upstreamTarget]) === 'commit', spec.bindings.upstreamTarget, 'commit exists');
  addCheck(checks, 'attempt02-mirror-mode', rehearsal.clone.mode === 'RETAINED_FULL_MIRROR_LOCAL_CLONE', rehearsal.clone.mode, 'RETAINED_FULL_MIRROR_LOCAL_CLONE');
  addCheck(checks, 'attempt02-mirror-source', rehearsal.clone.source === spec.paths.retainedFullMirror, rehearsal.clone.source, spec.paths.retainedFullMirror);
  addCheck(checks, 'attempt02-bundle-matches-retained', rehearsal.bundle.sha256 === spec.correction.retainedBundleSha256, rehearsal.bundle.sha256, spec.correction.retainedBundleSha256);

  const destinationHead = git(destinationRoot, ['rev-parse', 'refs/heads/main']);
  const destinationTree = git(destinationRoot, ['rev-parse', 'refs/heads/main^{tree}']);
  const destinationTreeListingSha256 = sha256Bytes(gitBuffer(destinationRoot, ['ls-tree', '-r', '-z', 'refs/heads/main']));
  const destinationShallow = git(destinationRoot, ['rev-parse', '--is-shallow-repository']) === 'true';
  const destinationCommitCount = Number(git(destinationRoot, ['rev-list', '--count', 'refs/heads/main']));
  const destinationForkCount = Number(git(destinationRoot, ['rev-list', '--count', `${spec.bindings.upstreamTarget}..refs/heads/main`]));
  const destinationMergeBase = git(destinationRoot, ['merge-base', spec.bindings.upstreamTarget, 'refs/heads/main']);
  const fsck = git(destinationRoot, ['fsck', '--full', '--no-dangling']);
  addCheck(checks, 'destination-not-shallow', !destinationShallow, destinationShallow, false);
  addCheck(checks, 'destination-head', destinationHead === spec.bindings.sourceHead, destinationHead, spec.bindings.sourceHead);
  addCheck(checks, 'destination-tree', destinationTree === spec.bindings.sourceTree, destinationTree, spec.bindings.sourceTree);
  addCheck(checks, 'destination-tree-listing', destinationTreeListingSha256 === spec.bindings.sourceTreeListingSha256, destinationTreeListingSha256, spec.bindings.sourceTreeListingSha256);
  addCheck(checks, 'destination-history-fuller-than-shallow', destinationCommitCount > spec.expectedInventory.currentCheckoutReachableCommitCount, destinationCommitCount, `>${spec.expectedInventory.currentCheckoutReachableCommitCount}`);
  addCheck(checks, 'destination-fork-count', destinationForkCount === spec.expectedInventory.forkOnlyCommitCount, destinationForkCount, spec.expectedInventory.forkOnlyCommitCount);
  addCheck(checks, 'destination-merge-base', destinationMergeBase === spec.bindings.upstreamTarget, destinationMergeBase, spec.bindings.upstreamTarget);
  addCheck(checks, 'destination-fsck', fsck === '', fsck || '<clean>', '<clean>');

  const externalBytes = treeBytes(spec.paths.externalRehearsalRoot);
  const evidenceBytesBeforeAudit = treeBytes(evidenceRoot);
  addCheck(checks, 'external-size-ceiling', externalBytes <= spec.acceptance.maximumExternalRehearsalBytes, externalBytes, `<=${spec.acceptance.maximumExternalRehearsalBytes}`);
  addCheck(checks, 'evidence-size-ceiling', evidenceBytesBeforeAudit <= spec.acceptance.maximumResearchEvidenceBytes, evidenceBytesBeforeAudit, `<=${spec.acceptance.maximumResearchEvidenceBytes}`);
  addCheck(checks, 'free-space-reserve', freeBytes(spec.paths.externalRehearsalRoot) >= 100n * (1024n ** 3n), freeBytes(spec.paths.externalRehearsalRoot).toString(), '>=' + (100n * (1024n ** 3n)).toString());

  const rootFiles = await listFiles(evidenceRoot);
  addCheck(checks, 'evidence-no-symlinks', rootFiles.every(item => item.type === 'file'), rootFiles.filter(item => item.type !== 'file'), []);
  const expectedControlIds = spec.acceptance.requiredNegativeControls;
  const controlIds = negative.controls.map(control => control.id);
  addCheck(checks, 'negative-control-roster', JSON.stringify(controlIds) === JSON.stringify(expectedControlIds), controlIds, expectedControlIds);
  addCheck(checks, 'negative-controls-all-pass', negative.controls.every(control => control.passed && !control.accepted), negative.controls.map(control => ({ id: control.id, passed: control.passed, accepted: control.accepted })), 'all passed and rejected');

  const counters = network.counters;
  const expectedZeros = {
    externalRepositoryCreates: spec.acceptance.externalRepositoryCreates,
    externalGitPushes: spec.acceptance.externalGitPushes,
    lfsUploads: spec.acceptance.lfsUploads,
    phaseBMutations: spec.acceptance.phaseBMutations,
    dmgDistributions: spec.acceptance.dmgDistributions,
    credentialMaterialReadsOrEmissions: spec.acceptance.credentialReads,
    blenderStarts: spec.acceptance.blenderStarts,
    renders: spec.acceptance.renders,
    modelCalls: spec.acceptance.modelCalls,
  };
  for (const [key, expected] of Object.entries(expectedZeros)) addCheck(checks, `counter:${key}`, counters[key] === expected, counters[key], expected);
  addCheck(checks, 'one-local-file-push', counters.localFilePushes === 1, counters.localFilePushes, 1);
  addCheck(checks, 'no-second-network-mirror', counters.readOnlyFullMirrorClones === spec.network.expectedReadOnlyFullMirrorClones, counters.readOnlyFullMirrorClones, spec.network.expectedReadOnlyFullMirrorClones);
  addCheck(checks, 'one-retained-local-mirror', counters.retainedFullMirrorLocalClones === spec.network.expectedRetainedFullMirrorLocalClones, counters.retainedFullMirrorLocalClones, spec.network.expectedRetainedFullMirrorLocalClones);
  addCheck(checks, 'commands-no-external-mutation', network.commands.every(command => command.externalMutation === false), network.commands.filter(command => command.externalMutation), []);
  const flattenedCommands = network.commands.map(command => command.command.join(' ')).join('\n');
  const forbiddenCommand = /\b(?:repo create|lfs push|push --mirror|api .*\/forks|curl .*--request\s+(?:POST|PUT|PATCH|DELETE))\b/i;
  addCheck(checks, 'commands-no-write-primitive', !forbiddenCommand.test(flattenedCommands), flattenedCommands, 'no external write primitive');
  const localPush = network.commands.find(command => command.operation === 'push exact candidate to local file destination');
  addCheck(checks, 'local-push-command-present', Boolean(localPush), Boolean(localPush), true);
  if (localPush) {
    const destinationArgument = localPush.command.find(argument => argument.startsWith('file://'));
    addCheck(checks, 'local-push-file-protocol', Boolean(destinationArgument), destinationArgument ?? null, 'file:// destination');
    addCheck(checks, 'local-push-no-credentials', destinationArgument && !/@/.test(destinationArgument), destinationArgument ?? null, 'no @ credential component');
  }

  for (const binding of verdict.evidenceBindings) {
    const observed = records[binding.file];
    addCheck(checks, `verdict-binding-file:${binding.file}`, Boolean(observed) && observed.fileSha256 === binding.fileSha256, observed?.fileSha256 ?? null, binding.fileSha256);
    addCheck(checks, `verdict-binding-receipt:${binding.file}`, Boolean(observed) && observed.record.receiptHash === binding.receiptHash, observed?.record.receiptHash ?? null, binding.receiptHash);
  }
  addCheck(checks, 'public-fork-status', verdict.topologyVerdicts.PUBLIC_GITHUB_FORK === 'READY_FOR_EXPLICIT_AUTHORIZATION', verdict.topologyVerdicts.PUBLIC_GITHUB_FORK, 'READY_FOR_EXPLICIT_AUTHORIZATION');
  addCheck(checks, 'private-mirror-remains-blocked', verdict.topologyVerdicts.PRIVATE_STANDALONE_MIRROR === 'BLOCKED_PENDING_OWNER_VISIBILITY_LFS_COST_AND_FULL_LFS_TRANSFER_AUTHORIZATION', verdict.topologyVerdicts.PRIVATE_STANDALONE_MIRROR, 'BLOCKED_PENDING_OWNER_VISIBILITY_LFS_COST_AND_FULL_LFS_TRANSFER_AUTHORIZATION');
  addCheck(checks, 'all-authorizations-still-false', Object.values(verdict.authorizationStillFalse).every(value => value === false), verdict.authorizationStillFalse, 'all false');

  const failed = checks.filter(check => !check.passed);
  const audit = await writeAuditExclusive(auditPath, {
    schemaVersion: 'bfs.repositoryReadinessIndependentAudit.v0.1',
    observedAt: new Date().toISOString(),
    status: failed.length === 0 ? 'PASS' : 'FAIL',
    independence: {
      importsRunner: false,
      trustsRunnerCheckBooleans: false,
      recomputesSourceGitAndLfs: true,
      recomputesMirrorAndDestinationGit: true,
      rerunsFsck: true,
    },
    checksPassed: checks.length - failed.length,
    checksFailed: failed.length,
    checks,
    externalRehearsalBytes: externalBytes,
    evidenceBytesBeforeAudit,
    topologyVerdicts: {
      PUBLIC_GITHUB_FORK: failed.length === 0 ? 'READY_FOR_EXPLICIT_AUTHORIZATION' : 'REJECTED_BY_INDEPENDENT_AUDIT',
      PRIVATE_STANDALONE_MIRROR: 'BLOCKED_PENDING_OWNER_VISIBILITY_LFS_COST_AND_FULL_LFS_TRANSFER_AUTHORIZATION',
    },
    claimCeiling: spec.claimCeiling,
  });
  process.stdout.write(`REPOSITORY_READINESS_AUDIT_${audit.status} checks=${audit.checksPassed}/${checks.length} receiptHash=${audit.receiptHash}\n`);
  if (audit.status !== 'PASS') process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
