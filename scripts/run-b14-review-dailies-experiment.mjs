import { appendFile, copyFile, link, mkdir, readFile, readdir, rm, stat, unlink, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { basename, relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';
import { verifyCompileReceipt } from './verify-compile-receipt.mjs';
import { probeVideo, verifyReviewDailies } from './verify-review-dailies.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/review-dailies-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const sequenceRoot = resolve(workRoot, 'formal-sequence');
const publicRoot = resolve(repositoryRoot, 'public/review-dailies-v0-1');
const specPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const rendererPath = resolve(repositoryRoot, 'blender/render_review_sequence.py');
const runnerPath = resolve(repositoryRoot, 'scripts/run-b14-review-dailies-experiment.mjs');
const verifierPath = resolve(repositoryRoot, 'scripts/verify-review-dailies.mjs');
const receiptVerifierPath = resolve(repositoryRoot, 'scripts/verify-compile-receipt.mjs');
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const ffmpeg = resolve(process.env.FFMPEG_BIN || '/opt/homebrew/bin/ffmpeg');
const ffprobe = resolve(process.env.FFPROBE_BIN || '/opt/homebrew/bin/ffprobe');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');
const redactRepositoryPath = value => typeof value === 'string' ? value.split(repositoryRoot).join('<REPO>') : value;

function run(command, args, environment = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env: environment, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; process.stdout.write(chunk); });
    child.stderr.on('data', chunk => { output += chunk; process.stderr.write(chunk); });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise(output) : reject(new Error(`Process failed (${code}): ${command}\n${output}`)));
  });
}

async function identity(path) {
  const metadata = await stat(path);
  return { uri: repoUri(path), sha256: await sha256File(path), bytes: metadata.size };
}

async function prerequisiteCheck(spec, receiptPath, scenePath) {
  const receiptFileSha = await sha256File(receiptPath);
  if (receiptFileSha !== spec.source.receiptFileSha256) throw new Error(`Preflight receipt file SHA mismatch: ${receiptFileSha}`);
  const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  if (receipt.receiptHash !== spec.source.receiptHash) throw new Error('Preflight receipt body hash mismatch');
  if (receipt.executionIdentityHash !== spec.source.executionIdentityHash) throw new Error('Preflight execution identity mismatch');
  if (receipt.executionIdentity.buildPlan.planHash !== spec.source.planHash) throw new Error('Preflight plan hash mismatch');
  if (receipt.run.sceneManifest.structureHash !== spec.source.structureHash) throw new Error('Preflight structure hash mismatch');
  if (await sha256File(scenePath) !== spec.source.sceneBlendSha256) throw new Error('Preflight scene blend SHA mismatch');
  const receiptVerification = await verifyCompileReceipt(receiptPath);
  if (!receiptVerification.valid) throw new Error(`Preflight B13 receipt verification failed: ${receiptVerification.reason}`);
  for (const [name, path] of [['blender', blender], ['ffmpeg', ffmpeg], ['ffprobe', ffprobe]]) {
    const observed = await sha256File(path);
    if (observed !== spec.runtime[name].binarySha256) throw new Error(`Preflight ${name} binary SHA mismatch: ${observed}`);
  }
  return receiptVerification;
}

async function writeSelfHashedEvidence(evidencePath, evidence) {
  const next = structuredClone(evidence);
  delete next.evidenceHash;
  next.evidenceHash = sha256Canonical(next);
  await writeFile(evidencePath, serialize(next));
  return next;
}

async function cloneFrames(target) {
  await mkdir(target, { recursive: true });
  for (const name of await readdir(sequenceRoot)) {
    if (name.endsWith('.png')) await link(resolve(sequenceRoot, name), resolve(target, name));
  }
}

async function writeAttackEvidence(id, baseEvidence, mutateEvidence) {
  const directory = resolve(workRoot, 'attacks', id);
  await mkdir(directory, { recursive: true });
  const evidence = structuredClone(baseEvidence);
  await mutateEvidence(evidence, directory);
  const path = resolve(directory, 'evidence.json');
  return { evidence: await writeSelfHashedEvidence(path, evidence), path, directory };
}

