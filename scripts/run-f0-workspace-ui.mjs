#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, statfsSync } from 'node:fs';
import { access, lstat, mkdir, open, readFile, readdir, readlink, stat } from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { relative, resolve } from 'node:path';
import process from 'node:process';

const SOURCE_COMMIT = '4f1446f780c2b7e23bc66f584b36f6254ecd985c';
const IDENTITY_COMMIT = '0a25790a1cd6feff4bae1b03d81e4c43ec55a0b5';
const DEPENDENCY_COMMIT = '5a140a8ccc8c070221b1b06e2c6f89f136c5758d';
const BRANCH = 'codex/f0.3-minimum-film-workspace';
const BINARY_SHA256 = 'eedf94e75571b78d83e916f2530630b83ab59927173d784e615392c528107695';
const BUILD_RECEIPT_HASH = '7a0fd8b6d2c4dee792e084acca359f9f6eb2f3d758ca6619ea74d63effab038b';
const OFFICIAL_CONFIG_DIGEST = 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf';
const REQUIRED_FREE_BYTES = 160n * (1024n ** 3n);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const OFFICIAL_CONFIG_ROOT = '/Users/mengyingli/Library/Application Support/Blender';
const SCREENSHOT_NAMES = ['film-start.png', 'film-shot-selected.png', 'expert-mode.png', 'film-roundtrip.png'];

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) {
      throw new Error(`Expected --name value argument, observed ${key ?? '<missing>'}`);
    }
    parsed[key.slice(2)] = value;
  }
  return parsed;
}

