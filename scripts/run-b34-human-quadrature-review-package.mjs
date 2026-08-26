import { createHash, randomBytes } from 'node:crypto';
import { link, mkdir, readFile, readdir, statfs, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';
import { analyzeB34Responses, responseBody, validateB34Response } from './lib/b34-human-review.mjs';
import { b34ObserverHtml } from './lib/b34-observer-html.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const sourceRoot = resolve(workRoot, 'sources');
const compositeRoot = resolve(workRoot, 'composites');
const displayRoot = resolve(workRoot, 'display');
const carrierRoot = resolve(workRoot, 'carriers');
const decodedRoot = resolve(workRoot, 'decoded');
const sessionRoot = resolve(workRoot, 'observer-sessions');
const sealedRoot = resolve(workRoot, 'sealed');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.1.json');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const b26SpecPath = resolve(repositoryRoot, 'specs/blind-temporal-review-spec.v0.1.json');
const b26ResultPath = resolve(repositoryRoot, 'experiments/blind-temporal-review-v0-1/results.json');
const b33SpecPath = resolve(repositoryRoot, 'specs/quadrature-temporal-holdout-spec.v0.1.json');
const b33ResultPath = resolve(repositoryRoot, 'experiments/quadrature-temporal-holdout-v0-1/results.json');
const b33AnalysisPath = resolve(repositoryRoot, 'experiments/quadrature-temporal-holdout-v0-1/evidence/temporal-analysis.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b34_human_quadrature_review.py');
const compositor = resolve(repositoryRoot, 'blender/composite_export_b34_review.py');
const verifier = resolve(repositoryRoot, 'blender/verify_b34_lossless_carrier.py');
const reviewLibrary = resolve(repositoryRoot, 'scripts/lib/b34-human-review.mjs');
const observerLibrary = resolve(repositoryRoot, 'scripts/lib/b34-observer-html.mjs');
const acceptor = resolve(repositoryRoot, 'scripts/accept-b34-human-response.mjs');
const analyzer = resolve(repositoryRoot, 'scripts/analyze-b34-human-responses.mjs');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const ffmpeg = resolve(process.env.FFMPEG_BIN || '/opt/homebrew/bin/ffmpeg');
const ffprobe = resolve(process.env.FFPROBE_BIN || '/opt/homebrew/bin/ffprobe');
const expectedSpecSha = '4afcb29f9d47671d4696d0b6d57f5d7e0c5fde4f08bee1e414040ed480257ba2';
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');
const digest = value => createHash('sha256').update(value).digest('hex');

const cells = ['NATURAL32', ...Array.from({ length: 4 }, (_, index) => `Q4_${index + 1}`), ...Array.from({ length: 8 }, (_, index) => `Q8_${index + 1}`)];
const methods = ['NATURAL32', 'QUADRATURE4', 'STRATIFIED8'];
const permutations = [
  { label: 'NQ4Q8', methods: ['NATURAL32', 'QUADRATURE4', 'STRATIFIED8'] },
  { label: 'NQ8Q4', methods: ['NATURAL32', 'STRATIFIED8', 'QUADRATURE4'] },
  { label: 'Q4NQ8', methods: ['QUADRATURE4', 'NATURAL32', 'STRATIFIED8'] },
  { label: 'Q4Q8N', methods: ['QUADRATURE4', 'STRATIFIED8', 'NATURAL32'] },
  { label: 'Q8NQ4', methods: ['STRATIFIED8', 'NATURAL32', 'QUADRATURE4'] },
  { label: 'Q8Q4N', methods: ['STRATIFIED8', 'QUADRATURE4', 'NATURAL32'] },
];

function run(command, args, env = process.env) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
    const processId = child.pid;
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ processId, output, code }) : reject(Object.assign(new Error(`${command} failed (${code}) pid=${processId}\n${output}`), { processId, output, code })));
  });
}

async function expectFailure(command, args, pattern) {
  try {
    await run(command, args);
    return 'UNEXPECTED_SUCCESS';
  } catch (error) {
    return error.output?.includes(pattern) ? pattern : `UNEXPECTED_FAILURE_${error.code}`;
  }
}

