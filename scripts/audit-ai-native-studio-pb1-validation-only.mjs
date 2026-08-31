#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  closeSync,
  existsSync,
  lstatSync,
  openSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { dirname, resolve } from 'node:path';
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
const SPEC_RELATIVE = 'specs/ai-native-studio-pb1-validation-only-execution.v0.3.json';
const RUNNER_RELATIVE = 'scripts/run-ai-native-studio-pb1-validation-only.mjs';
const SPEC_PATH = resolve(REPOSITORY_ROOT, SPEC_RELATIVE);
const RUNNER_PATH = resolve(REPOSITORY_ROOT, RUNNER_RELATIVE);
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

function execResult(command, args, options = {}) {
  try {
    const stdout = execFileSync(command, args, {
      cwd: options.cwd,
      encoding: options.encoding ?? 'utf8',
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
      timeout: options.timeout ?? 20 * 60 * 1000,
      maxBuffer: options.maxBuffer ?? 512 * 1024 * 1024,
    });
    return { exitCode: 0, stdout, stderr: '' };
  } catch (error) {
    return { exitCode: Number.isInteger(error.status) ? error.status : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? String(error.message ?? error) };
  }
}

function asText(value) {
  return Buffer.isBuffer(value) ? value.toString('utf8').trim() : String(value ?? '').trim();
}

function command(commandPath, args, options = {}) {
  const result = execResult(commandPath, args, options);
  if (result.exitCode !== 0) throw new Error(`Audit command failed (${result.exitCode}): ${commandPath} ${args.join(' ')}\n${asText(result.stderr)}`);
  return options.encoding === null ? result.stdout : asText(result.stdout);
}

function git(root, args, options = {}) {
  return command(GIT, ['-C', root, ...args], options);
}

function ghJson(args) {
  return JSON.parse(command(GH, args));
}

function treeBytes(path) {
  if (!existsSync(path)) return 0;
  return Number(command(DU, ['-sk', path]).split(/\s+/)[0]) * 1024;
}

function parseRemoteRefs(text) {
  return text.split(/\r?\n/).filter(Boolean).map(line => {
    const match = line.match(/^([0-9a-f]{40})\s+(.+)$/);
    if (!match) throw new Error(`Unexpected ls-remote line: ${line}`);
    return { oid: match[1], ref: match[2] };
  });
}

function collectRemote(spec) {
  const metadata = ghJson(['api', `repos/${spec.repository.fullName}`]);
  const branches = ghJson(['api', `repos/${spec.repository.fullName}/branches?per_page=100`]);
  const pulls = ghJson(['api', `repos/${spec.repository.fullName}/pulls?state=all&per_page=100`]);
  const releases = ghJson(['api', `repos/${spec.repository.fullName}/releases?per_page=100`]);
  const heads = parseRemoteRefs(command(GIT, ['ls-remote', '--heads', spec.repository.url]));
  const tags = parseRemoteRefs(command(GIT, ['ls-remote', '--tags', spec.repository.url]));
  return {
    metadata: { id: metadata.id, fullName: metadata.full_name, fork: metadata.fork, parent: metadata.parent?.full_name ?? null, visibility: metadata.visibility, private: metadata.private, defaultBranch: metadata.default_branch },
    branches: branches.map(item => item.name).sort(),
    heads,
    tags,
    main: heads.find(item => item.ref === 'refs/heads/main')?.oid ?? null,
    pullRequests: pulls.length,
    releases: releases.length,
  };
}

function treeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', entries: 0, digest: sha256Bytes('ABSENT') };
  const records = [];
  function walk(path, prefix = '') {
    for (const name of readdirSync(path).sort((left, right) => left.localeCompare(right, 'en'))) {
      const absolute = resolve(path, name);
      const item = lstatSync(absolute);
      const relativePath = prefix ? `${prefix}/${name}` : name;
      if (item.isDirectory()) {
        records.push({ path: relativePath, type: 'directory', mode: item.mode & 0o7777 });
        walk(absolute, relativePath);
      } else if (item.isFile()) {
        records.push({ path: relativePath, type: 'file', mode: item.mode & 0o7777, bytes: item.size, sha256: sha256File(absolute) });
      } else if (item.isSymbolicLink()) records.push({ path: relativePath, type: 'symlink', mode: item.mode & 0o7777 });
    }
  }
  walk(root);
  return { state: 'PRESENT', entries: records.length, digest: sha256Bytes(canonicalJson(records)) };
}

