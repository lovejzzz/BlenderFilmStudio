import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { readB41C1Spec } from './lib/b41-c1-docker-architecture-correction.mjs';
import { readB41C2Spec } from './lib/b41-c2-build-receipt-tooling-correction.mjs';
import { readB41C3Spec } from './lib/b41-c3-guest-buildx-correction.mjs';
import { readB41C4Spec } from './lib/b41-c4-platform-binary-identity-correction.mjs';
import { analyzeB41C5Evidence, readB41C5Spec } from './lib/b41-c5-eevee-enum-correction.mjs';

const root = resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-6');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const [baseSpec, c1Spec, c2Spec, c3Spec, c4Spec, c5Spec] = await Promise.all([readB41Spec(), readB41C1Spec(), readB41C2Spec(), readB41C3Spec(), readB41C4Spec(), readB41C5Spec()]);
const analysis = analyzeB41C5Evidence(result, c5Spec, c4Spec, c3Spec, c2Spec, c1Spec, baseSpec);
async function pngInfo(path) {
  try { const bytes = await readFile(path); return { valid: bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR', dimensions: bytes.length >= 24 ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }
  catch { return { valid: false, dimensions: null, bytes: 0, sha256: null }; }
}
async function fileInfo(path) {
  try { const bytes = await readFile(path); return { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }
  catch { return { bytes: 0, sha256: null }; }
}
const observedArtifacts = result.success?.artifacts ? { png: await pngInfo(resolve(root, 'success/canary.png')), blend: await fileInfo(resolve(root, 'success/canary.blend')) } : {};
const toolHashes = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => [key, await sha256File(resolve(repositoryRoot, item.uri))])));
const toolsMatch = Object.entries(toolHashes).every(([key, digest]) => digest === result.tools[key].sha256);
const artifactsMatch = JSON.stringify(observedArtifacts) === JSON.stringify(result.success?.artifacts ?? {});
const timeoutNonPromotable = result.timeout?.promotable === false;
const audit = { schemaVersion: 'bfs.linuxAmd64BlenderRuntimeIndependentAudit.v0.6', experimentId: 'B41-C5', analysis, toolsMatch, observedArtifacts, artifactsMatch, timeoutNonPromotable, passed: analysis.passed && toolsMatch && artifactsMatch && timeoutNonPromotable };
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B41_C5_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} tools=${toolsMatch ? 'MATCH' : 'MISMATCH'} artifacts=${artifactsMatch ? 'MATCH' : 'MISMATCH'} timeoutPromotable=${result.timeout?.promotable}\n`);
if (!audit.passed) process.exitCode = 1;
