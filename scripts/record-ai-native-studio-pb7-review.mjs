#!/usr/bin/env node
import { open, mkdir, readFile, realpath, stat } from 'node:fs/promises';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  canonicalJson,
  sha256Bytes,
  sha256Canonical,
  sha256File,
  validateHumanInput,
  validSelfHash,
} from './lib/ai-native-studio-pb7.mjs';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const EXPECTED_ROOT_URI = 'experiments/ai-native-studio-phase-b/PB.7-2026-08-31-human-review-attempt-01';
const EXPECTED_PREREG_URI = 'specs/ai-native-studio-pb7-human-review-preregistration.v0.1.json';
const EXPECTED_CORRECTION_URI = 'specs/ai-native-studio-pb7-human-review-preregistration-c1.v0.2.json';
const EXPECTED_FREEZE_URI = 'specs/ai-native-studio-pb7-human-review-tool-freeze.v0.2.json';

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (!key?.startsWith('--') || argv[index + 1] === undefined) throw new Error('USAGE');
    result[key.slice(2)] = argv[index + 1];
  }
  if (!result.input || !result['evidence-root'] || !result['captured-at']) throw new Error('USAGE');
  return result;
}

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

async function writeExclusiveJson(path, body, hashField) {
  const record = { ...body, [hashField]: sha256Canonical(body) };
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`);
    await handle.sync();
  } finally {
    await handle.close();
  }
  return record;
}

async function assertToolFreeze(freeze) {
  if (!validSelfHash(freeze, 'specHash') || freeze.status !== 'FROZEN_BEFORE_HUMAN_RESPONSE') throw new Error('TOOL_FREEZE');
  for (const tool of freeze.tools) {
    if (await sha256File(resolve(repositoryRoot, tool.uri)) !== tool.sha256) throw new Error(`TOOL_HASH_${tool.uri}`);
  }
}

export async function recordReview(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  const capturedAt = new Date(args['captured-at']);
  if (!Number.isFinite(capturedAt.valueOf()) || capturedAt.toISOString() !== args['captured-at']) throw new Error('CAPTURED_AT');
  const preregPath = resolve(repositoryRoot, EXPECTED_PREREG_URI);
  const correctionPath = resolve(repositoryRoot, EXPECTED_CORRECTION_URI);
  const freezePath = resolve(repositoryRoot, EXPECTED_FREEZE_URI);
  const prereg = await readJson(preregPath);
  const correction = await readJson(correctionPath);
  const freeze = await readJson(freezePath);
  if (!validSelfHash(prereg, 'specHash') || prereg.status !== 'PREREGISTERED_BEFORE_HUMAN_RESPONSE') throw new Error('PREREGISTRATION');
  if (freeze.preregistration.specHash !== prereg.specHash || freeze.preregistration.sha256 !== await sha256File(preregPath)) throw new Error('FREEZE_PREREGISTRATION');
  if (!validSelfHash(correction, 'specHash') || correction.status !== 'FROZEN_BEFORE_HUMAN_RESPONSE') throw new Error('CORRECTION');
  if (freeze.correction.specHash !== correction.specHash || freeze.correction.sha256 !== await sha256File(correctionPath)) throw new Error('FREEZE_CORRECTION');
  await assertToolFreeze(freeze);

  const evidenceRoot = resolve(repositoryRoot, args['evidence-root']);
  if (relative(repositoryRoot, evidenceRoot) !== EXPECTED_ROOT_URI) throw new Error('EVIDENCE_ROOT');
  const evidenceParent = await realpath(dirname(evidenceRoot));
  if (evidenceParent !== resolve(repositoryRoot, 'experiments/ai-native-studio-phase-b')) throw new Error('EVIDENCE_PARENT');
  try {
    await stat(evidenceRoot);
    throw new Error('EVIDENCE_ROOT_EXISTS');
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }

  const inputPath = resolve(args.input);
  const inputBytes = await readFile(inputPath);
  const input = JSON.parse(inputBytes.toString('utf8'));
  const validation = validateHumanInput(input);
  if (!validation.valid) throw new Error(validation.reason);
  await mkdir(evidenceRoot, { recursive: false, mode: 0o700 });
  const body = {
    schemaVersion: 'bfs.pb7HumanReviewReceipt.v0.1',
    status: 'RECORDED_UNMODIFIED_ALLOWED_TOKENS',
    gate: 'PB.7',
    capturedAt: capturedAt.toISOString(),
    reviewerRole: input.reviewerRole,
    responseOrigin: 'human-authored current-thread response',
    sourceMessageText: input.sourceMessageText,
    sourceMessageSha256: sha256Bytes(Buffer.from(input.sourceMessageText, 'utf8')),
    answers: input.answers,
    optionalNotes: input.optionalNotes,
    inputFileSha256: sha256Bytes(inputBytes),
    preregistration: { uri: EXPECTED_PREREG_URI, sha256: await sha256File(preregPath), specHash: prereg.specHash },
    correction: { uri: EXPECTED_CORRECTION_URI, sha256: await sha256File(correctionPath), specHash: correction.specHash },
    toolFreeze: { uri: EXPECTED_FREEZE_URI, sha256: await sha256File(freezePath), specHash: freeze.specHash },
    media: prereg.machineEvidence.reviewVideo,
    modelAuthoredAnswerCount: 0,
    normalizationApplied: false,
  };
  const receipt = await writeExclusiveJson(resolve(evidenceRoot, 'human-review.json'), body, 'reviewHash');
  process.stdout.write(`BFS_PB7_REVIEW_RECORDED ${receipt.reviewHash}\n`);
  return receipt;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  recordReview().catch(error => { process.stderr.write(`BFS_PB7_REVIEW_REJECTED ${error.message}\n`); process.exitCode = 1; });
}
