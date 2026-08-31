#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const basePath = resolve(root, 'scripts/audit-ai-native-studio-pc2.mjs');
const expectedBaseHash = '82cc4d9ee00c8919894a6fff513d216b0c4f738b4f6a797c06427bfcc6e1448c';
const payload = await readFile(basePath);
if (createHash('sha256').update(payload).digest('hex') !== expectedBaseHash) throw new Error('C1_BASE_AUDITOR_HASH');
let source = payload.toString('utf8');
const replacements = [
  ["const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');", `const repositoryRoot = ${JSON.stringify(root)};`],
  ["const FREEZE_URI = 'specs/ai-native-studio-pc2-tool-freeze.v0.1.json';", "const FREEZE_URI = 'specs/ai-native-studio-pc2-tool-freeze-c1.v0.2.json';"],
  ["const ROOT_URI = 'experiments/ai-native-studio-post-pb7/PC.2-2026-08-31-mac-m2max-attempt-01';", "const ROOT_URI = 'experiments/ai-native-studio-post-pb7/PC.2-2026-08-31-mac-m2max-attempt-02';"],
  ["const WORK_ROOT = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.2-2026-08-31-mac-m2max-attempt-01';", "const WORK_ROOT = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/PC.2-2026-08-31-mac-m2max-attempt-02';"],
  ['async function auditPc2(argv = process.argv.slice(2)) {', 'export async function auditPc2(argv = process.argv.slice(2)) {'],
  ["  const spec = await readJson(specPath), freeze = await readJson(freezePath), build = await readJson(resolve(root, 'build.json')), semantic = await readJson(resolve(root, 'semantic-audit.json')), receipt = await readJson(resolve(root, 'receipt.json'));", "  const spec = await readJson(specPath), freeze = await readJson(freezePath), build = await readJson(resolve(root, 'build.json')), semantic = await readJson(resolve(root, 'semantic-audit.json')), receipt = await readJson(resolve(root, 'receipt.json')); const acceptedPc1Path = resolve(repositoryRoot, 'experiments/ai-native-studio-post-pb7/PC.1-2026-08-31-mac-m2max-attempt-04/build.json'); if (await shaFile(acceptedPc1Path) !== 'a908299143cc4ce62cd135126884c67cee438f7a3f0d937cca1a22738d3d2be5') throw new Error('ACCEPTED_PC1_BUILD_FILE'); const acceptedPc1 = await readJson(acceptedPc1Path);"],
  ["  gate('PROTECTED_STATE', JSON.stringify(build.protectedStateBefore) === JSON.stringify(build.protectedStateAfter) && semantic.protectedStateCanonicalSha256 === spec.acceptedPc1Baseline.cameraLightSentinelsCanonicalSha256, semantic.protectedStateCanonicalSha256);", "  gate('PROTECTED_STATE', JSON.stringify(build.protectedStateBefore) === JSON.stringify(build.protectedStateAfter) && JSON.stringify(build.protectedStateAfter) === JSON.stringify(acceptedPc1.protectedStateAfter), semantic.protectedStateCanonicalSha256);"],
];
for (const [oldValue, newValue] of replacements) { if (source.split(oldValue).length !== 2) throw new Error('C1_BASE_AUDITOR_PATCH_SITE'); source = source.replace(oldValue, newValue); }
const guard = "if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) auditPc2().catch(error => { process.stderr.write(`BFS_PC2_AUDIT_REJECTED ${error.message}\\n`); process.exitCode = 1; });";
if (source.split(guard).length !== 2) throw new Error('C1_BASE_AUDITOR_GUARD');
source = source.replace(guard, '');
const module = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
try { await module.auditPc2(process.argv.slice(2)); }
catch (error) { process.stderr.write(`BFS_PC2_AUDIT_REJECTED ${error.message}\n`); process.exitCode = 1; }
