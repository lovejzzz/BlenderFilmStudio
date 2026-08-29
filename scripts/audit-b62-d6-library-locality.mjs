#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { measureOutput } from './lib/budgeted-process.mjs';
import { resolveExistingRepositoryPath, sha256File, validSelfHash } from './preflight-b62-phase0.mjs';

const ROOT = 'experiments/b62-phase0-d6-library-locality-v0-1';

export async function auditD6() {
  const root = await resolveExistingRepositoryPath(ROOT, 'D6', 'directory');
  const resultPath = resolve(root, 'result.json'); const receiptPath = resolve(root, 'receipt.json'); const probePath = resolve(root, 'probe.json');
  const result = JSON.parse(await readFile(resultPath, 'utf8')); const receipt = JSON.parse(await readFile(receiptPath, 'utf8')); const probe = JSON.parse(await readFile(probePath, 'utf8'));
  if (!validSelfHash(result, 'resultHash') || !validSelfHash(receipt, 'receiptHash') || !validSelfHash(probe, 'probeHash')
    || result.status !== 'PASS' || receipt.status !== 'PASS' || probe.status !== 'PASS' || receipt.verdict !== 'LOCAL_APPEND_SOURCE_DESCRIPTOR_ONLY'
    || result.checks.length !== 8 || !result.checks.every(row => row.pass) || probe.assets.length !== 3
    || !probe.checks.masterInitialLibrariesZero || !probe.checks.masterInitialLinkedIdsZero || !probe.checks.finalLibrariesZero || !probe.checks.finalLinkedIdsZero || !probe.checks.finalRosterExact
    || !probe.assets.every(row => row.checks.sourceRosterExact && row.checks.appendedIdsObserved && row.checks.appendedIdsAllLocal && row.checks.sourceDescriptorsObserved && row.checks.descriptorsExactSource && row.checks.descriptorRemovalSucceeded && row.checks.localIdsSurviveDescriptorRemoval && row.checks.cleanupExact)
    || receipt.result.sha256 !== await sha256File(resultPath) || receipt.result.resultHash !== result.resultHash || receipt.probeHash !== probe.probeHash || result.probe.sha256 !== await sha256File(probePath)) throw new Error('D6 semantic/hash');
  const output = await measureOutput(root); if (output.symlinkCount !== 0 || output.bytes > 16777216 || output.fileCount !== 5) throw new Error('D6 output');
  process.stdout.write(`BFS_B62_D6_AUDIT PASS 8/8 ${receipt.receiptHash}\n`); return receipt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) auditD6().catch(error => { process.stderr.write(`BFS_B62_D6_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
