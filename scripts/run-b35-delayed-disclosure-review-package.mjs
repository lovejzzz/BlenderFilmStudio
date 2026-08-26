import { createHash, randomBytes } from 'node:crypto';
import { link, mkdir, readFile, readdir, statfs, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';
import { analyzeB35Responses, responseBody, validateB35Response } from './lib/b35-human-review.mjs';
import { b35ObserverHtml } from './lib/b35-observer-html.mjs';
import { auditB35PublicState, buildB35SensitiveRegistry } from './lib/b35-public-state-audit.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-2');
const workRoot = resolve(experimentRoot, 'work');
const evidenceRoot = resolve(workRoot, 'private-evidence');
const sourceRoot = resolve(workRoot, 'sources');
const compositeRoot = resolve(workRoot, 'composites');
const displayRoot = resolve(workRoot, 'display');
const carrierRoot = resolve(workRoot, 'carriers');
const decodedRoot = resolve(workRoot, 'decoded');
const sessionRoot = resolve(workRoot, 'observer-sessions');
const sealedRoot = resolve(workRoot, 'sealed');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.2.json');
const reviewPath = resolve(repositoryRoot, 'specs/review-render-spec.v0.1.json');
const b34PackagePath = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1/evidence/package.manifest.json');
const b34CompositePath = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1/evidence/composite-display.manifest.json');
const b34AttackPath = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1/evidence/public-hash-unblinding-audit.json');
const publicCommitmentPath = resolve(experimentRoot, 'precollection-commitment.json');
const configurator = resolve(repositoryRoot, 'blender/configure_eevee_threads.py');
const renderer = resolve(repositoryRoot, 'blender/render_b35_delayed_disclosure_review.py');
const compositor = resolve(repositoryRoot, 'blender/composite_export_b35_review.py');
const verifier = resolve(repositoryRoot, 'blender/verify_b35_lossless_carrier.py');
const reviewLibrary = resolve(repositoryRoot, 'scripts/lib/b35-human-review.mjs');
const observerLibrary = resolve(repositoryRoot, 'scripts/lib/b35-observer-html.mjs');
const publicAuditLibrary = resolve(repositoryRoot, 'scripts/lib/b35-public-state-audit.mjs');
const publicAuditor = resolve(repositoryRoot, 'scripts/audit-b35-public-state.mjs');
const acceptor = resolve(repositoryRoot, 'scripts/accept-b35-human-response.mjs');
const closer = resolve(repositoryRoot, 'scripts/close-b35-collection.mjs');
const analyzer = resolve(repositoryRoot, 'scripts/analyze-b35-human-responses.mjs');
const independentAuditor = resolve(repositoryRoot, 'scripts/audit-b35-private-package.mjs');
const compositeAuditor = resolve(repositoryRoot, 'blender/audit_b35_composites.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const ffmpeg = resolve(process.env.FFMPEG_BIN || '/opt/homebrew/bin/ffmpeg');
const ffprobe = resolve(process.env.FFPROBE_BIN || '/opt/homebrew/bin/ffprobe');
const expectedSpecSha = '2a6af8e5d084b29dd51fc69acb3a96223cae477c85c815ea48c2667781ebf83f';
const expectedB34PackageSha = 'df12706646b0c893b0e8a5a8ef0858e1f3d831400154c59d754bdd20eb9276f7';
const expectedB34CompositeSha = '9e57c81716c5bd77eeae6fc12c0b28e8628894491db4bc0cc7375762d5400507';
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
  try { await run(command, args); return 'UNEXPECTED_SUCCESS'; }
  catch (error) { return error.output?.includes(pattern) ? pattern : `UNEXPECTED_FAILURE_${error.code}`; }
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
    documentType: 'BFS_B35_BLINDED_RESPONSE', version: spec.version, sessionId: publicSession.sessionId,
    studySpecSha256: specSha, mappingCommitment: publicSession.mappingCommitment, startedAt: now, lockedAt: later,
    carrierBindings: publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, sha256 })),
    playbackTelemetry: publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, carrierSha256: sha256, plays: Array.from({ length: 2 }, () => ({ ended: true, playbackRate: 1, elapsedSeconds: 6.01, totalVideoFramesDelta: 144, droppedVideoFramesDelta: 0, seekingEvents: 0, rateChangeEvents: 0, stallEvents: 0, pageHiddenDuringPlay: false })) })),
    clipResponses: publicSession.visibleCarrierBindings.map(({ label, sha256 }) => ({ label, carrierSha256: sha256, rating: label === visibleByMethod.QUADRATURE4 ? q4Rating : 'NONE', confidence: 'HIGH', note: '' })),
    pairResponses,
    viewing: { observerId, expertise: 'synthetic attack-test fixture', directDevelopmentInvolvement: 'NO', acuityScreening: 'PASS', colourVisionScreening: 'PASS', displayManufacturerModel: 'Frozen synthetic display', displayNativeWidth: 1920, displayNativeHeight: 1080, refreshRateHz: 120, brightnessSetting: 'recorded', browser: 'Synthetic 1', operatingSystem: 'Synthetic OS', viewingDistance: '3H', ambientLighting: 'dim stable', browserZoomPercent: 100, zoomConfirmed: true, cssVideoSize: [960, 540], devicePixelRatio: 1, userAgent: 'BFS-B35-synthetic-validator-fixture' },
  };
  return { ...body, responseHash: sha256Canonical(body) };
}

