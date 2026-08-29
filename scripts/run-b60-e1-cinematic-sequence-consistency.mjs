#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual, promisify } from 'node:util';
import {
  durableMkdir,
  repoUri,
  resolveExistingRepositoryPath,
  resolveFreshRepositoryPath,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
  writeDurableJson,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/cinematic-sequence-consistency.v0.1.json';
const TOOL_PATHS = [
  CONTRACT_URI,
  'research/2026-08-29-b60-e1-cinematic-sequence-consistency-protocol.md',
  'scripts/preflight-b60-e1-cinematic-sequence-consistency.mjs',
  'scripts/run-b60-e1-cinematic-sequence-consistency.mjs',
  'scripts/audit-b60-e1-cinematic-sequence-consistency.mjs',
];
const EXPECTED = {
  preflightRoot: 'experiments/cinematic-sequence-consistency-preflight-v0-1',
  attemptRoot: 'experiments/cinematic-sequence-consistency-attempt-v0-1',
  formalRoot: 'experiments/cinematic-sequence-consistency-v0-1',
};

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else if (token === '--preflight-evidence-commit') parsed.preflightEvidenceCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const key of [...Object.keys(EXPECTED), 'toolFreezeCommit', 'preflightEvidenceCommit']) {
    if (!parsed[key]) throw new Error(`Missing --${key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit) || !/^[0-9a-f]{40}$/.test(parsed.preflightEvidenceCommit)) {
    throw new Error('Tool-freeze and preflight-evidence commits must be full lowercase SHA-1 values');
  }
  for (const [key, expected] of Object.entries(EXPECTED)) if (parsed[key] !== expected) throw new Error(`B60 ${key} mismatch`);
  return parsed;
}

async function git(args, options = {}) {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot,
    encoding: options.encoding ?? 'utf8',
    timeout: 15000,
    maxBuffer: 32 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function verifyCommitAndTools(parsed, outerPath) {
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  await git(['merge-base', '--is-ancestor', parsed.toolFreezeCommit, origin]);
  await git(['merge-base', '--is-ancestor', parsed.preflightEvidenceCommit, origin]);
  await git(['merge-base', '--is-ancestor', parsed.toolFreezeCommit, parsed.preflightEvidenceCommit]);
  const hashes = {};
  for (const uri of TOOL_PATHS) {
    const path = await resolveExistingRepositoryPath(uri, `B60 frozen tool ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${parsed.toolFreezeCommit}:${uri}`], { encoding: null }));
    if (current !== frozen) throw new Error(`B60 frozen tool mismatch: ${uri}`);
    hashes[uri] = current;
  }
  const outerUri = repoUri(outerPath);
  const frozenOuter = sha256Bytes(await git(['show', `${parsed.preflightEvidenceCommit}:${outerUri}`], { encoding: null }));
  if (await sha256File(outerPath) !== frozenOuter) throw new Error('B60 preflight evidence differs from evidence commit');
  const dirty = await git(['status', '--porcelain=v1', '--untracked-files=all', '--', parsed.preflightRoot]);
  if (dirty.length !== 0) throw new Error('B60 preflight evidence root is dirty');
  return hashes;
}

function casesFor(contract) {
  return contract.sequence.shots.flatMap(shot => ['A', 'B'].map(repetition => ({
    id: `${shot.label}-${repetition}`,
    label: shot.label,
    repetition,
    sceneSpec: shot.sceneSpec.uri,
  })));
}

async function runChild(args, timeout = 180000) {
  const started = process.hrtime.bigint();
  try {
    const result = await execFileAsync(process.execPath, args, {
      cwd: repositoryRoot,
      encoding: 'utf8',
      timeout,
      maxBuffer: 8 * 1024 * 1024,
      env: {
        PATH: '/opt/homebrew/bin:/usr/bin:/bin',
        LANG: 'C.UTF-8',
        LC_ALL: 'C.UTF-8',
        BLENDER_BIN: '/Applications/Blender.app/Contents/MacOS/Blender',
      },
    });
    return {
      exitCode: 0,
      signal: null,
      elapsedNanoseconds: Number(process.hrtime.bigint() - started),
      stdout: result.stdout,
      stderr: result.stderr,
    };
  } catch (error) {
    return {
      exitCode: typeof error.code === 'number' ? error.code : 1,
      signal: error.signal ?? null,
      elapsedNanoseconds: Number(process.hrtime.bigint() - started),
      stdout: error.stdout ?? '',
      stderr: error.stderr ?? error.message,
    };
  }
}

function capturedProcess(row) {
  return {
    exitCode: row.exitCode,
    signal: row.signal,
    elapsedNanoseconds: row.elapsedNanoseconds,
    stdout: { bytes: Buffer.byteLength(row.stdout), sha256: sha256Bytes(Buffer.from(row.stdout)) },
    stderr: { bytes: Buffer.byteLength(row.stderr), sha256: sha256Bytes(Buffer.from(row.stderr)) },
  };
}

async function retainInvalidation(formalPath, phase, error, context) {
  try {
    await writeDurableHashed(resolve(formalPath, 'invalidation.json'), {
      schemaVersion: 'bfs.cinematicSequenceConsistencyInvalidation.v0.1',
      status: 'INVALIDATED',
      phase,
      error: { name: error?.name ?? 'Error', message: error?.message ?? String(error) },
      context,
      partialEvidenceRetained: true,
      verdict: null,
    }, 'invalidationHash');
  } catch (writeError) {
    if (writeError?.code !== 'EEXIST') throw writeError;
  }
}

export async function runB60(argv) {
  const parsed = parseArguments(argv);
  const preflightPath = await resolveExistingRepositoryPath(`${parsed.preflightRoot}/preflight.json`, 'B60 outer preflight');
  const attemptPath = await resolveFreshRepositoryPath(parsed.attemptRoot, 'B60 attempt root');
  const formalPath = await resolveFreshRepositoryPath(parsed.formalRoot, 'B60 formal root');
  const contractPath = await resolveExistingRepositoryPath(CONTRACT_URI, 'B60 contract');
  const contract = JSON.parse(await readFile(contractPath, 'utf8'));
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (!validSelfHash(preflight, 'preflightHash') || preflight.status !== 'ACCEPTED'
    || preflight.toolFreezeCommit !== parsed.toolFreezeCommit || !isDeepStrictEqual(preflight.roots, contract.roots)) {
    throw new Error('B60 preflight receipt is invalid or invocation binding differs');
  }
  const toolHashes = await verifyCommitAndTools(parsed, preflightPath);

  await durableMkdir(attemptPath);
  const outerAttemptPath = resolve(attemptPath, 'attempt.json');
  const outerAttempt = await writeDurableHashed(outerAttemptPath, {
    schemaVersion: 'bfs.cinematicSequenceConsistencyAttempt.v0.1',
    sequence: 1,
    status: 'STARTED',
    invocation: parsed,
    preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
    toolHashes,
    formalOutputAbsent: true,
    nativeCompileBlenderStartsAuthorized: 0,
    verdict: null,
  }, 'attemptHash');
  const admissionPath = resolve(attemptPath, 'admission.json');
  const admission = await writeDurableHashed(admissionPath, {
    schemaVersion: 'bfs.cinematicSequenceConsistencyAdmission.v0.1',
    sequence: 2,
    status: 'ACCEPTED',
    attempt: { uri: repoUri(outerAttemptPath), sha256: await sha256File(outerAttemptPath), attemptHash: outerAttempt.attemptHash },
    toolFreezeCommit: parsed.toolFreezeCommit,
    preflightEvidenceCommit: parsed.preflightEvidenceCommit,
    output: { uri: parsed.formalRoot, fresh: true },
    nativeCompileBlenderStartsAuthorized: 6,
    verdict: null,
  }, 'admissionHash');
  const attemptReceiptPath = resolve(attemptPath, 'receipt.json');
  const attemptReceipt = await writeDurableHashed(attemptReceiptPath, {
    schemaVersion: 'bfs.cinematicSequenceConsistencyAttemptReceipt.v0.1',
    sequence: 3,
    status: 'ACCEPTED',
    admission: { uri: repoUri(admissionPath), sha256: await sha256File(admissionPath), admissionHash: admission.admissionHash },
    formalOutputAuthorized: true,
    nativeCompileBlenderStartsAuthorized: 6,
    verdict: null,
  }, 'receiptHash');

  await durableMkdir(formalPath);
  await durableMkdir(resolve(formalPath, 'runs'));
  await durableMkdir(resolve(attemptPath, 'cases'));
  await durableMkdir(resolve(attemptPath, 'runner-processes'));
  await writeDurableHashed(resolve(formalPath, 'formal-start.json'), {
    schemaVersion: 'bfs.cinematicSequenceConsistencyFormalStart.v0.1',
    sequence: 4,
    status: 'AUTHORIZED',
    attemptReceipt: { uri: repoUri(attemptReceiptPath), sha256: await sha256File(attemptReceiptPath), receiptHash: attemptReceipt.receiptHash },
    formalRoot: parsed.formalRoot,
    nativeCompileBlenderStartsAuthorized: 6,
  }, 'formalStartHash');

  const processes = [];
  let phase = 'PRODUCTION_COMPILES';
  try {
    for (const item of casesFor(contract)) {
      const child = await runChild([
        'scripts/run-production-blender-compile.mjs',
        '--scene-spec', item.sceneSpec,
        '--preflight-root', `${parsed.preflightRoot}/cases/${item.id}`,
        '--attempt-root', `${parsed.attemptRoot}/cases/${item.id}`,
        '--output-root', `${parsed.formalRoot}/runs/${item.id}`,
        '--preflight-evidence-commit', parsed.preflightEvidenceCommit,
      ]);
      const processRecord = { id: item.id, ...capturedProcess(child) };
      await writeDurableJson(resolve(attemptPath, 'runner-processes', `${item.id}.json`), processRecord);
      processes.push(processRecord);
      if (child.exitCode !== 0 || child.signal !== null) throw new Error(`Production compile failed for ${item.id}: ${child.stderr || child.stdout}`);
      const receiptPath = await resolveExistingRepositoryPath(`${parsed.formalRoot}/runs/${item.id}/production-receipt.json`, `${item.id} production receipt`);
      const receipt = JSON.parse(await readFile(receiptPath, 'utf8'));
      if (!validSelfHash(receipt, 'receiptHash') || receipt.status !== 'PASS') throw new Error(`Production receipt invalid for ${item.id}`);
    }

    phase = 'INDEPENDENT_AUDIT';
    const auditChild = await runChild([
      'scripts/audit-b60-e1-cinematic-sequence-consistency.mjs',
      '--preflight-root', parsed.preflightRoot,
      '--attempt-root', parsed.attemptRoot,
      '--formal-root', parsed.formalRoot,
      '--output', `${parsed.formalRoot}/audit.json`,
    ]);
    const auditProcess = capturedProcess(auditChild);
    await writeDurableJson(resolve(attemptPath, 'runner-processes', 'AUDITOR.json'), { id: 'AUDITOR', ...auditProcess });
    if (auditChild.exitCode !== 0 || auditChild.signal !== null) throw new Error(`Independent auditor failed: ${auditChild.stderr || auditChild.stdout}`);
    const auditPath = await resolveExistingRepositoryPath(`${parsed.formalRoot}/audit.json`, 'B60 audit');
    const audit = JSON.parse(await readFile(auditPath, 'utf8'));
    if (!validSelfHash(audit, 'auditHash') || audit.status !== 'PASS' || audit.verdict !== contract.passVerdict) throw new Error('B60 audit receipt is invalid or non-passing');

    phase = 'FINALIZE';
    const resultsPath = resolve(formalPath, 'results.json');
    const totalElapsedNanoseconds = processes.reduce((sum, row) => sum + row.elapsedNanoseconds, 0);
    const results = await writeDurableHashed(resultsPath, {
      schemaVersion: 'bfs.cinematicSequenceConsistencyResults.v0.1',
      status: 'PASS',
      verdict: contract.passVerdict,
      contract: { uri: CONTRACT_URI, sha256: await sha256File(contractPath) },
      preflight: { uri: repoUri(preflightPath), sha256: await sha256File(preflightPath), preflightHash: preflight.preflightHash },
      audit: { uri: repoUri(auditPath), sha256: await sha256File(auditPath), auditHash: audit.auditHash },
      cases: audit.cases,
      gates: audit.gates,
      attacks: audit.attacks,
      timings: { productionCompileElapsedNanoseconds: totalElapsedNanoseconds, productionCompileElapsedSeconds: totalElapsedNanoseconds / 1e9 },
      operations: audit.operations,
      claimBoundary: contract.claimBoundary,
    }, 'resultsHash');
    const finalReceipt = await writeDurableHashed(resolve(formalPath, 'receipt.json'), {
      schemaVersion: 'bfs.cinematicSequenceConsistencyReceipt.v0.1',
      status: 'PASS',
      verdict: contract.passVerdict,
      authorization: {
        attempt: { uri: repoUri(outerAttemptPath), sha256: await sha256File(outerAttemptPath), attemptHash: outerAttempt.attemptHash },
        admission: { uri: repoUri(admissionPath), sha256: await sha256File(admissionPath), admissionHash: admission.admissionHash },
        attemptReceipt: { uri: repoUri(attemptReceiptPath), sha256: await sha256File(attemptReceiptPath), receiptHash: attemptReceipt.receiptHash },
      },
      results: { uri: repoUri(resultsPath), sha256: await sha256File(resultsPath), resultsHash: results.resultsHash },
      productionCompilerProcesses: processes,
      independentAuditorProcess: auditProcess,
      operations: audit.operations,
      claimBoundary: contract.claimBoundary,
    }, 'receiptHash');
    process.stdout.write(`BFS_B60_FORMAL PASS ${audit.gates.filter(gate => gate.pass).length}/${audit.gates.length} attacks=${audit.attacks.filter(attack => attack.pass).length}/${audit.attacks.length} ${finalReceipt.receiptHash}\n`);
    return finalReceipt;
  } catch (error) {
    await retainInvalidation(formalPath, phase, error, { completedProductionCompiles: processes.length, processes });
    process.stderr.write(`BFS_B60_FORMAL_INVALIDATED ${phase} ${error.message}\n`);
    process.exitCode = 1;
    return null;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB60(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B60_FORMAL_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