function requireValue(condition, message) { if (!condition) throw new Error(message); }
async function directoryEmpty(path) { try { return (await readdir(path)).length === 0; } catch { return true; } }

function expectedControls(spec, cell) {
  if (cell === 'NATURAL32') return { samples: spec.renderDesign.natural32.samples, jitter: null };
  const [family, indexText] = cell.split('_');
  const definition = family === 'Q4' ? spec.renderDesign.quadrature4 : spec.renderDesign.stratified8;
  return { samples: definition.samplesPerComponent, jitter: definition.points[Number(indexText) - 1] };
}

function syntheticResponse({ spec, specSha, manifest, sealed, sessionIndex, observerId, direction = 'INDISTINGUISHABLE', q4Rating = 'NONE' }) {
  const publicSession = manifest.sessions[sessionIndex], sealedSession = sealed.sessions[sessionIndex];
  const visibleByMethod = Object.fromEntries(sealedSession.mapping.map(item => [item.sourceLabel, item.visibleLabel]));
  const primaryLabels = [visibleByMethod.NATURAL32, visibleByMethod.STRATIFIED8].sort();
  const pairResponses = [['CLIP-01', 'CLIP-02'], ['CLIP-01', 'CLIP-03'], ['CLIP-02', 'CLIP-03']].map(labels => {
    let choice = 'INDISTINGUISHABLE';
    if (JSON.stringify(labels) === JSON.stringify(primaryLabels) && direction !== 'INDISTINGUISHABLE') {
      const chosen = direction === 'Q8_MORE_STABLE' ? visibleByMethod.STRATIFIED8 : visibleByMethod.NATURAL32;
      choice = labels[0] === chosen ? 'LEFT_MORE_STABLE' : 'RIGHT_MORE_STABLE';
    }
    return { labels, choice, note: '' };
  });
  const now = new Date(Date.UTC(2026, 7, 26, 18, sessionIndex, 0)).toISOString();
  const later = new Date(Date.UTC(2026, 7, 26, 18, sessionIndex, 30)).toISOString();
  const body = {
    documentType: 'BFS_B34_BLINDED_RESPONSE', version: spec.version, sessionId: publicSession.sessionId,
    studySpecSha256: specSha, mappingCommitment: publicSession.mappingCommitment, startedAt: now, lockedAt: later,
    carrierBindings: publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, sha256 })),
    playbackTelemetry: publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, carrierSha256: sha256, plays: Array.from({ length: 2 }, () => ({ ended: true, playbackRate: 1, elapsedSeconds: 6.01, totalVideoFramesDelta: 144, droppedVideoFramesDelta: 0, seekingEvents: 0, rateChangeEvents: 0, stallEvents: 0, pageHiddenDuringPlay: false })) })),
    clipResponses: publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, carrierSha256: sha256, rating: label === visibleByMethod.QUADRATURE4 ? q4Rating : 'NONE', confidence: 'HIGH', note: '' })),
    pairResponses,
    viewing: { observerId, expertise: 'synthetic attack-test fixture', directDevelopmentInvolvement: 'NO', acuityScreening: 'PASS', colourVisionScreening: 'PASS', displayManufacturerModel: 'Frozen synthetic display', displayNativeWidth: 1920, displayNativeHeight: 1080, refreshRateHz: 120, brightnessSetting: 'recorded', browser: 'Synthetic 1', operatingSystem: 'Synthetic OS', viewingDistance: '3H', ambientLighting: 'dim stable', browserZoomPercent: 100, zoomConfirmed: true, cssVideoSize: [960, 540], devicePixelRatio: 1, userAgent: 'BFS-B34-synthetic-validator-fixture' },
  };
  return { ...body, responseHash: sha256Canonical(body) };
}

