import { access, readFile, realpath, stat } from 'node:fs/promises';
import { constants } from 'node:fs';
import { execFile } from 'node:child_process';
import { isDeepStrictEqual } from 'node:util';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './scene-spec.mjs';
import { canonicalJson, rehashReceipt, sha256Bytes, sha256File } from './receipt-format.mjs';

const repositoryRealRoot = await realpath(repositoryRoot);

function repoUri(path) {
  return relative(repositoryRoot, path).split(sep).join('/');
}

async function trustedRepositoryFile(path, label) {
  const absolutePath = resolve(path);
  const pathFromRoot = relative(repositoryRoot, absolutePath);
  if (pathFromRoot === '' || pathFromRoot === '..' || pathFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} must resolve below the repository root`);
  const actualPath = await realpath(absolutePath).catch(() => { throw new Error(`${label} is missing`); });
  const realFromRoot = relative(repositoryRealRoot, actualPath);
  if (realFromRoot === '' || realFromRoot === '..' || realFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} resolves outside the repository root`);
  if (actualPath !== absolutePath) throw new Error(`${label} must not traverse symbolic links`);
  return absolutePath;
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
  const firstLine = output.split('\n').find(Boolean)?.trim() ?? null;
  return { version: firstLine, buildHash: line('build hash'), buildBranch: line('build branch'), buildPlatform: line('build platform'), buildType: line('build type') };
}

async function fileIdentity(path, uri = null) {
  const metadata = await stat(path);
  return { ...(uri ? { uri } : {}), sha256: await sha256File(path), bytes: metadata.size };
}

