import { spawnSync } from 'node:child_process';
import { readFile, stat, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson, repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB45Evidence, hashB45Evidence, readB45Spec, runB45Attacks } from './lib/b45-worker-pixel-promotion.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const outputRoot = resolve(repositoryRoot, 'experiments/codex-worker-pixel-promotion-v0-1');
const result = JSON.parse(await readFile(resolve(outputRoot, 'results.json'), 'utf8'));
const spec = await readB45Spec();

async function observeFile(uri, expectedSha256) {
  const observedSha256 = await sha256File(resolve(repositoryRoot, uri)).catch(() => null);
  return { uri, expectedSha256, observedSha256, match: observedSha256 === expectedSha256 };
}

async function fileInfo(path) {
  try { return { uri: path.slice(repositoryRoot.length + 1), bytes: (await stat(path)).size, sha256: await sha256File(path) }; }
  catch { return { uri: path.slice(repositoryRoot.length + 1), bytes: 0, sha256: null }; }
}

async function pngInfo(path) {
  const info = await fileInfo(path);
  if (!info.sha256) return { ...info, valid: false, dimensions: null };
  const bytes = await readFile(path);
  const valid = bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) && bytes.subarray(12, 16).toString('ascii') === 'IHDR';
  return { ...info, valid, dimensions: valid ? [bytes.readUInt32BE(16), bytes.readUInt32BE(20)] : null };
}

function analyzeExr(path) {
  const executed = spawnSync(spec.hostPixelDecoder.pythonExecutable, [resolve(repositoryRoot, 'scripts/analyze-b45-worker-pixels.py'), '--input', path, '--expected-width', String(spec.renderControl.width), '--expected-height', String(spec.renderControl.height), '--output', '-'], { cwd: repositoryRoot, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024, env: { ...process.env, OPENCV_IO_ENABLE_OPENEXR: '1' } });
  if (executed.status !== 0) throw new Error(`B45 audit decoder failed: ${executed.stderr}`);
  return JSON.parse(executed.stdout);
}

const parentObservations = [];
for (const parent of Object.values(spec.parents)) parentObservations.push(await observeFile(parent.resultUri, parent.resultSha256), await observeFile(parent.auditUri, parent.auditSha256));
const parentsMatch = parentObservations.every(item => item.match) && canonicalJson(parentObservations) === canonicalJson(result.parentObservations);

const toolObservations = Object.fromEntries(await Promise.all(Object.entries(result.tools).map(async ([key, item]) => {
  const observedSha256 = await sha256File(resolve(repositoryRoot, item.uri)).catch(() => null);
  return [key, { uri: item.uri, expectedSha256: item.sha256, observedSha256, match: observedSha256 === item.sha256 }];
})));
const toolsMatch = Object.values(toolObservations).every(item => item.match);
const inputObservations = await Promise.all(result.inputObservations.map(item => observeFile(item.uri, item.expectedSha256)));
const inputsMatch = inputObservations.every(item => item.match) && canonicalJson(inputObservations) === canonicalJson(result.inputObservations);

const runObservations = [];
for (const shot of result.shots) for (const run of shot.runs) {
  const root = resolve(outputRoot, 'runs', run.id);
  const exrPath = resolve(root, 'frame.exr');
  const report = JSON.parse(await readFile(resolve(root, 'render.report.json'), 'utf8'));
  const decoded = analyzeExr(exrPath);
  const milestones = (await readFile(resolve(root, 'milestones.jsonl'), 'utf8')).split('\n').filter(Boolean).map(line => JSON.parse(line));
  const artifacts = {
    exr: await fileInfo(exrPath), png: await pngInfo(resolve(root, 'frame.png')),
    report: await fileInfo(resolve(root, 'render.report.json')), pixelAnalysis: await fileInfo(resolve(root, 'pixel-analysis.json')),
  };
  const match = canonicalJson(report) === canonicalJson(run.report) && canonicalJson(decoded) === canonicalJson(run.decoded)
    && canonicalJson(milestones) === canonicalJson(run.milestones) && canonicalJson(artifacts) === canonicalJson(run.artifacts)
    && await sha256File(resolve(repositoryRoot, run.source.uri)) === run.source.sha256;
  runObservations.push({ id: run.id, report, decoded, milestones, artifacts, match });
}
const outputsMatch = runObservations.length === 4 && runObservations.every(item => item.match);
const pairObservations = result.shots.map(shot => {
  const [a, b] = shot.runs;
  return { id: shot.id, canonicalPixelSha256A: a.decoded.canonicalPixelSha256, canonicalPixelSha256B: b.decoded.canonicalPixelSha256, pixelExact: a.decoded.canonicalPixelSha256 === b.decoded.canonicalPixelSha256, exrContainerByteExact: a.artifacts.exr.sha256 === b.artifacts.exr.sha256, pngContainerByteExact: a.artifacts.png.sha256 === b.artifacts.png.sha256 };
});
const pairsMatch = result.shots.every(shot => canonicalJson(pairObservations.find(item => item.id === shot.id)) === canonicalJson({ id: shot.id, ...shot.pairComparison })) && pairObservations.every(item => item.pixelExact);
const attacks = runB45Attacks(result, spec);
const attacksMatch = canonicalJson(attacks) === canonicalJson(result.attacks) && attacks.every(item => item.passed);
const analysis = analyzeB45Evidence(result, spec);
const audit = {
  schemaVersion: 'bfs.codexWorkerPixelPromotionIndependentAudit.v0.1', experimentId: 'B45', analysis,
  parentsMatch, parentObservations, toolsMatch, toolObservations, inputsMatch, inputObservations,
  outputsMatch, runObservations, pairsMatch, pairObservations, attacksMatch, attacks,
  evidenceSelfHashMatch: result.evidenceHash === hashB45Evidence(result),
};
audit.passed = analysis.passed && parentsMatch && toolsMatch && inputsMatch && outputsMatch && pairsMatch && attacksMatch && audit.evidenceSelfHashMatch;
await writeFile(resolve(outputRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B45_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} outputs=${outputsMatch ? 'MATCH' : 'MISMATCH'} pixels=${pairObservations.filter(item => item.pixelExact).length}/${pairObservations.length} attacks=${attacks.filter(item => item.passed).length}/${attacks.length}\n`);
if (!audit.passed) process.exitCode = 1;
