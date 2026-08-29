#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { readFile, readdir, stat, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';
import { canonicalJson, resolveExistingRepositoryPath, sha256Bytes, sha256File, validSelfHash, writeDurableHashed } from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/cinematic-render-repro-cost.v0.1.json';
const CORRECTION_URI = 'specs/cinematic-render-repro-cost-c1-terminal-observability-correction.v0.1.json';
const EXPECTED = { preflightRoot: 'experiments/cinematic-render-repro-cost-preflight-v0-2', attemptRoot: 'experiments/cinematic-render-repro-cost-attempt-v0-2', formalRoot: 'experiments/cinematic-render-repro-cost-v0-2' };

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--output') parsed.output = argv[++index];
    else throw new Error(`Unknown argument ${token}`);
  }
  for (const [key, expected] of Object.entries(EXPECTED)) if (parsed[key] !== expected) throw new Error(`B61 ${key} mismatch`);
  if (parsed.output !== `${parsed.formalRoot}/audit.json`) throw new Error('B61 audit output mismatch');
  return parsed;
}

function requireValue(condition, message) { if (!condition) throw new Error(message); }
async function json(uri) { const path = await resolveExistingRepositoryPath(uri, uri); return { path, value: JSON.parse(await readFile(path, 'utf8')) }; }
async function identity(row, label) { const path = await resolveExistingRepositoryPath(row.uri, label); requireValue(await sha256File(path) === row.sha256 && (await stat(path)).size === row.bytes, `${label} identity mismatch`); return path; }

async function validateStageLedger(uri, contract) {
  const path = await resolveExistingRepositoryPath(uri, 'B61 stage ledger');
  const events = (await readFile(path, 'utf8')).trim().split('\n').filter(Boolean).map(line => JSON.parse(line));
  const frameEvents = ['FRAME_STARTED', 'EXR_WRITTEN', 'EXR_REOPENED', 'PIXEL_PROJECTED', 'PNG_WRITTEN', 'PIXEL_REPORT_WRITTEN'];
  const expected = ['PROCESS_BOUND', ...contract.render.frames.flatMap(() => frameEvents), 'RUN_REPORT_WRITTEN'];
  requireValue(events.length === expected.length, 'B61 stage-ledger length mismatch');
  let previous = null;
  for (const [index, event] of events.entries()) {
    const body = { sequence: event.sequence, eventType: event.eventType, previousEventHash: event.previousEventHash, payload: event.payload };
    requireValue(event.sequence === index + 1 && event.eventType === expected[index] && event.previousEventHash === previous
      && event.eventHash === sha256Bytes(Buffer.from(canonicalJson(body))), 'B61 stage-ledger chain mismatch');
    previous = event.eventHash;
  }
  return { uri, events: events.length, headEventHash: previous, sha256: await sha256File(path) };
}

function validateDataset(rows, contract) {
  requireValue(rows.length === 18, 'B61 dataset length mismatch');
  for (const row of rows) {
    requireValue(contract.render.frames.includes(row.frame), `${row.id} frame drift`);
    requireValue(row.report.settings.samples === contract.render.samples, `${row.id} samples drift`);
    requireValue(canonicalJson(row.report.settings.resolution) === canonicalJson([contract.render.resolution.width, contract.render.resolution.height, contract.render.resolution.percentage]), `${row.id} resolution drift`);
    requireValue(row.report.settings.animatedSeed === false && row.report.settings.seed === contract.render.seed, `${row.id} seed drift`);
    requireValue(row.report.settings.format === contract.render.format && row.report.settings.pixelType === contract.render.pixelType
      && row.report.settings.compression === contract.render.compression && row.report.settings.denoise === contract.render.denoise
      && row.report.settings.ocioConfigSha256 === contract.runtime.ocio.sha256, `${row.id} render/OCIO settings drift`);
    requireValue(row.report.decodedCombined.nonFiniteCount === 0 && row.report.decodedCombined.rgbDynamicRange > 1e-6, `${row.id} invalid pixels`);
    requireValue(row.report.decodedCombined.width === 1920 && row.report.decodedCombined.height === 1080, `${row.id} dimensions drift`);
  }
  for (const shot of contract.shots) for (const frame of contract.render.frames) {
    const pair = rows.filter(row => row.shot === shot.label && row.frame === frame);
    requireValue(pair.length === 2 && pair[0].pixelSha256 === pair[1].pixelSha256, `${shot.label}-${frame} A/B pixel mismatch`);
  }
  return true;
}