async function specAttack(id, expectedReason, baseEvidence, baseSpec, mutateSpec) {
  const directory = resolve(workRoot, 'attacks', id);
  await mkdir(directory, { recursive: true });
  const spec = structuredClone(baseSpec);
  mutateSpec(spec);
  const attackSpec = resolve(directory, 'review-render-spec.json');
  await writeFile(attackSpec, serialize(spec));
  const evidence = structuredClone(baseEvidence);
  evidence.spec = await identity(attackSpec);
  const evidencePath = resolve(directory, 'evidence.json');
  await writeSelfHashedEvidence(evidencePath, evidence);
  const verification = await verifyReviewDailies(evidencePath, { sequenceDir: sequenceRoot });
  return { id, expectedReason, observedReason: verification.reason, rejected: !verification.valid, pass: !verification.valid && verification.reason === expectedReason };
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await rm(publicRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true });
await mkdir(sequenceRoot, { recursive: true });
await mkdir(publicRoot, { recursive: true });

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, spec.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const receiptVerification = await prerequisiteCheck(spec, receiptPath, scenePath);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const renderReportWork = resolve(workRoot, 'render.report.json');
const renderLog = await run(blender, [
  '--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', rendererPath, '--',
  '--spec', specPath, '--receipt', receiptPath, '--output-dir', sequenceRoot, '--report', renderReportWork,
], { ...process.env, OCIO: ocioPath });

const renderReportPath = resolve(evidenceRoot, 'render.report.json');
await copyFile(renderReportWork, renderReportPath);
const renderReport = JSON.parse(await readFile(renderReportPath, 'utf8'));
const sequenceBody = {
  documentType: 'BFS_REVIEW_SEQUENCE_MANIFEST', version: '0.1.0', classification: 'REVIEW_PROXY_NOT_MASTER',
  specSha256: await sha256File(specPath), receiptHash: spec.source.receiptHash,
  planHash: spec.source.planHash, structureHash: spec.source.structureHash,
  frameStart: spec.timeline.frameStart, frameEnd: spec.timeline.frameEnd, frameCount: renderReport.frameCount,
  resolution: [spec.proxy.width, spec.proxy.height], format: spec.proxy.imageFormat,
  frames: renderReport.frames.map(({ frame, name, sha256, bytes }) => ({ frame, name, sha256, bytes })),
};
const sequenceManifest = { ...sequenceBody, sequenceHash: sha256Canonical(sequenceBody) };
const sequenceManifestPath = resolve(evidenceRoot, 'sequence.manifest.json');
await writeFile(sequenceManifestPath, serialize(sequenceManifest));

const videoPath = resolve(publicRoot, 'B02-review-proxy-v0.1.mp4');
const videoArgs = [
  '-y', '-hide_banner', '-loglevel', 'error', '-fflags', '+bitexact',
  '-framerate', String(spec.timeline.fpsNumerator), '-start_number', String(spec.timeline.frameStart),
  '-i', resolve(sequenceRoot, 'frame-%04d.png'), '-frames:v', String(spec.timeline.expectedFrameCount),
  '-map_metadata', '-1', '-an', '-c:v', spec.video.codec, '-preset', spec.video.preset,
  '-crf', String(spec.video.constantRateFactor), '-pix_fmt', spec.video.pixelFormat,
  '-flags:v', '+bitexact', '-movflags', '+faststart', videoPath,
];
await run(ffmpeg, videoArgs);
const probe = await probeVideo(videoPath, ffprobe);

const witnessFrames = [1, 72, 144];
const witnesses = [];
for (const frame of witnessFrames) {
  const source = resolve(sequenceRoot, `frame-${String(frame).padStart(4, '0')}.png`);
  const target = resolve(publicRoot, `B02-frame-${String(frame).padStart(4, '0')}.png`);
  await copyFile(source, target);
  witnesses.push({ frame, ...await identity(target) });
}

