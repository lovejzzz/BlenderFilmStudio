#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, readdirSync, readlinkSync, statSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repository = resolve(process.argv[2]);
const prior = resolve(repository, 'experiments/ai-native-studio-f0/F0.6-2026-08-30-mac-m2max-attempt-02/regression');
const experiment = resolve(repository, 'experiments/ai-native-studio-f0/F0.6-2026-08-30-mac-m2max-attempt-03');
const output = resolve(experiment, 'regression/f01-f04-corrected.json');
const source = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/blender-v5.2.0-src';
const product = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-f0.6-merge-drill/bin/Film Studio Engine F0.app/Contents/MacOS/Blender';
const official = '/Users/mengyingli/Library/Application Support/Blender';
const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const canonical = value => JSON.stringify(sortDeep(value));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
function sortDeep(value) {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortDeep(value[key])]));
  return value;
}
function validSelf(path, field) {
  const value = JSON.parse(readFileSync(path));
  const expected = value[field];
  delete value[field];
  return expected === prettyHash(value);
}
function treeDigest(root) {
  const rows = [];
  const walk = (current, prefix = '') => {
    for (const name of readdirSync(current).sort((a, b) => a.localeCompare(b, 'en'))) {
      const path = resolve(current, name);
      const rel = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (stat.isDirectory()) {
        rows.push({ path: rel, type: 'directory', mode });
        walk(path, rel);
      } else if (stat.isSymbolicLink()) rows.push({ path: rel, type: 'symlink', mode, target: readlinkSync(path) });
      else if (stat.isFile()) rows.push({ path: rel, type: 'file', mode, bytes: stat.size, sha256: shaFile(path) });
      else rows.push({ path: rel, type: 'other', mode, bytes: stat.size });
    }
  };
  walk(root);
  return shaBytes(`${rows.map(row => JSON.stringify(row)).join('\n')}\n`);
}

