#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, lstatSync, openSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const DU = '/usr/bin/du';
const PS = '/bin/ps';
const AUDITOR_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const SPEC_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c1-execution.v0.5.json';
const REQUEST_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c1-authorization-request.v0.4.json';
const RUNNER_RELATIVE = 'scripts/run-ai-native-studio-pb1-validation-only-c1.mjs';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const REQUEST_PATH = resolve(REPOSITORY_ROOT, REQUEST_RELATIVE);
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
  try {
    writeFileSync(descriptor, `${JSON.stringify(record, null, 2)}\n`);
  } finally {
    closeSync(descriptor);
  }
  return record;
}

function result(command, args, timeout = 20 * 60 * 1000) {
  try {
    const stdout = execFileSync(command, args, {
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
      timeout,
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

function command(commandPath, args) {
  const observed = result(commandPath, args);
  if (observed.exitCode !== 0) throw new Error(`Audit command failed: ${commandPath} ${args.join(' ')}\n${observed.stderr}`);
  return observed.stdout.trim();
}

function git(root, args) {
  return command(GIT, ['-C', root, ...args]);
}

function treeBytes(path) {
  return existsSync(path) ? Number(command(DU, ['-sk', path]).split(/\s+/)[0]) * 1024 : 0;
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

function emptyDirectorySkeleton(root) {
  const directories = [];
  let files = 0;
  let bytes = 0;
  let symlinks = 0;
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) {
        directories.push(relativePath);
        walk(absolute, relativePath);
      } else if (item.isFile()) {
        files += 1;
        bytes += item.size;
      } else if (item.isSymbolicLink()) {
        symlinks += 1;
      }
    }
  }
  walk(root);
  return {
    directories: directories.length,
    files,
    bytes,
    symlinks,
    directoryListSha256: sha256Bytes(`${directories.join('\n')}\n`),
  };
}

function tmpIdentity(storageRoot) {
  const tmpRoot = resolve(storageRoot, 'tmp');
  if (!existsSync(tmpRoot)) return { files: 0, bytes: 0, pathListSha256: sha256Bytes('\n') };
  const paths = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) walk(absolute, relativePath);
      else if (item.isFile()) paths.push({ path: `tmp/${relativePath}`, bytes: item.size });
    }
  }
  walk(tmpRoot);
  return {
    files: paths.length,
    bytes: paths.reduce((sum, item) => sum + item.bytes, 0),
    pathListSha256: sha256Bytes(`${paths.map(item => item.path).join('\n')}\n`),
  };
}

function parseRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ref: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function liveRemote(spec) {
  const metadata = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}`]));
  const pulls = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]));
  const releases = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/releases?per_page=100`]));
  const heads = parseRefs(command(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRefs(command(GIT, ['ls-remote', '--tags', spec.repository.url]));
  return {
    id: metadata.id,
    fullName: metadata.full_name,
    fork: metadata.fork,
    parent: metadata.parent?.full_name,
    visibility: metadata.visibility,
    private: metadata.private,
    heads,
    tags,
    main: heads.find(item => item.ref === 'refs/heads/main')?.oid,
    pulls: pulls.length,
    releases: releases.length,
  };
}

function add(checks, id, pass, observed = null, expected = true) {
  checks.push({ id, pass: Boolean(pass), observed, expected });
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const request = JSON.parse(readFileSync(REQUEST_PATH, 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
const auditPath = resolve(evidenceRoot, 'audit-failure.json');
if (existsSync(auditPath)) throw new Error(`Failure audit already exists: ${auditPath}`);
const initialEvidenceFiles = readdirSync(evidenceRoot).sort();
const read = name => JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'));
const preflight = read('preflight.json');
const negative = read('negative-controls.json');
const failure = read('failure.json');
const verdict = read('verdict.json');
const source = spec.paths.sourceRoot;
const localObjects = resolve(source, '.git', 'lfs', 'objects');
const sourceSkeleton = emptyDirectorySkeleton(localObjects);
const retainedWholeTree = treeIdentity(spec.lfsCorrection.retainedStorageRoot);
const retainedObjects = treeIdentity(spec.lfsCorrection.retainedStorageRoot, path => path.startsWith('objects/'));
const retainedTmp = tmpIdentity(spec.lfsCorrection.retainedStorageRoot);
const lfsFiles = JSON.parse(git(source, ['lfs', 'ls-files', '--json'])).files;
const lfsSummary = {
  count: lfsFiles.length,
  contentBytes: lfsFiles.reduce((sum, item) => sum + item.size, 0),
  downloadedCount: lfsFiles.filter(item => item.downloaded).length,
  checkoutCount: lfsFiles.filter(item => item.checkout).length,
};
const remote = liveRemote(spec);
const counters = failure.counters;
const restrictedProcesses = command(PS, ['-axo', 'pid=,comm=,args=']).split(/\r?\n/).map(line => line.trim()).filter(Boolean).filter(line => /(?:Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|Blender\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line));
const checks = [];

add(checks, 'AUDITOR_INDEPENDENT', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`));
add(checks, 'AUTHORIZATION_EXACT', spec.authorization.granted === true && spec.authorization.exactTextZhCN === request.exactRequestedAuthorizationTextZhCN);
add(checks, 'CONTRACT_REQUEST_RUNNER_BINDINGS', preflight.contract.sha256 === sha256File(SPEC_PATH) && preflight.request.sha256 === sha256File(REQUEST_PATH) && preflight.runner.sha256 === sha256File(RUNNER_PATH));
for (const [name, receipt] of Object.entries({ preflight, negative, failure, verdict })) add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt));
add(checks, 'PREFLIGHT_ACCEPTED', preflight.status === 'ACCEPTED' && preflight.failures.length === 0);
add(checks, 'NINE_NEGATIVE_CONTROLS_PASS', negative.status === 'PASS' && negative.checksPassed === 9 && negative.checksTotal === 9 && negative.controls.every(item => item.pass));
add(checks, 'EXPECTED_STOP_EXACT', failure.failedStage === 'FRESH_LOCAL_LFS_MATERIALIZATION' && failure.error === 'FRESH_LFS_OBJECTS_PATH_NOT_ABSENT' && verdict.status === 'FAIL' && verdict.failureReceiptHash === failure.receiptHash);
add(checks, 'SOURCE_HEAD_TREE_PARENT_EXACT', git(source, ['rev-parse', 'HEAD']) === spec.publicationBaseline.head && git(source, ['rev-parse', 'HEAD^{tree}']) === spec.publicationBaseline.tree && git(source, ['show', '-s', '--format=%P', 'HEAD']) === spec.publicationBaseline.soleParent);
add(checks, 'SOURCE_CLEAN_NONSHALLOW_COMPLETE', git(source, ['status', '--porcelain=v1']) === '' && git(source, ['rev-parse', '--is-shallow-repository']) === 'false' && Number(git(source, ['rev-list', '--count', 'HEAD'])) === spec.publicationBaseline.reachableCommitCount);
add(checks, 'SOURCE_LOCAL_FETCH_REMOTE_EXACT', git(source, ['remote', 'get-url', 'origin']) === spec.bindings.attempt01.sourceRoot);
add(checks, 'SOURCE_PUSH_DISABLED', git(source, ['remote', 'get-url', '--push', 'origin']) === 'disabled://film-engine-writes-forbidden');
add(checks, 'SOURCE_LFS_NETWORK_DISABLED', git(source, ['config', '--get', 'lfs.url']) === 'file:///PB1-C1-LFS-NETWORK-DISABLED');
add(checks, 'LFS_OBJECT_PATH_IS_DIRECTORY_NOT_LINK', existsSync(localObjects) && lstatSync(localObjects).isDirectory() && !lstatSync(localObjects).isSymbolicLink());
add(checks, 'LFS_OBJECT_SKELETON_EMPTY', sourceSkeleton.directories > 0 && sourceSkeleton.files === 0 && sourceSkeleton.bytes === 0 && sourceSkeleton.symlinks === 0, sourceSkeleton, 'nonzero empty directories and zero files/bytes/symlinks');
add(checks, 'NO_LFS_OBJECT_DOWNLOADED', lfsSummary.count === spec.lfsCorrection.trackedPathsAtPublicationHead && lfsSummary.contentBytes === spec.lfsCorrection.contentBytesAtPublicationHead && lfsSummary.downloadedCount === 0, lfsSummary, { count: spec.lfsCorrection.trackedPathsAtPublicationHead, contentBytes: spec.lfsCorrection.contentBytesAtPublicationHead, downloadedCount: 0 });
add(checks, 'RETAINED_WHOLE_STORAGE_UNCHANGED', canonicalJson(retainedWholeTree) === canonicalJson(preflight.retainedLfs.wholeTree), retainedWholeTree, preflight.retainedLfs.wholeTree);
add(checks, 'RETAINED_OBJECTS_EXACT', retainedObjects.files === spec.lfsCorrection.retainedObjectFiles && retainedObjects.bytes === spec.lfsCorrection.retainedObjectBytes && retainedObjects.manifestSha256 === spec.lfsCorrection.retainedObjectManifestSha256, retainedObjects, { files: spec.lfsCorrection.retainedObjectFiles, bytes: spec.lfsCorrection.retainedObjectBytes, manifestSha256: spec.lfsCorrection.retainedObjectManifestSha256 });
add(checks, 'RETAINED_TMP_PRESERVED', retainedTmp.files === spec.lfsCorrection.retainedTmpDriftToPreserveWithoutCleanup.files && retainedTmp.bytes === spec.lfsCorrection.retainedTmpDriftToPreserveWithoutCleanup.bytes && retainedTmp.pathListSha256 === spec.lfsCorrection.retainedTmpDriftToPreserveWithoutCleanup.pathListSha256, retainedTmp, spec.lfsCorrection.retainedTmpDriftToPreserveWithoutCleanup);
add(checks, 'LIVE_PUBLIC_FORK_EXACT', remote.id === spec.repository.repositoryId && remote.fullName === spec.repository.fullName && remote.fork && remote.parent === spec.repository.forkParent && remote.visibility === 'public' && !remote.private);
add(checks, 'LIVE_MAIN_REFSET_UNCHANGED', remote.main === spec.publicationBaseline.head && remote.heads.length === 1 && remote.heads[0]?.ref === spec.repository.expectedOnlyRemoteHead && remote.tags.length === 0 && remote.pulls === 0 && remote.releases === 0, remote, 'single exact main; zero tags, PRs and releases');
add(checks, 'ONLY_ONE_LOCAL_CLONE_CONSUMED', counters.localEngineClones === 1 && counters.freshObjectsSymlinks === 0 && counters.localLfsMaterializations === 0 && counters.localDependencyClones === 0 && counters.nativeBuilds === 0 && counters.productStarts === 0);
add(checks, 'ALL_FORBIDDEN_COUNTERS_ZERO', ['publicEngineNetworkClones', 'renders', 'engineRemoteWrites', 'engineRefUpdates', 'lfsNetworkDownloads', 'lfsUploads', 'releases', 'signing', 'notarization', 'dmg', 'pb2ThroughPb7', 'modelCalls'].every(name => counters[name] === 0), counters, 'all forbidden counters zero');
add(checks, 'NO_DEPENDENCY_BUILD_OR_RUNTIME_ROOT', !existsSync(resolve(source, 'lib', 'macos_arm64')) && !existsSync(spec.paths.buildRoot) && !existsSync(spec.paths.isolatedHome));
add(checks, 'NO_NATIVE_PROCESS_REMAINS', restrictedProcesses.length === 0, restrictedProcesses, []);
add(checks, 'EVIDENCE_PREAUDIT_FILESET_EXACT', initialEvidenceFiles.join('\n') === ['failure.json', 'negative-controls.json', 'preflight.json', 'verdict.json'].join('\n'), initialEvidenceFiles, ['failure.json', 'negative-controls.json', 'preflight.json', 'verdict.json']);
add(checks, 'ROOTS_WITHIN_CEILINGS', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumAttempt02ExternalRootBytes && treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes);
add(checks, 'STOP_RULE_PRESERVED', failure.stopRulePreserved === true && verdict.stopRulePreserved === true);

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyC1Attempt02FailureAudit.v0.6',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY_C1_ATTEMPT02_FAILURE',
  observedAt: new Date().toISOString(),
  status: failed.length ? 'FAIL' : 'PASS',
  classification: 'RETAINED_HARNESS_ORDERING_FAILURE_BEFORE_LFS_MATERIALIZATION',
  rootCause: 'The exact publication checkout ran before the fresh objects symlink was created. Even with smudge skipped, Git LFS created an empty 6,424-directory hash skeleton under .git/lfs/objects; the runner then correctly rejected the non-absent path before any LFS checkout.',
  correctionRequirement: 'A new versioned runner must assert .git/lfs/objects absent immediately after the no-checkout local clone, create the exact retained-objects symlink, and only then checkout the publication HEAD. It must not delete, repair or retry attempt-02 in place.',
  auditor: {
    path: 'scripts/audit-ai-native-studio-pb1-validation-only-c1-attempt02-failure.mjs',
    sha256: sha256File(AUDITOR_PATH),
    importsRunner: false
  },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
  request: { path: REQUEST_RELATIVE, sha256: sha256File(REQUEST_PATH) },
  failureReceiptHash: failure.receiptHash,
  verdictReceiptHash: verdict.receiptHash,
  sourceObjectsSkeleton: sourceSkeleton,
  lfsSummary,
  retainedWholeTree,
  retainedObjects,
  retainedTmp,
  liveRemote: remote,
  checksPassed: checks.length - failed.length,
  checksTotal: checks.length,
  checks,
  failures: failed.map(item => item.id),
  counters,
  externalMutationsPerformedByAuditor: 0,
  stopRulePreserved: true,
});

process.stdout.write(`${JSON.stringify(audit, null, 2)}\n`);
if (audit.status !== 'PASS') process.exitCode = 1;
