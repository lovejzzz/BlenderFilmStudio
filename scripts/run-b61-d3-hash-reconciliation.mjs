#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { readFile, readdir } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import {
  canonicalHash, durableMkdir, resolveExistingRepositoryPath, resolveFreshRepositoryPath,
  sha256Bytes, sha256File, validSelfHash, writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const SPEC_URI = 'specs/cinematic-render-repro-cost-d3-hash-reconciliation.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b61-e1-d3-hash-reconciliation.md';
const RUNNER_URI = 'scripts/run-b61-d3-hash-reconciliation.mjs';
const EXPECTED_OUTPUT = 'experiments/b61-exr-reopen-reconciliation-v0-1';
const PREREGISTRATION_COMMIT = '9d7df10';
const BUNDLED_PYTHON = '/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13';

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown argument ${token}`);
  }
  if (parsed.outputRoot !== EXPECTED_OUTPUT) throw new Error('D3 output root mismatch');
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit ?? '')) throw new Error('D3 tool-freeze commit invalid');
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
    else throw new Error(`Unsupported D3 tree entry ${path}`);
  }
  return output;
}

async function treeIdentity(uri) {
  const root = await resolveExistingRepositoryPath(uri, `D3 retained tree ${uri}`, 'directory');
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

function assert(pass, message) {
  if (!pass) throw new Error(message);
}

export async function runD3(argv) {
  const parsed = parseArguments(argv);
  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  assert(head === parsed.toolFreezeCommit && origin === parsed.toolFreezeCommit, 'D3 freeze must equal pushed HEAD/origin');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, parsed.toolFreezeCommit]);
  const toolHashes = {};
  for (const uri of [SPEC_URI, PROTOCOL_URI, RUNNER_URI]) {
    const path = await resolveExistingRepositoryPath(uri, `D3 frozen ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${parsed.toolFreezeCommit}:${uri}`], null));
    assert(current === frozen, `D3 tool freeze mismatch ${uri}`);
    toolHashes[uri] = current;
  }

  const specPath = await resolveExistingRepositoryPath(SPEC_URI, 'D3 spec');
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  assert(canonicalHash(await treeIdentity(spec.failedDiagnostic.root)) === canonicalHash(spec.failedDiagnostic.tree), 'D3 retained tree mismatch');
  const failurePath = await resolveExistingRepositoryPath(spec.failedDiagnostic.failure.uri, 'D3 failure');
  const failure = JSON.parse(await readFile(failurePath, 'utf8'));
  assert(await sha256File(failurePath) === spec.failedDiagnostic.failure.sha256 && validSelfHash(failure, 'failureHash')
    && failure.failureHash === spec.failedDiagnostic.failure.failureHash && failure.rootCauseProven === true, 'D3 failure binding mismatch');

  const resultPath = await resolveExistingRepositoryPath(spec.failedDiagnostic.result.uri, 'D3 retained result');
  const retained = JSON.parse(await readFile(resultPath, 'utf8'));
  assert(await sha256File(resultPath) === spec.failedDiagnostic.result.sha256, 'D3 result file mismatch');
  const body = structuredClone(retained);
  const storedHash = body.resultHash;
  delete body.resultHash;
  const nodeCanonicalHash = canonicalHash(body);
  assert(nodeCanonicalHash === spec.failedDiagnostic.result.nodeCanonicalHash && nodeCanonicalHash !== storedHash, 'D3 Node mismatch not reproduced');

  const pythonCode = [
    'import hashlib,json,math,sys',
    'x=json.load(open(sys.argv[1], encoding="utf-8")); stored=x.pop("resultHash")',
    'def norm(v):',
    '  if isinstance(v,float) and math.isfinite(v) and v.is_integer(): return int(v)',
    '  if isinstance(v,list): return [norm(i) for i in v]',
    '  if isinstance(v,dict): return {k:norm(v[k]) for k in sorted(v)}',
    '  return v',
    'def digest(v): return hashlib.sha256(json.dumps(v,ensure_ascii=True,separators=(",",":"),sort_keys=True).encode()).hexdigest()',
    'print(json.dumps({"stored":stored,"python":digest(x),"normalized":digest(norm(x))},sort_keys=True))',
  ].join('\n');
  const started = process.hrtime.bigint();
  const child = await execFileAsync(BUNDLED_PYTHON, ['-c', pythonCode, resultPath], {
    cwd: repositoryRoot, encoding: 'utf8', timeout: spec.resourceCeilings.timeoutSeconds * 1000, maxBuffer: 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
  });
  const pythonSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  const python = JSON.parse(child.stdout);
  assert(child.stderr.length === 0 && python.stored === storedHash && python.python === storedHash
    && python.normalized === nodeCanonicalHash, 'D3 Python reconciliation failed');

  const processPath = await resolveExistingRepositoryPath(`${spec.failedDiagnostic.root}/process.json`, 'D3 retained process');
  const retainedProcess = JSON.parse(await readFile(processPath, 'utf8'));
  const stdoutPath = await resolveExistingRepositoryPath(`${spec.failedDiagnostic.root}/stdout.log`, 'D3 retained stdout');
  const stderrPath = await resolveExistingRepositoryPath(`${spec.failedDiagnostic.root}/stderr.log`, 'D3 retained stderr');
  assert(retainedProcess.exitCode === 0 && retainedProcess.signal === null && retainedProcess.pythonExitCodeEnforced === true
    && retainedProcess.stdout.sha256 === await sha256File(stdoutPath) && retainedProcess.stderr.sha256 === await sha256File(stderrPath), 'D3 process/log binding failed');
  const quartet = retained.combinedRgba;
  const first = retained.firstProjection;
  assert(retained.status === 'PASS' && retained.verdict === 'BLENDER_BUNDLED_OPENIMAGEIO_COMBINED_RGBA_DECODER_SUPPORTED'
    && retained.bpyImageProbe.pixelValueCount === 0 && quartet.prefix.endsWith('.Combined') && quartet.channelNames.length === 4
    && first.width === 1920 && first.height === 1080 && first.channels === 4 && first.valueCount === 8294400
    && first.allValuesFinite === true && retained.repeatDigestExact === true
    && first.sha256 === retained.secondProjection.sha256 && first.sha256 === spec.failedDiagnostic.result.projectionSha256
    && retained.operations.blenderProcesses === 1 && retained.operations.renderCalls === 0
    && retained.operations.modelCalls === 0 && retained.operations.networkCalls === 0 && retained.operations.dockerProcesses === 0,
  'D3 retained decoder semantics failed');

  const outputRoot = await resolveFreshRepositoryPath(parsed.outputRoot, 'D3 output root');
  await durableMkdir(outputRoot);
  const result = await writeDurableHashed(resolve(outputRoot, 'result.json'), {
    schemaVersion: 'bfs.b61ExrReopenReconciliationResult.v0.1', status: 'PASS',
    verdict: 'BLENDER_BUNDLED_OPENIMAGEIO_COMBINED_RGBA_DECODER_SUPPORTED',
    toolFreezeCommit: parsed.toolFreezeCommit, toolHashes,
    retainedResult: { uri: spec.failedDiagnostic.result.uri, sha256: await sha256File(resultPath), storedHash, nodeCanonicalHash },
    reconciliation: { pythonCanonicalHash: python.python, pythonIntegralFloatNormalizedHash: python.normalized, normalizedMatchesNode: python.normalized === nodeCanonicalHash },
    projection: { sha256: first.sha256, width: first.width, height: first.height, channels: first.channels, valueCount: first.valueCount, allValuesFinite: first.allValuesFinite, repeatDigestExact: retained.repeatDigestExact },
    operations: { blenderProcesses: 0, renderCalls: 0, bundledPythonProcesses: 1, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    bundledPythonSeconds: pythonSeconds, claimBoundary: spec.claimBoundary,
  }, 'resultHash');
  const receipt = await writeDurableHashed(resolve(outputRoot, 'receipt.json'), {
    schemaVersion: 'bfs.b61ExrReopenReconciliationReceipt.v0.1', status: 'PASS', verdict: result.verdict,
    result: { uri: `${parsed.outputRoot}/result.json`, sha256: await sha256File(resolve(outputRoot, 'result.json')), resultHash: result.resultHash },
    operations: result.operations, claimBoundary: spec.claimBoundary,
  }, 'receiptHash');
  const bytes = (await Promise.all((await walk(outputRoot)).map(path => readFile(path)))).reduce((sum, value) => sum + value.length, 0);
  assert(bytes <= spec.resourceCeilings.maximumOutputBytes, 'D3 output ceiling exceeded');
  process.stdout.write(`BFS_B61_D3 PASS ${first.sha256} ${receipt.receiptHash}\n`);
  return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runD3(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B61_D3_ERROR ${error.message}\n`); process.exitCode = 1; });
}
