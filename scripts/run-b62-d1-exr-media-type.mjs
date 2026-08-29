#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import {
  durableMkdir, repoUri, repositoryRoot, resolveExistingRepositoryPath, resolveFreshRepositoryPath,
  sha256Bytes, sha256File, writeDurableHashed,
} from './preflight-b62-phase0.mjs';

const execFileAsync = promisify(execFile);
const CORRECTION_URI = 'specs/b62-phase0-c3-blender52-multilayer-media-correction.v0.1.json';
const OUTPUT_ROOT = 'experiments/b62-phase0-d1-exr-media-type-v0-1';
const TOOL_PATHS = ['blender/probe_b62_d1_exr_media_type.py', 'scripts/run-b62-d1-exr-media-type.mjs', 'scripts/audit-b62-d1-exr-media-type.mjs'];
const PREREGISTRATION_COMMIT = 'b3b7ec6';
const BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender';

async function git(args, encoding = 'utf8') {
  const result = await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 16 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } });
  return result.stdout;
}

async function durableLog(path, value) {
  const bytes = Buffer.from(value); const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); }
  return { uri: repoUri(path), sha256: sha256Bytes(bytes), bytes: bytes.length };
}

export async function runD1(argv) {
  if (argv.length !== 2 || argv[0] !== '--tool-freeze-commit' || !/^[0-9a-f]{40}$/.test(argv[1])) throw new Error('Usage: --tool-freeze-commit <full-sha>');
  const toolFreezeCommit = argv[1];
  const head = (await git(['rev-parse', 'HEAD'])).trim(); const origin = (await git(['rev-parse', 'origin/main'])).trim();
  if (head !== toolFreezeCommit || origin !== toolFreezeCommit) throw new Error('D1 tool freeze must equal pushed HEAD and origin/main');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, toolFreezeCommit]);
  const toolHashes = {};
  for (const uri of TOOL_PATHS) {
    const path = await resolveExistingRepositoryPath(uri, `D1 tool ${uri}`); const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${toolFreezeCommit}:${uri}`], null));
    if (current !== frozen) throw new Error(`D1 tool drift: ${uri}`); toolHashes[uri] = current;
  }
  const correctionPath = await resolveExistingRepositoryPath(CORRECTION_URI, 'D1 C3 correction');
  const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  if (correction.statusBeforeDiagnostic !== 'PREREGISTERED' || correction.authorizedDiagnostic.root !== OUTPUT_ROOT) throw new Error('D1 C3 binding mismatch');
  const output = await resolveFreshRepositoryPath(OUTPUT_ROOT, 'D1 output root'); await durableMkdir(output);
  const started = process.hrtime.bigint();
  let processResult;
  try {
    const child = await execFileAsync('/usr/bin/time', ['-lp', BLENDER, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/probe_b62_d1_exr_media_type.py')], {
      cwd: repositoryRoot, encoding: 'utf8', timeout: 60000, maxBuffer: 4 * 1024 * 1024,
      env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    });
    processResult = { exitCode: 0, stdout: child.stdout, stderr: child.stderr };
  } catch (error) {
    processResult = { exitCode: typeof error.code === 'number' ? error.code : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message };
  }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  const stdout = await durableLog(resolve(output, 'stdout.log'), processResult.stdout);
  const stderr = await durableLog(resolve(output, 'stderr.log'), processResult.stderr);
  if (processResult.exitCode !== 0) throw new Error('D1 Blender probe failed');
  const marker = processResult.stdout.split('\n').find(line => line.startsWith('BFS_B62_D1_JSON '));
  if (!marker) throw new Error('D1 probe marker absent');
  const probe = JSON.parse(marker.slice('BFS_B62_D1_JSON '.length));
  const checks = [
    ['BLENDER_BUILD_EXACT', probe.blender.version === '5.2.0 LTS' && probe.blender.buildHash === 'fbe6228777e7'],
    ['FACTORY_MEDIA_TYPE_IMAGE', probe.default.mediaType === 'IMAGE'],
    ['MULTILAYER_ENUM_ABSENT_BEFORE_MEDIA_TYPE', !probe.default.fileFormatEnums.includes('OPEN_EXR_MULTILAYER')],
    ['WRONG_ORDER_REJECTED', probe.assignmentBeforeMediaTypeRejected === true],
    ['MEDIA_TYPE_SWITCH_EXACT', probe.afterMediaType.mediaType === 'MULTI_LAYER_IMAGE'],
    ['MULTILAYER_ENUM_PRESENT_AFTER_MEDIA_TYPE', probe.afterMediaType.fileFormatEnums.includes('OPEN_EXR_MULTILAYER')],
    ['FINAL_HALF_ZIP_EXACT', probe.final.mediaType === 'MULTI_LAYER_IMAGE' && probe.final.fileFormat === 'OPEN_EXR_MULTILAYER' && probe.final.colorDepth === '16' && probe.final.exrCodec === 'ZIP'],
    ['ZERO_RENDER_EXTERNAL_CALLS', probe.operations.renderCalls === 0 && probe.operations.modelCalls === 0 && probe.operations.networkCalls === 0 && probe.operations.dockerProcesses === 0],
  ].map(([id, pass]) => ({ id, pass }));
  const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const result = await writeDurableHashed(resolve(output, 'result.json'), {
    schemaVersion: 'bfs.b62Phase0D1Result.v0.1', experimentId: 'B62-P0-D1', status,
    correction: { uri: CORRECTION_URI, sha256: await sha256File(correctionPath) }, toolFreezeCommit, toolHashes, probe, checks,
    process: { exitCode: processResult.exitCode, elapsedSeconds, stdout, stderr,
      timing: { realSeconds: Number(processResult.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? elapsedSeconds), userSeconds: Number(processResult.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0), systemSeconds: Number(processResult.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0), maximumResidentSetSizeBytes: Number(processResult.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0) } },
  }, 'resultHash');
  const receipt = await writeDurableHashed(resolve(output, 'receipt.json'), {
    schemaVersion: 'bfs.b62Phase0D1Receipt.v0.1', experimentId: 'B62-P0-D1', status, verdict: status === 'PASS' ? 'BLENDER52_MULTILAYER_MEDIA_ORDER_PROVEN' : 'B62_D1_INVALIDATED',
    result: { uri: `${OUTPUT_ROOT}/result.json`, sha256: await sha256File(resolve(output, 'result.json')), resultHash: result.resultHash },
    operations: probe.operations,
  }, 'receiptHash');
  if (status !== 'PASS') throw new Error('D1 checks failed');
  process.stdout.write(`BFS_B62_D1 PASS 8/8 ${receipt.receiptHash}\n`); return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runD1(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_D1_ERROR ${error.message}\n`); process.exitCode = 1; });