function materializedLfsInventory(source) {
  const files = JSON.parse(git(source, ['lfs', 'ls-files', '--json'])).files.sort((left, right) => left.name.localeCompare(right.name, 'en'));
  const mismatches = [];
  let bytes = 0;
  const manifest = [];
  for (const item of files) {
    const path = resolve(source, item.name);
    if (!existsSync(path)) {
      mismatches.push({ path: item.name, failure: 'MISSING' });
      continue;
    }
    const observedBytes = statSync(path).size;
    const observedSha256 = sha256File(path);
    bytes += observedBytes;
    manifest.push(`${item.name}\0${observedBytes}\0${observedSha256}`);
    if (observedBytes !== item.size || observedSha256 !== item.oid) mismatches.push({ path: item.name });
  }
  return {
    count: files.length,
    bytes,
    downloadedCount: files.filter(item => item.downloaded).length,
    checkoutCount: files.filter(item => item.checkout).length,
    manifestSha256: sha256Bytes(`${manifest.join('\n')}\n`),
    mismatches,
  };
}

function plistRaw(path, key) {
  const result = execResult(PLUTIL, ['-extract', key, 'raw', path]);
  return result.exitCode === 0 ? asText(result.stdout) : null;
}

function readReceipt(evidenceRoot, name) {
  return JSON.parse(readFileSync(resolve(evidenceRoot, name), 'utf8'));
}

function add(checks, id, pass, observed = null, expected = true) {
  checks.push({ id, pass: Boolean(pass), observed, expected });
}

const spec = JSON.parse(readFileSync(SPEC_PATH, 'utf8'));
const evidenceRoot = resolve(REPOSITORY_ROOT, spec.paths.evidenceRoot);
const auditPath = resolve(evidenceRoot, 'audit.json');
if (!existsSync(evidenceRoot)) throw new Error(`Evidence root missing: ${evidenceRoot}`);
if (existsSync(auditPath)) throw new Error(`Audit already exists: ${auditPath}`);

const requiredBeforeAudit = spec.requiredEvidence.filter(name => name !== 'audit.json');
for (const name of requiredBeforeAudit) if (!existsSync(resolve(evidenceRoot, name))) throw new Error(`Required evidence missing: ${name}`);

const receipts = Object.fromEntries(requiredBeforeAudit.map(name => [name, readReceipt(evidenceRoot, name)]));
const network = readReceipt(evidenceRoot, 'network-and-mutation-log.json');
const source = spec.paths.sourceRoot;
const dependency = resolve(source, 'lib', 'macos_arm64');
const app = resolve(spec.paths.buildRoot, 'bin', spec.build.expectedApplicationName);
const binary = resolve(app, 'Contents', 'MacOS', 'Blender');
const plist = resolve(app, 'Contents', 'Info.plist');
const checks = [];

add(checks, 'AUDITOR_DOES_NOT_IMPORT_RUNNER', !readFileSync(AUDITOR_PATH, 'utf8').includes(`from '${RUNNER_RELATIVE}'`) && !readFileSync(AUDITOR_PATH, 'utf8').includes(`from "${RUNNER_RELATIVE}"`));
add(checks, 'SPEC_AUTHORIZED', spec.authorization.granted === true);
add(checks, 'PUBLICATION_HEAD_FIXED', spec.publicationBaseline.head === '4061e12bd45a2bec83e68d0cf49abbf56d4738f6');
add(checks, 'F0_PARENT_FIXED', spec.publicationBaseline.soleParent === 'fa1b578bb421bbc82b3106b7d4223e11e65fae1d');

