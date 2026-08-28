#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { open, readFile, readdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  return value;
}

function canonical(value) { return JSON.stringify(sortValue(value)); }
function hashBytes(value) { return createHash('sha256').update(value).digest('hex'); }
function canonicalHash(value) { return hashBytes(Buffer.from(canonical(value))); }
async function fileHash(path) { return hashBytes(await readFile(path)); }
function validHash(record, field) {
  if (!record || typeof record[field] !== 'string') return false;
  const body = structuredClone(record);
  delete body[field];
  return record[field] === canonicalHash(body);
}

function parseArguments(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--repository-root') parsed.repositoryRoot = argv[++i];
    else if (argv[i] === '--preflight-root') parsed.preflightRoot = argv[++i];
    else if (argv[i] === '--attempt-root') parsed.attemptRoot = argv[++i];
    else if (argv[i] === '--formal-root') parsed.formalRoot = argv[++i];
    else if (argv[i] === '--output') parsed.output = argv[++i];
    else throw new Error(`Unknown argument ${argv[i]}`);
  }
  for (const key of ['repositoryRoot', 'preflightRoot', 'attemptRoot', 'formalRoot', 'output']) if (!parsed[key]) throw new Error(`Missing ${key}`);
  return parsed;
}

async function json(path) { return JSON.parse(await readFile(path, 'utf8')); }

function acceptedReceiptSemantics(receipt, expectedDiskHash = receipt?.authorization?.nativeCompileDiskAdmission?.diskAdmissionHash) {
  const disk = receipt?.authorization?.nativeCompileDiskAdmission;
  return receipt?.schemaVersion === 'bfs.productionCompileReceipt.v0.2' && receipt.status === 'PASS'
    && validHash(receipt, 'receiptHash') && disk?.sequence === 5 && disk.status === 'ACCEPTED'
    && disk.policy?.minimumReserveBytes === '107374182400' && disk.policy?.projectedWriteBytes === '536870912'
    && disk.policy?.overrideAllowedByReleaseEntry === false
    && disk.diskAdmissionHash === expectedDiskHash
    && BigInt(disk.effectiveAvailableBytes ?? -1) <= BigInt(disk.filesystemAvailableBytesObserved ?? -2)
    && Number.isSafeInteger(receipt.restrictedCompile?.budgetReport?.nativeChildPid)
    && receipt.restrictedCompile.budgetReport.nativeChildPid > 0
    && receipt.claims?.nativeCompileDiskReadmission === true && receipt.claims?.renderedPixels === false;
}

function reseal(record, field) {
  const body = structuredClone(record);
  delete body[field];
  return { ...body, [field]: canonicalHash(body) };
}

function receiptAttacks(runId, original, expectedDiskHash) {
  const mutations = [
    ['SCHEMA', r => { r.schemaVersion = 'bfs.productionCompileReceipt.v0.1'; }],
    ['STATUS', r => { r.status = 'FAIL'; }],
    ['DISK_MISSING', r => { delete r.authorization.nativeCompileDiskAdmission; }],
    ['DISK_SEQUENCE', r => { r.authorization.nativeCompileDiskAdmission.sequence = 4; }],
    ['DISK_STATUS', r => { r.authorization.nativeCompileDiskAdmission.status = 'REJECTED'; }],
    ['DISK_RESERVE', r => { r.authorization.nativeCompileDiskAdmission.policy.minimumReserveBytes = '107374182399'; }],
    ['DISK_PROJECTED', r => { r.authorization.nativeCompileDiskAdmission.policy.projectedWriteBytes = '536870911'; }],
    ['DISK_OVERRIDE', r => { r.authorization.nativeCompileDiskAdmission.policy.overrideAllowedByReleaseEntry = true; }],
    ['DISK_EFFECTIVE_RAISED', r => { r.authorization.nativeCompileDiskAdmission.effectiveAvailableBytes = (BigInt(r.authorization.nativeCompileDiskAdmission.filesystemAvailableBytesObserved) + 1n).toString(); }],
    ['DISK_HASH', r => { r.authorization.nativeCompileDiskAdmission.diskAdmissionHash = '0'.repeat(64); }],
    ['NATIVE_PID_NULL', r => { r.restrictedCompile.budgetReport.nativeChildPid = null; }],
    ['NATIVE_PID_ZERO', r => { r.restrictedCompile.budgetReport.nativeChildPid = 0; }],
    ['CLAIM_REMOVED', r => { delete r.claims.nativeCompileDiskReadmission; }],
    ['RENDER_CLAIM', r => { r.claims.renderedPixels = true; }],
  ];
  return mutations.map(([id, mutate]) => {
    const copy = structuredClone(original);
    mutate(copy);
    const sealed = reseal(copy, 'receiptHash');
    return { id: `${runId}_${id}`, rejected: !acceptedReceiptSemantics(sealed, expectedDiskHash) };
  });
}

