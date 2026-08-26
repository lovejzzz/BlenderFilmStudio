import { access, readFile, realpath, stat, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { execFile } from 'node:child_process';
import { dirname, relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual } from 'node:util';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { canonicalJson, sha256Canonical, sha256Bytes, sha256File } from './lib/receipt-format.mjs';

const repositoryRealRoot = await realpath(repositoryRoot);

async function trustedRepositoryFile(uri, label) {
  if (typeof uri !== 'string' || uri.length === 0) throw new Error(`${label} URI is missing`);
  const absolutePath = resolve(repositoryRoot, uri);
  const pathFromRoot = relative(repositoryRoot, absolutePath);
  if (pathFromRoot === '' || pathFromRoot === '..' || pathFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} URI resolves outside repository`);
  const actualPath = await realpath(absolutePath).catch(() => { throw new Error(`${label} file is missing`); });
  const realFromRoot = relative(repositoryRealRoot, actualPath);
  if (realFromRoot === '' || realFromRoot === '..' || realFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} real path escapes repository`);
  if (actualPath !== absolutePath) throw new Error(`${label} URI traverses symbolic links`);
  return actualPath;
}

async function trustedRepositoryOutput(path, label) {
  const absolutePath = resolve(path);
  const pathFromRoot = relative(repositoryRoot, absolutePath);
  if (pathFromRoot === '' || pathFromRoot === '..' || pathFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} must resolve below repository`);
  let probe = absolutePath;
  let actualPath = null;
  while (!actualPath) {
    actualPath = await realpath(probe).catch(error => {
      if (error?.code !== 'ENOENT') throw error;
      const parent = dirname(probe);
      if (parent === probe) throw error;
      probe = parent;
      return null;
    });
  }
  const realFromRoot = relative(repositoryRealRoot, actualPath);
  if ((probe !== repositoryRoot && realFromRoot === '') || realFromRoot === '..' || realFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} real path escapes repository`);
  if (actualPath !== probe) throw new Error(`${label} must not traverse symbolic links`);
  return absolutePath;
}

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate, constants.X_OK); return candidate; } catch {}
  }
  throw new Error('Blender executable not found');
}

function exec(command, args) {
  return new Promise((resolvePromise, reject) => {
    execFile(command, args, { maxBuffer: 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) { reject(new Error(`${stdout}${stderr}${error.message}`)); return; }
      resolvePromise(`${stdout}${stderr}`);
    });
  });
}

function parseBlenderVersion(output) {
  const line = key => output.split('\n').find(item => item.trimStart().startsWith(`${key}:`))?.split(':').slice(1).join(':').trim() ?? null;
  return { version: output.split('\n').find(Boolean)?.trim() ?? null, buildHash: line('build hash'), buildBranch: line('build branch'), buildPlatform: line('build platform'), buildType: line('build type') };
}

function failed(reason, observed, expected = null, checks = []) {
  return { documentType: 'BFS_COMPILE_RECEIPT_VERIFICATION', version: '0.1.0', valid: false, reason, observed, expected, checks };
}