export async function createCompileReceipt({ planPath, outputDir, budgetReportPath, budgetResult }) {
  const planFile = await trustedRepositoryFile(planPath, 'CompileReceipt BuildPlan');
  const reportFile = await trustedRepositoryFile(budgetReportPath, 'CompileReceipt budget report');
  const manifestFile = await trustedRepositoryFile(resolve(outputDir, 'scene.manifest.json'), 'CompileReceipt scene manifest');
  const structureCanonicalFile = await trustedRepositoryFile(resolve(outputDir, 'scene.structure.canonical.json'), 'CompileReceipt canonical structure');
  const blendFile = await trustedRepositoryFile(resolve(outputDir, 'scene.blend'), 'CompileReceipt scene blend');
  const sceneCompiler = await trustedRepositoryFile(resolve(repositoryRoot, 'blender/compile_scene.py'), 'CompileReceipt scene compiler');
  const restrictedCli = await trustedRepositoryFile(resolve(repositoryRoot, 'scripts/run-restricted-blender-compile.mjs'), 'CompileReceipt restricted CLI');
  const budgetSupervisor = await trustedRepositoryFile(resolve(repositoryRoot, 'scripts/lib/budgeted-process.mjs'), 'CompileReceipt budget supervisor');
  const receiptGenerator = await trustedRepositoryFile(resolve(repositoryRoot, 'scripts/lib/compile-receipt.mjs'), 'CompileReceipt generator');
  const receiptFormat = await trustedRepositoryFile(resolve(repositoryRoot, 'scripts/lib/receipt-format.mjs'), 'CompileReceipt format');
  const budgetProfile = await trustedRepositoryFile(resolve(repositoryRoot, 'specs/restricted-compile-budget.v0.1.json'), 'CompileReceipt budget profile');

  const wrapperBytes = await readFile(planFile);
  const wrapper = JSON.parse(wrapperBytes);
  const computedPlanHash = sha256Bytes(canonicalJson(wrapper.plan));
  if (computedPlanHash !== wrapper.planHash) throw new Error(`CompileReceipt BuildPlan self-hash mismatch: expected ${wrapper.planHash}, received ${computedPlanHash}`);
  const ocioUri = wrapper.plan.outputSpec.color.ocioConfigUri;
  const ocioFile = await trustedRepositoryFile(resolve(repositoryRoot, ocioUri), 'CompileReceipt OCIO config');
  const manifest = JSON.parse(await readFile(manifestFile, 'utf8'));
  if (manifest.execution?.planHash !== wrapper.planHash) throw new Error('CompileReceipt manifest plan binding mismatch');
  if (manifest.execution?.ocioConfigSha256 !== wrapper.plan.outputSpec.color.verifiedOcioConfigSha256) throw new Error('CompileReceipt manifest OCIO binding mismatch');
  const structureCanonicalBytes = await readFile(structureCanonicalFile);
  const computedStructureHash = sha256Bytes(structureCanonicalBytes);
  if (computedStructureHash !== manifest.structureHash || computedStructureHash !== manifest.structureCanonical?.sha256) throw new Error('CompileReceipt canonical structure hash mismatch');
  if (!isDeepStrictEqual(JSON.parse(structureCanonicalBytes), manifest.structure)) throw new Error('CompileReceipt canonical structure content mismatch');
  if (budgetResult.outcome !== 'PASS') throw new Error(`CompileReceipt requires a passing budget result, received ${budgetResult.outcome}`);

  const blenderBinary = resolve(budgetResult.command);
  await access(blenderBinary, constants.X_OK);
  const blenderVersion = parseBlenderVersion(await exec(blenderBinary, ['--version']));
  if (manifest.execution?.blender?.buildHash !== blenderVersion.buildHash) throw new Error('CompileReceipt manifest Blender build binding mismatch');
  const budgetProfileIdentity = await fileIdentity(budgetProfile, repoUri(budgetProfile));
  if (budgetProfileIdentity.sha256 !== budgetResult.budgetProfile?.sha256) throw new Error('CompileReceipt budget profile binding mismatch');
  const ocioIdentity = await fileIdentity(ocioFile, repoUri(ocioFile));
  if (ocioIdentity.sha256 !== wrapper.plan.outputSpec.color.verifiedOcioConfigSha256) throw new Error('CompileReceipt OCIO file hash mismatch');

  const executionIdentity = {
    buildPlan: { ...(await fileIdentity(planFile, repoUri(planFile))), planHash: wrapper.planHash, planVersion: wrapper.planVersion, sourceSceneCanonicalSha256: wrapper.plan.source.canonicalSha256, shotId: wrapper.plan.shot.id },
    tools: {
      sceneCompiler: await fileIdentity(sceneCompiler, repoUri(sceneCompiler)),
      restrictedCli: await fileIdentity(restrictedCli, repoUri(restrictedCli)),
      budgetSupervisor: await fileIdentity(budgetSupervisor, repoUri(budgetSupervisor)),
      receiptGenerator: await fileIdentity(receiptGenerator, repoUri(receiptGenerator)),
      receiptFormat: await fileIdentity(receiptFormat, repoUri(receiptFormat)),
    },
    configuration: { budgetProfile: budgetProfileIdentity, ocio: ocioIdentity },
    runtime: {
      blender: { ...(await fileIdentity(blenderBinary)), ...blenderVersion, binaryName: 'Blender' },
      node: { ...(await fileIdentity(process.execPath)), version: process.version, platform: process.platform, architecture: process.arch, binaryName: 'node' },
    },
  };
  const manifestIdentity = await fileIdentity(manifestFile, repoUri(manifestFile));
  const structureCanonicalIdentity = await fileIdentity(structureCanonicalFile, repoUri(structureCanonicalFile));
  const blendIdentity = await fileIdentity(blendFile, repoUri(blendFile));
  const reportIdentity = await fileIdentity(reportFile, repoUri(reportFile));
  return rehashReceipt({
    documentType: 'BFS_COMPILE_RECEIPT', version: '0.1.0', createdAtUtc: new Date().toISOString(), executionIdentity,
    run: {
      budgetReport: { ...reportIdentity, outcome: budgetResult.outcome, metrics: budgetResult.metrics },
      sceneManifest: { ...manifestIdentity, manifestVersion: manifest.manifestVersion, planHash: manifest.execution.planHash, structureHash: manifest.structureHash },
      sceneStructureCanonical: { ...structureCanonicalIdentity, structureHash: manifest.structureHash },
      sceneBlend: blendIdentity,
    },
    claims: { exactArtifactBinding: true, semanticStructureBinding: true, signed: false, remotelyAttested: false },
  });
}
