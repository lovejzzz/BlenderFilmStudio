#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile, readdir } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { canonicalHash, durableMkdir, resolveExistingRepositoryPath, resolveFreshRepositoryPath, sha256Bytes, sha256File, validSelfHash, writeDurableHashed, writeDurableJson } from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const SPEC_URI = 'specs/cinematic-render-repro-cost-d4-png-export-context-diagnostic.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b61-e1-d4-png-export-context-diagnostic.md';
const PROBE_URI = 'blender/probe_b61_png_export_context.py';
const RUNNER_URI = 'scripts/run-b61-d4-png-export-context-diagnostic.mjs';
const OUTPUT_ROOT = 'experiments/b61-png-export-context-diagnostic-v0-1';
const PREREGISTRATION_COMMIT = '85e74ee';

function parseArguments(argv) { const parsed = {}; for (let i = 0; i < argv.length; i += 1) { if (argv[i] === '--output-root') parsed.outputRoot = argv[++i]; else if (argv[i] === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++i]; else throw new Error(`Unknown ${argv[i]}`); } if (parsed.outputRoot !== OUTPUT_ROOT || !/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit ?? '')) throw new Error('D4 arguments invalid'); return parsed; }
async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function walk(directory) { const output = []; for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) output.push(...await walk(path)); else output.push(path); } return output; }
async function treeIdentity(uri) { const root = await resolveExistingRepositoryPath(uri, uri, 'directory'); const files = (await walk(root)).sort(); let bytes = 0; let material = ''; for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`; } return { files: files.length, bytes, sha256: sha256Bytes(Buffer.from(material)) }; }
async function writeLog(path, text) { const data = Buffer.from(text); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(data); await handle.sync(); } finally { await handle.close(); } return { bytes: data.length, sha256: sha256Bytes(data) }; }

export async function runD4(argv) {
  const parsed = parseArguments(argv); const head = (await git(['rev-parse', 'HEAD'])).trim(); const origin = (await git(['rev-parse', 'origin/main'])).trim(); if (head !== parsed.toolFreezeCommit || origin !== head) throw new Error('D4 freeze mismatch'); await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, head]);
  const toolHashes = {}; for (const uri of [SPEC_URI, PROTOCOL_URI, PROBE_URI, RUNNER_URI]) { const path = await resolveExistingRepositoryPath(uri, uri); const current = await sha256File(path); const frozen = sha256Bytes(await git(['show', `${head}:${uri}`], null)); if (current !== frozen) throw new Error(`D4 tool mismatch ${uri}`); toolHashes[uri] = current; }
  const spec = JSON.parse(await readFile(await resolveExistingRepositoryPath(SPEC_URI, 'D4 spec'), 'utf8'));
  if (canonicalHash(await treeIdentity(spec.failedRun.attemptRoot)) !== canonicalHash(spec.failedRun.attemptTree) || canonicalHash(await treeIdentity(spec.failedRun.formalRoot)) !== canonicalHash(spec.failedRun.formalTree)) throw new Error('D4 retained tree mismatch');
  const failurePath = await resolveExistingRepositoryPath(spec.failedRun.failureSummary.uri, 'D4 failure'); const failure = JSON.parse(await readFile(failurePath, 'utf8')); if (await sha256File(failurePath) !== spec.failedRun.failureSummary.sha256 || !validSelfHash(failure, 'failureHash') || failure.failureHash !== spec.failedRun.failureSummary.failureHash) throw new Error('D4 failure binding mismatch');
  const outputRoot = await resolveFreshRepositoryPath(parsed.outputRoot, 'D4 output root'); await durableMkdir(outputRoot); const source = await resolveExistingRepositoryPath('experiments/cinematic-sequence-consistency-v0-1/runs/WIDE-A/restricted/scene.blend', 'D4 source'); const resultPath = resolve(outputRoot, 'result.json');
  const started = process.hrtime.bigint(); let child; try { const value = await execFileAsync('/usr/bin/time', ['-lp', '/Applications/Blender.app/Contents/MacOS/Blender', '--background', source, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, PROBE_URI), '--', '--repository-root', repositoryRoot, '--spec', SPEC_URI, '--output', `${parsed.outputRoot}/result.json`], { cwd: repositoryRoot, encoding: 'utf8', timeout: 30000, maxBuffer: 16 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' } }); child = { exitCode: 0, signal: null, stdout: value.stdout, stderr: value.stderr }; } catch (error) { child = { exitCode: typeof error.code === 'number' ? error.code : 1, signal: error.signal ?? null, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message }; }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9; const stdout = await writeLog(resolve(outputRoot, 'stdout.log'), child.stdout); const stderr = await writeLog(resolve(outputRoot, 'stderr.log'), child.stderr); await writeDurableJson(resolve(outputRoot, 'process.json'), { exitCode: child.exitCode, signal: child.signal, elapsedSeconds, pythonExitCodeEnforced: true, stdout, stderr }); if (child.exitCode !== 0) throw new Error(`D4 Blender failed: ${child.stderr || child.stdout}`);
  const result = JSON.parse(await readFile(resultPath, 'utf8')); if (!validSelfHash(result, 'resultHash') || result.status !== 'PASS' || result.productionSettingsUnchanged !== true || result.isolatedReviewScene.png.validHeader !== true || result.operations.renderCalls !== 0) throw new Error('D4 result invalid');
  const receipt = await writeDurableHashed(resolve(outputRoot, 'receipt.json'), { schemaVersion: 'bfs.b61PngExportContextDiagnosticReceipt.v0.1', status: 'PASS', verdict: result.verdict, toolFreezeCommit: head, toolHashes, result: { uri: `${OUTPUT_ROOT}/result.json`, sha256: await sha256File(resultPath), resultHash: result.resultHash }, process: { elapsedSeconds, stdout, stderr }, operations: result.operations, claimBoundary: spec.claimBoundary }, 'receiptHash'); process.stdout.write(`BFS_B61_D4 PASS ${receipt.receiptHash}\n`); return receipt;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runD4(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B61_D4_ERROR ${error.message}\n`); process.exitCode = 1; });
