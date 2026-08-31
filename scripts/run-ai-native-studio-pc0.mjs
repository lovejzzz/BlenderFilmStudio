#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { open, mkdir, readFile, realpath, stat, statfs } from 'node:fs/promises';
import { dirname, extname, relative, resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SPEC_URI = 'specs/ai-native-studio-post-pb7-improvement-program.v0.1.json';
const FREEZE_URI = 'specs/ai-native-studio-pc0-tool-freeze.v0.1.json';
const EVIDENCE_URI = 'experiments/ai-native-studio-post-pb7/PC.0-2026-08-31-mac-m2max-attempt-01';
const WORK_ROOT = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.0-2026-08-31-mac-m2max-attempt-01';
const RENDER_EXTENSIONS = new Set(['.exr', '.png', '.jpg', '.jpeg', '.mov', '.mp4']);

function sorted(value) { if (Array.isArray(value)) return value.map(sorted); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, v]) => [k, sorted(v)])); return value; }
const canonical = value => JSON.stringify(sorted(value));
const sha = value => createHash('sha256').update(value).digest('hex');
const shaFile = async path => sha(await readFile(path));
const without = (value, field) => { const body = structuredClone(value); delete body[field]; return body; };
const validSelf = (value, field) => value?.[field] === sha(canonical(without(value, field)));

async function writeJson(path, body, field) {
  const value = { ...body, [field]: sha(canonical(body)) };
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(value, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); }
  return value;
}

async function writeBytes(path, bytes) { const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); } }

async function walk(root) {
  const { readdir } = await import('node:fs/promises'); const out = [];
  async function visit(path) { for (const entry of await readdir(path, { withFileTypes: true })) { const next = resolve(path, entry.name); if (entry.isSymbolicLink()) throw new Error(`SYMLINK_${next}`); if (entry.isDirectory()) await visit(next); else if (entry.isFile()) out.push(next); } }
  await visit(root); return out.sort();
}

function parseArgs(argv) {
  const values = {};
  for (let i = 0; i < argv.length; i += 2) { if (!argv[i]?.startsWith('--') || argv[i + 1] === undefined) throw new Error('USAGE'); values[argv[i].slice(2)] = argv[i + 1]; }
  if (values.spec !== SPEC_URI || values['tool-freeze'] !== FREEZE_URI || values['evidence-root'] !== EVIDENCE_URI || resolve(values['work-root'] || '') !== WORK_ROOT) throw new Error('EXACT_ARGUMENTS');
  return values;
}

async function runProcess(command, argv, options, timeoutMs) {
  const started = Date.now(); const child = spawn(command, argv, options); const stdout = [], stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk)); child.stderr.on('data', chunk => stderr.push(chunk));
  let timedOut = false; const timer = setTimeout(() => { timedOut = true; child.kill('SIGTERM'); }, timeoutMs);
  const result = await new Promise((done, reject) => { child.on('error', reject); child.on('close', (code, signal) => done({ code, signal })); }); clearTimeout(timer);
  return { ...result, pid: child.pid, timedOut, wallSeconds: (Date.now() - started) / 1000, stdout: Buffer.concat(stdout), stderr: Buffer.concat(stderr) };
}

