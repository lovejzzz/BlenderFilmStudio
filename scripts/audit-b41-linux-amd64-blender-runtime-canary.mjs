import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { analyzeB41Evidence, readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';

const root = resolve(repositoryRoot, 'experiments/linux-amd64-blender-runtime-canary-v0-1');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const spec = await readB41Spec();
const analysis = analyzeB41Evidence(result, spec);
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
const observedArtifacts = {
  png: await pngInfo(resolve(root, 'success/canary.png')),
  blend: await fileInfo(resolve(root, 'success/canary.blend')),
};
const toolHashes = {
  runner: await sha256File(resolve(repositoryRoot, result.tools.runner.uri)),
  library: await sha256File(resolve(repositoryRoot, result.tools.library.uri)),
  audit: await sha256File(resolve(repositoryRoot, result.tools.audit.uri)),
  dockerfile: await sha256File(resolve(repositoryRoot, result.tools.dockerfile.uri)),
  runtimeCanary: await sha256File(resolve(repositoryRoot, result.tools.runtimeCanary.uri)),
  timeoutCanary: await sha256File(resolve(repositoryRoot, result.tools.timeoutCanary.uri)),
};
const toolsMatch = Object.entries(toolHashes).every(([key, digest]) => digest === result.tools[key].sha256);
const artifactsMatch = JSON.stringify(observedArtifacts) === JSON.stringify(result.success.artifacts);
const audit = {
  schemaVersion: 'bfs.linuxAmd64BlenderRuntimeIndependentAudit.v0.1', experimentId: 'B41', analysis,
  toolsMatch, observedArtifacts, artifactsMatch,
  timeoutNonPromotable: result.timeout?.promotable === false,
  passed: analysis.passed && toolsMatch && artifactsMatch && result.timeout?.promotable === false,
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B41_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} tools=${toolsMatch ? 'MATCH' : 'MISMATCH'} artifacts=${artifactsMatch ? 'MATCH' : 'MISMATCH'} timeoutPromotable=${result.timeout?.promotable}\n`);
if (!audit.passed) process.exitCode = 1;