requireValue(await directoryEmpty(workRoot), 'B35 work directory must start empty; preserve or explicitly record cleanup before rerun');
requireValue(await readFile(publicCommitmentPath).catch(() => null) === null, 'B35 public commitment already exists; create a new version instead of overwriting');
const disk = await statfs(repositoryRoot);
const freeBytes = disk.bavail * disk.bsize;
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
requireValue(specSha === expectedSpecSha, 'B35 spec changed after preregistration');
requireValue(freeBytes >= spec.resourceGate.minimumFreeBytesBeforeRender, `B35 free-space gate failed: ${freeBytes}`);
const review = JSON.parse(await readFile(reviewPath, 'utf8'));
const receiptPath = resolve(repositoryRoot, review.source.receiptUri);
const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
const scenePath = resolve(repositoryRoot, receipt.run.sceneBlend.uri);
const ocioPath = resolve(repositoryRoot, receipt.executionIdentity.configuration.ocio.uri);
const fixedInputs = [
  [reviewPath, spec.source.reviewRenderSpecSha256, 'review spec'], [blender, spec.runtime.blenderBinarySha256, 'Blender'],
  [ocioPath, spec.runtime.ocioSha256, 'OCIO'], [ffmpeg, spec.runtime.ffmpegSha256, 'FFmpeg'],
  [ffprobe, spec.runtime.ffprobeSha256, 'FFprobe'], [scenePath, spec.source.sceneBlendSha256, 'scene'],
  [b34PackagePath, expectedB34PackageSha, 'B34 package'], [b34CompositePath, expectedB34CompositeSha, 'B34 composite'],
  [b34AttackPath, spec.supersededPackage.publicHashAttackSha256, 'B34 public-hash attack'],
];
for (const [path, expected, label] of fixedInputs) requireValue(await sha256File(path) === expected, `${label} frozen SHA mismatch`);
const b34Package = JSON.parse(await readFile(b34PackagePath, 'utf8'));
const b34Composite = JSON.parse(await readFile(b34CompositePath, 'utf8'));

