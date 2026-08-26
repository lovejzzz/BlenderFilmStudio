import { appendFile, copyFile, link, mkdir, readFile, readdir, realpath, rm, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/dither-isolation-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const isolationSpecPath = resolve(repositoryRoot, 'specs/dither-isolation-spec.v0.1.json');
const reviewSpecPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const renderer = resolve(repositoryRoot, 'blender/render_review_sequence.py');
const comparator = resolve(repositoryRoot, 'blender/compare_review_sequences.py');
const configurator = resolve(repositoryRoot, 'blender/configure_dither_isolation.py');
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
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

async function names(dir) { return (await readdir(dir)).filter(name => name.endsWith('.png')).sort(); }
async function makeManifest(report, isolationSpec, runId) {
  const body = { documentType: 'BFS_DITHER_ZERO_SEQUENCE', version: '0.1.0', runId, ditherIntensity: 0, frameCount: report.frameCount, frameStart: 1, frameEnd: 144, resolution: [960, 540], isolationSpecSha256: await sha256File(isolationSpecPath), frames: report.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })) };
  return { ...body, sequenceHash: sha256Canonical(body) };
}

async function validateRun({ dir, manifestPath, interventionPath, label, expectedConfiguratorSha, expectedAfter = 0, expectedBefore = 1 }) {
  if (await sha256File(configurator) !== expectedConfiguratorSha) return 'CONFIGURATOR_SHA';
  const intervention = JSON.parse(await readFile(interventionPath, 'utf8'));
  if (intervention.before !== expectedBefore) return 'STARTING_DITHER';
  if (intervention.requested !== expectedAfter || intervention.after !== expectedAfter || expectedAfter !== 0) return 'INTERVENTION_VALUE';
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const body = structuredClone(manifest); delete body.sequenceHash;
  if (sha256Canonical(body) !== manifest.sequenceHash) return `${label}_MANIFEST_SELF_HASH`;
  const expectedNames = manifest.frames.map(frame => frame.name), observed = await names(dir);
  if (expectedNames.some(name => !observed.includes(name))) return `${label}_MISSING_FRAME`;
  if (observed.some(name => !expectedNames.includes(name))) return `${label}_EXTRA_FRAME`;
  for (const frame of manifest.frames) if (await sha256File(resolve(dir, frame.name)) !== frame.sha256) return `${label}_FRAME_SHA`;
  return 'OK';
}

async function cloneFrames(source, target) { await mkdir(target, { recursive: true }); for (const name of await names(source)) await link(resolve(source, name), resolve(target, name)); }

await rm(evidenceRoot, { recursive: true, force: true }); await rm(workRoot, { recursive: true, force: true }); await mkdir(evidenceRoot, { recursive: true });
const isolationSpec = JSON.parse(await readFile(isolationSpecPath, 'utf8'));
const reviewSpec = JSON.parse(await readFile(reviewSpecPath, 'utf8'));
for (const [path, expected, label] of [[reviewSpecPath, isolationSpec.frozenIdentity.reviewRenderSpecSha256, 'ReviewRenderSpec'], [renderer, isolationSpec.frozenIdentity.rendererSha256, 'renderer'], [comparator, isolationSpec.frozenIdentity.comparatorSha256, 'comparator'], [blender, isolationSpec.frozenIdentity.blenderSha256, 'Blender']]) if (await sha256File(path) !== expected) throw new Error(`${label} frozen SHA mismatch`);
const receiptPath = resolve(repositoryRoot, reviewSpec.source.receiptUri), receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri), ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
if (await sha256File(scenePath) !== isolationSpec.frozenIdentity.sceneBlendSha256 || await sha256File(ocioPath) !== isolationSpec.frozenIdentity.ocioSha256) throw new Error('Scene or OCIO frozen SHA mismatch');
const configuratorSha = await sha256File(configurator);
const runs = {};
for (const runId of ['D0-A', 'D0-B']) {
  const dir = resolve(workRoot, runId), renderReportPath = resolve(evidenceRoot, `${runId}.render.json`), interventionPath = resolve(evidenceRoot, `${runId}.intervention.json`), manifestPath = resolve(evidenceRoot, `${runId}.sequence.manifest.json`);
  await mkdir(dir, { recursive: true });
  await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--spec', reviewSpecPath, '--receipt', receiptPath, '--output-dir', dir, '--report', renderReportPath], { ...process.env, OCIO: ocioPath, BFS_DITHER_INTENSITY: '0.0', BFS_EXPECT_DITHER_INTENSITY: '1.0', BFS_DITHER_REPORT: interventionPath });
  const renderReport = JSON.parse(await readFile(renderReportPath, 'utf8')), manifest = await makeManifest(renderReport, isolationSpec, runId); await writeFile(manifestPath, serialize(manifest));
  const reason = await validateRun({ dir, manifestPath, interventionPath, label: runId, expectedConfiguratorSha: configuratorSha }); if (reason !== 'OK') throw new Error(`${runId} control failed: ${reason}`);
  runs[runId] = { dir, renderReportPath, interventionPath, manifestPath, manifest, renderReport };
}
if (await realpath(runs['D0-A'].dir) === await realpath(runs['D0-B'].dir)) throw new Error('D0 run directories alias');
const comparisonPath = resolve(evidenceRoot, 'D0.sequence.comparison.json');
await run(blender, ['--factory-startup', '--background', '--python-exit-code', '1', '--python', comparator, '--', '--a-dir', runs['D0-A'].dir, '--b-dir', runs['D0-B'].dir, '--frame-start', '1', '--frame-end', '144', '--output', comparisonPath]);
const comparison = JSON.parse(await readFile(comparisonPath, 'utf8'));

