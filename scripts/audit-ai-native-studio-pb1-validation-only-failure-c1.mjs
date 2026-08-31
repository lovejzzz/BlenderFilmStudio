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
const FAILED_AUDITOR_RELATIVE = 'scripts/audit-ai-native-studio-pb1-validation-only-failure.mjs';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const RUNNER_PATH = resolve(REPOSITORY_ROOT, RUNNER_RELATIVE);
const FAILED_AUDITOR_PATH = resolve(REPOSITORY_ROOT, FAILED_AUDITOR_RELATIVE);
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

function result(command, args, timeout = 20 * 60 * 1000) {
  try {
    const stdout = execFileSync(command, args, {
      encoding: 'utf8',
      env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C', GH_PROMPT_DISABLED: '1', GIT_TERMINAL_PROMPT: '0', GIT_LFS_SKIP_SMUDGE: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout,
      maxBuffer: 512 * 1024 * 1024,
    });
    return { exitCode: 0, stdout, stderr: '' };
  } catch (error) {
    return { exitCode: Number.isInteger(error.status) ? error.status : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? String(error.message ?? error) };
  }
}

function command(commandPath, args) {
  const observed = result(commandPath, args);
  if (observed.exitCode !== 0) throw new Error(`Audit command failed: ${commandPath} ${args.join(' ')}\n${observed.stderr}`);
  return observed.stdout.trim();
}

function git(root, args) {
  return command(GIT, ['-C', root, ...args]);
}

function treeBytes(path) {
  return Number(command(DU, ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function filteredStorageIdentity(root, prefixFilter) {
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute, { bigint: true });
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) walk(absolute, relativePath);
      else if (item.isFile() && relativePath.startsWith(prefixFilter)) records.push(`${relativePath}\0${item.size}\0${item.mtimeNs}`);
    }
  }
  walk(root);
  return {
    files: records.length,
    bytes: records.reduce((sum, line) => sum + Number(line.split('\0')[1]), 0),
    manifestSha256: sha256Bytes(`${records.join('\n')}\n`),
  };
}

function tmpIdentity(root) {
  const tmp = resolve(root, 'tmp');
  if (!existsSync(tmp)) return { files: 0, bytes: 0, allZeroBytes: true };
  const paths = [];
  function walk(path) {
    for (const name of readdirSync(path).sort()) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      if (item.isDirectory()) walk(absolute);
      else if (item.isFile()) paths.push({ path: absolute.slice(root.length + 1), bytes: item.size });
    }
  }
  walk(tmp);
  return { files: paths.length, bytes: paths.reduce((sum, item) => sum + item.bytes, 0), allZeroBytes: paths.every(item => item.bytes === 0), pathListSha256: sha256Bytes(`${paths.map(item => item.path).join('\n')}\n`) };
}

function parseRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ref ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function liveRemote(spec) {
  const metadata = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}`]));
  const pulls = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]));
  const releases = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/releases?per_page=100`]));
  const heads = parseRefs(command(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRefs(command(GIT, ['ls-remote', '--tags', spec.repository.url]));
  return { id: metadata.id, fullName: metadata.full_name, fork: metadata.fork, parent: metadata.parent?.full_name, visibility: metadata.visibility, private: metadata.private, heads, tags, main: heads.find(item => item.ref === 'refs/heads/main')?.oid, pulls: pulls.length, releases: releases.length };
}

function add(checks, id, pass, observed = null, expected = true) {
  checks.push({ id, pass: Boolean(pass), observed, expected });
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
const auditPath = resolve(evidenceRoot, 'audit-failure-c1.json');
if (existsSync(auditPath)) throw new Error(`C1 audit already exists: ${auditPath}`);
const read = name => JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'));
const preflight = read('preflight.json');
const negative = read('negative-controls.json');
const history = read('remote-and-history.json');
const failure = read('failure.json');
const verdict = read('verdict.json');
const failedAudit = read('audit-failure.json');
const source = spec.paths.sourceRoot;
const retainedSource = resolve(spec.dependency.retainedCheckout, '..', '..');
const retainedStorage = resolve(retainedSource, '.git', 'lfs');
const checks = [];

add(checks, 'AUDITOR_INDEPENDENT', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`) && !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${FAILED_AUDITOR_RELATIVE}'`));
for (const [name, receipt] of Object.entries({ preflight, negative, history, failure, verdict, failedAudit })) add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt));
add(checks, 'FAILED_AUDIT_RETAINED_41_OF_42', failedAudit.status === 'FAIL' && failedAudit.checksPassed === 41 && failedAudit.checksTotal === 42 && failedAudit.failures.join('\n') === 'RETAINED_LFS_STORAGE_UNCHANGED', failedAudit.failures, ['RETAINED_LFS_STORAGE_UNCHANGED']);
add(checks, 'EXPECTED_RUNNER_FAILURE_RETAINED', failure.failedStage === 'HISTORY_AND_SOURCE_IDENTITY' && verdict.status === 'FAIL' && verdict.failureReceiptHash === failure.receiptHash);
add(checks, 'NINE_NEGATIVE_CONTROLS_PASS', negative.checksPassed === 9 && negative.controls.every(item => item.pass));
add(checks, 'ONLY_F0_METRIC_GATE_FAILED', Object.entries(history.checks).filter(([, pass]) => !pass).map(([name]) => name).join('\n') === 'f0PatchExact');
add(checks, 'GRAPH_IDENTITY_EXACT', history.checks.headExact && history.checks.treeExact && history.checks.soleParentExact && history.checks.nonShallow && history.checks.reachableCommitCountExact && history.checks.mergeBaseExact && history.checks.forkCommitCountExact && history.checks.fullFsckPass && history.checks.c1PathsExact && history.checks.publicationPatchExact);
add(checks, 'ATTRIBUTE_CONTEXT_STATS_EXACT', history.history.f0Diff.changedPaths === 16 && history.history.f0Diff.additions === 837 && history.history.f0Diff.deletions === 64 && history.history.f0Diff.binaryPaths === 2);
const retainedNumstat = git(retainedSource, ['diff', '--numstat', `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`]);
const retainedAssetStats = retainedNumstat.split(/\r?\n/).filter(line => spec.sourceIdentity.ordinaryBrandBlobs.some(item => line.endsWith(`\t${item.path}`)));
add(checks, 'RETAINED_CONTEXT_ADDS_FOUR_FOUR_POINTER_LINES', retainedAssetStats.length === 2 && retainedAssetStats.every(line => line.startsWith('2\t2\t')), retainedAssetStats, ['2/2', '2/2']);

const objects = filteredStorageIdentity(retainedStorage, 'objects/');
const tmp = tmpIdentity(retainedStorage);
add(checks, 'RETAINED_LFS_OBJECT_FILES_UNCHANGED', objects.files === preflight.retainedSource.lfsStorageIdentity.files, objects.files, preflight.retainedSource.lfsStorageIdentity.files);
add(checks, 'RETAINED_LFS_OBJECT_BYTES_UNCHANGED', objects.bytes === preflight.retainedSource.lfsStorageIdentity.bytes, objects.bytes, preflight.retainedSource.lfsStorageIdentity.bytes);
add(checks, 'RETAINED_LFS_OBJECT_MANIFEST_UNCHANGED', objects.manifestSha256 === preflight.retainedSource.lfsStorageIdentity.manifestSha256, objects.manifestSha256, preflight.retainedSource.lfsStorageIdentity.manifestSha256);
add(checks, 'MATERIALIZATION_TMP_DRIFT_ZERO_BYTES', tmp.files === 3918 && tmp.bytes === 0 && tmp.allZeroBytes, tmp, { files: 3918, bytes: 0, allZeroBytes: true });

const lfsFiles = JSON.parse(git(source, ['lfs', 'ls-files', '--json'])).files;
let materializedBytes = 0;
const mismatches = [];
for (const item of lfsFiles) {
  const path = resolve(source, item.name);
  if (!existsSync(path)) { mismatches.push(item.name); continue; }
  materializedBytes += statSync(path).size;
  if (statSync(path).size !== item.size || sha256File(path) !== item.oid || !item.downloaded || !item.checkout) mismatches.push(item.name);
}
add(checks, 'MATERIALIZED_LFS_EXACT', lfsFiles.length === spec.sourceIdentity.lfs.trackedPathsAtPublicationHead && materializedBytes === spec.sourceIdentity.lfs.contentBytesAtPublicationHead && mismatches.length === 0, { count: lfsFiles.length, bytes: materializedBytes, mismatches }, { count: spec.sourceIdentity.lfs.trackedPathsAtPublicationHead, bytes: spec.sourceIdentity.lfs.contentBytesAtPublicationHead, mismatches: [] });
add(checks, 'SOURCE_STILL_EXACT_CLEAN', git(source, ['rev-parse', 'HEAD']) === spec.publicationBaseline.head && git(source, ['rev-parse', 'HEAD^{tree}']) === spec.publicationBaseline.tree && git(source, ['status', '--porcelain=v1']) === '');