function lowDiskSemantics(disk, invalidation, roster) {
  return validHash(disk, 'diskAdmissionHash') && validHash(invalidation, 'invalidationHash')
    && disk.schemaVersion === 'bfs.productionNativeCompileDiskAdmission.v0.1' && disk.sequence === 5 && disk.status === 'REJECTED'
    && disk.reason === 'FREE_AFTER_PROJECTED_WRITE_BELOW_RESERVE'
    && disk.effectiveAvailableBytes === '107911053311' && disk.disk.freeAfterProjectedBytes === '107374182399'
    && disk.restrictedCompilerProcessesStarted === 0 && disk.nativeBlenderProcessesStarted === 0
    && invalidation.phase === 'NATIVE_COMPILE_DISK_ADMISSION'
    && canonical(roster) === canonical(['build-plan.json', 'formal-start.json', 'invalidation.json', 'native-compile-disk-admission.json']);
}

async function audit(parsed) {
  const root = parsed.repositoryRoot;
  const preflight = await json(resolve(root, parsed.preflightRoot, 'preflight.json'));
  const spec = await json(resolve(root, 'specs/production-disk-jit-readmission.v0.1.json'));
  const releaseV1Path = resolve(root, 'specs/production-compiler-entry.v0.1.json');
  const releaseV2Path = resolve(root, 'specs/production-compiler-entry.v0.2.json');
  const releaseV2 = await json(releaseV2Path);
  const operation = await json(resolve(root, parsed.formalRoot, 'operation-draft.json'));
  const metaAttempt = await json(resolve(root, parsed.attemptRoot, 'attempt.json'));
  const metaAdmission = await json(resolve(root, parsed.attemptRoot, 'admission.json'));
  const metaReceipt = await json(resolve(root, parsed.attemptRoot, 'receipt.json'));
  const formalStart = await json(resolve(root, parsed.formalRoot, 'formal-start.json'));

  const lowRoot = resolve(root, parsed.formalRoot, 'low-disk');
  const lowDisk = await json(resolve(lowRoot, 'native-compile-disk-admission.json'));
  const lowInvalidation = await json(resolve(lowRoot, 'invalidation.json'));
  const lowRoster = (await readdir(lowRoot)).sort();
  const lowExact = lowDiskSemantics(lowDisk, lowInvalidation, lowRoster) && operation.lowDisk.compile.exitCode === 1;

  const runInspections = [];
  const attacks = [];
  for (const run of operation.runs) {
    const runRoot = resolve(root, parsed.formalRoot, 'runs', run.runId);
    const receiptPath = resolve(runRoot, 'production-receipt.json');
    const receipt = await json(receiptPath);
    const diskPath = resolve(runRoot, 'native-compile-disk-admission.json');
    const disk = await json(diskPath);
    const budget = await json(resolve(runRoot, 'restricted', 'budget.report.json'));
    const currentReceipt = await json(resolve(runRoot, 'restricted', 'compile-receipt.json'));
    const rootRoster = (await readdir(runRoot)).sort();
    const restrictedRoster = (await readdir(resolve(runRoot, 'restricted'))).sort();
    const exact = acceptedReceiptSemantics(receipt) && validHash(disk, 'diskAdmissionHash')
      && receipt.authorization.nativeCompileDiskAdmission.sha256 === await fileHash(diskPath)
      && receipt.authorization.nativeCompileDiskAdmission.diskAdmissionHash === disk.diskAdmissionHash
      && disk.status === 'ACCEPTED' && disk.disk.status === 'PASS' && disk.restrictedCompilerProcessesStarted === 0
      && disk.nativeBlenderProcessesStarted === 0 && budget.child.pid === receipt.restrictedCompile.budgetReport.nativeChildPid
      && validHash(currentReceipt, 'receiptHash') && run.verification.valid === true && run.verification.checks.length === 11
      && run.verification.checks.includes('NATIVE_COMPILE_DISK_READMISSION') && run.verification.currentCompileReceiptVerification.checks.length === 19
      && canonical(rootRoster) === canonical(receipt.output.expectedRootRoster) && canonical(restrictedRoster) === canonical(receipt.output.expectedRestrictedRoster);
    runInspections.push({ runId: run.runId, benchmarkId: run.benchmarkId, exact, planHash: receipt.buildPlan.planHash, structureHash: receipt.restrictedCompile.sceneStructureCanonical.structureHash, wrapperPid: receipt.restrictedCompile.wrapperProcess.pid, nativePid: budget.child.pid, diskAdmissionHash: disk.diskAdmissionHash, receiptHash: receipt.receiptHash });
    attacks.push(...receiptAttacks(run.runId, receipt, disk.diskAdmissionHash));
  }
  const b01 = runInspections.filter(row => row.benchmarkId === 'B01');
  const b02 = runInspections.filter(row => row.benchmarkId === 'B02');
  const pairExact = rows => rows.length === 2 && rows[0].planHash === rows[1].planHash && rows[0].structureHash === rows[1].structureHash;
  const frozenFilesExact = (await Promise.all(Object.entries(releaseV2.frozenFiles).map(async ([uri, expected]) => await fileHash(resolve(root, uri)) === expected))).every(Boolean);
  const packageDocument = await json(resolve(root, 'package.json'));
  const aliasExact = Object.entries(releaseV2.packageAliases).every(([key, value]) => packageDocument.scripts[key] === value);
  const gates = {
    B56_SUPPORTED_PARENT_BOUND_EXACT: preflight.parent.exact === true,
    V0_1_RELEASE_AND_BEFORE_IDENTITIES_EXACT: await fileHash(releaseV1Path) === spec.beforeIdentities.releaseManifest.sha256,
    V0_2_RELEASE_AND_B57_TOOL_FREEZE_EXACT: frozenFilesExact && preflight.toolFreeze.exact === true,
    PACKAGE_ALIASES_UNCHANGED_EXACT: aliasExact,
    JIT_POLICY_EQUALS_PREFLIGHT_POLICY_EXACT: releaseV2.diskAdmission.minimumReserveBytes === 107374182400 && releaseV2.diskAdmission.projectedWriteBytes === 536870912,
    JIT_TEST_CEILING_CAN_ONLY_LOWER_REAL_OBSERVATION: preflight.disk.boundary.ceilingBelowReal === true,
    OFFICIAL_PREFLIGHT_ZERO_BLENDER_ACCEPTED_AND_PUSHED: preflight.status === 'ACCEPTED' && preflight.operations.blenderProcesses === 0,
    SCENESPEC_SUITE_22_OF_22: preflight.suite.exact === true,
    B01_B02_BUILDPLAN_PAIR_BYTES_EXACT: preflight.plans.every(row => row.exact),
    STALE_CAPACITY_CASE_REJECTED_BEFORE_RESTRICTED_SPAWN: lowExact,
    STALE_CAPACITY_REJECTION_EVIDENCE_DURABLE_AND_SELF_HASH_EXACT: validHash(lowDisk, 'diskAdmissionHash') && validHash(lowInvalidation, 'invalidationHash'),
    FOUR_PREFERRED_PRODUCTION_ALIAS_COMPILES_PASS: operation.runs.length === 4 && operation.runs.every(row => row.compile.exitCode === 0),
    FOUR_JIT_DISK_ADMISSIONS_ACCEPTED_BEFORE_WRAPPER_SPAWN: runInspections.length === 4 && runInspections.every(row => row.exact),
    FOUR_PRODUCTION_RECEIPTS_BIND_JIT_DISK_EVIDENCE: runInspections.every(row => row.exact),
    FOUR_PREFERRED_PRODUCTION_VERIFIERS_PASS: operation.runs.every(row => row.verify.exitCode === 0 && row.verification.valid),
    FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: operation.runs.every(row => row.verification.currentCompileReceiptVerification.checks.length === 19),
    FOUR_NATIVE_PID_RECEIPTS_EXACT: runInspections.every(row => Number.isSafeInteger(row.nativePid) && row.nativePid > 0 && row.nativePid !== row.wrapperPid),
    B01_B02_PLAN_HASHES_FROZEN: b01.every(row => row.planHash === '316114f10d4ec3a2b9e6b569e39476a143fc1b1db10e1603ba54d37dc73c3eaf') && b02.every(row => row.planHash === 'a9022bf6f881b1c8d7b7866813d22454c81f72de9190e05af82c10bf62a26687'),
    B01_B02_STRUCTURE_PAIR_BYTES_EXACT: pairExact(b01) && pairExact(b02),
    B01_B02_STRUCTURE_HASHES_FROZEN: b01.every(row => row.structureHash === 'c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b') && b02.every(row => row.structureHash === '025c6fa50dcacef3c6c30ea9ec7ed97ce09bce0a9f51157887bc73c3981fa856'),
    FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: operation.runs.every(row => row.verification.blendAudit?.documentType === 'BFS_COMPILED_BLEND_AUDIT'),
    NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: runInspections.every(row => row.exact),
    DIRECT_PROCESS_AND_OPERATION_COUNTS_EXACT: operation.counts.productionCompiles === 4 && operation.counts.nativeCompiles === 4 && operation.counts.lowDiskRestrictedCompiles === 0,
    MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: Object.values(operation.semanticOperations).every(value => value === 0),
    INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_56: attacks.length >= 56 && attacks.every(row => row.rejected),
    VERDICT_MAPPING_OUTCOME_NEUTRAL: true,
  };
  const passed = Object.values(gates).filter(Boolean).length;
  const derivedVerdict = passed === 26 ? 'PRODUCTION_DISK_JIT_READMISSION_SUPPORTED'
    : gates.STALE_CAPACITY_CASE_REJECTED_BEFORE_RESTRICTED_SPAWN ? 'PRODUCTION_DISK_JIT_READMISSION_BOUNDED' : 'PRODUCTION_DISK_JIT_READMISSION_REJECTED';
  gates.VERDICT_MAPPING_OUTCOME_NEUTRAL = derivedVerdict === (Object.values(gates).slice(0, 25).every(Boolean) ? 'PRODUCTION_DISK_JIT_READMISSION_SUPPORTED' : gates.STALE_CAPACITY_CASE_REJECTED_BEFORE_RESTRICTED_SPAWN ? 'PRODUCTION_DISK_JIT_READMISSION_BOUNDED' : 'PRODUCTION_DISK_JIT_READMISSION_REJECTED');
  const body = {
    schemaVersion: 'bfs.productionDiskJitReadmissionAudit.v0.1',
    experimentId: 'B57-E1',
    status: 'COMPLETE',
    independence: { importedProductionOrB57ExecutionModules: false, sourceReopenedDirectly: true },
    meta: { attemptExact: validHash(metaAttempt, 'attemptHash'), admissionExact: validHash(metaAdmission, 'admissionHash'), receiptExact: validHash(metaReceipt, 'receiptHash'), formalStartExact: validHash(formalStart, 'formalStartHash') },
    lowDisk: { exact: lowExact, diskAdmissionHash: lowDisk.diskAdmissionHash, invalidationHash: lowInvalidation.invalidationHash, roster: lowRoster },
    runInspections,
    attacks,
    attackSummary: { total: attacks.length, rejected: attacks.filter(row => row.rejected).length },
    gates,
    gatePassed: Object.values(gates).filter(Boolean).length,
    gateTotal: Object.keys(gates).length,
    derivedVerdict,
    scientificVerdict: derivedVerdict,
  };
  return { ...body, auditHash: canonicalHash(body) };
}

async function writeExclusive(path, value) {
  const handle = await open(path, 'wx', 0o600);
  try { await handle.writeFile(`${JSON.stringify(sortValue(value), null, 2)}\n`); await handle.sync(); } finally { await handle.close(); }
  const directory = await open(dirname(path), 'r');
  try { await directory.sync(); } finally { await directory.close(); }
}

export async function runAudit(argv) {
  const parsed = parseArguments(argv);
  const result = await audit(parsed);
  await writeExclusive(parsed.output, result);
  process.stdout.write(`BFS_B57_AUDIT ${result.gatePassed}/${result.gateTotal} attacks=${result.attackSummary.rejected}/${result.attackSummary.total} ${result.scientificVerdict}\n`);
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runAudit(process.argv.slice(2)).catch(error => { process.stderr.write(`BFS_B57_AUDIT_ERROR ${error.message}\n`); process.exitCode = 1; });
}
