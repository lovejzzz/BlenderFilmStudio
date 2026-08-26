import { readdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './lib/scene-spec.mjs';

const args = process.argv.slice(2);
const inputIndex = args.indexOf('--input-dir');
const outputIndex = args.indexOf('--output');
if (inputIndex < 0 || !args[inputIndex + 1]) throw new Error('Usage: node scripts/aggregate-b09-reviews.mjs --input-dir <dir> [--output <json>]');
const inputDir = resolve(process.cwd(), args[inputIndex + 1]);
const output = outputIndex >= 0 && args[outputIndex + 1] ? resolve(process.cwd(), args[outputIndex + 1]) : null;
const schema = JSON.parse(await readFile(resolve(repositoryRoot, 'specs/human-review-response.v0.4.schema.json'), 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true, formats: { 'date-time': true } });
const validate = ajv.compile(schema);
const files = (await readdir(inputDir, { withFileTypes: true })).filter(item => item.isFile() && item.name.endsWith('.review.json')).map(item => item.name).sort();
const valid = [];
const invalid = [];
const reviewerCodes = new Set();
for (const file of files) {
  try {
    const document = JSON.parse(await readFile(resolve(inputDir, file), 'utf8'));
    if (!validate(document)) invalid.push({ file, reason: 'SCHEMA', errors: (validate.errors ?? []).map(error => ({ path: error.instancePath || '/', message: error.message })) });
    else if (reviewerCodes.has(document.reviewerCode)) invalid.push({ file, reason: 'DUPLICATE_REVIEWER_CODE', reviewerCode: document.reviewerCode });
    else { reviewerCodes.add(document.reviewerCode); valid.push({ file, document }); }
  } catch (error) { invalid.push({ file, reason: 'INVALID_JSON', error: error.message }); }
}
const median = values => {
  if (values.length === 0) return null;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
};
const count = (field, value) => valid.filter(item => item.document.answers[field] === value).length;
const validCount = valid.length;
const metrics = {
  twoSidedSupportMedian: median(valid.map(item => item.document.answers.twoSidedSupport)),
  transportSynchronizationMedian: median(valid.map(item => item.document.answers.transportSynchronization)),
  releasePlausibilityMedian: median(valid.map(item => item.document.answers.releasePlausibility)),
  visibleInterpenetration: { yes: count('visibleInterpenetration', 'YES'), no: count('visibleInterpenetration', 'NO'), unsure: count('visibleInterpenetration', 'UNSURE') },
  visiblePop: { yes: count('visiblePop', 'YES'), no: count('visiblePop', 'NO'), unsure: count('visiblePop', 'UNSURE') },
  overallAcceptance: { pass: count('overallAcceptance', 'PASS'), fail: count('overallAcceptance', 'FAIL'), unsure: count('overallAcceptance', 'UNSURE') },
};
const enoughReviewers = validCount >= 3;
const gates = {
  minimumReviewers: enoughReviewers,
  supportMedianAtLeast4: enoughReviewers && metrics.twoSidedSupportMedian >= 4,
  transportMedianAtLeast4: enoughReviewers && metrics.transportSynchronizationMedian >= 4,
  releaseMedianAtLeast4: enoughReviewers && metrics.releasePlausibilityMedian >= 4,
  zeroVisibleInterpenetration: enoughReviewers && metrics.visibleInterpenetration.yes === 0,
  zeroVisiblePop: enoughReviewers && metrics.visiblePop.yes === 0,
  overallStrictMajority: enoughReviewers && metrics.overallAcceptance.pass > validCount / 2,
  zeroOverallFail: enoughReviewers && metrics.overallAcceptance.fail === 0,
};
const report = {
  documentType: 'BFS_B09_SOURCE_PHYSICS_REVIEW_AGGREGATE', protocolVersion: '0.4.0', clipId: 'CLIP_P84R',
  clipSha256: '244974d7be08107e9b88ab855a05fbfdeda486f52d66076fd29581305fe35041',
  generatedAtUtc: new Date().toISOString(), input: { files: files.length, validResponses: validCount, invalidResponses: invalid.length },
  validReviewerCodes: [...reviewerCodes].sort(), invalid, metrics, gates,
  status: !enoughReviewers ? 'PENDING_INSUFFICIENT_RESPONSES' : Object.values(gates).every(Boolean) ? 'PASS' : 'FAIL',
  humanGatePassed: enoughReviewers && Object.values(gates).every(Boolean), requiredAuthenticIndependentResponses: 3,
  explicitNonClaims: ['No machine metric or model judgment is counted as a human response.', 'This pilot evaluates one visible technical trajectory, not Bullet reproducibility, real-world force accuracy, anatomy, acting, or cinema quality.'],
};
const serialized = `${JSON.stringify(report, null, 2)}\n`;
if (output) await writeFile(output, serialized);
process.stdout.write(serialized);
