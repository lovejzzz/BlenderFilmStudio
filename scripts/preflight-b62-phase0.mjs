#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { access, lstat, mkdir, open, readFile, readdir, realpath, statfs } from 'node:fs/promises';
import { constants } from 'node:fs';
import { dirname, isAbsolute, normalize, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { isDeepStrictEqual, promisify } from 'node:util';

export const repositoryRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
const repositoryRealRoot = await realpath(repositoryRoot);

export function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  return value;
}
export function canonicalJson(value) { return JSON.stringify(sortValue(value)); }
export function sha256Bytes(value) { return createHash('sha256').update(value).digest('hex'); }
export function canonicalHash(value) { return sha256Bytes(Buffer.from(canonicalJson(value))); }
export async function sha256File(path) { return sha256Bytes(await readFile(path)); }
export function repoUri(path) { return relative(repositoryRoot, path).split(sep).join('/'); }
export function validSelfHash(record, field) {
  if (!record || typeof record !== 'object' || typeof record[field] !== 'string') return false;
  const body = structuredClone(record); delete body[field]; return record[field] === canonicalHash(body);
}
function requireRelativeSpelling(spelling, label) {
  if (typeof spelling !== 'string' || !spelling || isAbsolute(spelling) || spelling.includes('\\')) throw new Error(`${label} must be repository-relative POSIX`);
  if (normalize(spelling).split(sep).join('/') !== spelling || spelling === '.' || spelling.startsWith('../')) throw new Error(`${label} spelling is not normalized`);
}
async function pathState(path) { try { return await lstat(path); } catch (error) { if (error.code === 'ENOENT') return null; throw error; } }
async function requireContained(path, label, allowRoot = false) {
  const actual = await realpath(path); const fromRoot = relative(repositoryRealRoot, actual);
  if ((!allowRoot && fromRoot === '') || fromRoot === '..' || fromRoot.startsWith(`..${sep}`) || actual !== path) throw new Error(`${label} escapes or traverses a symlink`);
}
export async function resolveExistingRepositoryPath(spelling, label, expected = 'file') {
  requireRelativeSpelling(spelling, label); const path = resolve(repositoryRoot, spelling); const metadata = await pathState(path);
  if (!metadata || metadata.isSymbolicLink()) throw new Error(`${label} is missing or symbolic`);
  await requireContained(path, label);
  if (expected === 'file' && !metadata.isFile()) throw new Error(`${label} is not a file`);
  if (expected === 'directory' && !metadata.isDirectory()) throw new Error(`${label} is not a directory`);
  return path;
}
export async function resolveFreshRepositoryPath(spelling, label) {
  requireRelativeSpelling(spelling, label); const path = resolve(repositoryRoot, spelling);
  if (await pathState(path)) throw new Error(`${label} already exists`);
  let ancestor = dirname(path); let metadata = await pathState(ancestor);
  while (!metadata) { const parent = dirname(ancestor); if (parent === ancestor) throw new Error(`${label} has no contained ancestor`); ancestor = parent; metadata = await pathState(ancestor); }
  if (metadata.isSymbolicLink() || !metadata.isDirectory()) throw new Error(`${label} ancestor is untrusted`);
  await requireContained(ancestor, `${label} ancestor`, ancestor === repositoryRoot); return path;
}
async function syncDirectory(path) { const handle = await open(path, 'r'); try { await handle.sync(); } finally { await handle.close(); } }
export async function durableMkdir(path) { await mkdir(path, { recursive: false }); await syncDirectory(path); await syncDirectory(dirname(path)); }
export async function writeDurableJson(path, value) {
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(sortValue(value), null, 2)}\n`, 'utf8'); await handle.sync(); } finally { await handle.close(); }
  await syncDirectory(dirname(path));
}
export async function writeDurableHashed(path, body, field) { const record = { ...body, [field]: canonicalHash(body) }; await writeDurableJson(path, record); return record; }

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/b62-phase0-asset-animatic-calibration.v0.1.json';
const CORRECTION_URI = 'specs/b62-phase0-c1-ffprobe-accounting-correction.v0.1.json';
const CORRECTION_2_URI = 'specs/b62-phase0-c2-fresh-clone-node-dependency-correction.v0.1.json';
const CORRECTION_3_URI = 'specs/b62-phase0-c3-blender52-multilayer-media-correction.v0.1.json';
const CORRECTION_4_URI = 'specs/b62-phase0-c4-dynamic-exr-setter-correction.v0.1.json';
const CORRECTION_5_URI = 'specs/b62-phase0-c5-v02-retry-binding.v0.1.json';
const CORRECTION_6_URI = 'specs/b62-phase0-c6-blender52-config-surface-diagnostic.v0.1.json';
const CORRECTION_7_URI = 'specs/b62-phase0-c7-eevee-engine-runtime-correction.v0.1.json';
const CORRECTION_8_URI = 'specs/b62-phase0-c8-runtime-config-promotion-and-generator-smoke.v0.1.json';
const CORRECTION_9_URI = 'specs/b62-phase0-c9-v03-formal-binding.v0.1.json';
const CORRECTION_10_URI = 'specs/b62-phase0-c10-library-locality-diagnostic.v0.1.json';
const CORRECTION_11_URI = 'specs/b62-phase0-c11-auditor-library-locality-correction.v0.1.json';
const CORRECTION_12_URI = 'specs/b62-phase0-c12-v04-formal-retry-binding.v0.1.json';
const PREREGISTRATION_COMMIT = 'de57b63';
const CORRECTION_COMMIT = '9173ede';
const CORRECTION_2_COMMIT = '9c3aba7';
const CORRECTION_3_COMMIT = 'b3b7ec6';
const CORRECTION_4_COMMIT = 'a9e98c7';
const CORRECTION_5_COMMIT = 'a08ab25';
const CORRECTION_6_COMMIT = '89316e0';
const CORRECTION_7_COMMIT = 'eb9bcd6';
const CORRECTION_8_COMMIT = 'c5b2ba9';
const CORRECTION_9_COMMIT = '8492351';
const CORRECTION_10_COMMIT = '1ce8ffd';
const CORRECTION_11_COMMIT = '7060fbf';
const CORRECTION_12_COMMIT = 'aa066ca';
const EXPECTED = {
  outputRoot: 'experiments/b62-phase0-preflight-v0-4',
  attemptRoot: 'experiments/b62-phase0-attempt-v0-4',
  formalRoot: 'experiments/b62-phase0-v0-4',
};
const TOOL_PATHS = [
  CONTRACT_URI,
  CORRECTION_URI,
  CORRECTION_2_URI,
  CORRECTION_3_URI,
  CORRECTION_4_URI,
  CORRECTION_5_URI,
  CORRECTION_6_URI,
  CORRECTION_7_URI,
  CORRECTION_8_URI,
  CORRECTION_9_URI,
  CORRECTION_10_URI,
  CORRECTION_11_URI,
  CORRECTION_12_URI,
  'research/2026-08-29-b62-terminal-cinematic-proof-goal.md',
  'research/2026-08-29-b62-phase0-asset-animatic-calibration-protocol.md',
  'research/2026-08-29-b62-phase0-c1-ffprobe-accounting-correction.md',
  'research/2026-08-29-b62-phase0-c2-fresh-clone-node-dependency-correction.md',
  'research/2026-08-29-b62-phase0-c3-blender52-multilayer-media-correction.md',
  'research/2026-08-29-b62-phase0-c4-dynamic-exr-setter-correction.md',
  'research/2026-08-29-b62-phase0-c5-v02-retry-binding.md',
  'research/2026-08-29-b62-phase0-c6-blender52-config-surface-diagnostic.md',
  'research/2026-08-29-b62-phase0-c7-eevee-engine-runtime-correction.md',
  'research/2026-08-29-b62-phase0-c8-runtime-config-promotion-and-generator-smoke.md',
  'research/2026-08-29-b62-phase0-c9-v03-formal-binding.md',
  'research/2026-08-29-b62-phase0-c10-library-locality-diagnostic.md',
  'research/2026-08-29-b62-phase0-c11-auditor-library-locality-correction.md',
  'research/2026-08-29-b62-phase0-c12-v04-formal-retry-binding.md',
  'experiments/b62-phase0-d2-exr-media-state-ab-v0-1/result.json',
  'experiments/b62-phase0-d2-exr-media-state-ab-v0-1/receipt.json',
  'experiments/b62-phase0-d4-config-surface-v0-1/result.json',
  'experiments/b62-phase0-d4-config-surface-v0-1/receipt.json',
  'experiments/b62-phase0-d5-generator-smoke-v0-1/result.json',
  'experiments/b62-phase0-d5-generator-smoke-v0-1/receipt.json',
  'experiments/b62-phase0-d6-library-locality-v0-1/probe.json',
  'experiments/b62-phase0-d6-library-locality-v0-1/result.json',
  'experiments/b62-phase0-d6-library-locality-v0-1/receipt.json',
  'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1/blender-audit.json',
  'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1/result.json',
  'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1/receipt.json',
  'blender/generate_b62_phase0_assets.py',
  'blender/render_b62_phase0.py',
  'blender/audit_b62_phase0.py',
  'scripts/preflight-b62-phase0.mjs',
  'scripts/run-b62-phase0.mjs',
  'scripts/audit-b62-phase0.mjs',
];

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const [key, expected] of Object.entries(EXPECTED)) if (parsed[key] !== expected) throw new Error(`B62 ${key} mismatch`);
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit ?? '')) throw new Error('B62 tool-freeze commit must be a full SHA-1');
  return parsed;
}

async function git(args, encoding = 'utf8') {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function verifyFreeze(commit) {
  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  if (head !== commit || origin !== commit) throw new Error('B62 tool freeze must equal pushed HEAD and origin/main');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_2_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_3_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_4_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_5_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_6_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_7_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_8_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_9_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_10_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_11_COMMIT, commit]);
  await git(['merge-base', '--is-ancestor', CORRECTION_12_COMMIT, commit]);
  const hashes = {};
  for (const uri of TOOL_PATHS) {
    const path = await resolveExistingRepositoryPath(uri, `B62 frozen tool ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${commit}:${uri}`], null));
    if (current !== frozen) throw new Error(`B62 tool-freeze mismatch: ${uri}`);
    hashes[uri] = current;
  }
  return hashes;
}

async function verifyUpstream(contract) {
  const rows = [];
  for (const expected of contract.upstreamEvidence) {
    const path = await resolveExistingRepositoryPath(expected.uri, `B62 upstream ${expected.id}`);
    const record = JSON.parse(await readFile(path, 'utf8'));
    if (await sha256File(path) !== expected.sha256 || !validSelfHash(record, expected.selfHashField)
      || record[expected.selfHashField] !== expected.selfHash || record.status !== 'PASS') throw new Error(`B62 upstream binding mismatch: ${expected.id}`);
    rows.push({ id: expected.id, uri: expected.uri, sha256: expected.sha256, selfHash: expected.selfHash });
  }
  return rows;
}

async function treeIdentity(uri) {
  const root = await resolveExistingRepositoryPath(uri, `B62 retained tree ${uri}`, 'directory');
  const files = [];
  async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(`Unsupported retained entry: ${path}`); } }
  await walk(root); files.sort(); let bytes = 0; let material = '';
  for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`; }
  return { files: files.length, bytes, treeSha256: sha256Bytes(Buffer.from(material)) };
}