await mkdir(evidenceRoot, { recursive: true }); await mkdir(sourceRoot, { recursive: true });
await mkdir(carrierRoot, { recursive: true }); await mkdir(decodedRoot, { recursive: true });
await mkdir(sessionRoot, { recursive: true }); await mkdir(sealedRoot, { recursive: true });
const tools = Object.fromEntries(await Promise.all(Object.entries({ configurator, renderer, compositor, verifier, compositeAuditor, reviewLibrary, observerLibrary, publicAuditLibrary, publicAuditor, acceptor, closer, analyzer, independentAuditor, runner }).map(async ([name, path]) => [`${name}Sha256`, await sha256File(path)])));
const records = new Map();
for (const cell of cells) {
  const outputDir = resolve(sourceRoot, cell), reportPath = resolve(evidenceRoot, `${cell}.render.json`), threadPath = resolve(evidenceRoot, `${cell}.threads.json`), manifestPath = resolve(evidenceRoot, `${cell}.manifest.json`);
  await mkdir(outputDir);
  const launched = await run(blender, ['--background', scenePath, '--disable-autoexec', '--python-exit-code', '1', '--python', configurator, '--python', renderer, '--', '--study-spec', specPath, '--review-spec', reviewPath, '--receipt', receiptPath, '--output-dir', outputDir, '--report', reportPath, '--cell', cell], { ...process.env, OCIO: ocioPath, BFS_B22_THREADS_MODE: 'FIXED', BFS_B22_THREADS: '8', BFS_B22_CELL: 'T08', BFS_B22_INTERVENTION_REPORT: threadPath });
  const report = JSON.parse(await readFile(reportPath, 'utf8')), controls = expectedControls(spec, cell);
  requireValue(report.processId === launched.processId, `${cell} PID binding mismatch`);
  requireValue(report.renderCalls === 144 && report.outputs.length === 144, `${cell} render count mismatch`);
  requireValue(report.observedControls.samples === controls.samples && JSON.stringify(report.observedControls.jitter) === JSON.stringify(controls.jitter), `${cell} frozen sampling controls mismatch`);
  requireValue(report.visualRealization.originalLensMm === spec.newVisualRealization.expectedOriginalLensMm && report.visualRealization.intervenedLensMm === spec.newVisualRealization.intervenedLensMm && report.savedSourceBlend === false, `${cell} visual realization mismatch`);
  const manifestBody = { documentType: 'BFS_B35_SOURCE_RENDER_MANIFEST', version: spec.version, studySpecSha256: specSha, cell, processId: launched.processId, totalRenderSeconds: report.totalRenderSeconds, renderReportSha256: await sha256File(reportPath), threadReportSha256: await sha256File(threadPath), toolIdentities: tools, visualRealization: report.visualRealization, outputs: report.outputs.map(item => ({ frame: item.frame, name: item.name, fileUri: repoUri(resolve(outputDir, item.name)), sha256: item.sha256, bytes: item.bytes })) };
  const manifest = { ...manifestBody, manifestHash: sha256Canonical(manifestBody) };
  await writeFile(manifestPath, serialize(manifest)); records.set(cell, { report, manifest, reportPath, threadPath, manifestPath });
  process.stdout.write(`BFS_B35_SOURCE_OK ${cell} pid=${launched.processId} seconds=${report.totalRenderSeconds}\n`);
}
requireValue(new Set([...records.values()].map(item => item.report.processId)).size === 13, 'B35 source process IDs missing or duplicated');
requireValue([...records.values()].reduce((sum, item) => sum + item.report.renderCalls, 0) === 1872, 'B35 total render calls mismatch');
requireValue(await sha256File(scenePath) === spec.source.sceneBlendSha256, 'B35 source blend was modified');
const ledgerBody = { documentType: 'BFS_B35_SOURCE_PROCESS_LEDGER', version: spec.version, studySpecSha256: specSha, preflight: { freeBytes, minimumFreeBytes: spec.resourceGate.minimumFreeBytesBeforeRender, workStartedEmpty: true }, processes: cells.map((cell, orderIndex) => ({ orderIndex, cell, processId: records.get(cell).report.processId, renderCalls: records.get(cell).report.renderCalls, renderReportSha256: records.get(cell).manifest.renderReportSha256, threadReportSha256: records.get(cell).manifest.threadReportSha256, manifestHash: records.get(cell).manifest.manifestHash })) };
const processLedger = { ...ledgerBody, ledgerHash: sha256Canonical(ledgerBody) }, processLedgerPath = resolve(evidenceRoot, 'source-process-ledger.json');
await writeFile(processLedgerPath, serialize(processLedger));

const compositeReportPath = resolve(evidenceRoot, 'composite-display.manifest.json');
await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', compositor, '--', '--study-spec', specPath, '--source-root', sourceRoot, '--composite-root', compositeRoot, '--display-root', displayRoot, '--report', compositeReportPath], { ...process.env, OCIO: ocioPath });
const compositeManifest = JSON.parse(await readFile(compositeReportPath, 'utf8'));
requireValue(compositeManifest.totalSourceBindings === 1872 && compositeManifest.totalCompositeFrames === 432 && compositeManifest.totalDisplayFrames === 432, 'B35 composite/export count mismatch');
let displayFramesDistinctFromB34 = 0;
for (const method of methods) for (let index = 0; index < 144; index += 1) {
  requireValue(compositeManifest.methods[method].outputs[index].displaySha256 !== b34Composite.methods[method].outputs[index].displaySha256, `B35 ${method} display frame ${index + 1} reused B34 identity`);
  displayFramesDistinctFromB34 += 1;
}

