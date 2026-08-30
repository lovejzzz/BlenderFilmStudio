#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const evidence = resolve(process.argv[2]);
const sha = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const expected = {
  B01: { start: 1, plan: '316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf', structure: 'c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b' },
  B02: { start: 2, plan: 'a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687', structure: '025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856' },
};
const ocioSha = '24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15';

for (const id of ['B01', 'B02']) {
  const root = resolve(evidence, id.toLowerCase(), 'artifacts');
  const manifest = JSON.parse(readFileSync(resolve(root, 'scene.manifest.json')));
  const artifacts = Object.fromEntries(['scene.blend', 'scene.manifest.json', 'scene.structure.canonical.json'].map(name => [name, {
    bytes: statSync(resolve(root, name)).size,
    sha256: sha(resolve(root, name)),
  }]));
  const checks = {
    planHash: manifest.execution.planHash === expected[id].plan,
    structureHash: manifest.structureHash === expected[id].structure && artifacts['scene.structure.canonical.json'].sha256 === expected[id].structure,
    ocioConfigSha256: manifest.execution.ocioConfigSha256 === ocioSha,
    isolatedRoot: root.endsWith(`/${id.toLowerCase()}/artifacts`),
    artifactRoster: Object.keys(artifacts).length === 3,
  };
  const body = {
    schemaVersion: 'bfs.f0.4.correctionIsolatedBuildReceipt.v0.1',
    id,
    status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
    formalProductStart: expected[id].start,
    correction: 'C1_OCIO_LAUNCH_ENVIRONMENT_BINDING',
    checks,
    planHash: expected[id].plan,
    structureHash: expected[id].structure,
    ocioConfigSha256: ocioSha,
    artifacts,
  };
  body.receiptHash = createHash('sha256').update(JSON.stringify(body)).digest('hex');
  writeFileSync(resolve(evidence, id.toLowerCase(), 'receipt.json'), `${JSON.stringify(body, null, 2)}\n`, { flag: 'wx' });
  if (body.status !== 'PASS') throw new Error(`${id} correction receipt failed`);
}
console.log('F04_C1_FINALIZE PASS B01 B02');
