#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specUri = 'specs/ai-native-studio-causal-studio-preregistration.v0.1.json';
const contextUri = 'specs/ai-native-studio-causal-studio-execution-context-c1.v0.2.json';
const freezeUri = 'specs/ai-native-studio-causal-studio-tool-freeze-c1.v0.2.json';
function canonical(value) { if (value === null || typeof value !== 'object') return JSON.stringify(value); if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`; return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`; }
function shaBytes(value) { return createHash('sha256').update(value).digest('hex'); }
function shaFile(path) { return shaBytes(readFileSync(path)); }
function selfHash(value, field) { const copy = structuredClone(value); delete copy[field]; return shaBytes(Buffer.from(canonical(copy))); }
function validSelf(value, field) { return value?.[field] === selfHash(value, field); }
function dirBytes(path) { const stat = statSync(path); if (!stat.isDirectory()) return stat.size; return readdirSync(path).reduce((sum, name) => sum + dirBytes(join(path, name)), 0); }
function load(path) { return JSON.parse(readFileSync(path, 'utf8')); }

const specPath = resolve(root, specUri);
const contextPath = resolve(root, contextUri);
const freezePath = resolve(root, freezeUri);
const spec = load(specPath);
const context = load(contextPath);
const freeze = load(freezePath);
const evidenceRoot = resolve(root, context.roots.evidence);
const workRoot = resolve(context.roots.work);
if (!existsSync(evidenceRoot)) throw new Error('EVIDENCE_ROOT');
const build = load(join(evidenceRoot, 'build.json'));
const reopen = load(join(evidenceRoot, 'reopen.json'));
const receipt = load(join(evidenceRoot, 'receipt.json'));
const manifest = load(join(evidenceRoot, 'root-manifest.json'));
const processes = readdirSync(join(evidenceRoot, 'processes')).filter(name => name.endsWith('.json')).sort().map(name => load(join(evidenceRoot, 'processes', name)));
const checks = [];
function gate(id, pass, observation = null) { checks.push({ id, pass: Boolean(pass), observation }); }