function exec(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C' },
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

function git(source, args) {
  return exec('/usr/bin/git', ['-C', source, ...args]);
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

async function sha256File(path) {
  const hash = createHash('sha256');
  const input = createReadStream(path);
  input.on('data', chunk => hash.update(chunk));
  await finished(input);
  return hash.digest('hex');
}

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function writeJsonExclusive(path, value) {
  const bodyWithoutHash = `${JSON.stringify(value, null, 2)}\n`;
  const record = { ...value, receiptHash: sha256Bytes(Buffer.from(bodyWithoutHash)) };
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return record;
}

function verifyReceipt(record) {
  const { receiptHash, ...body } = record;
  return receiptHash === sha256Bytes(Buffer.from(`${JSON.stringify(body, null, 2)}\n`));
}

function freeBytes(path) {
  const value = statfsSync(path, { bigint: true });
  return value.bavail * value.bsize;
}

function sourceIdentity(source) {
  const status = git(source, ['status', '--porcelain=v1']);
  return {
    path: source,
    head: git(source, ['rev-parse', 'HEAD']),
    parent: git(source, ['rev-parse', 'HEAD^']),
    branch: git(source, ['branch', '--show-current']),
    dependency: git(source, ['submodule', 'status', '--', 'lib/macos_arm64']),
    clean: status === '',
    status,
  };
}

function restrictedProcesses() {
  const ownPid = process.pid;
  return exec('/bin/ps', ['-axo', 'pid=,ppid=,comm=,args='])
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .filter(line => {
      const pid = Number(line.split(/\s+/, 1)[0]);
      if (pid === ownPid) return false;
      return /(?:Blender\.app\/Contents\/MacOS\/Blender|Film Studio Engine F0\.app\/Contents\/MacOS\/Blender|\/usr\/bin\/make(?:\s|$)|\bclang(?:\+\+)?\b|\bcmake\b)/.test(line);
    });
}

async function walkTree(root, current = '') {
  const absolute = resolve(root, current);
  const names = await readdir(absolute);
  names.sort((left, right) => left.localeCompare(right, 'en'));
  const records = [];
  for (const name of names) {
    const relativePath = current ? `${current}/${name}` : name;
    const path = resolve(root, relativePath);
    const value = await lstat(path);
    const mode = value.mode & 0o7777;
    if (value.isDirectory()) {
      records.push({ path: relativePath, type: 'directory', mode });
      records.push(...await walkTree(root, relativePath));
    } else if (value.isSymbolicLink()) {
      records.push({ path: relativePath, type: 'symlink', mode, target: await readlink(path) });
    } else if (value.isFile()) {
      records.push({ path: relativePath, type: 'file', mode, bytes: value.size, sha256: await sha256File(path) });
    } else {
      records.push({ path: relativePath, type: 'other', mode, bytes: value.size });
    }
  }
  return records;
}

async function treeIdentity(root) {
  if (!(await exists(root))) {
    return { root, state: 'ABSENT', entries: 0, digest: sha256Bytes(Buffer.from('ABSENT')) };
  }
  const records = await walkTree(root);
  const manifest = `${records.map(record => JSON.stringify(record)).join('\n')}\n`;
  return { root, state: 'PRESENT', entries: records.length, digest: sha256Bytes(Buffer.from(manifest)) };
}

async function fileRecord(repositoryRoot, path) {
  const value = await stat(path);
  return { path: relative(repositoryRoot, path), bytes: value.size, sha256: await sha256File(path) };
}

async function admission({ repositoryRoot, evidenceRoot, workspace, source }) {
  const stageRoot = resolve(evidenceRoot, 'runtime-ui');
  const screenshotsRoot = resolve(evidenceRoot, 'screenshots');
  const binary = resolve(workspace, 'build-f0.3-workspace', 'bin', 'Film Studio Engine F0.app', 'Contents', 'MacOS', 'Blender');
  await mkdir(stageRoot, { recursive: false });
  await mkdir(screenshotsRoot, { recursive: true });
  const identity = sourceIdentity(source);
  const official = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const processes = restrictedProcesses();
  const observedFreeBytes = freeBytes(workspace);
  const failures = [];
  if (identity.head !== SOURCE_COMMIT) failures.push('SOURCE_HEAD_MISMATCH');
  if (identity.parent !== IDENTITY_COMMIT) failures.push('SOURCE_PARENT_MISMATCH');
  if (identity.branch !== BRANCH) failures.push('SOURCE_BRANCH_MISMATCH');
  if (!identity.clean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (!identity.dependency.includes(DEPENDENCY_COMMIT)) failures.push('DEPENDENCY_COMMIT_MISMATCH');
  if (observedFreeBytes < REQUIRED_FREE_BYTES) failures.push('FREE_DISK_BELOW_160_GIB');
  if (processes.length > 0) failures.push('RESTRICTED_NATIVE_PROCESS_ALREADY_RUNNING');
  if (!(await exists(binary))) failures.push('BINARY_MISSING');
  if (await exists(binary) && await sha256File(binary) !== BINARY_SHA256) failures.push('BINARY_HASH_MISMATCH');
  if (official.digest !== OFFICIAL_CONFIG_DIGEST) failures.push('OFFICIAL_CONFIG_DRIFT');
  if (Object.keys(process.env).some(name => name.startsWith('BLENDER_USER_'))) failures.push('BLENDER_USER_OVERRIDE_PRESENT');
  for (const name of SCREENSHOT_NAMES) {
    if (await exists(resolve(screenshotsRoot, name))) failures.push(`SCREENSHOT_ALREADY_EXISTS:${name}`);
  }
  const receipt = await writeJsonExclusive(resolve(stageRoot, 'admission.json'), {
    schemaVersion: 'bfs.f0WorkspaceUiAdmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    observedAt: new Date().toISOString(),
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: identity,
    binary: { path: binary, expectedSha256: BINARY_SHA256 },
    buildReceiptHash: BUILD_RECEIPT_HASH,
    officialConfiguration: official,
    restrictedProcesses: processes,
    expectedScreenshots: SCREENSHOT_NAMES.map(name => relative(repositoryRoot, resolve(screenshotsRoot, name))),
    authorizedNativeJobStarts: failures.length === 0 ? 1 : 0,
    failures,
  });
  process.stdout.write(`F03_UI_ADMISSION_${receipt.status} receipt=${receipt.receiptHash}\n`);
  if (failures.length > 0) process.exitCode = 2;
}

async function finalize({ repositoryRoot, evidenceRoot, workspace, source }) {
  const stageRoot = resolve(evidenceRoot, 'runtime-ui');
  const admissionPath = resolve(stageRoot, 'admission.json');
  const observationPath = resolve(stageRoot, 'observation.json');
  const screenshotsRoot = resolve(evidenceRoot, 'screenshots');
  const baselinePath = resolve(evidenceRoot, 'interaction-baseline.json');
  const admissionRecord = JSON.parse(await readFile(admissionPath, 'utf8'));
  const observation = JSON.parse(await readFile(observationPath, 'utf8'));
  const baseline = JSON.parse(await readFile(baselinePath, 'utf8'));
  const officialAfter = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const identityAfter = sourceIdentity(source);
  const processes = restrictedProcesses();
  const screenshotRecords = {};
  for (const name of SCREENSHOT_NAMES) {
    const path = resolve(screenshotsRoot, name);
    screenshotRecords[name] = await exists(path) ? await fileRecord(repositoryRoot, path) : null;
  }
  const f0Interactions = observation.task?.actualInteractions;
  const officialInteractions = baseline.measurement?.actualInteractions;
  const checks = {
    admissionAcceptedAndAuthentic: admissionRecord.status === 'ACCEPTED' && verifyReceipt(admissionRecord),
    observationPass: observation.status === 'PASS',
    startSurfaceTyped: observation.startSurface?.projectSceneShotCharacterVisible === true,
    noGenericDccNavigation: observation.task?.genericDccNavigationUsed === false,
    oneTaskInteraction: f0Interactions === 1,
    strictInteractionReduction: Number.isInteger(officialInteractions) && f0Interactions < officialInteractions,
    shotCreatedAndSelected: observation.task?.shotCreated === true && observation.task?.shotSelected === true,
    expertWorkspaceComplete: observation.expertRoundtrip?.completeBlenderWorkspaceVisible === true,
    expertNoConversion: observation.expertRoundtrip?.sameOpenSceneWithoutConversion === true,
    filmRoundtripExact: observation.expertRoundtrip?.typedStateExactAfterReturn === true,
    expertInteractionCountExact: observation.expertRoundtrip?.actualInteractions === 2,
    allScreenshotsPresent: Object.values(screenshotRecords).every(Boolean),
    officialConfigUnchanged: officialAfter.digest === OFFICIAL_CONFIG_DIGEST,
    sourceHeadUnchanged: identityAfter.head === SOURCE_COMMIT,
    sourceStillClean: identityAfter.clean,
    noNativeProcessRemaining: processes.length === 0,
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  const receipt = await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0WorkspaceUiReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    status,
    observedAt: new Date().toISOString(),
    admissionReceiptHash: admissionRecord.receiptHash,
    buildReceiptHash: BUILD_RECEIPT_HASH,
    officialInteractions,
    f0Interactions,
    interactionReduction: officialInteractions - f0Interactions,
    observation,
    screenshots: screenshotRecords,
    officialConfigurationAfter: officialAfter,
    sourceAfter: identityAfter,
    restrictedProcessesAfter: processes,
    checks,
    nativeJobStarts: 1,
    failures: Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name),
  });
  process.stdout.write(`F03_UI_${status} receipt=${receipt.receiptHash}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const values = {
    repositoryRoot: resolve(args.repository),
    evidenceRoot: resolve(args.evidence),
    workspace: resolve(args.workspace),
    source: resolve(args.source),
  };
  if (args.mode === 'admit') await admission(values);
  else if (args.mode === 'finalize') await finalize(values);
  else throw new Error(`Unsupported mode: ${args.mode}`);
}

await main();
