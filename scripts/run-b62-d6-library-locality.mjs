#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile, readdir, statfs } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { measureOutput } from './lib/budgeted-process.mjs';
import { durableMkdir, repoUri, repositoryRoot, resolveExistingRepositoryPath, resolveFreshRepositoryPath, sha256Bytes, sha256File, validSelfHash, writeDurableHashed } from './preflight-b62-phase0.mjs';

const execFileAsync = promisify(execFile);
const C10 = 'specs/b62-phase0-c10-library-locality-diagnostic.v0.1.json';
const ROOT = 'experiments/b62-phase0-d6-library-locality-v0-1';
const PREREG = '1ce8ffd';
const TOOLS = [C10, 'research/2026-08-29-b62-phase0-c10-library-locality-diagnostic.md', 'blender/probe_b62_d6_library_locality.py', 'scripts/run-b62-d6-library-locality.mjs', 'scripts/audit-b62-d6-library-locality.mjs'];

async function git(args, encoding = 'utf8') {
  return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout;
}
async function treeIdentity(uri) {
  const root = await resolveExistingRepositoryPath(uri, uri, 'directory'); const files = [];
  async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(`special ${path}`); } }
  await walk(root); files.sort(); let bytes = 0; let material = '';
  for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`; }
  return { files: files.length, bytes, treeSha256: sha256Bytes(Buffer.from(material)) };
}
async function log(path, value) { const bytes = Buffer.from(value); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); } return { uri: repoUri(path), sha256: sha256Bytes(bytes), bytes: bytes.length }; }

export async function runD6(argv) {
  if (argv.length !== 2 || argv[0] !== '--tool-freeze-commit' || !/^[0-9a-f]{40}$/.test(argv[1])) throw new Error('usage');
  const freeze = argv[1];
  if ((await git(['rev-parse', 'HEAD'])).trim() !== freeze || (await git(['rev-parse', 'origin/main'])).trim() !== freeze) throw new Error('freeze');
  await git(['merge-base', '--is-ancestor', PREREG, freeze]);
  const toolHashes = {};
  for (const uri of TOOLS) { const path = await resolveExistingRepositoryPath(uri, uri); const hash = await sha256File(path); if (hash !== sha256Bytes(await git(['show', `${freeze}:${uri}`], null))) throw new Error(`drift ${uri}`); toolHashes[uri] = hash; }
  const correctionPath = await resolveExistingRepositoryPath(C10, 'C10'); const correction = JSON.parse(await readFile(correctionPath, 'utf8'));
  if (correction.statusBeforeDiagnostic !== 'PREREGISTERED' || correction.authorizedDiagnostic.root !== ROOT) throw new Error('C10');
  for (const [uri, expected] of [[correction.retainedV03Failure.attemptRoot, correction.retainedV03Failure.attemptTree], [correction.retainedV03Failure.formalRoot, correction.retainedV03Failure.formalTree]]) if (JSON.stringify(await treeIdentity(uri)) !== JSON.stringify(expected)) throw new Error(`retained ${uri}`);
  const failurePath = await resolveExistingRepositoryPath(`${correction.retainedV03Failure.attemptRoot}/failure.json`, 'v03 failure'); const failure = JSON.parse(await readFile(failurePath, 'utf8'));
  const auditPath = await resolveExistingRepositoryPath(`${correction.retainedV03Failure.formalRoot}/reports/blender-audit.json`, 'v03 audit'); const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  if (await sha256File(failurePath) !== correction.retainedV03Failure.failure.sha256 || !validSelfHash(failure, 'failureHash') || failure.failureHash !== correction.retainedV03Failure.failure.failureHash
    || await sha256File(auditPath) !== correction.retainedV03Failure.blenderAudit.sha256 || !validSelfHash(audit, 'auditHash') || audit.auditHash !== correction.retainedV03Failure.blenderAudit.auditHash) throw new Error('retained hashes');
  const root = await resolveFreshRepositoryPath(ROOT, 'D6 root'); await durableMkdir(root);
  const probePath = resolve(root, 'probe.json'); const masterPath = await resolveExistingRepositoryPath(correction.authorizedDiagnostic.sourceMaster, 'D6 master');
  const started = process.hrtime.bigint(); let child;
  try {
    const value = await execFileAsync('/usr/bin/time', ['-lp', '/Applications/Blender.app/Contents/MacOS/Blender', '--background', masterPath, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/probe_b62_d6_library_locality.py'), '--', '--formal-root', resolve(repositoryRoot, correction.retainedV03Failure.formalRoot), '--output', probePath], { cwd: repositoryRoot, encoding: 'utf8', timeout: 120000, maxBuffer: 16 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio') } });
    child = { exitCode: 0, stdout: value.stdout, stderr: value.stderr };
  } catch (error) { child = { exitCode: typeof error.code === 'number' ? error.code : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message }; }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9; const stdout = await log(resolve(root, 'stdout.log'), child.stdout); const stderr = await log(resolve(root, 'stderr.log'), child.stderr);
  if (child.exitCode !== 0) throw new Error('probe process failed');
  const probe = JSON.parse(await readFile(probePath, 'utf8')); const filesystem = await statfs(repositoryRoot, { bigint: true }); const output = await measureOutput(root);
  const checks = [
    ['PROBE_EXIT_ZERO', child.exitCode === 0],
    ['PROBE_SELF_HASH_VALID', validSelfHash(probe, 'probeHash')],
    ['MASTER_INITIAL_LOCAL', probe.checks.masterInitialLibrariesZero && probe.checks.masterInitialLinkedIdsZero],
    ['THREE_ASSETS_LOCAL', probe.assets.length === 3 && probe.assets.every(row => row.checks.appendedIdsAllLocal)],
    ['DESCRIPTORS_EXACT_SOURCE', probe.assets.every(row => row.checks.sourceDescriptorsObserved && row.checks.descriptorsExactSource)],
    ['LOCAL_IDS_SURVIVE_DESCRIPTOR_REMOVAL', probe.assets.every(row => row.checks.descriptorRemovalSucceeded && row.checks.localIdsSurviveDescriptorRemoval)],
    ['CLEANUP_EXACT', probe.assets.every(row => row.checks.cleanupExact) && probe.checks.finalLibrariesZero && probe.checks.finalLinkedIdsZero && probe.checks.finalRosterExact],
    ['BUDGET_AND_ZERO_EXTERNAL_CALLS', output.bytes <= correction.authorizedDiagnostic.maximumWriteBytes && output.symlinkCount === 0 && filesystem.bavail * filesystem.bsize >= BigInt(correction.authorizedDiagnostic.minimumReserveBytes) && probe.operations.renderCalls === 0 && probe.operations.modelCalls === 0 && probe.operations.networkCalls === 0 && probe.operations.dockerProcesses === 0],
  ].map(([id, pass]) => ({ id, pass }));
  const status = checks.every(row => row.pass) && probe.status === 'PASS' ? 'PASS' : 'FAIL';
  const result = await writeDurableHashed(resolve(root, 'result.json'), { schemaVersion: 'bfs.b62Phase0D6Result.v0.1', experimentId: 'B62-P0-D6', status, correction: { uri: C10, sha256: await sha256File(correctionPath) }, toolFreezeCommit: freeze, toolHashes, retained: { failureHash: failure.failureHash, auditHash: audit.auditHash }, probe: { uri: repoUri(probePath), sha256: await sha256File(probePath), probeHash: probe.probeHash }, checks, output, process: { exitCode: child.exitCode, elapsedSeconds, stdout, stderr, timing: { realSeconds: Number(child.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? elapsedSeconds), userSeconds: Number(child.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0), systemSeconds: Number(child.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0), maximumResidentSetSizeBytes: Number(child.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0) } }, operations: probe.operations }, 'resultHash');
  const receipt = await writeDurableHashed(resolve(root, 'receipt.json'), { schemaVersion: 'bfs.b62Phase0D6Receipt.v0.1', experimentId: 'B62-P0-D6', status, verdict: status === 'PASS' ? 'LOCAL_APPEND_SOURCE_DESCRIPTOR_ONLY' : 'TRUE_EXTERNAL_LINK_OR_MASTER_DEPENDENCY', result: { uri: `${ROOT}/result.json`, sha256: await sha256File(resolve(root, 'result.json')), resultHash: result.resultHash }, probeHash: probe.probeHash, operations: probe.operations }, 'receiptHash');
  if (status !== 'PASS') throw new Error('D6 checks failed');
  process.stdout.write(`BFS_B62_D6 PASS 8/8 ${receipt.receiptHash}\n`); return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runD6(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_D6_ERROR ${error.message}\n`); process.exitCode = 1; });
