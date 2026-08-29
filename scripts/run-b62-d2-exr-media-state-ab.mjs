#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { durableMkdir, repoUri, repositoryRoot, resolveExistingRepositoryPath, resolveFreshRepositoryPath, sha256Bytes, sha256File, writeDurableHashed } from './preflight-b62-phase0.mjs';

const execFileAsync = promisify(execFile);
const CORRECTION_URI = 'specs/b62-phase0-c4-dynamic-exr-setter-correction.v0.1.json';
const OUTPUT_ROOT = 'experiments/b62-phase0-d2-exr-media-state-ab-v0-1';
const TOOLS = ['blender/probe_b62_d2_exr_media_state_ab.py', 'scripts/run-b62-d2-exr-media-state-ab.mjs', 'scripts/audit-b62-d2-exr-media-state-ab.mjs'];
const PREREGISTRATION_COMMIT = 'a9e98c7';

async function git(args, encoding = 'utf8') { const result = await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 16 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } }); return result.stdout; }
async function writeLog(path, value) { const bytes = Buffer.from(value); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); } return { uri: repoUri(path), sha256: sha256Bytes(bytes), bytes: bytes.length }; }

export async function runD2(argv) {
  if (argv.length !== 2 || argv[0] !== '--tool-freeze-commit' || !/^[0-9a-f]{40}$/.test(argv[1])) throw new Error('Usage: --tool-freeze-commit <full-sha>');
  const freeze = argv[1]; const head = (await git(['rev-parse', 'HEAD'])).trim(); const origin = (await git(['rev-parse', 'origin/main'])).trim();
  if (head !== freeze || origin !== freeze) throw new Error('D2 freeze must equal pushed HEAD/origin'); await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  const toolHashes = {};
  for (const uri of TOOLS) { const path = await resolveExistingRepositoryPath(uri, `D2 tool ${uri}`); const current = await sha256File(path); if (current !== sha256Bytes(await git(['show', `${freeze}:${uri}`], null))) throw new Error(`D2 tool drift ${uri}`); toolHashes[uri] = current; }
  const correctionPath = await resolveExistingRepositoryPath(CORRECTION_URI, 'D2 C4'); const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  if (correction.statusBeforeDiagnostic !== 'PREREGISTERED' || correction.authorizedDiagnostic.root !== OUTPUT_ROOT) throw new Error('D2 C4 binding mismatch');
  const root = await resolveFreshRepositoryPath(OUTPUT_ROOT, 'D2 root'); await durableMkdir(root);
  const started = process.hrtime.bigint(); let child;
  try { const value = await execFileAsync('/usr/bin/time', ['-lp', '/Applications/Blender.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/probe_b62_d2_exr_media_state_ab.py')], { cwd: repositoryRoot, encoding: 'utf8', timeout: 60000, maxBuffer: 4 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' } }); child = { exitCode: 0, stdout: value.stdout, stderr: value.stderr }; }
  catch (error) { child = { exitCode: typeof error.code === 'number' ? error.code : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message }; }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9; const stdout = await writeLog(resolve(root, 'stdout.log'), child.stdout); const stderr = await writeLog(resolve(root, 'stderr.log'), child.stderr);
  if (child.exitCode !== 0) throw new Error('D2 Blender failed'); const marker = child.stdout.split('\n').find(line => line.startsWith('BFS_B62_D2_JSON ')); if (!marker) throw new Error('D2 marker missing'); const probe = JSON.parse(marker.slice(16));
  const expectedPhases = Array.from({ length: 3 }, (_, index) => [[index + 1, 'A1_IMAGE_REJECT', false], [index + 1, 'B_MULTI_ACCEPT', true], [index + 1, 'A2_IMAGE_REJECT', false]]).flat();
  const rowsExact = probe.rows.length === 9 && probe.rows.every((row, index) => row.repetition === expectedPhases[index][0] && row.phase === expectedPhases[index][1] && row.expectedAccepted === expectedPhases[index][2] && row.accepted === expectedPhases[index][2] && row.outcomeExact === true);
  const checks = [
    ['BLENDER_BUILD_EXACT', probe.blender.version === '5.2.0 LTS' && probe.blender.buildHash === 'fbe6228777e7'],
    ['THREE_REPETITIONS_NINE_ROWS_EXACT', rowsExact],
    ['ALL_A1_IMAGE_ASSIGNMENTS_REJECT', probe.rows.filter(row => row.phase === 'A1_IMAGE_REJECT').every(row => !row.accepted && row.error?.startsWith('TypeError:'))],
    ['ALL_B_MULTI_ASSIGNMENTS_ACCEPT', probe.rows.filter(row => row.phase === 'B_MULTI_ACCEPT').every(row => row.accepted && row.fileFormatAfter === 'OPEN_EXR_MULTILAYER')],
    ['ALL_A2_IMAGE_ASSIGNMENTS_REJECT', probe.rows.filter(row => row.phase === 'A2_IMAGE_REJECT').every(row => !row.accepted && row.error?.startsWith('TypeError:'))],
    ['DECISION_IGNORES_ENUM_ITEMS', probe.decisionUsesEnumItems === false],
    ['FINAL_MEDIA_EXR_HALF_ZIP_EXACT', probe.final.mediaType === 'MULTI_LAYER_IMAGE' && probe.final.fileFormat === 'OPEN_EXR_MULTILAYER' && probe.final.colorDepth === '16' && probe.final.exrCodec === 'ZIP'],
    ['ZERO_RENDER_EXTERNAL_CALLS', probe.operations.blenderStarts === 1 && probe.operations.renderCalls === 0 && probe.operations.modelCalls === 0 && probe.operations.networkCalls === 0 && probe.operations.dockerProcesses === 0],
  ].map(([id, pass]) => ({ id, pass })); const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const result = await writeDurableHashed(resolve(root, 'result.json'), { schemaVersion: 'bfs.b62Phase0D2Result.v0.1', experimentId: 'B62-P0-D2', status, correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) }, toolFreezeCommit: freeze, toolHashes, probe, checks, process: { exitCode: child.exitCode, elapsedSeconds, stdout, stderr, timing: { realSeconds: Number(child.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? elapsedSeconds), userSeconds: Number(child.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0), systemSeconds: Number(child.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0), maximumResidentSetSizeBytes: Number(child.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0) } } }, 'resultHash');
  const receipt = await writeDurableHashed(resolve(root, 'receipt.json'), { schemaVersion: 'bfs.b62Phase0D2Receipt.v0.1', experimentId: 'B62-P0-D2', status, verdict: status === 'PASS' ? 'BLENDER52_DYNAMIC_MULTILAYER_SETTER_ORDER_PROVEN' : 'B62_D2_INVALIDATED', result: { uri: `${OUTPUT_ROOT}/result.json`, sha256: await sha256File(resolve(root, 'result.json')), resultHash: result.resultHash }, operations: probe.operations }, 'receiptHash');
  if (status !== 'PASS') throw new Error('D2 checks failed'); process.stdout.write(`BFS_B62_D2 PASS 8/8 setterOutcomes=9/9 ${receipt.receiptHash}\n`); return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runD2(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_D2_ERROR ${error.message}\n`); process.exitCode = 1; });
