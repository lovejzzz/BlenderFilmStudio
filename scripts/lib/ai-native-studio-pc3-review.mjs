import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';

export const IDS = ['Q1', 'Q2', 'Q3', 'Q4'];
export const TOKENS = ['YES', 'NO'];
export const TOP_LEVEL_KEYS = ['answers', 'optionalNotes', 'reviewerRole', 'schemaVersion', 'sourceMessageText'];
export function sorted(value) { if (Array.isArray(value)) return value.map(sorted); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, child]) => [key, sorted(child)])); return value; }
export const canonicalJson = value => JSON.stringify(sorted(value));
export const sha256Bytes = value => createHash('sha256').update(value).digest('hex');
export const sha256Canonical = value => sha256Bytes(canonicalJson(value));
export const sha256File = async path => sha256Bytes(await readFile(path));
export function validSelfHash(value, field) { const body = structuredClone(value); const expected = body[field]; delete body[field]; return typeof expected === 'string' && expected === sha256Canonical(body); }
export function validateHumanInput(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { valid: false, reason: 'INPUT_OBJECT' };
  if (JSON.stringify(Object.keys(input).sort()) !== JSON.stringify(TOP_LEVEL_KEYS)) return { valid: false, reason: 'TOP_LEVEL_KEYS' };
  if (input.schemaVersion !== 'bfs.pc3HumanReviewInput.v0.1') return { valid: false, reason: 'SCHEMA' };
  if (input.reviewerRole !== 'project-owner') return { valid: false, reason: 'REVIEWER_ROLE' };
  if (typeof input.sourceMessageText !== 'string' || input.sourceMessageText.length === 0) return { valid: false, reason: 'SOURCE_MESSAGE' };
  if (typeof input.optionalNotes !== 'string') return { valid: false, reason: 'OPTIONAL_NOTES' };
  if (!input.answers || typeof input.answers !== 'object' || Array.isArray(input.answers)) return { valid: false, reason: 'ANSWERS_OBJECT' };
  if (JSON.stringify(Object.keys(input.answers).sort()) !== JSON.stringify(IDS)) return { valid: false, reason: 'ANSWER_KEYS' };
  if (IDS.some(id => !TOKENS.includes(input.answers[id]))) return { valid: false, reason: 'ANSWER_TOKEN' };
  return { valid: true, verdict: IDS.every(id => input.answers[id] === 'YES') ? 'PASS' : 'FAIL' };
}
