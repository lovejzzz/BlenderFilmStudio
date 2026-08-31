#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, lstatSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const DU = '/usr/bin/du';
const AUDITOR_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const SPEC_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-execution.v0.3.json';
const RUNNER_RELATIVE = 'scripts/run-ai-native-studio-pb1-validation-only.mjs';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const RUNNER_PATH = resolve(REPOSITORY_ROOT, RUNNER_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)]));
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
  try { writeFileSync(descriptor, `${JSON.stringify(record, null, 2)}\n`); } finally { closeSync(descriptor); }
  return record;
}

function result(command, args, options = {}) {
  try {
    const stdout = execFileSync(command, args, {
      encoding: 'utf8',
      env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C', GH_PROMPT_DISABLED: '1', GIT_TERMINAL_PROMPT: '0', GIT_LFS_SKIP_SMUDGE: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: options.timeout ?? 20 * 60 * 1000,
      maxBuffer: 512 * 1024 * 1024,
    });
    return { exitCode: 0, stdout, stderr: '' };
  } catch (error) {
    return { exitCode: Number.isInteger(error.status) ? error.status : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? String(error.message ?? error) };
  }
}

function command(commandPath, args, options = {}) {
  const observed = result(commandPath, args, options);
  if (observed.exitCode !== 0) throw new Error(`Audit command failed: ${commandPath} ${args.join(' ')}\n${observed.stderr}`);
  return observed.stdout.trim();
}

function git(root, args, options = {}) {
  return command(GIT, ['-C', root, ...args], options);
}

function treeBytes(path) {
  if (!existsSync(path)) return 0;
  return Number(command(DU, ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function storageIdentity(root) {
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute, { bigint: true });
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) walk(absolute, relativePath);
      else if (item.isFile()) records.push(`${relativePath}\0${item.size}\0${item.mtimeNs}`);
    }
  }
  walk(root);
  return {
    state: 'PRESENT',
    files: records.length,
    bytes: records.reduce((sum, line) => sum + Number(line.split('\0')[1]), 0),
    manifestSha256: sha256Bytes(`${records.join('\n')}\n`),
  };
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected remote ref: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function collectRemote(spec) {
  const metadata = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}`]));
  const branches = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/branches?per_page=100`]));
  const pulls = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]));
  const releases = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/releases?per_page=100`]));
  const heads = parseRemoteRefs(command(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRemoteRefs(command(GIT, ['ls-remote', '--tags', spec.repository.url]));
  return {
    id: metadata.id,
    fullName: metadata.full_name,
    fork: metadata.fork,
    parent: metadata.parent?.full_name ?? null,
    visibility: metadata.visibility,
    private: metadata.private,
    branches: branches.map(item => item.name).sort(),
    heads,
    tags,
    main: heads.find(item => item.ref === 'refs/heads/main')?.oid ?? null,
    pullRequests: pulls.length,
    releases: releases.length,
  };
}

function add(checks, id, pass, observed = null, expected = true) {
  checks.push({ id, pass: Boolean(pass), observed, expected });
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
const source = spec.paths.sourceRoot;
const auditPath = resolve(evidenceRoot, 'audit-failure.json');
if (existsSync(auditPath)) throw new Error(`Failure audit already exists: ${auditPath}`);

const names = ['preflight.json', 'negative-controls.json', 'remote-and-history.json', 'failure.json', 'verdict.json'];
const receipts = Object.fromEntries(names.map(name => [name, JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'))]));
const preflight = receipts['preflight.json'];
const history = receipts['remote-and-history.json'];
const failure = receipts['failure.json'];
const verdict = receipts['verdict.json'];
const checks = [];

add(checks, 'AUDITOR_DOES_NOT_IMPORT_RUNNER', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`));
for (const [name, receipt] of Object.entries(receipts)) add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt), receipt.receiptHash, receiptHash(receipt));
add(checks, 'PREFLIGHT_ACCEPTED', preflight.status === 'ACCEPTED');
add(checks, 'NEGATIVE_CONTROLS_9_OF_9', receipts['negative-controls.json'].checksPassed === 9 && receipts['negative-controls.json'].controls.every(item => item.pass));
add(checks, 'EXPECTED_FAILED_STAGE', failure.failedStage === 'HISTORY_AND_SOURCE_IDENTITY', failure.failedStage, 'HISTORY_AND_SOURCE_IDENTITY');
add(checks, 'FAILURE_AND_VERDICT_FAIL', failure.status === 'FAIL' && verdict.status === 'FAIL');
add(checks, 'FAILURE_CROSS_BOUND', verdict.failureReceiptHash === failure.receiptHash, verdict.failureReceiptHash, failure.receiptHash);
add(checks, 'ONLY_F0_STAT_CHECK_FAILED', Object.entries(history.checks).filter(([, pass]) => !pass).map(([name]) => name).join('\n') === 'f0PatchExact', history.checks, 'only f0PatchExact=false');
add(checks, 'ALL_GRAPH_IDENTITIES_PASS', ['headExact', 'treeExact', 'soleParentExact', 'nonShallow', 'reachableCommitCountExact', 'mergeBaseExact', 'forkCommitCountExact', 'fullFsckPass', 'c1PathsExact', 'publicationPatchExact'].every(name => history.checks[name] === true));
add(checks, 'OBSERVED_ATTR_CONTEXT_F0_STATS', history.history.f0Diff.changedPaths === 16 && history.history.f0Diff.additions === 837 && history.history.f0Diff.deletions === 64 && history.history.f0Diff.binaryPaths === 2, history.history.f0Diff, { changedPaths: 16, additions: 837, deletions: 64, binaryPaths: 2 });