const remote = liveRemote(spec);
add(checks, 'LIVE_PUBLIC_FORK_EXACT', remote.id === spec.repository.repositoryId && remote.fullName === spec.repository.fullName && remote.fork && remote.parent === spec.repository.forkParent && remote.visibility === 'public' && !remote.private);
add(checks, 'LIVE_MAIN_AND_REF_SET_UNCHANGED', remote.main === spec.publicationBaseline.head && remote.heads.length === 1 && remote.tags.length === 0 && remote.pulls === 0 && remote.releases === 0, remote, 'single exact main, zero tag/PR/release');
add(checks, 'ONE_CLONE_ONE_MATERIALIZATION', failure.counters.publicEngineNetworkClones === 1 && failure.counters.localLfsMaterializations === 1);
add(checks, 'ZERO_DEPENDENCY_BUILD_START_RENDER', ['localDependencyClones', 'cleanNativeArm64Builds', 'productStarts', 'renderCalls'].every(name => failure.counters[name] === 0), failure.counters, 'all zero');
add(checks, 'ZERO_FORBIDDEN_EXTERNAL_MUTATIONS', ['engineRemoteWrites', 'engineRefUpdates', 'lfsNetworkDownloads', 'lfsUploads', 'releases', 'signingOperations', 'notarizationOperations', 'dmgOperations', 'pb2ThroughPb7Mutations', 'modelCalls'].every(name => failure.counters[name] === 0), failure.counters, 'all zero');
add(checks, 'NO_BUILD_OR_RUNTIME_ROOT', !existsSync(spec.paths.buildRoot) && !existsSync(spec.paths.isolatedHome));
add(checks, 'ROOTS_WITHIN_CEILINGS', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumExternalRootBytes && treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes);
add(checks, 'RUNNER_HAS_NO_ENGINE_PUSH_COMMAND', !/["']push["']/.test(readFileSync(RUNNER_PATH, 'utf8')));
add(checks, 'STOP_RULE_PRESERVED', failure.stopRulePreserved && verdict.stopRulePreserved);

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyFailureAuditC1.v0.4',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY',
  observedAt: new Date().toISOString(),
  status: failed.length === 0 ? 'PASS' : 'FAIL',
  classification: 'RETAINED_RUNNER_METRIC_FAILURE_AND_RETAINED_FAILURE_AUDITOR_STORAGE_SCOPE_FAILURE',
  rootCauses: [
    'The v0.3 F0 parent line metric was evaluated under C1 publication worktree attributes, which classify the two former LFS pointer paths as binary: 837/64 plus two binary paths is the same exact tree whose retained F0 attribute context reports 841/68.',
    'The v0.3 materializer bound lfs.storage directly to retained storage. git lfs checkout left 3,918 zero-byte tmp files there while all 6,488 immutable object files, 810,236,112 object bytes, mtimes and manifest hash remained exact. The first failure auditor compared the whole storage tree instead of the objects subtree.',
  ],
  correctionRequirement: 'A new attempt must use a versioned attribute-context-independent F0 metric and a fresh local LFS storage whose objects are read-only-linked to retained objects so tmp files cannot enter retained storage.',
  auditor: { path: 'scripts/audit-ai-native-studio-pb1-validation-only-failure-c1.mjs', sha256: sha256File(AUDITOR_PATH), importsRunnerOrFailedAuditor: false },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  failedAuditor: { path: FAILED_AUDITOR_RELATIVE, sha256: sha256File(FAILED_AUDITOR_PATH), receiptHash: failedAudit.receiptHash },
  specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
  failureReceiptHash: failure.receiptHash,
  verdictReceiptHash: verdict.receiptHash,
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
