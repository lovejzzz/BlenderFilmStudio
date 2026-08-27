import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { readB41Spec } from './lib/b41-linux-amd64-blender-runtime-canary.mjs';
import { analyzeB41D3Evidence, classifyB41D3, readB41D3Spec } from './lib/b41-d3-render-backend-control.mjs';

const root = resolve(repositoryRoot, 'experiments/linux-amd64-render-backend-control-v0-1');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const [spec, baseSpec] = await Promise.all([readB41D3Spec(), readB41Spec()]);
const analysis = analyzeB41D3Evidence(result, spec, baseSpec);
async function fileInfo(path) {
  try { const bytes = await readFile(path); return { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }
  catch { return { bytes: 0, sha256: null }; }
}
async function pngInfo(path) {
  try { const bytes = await readFile(path); return { valid: bytes.length >= 24 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR', dimensions: bytes.length >= 24 ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') }; }
  catch { return { valid: false, dimensions: null, bytes: 0, sha256: null }; }
}
async function milestones(path) {
  try { return (await readFile(path, 'utf8')).split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)); }
  catch { return []; }
}
const observed = [];
for (const control of result.controls) {
  const controlRoot = resolve(root, control.id);
  observed.push({ id: control.id, milestones: await milestones(resolve(controlRoot, 'milestones.jsonl')), artifacts: { blend: await fileInfo(resolve(controlRoot, 'canary.blend')), png: await pngInfo(resolve(controlRoot, 'canary.png')) } });
}
const observationsMatch = observed.every(item => { const recorded = result.controls.find(control => control.id === item.id); return JSON.stringify(item.milestones) === JSON.stringify(recorded.milestones) && JSON.stringify(item.artifacts) === JSON.stringify(recorded.artifacts); });
const toolHashes = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => [key, await sha256File(resolve(repositoryRoot, item.uri))])));
const toolsMatch = Object.entries(toolHashes).every(([key, digest]) => digest === result.tools[key].sha256);
const classificationMatch = classifyB41D3(result.controls) === result.classification;
const audit = { schemaVersion: 'bfs.linuxAmd64RenderBackendControlIndependentAudit.v0.1', experimentId: 'B41-D3', analysis, toolHashes, toolsMatch, observed, observationsMatch, classificationMatch, passed: analysis.passed && toolsMatch && observationsMatch && classificationMatch };
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B41_D3_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} tools=${toolsMatch ? 'MATCH' : 'MISMATCH'} observations=${observationsMatch ? 'MATCH' : 'MISMATCH'} classification=${classificationMatch ? 'MATCH' : 'MISMATCH'}\n`);
if (!audit.passed) process.exitCode = 1;
