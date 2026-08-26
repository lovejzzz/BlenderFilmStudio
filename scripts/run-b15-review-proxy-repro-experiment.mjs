import { appendFile, copyFile, link, mkdir, readFile, readdir, realpath, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';
import { verifyReviewDailies } from './verify-review-dailies.mjs';

const root = resolve(repositoryRoot, 'experiments/review-proxy-repro-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const aDir = resolve(repositoryRoot, 'experiments/review-dailies-v0-1/work/formal-sequence');
const bDir = resolve(workRoot, 'run-b');
const b14Evidence = resolve(repositoryRoot, 'experiments/review-dailies-v0-1/evidence/dailies.evidence.json');
const aManifestPath = resolve(repositoryRoot, 'experiments/review-dailies-v0-1/evidence/sequence.manifest.json');
const renderer = resolve(repositoryRoot, 'blender/render_review_sequence.py');
const comparator = resolve(repositoryRoot, 'blender/compare_review_sequences.py');
const specPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const frozen = { aManifestSha: 'c86cc14940a4d82771c72052c5bac69c2ab4ebef709f76fe56cbf2d7af24122b', rendererSha: 'b969e267db7b73eb7b6f8ea17abf09b2e129b9fce2e706fec950c5bb5e5eda5c', specSha: '65db6ca29fc1deb6c6e6b3927152794ca14ca09cbcc921db912fc2b5aecd9553' };
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject); child.on('close', code => code === 0 ? resolvePromise(output) : reject(new Error(`${command} failed (${code})\n${output}`)));
  });
}

async function frameNames(dir) { return (await readdir(dir)).filter(name => name.endsWith('.png')).sort(); }
async function validateSequences({ firstDir = aDir, secondDir = bDir, aManifest = aManifestPath, bManifest, expectedA = frozen.aManifestSha, expectedRenderer = frozen.rendererSha }) {
  if (await realpath(firstDir) === await realpath(secondDir)) return 'ALIAS_RUNS';
  if (await sha256File(aManifest) !== expectedA) return 'A_MANIFEST_SHA';
  if (await sha256File(renderer) !== expectedRenderer) return 'RENDERER_SHA';
  const a = JSON.parse(await readFile(aManifest, 'utf8')), b = JSON.parse(await readFile(bManifest, 'utf8'));
  const expected = a.frames.map(frame => frame.name);
  for (const [label, dir, names] of [['A', firstDir, await frameNames(firstDir)], ['B', secondDir, await frameNames(secondDir)]]) {
    const missing = expected.filter(name => !names.includes(name)); if (missing.length) return `${label}_MISSING_FRAME`;
    const extra = names.filter(name => !expected.includes(name)); if (extra.length) return `${label}_EXTRA_FRAME`;
  }
  for (const frame of a.frames) if (await sha256File(resolve(firstDir, frame.name)) !== frame.sha256) return 'A_FRAME_SHA';
  const bBody = structuredClone(b); delete bBody.sequenceHash;
  if (sha256Canonical(bBody) !== b.sequenceHash) return 'B_MANIFEST_SELF_HASH';
  for (const frame of b.frames) if (await sha256File(resolve(secondDir, frame.name)) !== frame.sha256) return 'B_FRAME_SHA';
  return 'OK';
}

async function cloneFrames(source, target) { await mkdir(target, { recursive: true }); for (const name of await frameNames(source)) await link(resolve(source, name), resolve(target, name)); }

await rm(evidenceRoot, { recursive: true, force: true }); await rm(workRoot, { recursive: true, force: true }); await mkdir(evidenceRoot, { recursive: true }); await mkdir(bDir, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
if (await sha256File(specPath) !== frozen.specSha) throw new Error('Frozen ReviewRenderSpec SHA changed');
const aVerification = await verifyReviewDailies(b14Evidence, { sequenceDir: aDir });
if (!aVerification.valid) throw new Error(`Run A/B14 verification failed: ${aVerification.reason}`);
if (await sha256File(aManifestPath) !== frozen.aManifestSha || await sha256File(renderer) !== frozen.rendererSha) throw new Error('Frozen run A or renderer identity changed');
const receiptPath = resolve(repositoryRoot, spec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const bReportWork = resolve(workRoot, 'run-b.render.json');
await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', renderer, '--', '--spec', specPath, '--receipt', receiptPath, '--output-dir', bDir, '--report', bReportWork], { ...process.env, OCIO: ocioPath });
const bReport = JSON.parse(await readFile(bReportWork, 'utf8'));
const bBody = { documentType: 'BFS_REVIEW_SEQUENCE_MANIFEST', version: '0.1.0', classification: 'REVIEW_PROXY_NOT_MASTER', specSha256: frozen.specSha, receiptHash: spec.source.receiptHash, planHash: spec.source.planHash, structureHash: spec.source.structureHash, frameStart: 1, frameEnd: 144, frameCount: bReport.frameCount, resolution: [spec.proxy.width, spec.proxy.height], format: spec.proxy.imageFormat, frames: bReport.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })) };
const bManifest = { ...bBody, sequenceHash: sha256Canonical(bBody) };
const bManifestPath = resolve(evidenceRoot, 'run-b.sequence.manifest.json'); await writeFile(bManifestPath, serialize(bManifest));
const controlReason = await validateSequences({ bManifest: bManifestPath });
if (controlReason !== 'OK') throw new Error(`B15 control failed: ${controlReason}`);
const comparisonPath = resolve(evidenceRoot, 'sequence.comparison.json');
await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', aDir, '--b-dir', bDir, '--frame-start', '1', '--frame-end', '144', '--output', comparisonPath]);
const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));

