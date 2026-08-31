#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { open, readFile, readdir, stat } from 'node:fs/promises';
import { dirname, extname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SPEC_URI = 'specs/ai-native-studio-post-pb7-improvement-program.v0.1.json';
const FREEZE_URI = 'specs/ai-native-studio-pc0-tool-freeze-c1.v0.2.json';
const ROOT_URI = 'experiments/ai-native-studio-post-pb7/PC.0-2026-08-31-mac-m2max-attempt-02';
const SENTINELS = [1, 48, 96, 97, 144, 192, 193, 240, 288];
const RENDER_EXTENSIONS = new Set(['.exr', '.png', '.jpg', '.jpeg', '.mov', '.mp4']);

function sorted(v) { if (Array.isArray(v)) return v.map(sorted); if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, x]) => [k, sorted(x)])); return v; }
const canonical = v => JSON.stringify(sorted(v)); const sha = v => createHash('sha256').update(v).digest('hex'); const shaFile = async p => sha(await readFile(p));
const without = (v, f) => { const x = structuredClone(v); delete x[f]; return x; }; const validSelf = (v, f) => v?.[f] === sha(canonical(without(v, f)));
const readJson = async p => JSON.parse(await readFile(p, 'utf8'));
async function writeJson(path, body, field) { const value = { ...body, [field]: sha(canonical(body)) }; const h = await open(path, 'wx', 0o600); try { await h.writeFile(`${JSON.stringify(value, null, 2)}\n`); await h.sync(); } finally { await h.close(); } return value; }
async function walk(root) { const out = []; async function visit(path) { for (const e of await readdir(path, { withFileTypes: true })) { const next = resolve(path, e.name); if (e.isSymbolicLink()) throw new Error(`SYMLINK_${next}`); if (e.isDirectory()) await visit(next); else if (e.isFile()) out.push(next); } } await visit(root); return out.sort(); }

export function inventoryChecks(inventory) {
  const objects = inventory?.objects || [], actions = inventory?.actions || [], sentinels = inventory?.sentinels || [], counts = inventory?.counts || {};
  const meshes = objects.filter(item => item.type === 'MESH'); const cameras = objects.filter(item => item.type === 'CAMERA').map(item => item.name); const lights = objects.filter(item => item.type === 'LIGHT').map(item => item.name);
  return {
    schemaAndStatus: inventory?.schemaVersion === 'bfs.pc0HeroAssetActionInventory.v0.1' && inventory.status === 'PASS',
    objectRoster: objects.length > 0 && new Set(objects.map(item => item.name)).size === objects.length && counts.objects === objects.length,
    meshTotals: counts.meshes === meshes.length && counts.vertices === meshes.reduce((sum, item) => sum + item.mesh.vertices, 0) && counts.polygons === meshes.reduce((sum, item) => sum + item.mesh.polygons, 0),
    heroRoster: Array.isArray(inventory.heroCandidates) && inventory.heroCandidates.length === counts.heroCandidates && inventory.heroCandidates.length > 0,
    materials: Array.isArray(inventory.materials) && inventory.materials.length === counts.materials,
    actions: actions.length === counts.actions && actions.reduce((sum, item) => sum + item.fcurveCount, 0) === counts.fcurves && actions.reduce((sum, item) => sum + item.keyframeCount, 0) === counts.keyframes,
    bindings: Array.isArray(inventory.animationBindings) && inventory.animationBindings.length === objects.length && inventory.animatedTargets.length === counts.animatedTargets,
    sentinelRoster: JSON.stringify(sentinels.map(item => item.frame)) === JSON.stringify(SENTINELS) && sentinels.every(item => Object.keys(item.objects).length === objects.length),
    cameraSamples: cameras.length > 0 && sentinels.every(item => cameras.every(name => item.objects[name]?.camera?.lens > 0)),
    lightSamples: lights.length > 0 && sentinels.every(item => lights.every(name => item.objects[name]?.light?.energy >= 0)),
    zeroOperations: inventory.operations?.renderCalls === 0 && inventory.operations?.sceneSaves === 0 && inventory.operations?.dataMutations === 0 && inventory.operations?.networkCalls === 0 && inventory.operations?.modelCalls === 0,
  };
}

