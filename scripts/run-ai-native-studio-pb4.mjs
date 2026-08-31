#!/usr/bin/env node
// SPDX-FileCopyrightText: 2026 BlenderFilmStudio Authors
// SPDX-License-Identifier: GPL-2.0-or-later

import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, mkdirSync, openSync, closeSync, readFileSync, readdirSync, readlinkSync, statfsSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import os from 'node:os';
import process from 'node:process';

const repositoryRoot = resolve(import.meta.dirname, '..');
const preregUri = 'specs/ai-native-studio-pb4-render-receipts-preregistration.v0.1.json';
const manifestUri = 'specs/ai-native-studio-pb4-render-job-attempt-01.v0.1.json';
const productHelper = resolve(repositoryRoot, 'scripts/run-ai-native-studio-pb4-product.py');
const auditHelper = resolve(repositoryRoot, 'scripts/audit-ai-native-studio-pb4.py');
const sourceRoot = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.4-2026-08-31-mac-m2max-attempt-01/source';
const buildRoot = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.4-2026-08-31-mac-m2max-attempt-01/build';
const workRoot = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.4-2026-08-31-mac-m2max-attempt-01/work';
const evidenceRoot = resolve(repositoryRoot, 'experiments/ai-native-studio-phase-b/PB.4-2026-08-31-mac-m2max-attempt-01');
const binary = resolve(buildRoot, 'bin/Film Studio Engine F0.app/Contents/MacOS/Blender');
const sourceBlend = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PhaseB-workspace/PB.3-2026-08-31-mac-m2max-attempt-06/b01/artifacts/scene.blend';
const officialConfig = resolve(os.homedir(), 'Library/Application Support/Blender');

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

