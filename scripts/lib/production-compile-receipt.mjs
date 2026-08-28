import { createHash } from 'node:crypto';
import { lstat, mkdir, open, readFile, readdir, realpath, stat } from 'node:fs/promises';
import { dirname, isAbsolute, normalize, relative, resolve, sep } from 'node:path';
import { isDeepStrictEqual } from 'node:util';
import { repositoryRoot } from './scene-spec.mjs';

const repositoryRealRoot = await realpath(repositoryRoot);

export function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortValue(value[key])]));
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(sortValue(value));
}

export function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

export function canonicalHash(value) {
  return sha256Bytes(Buffer.from(canonicalJson(value)));
}

export async function sha256File(filePath) {
  return sha256Bytes(await readFile(filePath));
}

export function repoUri(absolutePath) {
  return relative(repositoryRoot, absolutePath).split(sep).join('/');
}

function below(root, candidate) {
  const fromRoot = relative(root, candidate);
  return fromRoot !== '' && fromRoot !== '..' && !fromRoot.startsWith(`..${sep}`) && !isAbsolute(fromRoot);
}

function requireRelativeSpelling(spelling, label) {
  if (typeof spelling !== 'string' || spelling.length === 0) throw new Error(`${label} spelling is missing`);
  if (isAbsolute(spelling) || spelling.includes('\\')) throw new Error(`${label} must use a repository-relative POSIX spelling`);
  const normalized = normalize(spelling).split(sep).join('/');
  if (normalized !== spelling || spelling === '.' || spelling.startsWith('../')) {
    throw new Error(`${label} must be a normalized repository-relative spelling`);
  }
}

