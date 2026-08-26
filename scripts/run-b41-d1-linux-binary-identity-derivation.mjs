import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, stat, statfs, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import {
  B41_D1_PREREG_COMMIT, B41_D1_SPEC_SHA256, analyzeB41D1Evidence, buildB41D1Attacks,
  hashB41D1Evidence, readB41D1Spec,
} from './lib/b41-d1-linux-binary-identity-derivation.mjs';

const spec = await readB41D1Spec();
const outputRoot = resolve(repositoryRoot, 'experiments/linux-amd64-blender-binary-identity-derivation-v0-1');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b41-d1-linux-binary-identity-derivation.mjs');
const libraryPath = resolve(repositoryRoot, 'scripts/lib/b41-d1-linux-binary-identity-derivation.mjs');
const auditPath = resolve(repositoryRoot, 'scripts/audit-b41-d1-linux-binary-identity-derivation.mjs');
const operations = [];
const errors = [];

function probe(executable, args, label, options = {}) {
  const result = spawnSync(executable, args, {
    cwd: repositoryRoot, encoding: 'utf8', maxBuffer: options.maxBuffer ?? 10 * 1024 * 1024,
    timeout: options.timeout ?? 120000,
  });
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
    child.stdout.on('data', chunk => {
      digest.update(chunk);
      bytes += chunk.length;
      if (prefix.length < 64) prefix = Buffer.concat([prefix, chunk.subarray(0, 64 - prefix.length)]);
    });
    child.stderr.on('data', chunk => { stderr += chunk.toString(); });
    child.on('error', reject);
    child.on('close', code => code === 0
      ? resolvePromise({ sha256: digest.digest('hex'), bytes, prefix })
      : reject(new Error(`host member stream failed (${code}): ${stderr.trim().slice(-4000)}`)));
  });
}

function guestMemberIdentity(archivePath, member) {
  if (/[^A-Za-z0-9_./-]/.test(archivePath) || /[^A-Za-z0-9_./-]/.test(member)) throw new Error('unsafe guest derivation path');
  const command = `set -eu; tar -xJOf '${archivePath}' '${member}' | sha256sum; tar -xJOf '${archivePath}' '${member}' | wc -c`;
  const output = probe('colima', ['ssh', '--', 'sh', '-lc', command], 'Colima guest member derivation', { timeout: 5 * 60 * 1000 });
  const lines = output.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const sha256 = lines[0]?.match(/^([a-f0-9]{64})\b/)?.[1] ?? null;
  const bytes = Number(lines[1]);
  if (!sha256 || !Number.isSafeInteger(bytes)) throw new Error(`guest derivation output invalid: ${output}`);
  return { sha256, bytes };
}

if (spawnSync('git', ['merge-base', '--is-ancestor', B41_D1_PREREG_COMMIT, 'HEAD'], { cwd: repositoryRoot }).status !== 0) {
  throw new Error('B41-D1 preregistration is not an ancestor');
}
const toolFreezeCommit = probe('git', ['rev-parse', 'HEAD'], 'tool freeze identity');
if (probe('git', ['status', '--porcelain', '--untracked-files=no'], 'tracked status') !== '') throw new Error('B41-D1 tracked worktree must be clean');
const filesystem = await statfs(repositoryRoot, { bigint: true });
const availableBytes = filesystem.bavail * filesystem.bsize;
const freeAfterProjectedBytes = availableBytes - BigInt(spec.diskAdmission.projectedWriteBytes);
const diskAdmission = {
  availableBytes: String(availableBytes),
  projectedWriteBytes: String(spec.diskAdmission.projectedWriteBytes),
  minimumReserveBytes: String(spec.diskAdmission.minimumReserveBytes),
  freeAfterProjectedBytes: String(freeAfterProjectedBytes),
  status: freeAfterProjectedBytes >= BigInt(spec.diskAdmission.minimumReserveBytes) ? 'ACCEPTED' : 'BLOCKED',
};
if (diskAdmission.status !== 'ACCEPTED') throw new Error('B41-D1 disk admission blocked');