requireValue(await directoryEmpty(evidenceRoot), 'B34 evidence directory must start empty; preserve or explicitly record cleanup before rerun');
requireValue(await directoryEmpty(workRoot), 'B34 work directory must start empty; preserve or explicitly record cleanup before rerun');
const disk = await statfs(repositoryRoot);
const freeBytes = disk.bavail * disk.bsize;
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
requireValue(specSha === expectedSpecSha, 'B34 spec changed after preregistration');
requireValue(freeBytes >= spec.resourceGate.minimumFreeBytesBeforeRender, `B34 free-space gate failed: ${freeBytes}`);
const review = JSON.parse(await readFile(reviewPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, review.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const fixedInputs = [
  [reviewPath, spec.evidenceBasis.reviewRenderSpecSha256, 'review spec'], [b26SpecPath, spec.evidenceBasis.b26SpecSha256, 'B26 spec'], [b26ResultPath, spec.evidenceBasis.b26ResultSha256, 'B26 result'], [b33SpecPath, spec.evidenceBasis.b33SpecSha256, 'B33 spec'], [b33ResultPath, spec.evidenceBasis.b33ResultSha256, 'B33 result'], [b33AnalysisPath, spec.evidenceBasis.b33AnalysisSha256, 'B33 analysis'], [blender, spec.runtime.blenderBinarySha256, 'Blender'], [ocioPath, spec.runtime.ocioSha256, 'OCIO'], [ffmpeg, spec.runtime.ffmpegSha256, 'FFmpeg'], [ffprobe, spec.runtime.ffprobeSha256, 'FFprobe'], [scenePath, spec.source.sceneBlendSha256, 'scene'],
];
for (const [path, expected, label] of fixedInputs) requireValue(await sha256File(path) === expected, `${label} frozen SHA mismatch`);
requireValue(JSON.parse(await readFile(b33ResultPath, 'utf8')).decision === spec.evidenceBasis.b33Decision, 'B33 frozen decision mismatch');

await mkdir(evidenceRoot, { recursive: true }); await mkdir(sourceRoot, { recursive: true });
await mkdir(carrierRoot, { recursive: true }); await mkdir(decodedRoot, { recursive: true });
await mkdir(sessionRoot, { recursive: true }); await mkdir(sealedRoot, { recursive: true });
const tools = Object.fromEntries(await Promise.all(Object.entries({ configurator, renderer, compositor, verifier, reviewLibrary, observerLibrary, acceptor, analyzer, runner }).map(async ([name, path]) => [`${name}Sha256`, await sha256File(path)])));
const records = new Map();
for (const cell of cells) {
  const outputDir = resolve(sourceRoot, cell), reportPath = resolve(evidenceRoot, `${cell}.render.json`), threadPath = resolve(evidenceRoot, `${cell}.threads.json`), manifestPath = resolve(evidenceRoot, `${cell}.manifest.json`);
  await mkdir(outputDir);
  const launched = await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--study-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath, '--output-dir', outputDir, '--report', reportPath, '--cell', cell], { ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: threadPath });
  const report = JSON.parse(await readFile(reportPath, 'utf8')), controls = expectedControls(spec, cell);
  requireValue(report.processId === launched.processId, `${cell} PID binding mismatch`);
  requireValue(report.renderCalls === 144 && report.outputs.length === 144, `${cell} render count mismatch`);
  requireValue(report.observedControls.samples === controls.samples && JSON.stringify(report.observedControls.jitter) === JSON.stringify(controls.jitter), `${cell} frozen controls mismatch`);
  const manifestBody = { documentType: 'BFS_B34_SOURCE_RENDER_MANIFEST', version: spec.version, studySpecSha256: specSha, cell, processId: launched.processId, totalRenderSeconds: report.totalRenderSeconds, renderReportSha256: await sha256File(reportPath), threadReportSha256: await sha256File(threadPath), toolIdentities: tools, outputs: report.outputs.map(item => ({ frame: item.frame, name: item.name, fileUri: repoUri(resolve(outputDir, item.name)), sha256: item.sha256, bytes: item.bytes })) };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest)); records.set(cell, { report, manifest, reportPath, threadPath, manifestPath });
  process.stdout.write(`BFS_B34_SOURCE_OK ${cell} pid=${launched.processId} seconds=${report.totalRenderSeconds}\n`);
}
requireValue(new Set([...records.values()].map(item => item.report.processId)).size === spec.renderDesign.totalProcesses, 'B34 source process IDs missing or duplicated');
requireValue([...records.values()].reduce((sum, item) => sum + item.report.renderCalls, 0) === spec.renderDesign.totalRenderCalls, 'B34 total render calls mismatch');
const ledgerBody = { documentType: 'BFS_B34_SOURCE_PROCESS_LEDGER', version: spec.version, studySpecSha256: specSha, preflight: { freeBytes, minimumFreeBytes: spec.resourceGate.minimumFreeBytesBeforeRender, workStartedEmpty: true, evidenceStartedEmpty: true }, processes: cells.map((cell, orderIndex) => ({ orderIndex, cell, processId: records.get(cell).report.processId, renderCalls: records.get(cell).report.renderCalls, renderReportSha256: records.get(cell).manifest.renderReportSha256, threadReportSha256: records.get(cell).manifest.threadReportSha256, manifestHash: records.get(cell).manifest.manifestHash })) };
const processLedger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) }, processLedgerPath = resolve(evidenceRoot, 'source-process-ledger.json');
await writeFile(processLedgerPath, serialize(processLedger));

