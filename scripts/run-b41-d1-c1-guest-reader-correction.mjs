import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import { mkdir, mkdtemp, rm, stat, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { readB41D1Spec } from './lib/b41-d1-linux-binary-identity-derivation.mjs';
import {
  B41_D1_C1_PREREG_COMMIT, B41_D1_C1_SPEC_SHA256, analyzeB41D1C1Evidence,
  buildB41D1C1Attacks, hashB41D1C1Evidence, readB41D1C1Spec,
} from './lib/b41-d1-c1-guest-reader-correction.mjs';

const baseSpec = await readB41D1Spec();
const correctionSpec = await readB41D1C1Spec();
const outputRoot = resolve(repositoryRoot, 'experiments/linux-amd64-blender-binary-identity-derivation-v0-2');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b41-d1-c1-guest-reader-correction.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b41-d1-c1-guest-reader-correction.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b41-d1-c1-guest-reader-correction.mjs');
const operations = [];
const errors = [];

function probe(executable, args, label, options = {}) {
  const result = spawnSync(executable, args, { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: options.maxBuffer ?? 10 * 1024 * 1024, timeout: options.timeout ?? 120000 });
  if (result.status !== 0) throw new Error(`${label} failed (${result.status}): ${(result.stderr || result.stdout || '').trim().slice(-4000)}`);
  return result.stdout.trim();
}

async function download(url, destination) {
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok || !response.body) throw new Error(`download failed: HTTP ${response.status}`);
  await pipeline(Readable.fromWeb(response.body), createWriteStream(destination, { flags: 'wx' }));
}

function streamHostMember(archivePath, member) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn('tar', ['-xJOf', archivePath, member], { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    const digest = createHash('sha256');
    let bytes = 0;
    let prefix = Buffer.alloc(0);
    let stderr = '';
    child.stdout.on('data', chunk => { digest.update(chunk); bytes += chunk.length; if (prefix.length < 64) prefix = Buffer.concat([prefix, chunk.subarray(0, 64 - prefix.length)]); });
    child.stderr.on('data', chunk => { stderr += chunk.toString(); });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ sha256: digest.digest('hex'), bytes, prefix }) : reject(new Error(`host member stream failed (${code}): ${stderr.trim().slice(-4000)}`)));
  });
}