for (const [name, receipt] of Object.entries(receipts)) {
  add(checks, `RECEIPT_HASH_${name}`, receiptHashPass(receipt), receipt.receiptHash, receiptHash(receipt));
  add(checks, `RECEIPT_STATUS_${name}`, receipt.status === 'PASS' || (name === 'preflight.json' && receipt.status === 'ACCEPTED'), receipt.status, 'PASS/ACCEPTED');
}
add(checks, 'VERDICT_PASS', receipts['verdict.json'].status === 'PASS', receipts['verdict.json'].status, 'PASS');
add(checks, 'NINE_NEGATIVE_CONTROLS', receipts['negative-controls.json'].checksPassed === 9 && receipts['negative-controls.json'].checksTotal === 9 && receipts['negative-controls.json'].controls.every(item => item.pass));
add(checks, 'NEGATIVE_CONTROLS_BEFORE_EXTERNAL_ROOT', receipts['negative-controls.json'].externalRootExistedDuringControls === false);

const remote = collectRemote(spec);
add(checks, 'LIVE_REPOSITORY_ID', remote.metadata.id === spec.repository.repositoryId && remote.metadata.fullName === spec.repository.fullName, remote.metadata, { id: spec.repository.repositoryId, fullName: spec.repository.fullName });
add(checks, 'LIVE_PUBLIC_FORK_PARENT', remote.metadata.fork === true && remote.metadata.parent === spec.repository.forkParent && remote.metadata.visibility === 'public' && remote.metadata.private === false);
add(checks, 'LIVE_MAIN_EXACT', remote.main === spec.publicationBaseline.head, remote.main, spec.publicationBaseline.head);
add(checks, 'LIVE_ONLY_MAIN', remote.branches.join('\n') === 'main' && remote.heads.length === 1);
add(checks, 'LIVE_ZERO_TAGS', remote.tags.length === 0);
add(checks, 'LIVE_ZERO_PR_RELEASE', remote.pullRequests === 0 && remote.releases === 0, { pullRequests: remote.pullRequests, releases: remote.releases }, { pullRequests: 0, releases: 0 });
add(checks, 'REMOTE_BEFORE_AFTER_EXACT', network.remoteBefore.mainOid === network.remoteAfter.mainOid && network.remoteAfter.mainOid === remote.main);

const sourceHead = git(source, ['rev-parse', 'HEAD']);
const sourceTree = git(source, ['rev-parse', 'HEAD^{tree}']);
const sourceParents = git(source, ['show', '-s', '--format=%P', 'HEAD']);
const sourceStatus = git(source, ['status', '--porcelain=v1']);
const sourceShallow = git(source, ['rev-parse', '--is-shallow-repository']) === 'true';
const reachable = Number(git(source, ['rev-list', '--count', 'HEAD']));
const mergeBase = git(source, ['merge-base', spec.publicationBaseline.mergeBase, 'HEAD']);
const forkCommits = Number(git(source, ['rev-list', '--count', `${spec.publicationBaseline.mergeBase}..HEAD`]));
const fsck = execResult(GIT, ['-C', source, 'fsck', '--full', '--strict']);
add(checks, 'SOURCE_HEAD_EXACT', sourceHead === spec.publicationBaseline.head, sourceHead, spec.publicationBaseline.head);
add(checks, 'SOURCE_TREE_EXACT', sourceTree === spec.publicationBaseline.tree, sourceTree, spec.publicationBaseline.tree);
add(checks, 'SOURCE_SOLE_PARENT_EXACT', sourceParents === spec.publicationBaseline.soleParent, sourceParents, spec.publicationBaseline.soleParent);
add(checks, 'SOURCE_CLEAN', sourceStatus === '', sourceStatus, '');
add(checks, 'SOURCE_NON_SHALLOW', !sourceShallow, sourceShallow, false);
add(checks, 'REACHABLE_COMMITS_EXACT', reachable === spec.publicationBaseline.reachableCommitCount, reachable, spec.publicationBaseline.reachableCommitCount);
add(checks, 'MERGE_BASE_EXACT', mergeBase === spec.publicationBaseline.mergeBase, mergeBase, spec.publicationBaseline.mergeBase);
add(checks, 'FORK_COMMIT_COUNT_EXACT', forkCommits === spec.publicationBaseline.forkCommitCount, forkCommits, spec.publicationBaseline.forkCommitCount);
add(checks, 'FULL_FSCK_PASS', fsck.exitCode === 0, asText(fsck.stderr), '');
const c1Paths = git(source, ['diff', '--name-only', `${spec.publicationBaseline.soleParent}..HEAD`]).split(/\r?\n/).filter(Boolean).sort();
add(checks, 'C1_THREE_PATHS_EXACT', c1Paths.join('\n') === [...spec.publicationBaseline.c1ChangedPaths].sort().join('\n'), c1Paths, [...spec.publicationBaseline.c1ChangedPaths].sort());

