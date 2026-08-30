#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { readFileSync, statSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const evidence = resolve(process.argv[2]);
const id = process.argv[3]?.toUpperCase();
const expected = {
  B01: {
    start: 1,
    admission: '01-b01-identity-v2-build.json',
    plan: '316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf',
    semantic: 'e8c55fb73737f1871ac0008faa705dc204ebfe5bac471323cbb0a2d31435b4f8',
  },
  B02: {
    start: 2,
    admission: '02-b02-identity-v2-build.json',
    plan: 'a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687',
    semantic: 'd197b024c3b1de19c7fa981912c584de51d6d4884ef78b10e29db598ce979954',
  },
};
if (!expected[id]) throw new Error('Usage: finalize-isolated-build.mjs <evidence-root> <B01|B02>');

const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const root = resolve(evidence, id.toLowerCase(), 'artifacts');
const manifest = JSON.parse(readFileSync(resolve(root, 'scene.manifest.json')));
const admissionPath = resolve(evidence, 'admissions', expected[id].admission);
const admission = JSON.parse(readFileSync(admissionPath));
const artifacts = Object.fromEntries(['scene.blend', 'scene.manifest.json', 'scene.structure.canonical.json'].map(name => [name, {
  bytes: statSync(resolve(root, name)).size,
  sha256: shaFile(resolve(root, name)),
}]));
const product = manifest.execution.blender;
const checks = {
  admissionAccepted: admission.status === 'ACCEPTED' && admission.formalProductStart === expected[id].start,
  manifestVersion: manifest.manifestVersion === '0.3.0',
  structureIdentityVersion: manifest.structureIdentityVersion === 'bfs.semanticSceneStructure.v0.2',
  planHash: manifest.execution.planHash === expected[id].plan && manifest.structure.planHash === expected[id].plan,
  semanticStructureHash: manifest.structureHash === expected[id].semantic && artifacts['scene.structure.canonical.json'].sha256 === expected[id].semantic,
  semanticStructureExcludesProductProvenance: !Object.hasOwn(manifest.structure, 'blender'),
  productProvenanceExact: product.version === '5.2.0 LTS' && product.buildHash === 'b47eae224b6d' && product.buildBranch === 'codex/f0.4-embedded-contract' && product.buildPlatform === 'Darwin',
  ocioConfigSha256: manifest.execution.ocioConfigSha256 === '24ec81841048fc5db160a7bad882263246183385c5d49d0e86e11464917ead15',
  artifactRoster: Object.keys(artifacts).length === 3,
};
const body = {
  schemaVersion: 'bfs.f0.4.identityV2IsolatedBuildReceipt.v0.1',
  id,
  status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
  formalProductStart: expected[id].start,
  correction: 'C2_VERSIONED_SEMANTIC_STRUCTURE_AND_PRODUCT_PROVENANCE',
  admission: {
    uri: `admissions/${expected[id].admission}`,
    fileSha256: shaFile(admissionPath),
    freeBytes: admission.freeBytes,
  },
  checks,
  planHash: expected[id].plan,
  semanticStructureSha256: expected[id].semantic,
  productProvenance: product,
  productBinarySha256: '5a4538163d1fce6c531f2ad76a15232fc1d1d4bbff483d54778a290b4c37cb40',
  artifacts,
};
const pretty = `${JSON.stringify(body, null, 2)}\n`;
const record = { ...body, receiptHash: shaBytes(pretty) };
writeFileSync(resolve(evidence, id.toLowerCase(), 'receipt.json'), `${JSON.stringify(record, null, 2)}\n`, { flag: 'wx' });
console.log(`F04_C2_FINALIZE ${body.status} ${id} semantic=${expected[id].semantic}`);
if (body.status !== 'PASS') process.exitCode = 1;