const videoMetadata = await stat(videoPath);
const evidencePath = resolve(evidenceRoot, 'dailies.evidence.json');
const evidence = await writeSelfHashedEvidence(evidencePath, {
  documentType: 'BFS_REVIEW_DAILIES_EVIDENCE', version: '0.1.0', createdAtUtc: new Date().toISOString(),
  classification: 'REVIEW_PROXY_NOT_MASTER',
  spec: await identity(specPath),
  source: {
    receiptUri: spec.source.receiptUri, receiptFileSha256: spec.source.receiptFileSha256,
    receiptHash: spec.source.receiptHash, executionIdentityHash: spec.source.executionIdentityHash,
    planHash: spec.source.planHash, structureHash: spec.source.structureHash, sceneBlendSha256: spec.source.sceneBlendSha256,
    receiptVerification,
  },
  tools: { renderer: await identity(rendererPath), runner: await identity(runnerPath), verifier: await identity(verifierPath), receiptVerifier: await identity(receiptVerifierPath) },
  runtime: {
    blender: { sha256: await sha256File(blender), version: spec.runtime.blender.version, buildHash: spec.runtime.blender.buildHash },
    ffmpeg: { sha256: await sha256File(ffmpeg), version: spec.runtime.ffmpeg.version },
    ffprobe: { sha256: await sha256File(ffprobe), version: spec.runtime.ffprobe.version },
    ocioSha256: await sha256File(ocioPath),
  },
  render: {
    report: await identity(renderReportPath), totalRenderSeconds: renderReport.totalRenderSeconds,
    totalFrameBytes: renderReport.totalFrameBytes, frameCount: renderReport.frameCount,
    logTail: renderLog.trim().split('\n').slice(-8).map(redactRepositoryPath),
  },
  sequence: { manifest: await identity(sequenceManifestPath), sequenceHash: sequenceManifest.sequenceHash, frameDirectoryUri: repoUri(sequenceRoot), retainedPublicly: false },
  video: {
    uri: repoUri(videoPath), sha256: await sha256File(videoPath), bytes: videoMetadata.size,
    command: [basename(ffmpeg), ...videoArgs.slice(0, -1).map(redactRepositoryPath), `<REPO>/${repoUri(videoPath)}`], probe,
  },
  witnesses,
  claims: { completeLocalPngSequence: true, playableReviewVideo: true, sourceReceiptBound: true, reviewProxy: true, master: false, humanReviewPassed: false },
});

const positiveVerification = await verifyReviewDailies(evidencePath, { sequenceDir: sequenceRoot });
if (!positiveVerification.valid) throw new Error(`Formal evidence verification failed: ${positiveVerification.reason} ${JSON.stringify(positiveVerification.observed)}`);

const zeros = '0'.repeat(64);
const negativeTests = [];
negativeTests.push(await specAttack('N_RECEIPT_FILE_SHA', 'RECEIPT_FILE_SHA', evidence, spec, value => { value.source.receiptFileSha256 = zeros; }));
negativeTests.push(await specAttack('N_RECEIPT_BODY_HASH', 'RECEIPT_BODY_HASH', evidence, spec, value => { value.source.receiptHash = zeros; }));
negativeTests.push(await specAttack('N_BLEND_SHA', 'SOURCE_BLEND_SHA', evidence, spec, value => { value.source.sceneBlendSha256 = zeros; }));
negativeTests.push(await specAttack('N_PLAN_MARKER', 'PLAN_MARKER_BINDING', evidence, spec, value => { value.source.planHash = zeros; }));

for (const [id, expectedReason, mutate] of [
  ['N_MISSING_FRAME', 'MISSING_FRAME', async (_copy, directory) => { await unlink(resolve(directory, 'frames/frame-0072.png')); }],
  ['N_EXTRA_FRAME', 'EXTRA_FRAME', async (_copy, directory) => { await link(resolve(directory, 'frames/frame-0001.png'), resolve(directory, 'frames/frame-0145.png')); }],
  ['N_FRAME_SHA', 'FRAME_SHA', async (_copy, directory) => {
    const target = resolve(directory, 'frames/frame-0072.png');
    const detached = resolve(directory, 'frame-0072.detached.png');
    await copyFile(target, detached); await unlink(target); await copyFile(detached, target); await appendFile(target, Buffer.from([0]));
  }],
]) {
  const attack = await writeAttackEvidence(id, evidence, async (_copy, directory) => { await cloneFrames(resolve(directory, 'frames')); await mutate(_copy, directory); });
  const verification = await verifyReviewDailies(attack.path, { sequenceDir: resolve(attack.directory, 'frames') });
  negativeTests.push({ id, expectedReason, observedReason: verification.reason, rejected: !verification.valid, pass: !verification.valid && verification.reason === expectedReason });
}

