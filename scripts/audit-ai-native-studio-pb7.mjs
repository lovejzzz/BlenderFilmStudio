#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { open, readFile, readdir, stat } from 'node:fs/promises';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT_URI = 'experiments/ai-native-studio-phase-b/PB.7-2026-08-31-human-review-attempt-01';
const PREREG_URI = 'specs/ai-native-studio-pb7-human-review-preregistration.v0.1.json';
const CORRECTION_URI = 'specs/ai-native-studio-pb7-human-review-preregistration-c1.v0.2.json';
const FREEZE_URI = 'specs/ai-native-studio-pb7-human-review-tool-freeze.v0.2.json';
const IDS = ['Q1', 'Q2', 'Q3', 'Q4'];
const ANSWERS = ['YES', 'NO', 'UNCERTAIN', 'UNVIEWABLE'];

function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, child]) => [key, sorted(child)]));
  return value;
}
const canonical = value => JSON.stringify(sorted(value));
const hashBytes = value => createHash('sha256').update(value).digest('hex');
const hashCanonical = value => hashBytes(canonical(value));
const hashFile = async path => hashBytes(await readFile(path));
const without = (value, field) => { const body = structuredClone(value); delete body[field]; return body; };
const validSelf = (value, field) => value?.[field] === hashCanonical(without(value, field));
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));

