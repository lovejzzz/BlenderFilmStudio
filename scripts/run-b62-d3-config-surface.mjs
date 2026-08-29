#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { durableMkdir, repoUri, repositoryRoot, resolveExistingRepositoryPath, resolveFreshRepositoryPath, sha256Bytes, sha256File, writeDurableHashed } from './preflight-b62-phase0.mjs';

const execFileAsync = promisify(execFile);
const CORRECTION_URI = 'specs/b62-phase0-c6-blender52-config-surface-diagnostic.v0.1.json';
const ROOT = 'experiments/b62-phase0-d3-config-surface-v0-1';
const TOOLS = ['blender/probe_b62_d3_config_surface.py', 'scripts/run-b62-d3-config-surface.mjs', 'scripts/audit-b62-d3-config-surface.mjs'];
const PREREGISTRATION_COMMIT = '89316e0';

async function git(args, encoding = 'utf8') { const result = await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 16 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } }); return result.stdout; }
async function writeLog(path, value) { const bytes = Buffer.from(value); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); } return { uri: repoUri(path), sha256: sha256Bytes(bytes), bytes: bytes.length }; }

export async function runD3(argv) {
  if (argv.length !== 2 || argv[0] !== '--tool-freeze-commit' || !/^[0-9a-f]{40}$/.test(argv[1])) throw new Error('Usage: --tool-freeze-commit <full-sha>');
  const freeze = argv[1]; const head = (await git(['rev-parse', 'HEAD'])).trim(); const origin = (await git(['rev-parse', 'origin/main'])).trim(); if (head !== freeze || origin !== freeze) throw new Error('D3 freeze mismatch'); await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, freeze]);
  const toolHashes = {}; for (const uri of TOOLS) { const path = await resolveExistingRepositoryPath(uri, `D3 ${uri}`); const current = await sha256File(path); if (current !== sha256Bytes(await git(['show', `${freeze}:${uri}`], null))) throw new Error(`D3 tool drift ${uri}`); toolHashes[uri] = current; }
  const correctionPath = await resolveExistingRepositoryPath(CORRECTION_URI, 'D3 C6'); const correction = JSON.parse(await readFile(correctionPath, 'utf8')); if (correction.statusBeforeDiagnostic !== 'PREREGISTERED' || correction.authorizedDiagnostic.root !== ROOT) throw new Error('D3 C6 binding');
  const root = await resolveFreshRepositoryPath(ROOT, 'D3 root'); await durableMkdir(root); const started = process.hrtime.bigint(); let child;
  try { const value = await execFileAsync('/usr/bin/time', ['-lp', '/Applications/Blender.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/probe_b62_d3_config_surface.py')], { cwd: repositoryRoot, encoding: 'utf8', timeout: 60000, maxBuffer: 4 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, correction.authorizedDiagnostic.ocioUri) } }); child = { exitCode: 0, stdout: value.stdout, stderr: value.stderr }; }
  catch (error) { child = { exitCode: typeof error.code === 'number' ? error.code : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message }; }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9; const stdout = await writeLog(resolve(root, 'stdout.log'), child.stdout); const stderr = await writeLog(resolve(root, 'stderr.log'), child.stderr); if (child.exitCode !== 0) throw new Error('D3 Blender failed');
  const marker = child.stdout.split('\n').find(line => line.startsWith('BFS_B62_D3_JSON ')); if (!marker) throw new Error('D3 marker missing'); const probe = JSON.parse(marker.slice(16));
  const checks = [
    ['BLENDER_BUILD_EXACT', probe.blender.version === '5.2.0 LTS' && probe.blender.buildHash === 'fbe6228777e7'],
    ['DISPLAY_EXACT', probe.color.display === 'sRGB - Display'],
    ['VIEW_EXACT', probe.color.view === 'ACES 2.0 - SDR 100 nits (Rec.709)'],
    ['OLD_LOOK_REJECTED_NEUTRAL_ACCEPTED', probe.color.oldLookRejected && probe.color.look === 'None' && probe.color.exposure === 0 && probe.color.gamma === 1],
    ['CYCLES_SURFACE_EXACT', probe.cycles.engine === 'CYCLES' && probe.cycles.device === 'CPU' && probe.cycles.samples === 64 && probe.cycles.denoise && !probe.cycles.animatedSeed && probe.cycles.seed === 62001],
    ['EEVEE_SURFACE_EXACT', probe.eevee.engine === 'BLENDER_EEVEE_NEXT' && probe.eevee.viewportSamples === 16 && probe.eevee.renderSamples === 16],
    ['MOTION_BLUR_EXACT', probe.motionBlur.enabled === true],
    ['EXR_SURFACE_EXACT', probe.exr.mediaType === 'MULTI_LAYER_IMAGE' && probe.exr.fileFormat === 'OPEN_EXR_MULTILAYER' && probe.exr.colorDepth === '16' && probe.exr.exrCodec === 'ZIP'],
    ['ZERO_RENDER_EXTERNAL_CALLS', probe.operations.blenderStarts === 1 && probe.operations.renderCalls === 0 && probe.operations.modelCalls === 0 && probe.operations.networkCalls === 0 && probe.operations.dockerProcesses === 0],
  ].map(([id, pass]) => ({ id, pass })); const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const result = await writeDurableHashed(resolve(root, 'result.json'), { schemaVersion: 'bfs.b62Phase0D3Result.v0.1', experimentId: 'B62-P0-D3', status, correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) }, toolFreezeCommit: freeze, toolHashes, probe, checks, process: { exitCode: child.exitCode, elapsedSeconds, stdout, stderr, timing: { realSeconds: Number(child.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? elapsedSeconds), userSeconds: Number(child.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0), systemSeconds: Number(child.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0), maximumResidentSetSizeBytes: Number(child.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0) } } }, 'resultHash');
  const receipt = await writeDurableHashed(resolve(root, 'receipt.json'), { schemaVersion: 'bfs.b62Phase0D3Receipt.v0.1', experimentId: 'B62-P0-D3', status, verdict: status === 'PASS' ? 'BLENDER52_B62_CONFIG_SURFACE_PROVEN' : 'B62_D3_INVALIDATED', result: { uri: `${ROOT}/result.json`, sha256: await sha256File(resolve(root, 'result.json')), resultHash: result.resultHash }, operations: probe.operations }, 'receiptHash'); if (status !== 'PASS') throw new Error('D3 checks failed'); process.stdout.write(`BFS_B62_D3 PASS 9/9 ${receipt.receiptHash}\n`); return receipt;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runD3(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_D3_ERROR ${error.message}\n`); process.exitCode = 1; });
