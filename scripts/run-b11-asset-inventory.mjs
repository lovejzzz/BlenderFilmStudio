import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) { if (candidate === 'blender') return candidate; try { await access(candidate, constants.X_OK); return candidate; } catch {} }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}
function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = ''; child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; }); child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise(output) : reject(new Error(output)));
  });
}
const blender = await findBlender();
const benchmarkRoot = resolve(repositoryRoot, 'specs/benchmarks');
const benchmarkFiles = ['B01.scene.json','B02.scene.json','B03.scene.json','B04.scene.json','B04.socket-frame.scene.json','B04.surface.scene.json','B05.scene.json','B08.scene.json'];
const assets = new Map();
for (const file of benchmarkFiles) {
  const scene = JSON.parse(await readFile(resolve(benchmarkRoot, file), 'utf8'));
  for (const asset of scene.assets) assets.set(asset.uri, { id: asset.id, kind: asset.kind, uri: asset.uri, sha256: asset.sha256 });
}
const workRoot = resolve(repositoryRoot, 'experiments/asset-security-v0-1/work/inventory');
await mkdir(workRoot, { recursive: true });
const auditor = resolve(repositoryRoot, 'blender/audit_asset_safety.py');
const reports = [];
let index = 0;
for (const asset of [...assets.values()].sort((left, right) => left.uri.localeCompare(right.uri))) {
  const output = resolve(workRoot, `${String(index++).padStart(2,'0')}.json`);
  await run(blender, ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', auditor, '--', '--input', resolve(repositoryRoot, asset.uri), '--output', output]);
  reports.push({ ...asset, inventory: JSON.parse(await readFile(output, 'utf8')) });
}
const allowedRigConstraints = [];
const forbidden = reports.flatMap(asset => {
  const failures = [];
  for (const object of asset.inventory.objects) {
    for (const field of ['drivers','action','dataDrivers','dataAction','shapeKeyDrivers','shapeKeyAction','constraints','rigidBody','rigidBodyConstraint','library','overrideLibrary']) if (object[field]) failures.push({ asset: asset.id, uri: asset.uri, object: object.name, field, observed: object[field] });
    for (const constraint of object.poseConstraints ?? []) {
      const allowedLimit = asset.kind === 'CHARACTER' && constraint.bone === 'head' && constraint.type === 'LIMIT_ROTATION' && constraint.name === 'BFS_HEAD_LIMIT' && constraint.target === null;
      const allowedGaze = asset.kind === 'CHARACTER' && ['eye.L','eye.R'].includes(constraint.bone) && constraint.type === 'DAMPED_TRACK' && constraint.name === `BFS_GAZE_${constraint.bone}` && constraint.target === 'GAZE_TARGET' && asset.inventory.objects.some(item => item.name === constraint.target);
      if (allowedLimit || allowedGaze) allowedRigConstraints.push({ asset: asset.id, object: object.name, ...constraint });
      else failures.push({ asset: asset.id, uri: asset.uri, object: object.name, field: 'poseConstraint', observed: constraint });
    }
    for (const modifier of object.modifiers) if (!(asset.kind === 'CHARACTER' && modifier === 'ARMATURE')) failures.push({ asset: asset.id, uri: asset.uri, object: object.name, field: 'modifier', observed: modifier });
  }
  if (asset.inventory.libraries.length) failures.push({ asset: asset.id, uri: asset.uri, field: 'libraries', observed: asset.inventory.libraries });
  for (const finding of asset.inventory.auxiliaryFindings ?? []) failures.push({ asset: asset.id, uri: asset.uri, field: 'auxiliaryDataBlock', observed: finding });
  for (const text of asset.inventory.texts ?? []) if (text.useModule) failures.push({ asset: asset.id, uri: asset.uri, field: 'autoRunText', observed: text.name });
  if (asset.inventory.autoExecuteEnabled) failures.push({ asset: asset.id, uri: asset.uri, field: 'autoExecuteEnabled', observed: true });
  return failures;
});
const report = { documentType: 'BFS_B11_PINNED_ASSET_INVENTORY', version: '0.1.0', blender: reports[0]?.inventory.blender, assets: reports.map(asset => ({ id: asset.id, kind: asset.kind, uri: asset.uri, sha256: asset.sha256, totals: asset.inventory.totals, libraries: asset.inventory.libraries, texts: asset.inventory.texts, modifiers: [...new Set(asset.inventory.objects.flatMap(item => item.modifiers))].sort() })), allowedRigConstraints, forbidden, cleanBaseline: forbidden.length === 0 };
const output = resolve(repositoryRoot, 'experiments/asset-security-v0-1/pinned-asset-inventory.json');
await mkdir(resolve(repositoryRoot, 'experiments/asset-security-v0-1'), { recursive: true });
await writeFile(output, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B11_PINNED_ASSET_INVENTORY ${report.cleanBaseline ? 'CLEAN' : 'FORBIDDEN_FOUND'} ${reports.length} assets ${forbidden.length} findings\n`);
if (!report.cleanBaseline) process.exitCode = 1;
