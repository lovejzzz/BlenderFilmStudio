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
const FILE = '/usr/bin/file';
const PS = '/bin/ps';
const AUDITOR_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const SPEC_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c2-execution.v0.7.json';
const REQUEST_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c2-authorization-request.v0.6.json';
const RUNNER_RELATIVE = 'scripts/run-ai-native-studio-pb1-validation-only-c2.mjs';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const REQUEST_PATH = resolve(REPOSITORY_ROOT, REQUEST_RELATIVE);
const RUNNER_PATH = resolve(REPOSITORY_ROOT, RUNNER_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const FAILURE_FILESET = [
  'build.json',
  'build.stderr.log',
  'build.stdout.log',
  'build.timing.log',
  'dependency.json',
  'failure.json',
  'lfs-materialization.json',
  'license-and-generated-paths.json',
  'negative-controls.json',
  'preflight.json',
  'remote-and-history.json',
  'verdict.json',
];

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)]));
  }
  return value;
}

const canonicalJson = value => JSON.stringify(canonicalize(value));
const sha256Bytes = value => createHash('sha256').update(value).digest('hex');
const sha256File = path => sha256Bytes(readFileSync(path));

function receiptHash(value) {
  const copy = structuredClone(value);
  delete copy.receiptHash;
  return sha256Bytes(canonicalJson(copy));
}

const receiptHashPass = value => value.receiptHash === receiptHash(value);

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

