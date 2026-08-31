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
const REPOSITORY_ROOT = resolve(dirname(AUDITOR_PATH), '..');
const REQUEST_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-c2-authorization-request.v0.6.json';
const RUNNER_RELATIVE = 'scripts/run-ai-native-studio-pb1-validation-only-c2.mjs';
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
if (selfTestRequested) {
  const source = readFileSync(AUDITOR_PATH, 'utf8');
  const checks = [
    { id: 'NO_RUNNER_IMPORT', pass: !source.includes(`from '${RUNNER_RELATIVE}'`) && !source.includes(`from "${RUNNER_RELATIVE}"`) },
    { id: 'CONTRACT_SCHEMA', pass: ['bfs.pb1ValidationOnlyC2AuthorizationRequest.v0.6', 'bfs.pb1ValidationOnlyC2Execution.v0.7'].includes(spec.schemaVersion) },
    { id: 'SYMLINK_BEFORE_CHECKOUT', pass: readFileSync(RUNNER_PATH, 'utf8').indexOf("symlinkSync(retainedObjects, localObjects, 'dir')") > 0 && readFileSync(RUNNER_PATH, 'utf8').indexOf("symlinkSync(retainedObjects, localObjects, 'dir')") < readFileSync(RUNNER_PATH, 'utf8').indexOf("'checkout exact publication head after objects link'") },
    { id: 'METRIC_BOUND', pass: spec.metricCorrection.f0ParentRangeAttributeIndependent.textPathCountExcludingFormerLfsAssets === 14 && spec.metricCorrection.f0ParentRangeAttributeIndependent.formerLfsAssetObjectTransitions.length === 2 },
    { id: 'ZERO_PUBLIC_CLONE', pass: spec.authorizedOperationsIfOwnerApproves.publicEngineNetworkClones === 0 },
    { id: 'ZERO_FORBIDDEN', pass: spec.authorizedOperationsIfOwnerApproves.engineNetworkWrites === 0 && spec.authorizedOperationsIfOwnerApproves.lfsNetworkDownloads === 0 && spec.authorizedOperationsIfOwnerApproves.renderCalls === 0 },
  ];
  const failed = checks.filter(item => !item.pass);
  const output = { schemaVersion: 'bfs.pb1ValidationOnlyC2AuditorSelfTest.v0.7', status: failed.length ? 'FAIL' : 'PASS', checksPassed: checks.length - failed.length, checksTotal: checks.length, checks, failures: failed.map(item => item.id) };
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
  if (failed.length) process.exitCode = 1;
  process.exit();
}

const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
const auditPath = resolve(evidenceRoot, 'audit.json');
if (!existsSync(evidenceRoot)) throw new Error(`Evidence root missing: ${evidenceRoot}`);
if (existsSync(auditPath)) throw new Error(`Audit exists: ${auditPath}`);
const read = name => JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'));
const names = ['preflight.json','negative-controls.json','lfs-materialization.json','remote-and-history.json','license-and-generated-paths.json','dependency.json','build.json','runtime-identity.json','network-and-mutation-log.json','verdict.json'];
const receipts = Object.fromEntries(names.map(name => [name, read(name)]));
const preflight = receipts['preflight.json'];
const network = receipts['network-and-mutation-log.json'];
const verdict = receipts['verdict.json'];
const source = spec.paths.sourceRoot;
const dependency = resolve(source, 'lib', 'macos_arm64');
const app = resolve(spec.paths.buildRoot, 'bin', spec.build.expectedApplicationName);
const binary = resolve(app, 'Contents', 'MacOS', 'Blender');
const plist = resolve(app, 'Contents', 'Info.plist');
const checks = [];

