import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './lib/scene-spec.mjs';

const schema = JSON.parse(await readFile(resolve(repositoryRoot, 'specs/human-review-response.v0.4.schema.json'), 'utf8'));
const validate = new Ajv2020({ allErrors: true, strict: true, formats: { 'date-time': true } }).compile(schema);
const valid = {
  documentType: 'BFS_B09_SOURCE_PHYSICS_REVIEW_RESPONSE', protocolVersion: '0.4.0', clipId: 'CLIP_P84R', clipSha256: '244974d7be08107e9b88ab855a05fbfdeda486f52d66076fd29581305fe35041',
  reviewerCode: 'TEST_R01', submittedAtUtc: '2026-08-26T07:00:00Z', watchedTwice: true,
  answers: { twoSidedSupport: 4, transportSynchronization: 4, releasePlausibility: 4, visibleInterpenetration: 'NO', visiblePop: 'NO', overallAcceptance: 'PASS', note: '' },
  privacy: { transmitted: false, personalDataRequested: false },
};
const cases = [
  ['P01_VALID', document => document, true],
  ['N01_CLIP_HASH', document => { document.clipSha256 = '0'.repeat(64); return document; }, false],
  ['N02_DOCUMENT_TYPE', document => { document.documentType = 'OTHER'; return document; }, false],
  ['N03_WATCHED_FALSE', document => { document.watchedTwice = false; return document; }, false],
  ['N04_SCORE_RANGE', document => { document.answers.releasePlausibility = 6; return document; }, false],
  ['N05_EXTRA_ANSWER', document => { document.answers.machineScore = 5; return document; }, false],
  ['N06_PRIVACY', document => { document.privacy.personalDataRequested = true; return document; }, false],
  ['N07_MISSING_VERDICT', document => { delete document.answers.overallAcceptance; return document; }, false],
];
const results = cases.map(([id, mutate, expected]) => {
  const document = mutate(structuredClone(valid));
  const observed = validate(document);
  return { id, expectedValid: expected, observedValid: observed, pass: observed === expected, errors: observed ? [] : (validate.errors ?? []).map(error => ({ path: error.instancePath || '/', message: error.message })) };
});
const report = { documentType: 'BFS_B09_REVIEW_CONTRACT_SELF_TEST', version: '0.1.0', schema: 'specs/human-review-response.v0.4.schema.json', cases: results, passed: results.every(item => item.pass) };
const output = resolve(repositoryRoot, 'experiments/physics-review-v0-1/contract-self-test.json');
await writeFile(output, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B09_REVIEW_CONTRACT ${report.passed ? 'PASS' : 'FAIL'} ${results.filter(item => item.pass).length}/${results.length}\n`);
if (!report.passed) process.exitCode = 1;