for (const item of spec.sourceIdentity.ordinaryBrandBlobs) {
  const path = resolve(source, item.path);
  const oid = git(source, ['rev-parse', `HEAD:${item.path}`]);
  add(checks, `BRAND_OID_${item.path}`, oid === item.gitBlobOidSha1, oid, item.gitBlobOidSha1);
  add(checks, `BRAND_BYTES_${item.path}`, statSync(path).size === item.bytes, statSync(path).size, item.bytes);
  add(checks, `BRAND_SHA_${item.path}`, sha256File(path) === item.sha256, sha256File(path), item.sha256);
  const attrs = git(source, ['check-attr', 'filter', 'diff', 'merge', 'text', '--', item.path]);
  add(checks, `BRAND_ATTRIBUTES_UNSET_${item.path}`, attrs.split(/\r?\n/).every(line => line.endsWith(': unset')), attrs, 'all unset');
}

const lfs = materializedLfsInventory(source);
add(checks, 'LFS_COUNT_EXACT', lfs.count === spec.sourceIdentity.lfs.trackedPathsAtPublicationHead, lfs.count, spec.sourceIdentity.lfs.trackedPathsAtPublicationHead);
add(checks, 'LFS_BYTES_EXACT', lfs.bytes === spec.sourceIdentity.lfs.contentBytesAtPublicationHead, lfs.bytes, spec.sourceIdentity.lfs.contentBytesAtPublicationHead);
add(checks, 'LFS_ALL_DOWNLOADED', lfs.downloadedCount === lfs.count, lfs.downloadedCount, lfs.count);
add(checks, 'LFS_ALL_CHECKOUT', lfs.checkoutCount === lfs.count, lfs.checkoutCount, lfs.count);
add(checks, 'LFS_HASHES_EXACT', lfs.mismatches.length === 0, lfs.mismatches, []);
add(checks, 'LFS_MANIFEST_BOUND', lfs.manifestSha256 === receipts['source-identity.json'].lfs.manifestSha256, lfs.manifestSha256, receipts['source-identity.json'].lfs.manifestSha256);