await mkdir(outputRoot, { recursive: false });
const temporaryRoot = await mkdtemp(resolve(repositoryRoot, '.bfs-b41-d1-'));
const archivePath = resolve(temporaryRoot, spec.artifact.filename);
let artifact = { url: spec.artifact.url, filename: spec.artifact.filename, bytes: null, sha256: null };
let member = { path: spec.artifact.member, cardinality: null };
let derivations = { host: {}, guest: {} };
let elf = {};
let temporaryArchiveRemoved = false;
try {
  operations.push('ARCHIVE_DOWNLOAD');
  await download(spec.artifact.url, archivePath);
  artifact = { ...artifact, bytes: (await stat(archivePath)).size, sha256: await sha256File(archivePath) };
  if (artifact.bytes !== spec.artifact.bytes || artifact.sha256 !== spec.artifact.sha256) throw new Error('B41-D1 archive identity differs');
  const listing = probe('tar', ['-tJf', archivePath], 'archive member listing', { maxBuffer: 20 * 1024 * 1024, timeout: 5 * 60 * 1000 });
  member.cardinality = listing.split(/\r?\n/).filter(line => line === spec.artifact.member).length;
  if (member.cardinality !== 1) throw new Error(`B41-D1 member cardinality differs: ${member.cardinality}`);
  operations.push('HOST_MEMBER_STREAM');
  const host = await streamHostMember(archivePath, spec.artifact.member);
  derivations.host = { method: spec.derivation.hostMethod, sha256: host.sha256, bytes: host.bytes };
  elf = {
    magicHex: host.prefix.subarray(0, 4).toString('hex'),
    class: host.prefix[4] === 2 ? 'ELF64' : `UNKNOWN_${host.prefix[4]}`,
    endianness: host.prefix[5] === 1 ? 'little' : host.prefix[5] === 2 ? 'big' : `UNKNOWN_${host.prefix[5]}`,
    machine: host.prefix.readUInt16LE(18) === 62 ? 'x86-64' : `UNKNOWN_${host.prefix.readUInt16LE(18)}`,
    machineCode: host.prefix.readUInt16LE(18),
    prefix64Hex: host.prefix.toString('hex'),
  };
  operations.push('COLIMA_GUEST_MEMBER_STREAM');
  derivations.guest = { method: spec.derivation.guestMethod, ...guestMemberIdentity(archivePath, spec.artifact.member) };
} catch (error) {
  errors.push(error instanceof Error ? error.message : String(error));
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
  temporaryArchiveRemoved = true;
}

const evidence = {
  schemaVersion: 'bfs.linuxAmd64BlenderBinaryIdentityDerivationEvidence.v0.1',
  experimentId: 'B41-D1',
  status: 'OFFICIAL_ARCHIVE_MEMBER_IDENTITY_DERIVATION',
  preregistration: { commit: B41_D1_PREREG_COMMIT, specSha256: B41_D1_SPEC_SHA256 },
  parent: spec.parent,
  toolFreezeCommit,
  tools: {
    runner: { uri: 'scripts/run-b41-d1-linux-binary-identity-derivation.mjs', sha256: await sha256File(runnerPath) },
    library: { uri: 'scripts/lib/b41-d1-linux-binary-identity-derivation.mjs', sha256: await sha256File(libraryPath) },
    audit: { uri: 'scripts/audit-b41-d1-linux-binary-identity-derivation.mjs', sha256: await sha256File(auditPath) },
  },
  runtime: { nodeVersion: process.version, nodeBinary: process.execPath, hostTar: probe('tar', ['--version'], 'host tar version').split('\n')[0], colima: probe('colima', ['version'], 'Colima version').split('\n')[0] },
  diskAdmission,
  artifact,
  member,
  derivations,
  elf,
  cleanup: { temporaryArchiveRemoved },
  runtimeOperationsExecuted: operations,
  errors,
};
evidence.attacks = buildB41D1Attacks(evidence, spec);
evidence.evidenceHash = hashB41D1Evidence(evidence);
evidence.analysis = analyzeB41D1Evidence(evidence, spec);
evidence.verdict = evidence.analysis.decision;
evidence.nonClaims = spec.nonClaims;
await writeFile(resolve(outputRoot, 'results.json'), `${JSON.stringify(evidence, null, 2)}\n`);
process.stdout.write(`BFS_B41_D1 ${evidence.analysis.passed ? 'PASS' : 'FAIL'} sha256=${derivations.host.sha256 ?? 'none'} attacks=${evidence.attacks.filter(item => item.passed).length}/${evidence.attacks.length} decision=${evidence.verdict}\n`);
if (!evidence.analysis.passed || !evidence.attacks.every(item => item.passed)) process.exitCode = 1;
