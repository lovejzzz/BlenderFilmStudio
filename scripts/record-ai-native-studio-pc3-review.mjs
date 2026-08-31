#!/usr/bin/env node
import { mkdir, open, readFile, realpath, stat } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { sha256Bytes, sha256Canonical, sha256File, validateHumanInput, validSelfHash } from './lib/ai-native-studio-pc3-review.mjs';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT_URI = 'experiments/ai-native-studio-post-pb7/PC.3-2026-08-31-human-review-attempt-01';
const PREREG_URI = 'specs/ai-native-studio-pc3-integrated-review-preregistration.v0.1.json';
const FREEZE_URI = 'specs/ai-native-studio-pc3-human-review-tool-freeze.v0.1.json';
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
async function writeJson(path, body, field) { const record = { ...body, [field]: sha256Canonical(body) }; const handle = await open(path, 'wx', 0o600); try { await handle.writeFile(`${JSON.stringify(record, null, 2)}\n`); await handle.sync(); } finally { await handle.close(); } return record; }
function parseArgs(argv) { const out = {}; for (let i = 0; i < argv.length; i += 2) { if (!argv[i]?.startsWith('--') || argv[i + 1] === undefined) throw new Error('USAGE'); out[argv[i].slice(2)] = argv[i + 1]; } if (!out.input || !out['evidence-root'] || !out['captured-at']) throw new Error('USAGE'); return out; }

export async function recordReview(argv = process.argv.slice(2)) {
  const args = parseArgs(argv), capturedAt = new Date(args['captured-at']);
  if (!Number.isFinite(capturedAt.valueOf()) || capturedAt.toISOString() !== args['captured-at']) throw new Error('CAPTURED_AT');
  const preregPath = resolve(repositoryRoot, PREREG_URI), freezePath = resolve(repositoryRoot, FREEZE_URI), prereg = await readJson(preregPath), freeze = await readJson(freezePath);
  if (!validSelfHash(prereg, 'specHash') || prereg.status !== 'PREREGISTERED_BEFORE_PC3_RENDER') throw new Error('PREREGISTRATION');
  if (!validSelfHash(freeze, 'specHash') || freeze.status !== 'FROZEN_BEFORE_HUMAN_RESPONSE' || freeze.preregistration.specHash !== prereg.specHash || freeze.preregistration.sha256 !== await sha256File(preregPath)) throw new Error('TOOL_FREEZE');
  for (const tool of freeze.tools) if (await sha256File(resolve(repositoryRoot, tool.uri)) !== tool.sha256) throw new Error(`TOOL_HASH_${tool.uri}`);
  for (const item of Object.values(freeze.machineEvidence)) if (item.uri && await sha256File(resolve(repositoryRoot, item.uri)) !== item.sha256) throw new Error(`MACHINE_HASH_${item.uri}`);
  const evidenceRoot = resolve(repositoryRoot, args['evidence-root']);
  if (relative(repositoryRoot, evidenceRoot) !== ROOT_URI || await realpath(dirname(evidenceRoot)) !== resolve(repositoryRoot, 'experiments/ai-native-studio-post-pb7')) throw new Error('EVIDENCE_ROOT');
  try { await stat(evidenceRoot); throw new Error('EVIDENCE_ROOT_EXISTS'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const inputPath = resolve(args.input), inputBytes = await readFile(inputPath), input = JSON.parse(inputBytes.toString('utf8')), validation = validateHumanInput(input);
  if (!validation.valid) throw new Error(validation.reason);
  await mkdir(evidenceRoot, { recursive: false, mode: 0o700 });
  const body = { schemaVersion: 'bfs.pc3HumanReviewReceipt.v0.1', status: 'RECORDED_UNMODIFIED_ALLOWED_TOKENS', gate: 'PC.3', capturedAt: capturedAt.toISOString(), reviewerRole: input.reviewerRole, responseOrigin: 'human-authored current-thread response', sourceMessageText: input.sourceMessageText, sourceMessageSha256: sha256Bytes(Buffer.from(input.sourceMessageText, 'utf8')), answers: input.answers, optionalNotes: input.optionalNotes, inputFileSha256: sha256Bytes(inputBytes), preregistration: { uri: PREREG_URI, sha256: await sha256File(preregPath), specHash: prereg.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await sha256File(freezePath), specHash: freeze.specHash }, reviewArtifacts: { baselineA: prereg.baselineA.videoUri, integratedB: freeze.machineEvidence.integratedVideo.uri, contactSheet: freeze.machineEvidence.contactSheet.uri }, modelAuthoredAnswerCount: 0, normalizationApplied: false };
  const receipt = await writeJson(resolve(evidenceRoot, 'human-review.json'), body, 'reviewHash'); process.stdout.write(`BFS_PC3_REVIEW_RECORDED ${receipt.reviewHash}\n`); return receipt;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) recordReview().catch(error => { process.stderr.write(`BFS_PC3_REVIEW_REJECTED ${error.message}\n`); process.exitCode = 1; });