async function state(filePath) {
  try { return await lstat(filePath); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

async function requireRealContained(candidate, label, allowRoot = false) {
  const actual = await realpath(candidate);
  const fromRoot = relative(repositoryRealRoot, actual);
  if ((!allowRoot && fromRoot === '') || fromRoot === '..' || fromRoot.startsWith(`..${sep}`)) {
    throw new Error(`${label} resolves outside the repository`);
  }
  if (actual !== candidate) throw new Error(`${label} traverses a symbolic link`);
  return actual;
}

export async function resolveExistingRepositoryPath(spelling, label, expected = 'file') {
  requireRelativeSpelling(spelling, label);
  const candidate = resolve(repositoryRoot, spelling);
  if (!below(repositoryRoot, candidate)) throw new Error(`${label} resolves outside the repository`);
  const metadata = await state(candidate);
  if (!metadata) throw new Error(`${label} is missing`);
  if (metadata.isSymbolicLink()) throw new Error(`${label} is a symbolic link`);
  await requireRealContained(candidate, label);
  if (expected === 'file' && !metadata.isFile()) throw new Error(`${label} is not a file`);
  if (expected === 'directory' && !metadata.isDirectory()) throw new Error(`${label} is not a directory`);
  return candidate;
}

export async function resolveFreshRepositoryPath(spelling, label) {
  requireRelativeSpelling(spelling, label);
  const candidate = resolve(repositoryRoot, spelling);
  if (!below(repositoryRoot, candidate)) throw new Error(`${label} resolves outside the repository`);
  if (await state(candidate)) throw new Error(`${label} already exists`);
  let ancestor = dirname(candidate);
  let metadata = await state(ancestor);
  while (!metadata) {
    const parent = dirname(ancestor);
    if (parent === ancestor) throw new Error(`${label} has no repository-contained ancestor`);
    ancestor = parent;
    metadata = await state(ancestor);
  }
  if (metadata.isSymbolicLink() || !metadata.isDirectory()) throw new Error(`${label} ancestor is not a trusted directory`);
  await requireRealContained(ancestor, `${label} ancestor`, ancestor === repositoryRoot);
  return candidate;
}

async function syncDirectory(directory) {
  const handle = await open(directory, 'r');
  try { await handle.sync(); } finally { await handle.close(); }
}

export async function durableMkdir(directory) {
  await mkdir(directory, { recursive: false });
  await syncDirectory(directory);
  await syncDirectory(dirname(directory));
}

export async function writeDurableJson(filePath, value) {
  const handle = await open(filePath, 'wx', 0o600);
  try {
    await handle.writeFile(`${JSON.stringify(sortValue(value), null, 2)}\n`, 'utf8');
    await handle.sync();
  } finally {
    await handle.close();
  }
  await syncDirectory(dirname(filePath));
}

export async function writeDurableHashed(filePath, body, hashField) {
  const record = { ...body, [hashField]: canonicalHash(body) };
  await writeDurableJson(filePath, record);
  return record;
}

export function validSelfHash(record, hashField) {
  if (!record || typeof record !== 'object' || typeof record[hashField] !== 'string') return false;
  const body = structuredClone(record);
  delete body[hashField];
  return record[hashField] === canonicalHash(body);
}

export async function fileIdentity(filePath, uri = repoUri(filePath)) {
  const metadata = await stat(filePath);
  if (!metadata.isFile()) throw new Error(`Identity target is not a file: ${uri}`);
  return { uri, sha256: await sha256File(filePath), bytes: metadata.size };
}

function requireHashedRecord(record, hashField, label) {
  if (!validSelfHash(record, hashField)) throw new Error(`${label} self-hash mismatch`);
  return record;
}

export async function createProductionCompileReceipt({
  releaseManifestPath,
  releaseCommit,
  preflightPath,
  attemptPath,
  admissionPath,
  attemptReceiptPath,
  formalStartPath,
  diskAdmissionPath,
  sceneSpecPath,
  planPath,
  restrictedRoot,
  wrapperProcess,
}) {
  const budgetReportPath = resolve(restrictedRoot, 'budget.report.json');
  const compileReceiptPath = resolve(restrictedRoot, 'compile-receipt.json');
  const manifestPath = resolve(restrictedRoot, 'scene.manifest.json');
  const structurePath = resolve(restrictedRoot, 'scene.structure.canonical.json');
  const blendPath = resolve(restrictedRoot, 'scene.blend');
  const outputRoot = dirname(formalStartPath);

  const release = JSON.parse(await readFile(releaseManifestPath, 'utf8'));
  const preflight = requireHashedRecord(JSON.parse(await readFile(preflightPath, 'utf8')), 'preflightHash', 'Production preflight');
  const attempt = requireHashedRecord(JSON.parse(await readFile(attemptPath, 'utf8')), 'attemptHash', 'Production attempt');
  const admission = requireHashedRecord(JSON.parse(await readFile(admissionPath, 'utf8')), 'admissionHash', 'Production admission');
  const attemptReceipt = requireHashedRecord(JSON.parse(await readFile(attemptReceiptPath, 'utf8')), 'receiptHash', 'Production attempt receipt');
  const formalStart = requireHashedRecord(JSON.parse(await readFile(formalStartPath, 'utf8')), 'formalStartHash', 'Production formal start');
  const diskAdmission = requireHashedRecord(JSON.parse(await readFile(diskAdmissionPath, 'utf8')), 'diskAdmissionHash', 'Native compile disk admission');
  const wrapper = JSON.parse(await readFile(planPath, 'utf8'));
  const budgetReport = JSON.parse(await readFile(budgetReportPath, 'utf8'));
  const compileReceipt = JSON.parse(await readFile(compileReceiptPath, 'utf8'));
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const structureBytes = await readFile(structurePath);
  const structureHash = sha256Bytes(structureBytes);

  if (release.schemaVersion !== 'bfs.productionCompilerEntry.v0.2') throw new Error('Production release manifest schema mismatch');
  if (preflight.status !== 'ACCEPTED') throw new Error('Production preflight is not accepted');
  if (attempt.sequence !== 1 || admission.sequence !== 2 || attemptReceipt.sequence !== 3 || formalStart.sequence !== 4) {
    throw new Error('Production authorization sequence mismatch');
  }
  if (diskAdmission.schemaVersion !== 'bfs.productionNativeCompileDiskAdmission.v0.1' || diskAdmission.sequence !== 5 || diskAdmission.status !== 'ACCEPTED'
    || diskAdmission.disk?.status !== 'PASS' || diskAdmission.policy?.minimumReserveBytes !== '107374182400'
    || diskAdmission.policy?.projectedWriteBytes !== '536870912' || diskAdmission.policy?.overrideAllowedByReleaseEntry !== false
    || BigInt(diskAdmission.effectiveAvailableBytes) > BigInt(diskAdmission.filesystemAvailableBytesObserved)) {
    throw new Error('Native compile disk admission binding mismatch');
  }
  if (canonicalHash(wrapper.plan) !== wrapper.planHash) throw new Error('Production BuildPlan self-hash mismatch');
  if (budgetReport.documentType !== 'BFS_BUDGETED_PROCESS_RESULT' || budgetReport.version !== '0.2.0' || budgetReport.outcome !== 'PASS') {
    throw new Error('Production budget report schema or outcome mismatch');
  }
  if (!Number.isSafeInteger(budgetReport.child?.pid) || budgetReport.child.pid <= 0) throw new Error('Production native child PID is invalid');
  if (compileReceipt.documentType !== 'BFS_COMPILE_RECEIPT' || compileReceipt.version !== '0.1.0') throw new Error('Current CompileReceipt schema mismatch');
  if (manifest.execution?.planHash !== wrapper.planHash) throw new Error('Production manifest plan binding mismatch');
  if (structureHash !== manifest.structureHash || structureHash !== manifest.structureCanonical?.sha256) throw new Error('Production structure hash binding mismatch');
  if (!isDeepStrictEqual(JSON.parse(structureBytes), manifest.structure)) throw new Error('Production canonical structure content mismatch');

  const rootRosterBeforeReceipt = (await readdir(outputRoot)).sort();
  const restrictedRoster = (await readdir(restrictedRoot)).sort();
  const expectedRootBeforeReceipt = ['build-plan.json', 'formal-start.json', 'native-compile-disk-admission.json', 'restricted'];
  const expectedRestricted = ['budget.report.json', 'compile-receipt.json', 'scene.blend', 'scene.manifest.json', 'scene.structure.canonical.json'];
  if (!isDeepStrictEqual(rootRosterBeforeReceipt, expectedRootBeforeReceipt)) throw new Error(`Unexpected production output root roster: ${rootRosterBeforeReceipt.join(', ')}`);
  if (!isDeepStrictEqual(restrictedRoster, expectedRestricted)) throw new Error(`Unexpected restricted output roster: ${restrictedRoster.join(', ')}`);

  const body = {
    schemaVersion: 'bfs.productionCompileReceipt.v0.2',
    status: 'PASS',
    release: { ...(await fileIdentity(releaseManifestPath)), releaseCommit, releaseId: release.releaseId },
    authorization: {
      preflight: { ...(await fileIdentity(preflightPath)), preflightHash: preflight.preflightHash, status: preflight.status },
      attempt: { ...(await fileIdentity(attemptPath)), attemptHash: attempt.attemptHash, sequence: attempt.sequence },
      admission: { ...(await fileIdentity(admissionPath)), admissionHash: admission.admissionHash, sequence: admission.sequence, status: admission.status },
      attemptReceipt: { ...(await fileIdentity(attemptReceiptPath)), receiptHash: attemptReceipt.receiptHash, sequence: attemptReceipt.sequence, status: attemptReceipt.status },
      formalStart: { ...(await fileIdentity(formalStartPath)), formalStartHash: formalStart.formalStartHash, sequence: formalStart.sequence },
      nativeCompileDiskAdmission: { ...(await fileIdentity(diskAdmissionPath)), diskAdmissionHash: diskAdmission.diskAdmissionHash, sequence: diskAdmission.sequence, status: diskAdmission.status, filesystemAvailableBytesObserved: diskAdmission.filesystemAvailableBytesObserved, effectiveAvailableBytes: diskAdmission.effectiveAvailableBytes, testCeilingApplied: diskAdmission.testCeilingApplied, policy: diskAdmission.policy },
    },
    source: await fileIdentity(sceneSpecPath),
    buildPlan: { ...(await fileIdentity(planPath)), planHash: wrapper.planHash, planVersion: wrapper.planVersion, sourceSceneCanonicalSha256: wrapper.plan.source.canonicalSha256 },
    restrictedCompile: {
      wrapperProcess,
      budgetReport: { ...(await fileIdentity(budgetReportPath)), documentType: budgetReport.documentType, version: budgetReport.version, outcome: budgetReport.outcome, nativeChildPid: budgetReport.child.pid },
      compileReceipt: { ...(await fileIdentity(compileReceiptPath)), receiptHash: compileReceipt.receiptHash, executionIdentityHash: compileReceipt.executionIdentityHash },
      sceneManifest: { ...(await fileIdentity(manifestPath)), manifestVersion: manifest.manifestVersion, planHash: manifest.execution.planHash, structureHash: manifest.structureHash },
      sceneStructureCanonical: { ...(await fileIdentity(structurePath)), structureHash },
      sceneBlend: await fileIdentity(blendPath),
    },
    output: {
      root: repoUri(outputRoot),
      expectedRootRoster: [...expectedRootBeforeReceipt, 'production-receipt.json'].sort(),
      expectedRestrictedRoster: expectedRestricted,
    },
    claims: {
      admissionPrecedesOutput: true,
      nativeCompileDiskReadmission: true,
      exactArtifactBinding: true,
      supervisorLocalNativePidReceipt: true,
      signed: false,
      remotelyAttested: false,
      deterministicBlendContainerBytes: false,
      renderedPixels: false,
    },
  };
  return { ...body, receiptHash: canonicalHash(body) };
}