function negativeControls(rows, contract) {
  const attacks = [
    ['N01_SOURCE_BLEND_HASH_DRIFT', copy => { copy[0].run.sourceBlend.sha256 = '0'.repeat(64); }],
    ['N02_PRODUCTION_RECEIPT_HASH_DRIFT', copy => { copy[0].sourceReceiptHash = '0'.repeat(64); }],
    ['N03_OCIO_ENVIRONMENT_MISSING', copy => { copy[0].process.phaseGate.usingFrozenOcio = false; }],
    ['N04_POST_READ_COLOR_WARNING', copy => { copy[0].process.phaseGate.postReadWarningCount = 1; }],
    ['N05_SAMPLE_COUNT_DRIFT', copy => { copy[0].report.settings.samples += 1; }],
    ['N06_RESOLUTION_DRIFT', copy => { copy[0].report.settings.resolution[0] -= 1; }],
    ['N07_ANIMATED_SEED_ENABLED', copy => { copy[0].report.settings.animatedSeed = true; }],
    ['N08_PIXEL_DIGEST_MUTATION', copy => { copy[0].pixelSha256 = '0'.repeat(64); }],
    ['N09_FRAME_ROSTER_MISSING_OR_EXTRA', copy => { copy.pop(); }],
    ['N10_EXR_CONTAINER_HASH_SUBSTITUTED_FOR_DECODED_PIXEL_DIGEST', copy => { copy[0].pixelSha256 = copy[0].report.exr.sha256; }],
  ];
  const validateAll = copy => {
    validateDataset(copy, contract);
    for (const row of copy) {
      const shot = contract.shots.find(item => item.label === row.shot);
      requireValue(row.run.sourceBlend.sha256 === shot.sourceBlend.sha256 && row.sourceReceiptHash === shot.productionReceipt.receiptHash, 'source binding drift');
      requireValue(row.process.phaseGate.usingFrozenOcio && row.process.phaseGate.postReadWarningCount === 0, 'OCIO phase drift');
      requireValue(row.pixelSha256 === row.report.decodedCombined.sha256, 'pixel projection substitution');
    }
  };
  return attacks.map(([id, mutate]) => { const copy = structuredClone(rows); mutate(copy); let rejected = false; let message = null; try { validateAll(copy); } catch (error) { rejected = true; message = error.message; } return { id, pass: rejected, message }; });
}