function result(executable, args, timeout = 20 * 60 * 1000) {
  try {
    const stdout = execFileSync(executable, args, {
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

function command(executable, args) {
  const observed = result(executable, args);
  if (observed.exitCode !== 0) throw new Error(`Audit command failed: ${executable} ${args.join(' ')}\n${observed.stderr}`);
  return observed.stdout.trim();
}

const git = (root, args) => command(GIT, ['-C', root, ...args]);
const treeBytes = path => existsSync(path) ? Number(command(DU, ['-sk', path]).split(/\s+/)[0]) * 1024 : 0;

function treeIdentity(root, filter = () => true) {
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

function tmpIdentity(storageRoot) {
  const root = resolve(storageRoot, 'tmp');
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
  if (existsSync(root)) walk(root);
  return {
    files: paths.length,
    bytes: paths.reduce((sum, item) => sum + item.bytes, 0),
    pathListSha256: sha256Bytes(`${paths.map(item => item.path).join('\n')}\n`),
  };
}

function skeleton(root) {
  const observed = { directories: 0, files: 0, bytes: 0, symlinks: 0 };
  function walk(path) {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      if (item.isDirectory()) {
        observed.directories += 1;
        walk(absolute);
      } else if (item.isFile()) {
        observed.files += 1;
        observed.bytes += item.size;
      } else if (item.isSymbolicLink()) observed.symlinks += 1;
    }
  }
  walk(root);
  return observed;
}

function lfsWorktree(root) {
  const paths = git(root, ['lfs', 'ls-files', '-n']).split(/\r?\n/).filter(Boolean);
  const observed = { tracked: paths.length, pointers: 0, pointerBytes: 0, materialized: 0, materializedBytes: 0 };
  for (const path of paths) {
    const bytes = readFileSync(resolve(root, path));
    if (bytes.toString('utf8', 0, 80).startsWith('version https://git-lfs.github.com/spec/v1\n')) {
      observed.pointers += 1;
      observed.pointerBytes += bytes.length;
    } else {
      observed.materialized += 1;
      observed.materializedBytes += bytes.length;
    }
  }
  return observed;
}

function parsePointer(path) {
  const text = readFileSync(path, 'utf8');
  const oid = text.match(/^oid sha256:([0-9a-f]{64})$/m)?.[1] ?? null;
  const bytes = Number(text.match(/^size ([0-9]+)$/m)?.[1] ?? NaN);
  return { fileBytes: statSync(path).size, oid, bytes };
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
const initialFiles = readdirSync(evidenceRoot).sort();
const read = name => JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'));
const receipts = Object.fromEntries([
  'preflight.json',
  'negative-controls.json',
  'lfs-materialization.json',
  'remote-and-history.json',
  'license-and-generated-paths.json',
  'dependency.json',
  'build.json',
  'failure.json',
  'verdict.json',
].map(name => [name, read(name)]));
const preflight = receipts['preflight.json'];
const negative = receipts['negative-controls.json'];
const lfs = receipts['lfs-materialization.json'];
const history = receipts['remote-and-history.json'];
const license = receipts['license-and-generated-paths.json'];
const dependencyReceipt = receipts['dependency.json'];
const build = receipts['build.json'];
const failure = receipts['failure.json'];
const verdict = receipts['verdict.json'];
const source = spec.paths.sourceRoot;
const freshDependency = resolve(source, 'lib', 'macos_arm64');
const retainedDependency = spec.dependency.retainedCheckout;
const retainedDependencyObjects = git(retainedDependency, ['rev-parse', '--git-path', 'lfs/objects']);
const freshDependencyObjects = resolve(freshDependency, git(freshDependency, ['rev-parse', '--git-path', 'lfs/objects']));
const failedRelative = 'zstd/lib/libzstd.a';
const freshFailedPath = resolve(freshDependency, failedRelative);
const retainedFailedPath = resolve(retainedDependency, failedRelative);
const pointer = parsePointer(freshFailedPath);
const retainedObject = resolve(retainedDependencyObjects, pointer.oid.slice(0, 2), pointer.oid.slice(2, 4), pointer.oid);
const retainedEngineWhole = treeIdentity(spec.lfsCorrection.retainedStorageRoot);
const retainedEngineObjects = treeIdentity(spec.lfsCorrection.retainedStorageRoot, path => path.startsWith('objects/'));
const retainedEngineTmp = tmpIdentity(spec.lfsCorrection.retainedStorageRoot);
const attempt02Objects = resolve(spec.bindings.attempt02.sourceRoot, '.git', 'lfs', 'objects');
const attempt02Skeleton = skeleton(attempt02Objects);
const dependencyObjectsIdentity = treeIdentity(retainedDependencyObjects);
const freshDependencySkeleton = skeleton(freshDependencyObjects);
const freshDependencyWorktree = lfsWorktree(freshDependency);
const retainedDependencyWorktree = lfsWorktree(retainedDependency);
const live = liveRemote(spec);
const stderr = readFileSync(resolve(evidenceRoot, 'build.stderr.log'), 'utf8');
const restrictedProcesses = command(PS, ['-axo', 'pid=,comm=,args=']).split(/\r?\n/).map(line => line.trim()).filter(Boolean).filter(line => /(?:Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|Blender\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line));
const counters = failure.counters;
const checks = [];

add(checks, 'AUDITOR_INDEPENDENT', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`));
add(checks, 'AUTHORIZATION_EXACT', spec.authorization.granted === true && spec.authorization.exactTextZhCN === request.exactRequestedAuthorizationTextZhCN);
add(checks, 'CONTRACT_REQUEST_RUNNER_BINDINGS_EXACT', preflight.contract.sha256 === sha256File(SPEC_PATH) && preflight.request.sha256 === sha256File(REQUEST_PATH) && preflight.runner.sha256 === sha256File(RUNNER_PATH));
for (const [name, receipt] of Object.entries(receipts)) add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt));
add(checks, 'PREFLIGHT_AND_NEGATIVE_CONTROLS_PASS', preflight.status === 'ACCEPTED' && preflight.failures.length === 0 && negative.status === 'PASS' && negative.checksPassed === 9 && negative.checksTotal === 9);
add(checks, 'ENGINE_LFS_MATERIALIZATION_PASS', lfs.status === 'PASS' && Object.values(lfs.checks).every(Boolean) && lfs.lfs.count === 6669 && lfs.lfs.bytes === 812388053 && lfs.lfs.mismatches.length === 0);
add(checks, 'HISTORY_METRIC_PASS', history.status === 'PASS' && Object.values(history.checks).every(Boolean) && history.metric.allPaths.length === 16 && history.metric.textPaths.length === 14 && history.metric.textAdditions === 837 && history.metric.textDeletions === 64 && history.metric.transitions.length === 2 && history.metric.transitions.every(item => item.pass));
add(checks, 'LICENSE_AND_GENERATED_PASS', license.status === 'PASS' && Object.values(license.checks).every(Boolean));
add(checks, 'DEPENDENCY_IDENTITY_PASS_ONLY', dependencyReceipt.status === 'PASS' && Object.values(dependencyReceipt.checks).every(Boolean) && dependencyReceipt.dependency.head === spec.dependency.commit);
add(checks, 'EXPECTED_BUILD_FAILURE_AND_STOP', build.status === 'FAIL' && build.process.exitCode === 2 && !build.process.timedOut && !build.process.resourceExceeded && failure.failedStage === 'CLEAN_NATIVE_BUILD' && failure.error === 'BUILD_FAILED' && verdict.status === 'FAIL' && verdict.failedStage === 'CLEAN_NATIVE_BUILD' && verdict.failureReceiptHash === failure.receiptHash);
add(checks, 'BUILD_LOG_HASHES_EXACT', build.logs.stdout.sha256 === sha256File(resolve(evidenceRoot, 'build.stdout.log')) && build.logs.stderr.sha256 === sha256File(resolve(evidenceRoot, 'build.stderr.log')) && build.logs.timing.sha256 === sha256File(resolve(evidenceRoot, 'build.timing.log')));
add(checks, 'LINKER_REJECTED_ZSTD_POINTER', stderr.includes(`ld: unknown file type in '${freshFailedPath}'`) && stderr.includes('clang++: error: linker command failed with exit code 1'));
add(checks, 'FRESH_DEPENDENCY_ZSTD_POINTER_EXACT', pointer.fileBytes === 131 && pointer.oid === 'b7063197d587191be8e8a475735bd8af3d805c265a6696b9a44b6b1ec6ba2006' && pointer.bytes === 624344, pointer);
add(checks, 'RETAINED_ZSTD_CONTENT_EXACT', existsSync(retainedObject) && statSync(retainedObject).size === pointer.bytes && sha256File(retainedObject) === pointer.oid && statSync(retainedFailedPath).size === pointer.bytes && sha256File(retainedFailedPath) === pointer.oid && command(FILE, [retainedFailedPath]).includes('current ar archive'));
add(checks, 'FRESH_DEPENDENCY_ALL_POINTERS_NO_LFS_OBJECTS', freshDependencyWorktree.tracked === 622 && freshDependencyWorktree.pointers === 622 && freshDependencyWorktree.pointerBytes === 81300 && freshDependencyWorktree.materialized === 0 && freshDependencySkeleton.files === 0 && freshDependencySkeleton.bytes === 0 && freshDependencySkeleton.symlinks === 0, { worktree: freshDependencyWorktree, objects: freshDependencySkeleton });
add(checks, 'RETAINED_DEPENDENCY_MATERIALIZED_EXACT', retainedDependencyWorktree.tracked === 622 && retainedDependencyWorktree.pointers === 0 && retainedDependencyWorktree.materialized === 622 && retainedDependencyWorktree.materializedBytes === 1102333263 && dependencyObjectsIdentity.files === 618 && dependencyObjectsIdentity.bytes === 1070190055 && dependencyObjectsIdentity.manifestSha256 === 'e180738d406f6ba91d5f2fa315232efaac3d45c0e1f55c03b2fab98bf5ee5447', { worktree: retainedDependencyWorktree, objects: dependencyObjectsIdentity });
add(checks, 'SOURCE_IDENTITY_AND_NETWORK_DISABLE_EXACT', git(source, ['rev-parse', 'HEAD']) === spec.publicationBaseline.head && git(source, ['rev-parse', 'HEAD^{tree}']) === spec.publicationBaseline.tree && git(source, ['status', '--porcelain=v1']) === '' && git(source, ['remote', 'get-url', '--push', 'origin']) === 'disabled://film-engine-writes-forbidden' && git(source, ['config', '--get', 'lfs.url']) === 'file:///PB1-C2-LFS-NETWORK-DISABLED');
add(checks, 'ENGINE_OBJECT_LINK_EXACT', lstatSync(lfs.localObjects).isSymbolicLink() && command('/usr/bin/readlink', [lfs.localObjects]) === spec.lfsCorrection.retainedObjectsSubtree);
add(checks, 'RETAINED_ENGINE_LFS_EXACT', canonicalJson(retainedEngineWhole) === canonicalJson(preflight.retainedLfs.wholeTree) && retainedEngineObjects.files === spec.lfsCorrection.retainedObjectFiles && retainedEngineObjects.bytes === spec.lfsCorrection.retainedObjectBytes && retainedEngineObjects.manifestSha256 === spec.lfsCorrection.retainedObjectManifestSha256 && retainedEngineTmp.files === 3918 && retainedEngineTmp.bytes === 0 && retainedEngineTmp.pathListSha256 === spec.lfsCorrection.retainedTmpDriftToPreserveWithoutCleanup.pathListSha256);
add(checks, 'ATTEMPT02_RETAINED_EXACT', attempt02Skeleton.directories === 6424 && attempt02Skeleton.files === 0 && attempt02Skeleton.bytes === 0 && attempt02Skeleton.symlinks === 0, attempt02Skeleton);
add(checks, 'LIVE_PUBLIC_FORK_AND_REFSET_EXACT', live.id === spec.repository.repositoryId && live.fullName === spec.repository.fullName && live.fork && live.parent === spec.repository.forkParent && live.visibility === 'public' && !live.private && live.main === spec.publicationBaseline.head && live.heads.length === 1 && live.heads[0]?.ref === spec.repository.expectedOnlyRemoteHead && live.tags.length === 0 && live.pulls === 0 && live.releases === 0, live);
add(checks, 'AUTHORIZED_COUNTERS_EXACT', counters.localEngineClones === 1 && counters.freshObjectsSymlinks === 1 && counters.localLfsMaterializations === 1 && counters.localDependencyClones === 1 && counters.nativeBuilds === 1 && counters.productStarts === 0);
add(checks, 'FORBIDDEN_COUNTERS_ZERO', ['publicEngineNetworkClones', 'renders', 'engineRemoteWrites', 'engineRefUpdates', 'lfsNetworkDownloads', 'lfsUploads', 'releases', 'signing', 'notarization', 'dmg', 'pb2ThroughPb7', 'modelCalls'].every(name => counters[name] === 0), counters);
add(checks, 'NO_RUNTIME_OR_PRODUCT_START', !existsSync(spec.paths.isolatedHome) && counters.productStarts === 0 && counters.renders === 0);
add(checks, 'NO_NATIVE_PROCESS_REMAINS', restrictedProcesses.length === 0, restrictedProcesses, []);
add(checks, 'PREAUDIT_FILESET_EXACT', initialFiles.join('\n') === FAILURE_FILESET.join('\n'), initialFiles, FAILURE_FILESET);
add(checks, 'ROOTS_WITHIN_CEILINGS', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumAttempt03ExternalRootBytes && treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes);
add(checks, 'STOP_RULE_PRESERVED', failure.stopRulePreserved === true && verdict.stopRulePreserved === true);

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyC2Attempt03FailureAudit.v0.8',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY_C2_ATTEMPT03_FAILURE',
  observedAt: new Date().toISOString(),
  status: failed.length ? 'FAIL' : 'PASS',
  classification: 'RETAINED_HARNESS_DEPENDENCY_LFS_MATERIALIZATION_FAILURE',
  runnerRootCause: 'The exact local dependency clone used --no-checkout under GIT_LFS_SKIP_SMUDGE=1 but did not link or materialize the retained dependency LFS object store. All 622 dependency LFS worktree paths remained pointers; the first linker use rejected the 131-byte libzstd.a pointer.',
  correctionRequirement: 'A fresh correction may add one dependency-local objects symlink to the retained dependency LFS object store before dependency checkout and one zero-network dependency git lfs checkout, with retained dependency objects immutable. Attempt-03 must remain unchanged and must not be retried in place.',
  auditor: { path: 'scripts/audit-ai-native-studio-pb1-validation-only-c2-attempt03-failure.mjs', sha256: sha256File(AUDITOR_PATH), importsRunner: false },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
  request: { path: REQUEST_RELATIVE, sha256: sha256File(REQUEST_PATH) },
  failureReceiptHash: failure.receiptHash,
  verdictReceiptHash: verdict.receiptHash,
  buildReceiptHash: build.receiptHash,
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