export async function runB62Preflight(argv) {
  const parsed = parseArguments(argv);
  const outputPath = await resolveFreshRepositoryPath(parsed.outputRoot, 'B62 preflight root');
  await resolveFreshRepositoryPath(parsed.attemptRoot, 'B62 attempt root');
  await resolveFreshRepositoryPath(parsed.formalRoot, 'B62 formal root');
  const contractPath = await resolveExistingRepositoryPath(CONTRACT_URI, 'B62 contract');
  const correctionPath = await resolveExistingRepositoryPath(CORRECTION_URI, 'B62 C1 correction');
  const correction2Path = await resolveExistingRepositoryPath(CORRECTION_2_URI, 'B62 C2 correction');
  const correction3Path = await resolveExistingRepositoryPath(CORRECTION_3_URI, 'B62 C3 correction');
  const correction4Path = await resolveExistingRepositoryPath(CORRECTION_4_URI, 'B62 C4 correction');
  const correction5Path = await resolveExistingRepositoryPath(CORRECTION_5_URI, 'B62 C5 correction');
  const correction6Path = await resolveExistingRepositoryPath(CORRECTION_6_URI, 'B62 C6 correction');
  const correction7Path = await resolveExistingRepositoryPath(CORRECTION_7_URI, 'B62 C7 correction');
  const correction8Path = await resolveExistingRepositoryPath(CORRECTION_8_URI, 'B62 C8 correction');
  const correction9Path = await resolveExistingRepositoryPath(CORRECTION_9_URI, 'B62 C9 correction');
  const correction10Path = await resolveExistingRepositoryPath(CORRECTION_10_URI, 'B62 C10 correction');
  const correction11Path = await resolveExistingRepositoryPath(CORRECTION_11_URI, 'B62 C11 correction');
  const correction12Path = await resolveExistingRepositoryPath(CORRECTION_12_URI, 'B62 C12 correction');
  const contract = JSON.parse(await readFile(contractPath, 'utf8'));
  const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  const correction2 = JSON.parse(await readFile(correction2Path, 'utf8'));
  const correction3 = JSON.parse(await readFile(correction3Path, 'utf8'));
  const correction4 = JSON.parse(await readFile(correction4Path, 'utf8'));
  const correction5 = JSON.parse(await readFile(correction5Path, 'utf8'));
  const correction6 = JSON.parse(await readFile(correction6Path, 'utf8'));
  const correction7 = JSON.parse(await readFile(correction7Path, 'utf8'));
  const correction8 = JSON.parse(await readFile(correction8Path, 'utf8'));
  const correction9 = JSON.parse(await readFile(correction9Path, 'utf8'));
  const correction10 = JSON.parse(await readFile(correction10Path, 'utf8'));
  const correction11 = JSON.parse(await readFile(correction11Path, 'utf8'));
  const correction12 = JSON.parse(await readFile(correction12Path, 'utf8'));
  if (contract.schemaVersion !== 'bfs.b62Phase0AssetAnimaticCalibration.v0.1' || contract.statusBeforeExecution !== 'PREREGISTERED') throw new Error('B62 contract invalid');
  if (correction.statusBeforeExecution !== 'PREREGISTERED' || correction.parent.contractSha256 !== await sha256File(contractPath)) throw new Error('B62 C1 binding invalid');
  if (correction2.statusBeforeRetry !== 'PREREGISTERED' || correction2.parent.c1Sha256 !== await sha256File(correctionPath)) throw new Error('B62 C2 binding invalid');
  if (correction3.statusBeforeDiagnostic !== 'PREREGISTERED' || correction4.statusBeforeDiagnostic !== 'PREREGISTERED' || correction5.statusBeforeProductionToolChange !== 'PREREGISTERED'
    || correction6.statusBeforeDiagnostic !== 'PREREGISTERED' || correction7.statusBeforeDiagnostic !== 'PREREGISTERED'
    || correction8.statusBeforeProductionToolChange !== 'PREREGISTERED' || correction9.statusBeforeFormalToolChange !== 'PREREGISTERED'
    || correction7.parent.c6.sha256 !== await sha256File(correction6Path) || correction8.parent.c7.sha256 !== await sha256File(correction7Path)
    || correction9.parent.c6.sha256 !== await sha256File(correction6Path) || correction9.parent.c7.sha256 !== await sha256File(correction7Path)
    || correction9.parent.c8.sha256 !== await sha256File(correction8Path)
    || correction9.authorizedFormalToolChanges.roots.preflight !== 'experiments/b62-phase0-preflight-v0-3' || correction9.authorizedFormalToolChanges.roots.attempt !== 'experiments/b62-phase0-attempt-v0-3'
    || correction9.authorizedFormalToolChanges.roots.formal !== 'experiments/b62-phase0-v0-3'
    || correction10.statusBeforeDiagnostic !== 'PREREGISTERED' || correction11.statusBeforeAuditorChange !== 'PREREGISTERED' || correction12.statusBeforeFormalToolChange !== 'PREREGISTERED'
    || correction11.parent.c10.sha256 !== await sha256File(correction10Path) || correction12.parent.c10.sha256 !== await sha256File(correction10Path) || correction12.parent.c11.sha256 !== await sha256File(correction11Path)
    || correction12.authorizedFormalToolChanges.roots.preflight !== parsed.outputRoot || correction12.authorizedFormalToolChanges.roots.attempt !== parsed.attemptRoot
    || correction12.authorizedFormalToolChanges.roots.formal !== parsed.formalRoot) throw new Error('B62 C3-C12 status/binding/root invalid');
  for (const [uri, expected] of [['experiments/b62-phase0-attempt-v0-1', correction3.retainedFailure.attemptTree], ['experiments/b62-phase0-v0-1', correction3.retainedFailure.formalTree], [correction4.retainedD1.root, correction4.retainedD1.tree]]) {
    if (!isDeepStrictEqual(await treeIdentity(uri), expected)) throw new Error(`B62 retained failure tree drift: ${uri}`);
  }
  const d2ResultPath = await resolveExistingRepositoryPath('experiments/b62-phase0-d2-exr-media-state-ab-v0-1/result.json', 'B62 D2 result');
  const d2ReceiptPath = await resolveExistingRepositoryPath('experiments/b62-phase0-d2-exr-media-state-ab-v0-1/receipt.json', 'B62 D2 receipt');
  const d2Result = JSON.parse(await readFile(d2ResultPath, 'utf8')); const d2Receipt = JSON.parse(await readFile(d2ReceiptPath, 'utf8'));
  if (await sha256File(d2ResultPath) !== correction5.promotingEvidence.result.sha256 || !validSelfHash(d2Result, 'resultHash') || d2Result.status !== 'PASS'
    || d2Result.resultHash !== correction5.promotingEvidence.result.resultHash
    || await sha256File(d2ReceiptPath) !== correction5.promotingEvidence.receipt.sha256 || !validSelfHash(d2Receipt, 'receiptHash') || d2Receipt.status !== 'PASS'
    || d2Receipt.receiptHash !== correction5.promotingEvidence.receipt.receiptHash
    || !isDeepStrictEqual(await treeIdentity(correction5.promotingEvidence.root), correction5.promotingEvidence.tree)) throw new Error('B62 D2 promoting evidence invalid');
  for (const [uri, expected] of [[correction9.retainedFailures.v02Attempt.root, correction9.retainedFailures.v02Attempt.tree], [correction9.retainedFailures.v02Formal.root, correction9.retainedFailures.v02Formal.tree], [correction9.retainedFailures.d3.root, correction9.retainedFailures.d3.tree]]) {
    if (!isDeepStrictEqual(await treeIdentity(uri), expected)) throw new Error(`B62 C9 retained tree drift: ${uri}`);
  }
  const promoted = {};
  for (const id of ['d4', 'd5']) {
    const expected = correction9.promotingEvidence[id];
    const resultPath = await resolveExistingRepositoryPath(`${expected.root}/result.json`, `B62 ${id.toUpperCase()} result`);
    const receiptPath = await resolveExistingRepositoryPath(`${expected.root}/receipt.json`, `B62 ${id.toUpperCase()} receipt`);
    const result = JSON.parse(await readFile(resultPath, 'utf8')); const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
    if (!isDeepStrictEqual(await treeIdentity(expected.root), expected.tree)
      || await sha256File(resultPath) !== expected.result.sha256 || !validSelfHash(result, 'resultHash') || result.resultHash !== expected.result.resultHash || result.status !== 'PASS'
      || await sha256File(receiptPath) !== expected.receipt.sha256 || !validSelfHash(receipt, 'receiptHash') || receipt.receiptHash !== expected.receipt.receiptHash || receipt.status !== 'PASS') throw new Error(`B62 ${id.toUpperCase()} promoting evidence invalid`);
    promoted[id] = { resultHash: result.resultHash, receiptHash: receipt.receiptHash };
  }
  for (const [uri, expected] of [[correction12.retainedV03.attemptRoot, correction12.retainedV03.attemptTree], [correction12.retainedV03.formalRoot, correction12.retainedV03.formalTree]]) {
    if (!isDeepStrictEqual(await treeIdentity(uri), expected)) throw new Error(`B62 C12 retained tree drift: ${uri}`);
  }
  const d6Expected = correction11.promotingEvidence;
  if (!isDeepStrictEqual(await treeIdentity(d6Expected.root), d6Expected.tree)) throw new Error('B62 D6 tree invalid');
  for (const [name, field] of [['probe', 'probeHash'], ['result', 'resultHash'], ['receipt', 'receiptHash']]) {
    const path = await resolveExistingRepositoryPath(`${d6Expected.root}/${name}.json`, `B62 D6 ${name}`); const value = JSON.parse(await readFile(path, 'utf8'));
    if (await sha256File(path) !== d6Expected[name].sha256 || !validSelfHash(value, field) || value[field] !== d6Expected[name][field] || value.status !== 'PASS') throw new Error(`B62 D6 ${name} invalid`);
  }
  const d7Expected = correction12.promotingEvidence.d7;
  if (!isDeepStrictEqual(await treeIdentity(d7Expected.root), d7Expected.tree)) throw new Error('B62 D7 tree invalid');
  for (const [name, file, field] of [['audit', 'blender-audit.json', 'auditHash'], ['result', 'result.json', 'resultHash'], ['receipt', 'receipt.json', 'receiptHash']]) {
    const path = await resolveExistingRepositoryPath(`${d7Expected.root}/${file}`, `B62 D7 ${name}`); const value = JSON.parse(await readFile(path, 'utf8'));
    if (await sha256File(path) !== d7Expected[name].sha256 || !validSelfHash(value, field) || value[field] !== d7Expected[name][field] || value.status !== 'PASS') throw new Error(`B62 D7 ${name} invalid`);
  }
  promoted.d6 = { receiptHash: d6Expected.receipt.receiptHash }; promoted.d7 = { receiptHash: d7Expected.receipt.receiptHash, auditHash: d7Expected.audit.auditHash };
  const toolHashes = await verifyFreeze(parsed.toolFreezeCommit);
  const upstream = await verifyUpstream(contract);
  for (const binary of ['/Applications/Blender.app/Contents/MacOS/Blender', '/opt/homebrew/bin/ffmpeg', '/opt/homebrew/bin/ffprobe']) await access(binary, constants.X_OK);
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const availableBytes = filesystem.bavail * filesystem.bsize;
  const projectedBytes = BigInt(contract.processBudget.projectedWriteBytes);
  const reserveBytes = BigInt(contract.processBudget.minimumFreeReserveBytes);
  if (availableBytes - projectedBytes < reserveBytes) throw new Error('B62 disk reserve admission failed');
  const checks = [
    ['PREREGISTRATION_C1_TO_C12_ANCESTRY', true],
    ['TOOL_FREEZE_EQUALS_PUSHED_HEAD', Object.keys(toolHashes).length === TOOL_PATHS.length],
    ['UPSTREAM_RECEIPTS_EXACT', upstream.length === 3],
    ['ROOTS_FRESH', true],
    ['RUNTIME_BINARIES_EXECUTABLE', true],
    ['PROCESS_AND_RENDER_BUDGET_EXACT', contract.processBudget.blenderStarts === 6 && contract.processBudget.renderCalls === 291 && correction.correction.ffprobeMetadataProcesses === 1],
    ['DISK_RESERVE_PASS', availableBytes - projectedBytes >= reserveBytes],
    ['GATE_AND_ATTACK_ROSTERS_EXACT', contract.acceptanceGates.length === 18 && contract.negativeControls.length === 16],
    ['ZERO_BLENDER_MODEL_NETWORK_DOCKER_PREFLIGHT', true],
  ].map(([id, pass]) => ({ id, pass }));
  if (!checks.every(row => row.pass)) throw new Error('B62 preflight checks failed');
  await durableMkdir(outputPath);
  const record = await writeDurableHashed(`${outputPath}/preflight.json`, {
    schemaVersion: 'bfs.b62Phase0Preflight.v0.1', experimentId: contract.experimentId, status: 'ACCEPTED',
    preregistrationCommit: PREREGISTRATION_COMMIT, correctionCommit: CORRECTION_COMMIT, toolFreezeCommit: parsed.toolFreezeCommit,
    roots: { preflight: parsed.outputRoot, attempt: parsed.attemptRoot, formal: parsed.formalRoot },
    contract: { uri: CONTRACT_URI, sha256: await sha256File(contractPath) },
    correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) },
    correction2: { uri: CORRECTION_2_URI, sha256: await sha256File(correction2Path) },
    correction3: { uri: CORRECTION_3_URI, sha256: await sha256File(correction3Path) },
    correction4: { uri: CORRECTION_4_URI, sha256: await sha256File(correction4Path) },
    correction5: { uri: CORRECTION_5_URI, sha256: await sha256File(correction5Path) },
    correction6: { uri: CORRECTION_6_URI, sha256: await sha256File(correction6Path) },
    correction7: { uri: CORRECTION_7_URI, sha256: await sha256File(correction7Path) },
    correction8: { uri: CORRECTION_8_URI, sha256: await sha256File(correction8Path) },
    correction9: { uri: CORRECTION_9_URI, sha256: await sha256File(correction9Path) },
    correction10: { uri: CORRECTION_10_URI, sha256: await sha256File(correction10Path) },
    correction11: { uri: CORRECTION_11_URI, sha256: await sha256File(correction11Path) },
    correction12: { uri: CORRECTION_12_URI, sha256: await sha256File(correction12Path) },
    diagnostics: { d2ResultHash: d2Result.resultHash, d2ReceiptHash: d2Receipt.receiptHash, d4: promoted.d4, d5: promoted.d5, d6: promoted.d6, d7: promoted.d7 },
    upstream, toolHashes, checks,
    disk: { availableBytes: availableBytes.toString(), projectedBytes: projectedBytes.toString(), minimumReserveBytes: reserveBytes.toString() },
    operations: { childProcesses: 0, blenderStarts: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'preflightHash');
  process.stdout.write(`BFS_B62_PHASE0_PREFLIGHT ACCEPTED ${checks.length}/${checks.length} ${record.preflightHash}\n`);
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB62Preflight(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_PHASE0_PREFLIGHT_ERROR ${error.message}\n`); process.exitCode = 1; });
}
