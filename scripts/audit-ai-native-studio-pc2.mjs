#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { open, readFile, readdir, stat } from 'node:fs/promises';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SPEC_URI = 'specs/ai-native-studio-pc2-action-complexity-preregistration.v0.1.json';
const FREEZE_URI = 'specs/ai-native-studio-pc2-tool-freeze.v0.1.json';
const ROOT_URI = 'experiments/ai-native-studio-post-pb7/PC.2-2026-08-31-mac-m2max-attempt-01';
const WORK_ROOT = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.2-2026-08-31-mac-m2max-attempt-01';
function sorted(v) { if (Array.isArray(v)) return v.map(sorted); if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, x]) => [k, sorted(x)])); return v; }
const canonical = v => JSON.stringify(sorted(v)); const sha = v => createHash('sha256').update(v).digest('hex'); const shaFile = async p => sha(await readFile(p));
const without = (v, f) => { const x = structuredClone(v); delete x[f]; return x; }; const validSelf = (v, f) => v?.[f] === sha(canonical(without(v, f)));
function pythonNumber(value) { if (!Number.isFinite(value)) throw new Error('NONFINITE'); if (Number.isInteger(value)) return String(value); return String(value).replace(/e([+-]?)(\d+)$/i, (_, sign, digits) => `e${sign || ''}${digits.padStart(2, '0')}`); }
function pythonCanonical(value) { if (value === null) return 'null'; if (Array.isArray(value)) return `[${value.map(pythonCanonical).join(',')}]`; if (typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${pythonCanonical(value[key])}`).join(',')}}`; if (typeof value === 'number') return pythonNumber(value); return JSON.stringify(value); }
const validPythonSelf = (v, f) => v?.[f] === sha(pythonCanonical(without(v, f)));
const readJson = async p => JSON.parse(await readFile(p, 'utf8'));
async function writeJson(path, body, field) { const value = { ...body, [field]: sha(canonical(body)) }; const h = await open(path, 'wx', 0o600); try { await h.writeFile(`${JSON.stringify(value, null, 2)}\n`); await h.sync(); } finally { await h.close(); } return value; }
async function walk(root) { const out = []; async function visit(path) { for (const e of await readdir(path, { withFileTypes: true })) { const next = resolve(path, e.name); if (e.isSymbolicLink()) throw new Error(`SYMLINK_${next}`); if (e.isDirectory()) await visit(next); else if (e.isFile()) out.push(next); } } await visit(root); return out.sort(); }

async function auditPc2(argv = process.argv.slice(2)) {
  if (argv.length !== 2 || argv[0] !== '--evidence-root' || argv[1] !== ROOT_URI) throw new Error('USAGE');
  const root = resolve(repositoryRoot, ROOT_URI), specPath = resolve(repositoryRoot, SPEC_URI), freezePath = resolve(repositoryRoot, FREEZE_URI);
  const expectedRoster = ['build.json', 'logs', 'processes', 'receipt.json', 'semantic-audit.json'];
  const roster = (await readdir(root)).sort(); if (JSON.stringify(roster) !== JSON.stringify(expectedRoster)) throw new Error(`ROSTER_${roster.join(',')}`);
  const spec = await readJson(specPath), freeze = await readJson(freezePath), build = await readJson(resolve(root, 'build.json')), semantic = await readJson(resolve(root, 'semantic-audit.json')), receipt = await readJson(resolve(root, 'receipt.json'));
  const processPaths = ['processes/01-build.json', 'processes/02-semantic-audit.json']; const processes = await Promise.all(processPaths.map(path => readJson(resolve(root, path))));
  const checks = []; const gate = (id, pass, detail) => checks.push({ id, pass: Boolean(pass), detail });
  gate('SELF_HASHES', validSelf(spec, 'specHash') && validSelf(freeze, 'specHash') && validPythonSelf(build, 'buildHash') && validPythonSelf(semantic, 'auditHash') && validPythonSelf(receipt, 'receiptHash') && processes.every(row => validPythonSelf(row, 'processHash')), { spec: spec.specHash, freeze: freeze.specHash, build: build.buildHash, semantic: semantic.auditHash, receipt: receipt.receiptHash });
  gate('TOOL_BINDINGS', receipt.toolFreeze.specHash === freeze.specHash && receipt.preregistration.specHash === spec.specHash && freeze.tools.every(row => row.sha256 && row.uri), receipt.toolFreeze);
  gate('SOURCE_IMMUTABLE', receipt.source.beforeSha256 === spec.acceptedPc1Baseline.sha256 && receipt.source.afterSha256 === spec.acceptedPc1Baseline.sha256 && await shaFile(spec.acceptedPc1Baseline.sourcePath) === spec.acceptedPc1Baseline.sha256, receipt.source);
  gate('EVIDENCE_FILES', receipt.build.sha256 === await shaFile(resolve(root, 'build.json')) && receipt.build.buildHash === build.buildHash && receipt.semanticAudit.sha256 === await shaFile(resolve(root, 'semantic-audit.json')) && receipt.semanticAudit.auditHash === semantic.auditHash, { build: receipt.build, semantic: receipt.semanticAudit });
  gate('SEMANTIC_PASS', build.status === 'PASS' && semantic.status === 'PASS', { build: build.status, semantic: semantic.status });
  gate('FOUR_PHASES', JSON.stringify(semantic.phaseIds) === JSON.stringify(spec.semanticPhases.map(row => row.id).sort()) && semantic.phaseIds.length === 4, semantic.phaseIds);
  gate('FOUR_CHANNELS', build.independentActionChannels.length === spec.acceptance.minimumIndependentNonCameraActionChannels && JSON.stringify(build.independentActionChannels) === JSON.stringify(spec.independentActionChannels), build.independentActionChannels);
  gate('TARGET_SCOPE', semantic.signalTargets.length >= spec.acceptance.minimumAnimatedNonCameraTargets && semantic.signalTargets.every(name => spec.authorizedAnimatedNonCameraTargets.includes(name)), semantic.signalTargets);
  gate('SIGNAL_AMPLITUDES', semantic.signalChecks.length === build.signals.length && semantic.signalChecks.every(row => row.passed && row.peakToPeak + 1e-6 >= row.minimumPeakToPeak), semantic.signalChecks);
  gate('GEOMETRY_EXACT', JSON.stringify(build.geometryBefore) === JSON.stringify(build.geometryAfter) && JSON.stringify(semantic.geometry) === JSON.stringify(build.geometryAfter) && semantic.geometry.objects === 104 && semantic.geometry.meshes === 92 && semantic.geometry.polygons === 19810, semantic.geometry);
  gate('MATERIALS_EXACT', JSON.stringify(build.materialsBefore) === JSON.stringify(build.materialsAfter) && JSON.stringify(semantic.materials) === JSON.stringify(build.materialsAfter), semantic.materials);
  gate('PROTECTED_STATE', JSON.stringify(build.protectedStateBefore) === JSON.stringify(build.protectedStateAfter) && semantic.protectedStateCanonicalSha256 === spec.acceptedPc1Baseline.cameraLightSentinelsCanonicalSha256, semantic.protectedStateCanonicalSha256);
  gate('SHOT_STATE', JSON.stringify(build.shotsBefore) === JSON.stringify(build.shotsAfter), build.shotsAfter);
  gate('ACTION_INCREMENT', JSON.stringify(build.actionsBefore) !== JSON.stringify(build.actionsAfter) && build.addedAnimatedTargets.length >= 6 && build.addedAnimatedTargets.every(name => spec.authorizedAnimatedNonCameraTargets.includes(name)), { before: build.actionsBefore, after: build.actionsAfter, added: build.addedAnimatedTargets });
  gate('PROCESS_EXITS', processes.every(row => row.exitCode === 0 && row.peakRssBytes > 0 && row.peakRssBytes <= spec.resourceCeilings.peakRssBytesPerProcess), processes.map(row => ({ name: row.name, exitCode: row.exitCode, peakRssBytes: row.peakRssBytes })));
  let streamsPass = true; for (const row of processes) for (const stream of ['stdout', 'stderr']) streamsPass &&= row[stream].sha256 === await shaFile(resolve(repositoryRoot, row[stream].uri)) && row[stream].bytes === (await stat(resolve(repositoryRoot, row[stream].uri))).size;
  gate('PROCESS_STREAMS', streamsPass, streamsPass);
  gate('OPERATION_COUNTS', receipt.operations.BlenderStarts === 2 && receipt.operations.renderCalls === 0 && receipt.operations.derivedSceneSaves === 1 && Object.entries(receipt.operations).filter(([key]) => !['BlenderStarts', 'renderCalls', 'derivedSceneSaves'].includes(key)).every(([, value]) => value === 0), receipt.operations);
  const workFiles = await walk(WORK_ROOT), evidenceFiles = await walk(root); const workBytes = (await Promise.all(workFiles.map(stat))).reduce((sum, row) => sum + row.size, 0); const evidenceBytes = (await Promise.all(evidenceFiles.map(stat))).reduce((sum, row) => sum + row.size, 0);
  gate('RESOURCE_CEILINGS', workBytes <= spec.resourceCeilings.workBytes && evidenceBytes <= spec.resourceCeilings.evidenceBytes, { workBytes, evidenceBytes });
  gate('WORK_ROSTER_ZERO_RENDER', workFiles.some(path => path.endsWith('/PC2_ACTION_COMPLEXITY.blend')) && ![...workFiles, ...evidenceFiles].some(path => /\.(exr|png|jpg|jpeg|mov|mp4)$/i.test(path)), workFiles.map(path => relative(WORK_ROOT, path)));
  const passed = checks.filter(row => row.pass).length; if (passed !== checks.length) throw new Error(`AUDIT_${passed}_OF_${checks.length}_${checks.filter(row => !row.pass).map(row => row.id).join('_')}`);
  const audit = await writeJson(resolve(root, 'audit.json'), { schemaVersion: 'bfs.pc2IndependentAudit.v0.1', status: 'PASS', gate: 'PC.2', checks, checkPassed: passed, checkTotal: checks.length, observations: { phases: semantic.phaseIds, channels: build.independentActionChannels, signalTargets: semantic.signalTargets, signalChecks: semantic.signalChecks, geometry: semantic.geometry, workBytes, evidenceBytesBeforeAudit: evidenceBytes }, bindings: { preregistration: { uri: SPEC_URI, sha256: await shaFile(specPath), specHash: spec.specHash }, toolFreeze: { uri: FREEZE_URI, sha256: await shaFile(freezePath), specHash: freeze.specHash }, receipt: { uri: `${ROOT_URI}/receipt.json`, sha256: await shaFile(resolve(root, 'receipt.json')), receiptHash: receipt.receiptHash } }, operations: receipt.operations }, 'auditHash');
  const entries = []; for (const path of await walk(root)) { const s = await stat(path); entries.push({ path: relative(root, path), sha256: await shaFile(path), bytes: s.size }); }
  const manifest = await writeJson(resolve(root, 'root-manifest.json'), { schemaVersion: 'bfs.pc2RootManifest.v0.1', gate: 'PC.2', entries }, 'manifestHash');
  process.stdout.write(`BFS_PC2_AUDIT PASS ${passed}/${checks.length} ${audit.auditHash} ${manifest.manifestHash}\n`);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) auditPc2().catch(error => { process.stderr.write(`BFS_PC2_AUDIT_REJECTED ${error.message}\n`); process.exitCode = 1; });