const compositeReportPath = resolve(evidenceRoot, 'composite-display.manifest.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', compositor, '--', '--study-spec', specPath, '--source-root', sourceRoot, '--composite-root', compositeRoot, '--display-root', displayRoot, '--report', compositeReportPath], { ...process.env, OCIO: ocioPath });
const compositeManifest = JSON.parse(await readFile(compositeReportPath, 'utf8'));
requireValue(compositeManifest.totalSourceBindings === spec.renderDesign.totalRenderCalls && compositeManifest.totalCompositeFrames === 432 && compositeManifest.totalDisplayFrames === 432, 'B34 composite/export count mismatch');

const carriers = [];
for (const method of methods) {
  const sourceDir = resolve(displayRoot, method), carrierPath = resolve(carrierRoot, `${method}.lossless.webm`), decodedDir = resolve(decodedRoot, method), roundtripPath = resolve(evidenceRoot, `${method}.roundtrip.json`);
  await mkdir(decodedDir);
  await run(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-framerate', '24', '-start_number', '1', '-i', resolve(sourceDir, 'frame-%04d.png'), '-an', '-c:v', 'libvpx-vp9', '-lossless', '1', '-pix_fmt', 'gbrp', '-row-mt', '0', '-threads', '1', '-tile-columns', '0', carrierPath]);
  await run(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-i', carrierPath, '-fps_mode', 'passthrough', resolve(decodedDir, 'frame-%04d.png')]);
  await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', verifier, '--', '--study-spec', specPath, '--source-dir', sourceDir, '--decoded-dir', decodedDir, '--display-manifest', compositeReportPath, '--method', method, '--output', roundtripPath]);
  const probed = await run(ffprobe, ['-v', 'error', '-show_entries', 'format=size,duration,format_name:stream=codec_name,profile,pix_fmt,width,height,r_frame_rate', '-of', 'json', carrierPath]);
  const probe = JSON.parse(probed.output), stream = probe.streams[0], format = probe.format, roundtrip = JSON.parse(await readFile(roundtripPath, 'utf8'));
  const item = { method, localUri: repoUri(carrierPath), sha256: await sha256File(carrierPath), bytes: Number(format.size), metadata: { codecName: stream.codec_name, profile: stream.profile, pixelFormat: stream.pix_fmt, width: stream.width, height: stream.height, frameRate: stream.r_frame_rate, durationSeconds: Number(format.duration), container: format.format_name }, roundtrip, roundtripReportUri: repoUri(roundtripPath), roundtripReportSha256: await sha256File(roundtripPath) };
  requireValue(roundtrip.exactRgbFrames === 144 && roundtrip.allSourceAlphaOpaque && roundtrip.maximumAbsoluteRgbError === 0 && roundtrip.totalChangedRgbPixels === 0, `${method} carrier exactness failed`);
  carriers.push(item); process.stdout.write(`BFS_B34_CARRIER_OK ${method} bytes=${item.bytes} sha=${item.sha256}\n`);
}

const sealedSessions = [], publicSessions = [];
for (let index = 0; index < 18; index += 1) {
  const sessionId = `OBS-${String(index + 1).padStart(2, '0')}`, permutation = permutations[index % 6], salt = randomBytes(32).toString('hex');
  const mapping = permutation.methods.map((sourceLabel, position) => ({ visibleLabel: `CLIP-${String(position + 1).padStart(2, '0')}`, sourceLabel }));
  const commitment = sha256Canonical({ sessionId, salt, mapping });
  sealedSessions.push({ sessionId, salt, permutation: permutation.label, mapping, commitment });
  const dir = resolve(sessionRoot, sessionId); await mkdir(dir);
  const visibleCarriers = [];
  for (const item of mapping) {
    const source = carriers.find(carrier => carrier.method === item.sourceLabel), file = `${item.visibleLabel}.webm`;
    await link(resolve(carrierRoot, `${item.sourceLabel}.lossless.webm`), resolve(dir, file));
    visibleCarriers.push({ label: item.visibleLabel, file, sha256: source.sha256, bytes: source.bytes });
  }
  const html = b34ObserverHtml({ sessionId, studySpecSha256: specSha, mappingCommitment: commitment, visibleCarriers });
  await writeFile(resolve(dir, 'index.html'), html);
  publicSessions.push({ sessionId, mappingCommitment: commitment, observerPackageUri: repoUri(dir), observerHtmlSha256: digest(html), visibleCarrierBindings: visibleCarriers });
}
const sealedBody = { version: spec.version, sessions: sealedSessions }, sealed = { ...sealedBody, overallCommitment: sha256Canonical(sealedBody) };
const sealedPath = resolve(sealedRoot, 'mapping.sealed.json'); await writeFile(sealedPath, serialize(sealed));
const commitmentArtifact = { documentType: 'BFS_B34_MAPPING_COMMITMENT', version: spec.version, studySpecSha256: specSha, overallCommitment: sealed.overallCommitment, sessions: publicSessions.map(({ sessionId, mappingCommitment }) => ({ sessionId, mappingCommitment })), mappingStatus: 'SEALED_UNTIL_RESPONSE_HASH_LOCK' };
const commitmentPath = resolve(evidenceRoot, 'mapping.commitment.json'); await writeFile(commitmentPath, serialize(commitmentArtifact));
let actualSealedExposure = false, actualHtmlControlsSafe = true;
for (const session of publicSessions) {
  const names = await readdir(resolve(sessionRoot, session.sessionId));
  const html = await readFile(resolve(sessionRoot, session.sessionId, 'index.html'), 'utf8');
  if (names.some(name => /mapping|sealed/i.test(name)) || /NATURAL32|QUADRATURE4|STRATIFIED8|sourceLabel|permutation/i.test(html)) actualSealedExposure = true;
  if (/<video[^>]+controls/i.test(html) || !html.includes('droppedVideoFramesDelta') || !html.includes("video.addEventListener('seeking'") || !html.includes("video.addEventListener('ratechange'")) actualHtmlControlsSafe = false;
}
const manifest = { documentType: 'BFS_B34_HUMAN_REVIEW_PACKAGE', version: spec.version, createdAtUtc: new Date().toISOString(), packageStatus: 'CARRIER_AND_INTERFACE_READY', studySpecSha256: specSha, evidenceBasis: spec.evidenceBasis, tools, sourceProcessLedgerSha256: await sha256File(processLedgerPath), compositeDisplayManifestSha256: await sha256File(compositeReportPath), carriers, mappingCommitment: sealed.overallCommitment, mappingStatus: 'SEALED_LOCAL_NOT_PUBLISHED', sessions: publicSessions, humanReview: { status: 'HUMAN_REVIEW_PENDING', formalResponseCount: 0, pilotResponseCount: 0, decision: null, claim: 'No human response has been collected or inferred.' }, nonClaims: spec.nonClaims };
const manifestPath = resolve(evidenceRoot, 'package.manifest.json'); await writeFile(manifestPath, serialize(manifest));

function packageReason(overrides = {}) {
  const observed = { specSha, evidenceBasis: spec.evidenceBasis, blenderSha: spec.runtime.blenderBinarySha256, schedule: cells, processIds: cells.map(cell => records.get(cell).report.processId), sourceOutputBinding: true, freeBytes, directoriesStartedEmpty: true, weights: [compositeManifest.methods.QUADRATURE4.weights, compositeManifest.methods.STRATIFIED8.weights], displayTransform: compositeManifest.observedDisplayTransform, displayFrameCount: compositeManifest.totalDisplayFrames, carrierMetadata: carriers.map(item => item.metadata), exactFrames: carriers.map(item => item.roundtrip.exactRgbFrames), permutationCounts: Object.fromEntries(permutations.map(item => [item.label, sealedSessions.filter(session => session.permutation === item.label).length])), sealedExposure: actualSealedExposure, overallCommitment: sealed.overallCommitment, htmlControlsSafe: actualHtmlControlsSafe, unblindBeforeLock: false, ...overrides };
  if (observed.specSha !== expectedSpecSha) return 'SPEC_SHA';
  if (JSON.stringify(observed.evidenceBasis) !== JSON.stringify(spec.evidenceBasis)) return 'EVIDENCE_BASIS';
  if (observed.blenderSha !== spec.runtime.blenderBinarySha256) return 'RUNTIME_IDENTITY';
  if (JSON.stringify(observed.schedule) !== JSON.stringify(cells)) return 'METHOD_SCHEDULE';
  if (new Set(observed.processIds).size !== 13) return 'PROCESS_ID';
  if (!observed.sourceOutputBinding) return 'SOURCE_OUTPUT_BINDING';
  if (observed.freeBytes < spec.resourceGate.minimumFreeBytesBeforeRender || !observed.directoriesStartedEmpty) return 'RESOURCE_GATE';
  if (JSON.stringify(observed.weights) !== JSON.stringify([spec.renderDesign.quadrature4.weights, spec.renderDesign.stratified8.weights]) || sha256Canonical(observed.displayTransform) !== sha256Canonical({ display: spec.displayTransform.display, view: spec.displayTransform.view, look: spec.displayTransform.look, exposure: spec.displayTransform.exposure, gamma: spec.displayTransform.gamma, dither: spec.displayTransform.dither, output: spec.displayTransform.output })) return 'COMPOSITE_OR_DISPLAY';
  if (observed.displayFrameCount !== 432) return 'DISPLAY_FRAMES';
  if (observed.carrierMetadata.some(item => item.codecName !== 'vp9' || item.profile !== 'Profile 1' || item.pixelFormat !== 'gbrp' || item.width !== 960 || item.height !== 540 || item.frameRate !== '24/1' || item.durationSeconds !== 6)) return 'CARRIER_METADATA';
  if (observed.exactFrames.some(value => value !== 144)) return 'CARRIER_ROUNDTRIP';
  if (Object.values(observed.permutationCounts).some(value => value !== 3)) return 'SCHEDULE_BALANCE';
  if (observed.sealedExposure) return 'SEALED_EXPOSURE';
  if (observed.overallCommitment !== sealed.overallCommitment || observed.unblindBeforeLock) return 'MAPPING_OR_UNBLIND';
  if (!observed.htmlControlsSafe) return 'PRIMARY_CONTROLS';
  return 'OK';
}
const attack = (name, expected, observed) => ({ name, expected, observed, pass: expected === observed });
const synthetic = syntheticResponse({ spec, specSha, manifest, sealed, sessionIndex: 0, observerId: 'SYNTH-01' });
const responseReason = override => validateB34Response({ spec, specSha, manifest, sealed, response: override }).reason;
const acceptanceAttackRoot = resolve(workRoot, 'attack-response-immutability');
const acceptanceResponsePath = resolve(acceptanceAttackRoot, 'synthetic.response.json');
const acceptanceDir = resolve(acceptanceAttackRoot, 'accepted');
const acceptanceLedger = resolve(acceptanceAttackRoot, 'accepted-ledger.jsonl');
await mkdir(acceptanceAttackRoot);
await writeFile(acceptanceResponsePath, serialize(synthetic));
const acceptanceArgs = [acceptor, '--response', acceptanceResponsePath, '--manifest', manifestPath, '--sealed', sealedPath, '--accepted-dir', acceptanceDir, '--ledger', acceptanceLedger];
await run(process.execPath, acceptanceArgs);
const mutationAttackObserved = await expectFailure(process.execPath, acceptanceArgs, 'RESPONSE_MUTATION_OR_DUPLICATE');
const attacks = [
  attack('wrong_spec_or_evidence_hash', 'SPEC_SHA', packageReason({ specSha: '0'.repeat(64) })),
  attack('wrong_runtime_identity', 'RUNTIME_IDENTITY', packageReason({ blenderSha: '1'.repeat(64) })),
  attack('changed_method_schedule', 'METHOD_SCHEDULE', packageReason({ schedule: cells.slice(1) })),
  attack('duplicate_process_id', 'PROCESS_ID', packageReason({ processIds: cells.map(() => records.get(cells[0]).report.processId) })),
  attack('source_exr_hash_or_order_mismatch', 'SOURCE_OUTPUT_BINDING', packageReason({ sourceOutputBinding: false })),
  attack('insufficient_free_space', 'RESOURCE_GATE', packageReason({ freeBytes: 1 })),
  attack('changed_composite_or_display_transform', 'COMPOSITE_OR_DISPLAY', packageReason({ weights: [[1, 0, 0, 0], spec.renderDesign.stratified8.weights] })),
  attack('missing_display_frame', 'DISPLAY_FRAMES', packageReason({ displayFrameCount: 431 })),
  attack('carrier_metadata_substitution', 'CARRIER_METADATA', packageReason({ carrierMetadata: carriers.map(item => ({ ...item.metadata, codecName: 'h264' })) })),
  attack('carrier_roundtrip_mismatch', 'CARRIER_ROUNDTRIP', packageReason({ exactFrames: [143, 144, 144] })),
  attack('unbalanced_session_schedule', 'SCHEDULE_BALANCE', packageReason({ permutationCounts: Object.fromEntries(permutations.map((item, index) => [item.label, index ? 3 : 2])) })),
  attack('sealed_mapping_exposure', 'SEALED_EXPOSURE', packageReason({ sealedExposure: true })),
  attack('mapping_commitment_mismatch', 'MAPPING_OR_UNBLIND', packageReason({ overallCommitment: '3'.repeat(64) })),
  attack('native_primary_controls', 'PRIMARY_CONTROLS', packageReason({ htmlControlsSafe: false })),
  attack('wrong_playback_count_or_dropped_frame', 'DROPPED_FRAME', responseReason((() => { const value = structuredClone(synthetic); value.playbackTelemetry[0].plays[0].droppedVideoFramesDelta = 1; value.responseHash = sha256Canonical(responseBody(value)); return value; })())),
  attack('invalid_refresh_rate', 'DISPLAY_REFRESH', responseReason((() => { const value = structuredClone(synthetic); value.viewing.refreshRateHz = 60; value.responseHash = sha256Canonical(responseBody(value)); return value; })())),
  attack('missing_viewing_record', 'VIEWING_RECORD', responseReason((() => { const value = structuredClone(synthetic); value.viewing.ambientLighting = ''; value.responseHash = sha256Canonical(responseBody(value)); return value; })())),
  attack('developer_counted_independent', 'OBSERVER_INDEPENDENCE', responseReason((() => { const value = structuredClone(synthetic); value.viewing.directDevelopmentInvolvement = 'YES'; value.responseHash = sha256Canonical(responseBody(value)); return value; })())),
  attack('response_or_carrier_binding_mismatch', 'CARRIER_BINDING', responseReason((() => { const value = structuredClone(synthetic); value.carrierBindings[0].sha256 = '2'.repeat(64); value.responseHash = sha256Canonical(responseBody(value)); return value; })())),
  attack('response_mutation_after_acceptance', 'RESPONSE_MUTATION_OR_DUPLICATE', mutationAttackObserved),
  attack('unblinding_before_response_lock', 'MAPPING_OR_UNBLIND', packageReason({ unblindBeforeLock: true })),
];
const formalFixtures = Array.from({ length: 18 }, (_, index) => syntheticResponse({ spec, specSha, manifest, sealed, sessionIndex: index, observerId: `SYNTH-${String(index + 1).padStart(2, '0')}`, q4Rating: 'SEVERE' }));
const formal = analyzeB34Responses({ spec, specSha, manifest, sealed, responses: formalFixtures });
const duplicateFixture = structuredClone(formalFixtures); duplicateFixture[1].viewing.observerId = duplicateFixture[0].viewing.observerId; duplicateFixture[1].responseHash = sha256Canonical(responseBody(duplicateFixture[1]));
attacks.push(attack('duplicate_observer_or_session', 'INVALID_REVIEW', analyzeB34Responses({ spec, specSha, manifest, sealed, responses: duplicateFixture }).status));
attacks.push(attack('formal_gate_below_18', 'FORMAL_REVIEW_INCOMPLETE', analyzeB34Responses({ spec, specSha, manifest, sealed, responses: formalFixtures.slice(0, 17) }).status));
attacks.push(attack('q4_cannot_change_primary_decision', spec.formalDecision.noDirectionalDifferenceLabel, formal.decision));
requireValue(attacks.length === spec.attacksRequired.length && attacks.every(item => item.pass), `B34 attacks failed: ${JSON.stringify(attacks.filter(item => !item.pass))}`);
requireValue(packageReason() === 'OK', 'B34 package validation failed');
requireValue(formal.status === 'FORMAL_REVIEW_COMPLETE', 'B34 synthetic analyzer fixture failed');

const result = { documentType: 'BFS_B34_HUMAN_QUADRATURE_REVIEW_PACKAGE_RESULT', version: spec.version, experimentId: spec.experimentId, executedAtUtc: new Date().toISOString(), packageStatus: 'CARRIER_AND_INTERFACE_READY', validPackage: true, humanReview: { status: 'HUMAN_REVIEW_PENDING', formalResponseCount: 0, pilotResponseCount: 0, decision: null }, identities: { studySpecSha256: specSha, sourceProcessLedgerSha256: await sha256File(processLedgerPath), compositeDisplayManifestSha256: await sha256File(compositeReportPath), packageManifestSha256: await sha256File(manifestPath), mappingCommitmentSha256: await sha256File(commitmentPath), ...tools }, execution: { freeBytesBeforeRender: freeBytes, uniqueBlenderSourceProcesses: new Set([...records.values()].map(item => item.report.processId)).size, renderCalls: spec.renderDesign.totalRenderCalls, sourceExrFiles: spec.renderDesign.totalRenderCalls, compositeExrFiles: 432, displayPngFiles: 432 }, carrierSummary: { count: carriers.length, totalBytes: carriers.reduce((sum, item) => sum + item.bytes, 0), all144FrameRgbExact: carriers.every(item => item.roundtrip.exactRgbFrames === 144), maximumAbsoluteRgbError: Math.max(...carriers.map(item => item.roundtrip.maximumAbsoluteRgbError)), totalChangedRgbPixels: carriers.reduce((sum, item) => sum + item.roundtrip.totalChangedRgbPixels, 0) }, schedule: { formalTarget: 18, permutations: 6, repetitionsPerPermutation: 3, overallCommitment: sealed.overallCommitment, mappingStatus: 'SEALED_LOCAL_NOT_PUBLISHED' }, attacks: { passed: attacks.filter(item => item.pass).length, total: attacks.length, cases: attacks }, analyzerSyntheticFixture: { classification: 'ATTACK_TEST_ONLY_NOT_HUMAN_EVIDENCE', expectedDecision: spec.formalDecision.noDirectionalDifferenceLabel, observedDecision: formal.decision, q4AllSevere: true, pass: formal.decision === spec.formalDecision.noDirectionalDifferenceLabel }, artifacts: { sourceProcessLedger: repoUri(processLedgerPath), compositeDisplayManifest: repoUri(compositeReportPath), packageManifest: repoUri(manifestPath), mappingCommitment: repoUri(commitmentPath), localObserverSessions: repoUri(sessionRoot) }, nonClaims: spec.nonClaims };
const resultPath = resolve(experimentRoot, 'results.json'); await writeFile(resultPath, serialize(result));
process.stdout.write(`BFS_B34_PACKAGE_OK processes=13 renders=1872 carriers=3 rgbExact=true attacks=${attacks.length}/${attacks.length} human=HUMAN_REVIEW_PENDING\n`);
