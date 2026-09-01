import { readFile, writeFile, lstat } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { canonicalize, canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';

const freezeUri = 'specs/ai-native-studio-visual-understanding-tool-freeze-c1.v0.2.json';

function requireCondition(condition, message) {
  if (!condition) throw new Error(message);
}

function safeUri(uri) {
  requireCondition(typeof uri === 'string' && !uri.startsWith('/') && !uri.split('/').includes('..'), `unsafe uri ${uri}`);
  const absolute = resolve(repositoryRoot, uri);
  requireCondition(absolute === repositoryRoot || absolute.startsWith(`${repositoryRoot}/`), `outside repository ${uri}`);
  return absolute;
}

async function readBound(uri) {
  const path = safeUri(uri);
  const stat = await lstat(path);
  requireCondition(stat.isFile() && !stat.isSymbolicLink(), `not regular ${uri}`);
  const bytes = await readFile(path);
  return { uri, path, bytes, sha256: sha256(bytes), value: JSON.parse(bytes) };
}

function selfHash(value, key) {
  const projection = structuredClone(value);
  delete projection[key];
  return sha256(canonicalJson(projection));
}

const [rootArgument] = process.argv.slice(2);
requireCondition(rootArgument && process.argv.length === 3, 'usage: node scripts/audit-visual-understanding-loop.mjs <evidence-root>');
const rootUri = rootArgument.replace(/\/$/, '');
requireCondition(rootUri.startsWith('experiments/visual-understanding-loop/'), 'unexpected evidence root');
const rootPath = safeUri(rootUri);
const auditPath = resolve(rootPath, 'independent-audit.json');
try {
  await lstat(auditPath);
  throw new Error('independent audit already exists');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}

const [freeze, receipt, plan, tests, planSchema, packet, assessment] = await Promise.all([
  readBound(freezeUri),
  readBound(`${rootUri}/receipt.json`),
  readBound(`${rootUri}/visual-improvement-plan.json`),
  readBound(`${rootUri}/logs/contract-tests.tap`),
  readBound('specs/visual-improvement-plan.v0.1.schema.json'),
  readBound('specs/fixtures/visual-review/PC4_ATTEMPT03.packet.json'),
  readBound('specs/fixtures/visual-review/PC4_ATTEMPT03.teacher-assessment.json'),
]);
const validatePlan = new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true }).compile(planSchema.value);
const planProjection = structuredClone(plan.value);
delete planProjection.planHash;
const expectedPlanHash = sha256(canonicalJson(planProjection));
const expectedPreservations = new Set(['PRESERVE_ACCEPTED_CAMERA_LANGUAGE', 'PRESERVE_ACCEPTED_LIGHTING']);
const expectedPresets = new Set([
  'HIDE_CONFIRMED_FOREGROUND_OCCLUDER',
  'READABLE_SUBJECT_FRAMING',
  'LAYERED_MECHANICAL_JOINT',
  'FACIAL_SEGMENTATION',
  'MID_SCALE_PANEL_HIERARCHY',
]);
const checks = [
  ['A01_FREEZE_SCHEMA', freeze.value.schemaVersion === 'bfs.visualUnderstandingToolFreezeC1.v0.2'],
  ['A01B_FREEZE_SELF_HASH', freeze.value.freezeHash === selfHash(freeze.value, 'freezeHash')],
  ['A02_RECEIPT_SCHEMA', receipt.value.schemaVersion === 'bfs.visualUnderstandingLoopReceipt.v0.1' && receipt.value.experimentId === 'PC4-VU1'],
  ['A03_RECEIPT_SELF_HASH', receipt.value.receiptHash === selfHash(receipt.value, 'receiptHash')],
  ['A04_PLAN_SCHEMA', validatePlan(plan.value) === true],
  ['A05_PLAN_SELF_HASH', plan.value.planHash === expectedPlanHash],
  ['A06_PLAN_FILE_BINDING', receipt.value.outputs?.plan?.sha256 === plan.sha256 && receipt.value.outputs?.plan?.planHash === plan.value.planHash],
  ['A07_PACKET_BINDING', receipt.value.inputs?.packet?.sha256 === packet.sha256 && plan.value.source?.packetSha256 === packet.sha256 && assessment.value.packetSha256 === packet.sha256],
  ['A08_ASSESSMENT_BINDING', receipt.value.inputs?.assessment?.sha256 === assessment.sha256 && plan.value.source?.assessmentSha256 === assessment.sha256],
  ['A09_SCENE_BINDING', plan.value.source?.sceneSha256 === packet.value.scene?.sha256 && receipt.value.inputs?.sceneSha256 === packet.value.scene?.sha256],
  ['A10_TEST_LOG_BINDING', receipt.value.outputs?.contractTests?.sha256 === tests.sha256 && tests.bytes.toString('utf8').includes('# pass 19') && tests.bytes.toString('utf8').includes('# fail 0')],
  ['A11_DETERMINISTIC_RECEIPT', receipt.value.compiler?.repeatedCanonicalBytesExact === true],
  ['A12_EXPECTED_COUNTS', plan.value.operations?.length === 6 && plan.value.preservations?.length === 2 && plan.value.rerenderSet?.length === 3],
  ['A13_EXPECTED_TREATMENTS', [...expectedPresets].every(item => plan.value.operations?.some(operation => operation.preset === item))],
  ['A14_STRENGTH_PRESERVATION', [...expectedPreservations].every(item => plan.value.preservations?.some(row => row.rule === item))],
  ['A15_NO_EXECUTABLE_AUTHORITY', plan.value.authority?.allowsPython === false && plan.value.authority?.allowsShell === false && plan.value.authority?.allowsNetwork === false && plan.value.authority?.allowsArbitraryFilesystem === false],
  ['A16_ZERO_BLENDER_MUTATION', receipt.value.operationCounts?.blenderStarts === 0 && receipt.value.operationCounts?.renders === 0 && receipt.value.operationCounts?.sceneMutations === 0],
  ['A17_ZERO_MODEL_NETWORK_EXECUTION', receipt.value.operationCounts?.networkCalls === 0 && receipt.value.operationCounts?.modelCallsDuringCompilerExecution === 0 && receipt.value.operationCounts?.shellOrPythonFromAssessment === 0],
  ['A18_ALL_OPERATIONS_PROVENANCED', plan.value.operations?.every(operation => operation.issueId && operation.evidenceFrameIds?.length > 0 && operation.targetEntityIds?.length > 0 && operation.shotIds?.length > 0)],
  ['A19_NO_DEFERRED_FIXTURE_ISSUES', plan.value.deferredIssues?.length === 0 && plan.value.decision === 'COMPILED'],
];
const passed = checks.filter(([, value]) => value).length;
const audit = {
  schemaVersion: 'bfs.visualUnderstandingLoopIndependentAudit.v0.1',
  experimentId: 'PC4-VU1',
  status: passed === checks.length ? 'PASS' : 'FAIL',
  checks: checks.map(([id, value]) => ({ id, passed: Boolean(value) })),
  counts: { passed, total: checks.length },
  bindings: {
    freeze: { uri: freeze.uri, sha256: freeze.sha256 },
    receipt: { uri: receipt.uri, sha256: receipt.sha256, receiptHash: receipt.value.receiptHash },
    plan: { uri: plan.uri, sha256: plan.sha256, planHash: plan.value.planHash },
    packet: { uri: packet.uri, sha256: packet.sha256 },
    assessment: { uri: assessment.uri, sha256: assessment.sha256 },
  },
  operationCounts: { blenderStarts: 0, renders: 0, sceneMutations: 0, networkCalls: 0, modelCalls: 0 },
  auditHash: '',
};
audit.auditHash = selfHash(audit, 'auditHash');
await writeFile(auditPath, `${JSON.stringify(canonicalize(audit), null, 2)}\n`, { flag: 'wx' });
process.stdout.write(`BFS_VISUAL_UNDERSTANDING_AUDIT ${audit.status} ${passed}/${checks.length} ${audit.auditHash}\n`);
if (audit.status !== 'PASS') process.exitCode = 1;