add(checks, 'AUDITOR_DOES_NOT_IMPORT_RUNNER', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`));
add(checks, 'AUTHORIZATION_GRANTED_AND_BOUND', spec.authorization?.granted === true && spec.authorization?.exactTextZhCN === JSON.parse(readFileSync(resolve(REPOSITORY_ROOT, REQUEST_RELATIVE), 'utf8')).exactRequestedAuthorizationTextZhCN);
for (const [name, receipt] of Object.entries(receipts)) {
  add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt), receipt.receiptHash, receiptHash(receipt));
  add(checks, `RECEIPT_STATUS_${name}`, receipt.status === 'PASS' || (name === 'preflight.json' && receipt.status === 'ACCEPTED'), receipt.status, 'PASS/ACCEPTED');
}
add(checks, 'VERDICT_PASS', verdict.status === 'PASS');
add(checks, 'NEGATIVE_CONTROLS_9_OF_9', receipts['negative-controls.json'].checksPassed === 9 && receipts['negative-controls.json'].controls.every(item => item.pass));

add(checks, 'SOURCE_HEAD_TREE_PARENT_EXACT', git(source, ['rev-parse', 'HEAD']) === spec.publicationBaseline.head && git(source, ['rev-parse', 'HEAD^{tree}']) === spec.publicationBaseline.tree && git(source, ['show', '-s', '--format=%P', 'HEAD']) === spec.publicationBaseline.soleParent);
add(checks, 'SOURCE_CLEAN_NONSHALLOW', git(source, ['status', '--porcelain=v1']) === '' && git(source, ['rev-parse', '--is-shallow-repository']) === 'false');
add(checks, 'SOURCE_REACHABLE_EXACT', Number(git(source, ['rev-list', '--count', 'HEAD'])) === spec.publicationBaseline.reachableCommitCount);
add(checks, 'SOURCE_FSCK_PASS', execResult(GIT, ['-C', source, 'fsck', '--full', '--strict']).exitCode === 0);
const observedMetric = metric(source, spec);
const expectedMetric = spec.metricCorrection.f0ParentRangeAttributeIndependent;
add(checks, 'CORRECTED_TEXT_PATHS_EXACT', observedMetric.paths.length === expectedMetric.allChangedPaths && observedMetric.textPaths.length === expectedMetric.textPathCountExcludingFormerLfsAssets && observedMetric.textPathListSha256 === expectedMetric.textPathListSha256);
add(checks, 'CORRECTED_TEXT_STATS_EXACT', observedMetric.additions === expectedMetric.textAdditions && observedMetric.deletions === expectedMetric.textDeletions);
add(checks, 'FORMER_LFS_OBJECT_TRANSITIONS_EXACT', observedMetric.transitions.every(item => item.pass), observedMetric.transitions, 'all pass');

const localObjects = resolve(source, '.git', 'lfs', 'objects');
add(checks, 'LOCAL_OBJECTS_IS_EXACT_SYMLINK', lstatSync(localObjects).isSymbolicLink() && command('/usr/bin/readlink', [localObjects]) === spec.lfsCorrection.retainedObjectsSubtree);
const lfs = lfsInventory(source);
add(checks, 'LFS_COUNT_BYTES_EXACT', lfs.count === spec.lfsCorrection.trackedPathsAtPublicationHead && lfs.bytes === spec.lfsCorrection.contentBytesAtPublicationHead, { count: lfs.count, bytes: lfs.bytes }, { count: spec.lfsCorrection.trackedPathsAtPublicationHead, bytes: spec.lfsCorrection.contentBytesAtPublicationHead });
add(checks, 'LFS_HASHES_EXACT', lfs.mismatches.length === 0, lfs.mismatches, []);
add(checks, 'LFS_MANIFEST_BOUND', lfs.manifestSha256 === receipts['lfs-materialization.json'].lfs.manifestSha256);
const retainedNow = treeIdentity(spec.lfsCorrection.retainedStorageRoot);
add(checks, 'RETAINED_STORAGE_UNCHANGED', canonicalJson(retainedNow) === canonicalJson(preflight.retainedLfs.wholeTree), retainedNow, preflight.retainedLfs.wholeTree);

const v03 = JSON.parse(readFileSync(resolve(REPOSITORY_ROOT, 'specs/ai-native-studio-pb1-validation-only-execution.v0.3.json'), 'utf8'));
add(checks, 'COPYING_ASSET_LICENSE_EXACT', sha256File(resolve(source, 'COPYING')) === v03.sourceIdentity.licenses.copyingSha256 && sha256File(resolve(source, 'assets', 'LICENSE')) === v03.sourceIdentity.licenses.assetsLicenseSha256);
const trackedPaths = git(source, ['ls-files', '-z']).split('\0').filter(Boolean).sort();
const notices = trackedPaths.filter(path => /(^|\/)(?:copying|license|notice)(?:[._-]|$)/i.test(path)).sort();
add(checks, 'NOTICE_SET_EXACT', notices.length === v03.sourceIdentity.licenses.noticePathCount && sha256Bytes(`${notices.join('\n')}\n`) === v03.sourceIdentity.licenses.noticePathListSha256);
const generated = trackedPaths.filter(path => /(^|\/)CMakeCache\.txt$/.test(path) || /(^|\/)CMakeFiles\//.test(path) || /(^|\/)build-[^/]+\//.test(path) || /\.dmg$/i.test(path) || /\.app\/Contents\/MacOS\/Blender$/.test(path) || /\.(?:o|dylib|exe)$/i.test(path));
add(checks, 'GENERATED_PRODUCTS_NOT_TRACKED', generated.length === 0, generated, []);
add(checks, 'SECRET_SCAN_ZERO_BOUND', receipts['license-and-generated-paths.json'].inventory.secretScan.findingCount === 0);

add(checks, 'DEPENDENCY_EXACT_CLEAN_LOCAL', git(dependency, ['rev-parse', 'HEAD']) === spec.dependency.commit && git(dependency, ['status', '--porcelain=v1']) === '' && git(dependency, ['remote', 'get-url', 'origin']) === spec.dependency.retainedCheckout);
add(checks, 'RETAINED_DEPENDENCY_UNCHANGED', git(spec.dependency.retainedCheckout, ['rev-parse', 'HEAD']) === spec.dependency.commit && git(spec.dependency.retainedCheckout, ['status', '--porcelain=v1']) === '');

add(checks, 'APP_BINARY_PRESENT', existsSync(app) && existsSync(binary));
const fileIdentity = command(FILE, [binary]);
const architectures = command(LIPO, ['-archs', binary]).split(/\s+/);
add(checks, 'BINARY_ARM64_ONLY', architectures.join(' ') === 'arm64' && /Mach-O 64-bit executable arm64/.test(fileIdentity));
add(checks, 'BUNDLE_ID_NAME_EXACT', plistRaw(plist, 'CFBundleIdentifier') === spec.build.expectedBundleIdentifier && plistRaw(plist, 'CFBundleName') === 'Film Studio Engine F0');
add(checks, 'BINARY_HASH_BOUND', sha256File(binary) === receipts['build.json'].artifact.sha256);
add(checks, 'BUILD_RESOURCE_CEILINGS', receipts['build.json'].process.elapsedSeconds <= spec.resources.maximumBuildWallSeconds && receipts['build.json'].timing.maximumResidentSetSizeBytes <= spec.resources.maximumBuildPeakRssBytes);

const runtime = receipts['runtime-identity.json'];
add(checks, 'TWO_STARTS_ZERO_RENDERS', runtime.productStarts === 2 && runtime.renders === 0 && runtime.runtime.payload.renderCalls === 0);
add(checks, 'RUNTIME_PRODUCT_IDENTITY_EXACT', runtime.runtime.payload.version === spec.build.expectedVersion && runtime.runtime.payload.buildHash.startsWith(spec.build.expectedBuildHashPrefix) && runtime.runtime.payload.binaryPath === binary);
add(checks, 'RUNTIME_CONFIG_PATHS_EXACT', Object.entries(runtime.configuration.expectedPaths).every(([name, path]) => runtime.runtime.payload.paths[name] === path));
add(checks, 'OFFICIAL_CONFIG_UNCHANGED', runtime.configuration.officialBefore.state === runtime.configuration.officialAfter.state && runtime.configuration.officialBefore.digest === runtime.configuration.officialAfter.digest && contentTreeIdentity(runtime.configuration.actualOfficial).digest === runtime.configuration.officialAfter.digest);
add(checks, 'ISOLATED_OFFICIAL_ABSENT_PRODUCT_PRESENT', contentTreeIdentity(runtime.configuration.isolatedOfficial).state === 'ABSENT' && contentTreeIdentity(runtime.configuration.productRoot).state === 'PRESENT');

const live = remote(spec);
add(checks, 'LIVE_PUBLIC_FORK_EXACT', live.metadata.id === spec.repository.repositoryId && live.metadata.fullName === spec.repository.fullName && live.metadata.fork && live.metadata.parent === spec.repository.forkParent && live.metadata.visibility === 'public' && !live.metadata.private);
add(checks, 'LIVE_MAIN_SET_UNCHANGED', live.main === spec.publicationBaseline.head && live.heads.length === 1 && live.tags.length === 0 && live.pulls === 0 && live.releases === 0);
const counters = network.counters;
add(checks, 'AUTHORIZED_COUNTS_EXACT', counters.localEngineClones === 1 && counters.freshObjectsSymlinks === 1 && counters.localLfsMaterializations === 1 && counters.localDependencyClones === 1 && counters.nativeBuilds === 1 && counters.productStarts === 2);
add(checks, 'FORBIDDEN_COUNTS_ZERO', ['publicEngineNetworkClones','renders','engineRemoteWrites','engineRefUpdates','lfsNetworkDownloads','lfsUploads','releases','signing','notarization','dmg','pb2ThroughPb7','modelCalls'].every(name => counters[name] === 0), counters, 'all forbidden zero');
add(checks, 'COMMAND_LOG_NO_REMOTE_WRITE', network.commands.every(item => item.externalWrite === false && !item.args?.includes('push') && !item.args?.includes('tag')));
add(checks, 'COMMAND_LOG_NO_PUBLIC_CLONE_OR_LFS_NETWORK', network.commands.every(item => item.network === 'NONE' && !(item.args?.[0] === 'clone' && item.args?.some(arg => /^https?:/.test(arg)))));
add(checks, 'NO_RELEASE_SIGN_NOTARY_DMG_COMMAND', network.commands.every(item => !/(?:release|codesign|notary|hdiutil)/i.test([item.command, ...(item.args ?? [])].join(' '))));
add(checks, 'ROOTS_WITHIN_CEILINGS', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumAttempt03ExternalRootBytes && treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes);
add(checks, 'STOP_AND_CLAIM_CEILING', verdict.stopRulePreserved === true && verdict.claimCeiling.includes('does not authorize PB.2-PB.7'));

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyC2IndependentAudit.v0.7',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY_C2',
  observedAt: new Date().toISOString(),
  status: failed.length ? 'FAIL' : 'PASS',
  auditor: { path: 'scripts/audit-ai-native-studio-pb1-validation-only-c2.mjs', sha256: sha256File(AUDITOR_PATH), importsRunner: false },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  contract: { path: contractRelative, sha256: sha256File(contractPath) },
  publicationHead: spec.publicationBaseline.head,
  liveMain: live.main,
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
