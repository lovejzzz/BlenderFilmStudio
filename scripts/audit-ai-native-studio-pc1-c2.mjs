#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { open, readFile, readdir, stat } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SPEC_URI = 'specs/ai-native-studio-pc1-modeling-detail-preregistration-c1.v0.2.json';
const FREEZE_URI = 'specs/ai-native-studio-pc1-tool-freeze-c2.v0.2.json';
const ROOT_URI = 'experiments/ai-native-studio-post-pb7/PC.1-2026-08-31-mac-m2max-attempt-02';
const WORK_ROOT = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.1-2026-08-31-mac-m2max-attempt-02';
function sorted(v) { if (Array.isArray(v)) return v.map(sorted); if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, x]) => [k, sorted(x)])); return v; }
const canonical = v => JSON.stringify(sorted(v)); const sha = v => createHash('sha256').update(v).digest('hex'); const shaFile = async p => sha(await readFile(p));
const without = (v, f) => { const x = structuredClone(v); delete x[f]; return x; }; const validSelf = (v, f) => v?.[f] === sha(canonical(without(v, f)));
const readJson = async p => JSON.parse(await readFile(p, 'utf8'));
async function writeJson(path, body, field) { const value = { ...body, [field]: sha(canonical(body)) }; const h = await open(path, 'wx', 0o600); try { await h.writeFile(`${JSON.stringify(value, null, 2)}\n`); await h.sync(); } finally { await h.close(); } return value; }
async function walk(root) { const out = []; async function visit(path) { for (const e of await readdir(path, { withFileTypes: true })) { const next = resolve(path, e.name); if (e.isSymbolicLink()) throw new Error(`SYMLINK_${next}`); if (e.isDirectory()) await visit(next); else if (e.isFile()) out.push(next); } } await visit(root); return out.sort(); }

