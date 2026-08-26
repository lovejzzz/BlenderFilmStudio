import { execFile } from 'node:child_process';
import { access, readFile, readdir, realpath, stat, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { canonicalJson, sha256Bytes, sha256Canonical, sha256File } from './lib/receipt-format.mjs';
import { verifyCompileReceipt } from './verify-compile-receipt.mjs';

const repositoryRealRoot = await realpath(repositoryRoot);

async function repositoryFile(uri, label) {
  if (typeof uri !== 'string' || !uri) throw new Error(`${label} URI is missing`);
  const absolute = resolve(repositoryRoot, uri);
  const fromRoot = relative(repositoryRoot, absolute);
  if (fromRoot === '' || fromRoot === '..' || fromRoot.startsWith(`..${sep}`)) throw new Error(`${label} URI resolves outside repository`);
  const actual = await realpath(absolute).catch(() => { throw new Error(`${label} file is missing`); });
  const actualFromRoot = relative(repositoryRealRoot, actual);
  if (actualFromRoot === '' || actualFromRoot === '..' || actualFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} real path escapes repository`);
  if (actual !== absolute) throw new Error(`${label} URI traverses symbolic links`);
  return absolute;
}

function failure(reason, observed = null, expected = null, checks = []) {
  return { documentType: 'BFS_REVIEW_DAILIES_VERIFICATION', version: '0.1.0', valid: false, reason, observed, expected, checks };
}

function exec(command, args) {
  return new Promise((resolvePromise, reject) => {
    execFile(command, args, { cwd: repositoryRoot, maxBuffer: 4 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) reject(new Error(`${stdout}${stderr}${error.message}`));
      else resolvePromise(stdout);
    });
  });
}

async function findExecutable(envName, fallback) {
  const candidate = process.env[envName] || fallback;
  await access(candidate, constants.X_OK);
  return realpath(candidate);
}

export async function probeVideo(videoPath, ffprobePath = null) {
  const executable = ffprobePath || await findExecutable('FFPROBE_BIN', '/opt/homebrew/bin/ffprobe');
  const output = await exec(executable, [
    '-v', 'error', '-count_frames',
    '-show_entries', 'stream=index,codec_type,codec_name,pix_fmt,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,duration:format=duration',
    '-of', 'json', videoPath,
  ]);
  const parsed = JSON.parse(output);
  const video = parsed.streams.find(stream => stream.codec_type === 'video') || null;
  const audioStreams = parsed.streams.filter(stream => stream.codec_type === 'audio').length;
  return {
    codecName: video?.codec_name ?? null,
    pixelFormat: video?.pix_fmt ?? null,
    width: video?.width ?? null,
    height: video?.height ?? null,
    rFrameRate: video?.r_frame_rate ?? null,
    avgFrameRate: video?.avg_frame_rate ?? null,
    declaredFrames: Number(video?.nb_frames ?? 0),
    decodedFrames: Number(video?.nb_read_frames ?? 0),
    streamDurationSeconds: Number(video?.duration ?? 0),
    containerDurationSeconds: Number(parsed.format?.duration ?? 0),
    audioStreams,
  };
}

function pngDimensions(bytes) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (bytes.length < 24 || !bytes.subarray(0, 8).equals(signature) || bytes.toString('ascii', 12, 16) !== 'IHDR') throw new Error('not a PNG with IHDR');
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

async function checkIdentityFile(identity, reason, label, checks) {
  const path = await repositoryFile(identity.uri, label);
  const metadata = await stat(path);
  const observed = { sha256: await sha256File(path), bytes: metadata.size };
  if (observed.sha256 !== identity.sha256 || observed.bytes !== identity.bytes) return failure(reason, observed, { sha256: identity.sha256, bytes: identity.bytes }, checks);
  checks.push(reason);
  return { path };
}

export async function verifyReviewDailies(evidencePath, { sequenceDir = null } = {}) {
  const checks = [];
  try {
    const evidenceFile = await repositoryFile(relative(repositoryRoot, resolve(evidencePath)), 'Dailies evidence');
    const evidence = JSON.parse(await readFile(evidenceFile, 'utf8'));
    if (evidence.documentType !== 'BFS_REVIEW_DAILIES_EVIDENCE' || evidence.version !== '0.1.0') return failure('EVIDENCE_TYPE', `${evidence.documentType}@${evidence.version}`, 'BFS_REVIEW_DAILIES_EVIDENCE@0.1.0', checks);
    const evidenceBody = structuredClone(evidence);
    delete evidenceBody.evidenceHash;
    const computedEvidenceHash = sha256Canonical(evidenceBody);
    if (computedEvidenceHash !== evidence.evidenceHash) return failure('EVIDENCE_SELF_HASH', computedEvidenceHash, evidence.evidenceHash, checks);
    checks.push('EVIDENCE_SELF_HASH');

    const specIdentity = await checkIdentityFile(evidence.spec, 'SPEC_FILE_SHA', 'ReviewRenderSpec', checks);
    if (specIdentity.valid === false) return specIdentity;
    const spec = JSON.parse(await readFile(specIdentity.path, 'utf8'));
    if (spec.documentType !== 'BFS_REVIEW_RENDER_SPEC' || spec.specVersion !== '0.1.0' || spec.proxy?.classification !== 'REVIEW_PROXY_NOT_MASTER') return failure('SPEC_TYPE', spec.documentType, 'BFS_REVIEW_RENDER_SPEC@0.1.0 REVIEW_PROXY_NOT_MASTER', checks);

    const receiptPath = await repositoryFile(spec.source.receiptUri, 'Source receipt');
    const receiptFileSha = await sha256File(receiptPath);
    if (receiptFileSha !== spec.source.receiptFileSha256) return failure('RECEIPT_FILE_SHA', receiptFileSha, spec.source.receiptFileSha256, checks);
    const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
    if (receipt.receiptHash !== spec.source.receiptHash) return failure('RECEIPT_BODY_HASH', receipt.receiptHash, spec.source.receiptHash, checks);
    if (receipt.executionIdentityHash !== spec.source.executionIdentityHash) return failure('EXECUTION_IDENTITY_BINDING', receipt.executionIdentityHash, spec.source.executionIdentityHash, checks);
    if (receipt.run.sceneBlend.sha256 !== spec.source.sceneBlendSha256) return failure('SOURCE_BLEND_SHA', receipt.run.sceneBlend.sha256, spec.source.sceneBlendSha256, checks);
    if (receipt.executionIdentity.buildPlan.planHash !== spec.source.planHash) return failure('PLAN_MARKER_BINDING', receipt.executionIdentity.buildPlan.planHash, spec.source.planHash, checks);
    if (receipt.run.sceneManifest.structureHash !== spec.source.structureHash) return failure('STRUCTURE_MARKER_BINDING', receipt.run.sceneManifest.structureHash, spec.source.structureHash, checks);
    checks.push('SOURCE_SPEC_BINDINGS');
    const receiptVerification = await verifyCompileReceipt(receiptPath);
    if (!receiptVerification.valid) return failure('SOURCE_RECEIPT_VERIFICATION', receiptVerification.reason, 'OK', checks);
    checks.push('SOURCE_RECEIPT_VERIFICATION');

    const runtimePaths = {
      blender: await findExecutable('BLENDER_BIN', '/Applications/Blender.app/Contents/MacOS/Blender'),
      ffmpeg: await findExecutable('FFMPEG_BIN', '/opt/homebrew/bin/ffmpeg'),
      ffprobe: await findExecutable('FFPROBE_BIN', '/opt/homebrew/bin/ffprobe'),
    };
    for (const name of ['blender', 'ffmpeg', 'ffprobe']) {
      const observed = await sha256File(runtimePaths[name]);
      if (observed !== spec.runtime[name].binarySha256) return failure(`${name.toUpperCase()}_BINARY_SHA`, observed, spec.runtime[name].binarySha256, checks);
      checks.push(`${name.toUpperCase()}_BINARY_SHA`);
    }
    const ocioPath = await repositoryFile(receipt.executionIdentity.configuration.ocio.uri, 'OCIO config');
    const ocioSha = await sha256File(ocioPath);
    if (ocioSha !== spec.runtime.ocioConfigSha256) return failure('OCIO_SHA', ocioSha, spec.runtime.ocioConfigSha256, checks);
    checks.push('OCIO_SHA');

    for (const [field, reason, label] of [
      ['renderer', 'RENDERER_SHA', 'Sequence renderer'],
      ['runner', 'RUNNER_SHA', 'Dailies runner'],
      ['verifier', 'VERIFIER_SHA', 'Dailies verifier'],
    ]) {
      const result = await checkIdentityFile(evidence.tools[field], reason, label, checks);
      if (result.valid === false) return result;
    }

    const reportIdentity = await checkIdentityFile(evidence.render.report, 'RENDER_REPORT_SHA', 'Render report', checks);
    if (reportIdentity.valid === false) return reportIdentity;
    const renderReport = JSON.parse(await readFile(reportIdentity.path, 'utf8'));
    if (renderReport.classification !== 'REVIEW_PROXY_NOT_MASTER' || renderReport.source.planHash !== spec.source.planHash || renderReport.source.structureHash !== spec.source.structureHash || !renderReport.cameraAndTimelineInvariant) return failure('RENDER_REPORT_BINDING', renderReport.source, spec.source, checks);
    if (renderReport.frameCount !== spec.timeline.expectedFrameCount || renderReport.frames.length !== spec.timeline.expectedFrameCount) return failure('RENDER_FRAME_COUNT', renderReport.frameCount, spec.timeline.expectedFrameCount, checks);
    checks.push('RENDER_REPORT_BINDING');

    const sequenceIdentity = await checkIdentityFile(evidence.sequence.manifest, 'SEQUENCE_MANIFEST_SHA', 'Sequence manifest', checks);
    if (sequenceIdentity.valid === false) return sequenceIdentity;
    const sequence = JSON.parse(await readFile(sequenceIdentity.path, 'utf8'));
    const sequenceBody = structuredClone(sequence);
    delete sequenceBody.sequenceHash;
    const computedSequenceHash = sha256Canonical(sequenceBody);
    if (computedSequenceHash !== sequence.sequenceHash || sequence.sequenceHash !== evidence.sequence.sequenceHash) return failure('SEQUENCE_SELF_HASH', computedSequenceHash, sequence.sequenceHash, checks);
    if (sequence.frames.length !== spec.timeline.expectedFrameCount) return failure('SEQUENCE_FRAME_COUNT', sequence.frames.length, spec.timeline.expectedFrameCount, checks);
    checks.push('SEQUENCE_SELF_HASH');

    const frameRoot = sequenceDir ? resolve(sequenceDir) : resolve(repositoryRoot, evidence.sequence.frameDirectoryUri);
    const observedNames = (await readdir(frameRoot)).filter(name => name.toLowerCase().endsWith('.png')).sort();
    const expectedNames = Array.from({ length: spec.timeline.expectedFrameCount }, (_, index) => `frame-${String(index + spec.timeline.frameStart).padStart(4, '0')}.png`);
    const missing = expectedNames.filter(name => !observedNames.includes(name));
    const extra = observedNames.filter(name => !expectedNames.includes(name));
    if (missing.length) return failure('MISSING_FRAME', missing, [], checks);
    if (extra.length) return failure('EXTRA_FRAME', extra, [], checks);
    for (let index = 0; index < expectedNames.length; index += 1) {
      const expected = sequence.frames[index];
      if (expected.name !== expectedNames[index] || expected.frame !== index + spec.timeline.frameStart) return failure('FRAME_NAME_BINDING', expected, expectedNames[index], checks);
      const path = resolve(frameRoot, expected.name);
      const bytes = await readFile(path);
      const observedHash = sha256Bytes(bytes);
      if (observedHash !== expected.sha256) return failure('FRAME_SHA', { frame: expected.frame, sha256: observedHash }, { sha256: expected.sha256 }, checks);
      const dimensions = pngDimensions(bytes);
      if (dimensions.width !== spec.proxy.width || dimensions.height !== spec.proxy.height) return failure('FRAME_DIMENSIONS', dimensions, { width: spec.proxy.width, height: spec.proxy.height }, checks);
    }
    checks.push('FRAME_SEQUENCE_BYTES');

    const videoPath = await repositoryFile(evidence.video.uri, 'Review video');
    const videoMetadata = await stat(videoPath);
    const videoSha = await sha256File(videoPath);
    if (videoSha !== evidence.video.sha256 || videoMetadata.size !== evidence.video.bytes) return failure('VIDEO_SHA', { sha256: videoSha, bytes: videoMetadata.size }, { sha256: evidence.video.sha256, bytes: evidence.video.bytes }, checks);
    checks.push('VIDEO_SHA');
    const observedProbe = await probeVideo(videoPath, runtimePaths.ffprobe);
    if (canonicalJson(observedProbe) !== canonicalJson(evidence.video.probe)) return failure('VIDEO_PROBE_BINDING', observedProbe, evidence.video.probe, checks);
    const expectedProbe = {
      codecName: 'h264', pixelFormat: spec.video.pixelFormat, width: spec.proxy.width, height: spec.proxy.height,
      rFrameRate: `${spec.timeline.fpsNumerator}/${spec.timeline.fpsDenominator}`,
      avgFrameRate: `${spec.timeline.fpsNumerator}/${spec.timeline.fpsDenominator}`,
      declaredFrames: spec.timeline.expectedFrameCount, decodedFrames: spec.timeline.expectedFrameCount,
      streamDurationSeconds: spec.timeline.expectedDurationSeconds, containerDurationSeconds: spec.timeline.expectedDurationSeconds, audioStreams: 0,
    };
    if (canonicalJson(observedProbe) !== canonicalJson(expectedProbe)) return failure('VIDEO_PROFILE', observedProbe, expectedProbe, checks);
    checks.push('VIDEO_PROFILE');

    return { documentType: 'BFS_REVIEW_DAILIES_VERIFICATION', version: '0.1.0', valid: true, reason: 'OK', evidenceHash: evidence.evidenceHash, sequenceHash: sequence.sequenceHash, videoSha256: videoSha, checks };
  } catch (error) {
    return failure('VERIFIER_ERROR', error.message, null, checks);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const option = name => { const index = args.indexOf(name); return index >= 0 ? args[index + 1] : null; };
  const evidence = option('--evidence');
  const sequenceDir = option('--sequence-dir');
  const report = option('--report');
  if (!evidence) throw new Error('Usage: --evidence FILE [--sequence-dir DIR] [--report FILE]');
  const result = await verifyReviewDailies(evidence, { sequenceDir });
  if (report) await writeFile(resolve(report), `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`BFS_REVIEW_DAILIES_VERIFY ${result.valid ? 'PASS' : 'FAIL'} ${result.reason}\n`);
  if (!result.valid) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { process.stderr.write(`BFS_REVIEW_DAILIES_VERIFY_ERROR ${error.message}\n`); process.exitCode = 1; });
}