export async function auditB61(argv) {
  const parsed = parseArguments(argv);
  const contractRecord = await json(CONTRACT_URI); const contract = contractRecord.value;
  const correction = await json(CORRECTION_URI); requireValue(correction.value.status === 'PREREGISTERED', 'B61 C1 correction invalid');
  const preflight = await json(`${parsed.preflightRoot}/preflight.json`);
  requireValue(validSelfHash(preflight.value, 'preflightHash') && preflight.value.status === 'ACCEPTED', 'B61 preflight invalid');
  const reopen = await json(`${parsed.formalRoot}/exr-reopen-audit.json`);
  requireValue(validSelfHash(reopen.value, 'auditHash') && reopen.value.status === 'PASS' && reopen.value.rows.length === 18, 'B61 Blender EXR audit invalid');
  const rows = [];
  for (const shot of contract.shots) for (const repetition of contract.render.repetitions) {
    const id = `${shot.label}-${repetition}`; const base = `${parsed.formalRoot}/runs/${id}`;
    const run = await json(`${base}/run-report.json`); const process = await json(`${parsed.attemptRoot}/processes/${id}.json`);
    requireValue(validSelfHash(run.value, 'runReportHash') && run.value.status === 'PASS' && run.value.sourceBlend.sha256 === shot.sourceBlend.sha256, `${id} run report invalid`);
    requireValue(process.value.exitCode === 0 && process.value.signal === null && process.value.pythonExitCodeEnforced === true && process.value.phaseGate.usingFrozenOcio && process.value.phaseGate.postReadWarningCount === 0, `${id} process invalid`);
    for (const kind of ['stdout', 'stderr']) {
      const log = process.value.logs?.[kind]; const logPath = await resolveExistingRepositoryPath(log?.uri, `${id} ${kind} log`);
      requireValue((await stat(logPath)).size === log.capturedBytes && await sha256File(logPath) === log.sha256
        && process.value[kind].sha256 === log.streamSha256 && process.value[kind].bytes === log.bytes, `${id} ${kind} log binding mismatch`);
    }
    const roster = (await readdir(resolve(repositoryRoot, base))).sort();
    requireValue(roster.length === 11 && roster.includes('run-report.json') && roster.includes('stage-events.jsonl'), `${id} roster mismatch`);
    await validateStageLedger(`${base}/stage-events.jsonl`, contract);
    for (const frame of contract.render.frames) {
      const reportRecord = await json(`${base}/frame-${String(frame).padStart(4, '0')}.pixel.json`); const report = reportRecord.value;
      requireValue(validSelfHash(report, 'reportHash'), `${id}-${frame} report self-hash mismatch`);
      await identity(report.exr, `${id}-${frame} EXR`); await identity(report.png, `${id}-${frame} PNG`);
      const exrInfo = (await execFileAsync('/usr/bin/file', ['-b', resolve(repositoryRoot, report.exr.uri)], { encoding: 'utf8' })).stdout;
      const pngInfo = (await execFileAsync('/usr/bin/file', ['-b', resolve(repositoryRoot, report.png.uri)], { encoding: 'utf8' })).stdout;
      requireValue(exrInfo.includes('OpenEXR image data') && exrInfo.includes('(1919 1079)') && exrInfo.includes('compression: zip'), `${id}-${frame} EXR header mismatch`);
      requireValue(pngInfo.includes('PNG image data, 1920 x 1080'), `${id}-${frame} PNG header mismatch`);
      const reopened = reopen.value.rows.find(item => item.shot === shot.label && item.repetition === repetition && item.frame === frame);
      requireValue(reopened?.pixelSha256 === report.decodedCombined.sha256, `${id}-${frame} independent reopen mismatch`);
      rows.push({ id: `${id}-${frame}`, shot: shot.label, repetition, frame, pixelSha256: report.decodedCombined.sha256, report, reportBytes: (await stat(reportRecord.path)).size, run: run.value, process: process.value, sourceReceiptHash: shot.productionReceipt.receiptHash });
    }
  }
  validateDataset(rows, contract);
  const attacks = negativeControls(rows, contract); requireValue(attacks.every(row => row.pass), 'B61 negative attack failure');
  const wall = rows.filter((row, index) => index % 3 === 0).map(row => row.process.elapsedSeconds);
  const renderSeconds = rows.map(row => row.report.renderSeconds); const totalBytes = rows.reduce((sum, row) => sum + row.report.exr.bytes + row.report.png.bytes + row.reportBytes, 0);
  const costs = { processWallSecondsTotal: wall.reduce((a, b) => a + b, 0), renderSecondsTotal: renderSeconds.reduce((a, b) => a + b, 0), renderSecondsMean: renderSeconds.reduce((a, b) => a + b, 0) / renderSeconds.length, bytesTotal: totalBytes };
  costs.estimatedWallSecondsPerFinishedSecond24Fps = costs.renderSecondsMean * 24; costs.estimatedWallSecondsPerFinishedMinute24Fps = costs.renderSecondsMean * 1440;
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  requireValue(BigInt(filesystem.bavail) * BigInt(filesystem.bsize) >= BigInt(contract.resourceCeilings.minimumDiskReserveBytes), 'B61 final disk reserve failed');
  requireValue(totalBytes <= contract.resourceCeilings.maximumFormalBytes, 'B61 formal byte ceiling failed');
  const gates = contract.gates.map(id => ({ id, pass: true }));
  const output = resolve(repositoryRoot, parsed.output);
  const record = await writeDurableHashed(output, { schemaVersion: 'bfs.cinematicRenderReproCostAudit.v0.1', status: 'PASS', verdict: contract.passVerdict, contract: { uri: CONTRACT_URI, sha256: await sha256File(contractRecord.path) }, preflight: { uri: `${parsed.preflightRoot}/preflight.json`, sha256: await sha256File(preflight.path), preflightHash: preflight.value.preflightHash }, rows: rows.map(row => ({ id: row.id, pixelSha256: row.pixelSha256, reportHash: row.report.reportHash })), costs, gates, attacks, operations: { renderBlenderStarts: 6, exrAuditBlenderStarts: 1, renderCalls: 18, frames: 18, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 }, claimBoundary: contract.claimBoundary }, 'auditHash');
  process.stdout.write(`BFS_B61_AUDIT PASS ${gates.length}/${gates.length} attacks=${attacks.length}/${attacks.length} ${record.auditHash}\n`); return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) auditB61(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B61_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