const freshAttrs = spec.sourceIdentity.ordinaryBrandBlobs.map(item => git(source, ['check-attr', 'filter', 'diff', 'merge', 'text', '--', item.path]));
const retainedSource = resolve(spec.dependency.retainedCheckout, '..', '..');
const retainedAttrs = spec.sourceIdentity.ordinaryBrandBlobs.map(item => git(retainedSource, ['check-attr', 'filter', 'diff', 'merge', 'text', '--', item.path]));
const retainedNumstat = git(retainedSource, ['diff', '--numstat', `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`]);
const retainedAssetStats = retainedNumstat.split(/\r?\n/).filter(line => spec.sourceIdentity.ordinaryBrandBlobs.some(item => line.endsWith(`\t${item.path}`)));
add(checks, 'C1_WORKTREE_ATTRIBUTES_UNSET', freshAttrs.every(block => block.split(/\r?\n/).every(line => line.endsWith(': unset'))), freshAttrs, 'all unset');
add(checks, 'RETAINED_F0_ATTRIBUTES_LFS', retainedAttrs.every(block => block.includes(': filter: lfs') && block.includes(': diff: lfs')), retainedAttrs, 'filter/diff lfs');
add(checks, 'RETAINED_F0_ASSETS_COUNT_AS_POINTER_TEXT', retainedAssetStats.every(line => line.startsWith('2\t2\t')) && retainedAssetStats.length === 2, retainedAssetStats, ['2/2 icon', '2/2 splash']);
add(checks, 'METRIC_DIFFERENCE_EXACTLY_FOUR_FOUR', 841 - history.history.f0Diff.additions === 4 && 68 - history.history.f0Diff.deletions === 4);
add(checks, 'PUBLICATION_PATCH_STATS_STILL_EXACT', history.history.headDiff.changedPaths === 17 && history.history.headDiff.additions === 839 && history.history.headDiff.deletions === 64 && history.history.headDiff.binaryPaths === 2);

const fsck = result(GIT, ['-C', source, 'fsck', '--full', '--strict']);
add(checks, 'SOURCE_HEAD_EXACT', git(source, ['rev-parse', 'HEAD']) === spec.publicationBaseline.head);
add(checks, 'SOURCE_TREE_EXACT', git(source, ['rev-parse', 'HEAD^{tree}']) === spec.publicationBaseline.tree);
add(checks, 'SOURCE_CLEAN', git(source, ['status', '--porcelain=v1']) === '');
add(checks, 'SOURCE_NON_SHALLOW', git(source, ['rev-parse', '--is-shallow-repository']) === 'false');
add(checks, 'SOURCE_REACHABLE_EXACT', Number(git(source, ['rev-list', '--count', 'HEAD'])) === spec.publicationBaseline.reachableCommitCount);
add(checks, 'SOURCE_FSCK_PASS', fsck.exitCode === 0, fsck.stderr, '');

const lfsFiles = JSON.parse(git(source, ['lfs', 'ls-files', '--json'])).files;
let lfsBytes = 0;
const lfsMismatches = [];
for (const item of lfsFiles) {
  const path = resolve(source, item.name);
  if (!existsSync(path)) { lfsMismatches.push(item.name); continue; }
  const bytes = statSync(path).size;
  lfsBytes += bytes;
  if (bytes !== item.size || sha256File(path) !== item.oid) lfsMismatches.push(item.name);
}
add(checks, 'LOCAL_LFS_COUNT_EXACT', lfsFiles.length === spec.sourceIdentity.lfs.trackedPathsAtPublicationHead, lfsFiles.length, spec.sourceIdentity.lfs.trackedPathsAtPublicationHead);
add(checks, 'LOCAL_LFS_BYTES_EXACT', lfsBytes === spec.sourceIdentity.lfs.contentBytesAtPublicationHead, lfsBytes, spec.sourceIdentity.lfs.contentBytesAtPublicationHead);
add(checks, 'LOCAL_LFS_MATERIALIZED_HASHES_EXACT', lfsMismatches.length === 0 && lfsFiles.every(item => item.downloaded && item.checkout), lfsMismatches, []);
const retainedLfsStorage = resolve(retainedSource, '.git', 'lfs');
add(checks, 'RETAINED_LFS_STORAGE_UNCHANGED', canonicalJson(storageIdentity(retainedLfsStorage)) === canonicalJson(preflight.retainedSource.lfsStorageIdentity), storageIdentity(retainedLfsStorage), preflight.retainedSource.lfsStorageIdentity);

