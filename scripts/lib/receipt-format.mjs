import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';

export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0).map(([key, child]) => [key, canonicalize(child)]));
  }
  return value;
}

export const canonicalJson = value => JSON.stringify(canonicalize(value));
export const sha256Bytes = value => createHash('sha256').update(value).digest('hex');
export const sha256Canonical = value => sha256Bytes(canonicalJson(value));

export function sha256File(path) {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256');
    const stream = createReadStream(path);
    stream.on('data', chunk => hash.update(chunk));
    stream.on('error', reject);
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

export function rehashReceipt(receipt) {
  const next = structuredClone(receipt);
  delete next.receiptHash;
  delete next.executionIdentityHash;
  next.executionIdentityHash = sha256Canonical(next.executionIdentity);
  next.receiptHash = sha256Canonical(next);
  return next;
}
