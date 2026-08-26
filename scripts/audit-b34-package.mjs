import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1');
const evidenceRoot = resolve(experimentRoot, 'evidence');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.1.json');
const resultPath = resolve(experimentRoot, 'results.json');
const manifestPath = resolve(evidenceRoot, 'package.manifest.json');
const ledgerPath = resolve(evidenceRoot, 'source-process-ledger.json');
const compositePath = resolve(evidenceRoot, 'composite-display.manifest.json');
const sealedPath = resolve(workRoot, 'sealed/mapping.sealed.json');
const outputIndex = process.argv.indexOf('--output');
const outputPath = resolve(outputIndex === -1 ? resolve(evidenceRoot, 'independent-package-audit.json') : process.argv[outputIndex + 1]);
const expectedSpecSha = '4afcb29f9d47671d4696d0b6d57f5d7e0c5fde4f08bee1e414040ed480257ba2';
const cells = ['NATURAL32', ...Array.from({ length: 4 }, (_, index) => `Q4_${index + 1}`), ...Array.from({ length: 8 }, (_, index) => `Q8_${index + 1}`)];
const methods = ['NATURAL32', 'QUADRATURE4', 'STRATIFIED8'];
const fail = message => { throw new Error(message); };
const requireValue = (condition, message) => { if (!condition) fail(message); };
const json = async path => JSON.parse(await readFile(path, 'utf8'));

const [spec, result, manifest, ledger, composite, sealed] = await Promise.all([specPath, resultPath, manifestPath, ledgerPath, compositePath, sealedPath].map(json));
const specSha = await sha256File(specPath);
requireValue(specSha === expectedSpecSha && result.identities.studySpecSha256 === specSha && manifest.studySpecSha256 === specSha, 'spec binding mismatch');
requireValue(result.packageStatus === 'CARRIER_AND_INTERFACE_READY' && result.validPackage === true && result.humanReview.status === 'HUMAN_REVIEW_PENDING' && result.humanReview.formalResponseCount === 0, 'result classification mismatch');
requireValue(await sha256File(ledgerPath) === result.identities.sourceProcessLedgerSha256 && await sha256File(compositePath) === result.identities.compositeDisplayManifestSha256 && await sha256File(manifestPath) === result.identities.packageManifestSha256, 'top-level artifact binding mismatch');
requireValue(ledger.processes.length === 13 && new Set(ledger.processes.map(item => item.processId)).size === 13 && JSON.stringify(ledger.processes.map(item => item.cell)) === JSON.stringify(cells), 'process ledger mismatch');

let sourceFiles = 0, sourceBytes = 0;
for (const cell of cells) {
  const cellManifestPath = resolve(evidenceRoot, `${cell}.manifest.json`), cellManifest = await json(cellManifestPath);
  requireValue(cellManifest.manifestHash === sha256Canonical(Object.fromEntries(Object.entries(cellManifest).filter(([key]) => key !== 'manifestHash'))), `${cell} manifest canonical hash mismatch`);
  requireValue(cellManifest.outputs.length === 144 && cellManifest.outputs.every((item, index) => item.frame === index + 1 && item.name === `frame-${String(index + 1).padStart(4, '0')}.exr`), `${cell} frame schedule mismatch`);
  for (const item of cellManifest.outputs) {
    const path = resolve(repositoryRoot, item.fileUri);
    requireValue(await sha256File(path) === item.sha256, `${cell} source EXR hash mismatch at frame ${item.frame}`);
    sourceFiles += 1; sourceBytes += item.bytes;
  }
}
requireValue(sourceFiles === 1872, 'source EXR count mismatch');

let compositeFiles = 0, displayFiles = 0;
for (const method of methods) {
  const record = composite.methods[method];
  requireValue(record.frameCount === 144 && record.outputs.length === 144, `${method} composite count mismatch`);
  for (const item of record.outputs) {
    const compositeFile = resolve(workRoot, 'composites', method, item.compositeName), displayFile = resolve(workRoot, 'display', method, item.displayName);
    requireValue(await sha256File(compositeFile) === item.compositeSha256, `${method} composite hash mismatch at frame ${item.frame}`);
    requireValue(await sha256File(displayFile) === item.displaySha256, `${method} display hash mismatch at frame ${item.frame}`);
    requireValue(item.sources.length === record.cells.length && item.sources.every((source, index) => source.cell === record.cells[index] && source.weight === record.weights[index]), `${method} source binding mismatch at frame ${item.frame}`);
    compositeFiles += 1; displayFiles += 1;
  }
}
requireValue(compositeFiles === 432 && displayFiles === 432 && composite.totalSourceBindings === 1872, 'composite/display totals mismatch');