const remote = collectRemote(spec);
add(checks, 'LIVE_PUBLIC_FORK_EXACT', remote.id === spec.repository.repositoryId && remote.fullName === spec.repository.fullName && remote.fork && remote.parent === spec.repository.forkParent && remote.visibility === 'public' && !remote.private, remote, 'exact public fork');
add(checks, 'LIVE_MAIN_UNCHANGED', remote.main === spec.publicationBaseline.head, remote.main, spec.publicationBaseline.head);
add(checks, 'LIVE_ONLY_MAIN_ZERO_TAG_PR_RELEASE', remote.branches.join('\n') === 'main' && remote.heads.length === 1 && remote.tags.length === 0 && remote.pullRequests === 0 && remote.releases === 0);

add(checks, 'ONE_PUBLIC_CLONE_ONE_LOCAL_MATERIALIZATION', failure.counters.publicEngineNetworkClones === 1 && failure.counters.localLfsMaterializations === 1, failure.counters, { publicEngineNetworkClones: 1, localLfsMaterializations: 1 });
add(checks, 'ZERO_DEPENDENCY_BUILD_START_RENDER', ['localDependencyClones', 'cleanNativeArm64Builds', 'productStarts', 'renderCalls'].every(name => failure.counters[name] === 0), failure.counters, 'all zero');
add(checks, 'ZERO_FORBIDDEN_EXTERNAL_MUTATIONS', ['engineRemoteWrites', 'engineRefUpdates', 'lfsNetworkDownloads', 'lfsUploads', 'releases', 'signingOperations', 'notarizationOperations', 'dmgOperations', 'pb2ThroughPb7Mutations', 'modelCalls'].every(name => failure.counters[name] === 0), failure.counters, 'all zero');
add(checks, 'DEPENDENCY_TARGET_UNPOPULATED', !existsSync(resolve(source, 'lib', 'macos_arm64')) || readdirSync(resolve(source, 'lib', 'macos_arm64')).length === 0);
add(checks, 'BUILD_ROOT_ABSENT', !existsSync(spec.paths.buildRoot));
add(checks, 'RUNTIME_HOME_ABSENT', !existsSync(spec.paths.isolatedHome));
add(checks, 'EXTERNAL_ROOT_WITHIN_CEILING', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumExternalRootBytes, treeBytes(spec.paths.externalRoot), spec.resources.maximumExternalRootBytes);
add(checks, 'EVIDENCE_WITHIN_CEILING', treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes, treeBytes(evidenceRoot), spec.resources.maximumEvidenceRootBytes);
add(checks, 'RUNNER_HAS_NO_ENGINE_PUSH_COMMAND', !/["']push["']/.test(readFileSync(RUNNER_PATH, 'utf8')));
add(checks, 'STOP_RULE_PRESERVED', failure.stopRulePreserved === true && verdict.stopRulePreserved === true);

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyFailureAudit.v0.3',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY',
  observedAt: new Date().toISOString(),
  status: failed.length === 0 ? 'PASS' : 'FAIL',
  classification: 'RETAINED_HARNESS_METRIC_FAILURE_BEFORE_DEPENDENCY_BUILD_OR_PRODUCT_START',
  rootCause: 'C1 exact-path -diff/-text overrides make the two former LFS pointer paths binary under the publication worktree attribute context, so the F0 parent range reports 837/64 plus two binary paths instead of retained F0-context 841/68. All commit/tree/path/full-history and publication-head identities remain exact.',
  auditor: { path: 'scripts/audit-ai-native-studio-pb1-validation-only-failure.mjs', sha256: sha256File(AUDITOR_PATH), importsRunner: false },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
  failureReceiptHash: failure.receiptHash,
  verdictReceiptHash: verdict.receiptHash,
  liveMain: remote.main,
  checksPassed: checks.length - failed.length,
  checksTotal: checks.length,
  checks,
  failures: failed.map(item => item.id),
  counters: failure.counters,
  externalMutationsPerformedByAuditor: 0,
  stopRulePreserved: true,
});

process.stdout.write(`${JSON.stringify(audit, null, 2)}\n`);
if (audit.status !== 'PASS') process.exitCode = 1;
