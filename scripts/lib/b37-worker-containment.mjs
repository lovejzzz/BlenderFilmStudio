import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B37_SPEC_PATH = resolve(repositoryRoot, 'specs/worker-containment-spec.v0.1.json');
export const B37_SPEC_SHA256 = 'f1069f81a40abf407323f0df3be8b343d6123330201330f1cc12f049fccc7005';
export const B37_PREREG_COMMIT = '5b9a85c';
export const B37_FAKE_SECRET = 'BFS_B37_NONSECRET_ENV_CANARY_V1';

export const readB37Spec = async () => {
  const bytes = await readFile(B37_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B37_SPEC_SHA256) throw new Error(`B37 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
};

const success = (cell, capability) => cell.report?.capabilities?.[capability]?.success === true;

export function analyzeB37(record) {
  const failures = [];
  const requireGate = (condition, code) => {
    if (!condition) failures.push(code);
    return Boolean(condition);
  };
  const cells = record.cells ?? [];
  const expectedIds = [
    'UNSANDBOXED_A', 'UNSANDBOXED_B',
    'SBPL_INHERITED_A', 'SBPL_INHERITED_B',
    'SBPL_SANITIZED_A', 'SBPL_SANITIZED_B',
  ];
  const exactCells = requireGate(cells.length === 6 && expectedIds.every(id => cells.some(cell => cell.id === id)), 'CELL_SET');
  const pids = cells.map(cell => cell.processId);
  const uniquePositiveBlenderProcessIds = requireGate(
    pids.length === 6 && pids.every(pid => Number.isInteger(pid) && pid > 0) && new Set(pids).size === 6,
    'UNIQUE_POSITIVE_PIDS',
  );
  const zeroExitCodes = requireGate(cells.length === 6 && cells.every(cell => cell.exitCode === 0 && cell.timedOut === false), 'PROCESS_EXIT');
  const reports = requireGate(cells.length === 6 && cells.every(cell => cell.report?.processId === cell.processId), 'REPORTS');
  const runtimeIdentity = requireGate(
    cells.length === 6 && cells.every(cell => cell.report?.blenderVersion === '5.2.0 LTS' && cell.report?.blenderBuildHash === 'fbe6228777e7'),
    'RUNTIME_IDENTITY',
  );
  const cleanPreflight = requireGate(cells.length === 6 && cells.every(cell => cell.cleanPreflight === true), 'CLEAN_PREFLIGHT');
  const unsandboxed = cells.filter(cell => cell.class === 'UNSANDBOXED');
  const inherited = cells.filter(cell => cell.class === 'SBPL_INHERITED');
  const sanitized = cells.filter(cell => cell.class === 'SBPL_SANITIZED');
  const sandboxed = [...inherited, ...sanitized];
  const baselineCanariesSucceed = requireGate(
    unsandboxed.length === 2 && unsandboxed.every(cell =>
      ['allowedWrite', 'outsideRead', 'outsideWrite', 'loopbackConnect', 'childExec', 'fakeSecretVisible'].every(capability => success(cell, capability))),
    'BASELINE_CANARIES',
  );
  const sbplCapabilityBlocks = requireGate(
    sandboxed.length === 4 && sandboxed.every(cell =>
      ['outsideRead', 'outsideWrite', 'loopbackConnect', 'childExec'].every(capability => !success(cell, capability))),
    'SBPL_CAPABILITY_BLOCKS',
  );
  const allowedWorkerWrites = requireGate(cells.length === 6 && cells.every(cell => success(cell, 'allowedWrite')), 'ALLOWED_WORKER_WRITES');
  const inheritedFakeSecretCounterexample = requireGate(
    inherited.length === 2 && inherited.every(cell => success(cell, 'fakeSecretVisible')),
    'INHERITED_ENV_COUNTEREXAMPLE',
  );
  const sanitizedFakeSecret = requireGate(
    sanitized.length === 2 && sanitized.every(cell => !success(cell, 'fakeSecretVisible')),
    'SANITIZED_ENV',
  );
  const loopbackReceiptBinding = requireGate(
    unsandboxed.length === 2 && sandboxed.length === 4
      && unsandboxed.every(cell => cell.loopbackReceipts?.length === 1 && cell.loopbackReceipts[0] === cell.loopbackNonce)
      && sandboxed.every(cell => cell.loopbackReceipts?.length === 0),
    'LOOPBACK_RECEIPTS',
  );

  let decision = 'DEPRECATED_SBPL_CANARY_SUPPORT_WITH_ENV_COUNTEREXAMPLE';
  if (!baselineCanariesSucceed) decision = 'BASELINE_INVALID';
  else if (!zeroExitCodes || !reports || !sbplCapabilityBlocks || !allowedWorkerWrites) decision = 'SBPL_BOUNDARY_NOT_USABLE';
  else if (failures.length > 0) decision = 'RUN_INVALID';
  return {
    schemaVersion: 'bfs.workerContainmentAnalysis.v0.1',
    decision,
    passed: failures.length === 0,
    failures,
    gates: {
      exactCells,
      uniquePositiveBlenderProcessIds,
      zeroExitCodes,
      reports,
      runtimeIdentity,
      cleanPreflight,
      baselineCanariesSucceed,
      sbplCapabilityBlocks,
      allowedWorkerWrites,
      inheritedFakeSecretCounterexample,
      sanitizedFakeSecret,
      loopbackReceiptBinding,
    },
  };
}

const clone = value => structuredClone(value);

export function runB37AnalyzerAttacks(record) {
  const attacks = [
    ['SANDBOX_OUTSIDE_READ_SUCCESS', draft => { draft.cells.find(cell => cell.sandbox).report.capabilities.outsideRead.success = true; }],
    ['SANDBOX_OUTSIDE_WRITE_SUCCESS', draft => { draft.cells.find(cell => cell.sandbox).report.capabilities.outsideWrite.success = true; }],
    ['SANDBOX_LOOPBACK_SUCCESS', draft => { draft.cells.find(cell => cell.sandbox).report.capabilities.loopbackConnect.success = true; }],
    ['SANDBOX_CHILD_EXEC_SUCCESS', draft => { draft.cells.find(cell => cell.sandbox).report.capabilities.childExec.success = true; }],
    ['MISSING_ALLOWED_WORKER_WRITE', draft => { draft.cells[0].report.capabilities.allowedWrite.success = false; }],
    ['MISSING_INHERITED_ENV_COUNTEREXAMPLE', draft => { draft.cells.find(cell => cell.class === 'SBPL_INHERITED').report.capabilities.fakeSecretVisible.success = false; }],
    ['SANITIZED_SECRET_VISIBLE', draft => { draft.cells.find(cell => cell.class === 'SBPL_SANITIZED').report.capabilities.fakeSecretVisible.success = true; }],
    ['DUPLICATE_BLENDER_PID', draft => { draft.cells[1].processId = draft.cells[0].processId; draft.cells[1].report.processId = draft.cells[0].processId; }],
    ['SANDBOX_LOOPBACK_RECEIPT', draft => { const cell = draft.cells.find(item => item.sandbox); cell.loopbackReceipts = [cell.loopbackNonce]; }],
  ];
  return attacks.map(([id, mutate]) => {
    const draft = clone(record);
    mutate(draft);
    const analysis = analyzeB37(draft);
    return { id, passed: analysis.passed === false, observedDecision: analysis.decision, failures: analysis.failures };
  });
}