async function writeJson(path, body, field) {
  const record = { ...body, [field]: hashCanonical(body) };
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`); await handle.sync(); }
  finally { await handle.close(); }
  return record;
}

export function auditAnswerMapping(answers) {
  if (!answers || typeof answers !== 'object' || Array.isArray(answers)) throw new Error('ANSWERS_OBJECT');
  if (JSON.stringify(Object.keys(answers).sort()) !== JSON.stringify(IDS)) throw new Error('ANSWER_KEYS');
  const values = IDS.map(id => answers[id]);
  if (values.some(value => !ANSWERS.includes(value))) throw new Error('ANSWER_TOKEN');
  if (values.includes('NO')) return 'FAIL';
  if (values.every(value => value === 'YES')) return 'PASS';
  return 'BLOCKED';
}

async function exactInput(path, expected) {
  const s = await stat(path);
  return { uri: expected.uri, sha256: await hashFile(path), bytes: s.size };
}

export async function auditReview(argv = process.argv.slice(2)) {
  if (argv.length !== 2 || argv[0] !== '--evidence-root') throw new Error('USAGE');
  const root = resolve(repositoryRoot, argv[1]);
  if (relative(repositoryRoot, root) !== ROOT_URI) throw new Error('EVIDENCE_ROOT');
  if (JSON.stringify((await readdir(root)).sort()) !== JSON.stringify(['human-review.json'])) throw new Error('PRE_AUDIT_ROSTER');
  const preregPath = resolve(repositoryRoot, PREREG_URI), correctionPath = resolve(repositoryRoot, CORRECTION_URI), freezePath = resolve(repositoryRoot, FREEZE_URI);
  const prereg = await readJson(preregPath), correction = await readJson(correctionPath), freeze = await readJson(freezePath), reviewPath = resolve(root, 'human-review.json'), review = await readJson(reviewPath);
  const checks = [];
  const gate = (id, pass, detail) => checks.push({ id, pass: Boolean(pass), detail });

  gate('PREREGISTRATION_SELF_HASH', validSelf(prereg, 'specHash'), prereg.specHash);
  gate('CORRECTION_SELF_HASH', validSelf(correction, 'specHash'), correction.specHash);
  gate('TOOL_FREEZE_SELF_HASH', validSelf(freeze, 'specHash'), freeze.specHash);
  gate('REVIEW_SELF_HASH', validSelf(review, 'reviewHash'), review.reviewHash);
  gate('REVIEW_BINDING', review.preregistration?.specHash === prereg.specHash && review.correction?.specHash === correction.specHash && review.toolFreeze?.specHash === freeze.specHash, review.preregistration);
  gate('CORRECTION_SCOPE', correction.defect?.declaredValue === prereg.machineEvidence.independentAudit.receiptHash && correction.defect?.actualHistoricalJsonSelfHashField === 'auditHash' && Object.values(correction.correction).every(value => value === false || typeof value === 'string'), correction.defect);
  gate('RESPONSE_ORIGIN', review.responseOrigin === 'human-authored current-thread response' && review.modelAuthoredAnswerCount === 0 && review.normalizationApplied === false, review.responseOrigin);
  gate('SOURCE_MESSAGE_HASH', review.sourceMessageSha256 === hashBytes(Buffer.from(review.sourceMessageText, 'utf8')), review.sourceMessageSha256);
  const humanVerdict = auditAnswerMapping(review.answers);
  gate('ANSWER_MAPPING', ['PASS', 'FAIL', 'BLOCKED'].includes(humanVerdict), humanVerdict);
  gate('MACHINE_PASS', prereg.machineEvidence.status === 'PASS_FROZEN_BEFORE_HUMAN_RESPONSE', prereg.machineEvidence.status);

  const machinePaths = [
    ['receipt', prereg.machineEvidence.receipt],
    ['independentAudit', prereg.machineEvidence.independentAudit],
    ['sliceReceipt', prereg.machineEvidence.sliceReceipt],
    ['reviewVideo', prereg.machineEvidence.reviewVideo],
    ['contactSheet', prereg.machineEvidence.contactSheet],
  ];
  const machine = {};
  for (const [id, expected] of machinePaths) {
    const path = resolve(repositoryRoot, expected.uri);
    const actual = await exactInput(path, expected);
    const expectedSha = expected.fileSha256 ?? expected.sha256;
    gate(`MACHINE_${id.toUpperCase()}_HASH`, actual.sha256 === expectedSha, actual.sha256);
    if (expected.bytes !== undefined) gate(`MACHINE_${id.toUpperCase()}_BYTES`, actual.bytes === expected.bytes, actual.bytes);
    const declaredSelfHash = expected.receiptHash ?? expected.auditHash;
    if (declaredSelfHash) {
      const record = await readJson(path);
      const selfField = id === 'independentAudit' ? 'auditHash' : expected.auditHash ? 'auditHash' : 'receiptHash';
      gate(`MACHINE_${id.toUpperCase()}_SELF_HASH`, validSelf(record, selfField), record[selfField]);
      gate(`MACHINE_${id.toUpperCase()}_DECLARED_HASH`, record[selfField] === declaredSelfHash, declaredSelfHash);
      gate(`MACHINE_${id.toUpperCase()}_STATUS`, record.status === 'PASS', record.status);
    }
    machine[id] = actual;
  }
  gate('FRAME_288_BOUNDARY', prereg.machineEvidence.historicalFrame288Boundary.observed === 0.93378717684983 && prereg.machineEvidence.historicalFrame288Boundary.maximum === 0.9 && prereg.machineEvidence.historicalFrame288Boundary.mustRemainRejected === true, prereg.machineEvidence.historicalFrame288Boundary);
  const checkPassed = checks.filter(item => item.pass).length;
  if (checkPassed !== checks.length) throw new Error(`AUDIT_CHECKS_${checkPassed}_OF_${checks.length}`);
  const overallVerdict = humanVerdict === 'PASS' ? 'PASS' : humanVerdict === 'FAIL' ? 'FAIL' : 'BLOCKED';
  const audit = await writeJson(resolve(root, 'audit.json'), {
    schemaVersion: 'bfs.pb7HumanReviewAudit.v0.1', gate: 'PB.7', status: 'PASS',
    humanVerdict, overallVerdict, checkPassed, checkTotal: checks.length, checks,
    bindings: { preregistration: { uri: PREREG_URI, sha256: await hashFile(preregPath), specHash: prereg.specHash }, correction: { uri: CORRECTION_URI, sha256: await hashFile(correctionPath), specHash: correction.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await hashFile(freezePath), specHash: freeze.specHash }, humanReview: { uri: `${ROOT_URI}/human-review.json`, sha256: await hashFile(reviewPath), reviewHash: review.reviewHash }, machine },
    operationCounts: { engineSourceEdits: 0, engineCommits: 0, engineRemoteWrites: 0, nativeBuilds: 0, BlenderStarts: 0, renderCalls: 0, ffmpegProcesses: 0, networkCallsDuringReview: 0, modelCallsToAnswerQuestions: 0 },
  }, 'auditHash');
  const verdict = await writeJson(resolve(root, 'verdict.json'), {
    schemaVersion: 'bfs.pb7BoundedPrototypeVerdict.v0.1', gate: 'PB.7', verdict: overallVerdict,
    machineVerdict: 'PASS', humanVerdict, answers: review.answers, optionalNotes: review.optionalNotes,
    humanReview: { sha256: await hashFile(reviewPath), reviewHash: review.reviewHash },
    audit: { sha256: await hashFile(resolve(root, 'audit.json')), auditHash: audit.auditHash, checks: `${audit.checkPassed}/${audit.checkTotal}` },
    claimCeiling: prereg.claimCeiling,
  }, 'verdictHash');
  const manifestEntries = [];
  for (const name of ['human-review.json', 'audit.json', 'verdict.json']) {
    const path = resolve(root, name); const s = await stat(path);
    manifestEntries.push({ path: name, sha256: await hashFile(path), bytes: s.size });
  }
  const manifest = await writeJson(resolve(root, 'root-manifest.json'), { schemaVersion: 'bfs.pb7HumanReviewRootManifest.v0.1', gate: 'PB.7', entries: manifestEntries }, 'manifestHash');
  process.stdout.write(`BFS_PB7_AUDIT ${overallVerdict} ${audit.checkPassed}/${audit.checkTotal} ${verdict.verdictHash} ${manifest.manifestHash}\n`);
  return { audit, verdict, manifest };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  auditReview().catch(error => { process.stderr.write(`BFS_PB7_AUDIT_REJECTED ${error.message}\n`); process.exitCode = 1; });
}