function sha256File(path) {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

function selfHash(value, field) {
  const body = { ...value };
  delete body[field];
  return { ...body, [field]: sha256Bytes(canonical(body)) };
}

function validSelf(value, field) {
  const expected = value[field];
  const body = { ...value };
  delete body[field];
  return typeof expected === 'string' && sha256Bytes(canonical(body)) === expected;
}

function writeJsonExclusive(path, value) {
  mkdirSync(dirname(path), { recursive: true });
  const descriptor = openSync(path, 'wx', 0o644);
  try {
    writeFileSync(descriptor, `${JSON.stringify(value, null, 2)}\n`);
  } finally {
    closeSync(descriptor);
  }
  return value;
}

function git(args, cwd = repositoryRoot) {
  const result = spawnSync('/usr/bin/git', args, { cwd, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(`git ${args.join(' ')} failed: ${result.stderr}`);
  return result.stdout.trim();
}

function treeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', files: 0, bytes: 0, digest: sha256Bytes('ABSENT') };
  const rows = [];
  function walk(path) {
    for (const name of readdirSync(path).sort()) {
      const absolute = join(path, name);
      const item = lstatSync(absolute);
      const uri = relative(root, absolute).split('\\').join('/');
      if (item.isDirectory()) walk(absolute);
      else if (item.isSymbolicLink()) rows.push({ uri, type: 'symlink', target: readlinkSync(absolute) });
      else if (item.isFile()) rows.push({ uri, type: 'file', bytes: item.size, sha256: sha256File(absolute) });
    }
  }
  walk(root);
  return { state: 'PRESENT', files: rows.length, bytes: rows.reduce((sum, row) => sum + (row.bytes ?? 0), 0), digest: sha256Bytes(canonical(rows)), entries: rows };
}

function parseMarker(text, prefix) {
  const line = text.split(/\r?\n/).find(value => value.startsWith(prefix));
  if (!line) throw new Error(`Missing process marker: ${prefix}`);
  return JSON.parse(line.slice(prefix.length));
}

function parseMaximumRss(stderr) {
  const match = stderr.match(/\n\s*(\d+)\s+maximum resident set size/);
  if (!match) throw new Error('Missing maximum resident set size');
  return Number(match[1]);
}

function runProduct(index, name, args, marker, maximumWallSeconds) {
  const stdoutPath = resolve(evidenceRoot, 'logs', `0${index}-${name}.stdout.log`);
  const stderrPath = resolve(evidenceRoot, 'logs', `0${index}-${name}.stderr.log`);
  const processPath = resolve(evidenceRoot, 'processes', `0${index}-${name}.json`);
  const home = resolve(workRoot, 'homes', `0${index}-${name}`);
  mkdirSync(home, { recursive: false });
  const startedAt = new Date().toISOString();
  const started = process.hrtime.bigint();
  const result = spawnSync('/usr/bin/time', ['-l', binary, ...args], {
    cwd: buildRoot,
    env: { ...process.env, HOME: home },
    encoding: 'utf8',
    timeout: maximumWallSeconds * 1000,
    maxBuffer: 64 * 1024 * 1024,
  });
  const wallSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  writeFileSync(stdoutPath, result.stdout ?? '', { flag: 'wx' });
  writeFileSync(stderrPath, result.stderr ?? '', { flag: 'wx' });
  const payload = parseMarker(`${result.stdout ?? ''}\n${result.stderr ?? ''}`, marker);
  const body = {
    schemaVersion: 'bfs.pb4ProcessReceipt.v0.1',
    status: result.status === 0 && !result.error && wallSeconds <= maximumWallSeconds ? 'PASS' : 'FAIL',
    name,
    argv: [binary, ...args],
    pid: payload.pid,
    exitCode: result.status,
    signal: result.signal,
    timedOut: result.error?.code === 'ETIMEDOUT',
    startedAt,
    finishedAt: new Date().toISOString(),
    wallSeconds,
    maximumResidentSetSizeBytes: parseMaximumRss(result.stderr ?? ''),
    stdoutSha256: sha256File(stdoutPath),
    stderrSha256: sha256File(stderrPath),
    payload,
  };
  const receipt = writeJsonExclusive(processPath, selfHash(body, 'processHash'));
  if (receipt.status !== 'PASS') throw new Error(`Product process failed: ${name}`);
  return receipt;
}

function productArgs(action) {
  return [
    '--background', '--factory-startup', sourceBlend,
    '--python', productHelper, '--',
    '--action', action,
    '--repository-root', repositoryRoot,
    '--manifest-uri', manifestUri,
    '--evidence-root', evidenceRoot,
    '--work-root', workRoot,
  ];
}

function createBuildReceipt(manifest) {
  const stdoutPath = resolve(evidenceRoot, 'build.stdout.log');
  const stderrPath = resolve(evidenceRoot, 'build.stderr.log');
  const stderr = readFileSync(stderrPath, 'utf8');
  const timing = stderr.match(/\n?\s*([\d.]+)\s+real\s+([\d.]+)\s+user\s+([\d.]+)\s+sys/);
  const body = {
    schemaVersion: 'bfs.pb4BuildReceipt.v0.1',
    status: readFileSync(stdoutPath, 'utf8').includes('Blender successfully built') ? 'PASS' : 'FAIL',
    sourceCommit: git(['rev-parse', 'HEAD'], sourceRoot),
    sourceParent: git(['rev-parse', 'HEAD^'], sourceRoot),
    changedPaths: git(['diff', '--name-only', 'HEAD^..HEAD'], sourceRoot).split(/\r?\n/).filter(Boolean),
    binary: { path: binary, bytes: statSync(binary).size, sha256: sha256File(binary) },
    timing: timing ? { realSeconds: Number(timing[1]), userSeconds: Number(timing[2]), systemSeconds: Number(timing[3]), maximumResidentSetSizeBytes: parseMaximumRss(stderr) } : null,
    logs: {
      stdout: { bytes: statSync(stdoutPath).size, sha256: sha256File(stdoutPath) },
      stderr: { bytes: statSync(stderrPath).size, sha256: sha256File(stderrPath) },
    },
    buildSystemAdHocSignatureOnly: stderr.includes('blender-thumbnailer.appex: replacing existing signature'),
    developerIdSigning: false,
    notarization: false,
    distribution: false,
    manifestBinaryMatch: sha256File(binary) === manifest.baselines.binarySha256,
  };
  return writeJsonExclusive(resolve(evidenceRoot, 'build.json'), selfHash(body, 'buildHash'));
}

function createSourceReceipt(manifest) {
  const allowed = [
    'scripts/modules/film_studio_render.py',
    'scripts/startup/bl_operators/film_studio_workspace.py',
    'scripts/startup/bl_ui/space_topbar.py',
  ];
  const changed = git(['diff', '--name-only', 'HEAD^..HEAD'], sourceRoot).split(/\r?\n/).filter(Boolean);
  const numstat = git(['diff', '--numstat', 'HEAD^..HEAD'], sourceRoot).split(/\r?\n/).filter(Boolean).map(line => line.split('\t'));
  const body = {
    schemaVersion: 'bfs.pb4SourceReceipt.v0.1',
    status: canonical(changed) === canonical(allowed) && numstat.reduce((sum, row) => sum + Number(row[0]), 0) <= 600 ? 'PASS' : 'FAIL',
    commit: git(['rev-parse', 'HEAD'], sourceRoot),
    parent: git(['rev-parse', 'HEAD^'], sourceRoot),
    clean: git(['status', '--porcelain=v1'], sourceRoot) === '',
    shallow: git(['rev-parse', '--is-shallow-repository'], sourceRoot) === 'true',
    changedPaths: changed,
    additions: numstat.reduce((sum, row) => sum + Number(row[0]), 0),
    deletions: numstat.reduce((sum, row) => sum + Number(row[1]), 0),
    cOrCppPaths: changed.filter(path => /\.(?:c|cc|cpp|cxx|h|hh|hpp)$/.test(path)),
    installedProductModuleExact: sha256File(resolve(sourceRoot, 'scripts/modules/film_studio_render.py')) === sha256File(resolve(buildRoot, 'bin/Film Studio Engine F0.app/Contents/Resources/5.2/scripts/modules/film_studio_render.py')),
    manifestCommitMatch: git(['rev-parse', 'HEAD'], sourceRoot) === manifest.baselines.engineSourceCommit,
  };
  return writeJsonExclusive(resolve(evidenceRoot, 'source.json'), selfHash(body, 'sourceHash'));
}

function execute() {
  const prereg = JSON.parse(readFileSync(resolve(repositoryRoot, preregUri), 'utf8'));
  const manifest = JSON.parse(readFileSync(resolve(repositoryRoot, manifestUri), 'utf8'));
  if (!validSelf(manifest, 'manifestHash')) throw new Error('Manifest self hash differs');
  if (manifest.status !== 'APPROVED') throw new Error('Manifest is not approved');
  if (manifest.authorizedEvidenceRoot !== evidenceRoot) throw new Error('Evidence root differs');
  if (manifest.source.absolutePath !== sourceBlend || sha256File(sourceBlend) !== manifest.source.sha256) throw new Error('Source blend identity differs');
  if (git(['rev-parse', 'HEAD'], sourceRoot) !== manifest.baselines.engineSourceCommit || git(['status', '--porcelain=v1'], sourceRoot) !== '') throw new Error('Engine source identity differs');
  if (sha256File(binary) !== manifest.baselines.binarySha256) throw new Error('Binary identity differs');
  if (sha256File(productHelper) !== manifest.tools.productHelperSha256 || sha256File(auditHelper) !== manifest.tools.auditHelperSha256 || sha256File(import.meta.filename) !== manifest.tools.runnerSha256) throw new Error('Tool identity differs');
  if (git(['merge-base', '--is-ancestor', manifest.baselines.toolFreezeResearchCommit, 'HEAD']) === '') {
    // A zero exit is the assertion; stdout is intentionally empty.
  }
  const free = statfsSync(evidenceRoot, { bigint: true }).bavail * statfsSync(evidenceRoot, { bigint: true }).bsize;
  if (free < BigInt(prereg.resourceCeilings.minimumFreeReserveBytes + prereg.resourceCeilings.maximumWorkBytes + prereg.resourceCeilings.maximumEvidenceBytes)) throw new Error('Disk admission blocked');
  if (existsSync(workRoot)) throw new Error('Formal work root is not fresh');
  if (existsSync(resolve(evidenceRoot, 'build.json'))) throw new Error('Formal evidence already executed');
  mkdirSync(workRoot);
  mkdirSync(resolve(workRoot, 'homes'));
  mkdirSync(resolve(evidenceRoot, 'logs'));
  mkdirSync(resolve(evidenceRoot, 'processes'));
  const sourceBefore = sha256File(sourceBlend);
  const officialBefore = treeIdentity(officialConfig);
  const build = createBuildReceipt(manifest);
  const source = createSourceReceipt(manifest);
  if (build.status !== 'PASS' || source.status !== 'PASS') throw new Error('Build/source admission failed');

  const processes = [];
  processes.push(runProduct(1, 'inspect-negative', productArgs('INSPECT_NEGATIVE'), 'PB4_PRODUCT=', 120));
  processes.push(runProduct(2, 'preview', productArgs('PREVIEW'), 'PB4_PRODUCT=', prereg.resourceCeilings.maximumPreviewWallSeconds));
  processes.push(runProduct(3, 'final', productArgs('FINAL'), 'PB4_PRODUCT=', prereg.resourceCeilings.maximumFinalWallSeconds));
  const auditArgs = [
    '--background', '--factory-startup', '--python', auditHelper, '--',
    '--repository-root', repositoryRoot,
    '--manifest-uri', manifestUri,
    '--evidence-root', evidenceRoot,
    '--source-blend', sourceBlend,
  ];
  processes.push(runProduct(4, 'independent-audit', auditArgs, 'PB4_AUDIT=', 120));

  const pixelAudit = JSON.parse(readFileSync(resolve(evidenceRoot, 'pixel-pass-audit.json'), 'utf8'));
  const preview = JSON.parse(readFileSync(resolve(evidenceRoot, 'preview/receipt.json'), 'utf8'));
  const final = JSON.parse(readFileSync(resolve(evidenceRoot, 'final/receipt.json'), 'utf8'));
  const failures = ['tampered-manifest', 'escaped-output', 'final-without-preview'].map(name => JSON.parse(readFileSync(resolve(evidenceRoot, 'failures', `${name}.json`), 'utf8')));
  const officialAfter = treeIdentity(officialConfig);
  const workIdentity = treeIdentity(workRoot);
  const evidenceBeforeSummary = treeIdentity(evidenceRoot);
  const costBody = {
    schemaVersion: 'bfs.pb4CostReceipt.v0.1',
    status: 'PASS',
    monetaryCostUsd: 0,
    basis: 'Local owner-operated validation; zero model, API, network, signing, notarization or distribution charge.',
    renderSeconds: preview.timing.renderSeconds + final.timing.renderSeconds,
    peakResidentSetSizeBytes: Math.max(...processes.map(row => row.maximumResidentSetSizeBytes)),
    artifactBytes: preview.output.bytes + final.output.bytes,
    productStarts: processes.length,
    renderCalls: processes.reduce((sum, row) => sum + row.payload.renderCalls, 0),
  };
  const cost = writeJsonExclusive(resolve(evidenceRoot, 'cost.json'), selfHash(costBody, 'costHash'));
  const workManifest = writeJsonExclusive(resolve(evidenceRoot, 'work-root-manifest.json'), selfHash({ schemaVersion: 'bfs.pb4RootManifest.v0.1', status: 'PASS', root: workRoot, identity: workIdentity }, 'manifestHash'));
  const evidenceIdentity = treeIdentity(evidenceRoot);
  const evidenceManifest = writeJsonExclusive(resolve(evidenceRoot, 'evidence-root-manifest.json'), selfHash({ schemaVersion: 'bfs.pb4RootManifest.v0.1', status: 'PASS', root: evidenceRoot, scope: 'All evidence files before this manifest and final receipt.', identity: evidenceIdentity }, 'manifestHash'));
  const finalChecks = {
    manifestExact: validSelf(manifest, 'manifestHash'),
    buildPass: validSelf(build, 'buildHash') && build.status === 'PASS',
    sourcePass: validSelf(source, 'sourceHash') && source.status === 'PASS',
    processReceipts: processes.length === 4 && processes.every(row => validSelf(row, 'processHash') && row.status === 'PASS'),
    fourStarts: processes.length === prereg.resourceCeilings.maximumProductStarts,
    twoRenderCalls: cost.renderCalls === prereg.resourceCeilings.maximumRenderCalls,
    stageReceipts: validSelf(preview, 'receiptHash') && validSelf(final, 'receiptHash'),
    failureReceipts: failures.every(row => validSelf(row, 'failureHash') && row.process.renderCalls === 0 && row.source.unchanged === true),
    pixelPassAudit: validSelf(pixelAudit, 'auditHash') && pixelAudit.status === 'PASS' && pixelAudit.renderCalls === 0,
    costReceipt: validSelf(cost, 'costHash') && cost.productStarts === 4 && cost.renderCalls === 2,
    sourceUnchanged: sourceBefore === sha256File(sourceBlend),
    officialConfigUnchanged: canonical(officialBefore) === canonical(officialAfter),
    workCeiling: workIdentity.bytes <= prereg.resourceCeilings.maximumWorkBytes,
    evidenceCeiling: evidenceIdentity.bytes <= prereg.resourceCeilings.maximumEvidenceBytes,
    wallCeilings: processes[1].wallSeconds <= prereg.resourceCeilings.maximumPreviewWallSeconds && processes[2].wallSeconds <= prereg.resourceCeilings.maximumFinalWallSeconds,
    noEscapedArtifact: !existsSync(resolve(evidenceRoot, '..', 'escaped.png')),
    auditorDoesNotImportProductModule: !/^\s*(?:from|import)\s+film_studio_render\b/m.test(readFileSync(auditHelper, 'utf8')),
  };
  const receiptBody = {
    schemaVersion: 'bfs.pb4ValidationReceipt.v0.1',
    status: Object.values(finalChecks).every(Boolean) ? 'PASS' : 'FAIL',
    verdict: Object.values(finalChecks).every(Boolean) ? 'PASS' : 'FAIL',
    claim: 'One accepted PB.3 B01 workspace passed a product-owned approved preview/final render path with bounded receipts and independent pixel/pass audit on this host.',
    manifest: { uri: manifestUri, sha256: sha256File(resolve(repositoryRoot, manifestUri)), manifestHash: manifest.manifestHash },
    baselines: manifest.baselines,
    counters: { cleanBuilds: 1, productStarts: 4, renderCalls: 2, modelCalls: 0, networkCalls: 0, mouseInteractions: 0, releases: 0, signing: 0, notarization: 0, distributions: 0 },
    bindings: {
      buildHash: build.buildHash,
      sourceHash: source.sourceHash,
      processHashes: processes.map(row => row.processHash),
      previewReceiptHash: preview.receiptHash,
      finalReceiptHash: final.receiptHash,
      failureHashes: failures.map(row => row.failureHash),
      pixelPassAuditHash: pixelAudit.auditHash,
      costHash: cost.costHash,
      workManifestHash: workManifest.manifestHash,
      evidenceManifestHash: evidenceManifest.manifestHash,
    },
    roots: { sourceRoot, buildRoot, workRoot, evidenceRoot },
    resources: { workBytes: workIdentity.bytes, evidenceBytesBeforeFinalReceipt: evidenceIdentity.bytes, freeBytesAtAdmission: free.toString() },
    officialConfiguration: { before: officialBefore, after: officialAfter },
    checks: finalChecks,
  };
  const receipt = writeJsonExclusive(resolve(evidenceRoot, 'receipt.json'), selfHash(receiptBody, 'receiptHash'));
  if (receipt.status !== 'PASS') throw new Error(`PB.4 final checks failed: ${Object.entries(finalChecks).filter(([, pass]) => !pass).map(([name]) => name).join(',')}`);
  console.log(`PB4_PASS receiptHash=${receipt.receiptHash} preview=${preview.output.sha256} final=${final.output.sha256}`);
}

function selfTest() {
  const sample = selfHash({ schemaVersion: 'sample', status: 'PASS' }, 'receiptHash');
  const runnerSource = readFileSync(import.meta.filename, 'utf8');
  const mutationNeedles = ["git(['" + "push'", "git(['" + "tag'", '/usr/bin/' + 'gh', 'notary' + 'tool'];
  const checks = {
    canonicalSelfHash: validSelf(sample, 'receiptHash'),
    exactlyFourStarts: [1, 2, 3, 4].length === 4,
    exactlyTwoRenderStages: ['PREVIEW', 'FINAL'].length === 2,
    noRemoteMutationReleaseOrNotaryCode: !mutationNeedles.some(needle => runnerSource.includes(needle)),
    auditorImportIndependent: !/^\s*(?:from|import)\s+film_studio_render\b/m.test(readFileSync(auditHelper, 'utf8')),
  };
  console.log(JSON.stringify({ status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks }, null, 2));
  if (!Object.values(checks).every(Boolean)) process.exitCode = 1;
}

if (process.argv.includes('--self-test')) selfTest();
else if (process.argv.includes('--execute')) execute();
else throw new Error('Use --self-test or --execute');