const attacksRoot = resolve(workRoot, 'attacks'); await mkdir(attacksRoot, { recursive: true });
const attacks = [];
async function record(id, expected, options) { const observed = await validateSequences({ bManifest: bManifestPath, ...options }); attacks.push({ id, expectedReason: expected, observedReason: observed, pass: observed === expected }); }
await record('N_A_MANIFEST_SHA', 'A_MANIFEST_SHA', { expectedA: '0'.repeat(64) });
await record('N_RENDERER_SHA', 'RENDERER_SHA', { expectedRenderer: '0'.repeat(64) });
{
  const dir = resolve(attacksRoot, 'a-missing'); await cloneFrames(aDir, dir); await unlink(resolve(dir, 'frame-0072.png')); await record('N_A_MISSING_FRAME', 'A_MISSING_FRAME', { firstDir: dir });
}
{
  const dir = resolve(attacksRoot, 'b-missing'); await cloneFrames(bDir, dir); await unlink(resolve(dir, 'frame-0072.png')); await record('N_B_MISSING_FRAME', 'B_MISSING_FRAME', { secondDir: dir });
}
{
  const dir = resolve(attacksRoot, 'b-extra'); await cloneFrames(bDir, dir); await link(resolve(dir, 'frame-0001.png'), resolve(dir, 'frame-0145.png')); await record('N_B_EXTRA_FRAME', 'B_EXTRA_FRAME', { secondDir: dir });
}
{
  const dir = resolve(attacksRoot, 'a-sha'); await cloneFrames(aDir, dir); const target = resolve(dir, 'frame-0072.png'), copy = resolve(dir, 'copy.tmp'); await copyFile(target, copy); await unlink(target); await copyFile(copy, target); await appendFile(target, Buffer.from([0])); await record('N_A_FRAME_SHA', 'A_FRAME_SHA', { firstDir: dir });
}
{
  const dir = resolve(attacksRoot, 'b-sha'); await cloneFrames(bDir, dir); const target = resolve(dir, 'frame-0072.png'), copy = resolve(dir, 'copy.tmp'); await copyFile(target, copy); await unlink(target); await copyFile(copy, target); await appendFile(target, Buffer.from([0])); await record('N_B_FRAME_SHA', 'B_FRAME_SHA', { secondDir: dir });
}
await record('N_ALIAS_RUNS', 'ALIAS_RUNS', { secondDir: aDir });

const classification = comparison.decodedPixelExactFrames === 144 ? (comparison.containerExactFrames === 144 ? 'FORMAL EXACT TRUE' : 'FORMAL PIXEL TRUE / CONTAINER FALSE') : 'FORMAL EXACT FALSIFIED';
const result = { documentType: 'BFS_B15_REVIEW_PROXY_REPRO_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(), classification, validExperiment: controlReason === 'OK' && attacks.length === 8 && attacks.every(item => item.pass), exactPixelHypothesis: comparison.decodedPixelExactFrames === 144, exactContainerHypothesis: comparison.containerExactFrames === 144, identities: { b14EvidenceHash: aVerification.evidenceHash, aSequenceHash: JSON.parse(await readFile(aManifestPath, 'utf8')).sequenceHash, bSequenceHash: bManifest.sequenceHash, rendererSha256: frozen.rendererSha, specSha256: frozen.specSha, blenderSha256: spec.runtime.blender.binarySha256, ocioSha256: spec.runtime.ocioConfigSha256 }, comparison: { decoder: comparison.decoder, frameCount: comparison.frameCount, containerExactFrames: comparison.containerExactFrames, decodedPixelExactFrames: comparison.decodedPixelExactFrames, maximumAbsoluteError: comparison.maximumAbsoluteError, totalFailurePixels: comparison.totalFailurePixels, worstFrame: comparison.worstFrame.frame }, attacks, artifacts: { bManifest: repoUri(bManifestPath), comparison: repoUri(comparisonPath) }, nonClaims: ['No perceptual tolerance is selected.', 'Eevee proxy behavior is not a Cycles master result.', 'Same-machine behavior is not cross-device reproducibility.', 'Pixel difference does not by itself prove a visible defect.'] };
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B15_PROXY_REPRO ${result.validExperiment ? classification : 'INVALID EXPERIMENT'} bytes=${comparison.containerExactFrames}/144 pixels=${comparison.decodedPixelExactFrames}/144 max=${comparison.maximumAbsoluteError} attacks=${attacks.filter(item => item.pass).length}/8\n`);
if (!result.validExperiment) process.exitCode = 1;
