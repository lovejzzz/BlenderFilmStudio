#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdir, readFile, stat, statfs, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SPEC_URI = 'specs/ai-native-studio-pc4-hero-redesign-preregistration.v0.1.json';
const FREEZE_URI = 'specs/ai-native-studio-pc4-tool-freeze-c1.v0.2.json';
const EVIDENCE_URI = 'experiments/ai-native-studio-post-pb7/PC.4-2026-08-31-mac-m2max-attempt-02';
const WORK = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.4-2026-08-31-mac-m2max-attempt-02';
const sorted = value => Array.isArray(value) ? value.map(sorted) : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, child]) => [key, sorted(child)])) : value;
const canonical = value => JSON.stringify(sorted(value));
const sha = value => createHash('sha256').update(value).digest('hex');
const hashFile = async path => sha(await readFile(path));
const validSelf = (value, field) => { const body = structuredClone(value); const expected = body[field]; delete body[field]; return expected === sha(canonical(body)); };
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const exists = async path => { try { await stat(path); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; } };
const writeSelf = async (path, body, field) => { const value = { ...body, [field]: sha(canonical(body)) }; await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, { flag: 'wx', mode: 0o600 }); return value; };

async function runProcess(executable, argv, logPath, timeoutMs) {
  const started = Date.now(); const child = spawn(executable, argv, { cwd: root, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] }); let output = '';
  child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; });
  const timer = setTimeout(() => child.kill('SIGTERM'), timeoutMs);
  const result = await new Promise((done, reject) => { child.once('error', reject); child.once('close', (code, signal) => done({ code, signal })); });
  clearTimeout(timer); await writeFile(logPath, output, { flag: 'wx', mode: 0o600 });
  return { ...result, wallSeconds: (Date.now() - started) / 1000 };
}

async function main() {
  const specPath = resolve(root, SPEC_URI), freezePath = resolve(root, FREEZE_URI), evidence = resolve(root, EVIDENCE_URI);
  const spec = await readJson(specPath), freeze = await readJson(freezePath);
  if (!validSelf(spec, 'specHash') || spec.status !== 'PREREGISTERED_BEFORE_PC4_MUTATION') throw new Error('SPEC');
  if (!validSelf(freeze, 'specHash') || freeze.status !== 'FROZEN_C1_BEFORE_PC4_ATTEMPT_02' || freeze.preregistration.specHash !== spec.specHash) throw new Error('FREEZE');
  for (const tool of freeze.tools) if (await hashFile(resolve(root, tool.uri)) !== tool.sha256) throw new Error(`TOOL_${tool.uri}`);
  for (const item of Object.values(freeze.retainedAttempt01)) if (item.uri && await hashFile(resolve(root, item.uri)) !== item.sha256) throw new Error(`ATTEMPT01_${item.uri}`);
  if (await hashFile(spec.source.path) !== spec.source.sha256 || await hashFile(spec.binary.path) !== spec.binary.sha256) throw new Error('SOURCE_OR_BINARY');
  if (await exists(evidence) || await exists(WORK)) throw new Error('FORMAL_ROOT_EXISTS');
  const disk = await statfs(resolve(root)); const free = Number(disk.bavail) * Number(disk.bsize);
  if (free < spec.resourceCeilings.minimumFreeReserveBytes + spec.resourceCeilings.projectedWriteBytes) throw new Error('DISK_ADMISSION');
  await mkdir(resolve(evidence, 'derived'), { recursive: true }); await mkdir(resolve(evidence, 'logs'), { recursive: true }); await mkdir(resolve(WORK, 'tmp'), { recursive: true });
  const builder = resolve(root, 'scripts/build-ai-native-studio-pc4-c1.py');
  const buildArgv = ['--background', spec.source.path, '--disable-autoexec', '--python-exit-code', '1', '--python', builder, '--', '--spec', specPath, '--evidence-root', evidence, '--work-root', WORK];
  const build = await runProcess(spec.binary.path, buildArgv, resolve(evidence, 'logs/build.log'), spec.resourceCeilings.wallSecondsPerBlenderProcess * 1000);
  if (build.code !== 0 || build.signal) throw new Error(`BUILD_${build.code}_${build.signal}`);
  const buildRecord = await readJson(resolve(evidence, 'build.json'));
  if (!validSelf(buildRecord, 'buildHash') || buildRecord.status !== 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED') throw new Error('BUILD_RECORD');
  const auditArgv = ['--background', buildRecord.derived.path, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(root, 'scripts/audit-ai-native-studio-pc4.py'), '--', '--spec', specPath, '--evidence-root', evidence, '--work-root', WORK];
  const audit = await runProcess(spec.binary.path, auditArgv, resolve(evidence, 'logs/audit.log'), spec.resourceCeilings.wallSecondsPerBlenderProcess * 1000);
  if (audit.code !== 0 || audit.signal) throw new Error(`AUDIT_${audit.code}_${audit.signal}`);
  const auditRecord = await readJson(resolve(evidence, 'audit.json'));
  if (!validSelf(auditRecord, 'auditHash') || auditRecord.status !== 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED') throw new Error('AUDIT_RECORD');
  const receipt = await writeSelf(resolve(evidence, 'receipt.json'), {
    schemaVersion: 'bfs.pc4HeroRedesignReceipt.v0.2', status: 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED', gate: 'PC.4', attempt: 'attempt-02',
    preregistration: { uri: SPEC_URI, sha256: await hashFile(specPath), specHash: spec.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await hashFile(freezePath), specHash: freeze.specHash },
    retainedAttempt01: freeze.retainedAttempt01, source: { path: spec.source.path, sha256: await hashFile(spec.source.path) }, binary: { path: spec.binary.path, sha256: await hashFile(spec.binary.path) },
    build: { sha256: await hashFile(resolve(evidence, 'build.json')), buildHash: buildRecord.buildHash, wallSeconds: build.wallSeconds }, audit: { sha256: await hashFile(resolve(evidence, 'audit.json')), auditHash: auditRecord.auditHash, checks: `${auditRecord.checkPassed}/${auditRecord.checkTotal}`, wallSeconds: audit.wallSeconds },
    derived: buildRecord.derived, screenshots: buildRecord.screenshots, operationCounts: { BlenderStarts: 2, renderCalls: 3, derivedSceneSaves: 1, networkCalls: 0, modelCallsDuringExecution: 0, mouseInteractions: 0 },
  }, 'receiptHash');
  process.stdout.write(`BFS_PC4_C1_RUN ${receipt.status} ${receipt.receiptHash}\n`);
}

main().catch(error => { process.stderr.write(`BFS_PC4_C1_RUN_REJECTED ${error.message}\n`); process.exitCode = 1; });
