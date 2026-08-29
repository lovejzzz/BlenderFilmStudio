#!/usr/bin/env node

import { execFile } from 'node:child_process';
import { readFile, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { isDeepStrictEqual, promisify } from 'node:util';
import { compileBuildPlan } from './compile-build-plan.mjs';
import {
  canonicalHash,
  canonicalJson,
  durableMkdir,
  repoUri,
  resolveExistingRepositoryPath,
  resolveFreshRepositoryPath,
  sha256Bytes,
  sha256File,
  validSelfHash,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const CONTRACT_URI = 'specs/cinematic-sequence-consistency.v0.1.json';
const PROTOCOL_URI = 'research/2026-08-29-b60-e1-cinematic-sequence-consistency-protocol.md';
const PREREGISTRATION_COMMIT = '97e3afee8fc44695a4a3277265a051dd1a3cf272';
const EXPECTED_ROOTS = {
  outputRoot: 'experiments/cinematic-sequence-consistency-preflight-v0-1',
  attemptRoot: 'experiments/cinematic-sequence-consistency-attempt-v0-1',
  formalRoot: 'experiments/cinematic-sequence-consistency-v0-1',
};
const TOOL_PATHS = [
  CONTRACT_URI,
  PROTOCOL_URI,
  'scripts/preflight-b60-e1-cinematic-sequence-consistency.mjs',
  'scripts/run-b60-e1-cinematic-sequence-consistency.mjs',
  'scripts/audit-b60-e1-cinematic-sequence-consistency.mjs',
];

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--attempt-root') parsed.attemptRoot = argv[++index];
    else if (token === '--formal-root') parsed.formalRoot = argv[++index];
    else if (token === '--tool-freeze-commit') parsed.toolFreezeCommit = argv[++index];
    else throw new Error(`Unknown or incomplete argument: ${token}`);
  }
  for (const key of ['outputRoot', 'attemptRoot', 'formalRoot', 'toolFreezeCommit']) {
    if (!parsed[key]) throw new Error(`Missing --${key.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.toolFreezeCommit)) throw new Error('Tool-freeze commit must be a full lowercase SHA-1');
  if (!isDeepStrictEqual({ outputRoot: parsed.outputRoot, attemptRoot: parsed.attemptRoot, formalRoot: parsed.formalRoot }, EXPECTED_ROOTS)) {
    throw new Error('B60 official roots must match the preregistered roots exactly');
  }
  return parsed;
}

async function git(args, options = {}) {
  const result = await execFileAsync('/usr/bin/git', args, {
    cwd: repositoryRoot,
    encoding: options.encoding ?? 'utf8',
    timeout: 15000,
    maxBuffer: 16 * 1024 * 1024,
    env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0' },
  });
  return result.stdout;
}

async function verifyToolFreeze(commit) {
  const head = (await git(['rev-parse', 'HEAD'])).trim();
  const origin = (await git(['rev-parse', 'origin/main'])).trim();
  if (head !== commit || origin !== commit) throw new Error('Tool-freeze commit must equal clean pushed HEAD and origin/main');
  await git(['merge-base', '--is-ancestor', PREREGISTRATION_COMMIT, commit]);
  const hashes = {};
  for (const uri of TOOL_PATHS) {
    const path = await resolveExistingRepositoryPath(uri, `B60 frozen path ${uri}`);
    const current = await sha256File(path);
    const frozen = sha256Bytes(await git(['show', `${commit}:${uri}`], { encoding: null }));
    if (current !== frozen) throw new Error(`B60 tool-freeze mismatch: ${uri}`);
    hashes[uri] = current;
  }
  return hashes;
}

function planProjection(wrapper) {
  const plan = wrapper.plan;
  const render = structuredClone(plan.render);
  delete render.outputRoot;
  return {
    compiler: plan.compiler,
    actors: plan.actors,
    assets: plan.assets,
    targets: plan.targets,
    lights: plan.lights,
    world: plan.world,
    render,
    outputSpec: plan.outputSpec,
    security: plan.security,
  };
}

function assertIdentityLocks(wrapper, contract) {
  const actor = wrapper.plan.actors[0];
  const actorSpec = actor?.actorSpec;
  const locks = contract.sharedProjection.identityLocks;
  const topology = actorSpec?.deformation?.meshes?.map(row => row.topologySha256);
  if (actor?.id !== locks.actorId || actor?.assetRef !== locks.assetRef || actor?.identityLock !== true
    || actor?.verifiedActorSpecSha256 !== locks.actorSpecSha256
    || actorSpec?.actor?.assetSha256 !== locks.assetSha256
    || actorSpec?.rig?.restPoseSha256 !== locks.restPoseSha256
    || actorSpec?.deformation?.shapeKeySetSha256 !== locks.shapeKeySetSha256
    || !isDeepStrictEqual(topology, locks.meshTopologySha256)) {
    throw new Error(`Identity lock mismatch for ${wrapper.plan.shot.id}`);
  }
}

async function validateInputs(contract) {
  const frozenInputs = [contract.sequence.actorSpec, contract.sequence.actorAsset, contract.sequence.bodyAction,
    contract.runtime.productionRelease, ...contract.sequence.shots.map(shot => shot.sceneSpec)];
  for (const input of frozenInputs) {
    const path = await resolveExistingRepositoryPath(input.uri, `B60 input ${input.uri}`);
    if (await sha256File(path) !== input.sha256) throw new Error(`B60 input hash mismatch: ${input.uri}`);
  }
  const rows = [];
  for (const shot of contract.sequence.shots) {
    const first = await compileBuildPlan(shot.sceneSpec.uri);
    const second = await compileBuildPlan(shot.sceneSpec.uri);
    if (canonicalJson(first) !== canonicalJson(second)) throw new Error(`Repeated BuildPlan mismatch: ${shot.label}`);
    if (first.planHash !== shot.expectedPlanHash || canonicalHash(first.plan) !== first.planHash) throw new Error(`Expected PlanHash mismatch: ${shot.label}`);
    if (!isDeepStrictEqual(first.plan.cameras, [shot.camera])) throw new Error(`Camera contract mismatch: ${shot.label}`);
    assertIdentityLocks(first, contract);
    rows.push({ shot, wrapper: first, canonicalSha256: sha256Bytes(Buffer.from(canonicalJson(first))) });
  }
  const shared = canonicalJson(planProjection(rows[0].wrapper));
  if (!rows.every(row => canonicalJson(planProjection(row.wrapper)) === shared)) throw new Error('Cross-shot BuildPlan shared projection drift');
  if (new Set(rows.map(row => canonicalJson(row.wrapper.plan.cameras))).size !== rows.length) throw new Error('Preregistered cameras are not pairwise distinct');
  return rows;
}

function casesFor(contract) {
  return contract.sequence.shots.flatMap(shot => ['A', 'B'].map(repetition => ({
    id: `${shot.label}-${repetition}`,
    label: shot.label,
    repetition,
    sceneSpec: shot.sceneSpec.uri,
    expectedPlanHash: shot.expectedPlanHash,
  })));
}

async function runChild(args) {
  try {
    const result = await execFileAsync(process.execPath, args, {
      cwd: repositoryRoot,
      encoding: 'utf8',
      timeout: 120000,
      maxBuffer: 4 * 1024 * 1024,
      env: { PATH: '/opt/homebrew/bin:/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' },
    });
    return { exitCode: 0, stdout: result.stdout, stderr: result.stderr };
  } catch (error) {
    return { exitCode: error.code ?? 1, stdout: error.stdout ?? '', stderr: error.stderr ?? error.message };
  }
}

async function runProductionPreflights(parsed, contract) {
  const rows = [];
  for (const item of casesFor(contract)) {
    const preflightRoot = `${parsed.outputRoot}/cases/${item.id}`;
    const outputRoot = `${parsed.formalRoot}/runs/${item.id}`;
    const child = await runChild([
      'scripts/preflight-production-blender-compile.mjs',
      '--scene-spec', item.sceneSpec,
      '--preflight-root', preflightRoot,
      '--output-root', outputRoot,
      '--release-commit', parsed.toolFreezeCommit,
    ]);
    const receiptPath = resolve(repositoryRoot, preflightRoot, 'preflight.json');
    let receipt = null;
    try { receipt = JSON.parse(await readFile(receiptPath, 'utf8')); } catch { /* reported below */ }
    if (child.exitCode !== 0 || !receipt || !validSelfHash(receipt, 'preflightHash') || receipt.status !== 'ACCEPTED'
      || receipt.buildPlan?.planHash !== item.expectedPlanHash || receipt.operations?.blenderProcesses !== 0) {
      throw new Error(`Production preflight failed for ${item.id}: ${child.stderr || child.stdout}`);
    }
    rows.push({
      ...item,
      preflightRoot,
      outputRoot,
      receipt: { uri: repoUri(receiptPath), sha256: await sha256File(receiptPath), preflightHash: receipt.preflightHash },
      child: { exitCode: child.exitCode, stdoutSha256: sha256Bytes(Buffer.from(child.stdout)), stderrSha256: sha256Bytes(Buffer.from(child.stderr)) },
    });
  }
  return rows;
}

export async function runB60Preflight(argv) {
  const parsed = parseArguments(argv);
  const outputPath = await resolveFreshRepositoryPath(parsed.outputRoot, 'B60 preflight root');
  await resolveFreshRepositoryPath(parsed.attemptRoot, 'B60 attempt root');
  await resolveFreshRepositoryPath(parsed.formalRoot, 'B60 formal root');
  const contractPath = await resolveExistingRepositoryPath(CONTRACT_URI, 'B60 contract');
  const contract = JSON.parse(await readFile(contractPath, 'utf8'));
  if (contract.schemaVersion !== 'bfs.cinematicSequenceConsistency.v0.1' || contract.status !== 'PREREGISTERED'
    || !isDeepStrictEqual(contract.roots, { preflight: parsed.outputRoot, attempt: parsed.attemptRoot, formal: parsed.formalRoot })) {
    throw new Error('B60 contract schema, status or root binding mismatch');
  }
  const toolHashes = await verifyToolFreeze(parsed.toolFreezeCommit);
  const plans = await validateInputs(contract);
  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const availableBytes = filesystem.bavail * filesystem.bsize;
  if (availableBytes < BigInt(contract.resourceCeilings.minimumDiskReserveBytes)) throw new Error('B60 disk reserve is below the preregistered minimum');

  await durableMkdir(outputPath);
  await durableMkdir(resolve(outputPath, 'cases'));
  const productionPreflights = await runProductionPreflights(parsed, contract);
  const checks = [
    ['PREREGISTRATION_COMMIT_ANCESTRY', true],
    ['TOOL_FREEZE_EXACT', Object.keys(toolHashes).length === TOOL_PATHS.length],
    ['INPUT_HASHES_EXACT', true],
    ['BUILD_PLANS_REPEAT_EXACT', plans.length === 3],
    ['SHARED_PLAN_PROJECTION_EXACT', true],
    ['CAMERAS_CONTRACT_EXACT_DISTINCT', true],
    ['PRODUCTION_PREFLIGHTS_ACCEPTED', productionPreflights.length === 6],
    ['ZERO_BLENDER_PREFLIGHT', productionPreflights.every(row => row.receipt.preflightHash)],
    ['DISK_RESERVE_PASS', availableBytes >= BigInt(contract.resourceCeilings.minimumDiskReserveBytes)],
  ].map(([id, pass]) => ({ id, pass }));
  if (!checks.every(check => check.pass)) throw new Error('B60 outer preflight check failed');
  const record = await writeDurableHashed(resolve(outputPath, 'preflight.json'), {
    schemaVersion: 'bfs.cinematicSequenceConsistencyPreflight.v0.1',
    status: 'ACCEPTED',
    reason: null,
    preregistrationCommit: PREREGISTRATION_COMMIT,
    toolFreezeCommit: parsed.toolFreezeCommit,
    contract: { uri: CONTRACT_URI, sha256: await sha256File(contractPath) },
    roots: contract.roots,
    plans: plans.map(row => ({ label: row.shot.label, sceneSpec: row.shot.sceneSpec, planHash: row.wrapper.planHash, canonicalSha256: row.canonicalSha256 })),
    productionPreflights,
    checks,
    disk: { availableBytes: availableBytes.toString(), minimumReserveBytes: String(contract.resourceCeilings.minimumDiskReserveBytes) },
    toolHashes,
    operations: { nodeChildren: 6, blenderProcesses: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  }, 'preflightHash');
  process.stdout.write(`BFS_B60_PREFLIGHT ACCEPTED ${checks.length}/${checks.length} ${record.preflightHash}\n`);
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runB60Preflight(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_B60_PREFLIGHT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
