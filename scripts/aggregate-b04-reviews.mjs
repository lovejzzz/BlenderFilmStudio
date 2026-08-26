import { readdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './lib/scene-spec.mjs';

const args = process.argv.slice(2);
const inputIndex = args.indexOf('--input-dir');
const outputIndex = args.indexOf('--output');
const schemaIndex = args.indexOf('--schema');
if (inputIndex < 0 || !args[inputIndex + 1]) throw new Error('Usage: node scripts/aggregate-b04-reviews.mjs --input-dir <dir> [--output <json>]');
const inputDir = resolve(process.cwd(), args[inputIndex + 1]);
const output = outputIndex >= 0 && args[outputIndex + 1] ? resolve(process.cwd(), args[outputIndex + 1]) : null;
const schemaPath = schemaIndex >= 0 && args[schemaIndex + 1] ? resolve(process.cwd(), args[schemaIndex + 1]) : resolve(repositoryRoot, 'specs/human-review-response.v0.1.schema.json');
const schema = JSON.parse(await readFile(schemaPath, 'utf8'));
const protocolVersion = schema.properties?.protocolVersion?.const;
const clipId = schema.properties?.clipId?.const;
if (!protocolVersion || !clipId) throw new Error(`Review schema must declare protocolVersion and clipId constants: ${schemaPath}`);
const ajv = new Ajv2020({ allErrors: true, strict: true, formats: { 'date-time': true } });
const validate = ajv.compile(schema);

const files = (await readdir(inputDir, { withFileTypes: true })).filter(item => item.isFile() && item.name.endsWith('.review.json')).map(item => item.name).sort();
const valid = [];
const invalid = [];
const reviewerCodes = new Set();
for (const file of files) {
  try {
    const document = JSON.parse(await readFile(resolve(inputDir, file), 'utf8'));
    const schemaValid = validate(document);
    if (!schemaValid) {
      invalid.push({ file, reason: 'SCHEMA', errors: (validate.errors ?? []).map(error => ({ path: error.instancePath || '/', message: error.message })) });
    } else if (reviewerCodes.has(document.reviewerCode)) {
      invalid.push({ file, reason: 'DUPLICATE_REVIEWER_CODE', reviewerCode: document.reviewerCode });
    } else {
      reviewerCodes.add(document.reviewerCode);
      valid.push({ file, document });
    }
  } catch (error) {
    invalid.push({ file, reason: 'INVALID_JSON', error: error.message });
  }
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
  approachNaturalnessMedian: median(valid.map(item => item.document.answers.approachNaturalness)),
  supportReadabilityMedian: median(valid.map(item => item.document.answers.supportReadability)),
  weightCoherenceMedian: median(valid.map(item => item.document.answers.weightCoherence)),
  distractingIntersection: { yes: count('distractingIntersection', 'YES'), no: count('distractingIntersection', 'NO'), unsure: count('distractingIntersection', 'UNSURE') },
  visiblePop: { yes: count('visiblePop', 'YES'), no: count('visiblePop', 'NO'), unsure: count('visiblePop', 'UNSURE') },
  overallAcceptance: { pass: count('overallAcceptance', 'PASS'), fail: count('overallAcceptance', 'FAIL'), unsure: count('overallAcceptance', 'UNSURE') },
};
const enoughReviewers = validCount >= 3;
const gates = {
  minimumReviewers: enoughReviewers,
  approachMedian: enoughReviewers && metrics.approachNaturalnessMedian >= 3,
  supportMedian: enoughReviewers && metrics.supportReadabilityMedian >= 3,
  weightMedian: enoughReviewers && metrics.weightCoherenceMedian >= 3,
  intersectionMinority: enoughReviewers && metrics.distractingIntersection.yes < validCount / 2,
  popMinority: enoughReviewers && metrics.visiblePop.yes < validCount / 2,
  overallStrictMajority: enoughReviewers && metrics.overallAcceptance.pass > validCount / 2,
};
const report = {
  documentType: 'BFS_HUMAN_REVIEW_AGGREGATE', protocolVersion, clipId,
  generatedAtUtc: new Date().toISOString(), input: { files: files.length, validResponses: validCount, invalidResponses: invalid.length },
  validReviewerCodes: [...reviewerCodes].sort(), invalid, metrics, gates,
  status: !enoughReviewers ? 'PENDING_INSUFFICIENT_RESPONSES' : Object.values(gates).every(Boolean) ? 'PASS' : 'FAIL',
  humanGatePassed: enoughReviewers && Object.values(gates).every(Boolean),
  explicitNonClaims: ['This pilot does not establish population-level preference.', 'The aggregation contains no machine metrics and does not override individual reviewer notes.'],
};
const serialized = `${JSON.stringify(report, null, 2)}\n`;
if (output) await writeFile(output, serialized);
process.stdout.write(serialized);
