import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';

export const QUESTION_IDS = Object.freeze(['Q1', 'Q2', 'Q3', 'Q4']);
export const ALLOWED_ANSWERS = Object.freeze(['YES', 'NO', 'UNCERTAIN', 'UNVIEWABLE']);

export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value)
      .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
      .map(([key, child]) => [key, canonicalize(child)]));
  }
  return value;
}

export const canonicalJson = value => JSON.stringify(canonicalize(value));
export const sha256Bytes = value => createHash('sha256').update(value).digest('hex');
export const sha256Canonical = value => sha256Bytes(canonicalJson(value));
export const sha256File = async path => sha256Bytes(await readFile(path));

export function withoutField(value, field) {
  const body = structuredClone(value);
  delete body[field];
  return body;
}

export function validSelfHash(value, field) {
  return typeof value?.[field] === 'string'
    && value[field] === sha256Canonical(withoutField(value, field));
}

export function validateHumanInput(input) {
  const exactKeys = ['answers', 'optionalNotes', 'reviewerRole', 'schemaVersion', 'sourceMessageText'];
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { valid: false, reason: 'INPUT_OBJECT' };
  if (JSON.stringify(Object.keys(input).sort()) !== JSON.stringify(exactKeys)) return { valid: false, reason: 'INPUT_KEYS' };
  if (input.schemaVersion !== 'bfs.pb7HumanReviewInput.v0.1') return { valid: false, reason: 'INPUT_VERSION' };
  if (input.reviewerRole !== 'project owner and human viewer') return { valid: false, reason: 'REVIEWER_ROLE' };
  if (typeof input.sourceMessageText !== 'string' || input.sourceMessageText.trim() === '') return { valid: false, reason: 'SOURCE_MESSAGE' };
  if (typeof input.optionalNotes !== 'string') return { valid: false, reason: 'OPTIONAL_NOTES' };
  if (!input.answers || typeof input.answers !== 'object' || Array.isArray(input.answers)) return { valid: false, reason: 'ANSWERS_OBJECT' };
  if (JSON.stringify(Object.keys(input.answers).sort()) !== JSON.stringify(QUESTION_IDS)) return { valid: false, reason: 'ANSWER_KEYS' };
  for (const id of QUESTION_IDS) {
    if (!ALLOWED_ANSWERS.includes(input.answers[id])) return { valid: false, reason: `ANSWER_${id}` };
  }
  return { valid: true, reason: 'OK' };
}

export function humanVerdict(answers) {
  const values = QUESTION_IDS.map(id => answers[id]);
  if (values.includes('NO')) return 'FAIL';
  if (values.every(value => value === 'YES')) return 'PASS';
  return 'BLOCKED';
}