let roundtripFrames = 0, changedPixels = 0;
for (const carrier of manifest.carriers) {
  const carrierPath = resolve(repositoryRoot, carrier.localUri), roundtripPath = resolve(repositoryRoot, carrier.roundtripReportUri), roundtrip = await json(roundtripPath);
  requireValue(await sha256File(carrierPath) === carrier.sha256 && await sha256File(roundtripPath) === carrier.roundtripReportSha256, `${carrier.method} carrier/report hash mismatch`);
  requireValue(carrier.metadata.codecName === 'vp9' && carrier.metadata.profile === 'Profile 1' && carrier.metadata.pixelFormat === 'gbrp' && carrier.metadata.width === 960 && carrier.metadata.height === 540 && carrier.metadata.frameRate === '24/1' && carrier.metadata.durationSeconds === 6, `${carrier.method} carrier metadata mismatch`);
  requireValue(roundtrip.frameCount === 144 && roundtrip.exactRgbFrames === 144 && roundtrip.maximumAbsoluteRgbError === 0 && roundtrip.totalChangedRgbPixels === 0 && roundtrip.allSourceAlphaOpaque === true, `${carrier.method} roundtrip summary mismatch`);
  for (const item of roundtrip.frames) {
    const source = resolve(workRoot, 'display', carrier.method, item.sourceName), decoded = resolve(workRoot, 'decoded', carrier.method, item.sourceName);
    requireValue(await sha256File(source) === item.sourceSha256 && await sha256File(decoded) === item.decodedSha256 && item.rgbExact === true && item.changedRgbPixels === 0, `${carrier.method} roundtrip frame mismatch at ${item.frame}`);
    roundtripFrames += 1; changedPixels += item.changedRgbPixels;
  }
}
requireValue(roundtripFrames === 432 && changedPixels === 0, 'roundtrip totals mismatch');

requireValue(sealed.sessions.length === 18 && manifest.sessions.length === 18, 'session count mismatch');
const sealedBody = { version: sealed.version, sessions: sealed.sessions };
requireValue(sha256Canonical(sealedBody) === sealed.overallCommitment && manifest.mappingCommitment === sealed.overallCommitment, 'overall mapping commitment mismatch');
const permutationCounts = {};
for (const session of sealed.sessions) permutationCounts[session.permutation] = (permutationCounts[session.permutation] || 0) + 1;
requireValue(Object.keys(permutationCounts).length === 6 && Object.values(permutationCounts).every(value => value === 3), 'permutation balance mismatch');
for (const publicSession of manifest.sessions) {
  const sealedSession = sealed.sessions.find(item => item.sessionId === publicSession.sessionId);
  requireValue(sealedSession && sha256Canonical({ sessionId: sealedSession.sessionId, salt: sealedSession.salt, mapping: sealedSession.mapping }) === publicSession.mappingCommitment, `${publicSession.sessionId} commitment mismatch`);
  const dir = resolve(repositoryRoot, publicSession.observerPackageUri), names = await readdir(dir), htmlPath = resolve(dir, 'index.html'), html = await readFile(htmlPath, 'utf8');
  requireValue(await sha256File(htmlPath) === publicSession.observerHtmlSha256 && !names.some(name => /mapping|sealed/i.test(name)), `${publicSession.sessionId} package binding mismatch`);
  requireValue(!/NATURAL32|QUADRATURE4|STRATIFIED8|sourceLabel|permutation|<video[^>]+controls/i.test(html), `${publicSession.sessionId} mapping/control exposure`);
  for (const binding of publicSession.visibleCarrierBindings) requireValue(await sha256File(resolve(dir, binding.file)) === binding.sha256, `${publicSession.sessionId} visible carrier mismatch`);
}

const audit = {
  documentType: 'BFS_B34_INDEPENDENT_PACKAGE_AUDIT', version: spec.version,
  auditedAtUtc: new Date().toISOString(), status: 'PACKAGE_AUDIT_PASS',
  studySpecSha256: specSha, resultSha256: await sha256File(resultPath),
  packageManifestSha256: await sha256File(manifestPath), sourceProcessLedgerSha256: await sha256File(ledgerPath),
  compositeDisplayManifestSha256: await sha256File(compositePath),
  observations: { uniqueProcessIds: 13, sourceExrFiles: sourceFiles, sourceBytes, compositeExrFiles: compositeFiles, displayPngFiles: displayFiles, carrierFiles: 3, exactRoundtripFrames: roundtripFrames, changedRgbPixels, observerSessions: 18, permutationCounts, sealedMappingNotInObserverPackages: true, formalHumanResponses: 0 },
  nonClaim: 'This audits bytes, bindings, balance and package boundaries. It is not a human observation or a perceptual result.',
};
await writeFile(outputPath, `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B34_INDEPENDENT_PACKAGE_AUDIT_PASS source=${sourceFiles} composites=${compositeFiles} display=${displayFiles} roundtrip=${roundtripFrames} sessions=18 human=0\n`);
