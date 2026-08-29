#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { open, readFile, readdir, statfs } from 'node:fs/promises';
import { relative, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { measureOutput } from './lib/budgeted-process.mjs';
import { durableMkdir, repoUri, repositoryRoot, resolveExistingRepositoryPath, resolveFreshRepositoryPath, sha256Bytes, sha256File, validSelfHash, writeDurableHashed } from './preflight-b62-phase0.mjs';

const execFileAsync = promisify(execFile);
const C11 = 'specs/b62-phase0-c11-auditor-library-locality-correction.v0.1.json';
const ROOT = 'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1';
const PREREG = '7060fbf';
const TOOLS = [C11, 'research/2026-08-29-b62-phase0-c11-auditor-library-locality-correction.md', 'blender/audit_b62_phase0.py', 'scripts/run-b62-d7-corrected-auditor-smoke.mjs', 'scripts/audit-b62-d7-corrected-auditor-smoke.mjs'];

async function git(args, encoding = 'utf8') { return (await execFileAsync('/usr/bin/git', args, { cwd: repositoryRoot, encoding, timeout: 15000, maxBuffer: 32 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' } })).stdout; }
async function treeIdentity(uri) {
  const root = await resolveExistingRepositoryPath(uri, uri, 'directory'); const files = [];
  async function walk(directory) { for (const entry of await readdir(directory, { withFileTypes: true })) { const path = resolve(directory, entry.name); if (entry.isDirectory()) await walk(path); else if (entry.isFile()) files.push(path); else throw new Error(path); } }
  await walk(root); files.sort(); let bytes = 0; let material = '';
  for (const path of files) { const content = await readFile(path); bytes += content.length; material += `${relative(root, path).split('\\').join('/')}\0${sha256Bytes(content)}\n`; }
  return { files: files.length, bytes, treeSha256: sha256Bytes(Buffer.from(material)) };
}
async function log(path, value) { const bytes = Buffer.from(value); const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); } return { uri: repoUri(path), sha256: sha256Bytes(bytes), bytes: bytes.length }; }

export async function runD7(argv) {
  if (argv.length !== 2 || argv[0] !== '--tool-freeze-commit' || !/^[0-9a-f]{40}$/.test(argv[1])) throw new Error('usage'); const freeze = argv[1];
  if ((await git(['rev-parse', 'HEAD'])).trim() !== freeze || (await git(['rev-parse', 'origin/main'])).trim() !== freeze) throw new Error('freeze'); await git(['merge-base', '--is-ancestor', PREREG, freeze]);
  const toolHashes = {}; for (const uri of TOOLS) { const path = await resolveExistingRepositoryPath(uri, uri); const hash = await sha256File(path); if (hash !== sha256Bytes(await git(['show', `${freeze}:${uri}`], null))) throw new Error(`drift ${uri}`); toolHashes[uri] = hash; }
  const correctionPath = await resolveExistingRepositoryPath(C11, 'C11'); const correction = JSON.parse(await readFile(correctionPath, 'utf8')); if (correction.statusBeforeAuditorChange !== 'PREREGISTERED' || correction.authorizedDiagnostic.root !== ROOT) throw new Error('C11');
  const d6 = correction.promotingEvidence; if (JSON.stringify(await treeIdentity(d6.root)) !== JSON.stringify(d6.tree)) throw new Error('D6 tree');
  for (const [name, field] of [['probe', 'probeHash'], ['result', 'resultHash'], ['receipt', 'receiptHash']]) { const path = await resolveExistingRepositoryPath(`${d6.root}/${name}.json`, `D6 ${name}`); const value = JSON.parse(await readFile(path, 'utf8')); if (await sha256File(path) !== d6[name].sha256 || !validSelfHash(value, field) || value[field] !== d6[name][field] || value.status !== 'PASS') throw new Error(`D6 ${name}`); }
  const root = await resolveFreshRepositoryPath(ROOT, 'D7 root'); await durableMkdir(root);
  const formalRoot = correction.authorizedDiagnostic.sourceFormalRoot; const master = await resolveExistingRepositoryPath(`${formalRoot}/scene/B62_PHASE0_MASTER.blend`, 'D7 master'); const auditPath = resolve(root, 'blender-audit.json');
  const started = process.hrtime.bigint(); let child;
  try { const value = await execFileAsync('/usr/bin/time', ['-lp', '/Applications/Blender.app/Contents/MacOS/Blender', '--background', master, '--disable-autoexec', '--python-exit-code', '1', '--python', resolve(repositoryRoot, 'blender/audit_b62_phase0.py'), '--', '--repository-root', repositoryRoot, '--formal-root', resolve(repositoryRoot, formalRoot), '--output', auditPath], { cwd: repositoryRoot, encoding: 'utf8', timeout: 120000, maxBuffer: 16 * 1024 * 1024, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', OCIO: resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio') } }); child = { exitCode: 0, stdout: value.stdout, stderr: value.stderr }; } catch (error) { child = { exitCode: typeof error.code === 'number' ? error.code : 1, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message }; }
  const elapsedSeconds = Number(process.hrtime.bigint() - started) / 1e9; const stdout = await log(resolve(root, 'stdout.log'), child.stdout); const stderr = await log(resolve(root, 'stderr.log'), child.stderr); if (child.exitCode !== 0) throw new Error('corrected auditor failed');
  const audit = JSON.parse(await readFile(auditPath, 'utf8')); const output = await measureOutput(root); const filesystem = await statfs(repositoryRoot, { bigint: true });
  const checks = [
    ['AUDITOR_EXIT_ZERO', child.exitCode === 0], ['AUDIT_SELF_HASH_VALID', validSelfHash(audit, 'auditHash')],
    ['UNCHANGED_23_CHECKS_PASS', audit.status === 'PASS' && Object.keys(audit.checks).length === 23 && Object.values(audit.checks).every(Boolean)],
    ['MASTER_INITIAL_LOCAL', audit.masterLocality.libraries.length === 0 && audit.masterLocality.linkedIds.length === 0],
    ['THREE_ASSET_LOCALITY_ROWS_PASS', audit.assetLibraries.length === 3 && audit.assetLibraries.every(row => row.findings.length === 0 && row.locality.appendedIds.every(item => item.library === null) && row.locality.sourceDescriptors.length === 1 && row.locality.descriptorRemovalErrors.length === 0 && row.locality.afterDescriptorRemoval.every(item => item.present && item.library === null) && Object.values(row.locality.cleanup).every(Boolean))],
    ['RETAINED_RENDER_EVIDENCE_COMPLETE', audit.calibration.length === 3 && audit.checks.animaticRosterExact && audit.checks.calibrationTriplesExact],
    ['BUDGET_PASS', output.bytes <= correction.authorizedDiagnostic.maximumWriteBytes && output.symlinkCount === 0 && filesystem.bavail * filesystem.bsize >= BigInt(correction.authorizedDiagnostic.minimumReserveBytes)],
    ['ZERO_RENDER_EXTERNAL_CALLS', audit.operations.blenderStarts === 1 && audit.operations.renderCalls === 0 && audit.operations.modelCalls === 0 && audit.operations.networkCalls === 0 && audit.operations.dockerProcesses === 0],
  ].map(([id, pass]) => ({ id, pass })); const status = checks.every(row => row.pass) ? 'PASS' : 'FAIL';
  const result = await writeDurableHashed(resolve(root, 'result.json'), { schemaVersion: 'bfs.b62Phase0D7Result.v0.1', experimentId: 'B62-P0-D7', status, correction: { uri: C11, sha256: await sha256File(correctionPath) }, toolFreezeCommit: freeze, toolHashes, d6: { receiptHash: d6.receipt.receiptHash }, correctedAudit: { uri: repoUri(auditPath), sha256: await sha256File(auditPath), auditHash: audit.auditHash }, checks, output, process: { exitCode: child.exitCode, elapsedSeconds, stdout, stderr, timing: { realSeconds: Number(child.stderr.match(/^real\s+([0-9.]+)/m)?.[1] ?? elapsedSeconds), userSeconds: Number(child.stderr.match(/^user\s+([0-9.]+)/m)?.[1] ?? 0), systemSeconds: Number(child.stderr.match(/^sys\s+([0-9.]+)/m)?.[1] ?? 0), maximumResidentSetSizeBytes: Number(child.stderr.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? 0) } }, operations: audit.operations }, 'resultHash');
  const receipt = await writeDurableHashed(resolve(root, 'receipt.json'), { schemaVersion: 'bfs.b62Phase0D7Receipt.v0.1', experimentId: 'B62-P0-D7', status, verdict: status === 'PASS' ? 'CORRECTED_PRODUCTION_AUDITOR_PROVEN' : 'B62_D7_INVALIDATED', result: { uri: `${ROOT}/result.json`, sha256: await sha256File(resolve(root, 'result.json')), resultHash: result.resultHash }, correctedAuditHash: audit.auditHash, operations: audit.operations }, 'receiptHash');
  if (status !== 'PASS') throw new Error('D7 checks'); process.stdout.write(`BFS_B62_D7 PASS 8/8 ${receipt.receiptHash}\n`); return receipt;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) runD7(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B62_D7_ERROR ${error.message}\n`); process.exitCode = 1; });
