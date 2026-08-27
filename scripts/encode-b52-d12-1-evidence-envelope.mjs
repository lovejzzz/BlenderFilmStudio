#!/usr/bin/env node
/** Node implementation of the preregistered D12.1 typed evidence envelope. */

import fs from 'node:fs';
import crypto from 'node:crypto';
import process from 'node:process';

const SPEC_SHA256 = '8bd219570e0c7ec922a671919d680787caf55b2ba7d8a631ed5bc995ab24f116';
const MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER;

function parseArgs() {
  const result = {};
  for (let index = 2; index < process.argv.length; index += 2) result[process.argv[index].replace(/^--/, '')] = process.argv[index + 1];
  for (const key of ['spec', 'input', 'output']) if (!(key in result)) throw new Error(`missing --${key}`);
  return result;
}

function shaBytes(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function validateString(value) {
  for (let index = 0; index < value.length; index++) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error('unpaired surrogate is forbidden');
      index++;
    } else if (code >= 0xdc00 && code <= 0xdfff) throw new Error('unpaired surrogate is forbidden');
  }
}
function codePoints(value) { return Array.from(value, character => character.codePointAt(0)); }
function compareKeys(left, right) {
  const a = codePoints(left), b = codePoints(right), length = Math.min(a.length, b.length);
  for (let index = 0; index < length; index++) if (a[index] !== b[index]) return a[index] - b[index];
  return a.length - b.length;
}
function encodeNumber(value) {
  if (!Number.isFinite(value)) throw new Error('nonfinite number is forbidden');
  if (Number.isInteger(value) && Math.abs(value) > MAX_SAFE_INTEGER) throw new Error('integer-valued number exceeds binary64 safe integer domain');
  const buffer = Buffer.alloc(8);
  buffer.writeDoubleBE(Object.is(value, -0) ? 0 : value);
  return { $f64be: buffer.toString('hex') };
}
function transform(value) {
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'number') return encodeNumber(value);
  if (typeof value === 'string') { validateString(value); return value; }
  if (Array.isArray(value)) return value.map(transform);
  if (typeof value === 'object') {
    const result = {};
    for (const key of Object.keys(value).sort(compareKeys)) { validateString(key); result[key] = transform(value[key]); }
    return result;
  }
  throw new Error(`unsupported JSON value type: ${typeof value}`);
}
function envelopeBytes(value) { return Buffer.from(JSON.stringify(transform(value)), 'utf8'); }

function main() {
  const args = parseArgs();
  if (shaBytes(fs.readFileSync(args.spec)) !== SPEC_SHA256) throw new Error('D12.1 development spec identity mismatch');
  if (fs.existsSync(args.output)) throw new Error('refusing to overwrite evidence envelope');
  let payload = JSON.parse(fs.readFileSync(args.input, 'utf8'));
  if (args.subtree) {
    if (!payload || typeof payload !== 'object' || !(args.subtree in payload)) throw new Error('requested subtree is absent');
    payload = payload[args.subtree];
  } else if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    payload = Object.fromEntries(Object.entries(payload).filter(([key]) => key !== 'reportHash'));
  }
  const encoded = envelopeBytes(payload);
  fs.mkdirSync(args.output.slice(0, args.output.lastIndexOf('/')), { recursive: true });
  fs.writeFileSync(args.output, encoded);
  process.stdout.write(`BFS_D12_1_ENVELOPE_NODE_OK bytes=${encoded.length} sha256=${shaBytes(encoded)}\n`);
}

main();
