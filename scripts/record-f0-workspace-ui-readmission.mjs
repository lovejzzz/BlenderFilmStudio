#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, statfsSync } from 'node:fs';
import { access, lstat, open, readFile, readdir, readlink } from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { resolve } from 'node:path';
import process from 'node:process';

const SOURCE_COMMIT = '4f1446f780c2b7e23bc66f584b36f6254ecd985c';
const IDENTITY_COMMIT = '0a25790a1cd6feff4bae1b03d81e4c43ec55a0b5';
const DEPENDENCY_COMMIT = '5a140a8ccc8c070221b1b06e2c6f89f136c5758d';
const BRANCH = 'codex/f0.3-minimum-film-workspace';
const BINARY_SHA256 = 'eedf94e75571b78d83e916f2530630b83ab59927173d784e615392c528107695';
const OFFICIAL_CONFIG_DIGEST = 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf';
const PRIOR_ADMISSION_HASH = '52a96a8680c7cb743fac44c8e70eebaec16103ad20804d4b5209bbb75014f3e8';
const REQUIRED_FREE_BYTES = 160n * (1024n ** 3n);
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const OFFICIAL_CONFIG_ROOT = '/Users/mengyingli/Library/Application Support/Blender';
const SCREENSHOT_NAMES = ['film-start.png', 'film-shot-selected.png', 'expert-mode.png', 'film-roundtrip.png'];

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) throw new Error(`Invalid argument: ${key}`);
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

function verifyReceipt(record) {
  const { receiptHash, ...body } = record;
  return receiptHash === sha256Bytes(Buffer.from(`${JSON.stringify(body, null, 2)}\n`));
}

async function writeJsonExclusive(path, value) {
  const body = `${JSON.stringify(value, null, 2)}\n`;
  const record = { ...value, receiptHash: sha256Bytes(Buffer.from(body)) };
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return record;
}

async function walkTree(root, current = '') {
  const names = await readdir(resolve(root, current));
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
  if (!(await exists(root))) return { root, state: 'ABSENT', entries: 0, digest: sha256Bytes(Buffer.from('ABSENT')) };
  const records = await walkTree(root);
  const manifest = `${records.map(record => JSON.stringify(record)).join('\n')}\n`;
  return { root, state: 'PRESENT', entries: records.length, digest: sha256Bytes(Buffer.from(manifest)) };
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

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const repositoryRoot = resolve(args.repository);
  const evidenceRoot = resolve(args.evidence);
  const workspace = resolve(args.workspace);
  const source = resolve(args.source);
  const stageRoot = resolve(evidenceRoot, 'runtime-ui');
  const priorPath = resolve(stageRoot, 'admission.json');
  const outputPath = resolve(stageRoot, 'readmission-after-unlock.json');
  const binary = resolve(workspace, 'build-f0.3-workspace', 'bin', 'Film Studio Engine F0.app', 'Contents', 'MacOS', 'Blender');
  const prior = JSON.parse(await readFile(priorPath, 'utf8'));
  const sourceStatus = git(source, ['status', '--porcelain=v1']);
  const identity = {
    path: source,
    head: git(source, ['rev-parse', 'HEAD']),
    parent: git(source, ['rev-parse', 'HEAD^']),
    branch: git(source, ['branch', '--show-current']),
    dependency: git(source, ['submodule', 'status', '--', 'lib/macos_arm64']),
    clean: sourceStatus === '',
    status: sourceStatus,
  };
  const official = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const processes = restrictedProcesses();
  const stat = statfsSync(workspace, { bigint: true });
  const observedFreeBytes = stat.bavail * stat.bsize;
  const failures = [];
  if (!verifyReceipt(prior) || prior.receiptHash !== PRIOR_ADMISSION_HASH || prior.status !== 'ACCEPTED') failures.push('PRIOR_ADMISSION_INVALID');
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
  if (await exists(resolve(stageRoot, 'receipt.json'))) failures.push('UI_RECEIPT_ALREADY_EXISTS');
  if (await exists(resolve(stageRoot, 'observation.json'))) failures.push('UI_OBSERVATION_ALREADY_EXISTS');
  for (const name of SCREENSHOT_NAMES) {
    if (await exists(resolve(evidenceRoot, 'screenshots', name))) failures.push(`SCREENSHOT_ALREADY_EXISTS:${name}`);
  }
  const record = await writeJsonExclusive(outputPath, {
    schemaVersion: 'bfs.f0WorkspaceUiReadmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.3',
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    reason: 'Fresh just-in-time readmission after the user manually unlocked macOS; the prior accepted admission started zero native processes.',
    observedAt: new Date().toISOString(),
    priorAdmissionReceiptHash: prior.receiptHash,
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: identity,
    binary: { path: binary, expectedSha256: BINARY_SHA256 },
    officialConfiguration: official,
    restrictedProcesses: processes,
    failures,
    priorNativeJobStarts: 0,
    authorizedNativeJobStarts: failures.length === 0 ? 1 : 0,
  });
  process.stdout.write(`F03_UI_READMISSION_${record.status} receipt=${record.receiptHash}\n`);
  if (failures.length > 0) process.exitCode = 2;
}

await main();