export async function verifyCompileReceipt(receiptPath) {
  const checks = [];
  try {
    const receiptFile = await trustedRepositoryFile(relative(repositoryRoot, resolve(receiptPath)), 'CompileReceipt');
    const receipt = JSON.parse(await readFile(receiptFile, 'utf8'));
    if (receipt.documentType !== 'BFS_COMPILE_RECEIPT' || receipt.version !== '0.1.0') return failed('RECEIPT_TYPE', `${receipt.documentType}@${receipt.version}`, 'BFS_COMPILE_RECEIPT@0.1.0', checks);
    const receiptBody = structuredClone(receipt);
    delete receiptBody.receiptHash;
    const computedReceiptHash = sha256Canonical(receiptBody);
    if (computedReceiptHash !== receipt.receiptHash) return failed('RECEIPT_SELF_HASH', computedReceiptHash, receipt.receiptHash, checks);
    checks.push('RECEIPT_SELF_HASH');
    const computedIdentityHash = sha256Canonical(receipt.executionIdentity);
    if (computedIdentityHash !== receipt.executionIdentityHash) return failed('EXECUTION_IDENTITY_HASH', computedIdentityHash, receipt.executionIdentityHash, checks);
    checks.push('EXECUTION_IDENTITY_HASH');

    const planPath = await trustedRepositoryFile(receipt.executionIdentity.buildPlan.uri, 'BuildPlan');
    const planMetadata = await stat(planPath);
    const planFileSha = await sha256File(planPath);
    if (planFileSha !== receipt.executionIdentity.buildPlan.sha256 || planMetadata.size !== receipt.executionIdentity.buildPlan.bytes) return failed('PLAN_FILE_SHA', { sha256: planFileSha, bytes: planMetadata.size }, { sha256: receipt.executionIdentity.buildPlan.sha256, bytes: receipt.executionIdentity.buildPlan.bytes }, checks);
    checks.push('PLAN_FILE_SHA');
    const wrapper = JSON.parse(await readFile(planPath, 'utf8'));
    const computedPlanHash = sha256Bytes(canonicalJson(wrapper.plan));
    if (computedPlanHash !== wrapper.planHash) return failed('PLAN_SELF_HASH', computedPlanHash, wrapper.planHash, checks);
    if (wrapper.planHash !== receipt.executionIdentity.buildPlan.planHash) return failed('PLAN_HASH_BINDING', wrapper.planHash, receipt.executionIdentity.buildPlan.planHash, checks);
    checks.push('PLAN_HASH_BINDING');

    const expectedToolUris = {
      sceneCompiler: 'blender/compile_scene.py',
      restrictedCli: 'scripts/run-restricted-blender-compile.mjs',
      budgetSupervisor: 'scripts/lib/budgeted-process.mjs',
      receiptGenerator: 'scripts/lib/compile-receipt.mjs',
      receiptFormat: 'scripts/lib/receipt-format.mjs',
    };
    for (const [field, expectedUri] of Object.entries(expectedToolUris)) {
      if (receipt.executionIdentity.tools[field]?.uri !== expectedUri) return failed('TOOL_URI_BINDING', receipt.executionIdentity.tools[field]?.uri, expectedUri, checks);
    }
    if (receipt.executionIdentity.configuration.budgetProfile?.uri !== 'specs/restricted-compile-budget.v0.1.json') return failed('BUDGET_PROFILE_URI_BINDING', receipt.executionIdentity.configuration.budgetProfile?.uri, 'specs/restricted-compile-budget.v0.1.json', checks);
    if (receipt.executionIdentity.configuration.ocio?.uri !== wrapper.plan.outputSpec.color.ocioConfigUri) return failed('OCIO_URI_BINDING', receipt.executionIdentity.configuration.ocio?.uri, wrapper.plan.outputSpec.color.ocioConfigUri, checks);
    checks.push('TRUSTED_URIS');

    for (const [field, reason, label] of [
      ['sceneCompiler', 'COMPILER_SHA', 'Scene compiler'],
      ['restrictedCli', 'RESTRICTED_CLI_SHA', 'Restricted CLI'],
      ['budgetSupervisor', 'BUDGET_SUPERVISOR_SHA', 'Budget supervisor'],
      ['receiptGenerator', 'RECEIPT_GENERATOR_SHA', 'Receipt generator'],
      ['receiptFormat', 'RECEIPT_FORMAT_SHA', 'Receipt format'],
    ]) {
      const identity = receipt.executionIdentity.tools[field];
      const path = await trustedRepositoryFile(identity.uri, label);
      const metadata = await stat(path);
      const observed = await sha256File(path);
      if (observed !== identity.sha256 || metadata.size !== identity.bytes) return failed(reason, { sha256: observed, bytes: metadata.size }, { sha256: identity.sha256, bytes: identity.bytes }, checks);
      checks.push(reason);
    }

    for (const [field, reason, label] of [
      ['budgetProfile', 'BUDGET_PROFILE_SHA', 'Budget profile'],
      ['ocio', 'OCIO_SHA', 'OCIO config'],
    ]) {
      const identity = receipt.executionIdentity.configuration[field];
      const path = await trustedRepositoryFile(identity.uri, label);
      const metadata = await stat(path);
      const observed = await sha256File(path);
      if (observed !== identity.sha256 || metadata.size !== identity.bytes) return failed(reason, { sha256: observed, bytes: metadata.size }, { sha256: identity.sha256, bytes: identity.bytes }, checks);
      checks.push(reason);
    }

    const blenderPath = resolve(await findBlender());
    const blenderMetadata = await stat(blenderPath);
    const blenderSha = await sha256File(blenderPath);
    if (blenderSha !== receipt.executionIdentity.runtime.blender.sha256 || blenderMetadata.size !== receipt.executionIdentity.runtime.blender.bytes) return failed('BLENDER_BINARY_SHA', { sha256: blenderSha, bytes: blenderMetadata.size }, { sha256: receipt.executionIdentity.runtime.blender.sha256, bytes: receipt.executionIdentity.runtime.blender.bytes }, checks);
    const blenderVersion = parseBlenderVersion(await exec(blenderPath, ['--version']));
    if (blenderVersion.buildHash !== receipt.executionIdentity.runtime.blender.buildHash) return failed('BLENDER_BUILD_IDENTITY', blenderVersion.buildHash, receipt.executionIdentity.runtime.blender.buildHash, checks);
    checks.push('BLENDER_BINARY_SHA');

    const nodeMetadata = await stat(process.execPath);
    const nodeSha = await sha256File(process.execPath);
    if (nodeSha !== receipt.executionIdentity.runtime.node.sha256 || nodeMetadata.size !== receipt.executionIdentity.runtime.node.bytes) return failed('NODE_BINARY_SHA', { sha256: nodeSha, bytes: nodeMetadata.size }, { sha256: receipt.executionIdentity.runtime.node.sha256, bytes: receipt.executionIdentity.runtime.node.bytes }, checks);
    if (process.version !== receipt.executionIdentity.runtime.node.version) return failed('NODE_VERSION', process.version, receipt.executionIdentity.runtime.node.version, checks);
    checks.push('NODE_BINARY_SHA');

    const artifactChecks = [
      ['budgetReport', 'BUDGET_REPORT_SHA', 'Budget report'],
      ['sceneManifest', 'MANIFEST_SHA', 'Scene manifest'],
      ['sceneStructureCanonical', 'STRUCTURE_CANONICAL_SHA', 'Canonical scene structure'],
      ['sceneBlend', 'BLEND_SHA', 'Scene blend'],
    ];
    const artifactPaths = {};
    for (const [field, reason, label] of artifactChecks) {
      const identity = receipt.run[field];
      const path = await trustedRepositoryFile(identity.uri, label);
      const metadata = await stat(path);
      const observed = await sha256File(path);
      if (observed !== identity.sha256 || metadata.size !== identity.bytes) return failed(reason, { sha256: observed, bytes: metadata.size }, { sha256: identity.sha256, bytes: identity.bytes }, checks);
      artifactPaths[field] = path;
      checks.push(reason);
    }

    const budgetReport = JSON.parse(await readFile(artifactPaths.budgetReport, 'utf8'));
    if (budgetReport.outcome !== 'PASS' || receipt.run.budgetReport.outcome !== 'PASS') return failed('BUDGET_OUTCOME_BINDING', budgetReport.outcome, 'PASS', checks);
    if (!isDeepStrictEqual(budgetReport.metrics, receipt.run.budgetReport.metrics) || budgetReport.budgetProfile?.sha256 !== receipt.executionIdentity.configuration.budgetProfile.sha256) return failed('BUDGET_REPORT_BINDING', { metrics: budgetReport.metrics, profile: budgetReport.budgetProfile?.sha256 }, { metrics: receipt.run.budgetReport.metrics, profile: receipt.executionIdentity.configuration.budgetProfile.sha256 }, checks);
    const manifest = JSON.parse(await readFile(artifactPaths.sceneManifest, 'utf8'));
    if (manifest.execution?.planHash !== receipt.executionIdentity.buildPlan.planHash || receipt.run.sceneManifest.planHash !== receipt.executionIdentity.buildPlan.planHash) return failed('MANIFEST_PLAN_BINDING', manifest.execution?.planHash, receipt.executionIdentity.buildPlan.planHash, checks);
    if (manifest.execution?.ocioConfigSha256 !== receipt.executionIdentity.configuration.ocio.sha256) return failed('MANIFEST_OCIO_BINDING', manifest.execution?.ocioConfigSha256, receipt.executionIdentity.configuration.ocio.sha256, checks);
    if (manifest.execution?.blender?.buildHash !== receipt.executionIdentity.runtime.blender.buildHash) return failed('MANIFEST_BLENDER_BINDING', manifest.execution?.blender?.buildHash, receipt.executionIdentity.runtime.blender.buildHash, checks);
    const canonicalStructureBytes = await readFile(artifactPaths.sceneStructureCanonical);
    const structureHash = sha256Bytes(canonicalStructureBytes);
    if (!isDeepStrictEqual(JSON.parse(canonicalStructureBytes), manifest.structure)) return failed('MANIFEST_STRUCTURE_CONTENT', 'parsed canonical structure differs from manifest structure', 'deep equality', checks);
    if (structureHash !== manifest.structureHash || structureHash !== manifest.structureCanonical?.sha256 || receipt.run.sceneManifest.structureHash !== manifest.structureHash || receipt.run.sceneStructureCanonical.structureHash !== manifest.structureHash) return failed('MANIFEST_STRUCTURE_BINDING', structureHash, receipt.run.sceneManifest.structureHash, checks);
    checks.push('MANIFEST_BINDINGS');
    return { documentType: 'BFS_COMPILE_RECEIPT_VERIFICATION', version: '0.1.0', valid: true, reason: 'OK', receiptHash: receipt.receiptHash, executionIdentityHash: receipt.executionIdentityHash, planHash: wrapper.planHash, structureHash: manifest.structureHash, checks };
  } catch (error) {
    return failed('VERIFIER_ERROR', error.message, null, checks);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const option = name => { const index = args.indexOf(name); return index >= 0 ? args[index + 1] : null; };
  const receipt = option('--receipt');
  const report = option('--report');
  if (!receipt) throw new Error('Usage: --receipt FILE [--report FILE]');
  const result = await verifyCompileReceipt(receipt);
  if (report) await writeFile(await trustedRepositoryOutput(report, 'Receipt verifier report'), `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`BFS_RECEIPT_VERIFY ${result.valid ? 'PASS' : 'FAIL'} ${result.reason}\n`);
  if (!result.valid) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { process.stderr.write(`BFS_RECEIPT_VERIFY_ERROR ${error.message}\n`); process.exitCode = 1; });
}
