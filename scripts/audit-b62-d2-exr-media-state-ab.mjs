#!/usr/bin/env node

import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { resolveExistingRepositoryPath, sha256File, validSelfHash } from './preflight-b62-phase0.mjs';

const ROOT = 'experiments/b62-phase0-d2-exr-media-state-ab-v0-1';
export async function auditD2() {
  const root = await resolveExistingRepositoryPath(ROOT, 'D2 root', 'directory'); if (!isDeepStrictEqual((await readdir(root)).sort(), ['receipt.json', 'result.json', 'stderr.log', 'stdout.log'])) throw new Error('D2 roster mismatch');
  const resultPath = resolve(root, 'result.json'); const receiptPath = resolve(root, 'receipt.json'); const result = JSON.parse(await readFile(resultPath, 'utf8')); const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  if (!validSelfHash(result, 'resultHash') || !validSelfHash(receipt, 'receiptHash') || result.status !== 'PASS' || receipt.status !== 'PASS' || result.checks.length !== 8 || !result.checks.every(row => row.pass)) throw new Error('D2 status/check/hash mismatch');
  if (receipt.result.sha256 !== await sha256File(resultPath) || receipt.result.resultHash !== result.resultHash || result.probe.rows.length !== 9 || !result.probe.rows.every(row => row.outcomeExact)) throw new Error('D2 semantic binding mismatch');
  for (const stream of ['stdout', 'stderr']) { const row = result.process[stream]; const path = await resolveExistingRepositoryPath(row.uri, `D2 ${stream}`); if (row.sha256 !== await sha256File(path) || row.bytes !== (await stat(path)).size) throw new Error(`D2 ${stream} mismatch`); }
  process.stdout.write(`BFS_B62_D2_AUDIT PASS 8/8 setterOutcomes=9/9 ${receipt.receiptHash}\n`); return receipt;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) auditD2().catch(error => { process.stderr.write(`BFS_B62_D2_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
