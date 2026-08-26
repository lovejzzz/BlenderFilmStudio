import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { readB41C1Spec } from './lib/b41-c1-docker-architecture-correction.mjs';
import { readB41C2Spec } from './lib/b41-c2-build-receipt-tooling-correction.mjs';
import { analyzeB41C3Evidence, readB41C3Spec } from './lib/b41-c3-guest-buildx-correction.mjs';

const root = resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-4');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const baseSpec = await readB41Spec();
const c1Spec = await readB41C1Spec();
const c2Spec = await readB41C2Spec();
const c3Spec = await readB41C3Spec();
const analysis = analyzeB41C3Evidence(result, c3Spec, c2Spec, c1Spec, baseSpec);
async function pngInfo(path) {
  try {
    const bytes = await readFile(path);
    return {
      valid: bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR',
      dimensions: bytes.length >= 24 ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null,
      bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'),
    };
  } catch { return { valid: false, dimensions: null, bytes: 0, sha256: null }; }
}
async function fileInfo(path) {
  try { const bytes = await readFile(path); return { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }
  catch { return { bytes: 0, sha256: null }; }
}
const observedArtifacts = { png: await pngInfo(resolve(root, 'success/canary.png')), blend: await fileInfo(resolve(root, 'success/canary.blend')) };
const toolHashes = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => [key, await sha256File(resolve(repositoryRoot, item.uri))])));
const toolsMatch = Object.entries(toolHashes).every(([key, digest]) => digest === result.tools[key].sha256);
const artifactsMatch = JSON.stringify(observedArtifacts) === JSON.stringify(result.success.artifacts);
const audit = {
  schemaVersion: 'bfs.linuxAmd64BlenderRuntimeIndependentAudit.v0.4', experimentId: 'B41-C3', analysis,
  toolsMatch, observedArtifacts, artifactsMatch, timeoutNonPromotable: result.timeout?.promotable === false,
  passed: analysis.passed && toolsMatch && artifactsMatch && result.timeout?.promotable === false,
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B41_C3_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} tools=${toolsMatch ? 'MATCH' : 'MISMATCH'} artifacts=${artifactsMatch ? 'MATCH' : 'MISMATCH'} timeoutPromotable=${result.timeout?.promotable}\n`);
if (!audit.passed) process.exitCode = 1;