const carriers = [];
for (const method of methods) {
  const sourceDir = resolve(displayRoot, method), carrierPath = resolve(carrierRoot, `${method}.lossless.webm`), decodedDir = resolve(decodedRoot, method), roundtripPath = resolve(evidenceRoot, `${method}.roundtrip.json`);
  await mkdir(decodedDir);
  await run(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-framerate', '24', '-start_number', '1', '-i', resolve(sourceDir, 'frame-%04d.png'), '-an', '-c:v', 'libvpx-vp9', '-lossless', '1', '-pix_fmt', 'gbrp', '-row-mt', '0', '-threads', '1', '-tile-columns', '0', carrierPath]);
  await run(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-i', carrierPath, '-fps_mode', 'passthrough', resolve(decodedDir, 'frame-%04d.png')]);
  await run(blender, ['--factory-startup', '--background', '--disable-autoexec', '--python-exit-code', '1', '--python', verifier, '--', '--study-spec', specPath, '--source-dir', sourceDir, '--decoded-dir', decodedDir, '--display-manifest', compositeReportPath, '--method', method, '--output', roundtripPath]);
  const probeResult = await run(ffprobe, ['-v', 'error', '-show_entries', 'format=size,duration,format_name:stream=codec_name,profile,pix_fmt,width,height,r_frame_rate', '-of', 'json', carrierPath]);
  const probe = JSON.parse(probeResult.output), stream = probe.streams[0], format = probe.format, roundtrip = JSON.parse(await readFile(roundtripPath, 'utf8'));
  const item = { method, localUri: repoUri(carrierPath), sha256: await sha256File(carrierPath), bytes: Number(format.size), metadata: { codecName: stream.codec_name, profile: stream.profile, pixelFormat: stream.pix_fmt, width: stream.width, height: stream.height, frameRate: stream.r_frame_rate, durationSeconds: Number(format.duration), container: format.format_name }, roundtrip, roundtripReportUri: repoUri(roundtripPath), roundtripReportSha256: await sha256File(roundtripPath) };
  requireValue(roundtrip.exactRgbFrames === 144 && roundtrip.allSourceAlphaOpaque && roundtrip.maximumAbsoluteRgbError === 0 && roundtrip.totalChangedRgbPixels === 0, `${method} carrier exactness failed`);
  requireValue(item.sha256 !== b34Package.carriers.find(carrier => carrier.method === method).sha256, `${method} carrier reused B34 identity`);
  carriers.push(item); process.stdout.write(`BFS_B35_CARRIER_OK ${method} bytes=${item.bytes}\n`);
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
  const html = b35ObserverHtml({ version: spec.version, sessionId, studySpecSha256: specSha, mappingCommitment: commitment, visibleCarriers });
  await writeFile(resolve(dir, 'index.html'), html);
  publicSessions.push({ sessionId, mappingCommitment: commitment, observerPackageUri: repoUri(dir), observerHtmlSha256: digest(html), visibleCarrierBindings: visibleCarriers });
}
const sealedBody = { version: spec.version, sessions: sealedSessions }, sealed = { ...sealedBody, overallCommitment: sha256Canonical(sealedBody) };
const sealedPath = resolve(sealedRoot, 'mapping.sealed.json'); await writeFile(sealedPath, serialize(sealed));
let actualObserverPackageLeak = false, actualHtmlControlsSafe = true;
for (const session of publicSessions) {
  const dir = resolve(sessionRoot, session.sessionId), names = await readdir(dir), html = await readFile(resolve(dir, 'index.html'), 'utf8');
  if (names.some(name => /mapping|sealed/i.test(name)) || /NATURAL32|QUADRATURE4|STRATIFIED8|sourceLabel|permutation|github\.com\/lovejzzz|lovejzzz\.github\.io|BlenderFilmStudio\/experiments/i.test(html)) actualObserverPackageLeak = true;
  if (/<video[^>]+controls/i.test(html) || !html.includes('droppedVideoFramesDelta') || !html.includes("video.addEventListener('seeking'") || !html.includes("video.addEventListener('ratechange'")) actualHtmlControlsSafe = false;
}
const manifest = { documentType: 'BFS_B35_PRIVATE_HUMAN_REVIEW_PACKAGE', version: spec.version, createdAtUtc: new Date().toISOString(), packageStatus: 'PRIVATE_CARRIER_AND_INTERFACE_READY', disclosureStatus: 'PRIVATE_UNTIL_COLLECTION_CLOSE', studySpecSha256: specSha, source: spec.source, tools, visualRealization: spec.newVisualRealization, sourceProcessLedgerSha256: await sha256File(processLedgerPath), compositeDisplayManifestSha256: await sha256File(compositeReportPath), carriers, mappingCommitment: sealed.overallCommitment, mappingStatus: 'SEALED_LOCAL_NOT_PUBLISHED', sessions: publicSessions, humanReview: { status: 'HUMAN_REVIEW_PENDING', formalResponseCount: 0, pilotResponseCount: 0, decision: null }, nonClaims: spec.nonClaims };
const manifestPath = resolve(evidenceRoot, 'package.manifest.json'); await writeFile(manifestPath, serialize(manifest));

const sensitiveValues = await buildB35SensitiveRegistry({ privateEvidenceRoot: evidenceRoot, sealedPath, sessionRoot });
const registrySalt = randomBytes(32).toString('hex');
const registryCommitment = sha256Canonical({ salt: registrySalt, values: sensitiveValues });
const registryPath = resolve(sealedRoot, 'sensitive-hash-registry.sealed.json');
await writeFile(registryPath, serialize({ documentType: 'BFS_B35_SENSITIVE_HASH_REGISTRY', version: spec.version, salt: registrySalt, values: sensitiveValues, commitment: registryCommitment }));
const privateManifestSha256 = await sha256File(manifestPath), packageSalt = randomBytes(32).toString('hex');
const packageCommitment = sha256Canonical({ salt: packageSalt, privateManifestSha256 });
await writeFile(resolve(sealedRoot, 'package-commitment.sealed.json'), serialize({ documentType: 'BFS_B35_PRIVATE_PACKAGE_COMMITMENT_OPENING', version: spec.version, salt: packageSalt, privateManifestSha256, commitment: packageCommitment }));

function packageReason(overrides = {}) {
  const observed = {
    specSha, blenderSha: spec.runtime.blenderBinarySha256, schedule: cells,
    processIds: cells.map(cell => records.get(cell).report.processId), sourceOutputBinding: true,
    freeBytes, directoriesStartedEmpty: true, visualRealizationValid: true,
    displayFramesDistinctFromB34, carrierDistinctFromB34: carriers.every(item => item.sha256 !== b34Package.carriers.find(old => old.method === item.method).sha256),
    weights: [compositeManifest.methods.QUADRATURE4.weights, compositeManifest.methods.STRATIFIED8.weights],
    displayTransform: compositeManifest.observedDisplayTransform, displayFrameCount: compositeManifest.totalDisplayFrames,
    carrierMetadata: carriers.map(item => item.metadata), exactFrames: carriers.map(item => item.roundtrip.exactRgbFrames),
    permutationCounts: Object.fromEntries(permutations.map(item => [item.label, sealedSessions.filter(session => session.permutation === item.label).length])),
    observerPackageLeak: actualObserverPackageLeak, htmlControlsSafe: actualHtmlControlsSafe,
    publicContainsMethodCarrierHashes: false, currentPublicHead: null, auditedPublicHead: null,
    preAcceptAuditPass: true, unblindBeforeClose: false, ...overrides,
  };
  if (!observed.visualRealizationValid || observed.displayFramesDistinctFromB34 !== 432 || !observed.carrierDistinctFromB34) return 'VISUAL_REALIZATION';
  if (observed.specSha !== expectedSpecSha || observed.blenderSha !== spec.runtime.blenderBinarySha256) return 'SPEC_OR_RUNTIME';
  if (JSON.stringify(observed.schedule) !== JSON.stringify(cells)) return 'METHOD_SCHEDULE';
  if (new Set(observed.processIds).size !== 13 || !observed.sourceOutputBinding) return 'PROCESS_OR_OUTPUT';
  if (observed.freeBytes < spec.resourceGate.minimumFreeBytesBeforeRender || !observed.directoriesStartedEmpty) return 'RESOURCE_GATE';
  if (JSON.stringify(observed.weights) !== JSON.stringify([spec.renderDesign.quadrature4.weights, spec.renderDesign.stratified8.weights]) || observed.displayFrameCount !== 432 || sha256Canonical(observed.displayTransform) !== sha256Canonical({ display: spec.displayTransform.display, view: spec.displayTransform.view, look: spec.displayTransform.look, exposure: spec.displayTransform.exposure, gamma: spec.displayTransform.gamma, dither: spec.displayTransform.dither, output: spec.displayTransform.output })) return 'COMPOSITE_OR_DISPLAY';
  if (observed.carrierMetadata.some(item => item.codecName !== 'vp9' || item.profile !== 'Profile 1' || item.pixelFormat !== 'gbrp' || item.width !== 960 || item.height !== 540 || item.frameRate !== '24/1' || item.durationSeconds !== 6) || observed.exactFrames.some(value => value !== 144)) return 'CARRIER_OR_ROUNDTRIP';
  if (Object.values(observed.permutationCounts).some(value => value !== 3)) return 'SCHEDULE_BALANCE';
  if (observed.observerPackageLeak || !observed.htmlControlsSafe) return 'OBSERVER_PACKAGE_LEAK';
  if (observed.publicContainsMethodCarrierHashes) return 'PUBLIC_HASH_JOIN';
  if (observed.currentPublicHead && observed.auditedPublicHead && observed.currentPublicHead !== observed.auditedPublicHead) return 'STALE_PUBLIC_AUDIT';
  if (!observed.preAcceptAuditPass) return 'PREACCEPT_LEAK_AUDIT';
  if (observed.unblindBeforeClose) return 'PREMATURE_UNBLIND';
  return 'OK';
}

const attack = (name, expected, observed) => ({ name, expected, observed, pass: expected === observed });
const synthetic = syntheticResponse({ spec, specSha, manifest, sealed, sessionIndex: 0, observerId: 'SYNTH-01' });
const responseReason = override => validateB35Response({ spec, specSha, manifest, sealed, response: override }).reason;
const cleanAudit = await auditB35PublicState({ repositoryRoot, privateEvidenceRoot: evidenceRoot, sealedPath, sessionRoot, registryPath, publicRoots: [resolve(repositoryRoot, 'out')], requireCleanTrackedTree: true });
requireValue(cleanAudit.status === 'PUBLIC_STATE_LEAK_AUDIT_PASS', `B35 precollection public-state audit failed: ${JSON.stringify(cleanAudit.privateDetails)}`);
const attackPublicRoot = resolve(workRoot, 'attack-public-surface'); await mkdir(attackPublicRoot);
await writeFile(resolve(attackPublicRoot, 'leak.txt'), `${sensitiveValues[0]}\n`);
const injectedLeakAudit = await auditB35PublicState({ repositoryRoot, privateEvidenceRoot: evidenceRoot, sealedPath, sessionRoot, registryPath, publicRoots: [attackPublicRoot], requireCleanTrackedTree: true });

const acceptanceAttackRoot = resolve(workRoot, 'attack-response-immutability');
const acceptanceResponsePath = resolve(acceptanceAttackRoot, 'synthetic.response.json');
const acceptanceDir = resolve(acceptanceAttackRoot, 'accepted');
const acceptanceLedger = resolve(acceptanceAttackRoot, 'accepted-ledger.jsonl');
await mkdir(acceptanceAttackRoot); await writeFile(acceptanceResponsePath, serialize(synthetic));
const acceptanceArgs = [acceptor, '--response', acceptanceResponsePath, '--manifest', manifestPath, '--sealed', sealedPath, '--registry', registryPath, '--accepted-dir', acceptanceDir, '--ledger', acceptanceLedger];
await run(process.execPath, acceptanceArgs);
const mutationAttackObserved = await expectFailure(process.execPath, acceptanceArgs, 'RESPONSE_MUTATION_OR_DUPLICATE');
const formalFixtures = Array.from({ length: 18 }, (_, index) => syntheticResponse({ spec, specSha, manifest, sealed, sessionIndex: index, observerId: `SYNTH-${String(index + 1).padStart(2, '0')}`, q4Rating: 'SEVERE' }));
const formal = analyzeB35Responses({ spec, specSha, manifest, sealed, responses: formalFixtures });
const invalidHumanReasons = [
  responseReason((() => { const value = structuredClone(synthetic); value.playbackTelemetry[0].plays[0].droppedVideoFramesDelta = 1; value.responseHash = sha256Canonical(responseBody(value)); return value; })()),
  responseReason((() => { const value = structuredClone(synthetic); value.viewing.directDevelopmentInvolvement = 'YES'; value.responseHash = sha256Canonical(responseBody(value)); return value; })()),
  responseReason((() => { const value = structuredClone(synthetic); value.carrierBindings[0].sha256 = '2'.repeat(64); value.responseHash = sha256Canonical(responseBody(value)); return value; })()),
];
const attacks = [
  attack('old_realization_or_lens_intervention', 'VISUAL_REALIZATION', packageReason({ visualRealizationValid: false })),
  attack('wrong_spec_or_runtime_identity', 'SPEC_OR_RUNTIME', packageReason({ specSha: '0'.repeat(64) })),
  attack('changed_render_schedule', 'METHOD_SCHEDULE', packageReason({ schedule: cells.slice(1) })),
  attack('missing_or_duplicate_process_or_output', 'PROCESS_OR_OUTPUT', packageReason({ processIds: cells.map(() => records.get(cells[0]).report.processId) })),
  attack('insufficient_space_or_dirty_work', 'RESOURCE_GATE', packageReason({ freeBytes: 1 })),
  attack('changed_composite_or_display', 'COMPOSITE_OR_DISPLAY', packageReason({ displayFrameCount: 431 })),
  attack('carrier_metadata_or_roundtrip', 'CARRIER_OR_ROUNDTRIP', packageReason({ exactFrames: [143, 144, 144] })),
  attack('public_sensitive_registry_injection', 'PUBLIC_STATE_LEAK_AUDIT_FAIL', injectedLeakAudit.status),
  attack('public_method_to_carrier_join', 'PUBLIC_HASH_JOIN', packageReason({ publicContainsMethodCarrierHashes: true })),
  attack('observer_package_mapping_or_repository_leak', 'OBSERVER_PACKAGE_LEAK', packageReason({ observerPackageLeak: true })),
  attack('public_tree_changed_without_reaudit', 'STALE_PUBLIC_AUDIT', packageReason({ currentPublicHead: 'a', auditedPublicHead: 'b' })),
  attack('response_accept_without_same_state_audit', 'PREACCEPT_LEAK_AUDIT', packageReason({ preAcceptAuditPass: false })),
  attack('unblind_before_collection_close', 'PREMATURE_UNBLIND', packageReason({ unblindBeforeClose: true })),
  attack('invalid_human_telemetry_independence_or_binding', 'ALL_REJECTED', JSON.stringify(invalidHumanReasons) === JSON.stringify(['DROPPED_FRAME', 'OBSERVER_INDEPENDENCE', 'CARRIER_BINDING']) ? 'ALL_REJECTED' : 'NOT_ALL_REJECTED'),
  attack('response_mutation_or_formal_below_18', 'ALL_REJECTED', mutationAttackObserved === 'RESPONSE_MUTATION_OR_DUPLICATE' && analyzeB35Responses({ spec, specSha, manifest, sealed, responses: formalFixtures.slice(0, 17) }).status === 'FORMAL_REVIEW_INCOMPLETE' ? 'ALL_REJECTED' : 'NOT_ALL_REJECTED'),
  attack('q4_secondary_cannot_change_primary', spec.formalDecision.noDirectionalDifferenceLabel, formal.decision),
];
requireValue(attacks.length === spec.attacksRequired.length && attacks.every(item => item.pass), `B35 attacks failed: ${JSON.stringify(attacks.filter(item => !item.pass))}`);
requireValue(packageReason() === 'OK' && formal.status === 'FORMAL_REVIEW_COMPLETE', 'B35 private package or synthetic analyzer fixture failed');

const privateResult = {
  documentType: 'BFS_B35_PRIVATE_PACKAGE_RESULT', version: spec.version, experimentId: spec.experimentId, executedAtUtc: new Date().toISOString(),
  packageStatus: 'PRIVATE_CARRIER_AND_INTERFACE_READY', disclosureStatus: 'DELAYED_UNTIL_COLLECTION_CLOSE', validPackage: true,
  humanReview: { status: 'HUMAN_REVIEW_PENDING', formalResponseCount: 0, pilotResponseCount: 0, decision: null },
  identities: { studySpecSha256: specSha, sourceProcessLedgerSha256: await sha256File(processLedgerPath), compositeDisplayManifestSha256: await sha256File(compositeReportPath), privatePackageManifestSha256: privateManifestSha256, packageCommitment, sensitiveRegistryCommitment: registryCommitment, ...tools },
  execution: { freeBytesBeforeRender: freeBytes, uniqueBlenderSourceProcesses: 13, renderCalls: 1872, sourceExrFiles: 1872, compositeExrFiles: 432, displayPngFiles: 432 },
  realization: { originalLensMm: 50, intervenedLensMm: 52, displayFramesDistinctFromB34, carriersDistinctFromB34: 3 },
  carrierSummary: { count: 3, totalBytes: carriers.reduce((sum, item) => sum + item.bytes, 0), exactRgbFrames: 432, maximumAbsoluteRgbError: 0, totalChangedRgbPixels: 0 },
  schedule: { formalTarget: 18, permutations: 6, repetitionsPerPermutation: 3, mappingStatus: 'SEALED_LOCAL_NOT_PUBLISHED' },
  publicState: { status: cleanAudit.status, ...cleanAudit.publicSummary },
  attacks: { passed: attacks.length, total: attacks.length, cases: attacks },
  analyzerSyntheticFixture: { classification: 'ATTACK_TEST_ONLY_NOT_HUMAN_EVIDENCE', observedDecision: formal.decision, q4AllSevere: true, pass: formal.decision === spec.formalDecision.noDirectionalDifferenceLabel },
  nonClaims: spec.nonClaims,
};
await writeFile(resolve(workRoot, 'private-result.json'), serialize(privateResult));
const publicCommitment = {
  documentType: 'BFS_B35_PRECOLLECTION_COMMITMENT', version: spec.version, experimentId: spec.experimentId,
  createdAtUtc: new Date().toISOString(), status: 'PRIVATE_PACKAGE_VALIDATED_COLLECTION_NOT_OPEN',
  studySpecSha256: specSha, packageCommitment, sensitiveRegistryCommitment: registryCommitment,
  disclosure: 'No method-labelled output, carrier, decoded-frame, display-frame, mapping, session or response identity is disclosed before collection close.',
  counts: { uniqueBlenderProcesses: 13, renderCalls: 1872, sourceExrFiles: 1872, compositeExrFiles: 432, displayPngFiles: 432, losslessCarriers: 3, observerSessionsPrepared: 18, formalHumanResponses: 0 },
  engineeringGates: { newVisualRealization: 'PASS', sourceBlendByteUnchanged: true, allCarrierRgbExact: true, displayFramesDistinctFromB34: 432, carriersDistinctFromB34: 3, publicStateLeakAudit: cleanAudit.status, sensitiveMatchCount: 0, attacksPassed: attacks.length, attacksTotal: attacks.length },
  evidenceClasses: { engineering: 'MEASURED_FACT', human: 'PENDING', cinematic: 'NOT_TESTED' },
  nonClaims: spec.nonClaims,
};
await mkdir(experimentRoot, { recursive: true });
await writeFile(publicCommitmentPath, serialize(publicCommitment));
process.stdout.write(`BFS_B35_PRIVATE_PACKAGE_OK processes=13 renders=1872 carriers=3 rgbExact=true attacks=${attacks.length}/${attacks.length} sensitive=${sensitiveValues.length} human=0 disclosure=DELAYED\n`);
