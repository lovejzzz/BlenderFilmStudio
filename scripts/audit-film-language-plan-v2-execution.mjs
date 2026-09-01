import { readFile, writeFile, lstat, readdir } from 'node:fs/promises';
import { resolve, isAbsolute } from 'node:path';
import { canonicalize, canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';

const FREEZE_URI = 'specs/ai-native-studio-film-language-typed-executor-tool-freeze.v0.1.json';
const CONTEXT_URI = 'specs/fixtures/visual-review/PC4_VX2.execution-context.v0.1.json';
function requireCondition(value, message) { if (!value) throw new Error(message); }
function safe(uri) { requireCondition(typeof uri === 'string' && !isAbsolute(uri) && !uri.split('/').includes('..'), 'unsafe uri'); const path = resolve(repositoryRoot, uri); requireCondition(path.startsWith(`${repositoryRoot}/`), 'outside repo'); return path; }
async function hash(path) { return sha256(await readFile(path)); }
function self(value, field) { const copy = structuredClone(value); delete copy[field]; return sha256(canonicalJson(copy)); }
async function treeBytes(path) { const stat = await lstat(path); if (stat.isFile()) return stat.size; if (!stat.isDirectory()) return 0; let total = 0; for (const entry of await readdir(path)) total += await treeBytes(resolve(path, entry)); return total; }
function check(rows, id, passed, observed = null) { rows.push({ id, passed: Boolean(passed), ...(observed === null ? {} : { observed }) }); }

const freeze = JSON.parse(await readFile(safe(FREEZE_URI))), context = JSON.parse(await readFile(safe(CONTEXT_URI)));
const root = safe(context.roots.evidence), work = context.roots.work;
const buildPath = resolve(root, 'build.json'), reopenPath = resolve(root, 'reopen-audit.json'), receiptPath = resolve(root, 'receipt.json');
const build = JSON.parse(await readFile(buildPath)), reopen = JSON.parse(await readFile(reopenPath)), receipt = JSON.parse(await readFile(receiptPath));
const plan = JSON.parse(await readFile(safe(context.plan.uri))), packet = JSON.parse(await readFile(safe(context.packet.uri)));
const checks = [];
check(checks, 'A01_FREEZE_SELF_HASH', freeze.freezeHash === self(freeze, 'freezeHash'));
check(checks, 'A02_CONTEXT_SELF_HASH', context.contextHash === self(context, 'contextHash'));
check(checks, 'A03_ALL_FROZEN_INPUTS', (await Promise.all(freeze.inputs.map(async row => await hash(safe(row.uri)) === row.sha256))).every(Boolean));
check(checks, 'A04_PLAN_PACKET_BINDING', await hash(safe(context.plan.uri)) === context.plan.sha256 && plan.planHash === context.plan.planHash && await hash(safe(context.packet.uri)) === context.packet.sha256);
check(checks, 'A05_EXTERNAL_IDENTITIES', await hash(context.source.path) === context.source.sha256 && await hash(context.binary.path) === context.binary.sha256);
check(checks, 'A06_BUILD_SELF_HASH', build.buildHash === self(build, 'buildHash'));
check(checks, 'A07_REOPEN_SELF_HASH', reopen.auditHash === self(reopen, 'auditHash'));
check(checks, 'A08_RECEIPT_SELF_HASH', receipt.receiptHash === self(receipt, 'receiptHash'));
check(checks, 'A09_EVIDENCE_BINDINGS', receipt.build.sha256 === await hash(buildPath) && receipt.reopen.sha256 === await hash(reopenPath));
check(checks, 'A10_DERIVED_IDENTITY', await hash(build.derived.path) === build.derived.sha256 && receipt.derived.sha256 === build.derived.sha256);
check(checks, 'A11_EXACT_FIVE_OPERATIONS', plan.operations.length === 5 && build.operationsConsumed.length === 5 && new Set(build.operationsConsumed).size === 5);
const presets = new Set(build.effects.map(row => row.preset));
check(checks, 'A12_TYPED_PRESET_ROSTER', ['HIDE_NEAREST_NONSTORY_OCCLUDER', 'FIT_BOUND_SUBJECT_WITH_MARGIN', 'CONCENTRIC_CORE_SHELL_GAP', 'LANDMARK_DRIVEN_FACEPLATE', 'SPARSE_HIERARCHICAL_PANELING'].every(value => presets.has(value)));
const occlusion = build.effects.find(row => row.preset === 'HIDE_NEAREST_NONSTORY_OCCLUDER').result;
check(checks, 'A13_SCREENSPACE_OCCLUSION', occlusion.hidden.length > 0 && Number(occlusion.afterMaximumOcclusionRatio) <= Number(occlusion.maximumOcclusionRatio));
const framing = build.effects.find(row => row.preset === 'FIT_BOUND_SUBJECT_WITH_MARGIN').result;
check(checks, 'A14_MEASURED_FRAMING', Number(framing.afterOccupancy) <= Number(framing.targetRange[1]) + 0.01 && Number(framing.measuredMargin) >= Number(framing.requiredMargin) - 0.01, framing);
const formEffects = build.effects.filter(row => ['CONCENTRIC_CORE_SHELL_GAP', 'LANDMARK_DRIVEN_FACEPLATE', 'SPARSE_HIERARCHICAL_PANELING'].includes(row.preset));
const formRows = formEffects.flatMap(row => Array.isArray(row.result) ? row.result : [row.result]);
check(checks, 'A15_RELIEF_CAPS', formRows.every(row => Number(row.reliefRatio) <= Number(row.reliefCap) + 1e-9));
check(checks, 'A16_COVERAGE_CAPS', formRows.every(row => Number(row.coverageRatio) <= Number(row.coverageCap) + 1e-9));
check(checks, 'A17_THREE_SCALE_BANDS', formRows.every(row => canonicalJson(row.scaleBands) === canonicalJson([1, 2, 3])));
const face = build.effects.find(row => row.preset === 'LANDMARK_DRIVEN_FACEPLATE').result;
check(checks, 'A18_FOUR_FACE_ZONES', canonicalJson(face.zones) === canonicalJson(['EYE_LINE', 'BROW', 'CHEEK', 'JAW']) && canonicalJson(reopen.faceZones) === canonicalJson(['BROW', 'CHEEK', 'EYE_LINE', 'JAW']));
const cameraMatrices = rows => rows.map(row => ({ frame: row.frame, cameras: Object.fromEntries(Object.entries(row.cameras).map(([name, value]) => [name, value.matrixWorld])) }));
check(checks, 'A19_CAMERA_TRANSFORMS_EXACT', canonicalJson(cameraMatrices(build.protectedStateBefore)) === canonicalJson(cameraMatrices(build.protectedStateAfter)));
check(checks, 'A20_LIGHTS_EXACT', build.protectedStateBefore.every((row, index) => canonicalJson(row.lights) === canonicalJson(build.protectedStateAfter[index].lights)));
check(checks, 'A21_REOPEN_EXACT', reopen.protectedStateExact === true && reopen.parts === build.createdParts.length);
check(checks, 'A22_THREE_BOUND_PNGS', build.screenshots.length === 3 && (await Promise.all(build.screenshots.map(async row => await hash(row.uri) === row.sha256))).every(Boolean));
const allFiles = async path => { const rows = []; for (const entry of await readdir(path, { withFileTypes: true })) { const full = resolve(path, entry.name); if (entry.isDirectory()) rows.push(...await allFiles(full)); else rows.push(full); } return rows; };
const files = [...await allFiles(root), ...await allFiles(work)];
check(checks, 'A23_ZERO_RETAINED_EXR', files.every(path => !path.toLowerCase().endsWith('.exr')));
check(checks, 'A24_PROCESS_COUNTS', receipt.processes.length === 2 && receipt.processes.every(row => row.exitCode === 0 && row.peakRssBytes <= 4294967296) && receipt.operationCounts.renderCalls === 3 && receipt.operationCounts.sceneSaves === 1);
check(checks, 'A25_RESOURCE_CEILINGS', await treeBytes(work) <= 1073741824 && await treeBytes(root) <= 67108864 && receipt.resources.wallSeconds <= 900);
check(checks, 'A26_ZERO_EXTERNAL_AUTHORITY', receipt.operationCounts.networkCalls === 0 && receipt.operationCounts.modelCallsDuringExecution === 0 && receipt.operationCounts.mouseInteractions === 0);
check(checks, 'A27_VISUAL_REVIEW_PENDING', receipt.visualVerdict === 'PENDING_DIRECT_MODEL_REVIEW' && receipt.status === 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED');
const failed = checks.filter(row => !row.passed);
const audit = { schemaVersion: 'bfs.filmLanguageExecutionIndependentAudit.v0.1', experimentId: context.experimentId, status: failed.length ? 'FAIL' : 'MACHINE_PASS_VISUAL_REVIEW_REQUIRED', checks, counts: { passed: checks.length - failed.length, total: checks.length }, bindings: { freeze: { sha256: await hash(safe(FREEZE_URI)), freezeHash: freeze.freezeHash }, context: { sha256: await hash(safe(CONTEXT_URI)), contextHash: context.contextHash }, build: { sha256: await hash(buildPath), buildHash: build.buildHash }, reopen: { sha256: await hash(reopenPath), auditHash: reopen.auditHash }, receipt: { sha256: await hash(receiptPath), receiptHash: receipt.receiptHash } }, visualVerdict: 'PENDING_DIRECT_MODEL_REVIEW', auditHash: '' };
audit.auditHash = self(audit, 'auditHash');
await writeFile(resolve(root, 'independent-audit.json'), `${JSON.stringify(canonicalize(audit), null, 2)}\n`, { flag: 'wx' });
if (failed.length) throw new Error(`audit failed ${failed.map(row => row.id).join(',')}`);
process.stdout.write(`BFS_FILM_LANGUAGE_AUDIT MACHINE_PASS_VISUAL_REVIEW_REQUIRED ${audit.counts.passed}/${audit.counts.total} ${audit.auditHash}\n`);