gate('A01_SPEC_SELF_HASH', validSelf(spec, 'specHash'), spec.specHash);
gate('A02_CONTEXT_AND_FREEZE_SELF_HASH', validSelf(context, 'contextHash') && validSelf(freeze, 'freezeHash'), { contextHash: context.contextHash, freezeHash: freeze.freezeHash });
gate('A03_TOOL_BINDINGS', context.base.sha256 === shaFile(specPath) && context.base.specHash === spec.specHash && freeze.context.sha256 === shaFile(contextPath) && freeze.context.contextHash === context.contextHash && freeze.tools.every(row => shaFile(resolve(root, row.uri)) === row.sha256));
gate('A04_OUTPUT_SELF_HASHES', validSelf(build, 'buildHash') && validSelf(reopen, 'reopenHash') && validSelf(receipt, 'receiptHash') && validSelf(manifest, 'manifestHash') && processes.every(row => validSelf(row, 'processHash')));
gate('A05_BINARY_IDENTITY', shaFile(spec.engine.path) === spec.engine.sha256, spec.engine.sha256);
gate('A06_PROCESS_BOUND', processes.length === 2 && processes.every(row => row.exitCode === 0 && row.timedOut === false), processes.map(row => ({ mode: row.mode, exitCode: row.exitCode })));
gate('A07_RENDER_BOUND', receipt.operations.renderCalls === 3 && build.reviews.length === 3 && build.reviews.every(row => existsSync(join(evidenceRoot, row.uri)) && shaFile(join(evidenceRoot, row.uri)) === row.sha256), build.reviews);
gate('A08_PROCEDURAL_ASSETS', build.inventory.externalImages.length === 0 && build.inventory.externalLibraries.length === 0 && build.inventory.proceduralModeling.ballChannelCount >= 3 && build.inventory.proceduralModeling.bottleCount === 3 && build.inventory.proceduralModeling.bottleDetailObjectCount >= 9, build.inventory.proceduralModeling);
gate('A09_RIGID_BODY_CAUSALITY', Object.values(build.inventory.dynamicFinalPoseKeyframes).every(value => value === false) && Object.entries(build.inventory.rigidBodies).filter(([name]) => name.startsWith('ACTOR_') || name.startsWith('TARGET_')).every(([, row]) => row.type === 'ACTIVE'), build.inventory.dynamicFinalPoseKeyframes);
const minClearance = Math.min(...build.initialClearances.map(row => Number(row.meters)));
gate('A10_INITIAL_NO_PENETRATION', minClearance >= -spec.causalAcceptance.initialPenetrationMaximumMeters, minClearance);
const contact = Number(build.physics.firstTargetContactFrame);
gate('A11_CONTACT_WINDOW', contact >= spec.causalAcceptance.firstTargetContactFrameWindowInclusive[0] && contact <= spec.causalAcceptance.firstTargetContactFrameWindowInclusive[1], contact);
gate('A12_FORWARD_TRAVEL', Number(build.physics.ballTravelBeforeFirstContact) >= spec.causalAcceptance.ballForwardTravelBeforeFirstTargetContactMinimumMeters, build.physics.ballTravelBeforeFirstContact);
gate('A13_ALL_THREE_KNOCKED_DOWN', Object.keys(build.physics.finalTiltDegrees).length === 3 && Object.values(build.physics.finalTiltDegrees).every(value => Number(value) >= spec.causalAcceptance.targetTiltDegreesAtFinalMinimumEach), build.physics.finalTiltDegrees);
gate('A14_FINITE_TRANSFORMS', Object.values(build.physics.finiteTransforms).every(Boolean) && Object.values(reopen.physics.finiteTransforms).every(Boolean));
gate('A15_REOPEN_CAUSAL_ORDER', canonical(build.physics.targetResponseFrames) === canonical(reopen.physics.targetResponseFrames) && canonical(build.physics.contactOrder) === canonical(reopen.physics.contactOrder), { build: build.physics.targetResponseFrames, reopen: reopen.physics.targetResponseFrames });
gate('A16_REOPEN_FINAL_TILTS', Object.keys(build.physics.finalTiltDegrees).every(name => Math.abs(Number(build.physics.finalTiltDegrees[name]) - Number(reopen.physics.finalTiltDegrees[name])) <= 0.01), { build: build.physics.finalTiltDegrees, reopen: reopen.physics.finalTiltDegrees });
gate('A17_SEMANTIC_ROSTER', build.inventory.semanticObjects.dynamic_actor.length === 1 && build.inventory.semanticObjects.target_group.length === 3 && build.inventory.semanticObjects.camera.length === 3 && build.inventory.semanticObjects.lights.length === 3, build.inventory.semanticObjects);
gate('A18_RESOURCE_CEILINGS', dirBytes(workRoot) <= spec.resourceCeilings.workRootBytes && dirBytes(evidenceRoot) <= spec.resourceCeilings.evidenceRootBytes, { workBytes: dirBytes(workRoot), evidenceBytes: dirBytes(evidenceRoot) });
gate('A19_FORBIDDEN_COUNTS', receipt.operations.networkCalls === 0 && receipt.operations.externalAssetDownloads === 0 && receipt.operations.engineMutations === 0 && receipt.operations.engineRemoteWrites === 0, receipt.operations);
gate('A20_SCREENSHOT_SEQUENCE', build.reviews.map(row => row.shotId).join(',') === 'SETUP,IMPACT,AFTERMATH' && build.reviews[0].frame < build.reviews[1].frame && build.reviews[1].frame < build.reviews[2].frame, build.reviews.map(row => ({ shotId: row.shotId, frame: row.frame })));

const passed = checks.filter(row => row.pass).length;
const body = {
  schemaVersion: 'bfs.causalStudioIndependentAudit.v0.1',
  status: passed === checks.length ? 'PASS' : 'FAIL',
  machineVerdict: passed === checks.length ? 'PASS' : 'FAIL',
  visualVerdict: 'PENDING_DIRECT_SCREENSHOT_REVIEW',
  overallVerdict: 'PENDING_DIRECT_SCREENSHOT_REVIEW',
  checkPassed: passed,
  checkTotal: checks.length,
  checks,
  bindings: { preregistration: { uri: specUri, sha256: shaFile(specPath), specHash: spec.specHash }, context: { uri: contextUri, sha256: shaFile(contextPath), contextHash: context.contextHash }, toolFreeze: { uri: freezeUri, sha256: shaFile(freezePath), freezeHash: freeze.freezeHash }, receipt: { uri: `${context.roots.evidence}/receipt.json`, sha256: shaFile(join(evidenceRoot, 'receipt.json')), receiptHash: receipt.receiptHash } },
};
const audit = { ...body, auditHash: selfHash(body, 'auditHash') };
writeFileSync(join(evidenceRoot, 'independent-audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
console.log(`BFS_CAUSAL_STUDIO_AUDIT ${audit.status} ${passed}/${checks.length} ${audit.auditHash}`);
if (audit.status !== 'PASS') process.exitCode = 1;
