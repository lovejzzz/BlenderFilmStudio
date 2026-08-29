#!/usr/bin/env node

import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { repositoryRoot, resolveExistingRepositoryPath, sha256File, validSelfHash } from './preflight-b62-phase0.mjs';

const ROOT = 'experiments/b62-phase0-d1-exr-media-type-v0-1';

export async function auditD1() {
  const root = await resolveExistingRepositoryPath(ROOT, 'D1 root', 'directory');
  const roster = (await readdir(root)).sort();
  if (!isDeepStrictEqual(roster, ['receipt.json', 'result.json', 'stderr.log', 'stdout.log'])) throw new Error('D1 roster mismatch');
  const resultPath = resolve(root, 'result.json'); const receiptPath = resolve(root, 'receipt.json');
  const result = JSON.parse(await readFile(resultPath, 'utf8')); const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
  if (!validSelfHash(result, 'resultHash') || !validSelfHash(receipt, 'receiptHash') || result.status !== 'PASS' || receipt.status !== 'PASS') throw new Error('D1 self-hash/status mismatch');
  if (result.checks.length !== 8 || !result.checks.every(row => row.pass)) throw new Error('D1 checks mismatch');
  if (receipt.result.sha256 !== await sha256File(resultPath) || receipt.result.resultHash !== result.resultHash) throw new Error('D1 result binding mismatch');
  for (const stream of ['stdout', 'stderr']) {
    const row = result.process[stream]; const path = await resolveExistingRepositoryPath(row.uri, `D1 ${stream}`);
    if (row.sha256 !== await sha256File(path) || row.bytes !== (await stat(path)).size) throw new Error(`D1 ${stream} identity mismatch`);
  }
  if (!result.probe.assignmentBeforeMediaTypeRejected || result.probe.final.mediaType !== 'MULTI_LAYER_IMAGE' || result.probe.final.fileFormat !== 'OPEN_EXR_MULTILAYER'
    || result.probe.final.colorDepth !== '16' || result.probe.final.exrCodec !== 'ZIP' || result.probe.operations.renderCalls !== 0) throw new Error('D1 semantic mismatch');
  process.stdout.write(`BFS_B62_D1_AUDIT PASS 8/8 ${receipt.receiptHash}\n`); return { resultHash: result.resultHash, receiptHash: receipt.receiptHash, root: root.slice(repositoryRoot.length + 1) };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) auditD1().catch(error => { process.stderr.write(`BFS_B62_D1_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
