#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { readFile, realpath, statfs } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { compileBuildPlan } from './compile-build-plan.mjs';
import { evaluateDiskSpace, gibToBytes } from './lib/disk-space-guard.mjs';
import { runGit } from './lib/formal-run-admission.mjs';
import {
  canonicalJson,
  durableMkdir,
  repoUri,
  resolveExistingRepositoryPath,
  resolveFreshRepositoryPath,
  sha256File,
  writeDurableHashed,
} from './lib/production-compile-receipt.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';

const RELEASE_MANIFEST_URI = 'specs/production-compiler-entry.v0.2.json';

class PreflightError extends Error {
  constructor(reason, message) {
    super(message);
    this.name = 'PreflightError';
    this.reason = reason;
  }
}

function parseArguments(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--scene-spec') parsed.sceneSpec = argv[++index];
    else if (token === '--preflight-root') parsed.preflightRoot = argv[++index];
    else if (token === '--output-root') parsed.outputRoot = argv[++index];
    else if (token === '--release-commit') parsed.releaseCommit = argv[++index];
    else throw new PreflightError('CLI_ARGUMENT', `Unknown or incomplete argument: ${token}`);
  }
  for (const required of ['sceneSpec', 'preflightRoot', 'outputRoot', 'releaseCommit']) {
    if (!parsed[required]) throw new PreflightError('CLI_ARGUMENT', `Missing --${required.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)}`);
  }
  if (!/^[0-9a-f]{40}$/.test(parsed.releaseCommit)) throw new PreflightError('RELEASE_COMMIT', 'Release commit must be a full lowercase SHA-1');
  return parsed;
}

async function gitRequired(args, gitChildren, reason, message) {
  const result = await runGit(args, repositoryRoot, row => gitChildren.push(row));
  if (result.exitCode !== 0) throw new PreflightError(reason, `${message}: ${result.stderr.trim()}`);
  return result.stdout.trim();
}

async function requireTrackedClean(uri, gitChildren) {
  await gitRequired(['ls-files', '--error-unmatch', '--', uri], gitChildren, 'TRACKED_CLEAN', `Untracked path ${uri}`);
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', uri], repositoryRoot, row => gitChildren.push(row));
  if (dirty.exitCode !== 0 || dirty.stdout.length !== 0) throw new PreflightError('TRACKED_CLEAN', `Dirty path ${uri}`);
}

async function requireCommitPushed(commit, gitChildren) {
  const resolved = await gitRequired(['rev-parse', '--verify', `${commit}^{commit}`], gitChildren, 'RELEASE_COMMIT', 'Release commit is missing');
  if (resolved !== commit) throw new PreflightError('RELEASE_COMMIT', 'Release commit did not resolve exactly');
  await gitRequired(['rev-parse', '--verify', 'origin/main'], gitChildren, 'ORIGIN_BRANCH', 'origin/main is missing');
  const ancestor = await runGit(['merge-base', '--is-ancestor', commit, 'origin/main'], repositoryRoot, row => gitChildren.push(row));
  if (ancestor.exitCode !== 0) throw new PreflightError('RELEASE_NOT_PUSHED', 'Release commit is not an ancestor of origin/main');
}

async function requireBlobAtCommit(uri, expectedSha256, releaseCommit, gitChildren) {
  const shown = await runGit(['show', `${releaseCommit}:${uri}`], repositoryRoot, row => gitChildren.push(row));
  if (shown.exitCode !== 0) throw new PreflightError('RELEASE_BLOB', `Release commit does not contain ${uri}`);
  const currentPath = await resolveExistingRepositoryPath(uri, `Release path ${uri}`);
  const currentSha256 = await sha256File(currentPath);
  const commitSha256 = createHash('sha256').update(Buffer.from(shown.stdout)).digest('hex');
  if (currentSha256 !== expectedSha256 || commitSha256 !== expectedSha256) {
    throw new PreflightError('RELEASE_BLOB', `Release hash mismatch for ${uri}`);
  }
  return currentSha256;
}