export async function runPc0(argv = process.argv.slice(2)) {
  const args = parseArgs(argv); const specPath = resolve(repositoryRoot, SPEC_URI), freezePath = resolve(repositoryRoot, FREEZE_URI);
  const spec = JSON.parse(await readFile(specPath, 'utf8')), freeze = JSON.parse(await readFile(freezePath, 'utf8'));
  if (!validSelf(spec, 'specHash') || !validSelf(freeze, 'specHash') || freeze.status !== 'FROZEN_BEFORE_PC0_START') throw new Error('CONTRACT_HASH');
  if (freeze.program.specHash !== spec.specHash || freeze.program.sha256 !== await shaFile(specPath)) throw new Error('PROGRAM_BINDING');
  for (const tool of freeze.tools) if (await shaFile(resolve(repositoryRoot, tool.uri)) !== tool.sha256) throw new Error(`TOOL_HASH_${tool.uri}`);
  const evidenceRoot = resolve(repositoryRoot, EVIDENCE_URI), workRoot = resolve(WORK_ROOT);
  await mkdir(dirname(evidenceRoot), { recursive: true }); await mkdir(dirname(workRoot), { recursive: true });
  for (const [path, id] of [[evidenceRoot, 'EVIDENCE'], [workRoot, 'WORK']]) { try { await stat(path); throw new Error(`${id}_ROOT_EXISTS`); } catch (error) { if (error.code !== 'ENOENT') throw error; } }
  const sourcePath = resolve(repositoryRoot, spec.frozenBaseline.scene.uri), binary = spec.frozenBaseline.binary.path;
  if (await shaFile(sourcePath) !== spec.frozenBaseline.scene.sha256 || await shaFile(binary) !== spec.frozenBaseline.binary.sha256) throw new Error('BASELINE_HASH');
  const disk = await statfs(repositoryRoot); const availableBytes = disk.bavail * disk.bsize;
  if (availableBytes < spec.resourceCeilings.minimumFreeReserveBytes + spec.resourceCeilings.pc0EvidenceBytes) throw new Error('DISK_ADMISSION');
  await mkdir(evidenceRoot, { mode: 0o700 }); await mkdir(resolve(evidenceRoot, 'logs')); await mkdir(workRoot, { mode: 0o700 });
  for (const name of ['home', 'tmp', 'config', 'scripts']) await mkdir(resolve(workRoot, name));
  const inventoryPath = resolve(evidenceRoot, 'inventory.json'), probe = resolve(repositoryRoot, freeze.probe.uri);
  const blenderArgv = ['--background', '--factory-startup', sourcePath, '--python', probe, '--', '--output', inventoryPath];
  const command = '/usr/bin/time', timedArgv = ['-l', binary, ...blenderArgv];
  const env = { ...process.env, HOME: resolve(workRoot, 'home'), TMPDIR: `${resolve(workRoot, 'tmp')}/`, BLENDER_USER_CONFIG: resolve(workRoot, 'config'), BLENDER_USER_SCRIPTS: resolve(workRoot, 'scripts'), PYTHONNOUSERSITE: '1', LC_ALL: 'C', LANG: 'C' };
  const beforeSourceSha256 = await shaFile(sourcePath); const process = await runProcess(command, timedArgv, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] }, spec.resourceCeilings.pc0WallSeconds * 1000);
  await writeBytes(resolve(evidenceRoot, 'logs/stdout.log'), process.stdout); await writeBytes(resolve(evidenceRoot, 'logs/stderr.log'), process.stderr);
  const afterSourceSha256 = await shaFile(sourcePath); const rssMatch = process.stderr.toString('utf8').match(/([0-9]+)\s+maximum resident set size/); const peakRssBytes = rssMatch ? Number(rssMatch[1]) : null;
  const inventoryExists = await stat(inventoryPath).catch(() => null);
  const processRecord = await writeJson(resolve(evidenceRoot, 'process.json'), { schemaVersion: 'bfs.pc0Process.v0.1', command, argv: timedArgv, blenderArgv: [binary, ...blenderArgv], cwd: repositoryRoot, environment: { HOME: env.HOME, TMPDIR: env.TMPDIR, BLENDER_USER_CONFIG: env.BLENDER_USER_CONFIG, BLENDER_USER_SCRIPTS: env.BLENDER_USER_SCRIPTS, PYTHONNOUSERSITE: env.PYTHONNOUSERSITE, LC_ALL: env.LC_ALL, LANG: env.LANG }, pid: process.pid, exitCode: process.code, signal: process.signal, timedOut: process.timedOut, wallSeconds: process.wallSeconds, peakRssBytes, stdout: { uri: `${EVIDENCE_URI}/logs/stdout.log`, sha256: sha(process.stdout), bytes: process.stdout.length }, stderr: { uri: `${EVIDENCE_URI}/logs/stderr.log`, sha256: sha(process.stderr), bytes: process.stderr.length } }, 'processHash');
  const files = [...await walk(evidenceRoot), ...await walk(workRoot)]; const renderArtifacts = files.filter(path => RENDER_EXTENSIONS.has(extname(path).toLowerCase()));
  const passed = process.code === 0 && !process.timedOut && inventoryExists && beforeSourceSha256 === afterSourceSha256 && peakRssBytes !== null && peakRssBytes <= spec.resourceCeilings.pc0PeakRssBytes && process.wallSeconds <= spec.resourceCeilings.pc0WallSeconds && renderArtifacts.length === 0;
  const receipt = await writeJson(resolve(evidenceRoot, 'receipt.json'), { schemaVersion: 'bfs.pc0RunReceipt.v0.1', status: passed ? 'PASS' : 'FAIL', program: { uri: SPEC_URI, sha256: await shaFile(specPath), specHash: spec.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await shaFile(freezePath), specHash: freeze.specHash }, source: { uri: spec.frozenBaseline.scene.uri, beforeSha256: beforeSourceSha256, afterSha256: afterSourceSha256, bytes: (await stat(sourcePath)).size }, binary: { path: binary, sha256: await shaFile(binary), bytes: (await stat(binary)).size }, inventory: inventoryExists ? { uri: `${EVIDENCE_URI}/inventory.json`, sha256: await shaFile(inventoryPath), bytes: inventoryExists.size } : null, process: { uri: `${EVIDENCE_URI}/process.json`, sha256: await shaFile(resolve(evidenceRoot, 'process.json')), processHash: processRecord.processHash }, resources: { availableBytes, evidenceCeilingBytes: spec.resourceCeilings.pc0EvidenceBytes, wallCeilingSeconds: spec.resourceCeilings.pc0WallSeconds, peakRssCeilingBytes: spec.resourceCeilings.pc0PeakRssBytes, observedWallSeconds: process.wallSeconds, observedPeakRssBytes: peakRssBytes }, operations: { BlenderStarts: 1, renderCalls: 0, sceneSaves: 0, engineSourceEdits: 0, engineCommits: 0, engineRemoteWrites: 0, networkCalls: 0, modelCalls: 0, mouseInteractions: 0 }, renderArtifacts, workRoot, evidenceRoot: EVIDENCE_URI }, 'receiptHash');
  if (!passed) throw new Error(`PC0_RUN_FAIL_${receipt.receiptHash}`);
  globalThis.process.stdout.write(`BFS_PC0_RUN PASS ${receipt.receiptHash}\n`); return receipt;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) runPc0().catch(error => { process.stderr.write(`BFS_PC0_RUN_REJECTED ${error.message}\n`); process.exitCode = 1; });
