import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot, sha256 } from './scene-spec.mjs';

export const B36_SPEC_PATH = resolve(repositoryRoot, 'specs/autoexec-boundary-spec.v0.1.json');
export const B36_SPEC_SHA256 = '45990fd009ce719dfb25b533276b0aab6e3040a2cf9c0a5f0c2f19c90142a170';
export const B36_PREREG_COMMIT = '541e0a7';
export const B36_CANARY_TOKEN = 'BFS_B36_NONSECRET_CANARY_V1';

export const readB36Spec = async () => {
  const bytes = await readFile(B36_SPEC_PATH);
  const digest = sha256(bytes);
  if (digest !== B36_SPEC_SHA256) throw new Error(`B36 spec SHA mismatch: ${digest}`);
  return JSON.parse(bytes);
};

export function analyzeB36(record) {
  const failures = [];
  const cells = record.cells ?? [];
  const cellById = new Map(cells.map(cell => [cell.id, cell]));
  const expectedIds = ['ENABLE_A', 'ENABLE_B', 'DISABLE_A', 'DISABLE_B', 'FACTORY_DEFAULT_A', 'FACTORY_DEFAULT_B'];
  const requireGate = (condition, code) => {
    if (!condition) failures.push(code);
    return Boolean(condition);
  };

  const exactCells = requireGate(cells.length === expectedIds.length && expectedIds.every(id => cellById.has(id)), 'CELL_SET');
  const pids = cells.map(cell => cell.processId);
  const uniquePositiveProcessIds = requireGate(
    pids.length === 6 && pids.every(pid => Number.isInteger(pid) && pid > 0) && new Set(pids).size === 6,
    'UNIQUE_POSITIVE_PIDS',
  );
  const zeroExitCodes = requireGate(cells.length === 6 && cells.every(cell => cell.exitCode === 0 && cell.timedOut === false), 'PROCESS_EXIT');
  const trustedProbeReports = requireGate(
    cells.length === 6 && cells.every(cell => cell.report && cell.report.processId === cell.processId),
    'TRUSTED_PROBE_REPORTS',
  );
  const runtimeIdentity = requireGate(
    cells.length === 6 && cells.every(cell => cell.report?.blenderVersion === '5.2.0 LTS' && cell.report?.blenderBuildHash === 'fbe6228777e7'),
    'RUNTIME_IDENTITY',
  );
  const registeredText = requireGate(
    cells.length === 6 && cells.every(cell => cell.report?.registeredTextPresent === true && cell.report?.registeredTextUseModule === true),
    'REGISTERED_TEXT_IDENTITY',
  );
  const markerAbsentBeforeEveryLaunch = requireGate(
    cells.length === 6 && cells.every(cell => cell.markerAbsentBeforeLaunch === true),
    'MARKER_PREFLIGHT',
  );
  const enabled = cells.filter(cell => cell.autoexec === 'ENABLE');
  const disabled = cells.filter(cell => cell.autoexec === 'DISABLE');
  const factoryDefault = cells.filter(cell => cell.autoexec === 'FACTORY_DEFAULT');
  const enabledMarkers = requireGate(enabled.length === 2 && enabled.every(cell => cell.marker !== null), 'ENABLED_MARKERS');
  const enabledMarkerTokenExact = requireGate(
    enabled.length === 2 && enabled.every(cell => cell.marker?.token === B36_CANARY_TOKEN),
    'ENABLED_MARKER_TOKEN',
  );
  const enabledMarkerPidEqualsProbePid = requireGate(
    enabled.length === 2 && enabled.every(cell => cell.marker?.processId === cell.report?.processId),
    'ENABLED_MARKER_PID',
  );
  const disabledMarkersAbsent = requireGate(disabled.length === 2 && disabled.every(cell => cell.marker === null), 'DISABLED_MARKER_ABSENCE');
  const factoryDefaultMarkersAbsent = requireGate(
    factoryDefault.length === 2 && factoryDefault.every(cell => cell.marker === null),
    'FACTORY_DEFAULT_MARKER_ABSENCE',
  );
  const sourceBlendByteUnchanged = requireGate(
    typeof record.sourceBlendSha256Pre === 'string' && record.sourceBlendSha256Pre === record.sourceBlendSha256Post,
    'SOURCE_BLEND_SHA',
  );

  let decision = 'REGISTERED_TEXT_AUTOEXEC_FLAG_BOUNDARY_SUPPORT';
  if (disabled.some(cell => cell.marker?.token === B36_CANARY_TOKEN)) decision = 'AUTOEXEC_DISABLE_INSUFFICIENT';
  else if (!runtimeIdentity || !registeredText || !enabledMarkers) decision = 'IDENTITY_OR_DESIGN_INVALID';
  else if (failures.length > 0) decision = 'RUN_INVALID';

  return {
    schemaVersion: 'bfs.autoexecBoundaryAnalysis.v0.1',
    decision,
    passed: failures.length === 0,
    failures,
    gates: {
      exactCells,
      uniquePositiveProcessIds,
      zeroExitCodes,
      trustedProbeReports,
      runtimeIdentity,
      registeredText,
      markerAbsentBeforeEveryLaunch,
      enabledMarkers,
      enabledMarkerTokenExact,
      enabledMarkerPidEqualsProbePid,
      disabledMarkersAbsent,
      factoryDefaultMarkersAbsent,
      sourceBlendByteUnchanged,
    },
  };
}

const clone = value => structuredClone(value);

export function runB36AnalyzerAttacks(record) {
  const firstEnabled = record.cells.find(cell => cell.autoexec === 'ENABLE');
  if (!firstEnabled?.marker) throw new Error('B36 attacks require a valid enabled marker fixture');
  const attacks = [
    ['UNEXPECTED_DISABLE_MARKER', draft => { draft.cells.find(cell => cell.autoexec === 'DISABLE').marker = clone(firstEnabled.marker); }],
    ['UNEXPECTED_FACTORY_DEFAULT_MARKER', draft => { draft.cells.find(cell => cell.autoexec === 'FACTORY_DEFAULT').marker = clone(firstEnabled.marker); }],
    ['MISSING_ENABLE_MARKER', draft => { draft.cells.find(cell => cell.autoexec === 'ENABLE').marker = null; }],
    ['WRONG_CANARY_TOKEN', draft => { draft.cells.find(cell => cell.autoexec === 'ENABLE').marker.token = 'WRONG'; }],
    ['MARKER_PID_MISMATCH', draft => { draft.cells.find(cell => cell.autoexec === 'ENABLE').marker.processId += 1; }],
    ['DUPLICATE_PROCESS_PID', draft => { draft.cells[1].processId = draft.cells[0].processId; draft.cells[1].report.processId = draft.cells[0].processId; }],
    ['SOURCE_BLEND_SHA_MUTATION', draft => { draft.sourceBlendSha256Post = '0'.repeat(64); }],
  ];
  return attacks.map(([id, mutate]) => {
    const draft = clone(record);
    mutate(draft);
    const analysis = analyzeB36(draft);
    return { id, passed: analysis.passed === false, observedDecision: analysis.decision, failures: analysis.failures };
  });
}