add(checks, 'COPYING_EXACT', sha256File(resolve(source, 'COPYING')) === spec.sourceIdentity.licenses.copyingSha256);
add(checks, 'ASSETS_LICENSE_EXACT', sha256File(resolve(source, 'assets', 'LICENSE')) === spec.sourceIdentity.licenses.assetsLicenseSha256);
const trackedPaths = git(source, ['ls-files', '-z']).split('\0').filter(Boolean).sort();
const noticePaths = trackedPaths.filter(path => /(^|\/)(?:copying|license|notice)(?:[._-]|$)/i.test(path)).sort();
add(checks, 'NOTICE_COUNT_EXACT', noticePaths.length === spec.sourceIdentity.licenses.noticePathCount, noticePaths.length, spec.sourceIdentity.licenses.noticePathCount);
add(checks, 'NOTICE_LIST_EXACT', sha256Bytes(`${noticePaths.join('\n')}\n`) === spec.sourceIdentity.licenses.noticePathListSha256);
const generatedPaths = trackedPaths.filter(path => /(^|\/)CMakeCache\.txt$/.test(path) || /(^|\/)CMakeFiles\//.test(path) || /(^|\/)build-[^/]+\//.test(path) || /\.dmg$/i.test(path) || /\.app\/Contents\/MacOS\/Blender$/.test(path) || /\.(?:o|dylib|exe)$/i.test(path));
add(checks, 'GENERATED_PRODUCTS_NOT_TRACKED', generatedPaths.length === 0, generatedPaths, []);
add(checks, 'SECRET_SCAN_ZERO_BOUND', receipts['license-and-generated-paths.json'].inventory.secretScan.findingCount === 0);

add(checks, 'DEPENDENCY_HEAD_EXACT', git(dependency, ['rev-parse', 'HEAD']) === spec.dependency.commit, git(dependency, ['rev-parse', 'HEAD']), spec.dependency.commit);
add(checks, 'DEPENDENCY_CLEAN', git(dependency, ['status', '--porcelain=v1']) === '');
add(checks, 'DEPENDENCY_LOCAL_ORIGIN', git(dependency, ['remote', 'get-url', 'origin']) === spec.dependency.retainedCheckout, git(dependency, ['remote', 'get-url', 'origin']), spec.dependency.retainedCheckout);
add(checks, 'RETAINED_DEPENDENCY_UNCHANGED', git(spec.dependency.retainedCheckout, ['rev-parse', 'HEAD']) === spec.dependency.commit && git(spec.dependency.retainedCheckout, ['status', '--porcelain=v1']) === '');

add(checks, 'PRODUCT_APP_PRESENT', existsSync(app));
add(checks, 'PRODUCT_BINARY_PRESENT', existsSync(binary));
const fileIdentity = command(FILE, [binary]);
const architectures = command(LIPO, ['-archs', binary]).split(/\s+/).filter(Boolean);
add(checks, 'PRODUCT_ARM64_ONLY', architectures.join(' ') === 'arm64' && /Mach-O 64-bit executable arm64/.test(fileIdentity), { architectures, fileIdentity }, 'arm64 Mach-O');
add(checks, 'BUNDLE_IDENTIFIER_EXACT', plistRaw(plist, 'CFBundleIdentifier') === spec.build.expectedBundleIdentifier, plistRaw(plist, 'CFBundleIdentifier'), spec.build.expectedBundleIdentifier);
add(checks, 'BUNDLE_NAME_EXACT', plistRaw(plist, 'CFBundleName') === 'Film Studio Engine F0', plistRaw(plist, 'CFBundleName'), 'Film Studio Engine F0');
add(checks, 'BINARY_SHA_BOUND', sha256File(binary) === receipts['build.json'].artifact.binarySha256, sha256File(binary), receipts['build.json'].artifact.binarySha256);
add(checks, 'BUILD_WALL_WITHIN_CEILING', receipts['build.json'].process.elapsedSeconds <= spec.resources.maximumBuildWallSeconds, receipts['build.json'].process.elapsedSeconds, spec.resources.maximumBuildWallSeconds);
add(checks, 'BUILD_RSS_WITHIN_CEILING', receipts['build.json'].timing.maximumResidentSetSizeBytes <= spec.resources.maximumBuildPeakRssBytes, receipts['build.json'].timing.maximumResidentSetSizeBytes, spec.resources.maximumBuildPeakRssBytes);

const runtime = receipts['runtime-identity.json'];
add(checks, 'TWO_PRODUCT_STARTS', runtime.productStarts === 2 && network.counters.productStarts === 2, { runtime: runtime.productStarts, counters: network.counters.productStarts }, 2);
add(checks, 'ZERO_RENDERS', runtime.renders === 0 && runtime.configurationProcess.payload.renderCalls === 0 && network.counters.renderCalls === 0);
add(checks, 'RUNTIME_VERSION_EXACT', runtime.configurationProcess.payload.version === spec.build.expectedVersion, runtime.configurationProcess.payload.version, spec.build.expectedVersion);
add(checks, 'RUNTIME_BUILD_HASH_EXACT', runtime.configurationProcess.payload.buildHash.startsWith(spec.build.expectedBuildHashPrefix), runtime.configurationProcess.payload.buildHash, spec.build.expectedBuildHashPrefix);
add(checks, 'RUNTIME_BINARY_EXACT', runtime.configurationProcess.payload.binaryPath === binary, runtime.configurationProcess.payload.binaryPath, binary);
add(checks, 'RUNTIME_PATHS_EXACT', Object.entries(runtime.configuration.expectedPaths).every(([name, path]) => runtime.configurationProcess.payload.paths[name] === path));
add(checks, 'OFFICIAL_CONFIGURATION_UNCHANGED', runtime.configuration.officialBefore.state === runtime.configuration.officialAfter.state && runtime.configuration.officialBefore.digest === runtime.configuration.officialAfter.digest);
add(checks, 'OFFICIAL_CONFIGURATION_LIVE_STILL_BOUND', treeIdentity(runtime.configuration.actualOfficialRoot).digest === runtime.configuration.officialAfter.digest);
add(checks, 'ISOLATED_OFFICIAL_CONFIGURATION_ABSENT', treeIdentity(runtime.configuration.isolatedOfficialRoot).state === 'ABSENT');
add(checks, 'PRODUCT_CONFIGURATION_PRESENT', treeIdentity(runtime.configuration.expectedProductRoot).state === 'PRESENT');

const counters = network.counters;
add(checks, 'ONE_PUBLIC_ENGINE_CLONE', counters.publicEngineNetworkClones === 1);
add(checks, 'ONE_LOCAL_LFS_MATERIALIZATION', counters.localLfsMaterializations === 1);
add(checks, 'ONE_LOCAL_DEPENDENCY_CLONE', counters.localDependencyClones === 1);
add(checks, 'ONE_NATIVE_BUILD', counters.cleanNativeArm64Builds === 1);
add(checks, 'ZERO_FORBIDDEN_COUNTERS', ['renderCalls', 'engineRemoteWrites', 'engineRefUpdates', 'lfsNetworkDownloads', 'lfsUploads', 'releases', 'signingOperations', 'notarizationOperations', 'dmgOperations', 'pb2ThroughPb7Mutations', 'modelCalls'].every(name => counters[name] === 0), counters, 'forbidden counters zero');
add(checks, 'COMMAND_LOG_ZERO_REMOTE_WRITE', network.commands.every(item => item.externalWrite === false && !item.args?.includes('push') && !item.args?.includes('tag')), network.commands.filter(item => item.externalWrite || item.args?.includes('push') || item.args?.includes('tag')), []);
add(checks, 'COMMAND_LOG_ZERO_LFS_NETWORK', network.commands.filter(item => item.args?.[2] === 'lfs' || item.args?.includes('lfs')).every(item => item.operation === 'single local-only LFS checkout' || item.operation === 'bind retained local LFS storage' || item.operation === 'disable LFS network endpoint'));
add(checks, 'NO_RELEASE_SIGN_NOTARY_DMG_COMMAND', network.commands.every(item => !/(?:release|codesign|notary|hdiutil)/i.test([item.command, ...(item.args ?? [])].join(' '))));
add(checks, 'REMOTE_MAIN_UNCHANGED', network.remoteMainUnchanged === true && remote.main === spec.publicationBaseline.head);
add(checks, 'EXTERNAL_ROOT_WITHIN_CEILING', treeBytes(spec.paths.externalRoot) <= spec.resources.maximumExternalRootBytes, treeBytes(spec.paths.externalRoot), spec.resources.maximumExternalRootBytes);
add(checks, 'EVIDENCE_ROOT_WITHIN_CEILING', treeBytes(evidenceRoot) <= spec.resources.maximumEvidenceRootBytes, treeBytes(evidenceRoot), spec.resources.maximumEvidenceRootBytes);
add(checks, 'CLAIM_CEILING_PRESENT', receipts['verdict.json'].claimCeiling.includes('does not authorize PB.2-PB.7'));
add(checks, 'STOP_RULE_PRESERVED', receipts['verdict.json'].stopRulePreserved === true);

const failed = checks.filter(item => !item.pass);
const audit = writeJsonExclusive(auditPath, {
  schemaVersion: 'bfs.pb1ValidationOnlyIndependentAudit.v0.3',
  gate: 'PB.1',
  mode: 'VALIDATION_ONLY',
  observedAt: new Date().toISOString(),
  status: failed.length === 0 ? 'PASS' : 'FAIL',
  auditor: { path: 'scripts/audit-ai-native-studio-pb1-validation-only.mjs', sha256: sha256File(AUDITOR_PATH), importsRunner: false },
  runner: { path: RUNNER_RELATIVE, sha256: sha256File(RUNNER_PATH) },
  specification: { path: SPEC_RELATIVE, sha256: sha256File(SPEC_PATH) },
  publicationHead: spec.publicationBaseline.head,
  f0CodeIdentityParent: spec.publicationBaseline.soleParent,
  liveMain: remote.main,
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