async function sceneCommitIdentity(sceneUri, gitChildren) {
  const commit = await gitRequired(['log', '-1', '--format=%H', '--', sceneUri], gitChildren, 'SCENE_COMMIT', 'SceneSpec has no affecting commit');
  const ancestor = await runGit(['merge-base', '--is-ancestor', commit, 'origin/main'], repositoryRoot, row => gitChildren.push(row));
  if (ancestor.exitCode !== 0) throw new PreflightError('SCENE_NOT_PUSHED', 'SceneSpec affecting commit is not pushed to origin/main');
  return commit;
}

async function readReleaseManifest(releasePath) {
  const release = JSON.parse(await readFile(releasePath, 'utf8'));
  if (release.schemaVersion !== 'bfs.productionCompilerEntry.v0.2' || release.status !== 'RELEASE_CANDIDATE') {
    throw new PreflightError('RELEASE_MANIFEST', 'Production release manifest schema or status mismatch');
  }
  if (release.originRef !== 'origin/main' || release.preregistrationCommit !== 'c9e0b9e25c41b751fb456cf115e29e63996dbea4') {
    throw new PreflightError('RELEASE_MANIFEST', 'Production release manifest provenance mismatch');
  }
  return release;
}

async function evaluate(parsed) {
  const gitChildren = [];
  const releasePath = await resolveExistingRepositoryPath(RELEASE_MANIFEST_URI, 'Production release manifest');
  const scenePath = await resolveExistingRepositoryPath(parsed.sceneSpec, 'Production SceneSpec');
  const outputPath = await resolveFreshRepositoryPath(parsed.outputRoot, 'Production output root');
  const release = await readReleaseManifest(releasePath);
  if (repoUri(scenePath) !== parsed.sceneSpec || repoUri(outputPath) !== parsed.outputRoot) throw new PreflightError('PATH_SPELLING', 'Canonical repository-relative spelling mismatch');
  await requireCommitPushed(parsed.releaseCommit, gitChildren);

  const frozenHashes = { [RELEASE_MANIFEST_URI]: await sha256File(releasePath) };
  const trustedUris = [RELEASE_MANIFEST_URI, 'package.json', ...Object.keys(release.frozenFiles)].sort();
  for (const uri of trustedUris) await requireTrackedClean(uri, gitChildren);
  await requireTrackedClean(parsed.sceneSpec, gitChildren);
  for (const [uri, expectedSha256] of Object.entries(release.frozenFiles).sort(([left], [right]) => left.localeCompare(right))) {
    frozenHashes[uri] = await requireBlobAtCommit(uri, expectedSha256, parsed.releaseCommit, gitChildren);
  }
  const releaseCommitManifestSha = await requireBlobAtCommit(RELEASE_MANIFEST_URI, frozenHashes[RELEASE_MANIFEST_URI], parsed.releaseCommit, gitChildren);
  if (releaseCommitManifestSha !== frozenHashes[RELEASE_MANIFEST_URI]) throw new PreflightError('RELEASE_MANIFEST', 'Release manifest commit binding mismatch');
  const sceneSha256 = await sha256File(scenePath);
  const sceneCommit = await sceneCommitIdentity(parsed.sceneSpec, gitChildren);

  const first = await compileBuildPlan(parsed.sceneSpec);
  const second = await compileBuildPlan(parsed.sceneSpec);
  const buildPlanCanonicalExact = canonicalJson(first) === canonicalJson(second);
  if (!buildPlanCanonicalExact) throw new PreflightError('BUILD_PLAN_IDENTITY', 'Repeated in-memory BuildPlan bytes differ');

  const filesystem = await statfs(repositoryRoot, { bigint: true });
  const observedAvailableBytes = filesystem.bavail * filesystem.bsize;
  const ceilingText = process.env.BFS_PRODUCTION_PREFLIGHT_AVAILABLE_BYTES_CEILING;
  const ceilingBytes = ceilingText === undefined ? null : BigInt(ceilingText);
  if (ceilingBytes !== null && (ceilingBytes < 0n || ceilingBytes > observedAvailableBytes)) {
    throw new PreflightError('DISK_TEST_CEILING', 'Available-byte ceiling may only lower the real observation');
  }
  const effectiveAvailableBytes = ceilingBytes === null ? observedAvailableBytes : ceilingBytes;
  const disk = evaluateDiskSpace({
    availableBytes: effectiveAvailableBytes,
    capacityBytes: filesystem.blocks * filesystem.bsize,
    reserveBytes: gibToBytes(100),
    projectedWriteBytes: gibToBytes(0.5),
    target: repositoryRoot,
  });
  if (disk.status !== 'PASS') throw new PreflightError('DISK_ADMISSION', 'Projected production compile violates the frozen disk reserve');
  const nodePath = await realpath(process.execPath);
  const blenderPath = '/Applications/Blender.app/Contents/MacOS/Blender';
  const runtime = {
    node: { executable: nodePath, version: process.version, sha256: await sha256File(nodePath) },
    blender: { executable: blenderPath, sha256: await sha256File(blenderPath), buildHash: release.runtime.blender.buildHash, processStarted: false },
  };
  if (runtime.node.sha256 !== release.runtime.node.sha256 || runtime.node.version !== release.runtime.node.version
    || runtime.blender.sha256 !== release.runtime.blender.sha256) throw new PreflightError('RUNTIME_IDENTITY', 'Runtime identity mismatch');

  return {
    status: 'ACCEPTED',
    release: { uri: RELEASE_MANIFEST_URI, sha256: frozenHashes[RELEASE_MANIFEST_URI], releaseId: release.releaseId, releaseCommit: parsed.releaseCommit },
    invocation: { sceneSpec: parsed.sceneSpec, preflightRoot: parsed.preflightRoot, outputRoot: parsed.outputRoot },
    source: { uri: parsed.sceneSpec, sha256: sceneSha256, affectingCommit: sceneCommit },
    output: { repositoryRelative: parsed.outputRoot, absolutePathRecorded: false, absent: true },
    buildPlan: { planHash: first.planHash, planVersion: first.planVersion, canonicalPairExact: true, sourceSceneCanonicalSha256: first.plan.source.canonicalSha256 },
    runtime,
    disk: { ...disk, filesystemAvailableBytesObserved: observedAvailableBytes.toString(), effectiveAvailableBytes: effectiveAvailableBytes.toString(), testCeilingApplied: ceilingBytes !== null },
    toolHashes: Object.fromEntries(Object.entries(frozenHashes).sort(([left], [right]) => left.localeCompare(right))),
    git: { originRef: 'origin/main', gitChildren },
    operations: { blenderProcesses: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
  };
}

export async function runProductionPreflight(argv) {
  const parsed = parseArguments(argv);
  const rootSpellings = [parsed.preflightRoot, parsed.outputRoot];
  if (rootSpellings.some((left, index) => rootSpellings.some((right, other) => index !== other && (left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`))))) {
    throw new Error('Production preflight and output roots must be disjoint');
  }
  const preflightPath = await resolveFreshRepositoryPath(parsed.preflightRoot, 'Production preflight root');
  let body;
  try {
    body = { schemaVersion: 'bfs.productionCompilePreflight.v0.1', ...(await evaluate(parsed)), reason: null };
  } catch (error) {
    body = {
      schemaVersion: 'bfs.productionCompilePreflight.v0.1',
      status: 'REJECTED',
      reason: error instanceof PreflightError ? error.reason : 'PREFLIGHT_EXCEPTION',
      message: error?.message ?? String(error),
      invocation: { sceneSpec: parsed.sceneSpec, preflightRoot: parsed.preflightRoot, outputRoot: parsed.outputRoot, releaseCommit: parsed.releaseCommit },
      toolHashes: {},
      operations: { blenderProcesses: 0, renderCalls: 0, modelCalls: 0, networkCalls: 0, dockerProcesses: 0 },
    };
  }
  await durableMkdir(preflightPath);
  const record = await writeDurableHashed(resolve(preflightPath, 'preflight.json'), body, 'preflightHash');
  process.stdout.write(`BFS_PRODUCTION_PREFLIGHT ${record.status} ${record.reason ?? record.buildPlan?.planHash ?? 'OK'}\n`);
  if (record.status !== 'ACCEPTED') process.exitCode = 1;
  return record;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runProductionPreflight(process.argv.slice(2)).catch(error => {
    process.stderr.write(`BFS_PRODUCTION_PREFLIGHT_ERROR ${error.message}\n`);
    process.exitCode = 1;
  });
}