{
  const id = 'N_SEQUENCE_SELF_HASH';
  const attack = await writeAttackEvidence(id, evidence, async (copy, directory) => {
    const manifest = structuredClone(sequenceManifest);
    manifest.frameCount = 143;
    const path = resolve(directory, 'sequence.manifest.json');
    await writeFile(path, serialize(manifest));
    copy.sequence.manifest = await identity(path);
  });
  const verification = await verifyReviewDailies(attack.path, { sequenceDir: sequenceRoot });
  negativeTests.push({ id, expectedReason: 'SEQUENCE_SELF_HASH', observedReason: verification.reason, rejected: !verification.valid, pass: !verification.valid && verification.reason === 'SEQUENCE_SELF_HASH' });
}

{
  const id = 'N_VIDEO_SHA';
  const attack = await writeAttackEvidence(id, evidence, async (copy, directory) => {
    const target = resolve(directory, 'review.mp4');
    await copyFile(videoPath, target); await appendFile(target, Buffer.from([0]));
    copy.video.uri = repoUri(target);
  });
  const verification = await verifyReviewDailies(attack.path, { sequenceDir: sequenceRoot });
  negativeTests.push({ id, expectedReason: 'VIDEO_SHA', observedReason: verification.reason, rejected: !verification.valid, pass: !verification.valid && verification.reason === 'VIDEO_SHA' });
}

{
  const id = 'N_VIDEO_PROBE';
  const attack = await writeAttackEvidence(id, evidence, async copy => { copy.video.probe.width = 961; });
  const verification = await verifyReviewDailies(attack.path, { sequenceDir: sequenceRoot });
  negativeTests.push({ id, expectedReason: 'VIDEO_PROBE_BINDING', observedReason: verification.reason, rejected: !verification.valid, pass: !verification.valid && verification.reason === 'VIDEO_PROBE_BINDING' });
}

const positiveChecks = {
  sourceReceiptVerified: receiptVerification.valid,
  evidenceVerifierPassed: positiveVerification.valid,
  cameraAndTimelineInvariant: renderReport.cameraAndTimelineInvariant,
  exactFrameCount: renderReport.frameCount === spec.timeline.expectedFrameCount,
  exactFrameNames: sequenceManifest.frames.every((frame, index) => frame.name === `frame-${String(index + 1).padStart(4, '0')}.png`),
  sequenceSelfHashed: sequenceManifest.sequenceHash.length === 64,
  videoProfileExact: probe.codecName === 'h264' && probe.pixelFormat === spec.video.pixelFormat && probe.width === spec.proxy.width && probe.height === spec.proxy.height && probe.decodedFrames === spec.timeline.expectedFrameCount && probe.audioStreams === 0,
  witnessesPublished: witnesses.length === 3,
  explicitlyNotMaster: evidence.classification === 'REVIEW_PROXY_NOT_MASTER' && evidence.claims.master === false,
};
const result = {
  documentType: 'BFS_B14_REVIEW_DAILIES_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  classification: 'REVIEW_PROXY_NOT_MASTER', specSha256: await sha256File(specPath), evidenceHash: evidence.evidenceHash,
  source: evidence.source, runtime: evidence.runtime,
  metrics: {
    frameCount: renderReport.frameCount, totalRenderSeconds: renderReport.totalRenderSeconds,
    meanRenderSecondsPerFrame: Number((renderReport.totalRenderSeconds / renderReport.frameCount).toFixed(6)),
    totalPngBytes: renderReport.totalFrameBytes, videoBytes: videoMetadata.size, durationSeconds: probe.containerDurationSeconds,
  },
  sequenceHash: sequenceManifest.sequenceHash, videoSha256: evidence.video.sha256, videoProbe: probe,
  positiveChecks, positiveVerification, negativeTests, preRegisteredNegativeCount: 10,
  formalB14AutomationComplete: Object.values(positiveChecks).every(Boolean) && negativeTests.length === 10 && negativeTests.every(test => test.pass),
  humanReview: { status: 'PENDING', claim: 'Automation cannot determine cinematic quality or temporal perceptual stability.' },
  retention: { fullPngSequenceTracked: false, publicWitnessFrames: witnessFrames, publicReviewVideo: evidence.video.uri },
  nonClaims: spec.explicitNonClaims,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(result));
process.stdout.write(`BFS_B14_REVIEW_DAILIES ${result.formalB14AutomationComplete ? 'FORMAL_AUTOMATION_TRUE' : 'FAILED'} ${negativeTests.filter(test => test.pass).length}/${negativeTests.length} attacks; HUMAN_${result.humanReview.status}\n`);
if (!result.formalB14AutomationComplete) process.exitCode = 1;
