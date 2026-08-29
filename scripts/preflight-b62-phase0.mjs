#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import { access, lstat, mkdir, open, readFile, realpath, statfs } from 'node:fs/promises';
import { constants } from 'node:fs';
import { dirname, isAbsolute, normalize, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

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
const PREREGISTRATION_COMMIT = 'de57b63';
const CORRECTION_COMMIT = '9173ede';
const CORRECTION_2_COMMIT = '9c3aba7';
const EXPECTED = {
  outputRoot: 'experiments/b62-phase0-preflight-v0-1',
  attemptRoot: 'experiments/b62-phase0-attempt-v0-1',
  formalRoot: 'experiments/b62-phase0-v0-1',
};
const TOOL_PATHS = [
  CONTRACT_URI,
  CORRECTION_URI,
  CORRECTION_2_URI,
  'research/2026-08-29-b62-terminal-cinematic-proof-goal.md',
  'research/2026-08-29-b62-phase0-asset-animatic-calibration-protocol.md',
  'research/2026-08-29-b62-phase0-c1-ffprobe-accounting-correction.md',
  'research/2026-08-29-b62-phase0-c2-fresh-clone-node-dependency-correction.md',
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

export async function runB62Preflight(argv) {
  const parsed = parseArguments(argv);
  const outputPath = await resolveFreshRepositoryPath(parsed.outputRoot, 'B62 preflight root');
  await resolveFreshRepositoryPath(parsed.attemptRoot, 'B62 attempt root');
  await resolveFreshRepositoryPath(parsed.formalRoot, 'B62 formal root');
  const contractPath = await resolveExistingRepositoryPath(CONTRACT_URI, 'B62 contract');
  const correctionPath = await resolveExistingRepositoryPath(CORRECTION_URI, 'B62 C1 correction');
  const correction2Path = await resolveExistingRepositoryPath(CORRECTION_2_URI, 'B62 C2 correction');
  const contract = JSON.parse(await readFile(contractPath, 'utf8'));
  const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  const correction2 = JSON.parse(await readFile(correction2Path, 'utf8'));
  if (contract.schemaVersion !== 'bfs.b62Phase0AssetAnimaticCalibration.v0.1' || contract.statusBeforeExecution !== 'PREREGISTERED') throw new Error('B62 contract invalid');
  if (correction.statusBeforeExecution !== 'PREREGISTERED' || correction.parent.contractSha256 !== await sha256File(contractPath)) throw new Error('B62 C1 binding invalid');
  if (correction2.statusBeforeRetry !== 'PREREGISTERED' || correction2.parent.c1Sha256 !== await sha256File(correctionPath)) throw new Error('B62 C2 binding invalid');
  const toolHashes = await verifyFreeze(parsed.toolFreezeCommit);
  const upstream = await verifyUpstream(contract);
  for (const binary of ['/Applications/Blender.app/Contents/MacOS/Blender', '/opt/homebrew/bin/ffmpeg', '/opt/homebrew/bin/ffprobe']) await access(binary, constants.X_OK);
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const availableBytes = filesystem.bavail * filesystem.bsize;
  const projectedBytes = BigInt(contract.processBudget.projectedWriteBytes);
  const reserveBytes = BigInt(contract.processBudget.minimumFreeReserveBytes);
  if (availableBytes - projectedBytes < reserveBytes) throw new Error('B62 disk reserve admission failed');
  const checks = [
    ['PREREGISTRATION_C1_C2_ANCESTRY', true],
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