const attacks = [];
async function record(id, expected, observed) { attacks.push({ id, expectedReason: expected, observedReason: observed, pass: observed === expected }); }
await record('N_CONFIGURATOR_SHA', 'CONFIGURATOR_SHA', await validateRun({ dir: runs['D0-A'].dir, manifestPath: runs['D0-A'].manifestPath, interventionPath: runs['D0-A'].interventionPath, label: 'D0-A', expectedConfiguratorSha: '0'.repeat(64) }));
await record('N_INTERVENTION_VALUE', 'INTERVENTION_VALUE', await validateRun({ dir: runs['D0-A'].dir, manifestPath: runs['D0-A'].manifestPath, interventionPath: runs['D0-A'].interventionPath, label: 'D0-A', expectedConfiguratorSha: configuratorSha, expectedAfter: 0.5 }));
await record('N_STARTING_DITHER', 'STARTING_DITHER', await validateRun({ dir: runs['D0-A'].dir, manifestPath: runs['D0-A'].manifestPath, interventionPath: runs['D0-A'].interventionPath, label: 'D0-A', expectedConfiguratorSha: configuratorSha, expectedBefore: 0 }));
await record('N_ALIAS_RUNS', 'ALIAS_RUNS', await realpath(runs['D0-A'].dir) === await realpath(runs['D0-A'].dir) ? 'ALIAS_RUNS' : 'OK');
for (const [id, label, sourceRun, mutate] of [
  ['N_A_MISSING_FRAME', 'D0-A_MISSING_FRAME', 'D0-A', async dir => unlink(resolve(dir, 'frame-0072.png'))],
  ['N_B_MISSING_FRAME', 'D0-B_MISSING_FRAME', 'D0-B', async dir => unlink(resolve(dir, 'frame-0072.png'))],
  ['N_B_EXTRA_FRAME', 'D0-B_EXTRA_FRAME', 'D0-B', async dir => link(resolve(dir, 'frame-0001.png'), resolve(dir, 'frame-0145.png'))],
  ['N_B_FRAME_SHA', 'D0-B_FRAME_SHA', 'D0-B', async dir => { const target = resolve(dir, 'frame-0072.png'), temp = resolve(dir, 'copy.tmp'); await copyFile(target, temp); await unlink(target); await copyFile(temp, target); await appendFile(target, Buffer.from([0])); }],
]) {
  const dir = resolve(workRoot, 'attacks', id); await cloneFrames(runs[sourceRun].dir, dir); await mutate(dir);
  const observed = await validateRun({ dir, manifestPath: runs[sourceRun].manifestPath, interventionPath: runs[sourceRun].interventionPath, label: sourceRun, expectedConfiguratorSha: configuratorSha }); await record(id, label, observed);
}
const valid = attacks.length === 8 && attacks.every(item => item.pass);
const exact = comparison.decodedPixelExactFrames === 144 && comparison.maximumAbsoluteError === 0 && comparison.totalFailurePixels === 0;
const decision = !valid ? 'INVALID_EXPERIMENT' : exact ? 'CAUSAL_SUPPORT_DITHER' : 'DITHER_NOT_SUFFICIENT';
const result = { documentType: 'BFS_B16_DITHER_ISOLATION_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(), decision, validExperiment: valid, exactDecodedPixels: exact, intervention: { before: 1, after: 0, configuratorSha256: configuratorSha }, baseline: isolationSpec.baseline, ditherZero: { aSequenceHash: runs['D0-A'].manifest.sequenceHash, bSequenceHash: runs['D0-B'].manifest.sequenceHash, containerExactFrames: comparison.containerExactFrames, decodedPixelExactFrames: comparison.decodedPixelExactFrames, maximumAbsoluteError: comparison.maximumAbsoluteError, totalFailurePixels: comparison.totalFailurePixels, aRenderSeconds: runs['D0-A'].renderReport.totalRenderSeconds, bRenderSeconds: runs['D0-B'].renderReport.totalRenderSeconds }, identities: isolationSpec.frozenIdentity, attacks, artifacts: { comparison: repoUri(comparisonPath), d0aManifest: repoUri(runs['D0-A'].manifestPath), d0bManifest: repoUri(runs['D0-B'].manifestPath) }, nonClaims: isolationSpec.explicitNonClaims };
await writeFile(resolve(root, 'results.json'), serialize(result));
process.stdout.write(`BFS_B16_DITHER_ISOLATION ${decision} bytes=${comparison.containerExactFrames}/144 pixels=${comparison.decodedPixelExactFrames}/144 max=${comparison.maximumAbsoluteError} attacks=${attacks.filter(item => item.pass).length}/8\n`);
if (!valid) process.exitCode = 1;