async function auditPc1(argv = process.argv.slice(2)) {
  if (argv.length !== 2 || argv[0] !== '--evidence-root' || argv[1] !== ROOT_URI) throw new Error('USAGE');
  const root = resolve(repositoryRoot, ROOT_URI); const specPath = resolve(repositoryRoot, SPEC_URI), freezePath = resolve(repositoryRoot, FREEZE_URI);
  const expectedRoster = ['baseline', 'build.json', 'derived', 'logs', 'processes', 'receipt.json', 'semantic-audit.json'];
  const roster = (await readdir(root)).sort(); if (JSON.stringify(roster) !== JSON.stringify(expectedRoster)) throw new Error(`ROSTER_${roster.join(',')}`);
  const spec = await readJson(specPath), freeze = await readJson(freezePath), build = await readJson(resolve(root, 'build.json')), semantic = await readJson(resolve(root, 'semantic-audit.json')), receipt = await readJson(resolve(root, 'receipt.json'));
  const processPaths = ['processes/01-build.json', 'processes/02-semantic-audit.json']; const processes = await Promise.all(processPaths.map(path => readJson(resolve(root, path))));
  const checks = []; const gate = (id, pass, detail) => checks.push({ id, pass: Boolean(pass), detail });
  gate('SELF_HASHES', validSelf(spec, 'specHash') && validSelf(freeze, 'specHash') && validSelf(build, 'buildHash') && validSelf(semantic, 'auditHash') && validSelf(receipt, 'receiptHash') && processes.every(row => validSelf(row, 'processHash')), { spec: spec.specHash, freeze: freeze.specHash, build: build.buildHash, semantic: semantic.auditHash, receipt: receipt.receiptHash });
  gate('TOOL_BINDINGS', freeze.tools.every(row => row.sha256 && row.uri) && receipt.toolFreeze.specHash === freeze.specHash && receipt.preregistration.specHash === spec.specHash, receipt.toolFreeze);
  gate('SOURCE_IMMUTABLE', receipt.source.beforeSha256 === spec.baseline.source.sha256 && receipt.source.afterSha256 === spec.baseline.source.sha256 && await shaFile(resolve(repositoryRoot, spec.baseline.source.uri)) === spec.baseline.source.sha256, receipt.source);
  gate('BUILD_FILE', receipt.build.sha256 === await shaFile(resolve(root, 'build.json')) && receipt.build.buildHash === build.buildHash, receipt.build);
  gate('SEMANTIC_FILE', receipt.semanticAudit.sha256 === await shaFile(resolve(root, 'semantic-audit.json')) && receipt.semanticAudit.auditHash === semantic.auditHash && semantic.status === 'PASS', receipt.semanticAudit);
  gate('DETAIL_ROSTER', JSON.stringify(build.details.map(row => row.id).sort()) === JSON.stringify([...spec.semanticDetailComponents].sort()) && build.details.length >= spec.acceptance.minimumNewSemanticDetailComponents, build.details.length);
  gate('MATERIAL_REGIONS', JSON.stringify(build.materialRegions.map(row => row.name).sort()) === JSON.stringify([...spec.materialRegions].sort()) && build.materialRegions.every(row => row.nodeCount >= 4), build.materialRegions);
  gate('COUNTS_INCREASE', build.derivedCounts.objects > spec.baseline.counts.objects && build.derivedCounts.polygons > spec.baseline.counts.polygons, build.derivedCounts);
  gate('PROTECTED_STATE', JSON.stringify(build.protectedStateBefore) === JSON.stringify(build.protectedStateAfter), true);
  gate('ACTIONS_EXACT', JSON.stringify(build.actionsBefore) === JSON.stringify(build.actionsAfter), true);
  gate('VISIBLE_VIEWS', receipt.visibleViews >= spec.acceptance.minimumProtectedViewsWithVisibleChange && semantic.pixelMetrics.filter(row => row.passesVisibleChange).length === receipt.visibleViews, semantic.pixelMetrics);
  gate('PROCESS_EXITS', processes.every(row => row.exitCode === 0 && row.peakRssBytes > 0 && row.peakRssBytes <= spec.resourceCeilings.peakRssBytesPerProcess), processes.map(row => ({ name: row.name, exitCode: row.exitCode, peakRssBytes: row.peakRssBytes })));
  let streamsPass = true; for (const row of processes) for (const stream of ['stdout', 'stderr']) streamsPass &&= row[stream].sha256 === await shaFile(resolve(repositoryRoot, row[stream].uri)) && row[stream].bytes === (await stat(resolve(repositoryRoot, row[stream].uri))).size;
  gate('PROCESS_STREAMS', streamsPass, streamsPass);
  const renderPaths = [...await walk(resolve(root, 'baseline')), ...await walk(resolve(root, 'derived'))];
  gate('RENDER_ROSTER', renderPaths.length === 6 && receipt.renders.length === 6 && receipt.renders.every(row => renderPaths.includes(resolve(repositoryRoot, row.uri))), renderPaths.map(path => relative(root, path)));
  let renderHashes = true; for (const row of receipt.renders) renderHashes &&= row.sha256 === await shaFile(resolve(repositoryRoot, row.uri)) && row.bytes === (await stat(resolve(repositoryRoot, row.uri))).size; gate('RENDER_HASHES', renderHashes, renderHashes);
  gate('OPERATION_COUNTS', receipt.operations.BlenderStarts === 2 && receipt.operations.renderCalls === 6 && receipt.operations.derivedSceneSaves === 1 && Object.entries(receipt.operations).filter(([key]) => !['BlenderStarts', 'renderCalls', 'derivedSceneSaves'].includes(key)).every(([, value]) => value === 0), receipt.operations);
  const workFiles = await walk(WORK_ROOT), evidenceFiles = await walk(root); const workBytes = (await Promise.all(workFiles.map(stat))).reduce((sum, row) => sum + row.size, 0); const evidenceBytes = (await Promise.all(evidenceFiles.map(stat))).reduce((sum, row) => sum + row.size, 0);
  gate('RESOURCE_CEILINGS', workBytes <= spec.resourceCeilings.workBytes && evidenceBytes <= spec.resourceCeilings.evidenceBytes, { workBytes, evidenceBytes });
  gate('WORK_ROSTER', workFiles.some(path => path.endsWith('/PC1_MODELING_DETAIL.blend')) && !workFiles.some(path => /\.(exr|mov|mp4)$/i.test(path)), workFiles.map(path => relative(WORK_ROOT, path)));
  const passed = checks.filter(row => row.pass).length; if (passed !== checks.length) throw new Error(`AUDIT_${passed}_OF_${checks.length}_${checks.filter(row => !row.pass).map(row => row.id).join('_')}`);
  const audit = await writeJson(resolve(root, 'audit.json'), { schemaVersion: 'bfs.pc1IndependentAudit.v0.1', status: 'PASS', gate: 'PC.1', checks, checkPassed: passed, checkTotal: checks.length, observations: { detailCount: build.details.length, materialRegionCount: build.materialRegions.length, derivedCounts: build.derivedCounts, pixelMetrics: semantic.pixelMetrics, workBytes, evidenceBytesBeforeAudit: evidenceBytes }, bindings: { preregistration: { uri: SPEC_URI, sha256: await shaFile(specPath), specHash: spec.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await shaFile(freezePath), specHash: freeze.specHash }, receipt: { uri: `${ROOT_URI}/receipt.json`, sha256: await shaFile(resolve(root, 'receipt.json')), receiptHash: receipt.receiptHash } }, operations: receipt.operations }, 'auditHash');
  const entries = []; for (const path of await walk(root)) { const s = await stat(path); entries.push({ path: relative(root, path), sha256: await shaFile(path), bytes: s.size }); }
  const manifest = await writeJson(resolve(root, 'root-manifest.json'), { schemaVersion: 'bfs.pc1RootManifest.v0.1', gate: 'PC.1', entries }, 'manifestHash');
  process.stdout.write(`BFS_PC1_AUDIT PASS ${passed}/${checks.length} ${audit.auditHash} ${manifest.manifestHash}\n`);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) auditPc1().catch(error => { process.stderr.write(`BFS_PC1_AUDIT_REJECTED ${error.message}\n`); process.exitCode = 1; });