export async function auditPc0(argv = process.argv.slice(2)) {
  if (argv.length !== 2 || argv[0] !== '--evidence-root' || argv[1] !== ROOT_URI) throw new Error('USAGE'); const root = resolve(repositoryRoot, ROOT_URI);
  if (relative(repositoryRoot, root) !== ROOT_URI) throw new Error('ROOT');
  const roster = (await readdir(root)).sort(); if (JSON.stringify(roster) !== JSON.stringify(['inventory.json', 'logs', 'process.json', 'receipt.json'])) throw new Error(`PRE_AUDIT_ROSTER_${roster.join(',')}`);
  const specPath = resolve(repositoryRoot, SPEC_URI), freezePath = resolve(repositoryRoot, FREEZE_URI), inventoryPath = resolve(root, 'inventory.json'), processPath = resolve(root, 'process.json'), receiptPath = resolve(root, 'receipt.json');
  const spec = await readJson(specPath), freeze = await readJson(freezePath), inventory = await readJson(inventoryPath), processRecord = await readJson(processPath), receipt = await readJson(receiptPath); const checks = [];
  const gate = (id, pass, detail) => checks.push({ id, pass: Boolean(pass), detail });
  gate('SPEC_SELF_HASH', validSelf(spec, 'specHash'), spec.specHash); gate('FREEZE_SELF_HASH', validSelf(freeze, 'specHash'), freeze.specHash); gate('PROCESS_SELF_HASH', validSelf(processRecord, 'processHash'), processRecord.processHash); gate('RECEIPT_SELF_HASH', validSelf(receipt, 'receiptHash'), receipt.receiptHash);
  gate('CONTRACT_BINDINGS', receipt.program.specHash === spec.specHash && receipt.toolFreeze.specHash === freeze.specHash, receipt.program);
  gate('SOURCE_IMMUTABLE', receipt.source.beforeSha256 === spec.frozenBaseline.scene.sha256 && receipt.source.afterSha256 === spec.frozenBaseline.scene.sha256 && await shaFile(resolve(repositoryRoot, spec.frozenBaseline.scene.uri)) === spec.frozenBaseline.scene.sha256, receipt.source);
  gate('BINARY_EXACT', receipt.binary.sha256 === spec.frozenBaseline.binary.sha256 && await shaFile(spec.frozenBaseline.binary.path) === spec.frozenBaseline.binary.sha256, receipt.binary.sha256);
  gate('INVENTORY_FILE', receipt.inventory.sha256 === await shaFile(inventoryPath) && receipt.inventory.bytes === (await stat(inventoryPath)).size, receipt.inventory);
  gate('PROCESS_FILE', receipt.process.sha256 === await shaFile(processPath) && receipt.process.processHash === processRecord.processHash, receipt.process);
  gate('PROCESS_EXIT', processRecord.exitCode === 0 && processRecord.signal === null && processRecord.timedOut === false, { exitCode: processRecord.exitCode, signal: processRecord.signal, timedOut: processRecord.timedOut });
  gate('PROCESS_STREAMS', processRecord.stdout.sha256 === await shaFile(resolve(root, 'logs/stdout.log')) && processRecord.stderr.sha256 === await shaFile(resolve(root, 'logs/stderr.log')), { stdout: processRecord.stdout, stderr: processRecord.stderr });
  gate('RESOURCE_CEILINGS', processRecord.wallSeconds <= spec.resourceCeilings.pc0WallSeconds && processRecord.peakRssBytes <= spec.resourceCeilings.pc0PeakRssBytes && processRecord.peakRssBytes > 0, { wallSeconds: processRecord.wallSeconds, peakRssBytes: processRecord.peakRssBytes });
  gate('OPERATION_COUNTS', receipt.operations.BlenderStarts === 1 && Object.entries(receipt.operations).filter(([key]) => key !== 'BlenderStarts').every(([, value]) => value === 0), receipt.operations);
  for (const [id, pass] of Object.entries(inventoryChecks(inventory))) gate(`INVENTORY_${id.toUpperCase()}`, pass, pass);
  const workFiles = await walk(receipt.workRoot), evidenceFiles = await walk(root); const renderArtifacts = [...workFiles, ...evidenceFiles].filter(path => RENDER_EXTENSIONS.has(extname(path).toLowerCase())); gate('NO_RENDER_ARTIFACTS', renderArtifacts.length === 0 && receipt.renderArtifacts.length === 0, renderArtifacts);
  const workBytes = (await Promise.all(workFiles.map(path => stat(path)))).reduce((sum, item) => sum + item.size, 0); gate('WORK_CEILING', workBytes <= freeze.resourceCeilings.workBytes, workBytes);
  const evidenceBytesBeforeAudit = (await Promise.all(evidenceFiles.map(path => stat(path)))).reduce((sum, item) => sum + item.size, 0); gate('EVIDENCE_CEILING', evidenceBytesBeforeAudit < spec.resourceCeilings.pc0EvidenceBytes, evidenceBytesBeforeAudit);
  const passed = checks.filter(item => item.pass).length; if (passed !== checks.length) throw new Error(`AUDIT_${passed}_OF_${checks.length}_${checks.filter(item => !item.pass).map(item => item.id).join('_')}`);
  const audit = await writeJson(resolve(root, 'audit.json'), { schemaVersion: 'bfs.pc0InventoryAudit.v0.1', status: 'PASS', gate: 'PC.0', checks, checkPassed: passed, checkTotal: checks.length, observations: { counts: inventory.counts, heroCandidates: inventory.heroCandidates, animatedTargets: inventory.animatedTargets, actionNames: inventory.actions.map(item => item.name), workFileCount: workFiles.length, workBytes, evidenceBytesBeforeAudit }, bindings: { program: { uri: SPEC_URI, sha256: await shaFile(specPath), specHash: spec.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await shaFile(freezePath), specHash: freeze.specHash }, inventory: { uri: `${ROOT_URI}/inventory.json`, sha256: await shaFile(inventoryPath) }, runReceipt: { uri: `${ROOT_URI}/receipt.json`, sha256: await shaFile(receiptPath), receiptHash: receipt.receiptHash } }, operations: receipt.operations }, 'auditHash');
  const manifestEntries = []; for (const path of await walk(root)) { const s = await stat(path); manifestEntries.push({ path: relative(root, path), sha256: await shaFile(path), bytes: s.size }); }
  const manifest = await writeJson(resolve(root, 'root-manifest.json'), { schemaVersion: 'bfs.pc0RootManifest.v0.1', gate: 'PC.0', entries: manifestEntries }, 'manifestHash');
  globalThis.process.stdout.write(`BFS_PC0_AUDIT PASS ${passed}/${checks.length} ${audit.auditHash} ${manifest.manifestHash}\n`); return { audit, manifest };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) auditPc0().catch(error => { process.stderr.write(`BFS_PC0_AUDIT_REJECTED ${error.message}\n`); process.exitCode = 1; });