function guestMemberIdentity(archivePath, member) {
  const program = [
    'import hashlib,json,sys,tarfile',
    'archive,member=sys.argv[1:3]',
    'digest=hashlib.sha256()',
    'count=0',
    'with tarfile.open(archive,"r:xz") as bundle:',
    '    info=bundle.getmember(member)',
    '    stream=bundle.extractfile(info)',
    '    assert stream is not None',
    '    while True:',
    '        chunk=stream.read(1048576)',
    '        if not chunk: break',
    '        digest.update(chunk)',
    '        count += len(chunk)',
    'print(json.dumps({"bytes":count,"sha256":digest.hexdigest()},sort_keys=True,separators=(",",":")))',
  ].join('\n');
  const output = probe('colima', ['ssh', '--', 'python3', '-c', program, archivePath, member], 'Colima Python member derivation', { timeout: 5 * 60 * 1000 });
  const lines = output.split(/\r?\n/).filter(Boolean);
  if (lines.length !== 1) throw new Error(`guest derivation emitted ${lines.length} lines`);
  const parsed = JSON.parse(lines[0]);
  if (!/^[a-f0-9]{64}$/.test(parsed.sha256 ?? '') || !Number.isSafeInteger(parsed.bytes) || parsed.bytes <= 0) throw new Error('guest derivation JSON invalid');
  return parsed;
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B41_D1_C1_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) throw new Error('B41-D1-C1 preregistration is not an ancestor');
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B41-D1-C1 tracked worktree must be clean');
const parentResultSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-binary-identity-derivation-v0-1/results.json'));
const parentAuditSha256 = await sha256File(resolve(repositoryRoot, 'experiments/linux-amd64-blender-binary-identity-derivation-v0-1/audit.json'));
if (parentResultSha256 !== correctionSpec.parent.failedResultSha256 || parentAuditSha256 !== correctionSpec.parent.failedAuditSha256) throw new Error('B41-D1-C1 parent evidence differs');
const pythonVersion = probe('colima', ['ssh', '--', 'python3', '-c', 'import sys; print(sys.version.split()[0])'], 'Colima Python version');
if (pythonVersion !== correctionSpec.guestCorrection.pythonVersionExact) throw new Error(`B41-D1-C1 Python version differs: ${pythonVersion}`);
const filesystem = await statfs(repositoryRoot, { bigint: true });
const availableBytes = filesystem.bavail * filesystem.bsize;
const freeAfterProjectedBytes = availableBytes - BigInt(baseSpec.diskAdmission.projectedWriteBytes);
const diskAdmission = { availableBytes: String(availableBytes), projectedWriteBytes: String(baseSpec.diskAdmission.projectedWriteBytes), minimumReserveBytes: String(baseSpec.diskAdmission.minimumReserveBytes), freeAfterProjectedBytes: String(freeAfterProjectedBytes), status: freeAfterProjectedBytes >= BigInt(baseSpec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED' };
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B41-D1-C1 disk admission blocked');

await mkdir(outputRoot, { recursive: false });
const temporaryRoot = await mkdtemp(resolve(repositoryRoot, '.bfs-b41-d1-c1-'));
const archivePath = resolve(temporaryRoot, baseSpec.artifact.filename);
let artifact = { url: baseSpec.artifact.url, filename: baseSpec.artifact.filename, bytes: null, sha256: null };
let member = { path: baseSpec.artifact.member, cardinality: null };
let derivations = { host: {}, guest: {} };
let elf = {};
let temporaryArchiveRemoved = false;
try {
  operations.push('ARCHIVE_DOWNLOAD');
  await download(baseSpec.artifact.url, archivePath);
  artifact = { ...artifact, bytes: (await stat(archivePath)).size, sha256: await sha256File(archivePath) };
  if (artifact.bytes !== baseSpec.artifact.bytes || artifact.sha256 !== baseSpec.artifact.sha256) throw new Error('B41-D1-C1 archive identity differs');
  const listing = probe('tar', ['-tJf', archivePath], 'archive member listing', { maxBuffer: 20 * 1024 * 1024, timeout: 5 * 60 * 1000 });
  member.cardinality = listing.split(/\r?\n/).filter(line => line === baseSpec.artifact.member).length;
  if (member.cardinality !== 1) throw new Error(`B41-D1-C1 member cardinality differs: ${member.cardinality}`);
  operations.push('HOST_MEMBER_STREAM');
  const host = await streamHostMember(archivePath, baseSpec.artifact.member);
  derivations.host = { method: baseSpec.derivation.hostMethod, sha256: host.sha256, bytes: host.bytes };
  elf = { magicHex: host.prefix.subarray(0, 4).toString('hex'), class: host.prefix[4] === 2 ? 'ELF64' : `UNKNOWN_${host.prefix[4]}`, endianness: host.prefix[5] === 1 ? 'little' : host.prefix[5] === 2 ? 'big' : `UNKNOWN_${host.prefix[5]}`, machine: host.prefix.readUInt16LE(18) === 62 ? 'x86-64' : `UNKNOWN_${host.prefix.readUInt16LE(18)}`, machineCode: host.prefix.readUInt16LE(18), prefix64Hex: host.prefix.toString('hex') };
  operations.push('COLIMA_GUEST_MEMBER_STREAM');
  derivations.guest = { method: correctionSpec.guestCorrection.reader, ...guestMemberIdentity(archivePath, baseSpec.artifact.member) };
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
  temporaryArchiveRemoved = true;
}

const evidence = {
  schemaVersion: 'bfs.linuxAmd64BlenderBinaryIdentityDerivationEvidence.v0.2', experimentId: 'B41-D1-C1', status: 'CORRECTED_OFFICIAL_ARCHIVE_MEMBER_IDENTITY_DERIVATION',
  preregistration: { commit: B41_D1_C1_PREREG_COMMIT, specSha256: B41_D1_C1_SPEC_SHA256 }, parent: baseSpec.parent,
  guestCorrection: { parent: correctionSpec.parent, changedImplementationExact: correctionSpec.guestCorrection.changedImplementationExact, pythonVersion, reader: correctionSpec.guestCorrection.reader, shellPipeline: false, installPackages: false },
  toolFreezeCommit,
  tools: { runner: { uri: 'scripts/run-b41-d1-c1-guest-reader-correction.mjs', sha256: await sha256File(runnerPath) }, library: { uri: 'scripts/lib/b41-d1-c1-guest-reader-correction.mjs', sha256: await sha256File(libraryPath) }, audit: { uri: 'scripts/audit-b41-d1-c1-guest-reader-correction.mjs', sha256: await sha256File(auditPath) } },
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, hostTar: probe('tar', ['--version'], 'host tar version').split('\n')[0], colima: probe('colima', ['version'], 'Colima version').split('\n')[0], guestPythonVersion: pythonVersion },
  diskAdmission, artifact, member, derivations, elf, cleanup: { temporaryArchiveRemoved }, runtimeOperationsExecuted: operations, errors,
};
evidence.attacks = buildB41D1C1Attacks(evidence, correctionSpec, baseSpec);
evidence.evidenceHash = hashB41D1C1Evidence(evidence);
evidence.analysis = analyzeB41D1C1Evidence(evidence, correctionSpec, baseSpec);
evidence.verdict = evidence.analysis.decision;
evidence.nonClaims = correctionSpec.nonClaims;
await writeFile(resolve(outputRoot, 'results.json'), `${JSON.stringify(evidence, null, 2)}\n`);
process.stdout.write(`BFS_B41_D1_C1 ${evidence.analysis.passed ? 'PASS' : 'FAIL'} sha256=${derivations.host.sha256 ?? 'none'} attacks=${evidence.attacks.filter(item => item.passed).length}/${evidence.attacks.length} decision=${evidence.verdict}\n`);
if (!evidence.analysis.passed || !evidence.attacks.every(item => item.passed)) process.exitCode = 1;
