#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile, readdir } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import {
  canonicalHash, durableMkdir, resolveExistingRepositoryPath,
  resolveFreshRepositoryPath, sha256Bytes, sha256File, validSelfHash, writeDurableHashed,
  writeDurableJson,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const SPEC_URI = 'specs/cinematic-render-repro-cost-d1-exr-reopen-diagnostic.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b61-e1-d1-exr-reopen-diagnostic.md';
const PROBE_URI = 'blender/probe_b61_exr_reopen.py';
const RUNNER_URI = 'scripts/run-b61-d1-exr-reopen-diagnostic.mjs';
const EXPECTED_OUTPUT = 'experiments/b61-exr-reopen-diagnostic-v0-1';
const PREREGISTRATION_COMMIT = '9d5cc09';

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown argument ${token}`);
  }
  if (parsed.outputRoot !== EXPECTED_OUTPUT) throw new Error('D1 output root mismatch');
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit ?? '')) throw new Error('D1 tool-freeze commit invalid');
  return parsed;
}

async function git(args, encoding = 'utf8') {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function walk(directory) {
  const output = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) output.push(...await walk(path));
    else if (entry.isFile()) output.push(path);
    else throw new Error(`Unsupported tree entry ${path}`);
  }
  return output;
}

async function treeIdentity(uri) {
  const root = await resolveExistingRepositoryPath(uri, `D1 retained tree ${uri}`, 'directory');
  const files = (await walk(root)).sort();
  let bytes = 0;
  let material = '';
  for (const path of files) {
    const content = await readFile(path);
    bytes += content.length;
    material += `${relative(root, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`;
  }
  return { files: files.length, bytes, sha256: sha256Bytes(Buffer.from(material)) };
}

async function writeLog(path, text) {
  const buffer = Buffer.from(text);
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(buffer); await handle.sync(); } finally { await handle.close(); }
  return { bytes: buffer.length, sha256: sha256Bytes(buffer) };
}

export async function runD1(argv) {
  const parsed = parseArguments(argv);
  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  if (head !== parsed.toolFreezeCommit || origin !== parsed.toolFreezeCommit) throw new Error('D1 freeze must equal pushed HEAD/origin');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, parsed.toolFreezeCommit]);
  const toolHashes = {};
  for (const uri of [SPEC_URI, PROTOCOL_URI, PROBE_URI, RUNNER_URI]) {
    const path = await resolveExistingRepositoryPath(uri, `D1 frozen ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${parsed.toolFreezeCommit}:${uri}`], null));
    if (current !== frozen) throw new Error(`D1 tool freeze mismatch ${uri}`);
    toolHashes[uri] = current;
  }
  const specPath = await resolveExistingRepositoryPath(SPEC_URI, 'D1 spec');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  for (const key of ['attemptTree', 'formalTree']) {
    const uri = key === 'attemptTree' ? spec.failedRun.attemptRoot : spec.failedRun.formalRoot;
    if (canonicalHash(await treeIdentity(uri)) !== canonicalHash(spec.failedRun[key])) throw new Error(`D1 retained ${key} mismatch`);
  }
  const failurePath = await resolveExistingRepositoryPath(spec.failedRun.failureSummary.uri, 'D1 failure summary');
  const failure = JSON.parse(await readFile(failurePath, 'utf8'));
  if (await sha256File(failurePath) !== spec.failedRun.failureSummary.sha256 || !validSelfHash(failure, 'failureHash')
    || failure.failureHash !== spec.failedRun.failureSummary.failureHash || failure.rootCauseProven !== true) throw new Error('D1 failure binding mismatch');
  const exrPath = await resolveExistingRepositoryPath(spec.failedRun.retainedExr.uri, 'D1 retained EXR');
  if (await sha256File(exrPath) !== spec.failedRun.retainedExr.sha256) throw new Error('D1 retained EXR mismatch');

  const outputRoot = await resolveFreshRepositoryPath(parsed.outputRoot, 'D1 output root');
  await durableMkdir(outputRoot);
  const resultPath = resolve(outputRoot, 'result.json');
  const started = process.hrtime.bigint();
  let result;
  try {
    const child = await execFileAsync('/usr/bin/time', [
      '-lp', '/Applications/Blender.app/Contents/MacOS/Blender', '--background', '--factory-startup', '--disable-autoexec',
      '--python-exit-code', '1', '--python', resolve(repositoryRoot, PROBE_URI), '--', '--repository-root', repositoryRoot,
      '--spec', SPEC_URI, '--output', `${parsed.outputRoot}/result.json`,
    ], {
      cwd: repositoryRoot, encoding: 'utf8', timeout: spec.resourceCeilings.timeoutSeconds * 1000, maxBuffer: 16 * 1024 * 1024,
      env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    });
    result = { exitCode: 0, signal: null, stdout: child.stdout, stderr: child.stderr };
  } catch (error) {
    result = { exitCode: typeof error.code === 'number' ? error.code : 1, signal: error.signal ?? null, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message };
  }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  const stdout = await writeLog(resolve(outputRoot, 'stdout.log'), result.stdout);
  const stderr = await writeLog(resolve(outputRoot, 'stderr.log'), result.stderr);
  await writeDurableJson(resolve(outputRoot, 'process.json'), {
    exitCode: result.exitCode, signal: result.signal, elapsedSeconds, pythonExitCodeEnforced: true, stdout, stderr,
  });
  if (result.exitCode !== 0 || result.signal !== null) throw new Error(`D1 Blender probe failed: ${result.stderr || result.stdout}`);
  const probe = JSON.parse(await readFile(resultPath, 'utf8'));
  if (!validSelfHash(probe, 'resultHash') || probe.status !== 'PASS' || probe.bpyImageProbe.pixelValueCount !== 0
    || probe.firstProjection.valueCount !== 8294400 || !probe.firstProjection.allValuesFinite || !probe.repeatDigestExact
    || probe.operations.renderCalls !== 0) throw new Error('D1 result criteria failed');
  const bytes = (await Promise.all((await walk(outputRoot)).map(path => readFile(path)))).reduce((sum, value) => sum + value.length, 0);
  if (bytes > spec.resourceCeilings.maximumOutputBytes) throw new Error('D1 output ceiling exceeded');
  const receipt = await writeDurableHashed(resolve(outputRoot, 'receipt.json'), {
    schemaVersion: 'bfs.b61ExrReopenDiagnosticReceipt.v0.1', status: 'PASS', verdict: probe.verdict,
    toolFreezeCommit: parsed.toolFreezeCommit, toolHashes,
    result: { uri: `${parsed.outputRoot}/result.json`, sha256: await sha256File(resultPath), resultHash: probe.resultHash },
    process: { exitCode: result.exitCode, signal: result.signal, elapsedSeconds, stdout, stderr },
    operations: { blenderProcesses: 1, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    claimBoundary: spec.claimBoundary,
  }, 'receiptHash');
  process.stdout.write(`BFS_B61_D1 PASS ${probe.firstProjection.sha256} ${receipt.receiptHash}\n`);
  return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runD1(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B61_D1_ERROR ${error.message}\n`); process.exitCode = 1; });
}
