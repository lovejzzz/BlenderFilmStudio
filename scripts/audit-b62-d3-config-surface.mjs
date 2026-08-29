#!/usr/bin/env node

import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { resolveExistingRepositoryPath, sha256File, validSelfHash } from './preflight-b62-phase0.mjs';

const ROOT = 'experiments/b62-phase0-d3-config-surface-v0-1';
export async function auditD3() {
  const root = await resolveExistingRepositoryPath(ROOT, 'D3 root', 'directory'); if (!isDeepStrictEqual((await readdir(root)).sort(), ['receipt.json', 'result.json', 'stderr.log', 'stdout.log'])) throw new Error('D3 roster');
  const resultPath = resolve(root, 'result.json'); const receiptPath = resolve(root, 'receipt.json'); const result = JSON.parse(await readFile(resultPath, 'utf8')); const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  if (!validSelfHash(result, 'resultHash') || !validSelfHash(receipt, 'receiptHash') || result.status !== 'PASS' || receipt.status !== 'PASS' || result.checks.length !== 9 || !result.checks.every(row => row.pass)) throw new Error('D3 hash/status/checks');
  if (receipt.result.sha256 !== await sha256File(resultPath) || receipt.result.resultHash !== result.resultHash || result.probe.color.look !== 'None' || result.probe.eevee.renderSamples !== 16 || result.probe.exr.mediaType !== 'MULTI_LAYER_IMAGE' || result.probe.operations.renderCalls !== 0) throw new Error('D3 semantic binding');
  for (const stream of ['stdout', 'stderr']) { const row = result.process[stream]; const path = await resolveExistingRepositoryPath(row.uri, `D3 ${stream}`); if (row.sha256 !== await sha256File(path) || row.bytes !== (await stat(path)).size) throw new Error(`D3 ${stream}`); }
  process.stdout.write(`BFS_B62_D3_AUDIT PASS 9/9 ${receipt.receiptHash}\n`); return receipt;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) auditD3().catch(error => { process.stderr.write(`BFS_B62_D3_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
