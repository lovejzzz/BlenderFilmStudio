import { readFile, writeFile, lstat, readdir } from 'node:fs/promises';
import { resolve, isAbsolute } from 'node:path';
import { canonicalize, canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';

const FREEZE_URI = 'specs/ai-native-studio-visual-plan-typed-execution-tool-freeze-c1.v0.2.json';
const CONTEXT_URI = 'specs/fixtures/visual-review/PC4_ATTEMPT03.execution-context-c1.v0.2.json';

function requireCondition(condition, message) {
  if (!condition) throw new Error(message);
}

function safeRepositoryPath(uri) {
  requireCondition(typeof uri === 'string' && !isAbsolute(uri) && !uri.split('/').includes('..'), `unsafe uri ${uri}`);
  const path = resolve(repositoryRoot, uri);
  requireCondition(path.startsWith(`${repositoryRoot}/`), `outside repository ${uri}`);
  return path;
}

async function boundJson(uri) {
  const path = safeRepositoryPath(uri);
  const stat = await lstat(path);
  requireCondition(stat.isFile() && !stat.isSymbolicLink(), `not regular ${uri}`);
  const bytes = await readFile(path);
  return { uri, path, bytes, sha256: sha256(bytes), value: JSON.parse(bytes) };
}

async function sha256File(path) {
  return sha256(await readFile(path));
}

function selfHash(value, key) {
  const projection = structuredClone(value);
  delete projection[key];
  return sha256(canonicalJson(projection));
}

async function listFiles(path, prefix = '') {
  const rows = [];
  for (const entry of await readdir(path, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    const absolute = resolve(path, entry.name);
    if (entry.isDirectory()) rows.push(...await listFiles(absolute, relative));
    else if (entry.isFile()) rows.push(relative);
    else rows.push(`SPECIAL:${relative}`);
  }
  return rows.sort();
}

function cameraTransformProjection(state) {
  return state.map(row => ({ frame: row.frame, cameras: Object.fromEntries(Object.entries(row.cameras).map(([name, value]) => [name, value.matrixWorld])) }));
}

const [freeze, context] = await Promise.all([boundJson(FREEZE_URI), boundJson(CONTEXT_URI)]);
const rootUri = context.value.roots.evidence;
const rootPath = safeRepositoryPath(rootUri);
const auditPath = resolve(rootPath, 'independent-audit.json');
try {
  await lstat(auditPath);
  throw new Error('independent audit already exists');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}
const [plan, packet, build, reopen, receipt, buildProcess, reopenProcess] = await Promise.all([
  boundJson(context.value.plan.uri),
  boundJson(context.value.packet.uri),
  boundJson(`${rootUri}/build.json`),
  boundJson(`${rootUri}/reopen-audit.json`),
  boundJson(`${rootUri}/receipt.json`),
  boundJson(`${rootUri}/processes/01-build.json`),
  boundJson(`${rootUri}/processes/02-reopen.json`),
]);
const rootFiles = await listFiles(rootPath);
const workFiles = await listFiles(context.value.roots.work);
const pngRows = build.value.screenshots ?? [];
const pngChecks = [];
for (const row of pngRows) {
  const bytes = await readFile(row.uri);
  pngChecks.push(bytes.length === row.bytes && sha256(bytes) === row.sha256 && bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])));
}
const expectedAdapters = new Set([
  'SET_SHOT_VISIBILITY:HIDE_CONFIRMED_FOREGROUND_OCCLUDER',
  'APPLY_FRAMING_PRESET:READABLE_SUBJECT_FRAMING',
  'REPLACE_FORM_WITH_ASSEMBLY:LAYERED_MECHANICAL_JOINT',
  'ADD_DETAIL_SYSTEM:FACIAL_SEGMENTATION',
  'ADD_DETAIL_SYSTEM:MID_SCALE_PANEL_HIERARCHY',
]);
const observedAdapters = new Set(build.value.effects?.map(row => `${row.operationType}:${row.preset}`));
const semanticCounts = Object.fromEntries(build.value.createdParts.reduce((entries, row) => entries.set(row.semantic, (entries.get(row.semantic) ?? 0) + 1), new Map()));
const framingEffects = build.value.effects?.filter(row => row.operationType === 'APPLY_FRAMING_PRESET').flatMap(row => row.effects) ?? [];
const visibilityEffects = build.value.effects?.find(row => row.operationType === 'SET_SHOT_VISIBILITY')?.effects ?? [];
const planProjection = structuredClone(plan.value);
delete planProjection.planHash;
const checks = [
  ['A01_FREEZE_SELF_HASH', freeze.value.freezeHash === selfHash(freeze.value, 'freezeHash')],
  ['A02_CONTEXT_SELF_HASH', context.value.contextHash === selfHash(context.value, 'contextHash')],
  ['A03_PLAN_FILE_AND_SELF_HASH', plan.sha256 === context.value.plan.sha256 && plan.value.planHash === context.value.plan.planHash && plan.value.planHash === sha256(canonicalJson(planProjection))],
  ['A04_PACKET_FILE_HASH', packet.sha256 === context.value.packet.sha256],
  ['A05_BUILD_SELF_HASH', build.value.buildHash === selfHash(build.value, 'buildHash')],
  ['A06_REOPEN_SELF_HASH', reopen.value.auditHash === selfHash(reopen.value, 'auditHash') && reopen.value.status === 'PASS'],
  ['A07_RECEIPT_SELF_HASH', receipt.value.receiptHash === selfHash(receipt.value, 'receiptHash')],
  ['A08_BUILD_RECEIPT_BINDING', receipt.value.build?.sha256 === build.sha256 && receipt.value.build?.buildHash === build.value.buildHash],
  ['A09_REOPEN_RECEIPT_BINDING', receipt.value.reopen?.sha256 === reopen.sha256 && receipt.value.reopen?.auditHash === reopen.value.auditHash],
  ['A10_SOURCE_IDENTITY', await sha256File(context.value.source.path) === context.value.source.sha256 && build.value.source?.beforeSha256 === context.value.source.sha256 && build.value.source?.afterSha256 === context.value.source.sha256],
  ['A11_DERIVED_IDENTITY', await sha256File(build.value.derived.path) === build.value.derived.sha256 && build.value.derived.sha256 !== context.value.source.sha256],
  ['A12_EXACT_SIX_OPERATIONS', plan.value.operations?.length === 6 && build.value.operationsConsumed === 6 && receipt.value.operationCounts?.blenderStarts === 2],
  ['A13_TYPED_ADAPTER_ROSTER', [...expectedAdapters].every(value => observedAdapters.has(value)) && observedAdapters.size === expectedAdapters.size],
  ['A14_CREATED_PART_FLOORS', build.value.createdParts?.length >= 28 && semanticCounts.LAYERED_MECHANICAL_JOINT >= 12 && semanticCounts.FACIAL_SEGMENTATION >= 7 && semanticCounts.MID_SCALE_PANEL_HIERARCHY >= 9],
  ['A15_VISIBILITY_EFFECTS', visibilityEffects.length === 2 && visibilityEffects.every(row => row.frameStart === 1 && row.frameEnd === 96 && row.prior === false) && reopen.value.visibilityRoundTrip === true],
  ['A16_FRAMING_BOUNDS', framingEffects.length === 2 && framingEffects.every(row => row.absoluteChangePercent === 12 && row.absoluteChangePercent <= 15)],
  ['A17_CAMERA_TRANSFORMS_EXACT', canonicalJson(cameraTransformProjection(build.value.protectedStateBefore)) === canonicalJson(cameraTransformProjection(build.value.protectedStateAfter))],
  ['A18_LIGHT_STATE_EXACT', build.value.protectedStateBefore.every((row, index) => canonicalJson(row.lights) === canonicalJson(build.value.protectedStateAfter[index].lights))],
  ['A19_THREE_BOUND_PNGS', pngRows.length === 3 && pngChecks.every(Boolean) && pngRows.map(row => row.frame).join(',') === '48,144,240'],
  ['A20_ZERO_EXR_AND_SPECIAL_FILES', !rootFiles.some(path => path.startsWith('SPECIAL:') || /\.exr$/i.test(path)) && !workFiles.some(path => path.startsWith('SPECIAL:') || /\.exr$/i.test(path))],
  ['A21_PROCESS_EVIDENCE', buildProcess.value.exitCode === 0 && reopenProcess.value.exitCode === 0 && buildProcess.value.peakRssBytes <= 4294967296 && reopenProcess.value.peakRssBytes <= 4294967296],
  ['A22_RESOURCE_CEILINGS', receipt.value.resources?.workRootBytes <= 1073741824 && receipt.value.resources?.evidenceRootBytesBeforeReceipt <= 67108864 && receipt.value.resources?.wallSeconds <= 900],
  ['A23_OPERATION_COUNTS', receipt.value.operationCounts?.renderCalls === 3 && receipt.value.operationCounts?.derivedSceneSaves === 1 && receipt.value.operationCounts?.reopenAudits === 1 && receipt.value.operationCounts?.retainedExr === 0],
  ['A24_ZERO_NETWORK_MODEL_MOUSE', receipt.value.operationCounts?.networkCalls === 0 && receipt.value.operationCounts?.modelCallsDuringExecution === 0 && receipt.value.operationCounts?.mouseInteractions === 0],
  ['A25_VISUAL_REVIEW_STILL_PENDING', receipt.value.status === 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED' && receipt.value.visualVerdict === 'PENDING_DIRECT_MODEL_REVIEW'],
];
const passed = checks.filter(([, value]) => value).length;
const audit = {
  schemaVersion: 'bfs.visualPlanTypedExecutionIndependentAudit.v0.1',
  experimentId: 'PC4-VX1',
  status: passed === checks.length ? 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED' : 'FAIL',
  checks: checks.map(([id, value]) => ({ id, passed: Boolean(value) })),
  counts: { passed, total: checks.length },
  bindings: {
    freeze: { uri: FREEZE_URI, sha256: freeze.sha256, freezeHash: freeze.value.freezeHash },
    context: { uri: CONTEXT_URI, sha256: context.sha256, contextHash: context.value.contextHash },
    plan: { uri: plan.uri, sha256: plan.sha256, planHash: plan.value.planHash },
    build: { uri: build.uri, sha256: build.sha256, buildHash: build.value.buildHash },
    reopen: { uri: reopen.uri, sha256: reopen.sha256, auditHash: reopen.value.auditHash },
    receipt: { uri: receipt.uri, sha256: receipt.sha256, receiptHash: receipt.value.receiptHash },
  },
  semanticCounts,
  operationCounts: receipt.value.operationCounts,
  visualVerdict: 'PENDING_DIRECT_MODEL_REVIEW',
  auditHash: '',
};
audit.auditHash = selfHash(audit, 'auditHash');
await writeFile(auditPath, `${JSON.stringify(canonicalize(audit), null, 2)}\n`, { flag: 'wx' });
process.stdout.write(`BFS_TYPED_VISUAL_AUDIT ${audit.status} ${passed}/${checks.length} ${audit.auditHash}\n`);
if (audit.status === 'FAIL') process.exitCode = 1;
