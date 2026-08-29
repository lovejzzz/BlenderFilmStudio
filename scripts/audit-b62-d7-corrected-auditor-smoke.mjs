#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { measureOutput } from './lib/budgeted-process.mjs';
import { resolveExistingRepositoryPath, sha256File, validSelfHash } from './preflight-b62-phase0.mjs';

const ROOT = 'experiments/b62-phase0-d7-corrected-auditor-smoke-v0-1';
export async function auditD7() {
  const root = await resolveExistingRepositoryPath(ROOT, 'D7', 'directory'); const resultPath = resolve(root, 'result.json'); const receiptPath = resolve(root, 'receipt.json'); const auditPath = resolve(root, 'blender-audit.json');
  const result = JSON.parse(await readFile(resultPath, 'utf8')); const receipt = JSON.parse(await readFile(receiptPath, 'utf8')); const audit = JSON.parse(await readFile(auditPath, 'utf8'));
  if (!validSelfHash(result, 'resultHash') || !validSelfHash(receipt, 'receiptHash') || !validSelfHash(audit, 'auditHash') || result.status !== 'PASS' || receipt.status !== 'PASS' || audit.status !== 'PASS'
    || receipt.verdict !== 'CORRECTED_PRODUCTION_AUDITOR_PROVEN' || result.checks.length !== 8 || !result.checks.every(row => row.pass) || Object.keys(audit.checks).length !== 23 || !Object.values(audit.checks).every(Boolean)
    || audit.masterLocality.libraries.length !== 0 || audit.masterLocality.linkedIds.length !== 0 || audit.assetLibraries.length !== 3 || !audit.assetLibraries.every(row => row.findings.length === 0 && row.locality.appendedIds.every(item => item.library === null) && Object.values(row.locality.cleanup).every(Boolean))
    || receipt.result.sha256 !== await sha256File(resultPath) || receipt.result.resultHash !== result.resultHash || receipt.correctedAuditHash !== audit.auditHash || result.correctedAudit.sha256 !== await sha256File(auditPath)) throw new Error('D7 semantic/hash');
  const output = await measureOutput(root); if (output.symlinkCount !== 0 || output.bytes > 8388608 || output.fileCount !== 5) throw new Error('D7 output'); process.stdout.write(`BFS_B62_D7_AUDIT PASS 8/8 ${receipt.receiptHash}\n`); return receipt;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) auditD7().catch(error => { process.stderr.write(`BFS_B62_D7_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