const expectedFiles = {
  f01f02: ['f01-f02.json', 'cc323221303b00ca682b13b1a50d757784a3242f10eb50c59bf39a5e53a18477', 'receiptHash'],
  f03: ['f03/receipt.json', 'a4ada01f52607154c0c369385b540fc97f7c546aa0a5a2b3b547b1c5ac1bf1a8', 'receiptHash'],
  f04Aggregate: ['f04/receipt.json', '17b6c67e2b51174c897c58b139b37ea4254026c8f916047fefc172513085f885', 'receiptHash'],
  f04Audit: ['f04/audit.json', '5ee9b99b4894ebc7f3b3100bb6e69284a9feedb228930d2503c977c305066073', null],
  b01Manifest: ['f04/b01/artifacts/scene.manifest.json', 'b7a4fa26418e52796484b620f72268bc848ce19279161cced96a042114eda64a', null],
  b02Manifest: ['f04/b02/artifacts/scene.manifest.json', '24fbbabec39ddd43b1bbbf43c68c332df7ac52f175e268bc24a64524f2e7351d', null],
  b01Blend: ['f04/b01/artifacts/scene.blend', '719eeff69bb1e3bb13c5227f107f20617ae64b7ac12cf319b3d52f25b3a0ff08', null],
  b02Blend: ['f04/b02/artifacts/scene.blend', 'be97b29fa868fcd6d60e8638667c6082edb4f3ad22df462e5ac2f9f8de093cbb', null],
};
const fileChecks = {};
for (const [id, [relative, expected, selfField]] of Object.entries(expectedFiles)) {
  const path = resolve(prior, relative);
  fileChecks[id] = shaFile(path) === expected && (!selfField || validSelf(path, selfField));
}
const f01 = JSON.parse(readFileSync(resolve(prior, 'f01-f02.json')));
const f03 = JSON.parse(readFileSync(resolve(prior, 'f03/receipt.json')));
const aggregate = JSON.parse(readFileSync(resolve(prior, 'f04/receipt.json')));
const comparison = JSON.parse(readFileSync(resolve(prior, 'f04/canonical-comparison.json')));
const negatives = JSON.parse(readFileSync(resolve(prior, 'f04/negative-fixtures.json')));
const proposal = JSON.parse(readFileSync(resolve(prior, 'f04/proposal-diff.json')));
const audit = JSON.parse(readFileSync(resolve(prior, 'f04/audit.json')));
const provenance = { version: '5.2.1 LTS', buildHash: 'fa1b578bb421', buildBranch: 'codex/f0.6-upstream-merge-drill', buildPlatform: 'Darwin' };
const manifests = ['b01', 'b02'].map(id => JSON.parse(readFileSync(resolve(prior, `f04/${id}/artifacts/scene.manifest.json`))));
const processRows = readdirSync(resolve(prior, 'processes')).filter(name => /^\d\d-.*\.json$/.test(name)).sort().map(name => {
  const path = resolve(prior, 'processes', name);
  const value = JSON.parse(readFileSync(path));
  return { name, status: value.status, exitCode: value.exitCode, selfHash: validSelf(path, 'processHash') };
});
const admissionRows = readdirSync(resolve(prior, 'admissions')).filter(name => name.endsWith('.json')).sort().map(name => {
  const path = resolve(prior, 'admissions', name);
  const value = JSON.parse(readFileSync(path));
  return { name, status: value.status, selfHash: validSelf(path, 'admissionHash') };
});
const sourceStatus = execFileSync('/usr/bin/git', ['-C', source, 'status', '--porcelain=v1'], { encoding: 'utf8' }).trim();
const checks = {
  exactBoundFiles: Object.values(fileChecks).every(Boolean),
  f01f02Pass: f01.status === 'PASS' && Object.values(f01.checks).every(Boolean),
  f03Pass: f03.status === 'PASS' && Object.values(f03.checks).every(Boolean),
  tenAcceptedAdmissions: admissionRows.length === 10 && admissionRows.every(row => row.status === 'ACCEPTED' && row.selfHash),
  tenPassingProcesses: processRows.length === 10 && processRows.every(row => row.status === 'PASS' && row.exitCode === 0 && row.selfHash),
  canonicalBuildPlansExact: comparison.status === 'PASS' && comparison.comparisons.length === 2 && comparison.comparisons.every(row => row.byteExact && row.sceneMutations === 0),
  fourNegativeControlsExact: negatives.status === 'PASS' && negatives.cases.length === 4 && negatives.cases.every(row => row.passed && row.sceneMutations === 0 && row.buildPlanFilesWritten === 0),
  proposalInspectionExact: proposal.status === 'PASS',
  independentAuditPass: audit.status === 'PASS' && audit.builds.every(row => row.status === 'PASS' && Object.values(row.checks).every(Boolean)) && audit.separationAttacks.every(row => row.passed),
  aggregateFailedOnlyOrderSensitiveChecks: aggregate.status === 'FAIL' && aggregate.builds.length === 2 && aggregate.builds.every(row => !row.checks.provenance && row.checks.planHash && row.checks.semanticHash && row.checks.sceneBlendPresent),
  provenanceCanonicalExact: manifests.every(manifest => canonical(manifest.execution.blender) === canonical(provenance)),
  productBinaryExact: shaFile(product) === '58d5c984c58d986d3cf44622ad5876052a67890d0b077dafd4977f6e2b24a71d',
  sourceExactAndClean: execFileSync('/usr/bin/git', ['-C', source, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim() === 'fa1b578bb421bbc82b3106b7d4223e11e65fae1d' && sourceStatus === '',
  officialConfigUnchanged: treeDigest(official) === 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf',
};
const body = {
  schemaVersion: 'bfs.f0.6.f01F04CorrectiveAudit.v0.1',
  status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
  correction: 'ORDER_INSENSITIVE_EXACT_PROVENANCE_PROPERTY_COMPARISON',
  productStarts: 0,
  attempt02ProductStartsCrossBound: 10,
  fileChecks,
  processRows,
  admissionRows,
  expectedProvenance: provenance,
  observedProvenance: manifests.map(manifest => manifest.execution.blender),
  checks,
};
const record = { ...body, receiptHash: prettyHash(body) };
writeFileSync(output, `${JSON.stringify(record, null, 2)}\n`, { flag: 'wx' });
if (body.status !== 'PASS') throw new Error(`F0.1-F0.4 corrective audit failed: ${JSON.stringify(checks)}`);
console.log('F06_ATTEMPT03_F01_F04 PASS boundStarts=10 correctiveStarts=0');
