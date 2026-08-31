#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, lstatSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

const GIT = '/usr/bin/git';
const GH = '/opt/homebrew/bin/gh';
const PLUTIL = '/usr/bin/plutil';
const FILE = '/usr/bin/file';
const LIPO = '/usr/bin/lipo';
const DU = '/usr/bin/du';
const AUDITOR_PATH = fileURLToPath(import.meta.url);
const PS = '/bin/ps';
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const REQUEST_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c3-authorization-request.v0.8.json';
const RUNNER_RELATIVE = 'scripts/run-ai-native-studio-pb1-validation-only-c3.mjs';
const RUNNER_PATH = resolve(REPOSITORY_ROOT, RUNNER_RELATIVE);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';

function argument(name, fallback = null) {
  const index = process.argv.indexOf(name);
  if (index < 0) return fallback;
  if (!process.argv[index + 1] || process.argv[index + 1].startsWith('--')) throw new Error(`Missing value for ${name}`);
  return process.argv[index + 1];
}

const selfTestRequested = process.argv.includes('--self-test');
const contractRelative = argument('--contract', REQUEST_RELATIVE);
const contractPath = resolve(REPOSITORY_ROOT, contractRelative);
if (relative(resolve(REPOSITORY_ROOT, 'specs'), contractPath).startsWith('..')) throw new Error('Contract must remain under specs/');

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, canonicalize(child)]));
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

function execResult(command, args, timeout = 20 * 60 * 1000) {
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

function command(commandPath, args, timeout) {
  const observed = execResult(commandPath, args, timeout);
  if (observed.exitCode !== 0) throw new Error(`Audit command failed (${observed.exitCode}): ${commandPath} ${args.join(' ')}\n${observed.stderr}`);
  return observed.stdout.trim();
}

function git(root, args) {
  return command(GIT, ['-C', root, ...args]);
}

function treeBytes(path) {
  return Number(command(DU, ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function treeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', files: 0, bytes: 0, manifestSha256: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute, { bigint: true });
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) walk(absolute, relativePath);
      else if (item.isFile()) records.push(`${relativePath}\0${item.size}\0${item.mtimeNs}`);
      else if (item.isSymbolicLink()) records.push(`${relativePath}\0SYMLINK`);
    }
  }
  walk(root);
  return { state: 'PRESENT', files: records.length, bytes: records.reduce((sum, line) => sum + (line.endsWith('\0SYMLINK') ? 0 : Number(line.split('\0')[1])), 0), manifestSha256: sha256Bytes(`${records.join('\n')}\n`) };
}

function contentTreeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', entries: 0, digest: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((a, b) => a.localeCompare(b, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) { records.push({ path: relativePath, type: 'directory', mode: item.mode & 0o7777 }); walk(absolute, relativePath); }
      else if (item.isFile()) records.push({ path: relativePath, type: 'file', mode: item.mode & 0o7777, bytes: item.size, sha256: sha256File(absolute) });
      else if (item.isSymbolicLink()) records.push({ path: relativePath, type: 'symlink', mode: item.mode & 0o7777 });
    }
  }
  walk(root);
  return { state: 'PRESENT', entries: records.length, digest: sha256Bytes(canonicalJson(records)) };
}

function parseRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ref: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function remote(spec) {
  const metadata = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}`]));
  const pulls = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]));
  const releases = JSON.parse(command(GH, ['api', `repos/${spec.repository.fullName}/releases?per_page=100`]));
  const heads = parseRefs(command(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRefs(command(GIT, ['ls-remote', '--tags', spec.repository.url]));
  return { metadata: { id: metadata.id, fullName: metadata.full_name, fork: metadata.fork, parent: metadata.parent?.full_name, visibility: metadata.visibility, private: metadata.private }, heads, tags, main: heads.find(item => item.ref === 'refs/heads/main')?.oid, pulls: pulls.length, releases: releases.length };
}

function parsePointer(text) {
  const match = text.match(/^version https:\/\/git-lfs\.github\.com\/spec\/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n?$/);
  return match ? { sha256: match[1], bytes: Number(match[2]) } : null;
}

function metric(source, spec) {
  const expected = spec.metricCorrection.f0ParentRangeAttributeIndependent;
  const assets = expected.formerLfsAssetObjectTransitions;
  const assetSet = new Set(assets.map(item => item.path));
  const paths = git(source, ['diff', '--name-only', `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`]).split(/\r?\n/).filter(Boolean).sort();
  const textPaths = paths.filter(path => !assetSet.has(path));
  let additions = 0; let deletions = 0;
  for (const path of textPaths) {
    const [left, right] = git(source, ['diff', '--numstat', `${spec.publicationBaseline.mergeBase}..${spec.publicationBaseline.soleParent}`, '--', path]).split('\t');
    additions += Number(left); deletions += Number(right);
  }
  const transitions = assets.map(item => {
    const basePointer = parsePointer(command(GIT, ['-C', source, 'show', `${spec.publicationBaseline.mergeBase}:${item.path}`]));
    const parentPointer = parsePointer(command(GIT, ['-C', source, 'show', `${spec.publicationBaseline.soleParent}:${item.path}`]));
    return {
      path: item.path,
      pass: git(source, ['rev-parse', `${spec.publicationBaseline.mergeBase}:${item.path}`]) === item.mergeBasePointerGitBlobOidSha1 && git(source, ['rev-parse', `${spec.publicationBaseline.soleParent}:${item.path}`]) === item.f0ParentPointerGitBlobOidSha1 && basePointer?.sha256 === item.mergeBaseContentSha256 && basePointer?.bytes === item.mergeBaseContentBytes && parentPointer?.sha256 === item.f0ParentContentSha256 && parentPointer?.bytes === item.f0ParentContentBytes,
    };
  });
  return { paths, textPaths, textPathListSha256: sha256Bytes(`${textPaths.join('\n')}\n`), additions, deletions, transitions };
}

function lfsInventory(source) {
  const files = JSON.parse(git(source, ['lfs', 'ls-files', '--json'])).files.sort((a, b) => a.name.localeCompare(b.name, 'en'));
  let bytes = 0;
  const mismatches = [];
  const manifest = [];
  for (const item of files) {
    const path = resolve(source, item.name);
    if (!existsSync(path)) { mismatches.push(item.name); continue; }
    const observedBytes = statSync(path).size;
    const observedSha = sha256File(path);
    bytes += observedBytes;
    manifest.push(`${item.name}\0${observedBytes}\0${observedSha}`);
    if (observedBytes !== item.size || observedSha !== item.oid || !item.downloaded || !item.checkout) mismatches.push(item.name);
  }
  return { count: files.length, bytes, manifestSha256: sha256Bytes(`${manifest.join('\n')}\n`), mismatches };
}

function plistRaw(path, key) {
  const observed = execResult(PLUTIL, ['-extract', key, 'raw', path]);
  return observed.exitCode === 0 ? observed.stdout.trim() : null;
}

function add(checks, id, pass, observed = null, expected = true) {
  checks.push({ id, pass: Boolean(pass), observed, expected });
}

const spec = JSON.parse(readFileSync(contractPath, 'utf8'));
const request = JSON.parse(readFileSync(resolve(REPOSITORY_ROOT, REQUEST_RELATIVE), 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
const auditPath = resolve(evidenceRoot, 'audit-failure.json');
if (!existsSync(evidenceRoot)) throw new Error(`Evidence root missing: ${evidenceRoot}`);
if (existsSync(auditPath)) throw new Error(`Failure audit exists: ${auditPath}`);
const initialFiles = readdirSync(evidenceRoot).sort();
const read = name => JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'));
const names = ['preflight.json','negative-controls.json','lfs-materialization.json','remote-and-history.json','license-and-generated-paths.json','dependency.json','build.json','runtime-identity.json','failure.json','verdict.json'];
const receipts = Object.fromEntries(names.map(name => [name, read(name)]));
const preflight = receipts['preflight.json'];
const build = receipts['build.json'];
const runtime = receipts['runtime-identity.json'];
const failure = receipts['failure.json'];
const verdict = receipts['verdict.json'];
const source = spec.paths.sourceRoot;
const dependency = resolve(source, 'lib', 'macos_arm64');
const app = resolve(spec.paths.buildRoot, 'bin', spec.build.expectedApplicationName);
const binary = resolve(app, 'Contents', 'MacOS', 'Blender');
const plist = resolve(app, 'Contents', 'Info.plist');
const globalProductRoot = resolve(process.env.HOME, 'Library', 'Application Support', spec.build.expectedConfigurationNamespace, '5.2');
const globalUserpref = resolve(globalProductRoot, 'config', 'userpref.blend');
const live = remote(spec);
const restrictedProcesses = command(PS, ['-axo', 'pid=,comm=,args=']).split(/\r?\n/).map(line => line.trim()).filter(Boolean).filter(line => /(?:Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|Blender\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line));
const counters = failure.counters;
const checks = [];

add(checks, 'AUDITOR_INDEPENDENT', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`));
add(checks, 'AUTHORIZATION_BOUND', spec.authorization.granted === true && spec.authorization.exactTextZhCN === request.exactStandingAuthorizationTextZhCN);
add(checks, 'CONTRACT_REQUEST_RUNNER_BOUND', preflight.contract.sha256 === sha256File(contractPath) && preflight.request.sha256 === sha256File(resolve(REPOSITORY_ROOT, REQUEST_RELATIVE)) && preflight.runner.sha256 === sha256File(RUNNER_PATH));
for (const [name, receipt] of Object.entries(receipts)) add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt));
for (const name of ['negative-controls.json','lfs-materialization.json','remote-and-history.json','license-and-generated-paths.json','dependency.json','build.json']) add(checks, `PRE_RUNTIME_PASS_${name}`, receipts[name].status === 'PASS');
add(checks, 'PREFLIGHT_ACCEPTED_10_CONTROLS', preflight.status === 'ACCEPTED' && receipts['negative-controls.json'].checksPassed === 10 && receipts['negative-controls.json'].checksTotal === 10);
add(checks, 'EXPECTED_RUNTIME_FAILURE_STOP', runtime.status === 'FAIL' && failure.failedStage === 'RUNTIME_IDENTITY_CONFIGURATION' && failure.error === 'RUNTIME_IDENTITY_FAILED' && verdict.status === 'FAIL' && verdict.failedStage === 'RUNTIME_IDENTITY_CONFIGURATION' && verdict.failureReceiptHash === failure.receiptHash);
add(checks, 'BUILD_PASS_EXACT', build.status === 'PASS' && Object.values(build.checks).every(Boolean) && build.process.exitCode === 0 && build.process.elapsedSeconds <= spec.resources.maximumBuildWallSeconds && build.timing.maximumResidentSetSizeBytes <= spec.resources.maximumBuildPeakRssBytes);
add(checks, 'BUILD_ARTIFACT_EXACT', existsSync(binary) && sha256File(binary) === build.artifact.sha256 && statSync(binary).size === build.artifact.bytes && command(LIPO, ['-archs', binary]) === 'arm64' && plistRaw(plist, 'CFBundleIdentifier') === spec.build.expectedBundleIdentifier);
add(checks, 'BUILD_LOG_HASHES_EXACT', build.logs.stdout.sha256 === sha256File(resolve(evidenceRoot, 'build.stdout.log')) && build.logs.stderr.sha256 === sha256File(resolve(evidenceRoot, 'build.stderr.log')) && build.logs.timing.sha256 === sha256File(resolve(evidenceRoot, 'build.timing.log')));
add(checks, 'TWO_STARTS_ZERO_RENDER_IDENTITY_PASS', runtime.productStarts === 2 && runtime.renders === 0 && runtime.runtime.exitCode === 0 && runtime.runtime.payload.renderCalls === 0 && runtime.checks.versionIdentity && runtime.checks.payloadIdentity && runtime.checks.preferenceSaved);
add(checks, 'SOLE_RUNTIME_FAILURES_ARE_ISOLATION', !runtime.checks.pathsExact && !runtime.checks.productConfigPresent && Object.entries(runtime.checks).filter(([, pass]) => !pass).map(([name]) => name).join('\n') === 'pathsExact\nproductConfigPresent');
add(checks, 'OFFICIAL_CONFIG_UNCHANGED', runtime.checks.officialUnchanged && runtime.configuration.officialBefore.digest === runtime.configuration.officialAfter.digest);
add(checks, 'ISOLATED_ROOTS_ABSENT', runtime.checks.isolatedOfficialAbsent && runtime.configuration.productAfter.state === 'ABSENT' && contentTreeIdentity(runtime.configuration.isolatedOfficial).state === 'ABSENT' && contentTreeIdentity(runtime.configuration.productRoot).state === 'ABSENT');
add(checks, 'GLOBAL_PRODUCT_PATH_OBSERVED', Object.values(runtime.runtime.payload.paths).every(path => path.startsWith(`${globalProductRoot}/`)) && existsSync(globalUserpref) && statSync(globalUserpref).size === 179901 && sha256File(globalUserpref) === '5c635b481c675f3a4fc4a95ae851ab8a68442ed690d6014597477df9aa320dc1');
add(checks, 'RUNTIME_LOGS_BOUND', runtime.runtime.stdoutSha256 === sha256File(resolve(evidenceRoot, 'runtime.stdout.log')) && runtime.runtime.stderrSha256 === sha256File(resolve(evidenceRoot, 'runtime.stderr.log')));
add(checks, 'SOURCE_DEPENDENCY_CLEAN', git(source, ['status', '--porcelain=v1']) === '' && git(source, ['rev-parse', 'HEAD']) === spec.publicationBaseline.head && git(dependency, ['status', '--porcelain=v1']) === '' && git(dependency, ['rev-parse', 'HEAD']) === spec.dependency.commit);
const engineObjects = resolve(source, '.git', 'lfs', 'objects');
const dependencyObjects = resolve(dependency, '.git', 'lfs', 'objects');
add(checks, 'LOCAL_OBJECT_LINKS_EXACT', lstatSync(engineObjects).isSymbolicLink() && command('/usr/bin/readlink', [engineObjects]) === spec.lfsCorrection.retainedObjectsSubtree && lstatSync(dependencyObjects).isSymbolicLink() && command('/usr/bin/readlink', [dependencyObjects]) === spec.dependencyLfsCorrection.retainedObjectsSubtree);
add(checks, 'LIVE_REMOTE_UNCHANGED', live.metadata.id === spec.repository.repositoryId && live.main === spec.publicationBaseline.head && live.heads.length === 1 && live.tags.length === 0 && live.pulls === 0 && live.releases === 0);
add(checks, 'COUNTERS_EXACT', counters.localEngineClones === 1 && counters.freshObjectsSymlinks === 1 && counters.localLfsMaterializations === 1 && counters.localDependencyClones === 1 && counters.freshDependencyObjectsSymlinks === 1 && counters.localDependencyLfsMaterializations === 1 && counters.nativeBuilds === 1 && counters.productStarts === 2);
add(checks, 'FORBIDDEN_ZERO', ['publicEngineNetworkClones','renders','engineRemoteWrites','engineRefUpdates','lfsNetworkDownloads','lfsUploads','releases','signing','notarization','dmg','pb2ThroughPb7','modelCalls'].every(name => counters[name] === 0));
add(checks, 'NO_NATIVE_PROCESS_REMAINS', restrictedProcesses.length === 0, restrictedProcesses, []);
add(checks, 'PREAUDIT_FILESET_EXACT', initialFiles.join('\n') === ['build.json','build.stderr.log','build.stdout.log','build.timing.log','dependency.json','failure.json','lfs-materialization.json','license-and-generated-paths.json','negative-controls.json','preflight.json','remote-and-history.json','runtime-identity.json','runtime.stderr.log','runtime.stdout.log','verdict.json'].join('\n'));
add(checks, 'ROOTS_WITHIN_CEILINGS', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumAttempt04ExternalRootBytes && treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes);
add(checks, 'STOP_RULE_PRESERVED', failure.stopRulePreserved && verdict.stopRulePreserved);

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyC3Attempt04FailureAudit.v0.10',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY_C3_ATTEMPT04_FAILURE',
  observedAt: new Date().toISOString(),
  status: failed.length ? 'FAIL' : 'PASS',
  classification: 'RETAINED_HARNESS_MACOS_HOME_ISOLATION_FAILURE_AFTER_ACCEPTED_BUILD',
  rootCause: 'The product ignored the process HOME override for macOS application-support resolution and used the real user FilmStudioEngineF0 root. Build and product identity passed; only isolated path equality and isolated product-root presence failed.',
  correctionRequirement: 'Reuse the accepted attempt-04 build in a fresh recovery evidence root and set the four BLENDER_USER_* paths explicitly to fresh isolated directories for at most two zero-render starts. Do not rebuild or modify attempt-04.',
  globalProductConfigObserved: { root: globalProductRoot, userpref: globalUserpref, bytes: existsSync(globalUserpref) ? statSync(globalUserpref).size : null, sha256: existsSync(globalUserpref) ? sha256File(globalUserpref) : null },
  auditor: { path: 'scripts/audit-ai-native-studio-pb1-validation-only-c3-attempt04-failure.mjs', sha256: sha256File(AUDITOR_PATH), importsRunner: false },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  contract: { path: contractRelative, sha256: sha256File(contractPath) },
  buildReceiptHash: build.receiptHash,
  runtimeReceiptHash: runtime.receiptHash,
  failureReceiptHash: failure.receiptHash,
  verdictReceiptHash: verdict.receiptHash,
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
