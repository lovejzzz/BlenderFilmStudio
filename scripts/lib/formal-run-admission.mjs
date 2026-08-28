import { createHash } from 'node:crypto';
import { lstat, readFile, realpath } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { spawn } from 'node:child_process';

export class AdmissionError extends Error {
  constructor(reason, message) {
    super(message);
    this.name = 'AdmissionError';
    this.reason = reason;
  }
}

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

export async function sha256File(path) {
  return sha256Bytes(await readFile(path));
}

export function canonicalHash(value) {
  return sha256Bytes(Buffer.from(canonicalJson(value)));
}

function below(root, candidate) {
  const pathFromRoot = relative(root, candidate);
  return pathFromRoot !== '' && pathFromRoot !== '..' && !pathFromRoot.startsWith(`..${sep}`) && !isAbsolute(pathFromRoot);
}

async function pathState(path) {
  try { return await lstat(path); } catch (error) {
    if (error?.code === 'ENOENT') return null;
    throw error;
  }
}

export async function runGit(args, cwd, observer = null) {
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/git', args, {
    cwd,
    env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', GIT_CONFIG_NOSYSTEM: '1', GIT_TERMINAL_PROMPT: '0', GIT_ALLOW_PROTOCOL: 'file' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const stdout = [];
  const stderr = [];
  child.stdout.on('data', chunk => stdout.push(chunk));
  child.stderr.on('data', chunk => stderr.push(chunk));
  const exitCode = await new Promise((resolvePromise, reject) => {
    child.on('error', reject);
    child.on('close', resolvePromise);
  });
  const result = {
    args,
    pid: child.pid,
    exitCode,
    stdout: Buffer.concat(stdout).toString('utf8'),
    stderr: Buffer.concat(stderr).toString('utf8'),
    elapsedNanoseconds: Number(process.hrtime.bigint() - started),
  };
  if (observer) observer(result);
  return result;
}

async function gitRequired(args, cwd, observer, reason, message) {
  const result = await runGit(args, cwd, observer);
  if (result.exitCode !== 0) throw new AdmissionError(reason, `${message}: ${result.stderr.trim()}`);
  return result.stdout.trim();
}

async function repositoryContext(repositoryRoot) {
  const lexical = resolve(repositoryRoot);
  const actual = await realpath(lexical);
  if (lexical !== actual) throw new AdmissionError('REPOSITORY_SYMLINK_ALIAS', 'Repository root must not traverse symbolic links');
  return { lexical, actual };
}

async function resolveEvidencePath(repository, spelling) {
  const candidate = resolve(repository.lexical, spelling);
  if (!below(repository.lexical, candidate)) throw new AdmissionError('EVIDENCE_OUTSIDE_REPOSITORY', 'Evidence must resolve strictly below repository root');
  const state = await pathState(candidate);
  if (!state) throw new AdmissionError('EVIDENCE_MISSING', 'Evidence path is missing');
  if (state.isSymbolicLink()) throw new AdmissionError('EVIDENCE_SYMLINK_ALIAS', 'Evidence path is a symbolic link');
  const actual = await realpath(candidate);
  if (candidate !== actual) throw new AdmissionError('EVIDENCE_SYMLINK_ALIAS', 'Evidence path traverses a symbolic link');
  if (!below(repository.actual, actual)) throw new AdmissionError('EVIDENCE_OUTSIDE_REPOSITORY', 'Evidence realpath escapes repository');
  if (!state.isDirectory()) throw new AdmissionError('EVIDENCE_NOT_DIRECTORY', 'Evidence path is not a directory');
  return { absolute: candidate, repositoryRelative: relative(repository.lexical, candidate).split(sep).join('/') };
}

async function resolveOutputPath(repository, spelling) {
  const candidate = resolve(repository.lexical, spelling);
  if (!below(repository.lexical, candidate)) throw new AdmissionError('OUTPUT_OUTSIDE_REPOSITORY', 'Output must resolve strictly below repository root');
  const targetState = await pathState(candidate);
  if (targetState?.isSymbolicLink()) throw new AdmissionError('OUTPUT_SYMLINK_ALIAS', 'Output target is a symbolic link');
  if (targetState) throw new AdmissionError('OUTPUT_EXISTS', 'Output target already exists');
  let ancestor = dirname(candidate);
  let ancestorState = await pathState(ancestor);
  while (!ancestorState) {
    const parent = dirname(ancestor);
    if (parent === ancestor) throw new AdmissionError('OUTPUT_OUTSIDE_REPOSITORY', 'Output has no repository-contained existing ancestor');
    ancestor = parent;
    ancestorState = await pathState(ancestor);
  }
  if (ancestorState.isSymbolicLink()) throw new AdmissionError('OUTPUT_SYMLINK_ALIAS', 'Output ancestor is a symbolic link');
  const actualAncestor = await realpath(ancestor);
  if (ancestor !== actualAncestor) throw new AdmissionError('OUTPUT_SYMLINK_ALIAS', 'Output ancestor traverses a symbolic link');
  if (!below(repository.actual, actualAncestor)) throw new AdmissionError('OUTPUT_OUTSIDE_REPOSITORY', 'Output ancestor realpath escapes repository');
  return {
    absolute: candidate,
    repositoryRelative: relative(repository.lexical, candidate).split(sep).join('/'),
    parentRepositoryRelative: relative(repository.lexical, dirname(candidate)).split(sep).join('/'),
  };
}

function verifiedSelfHash(record, field) {
  const body = structuredClone(record);
  delete body[field];
  return record[field] === canonicalHash(body);
}

export async function admitFormalRun({ repositoryRoot, evidenceInput, formalOutput, originRef = 'origin/main', gitObserver = null }) {
  const repository = await repositoryContext(repositoryRoot);
  const evidence = await resolveEvidencePath(repository, evidenceInput);
  const tracked = await runGit(['ls-files', '-z', '--', evidence.repositoryRelative], repository.lexical, gitObserver);
  const dirty = await runGit(['status', '--porcelain=v1', '--untracked-files=all', '--', evidence.repositoryRelative], repository.lexical, gitObserver);
  if (tracked.exitCode !== 0 || tracked.stdout.length === 0 || dirty.exitCode !== 0 || dirty.stdout.length !== 0) {
    throw new AdmissionError('EVIDENCE_NOT_TRACKED_CLEAN', 'Evidence must be tracked and clean at HEAD');
  }
  const evidenceCommit = await gitRequired(['log', '-1', '--format=%H', '--', evidence.repositoryRelative], repository.lexical, gitObserver, 'EVIDENCE_NOT_TRACKED_CLEAN', 'Evidence has no affecting commit');
  const origin = await runGit(['rev-parse', '--verify', originRef], repository.lexical, gitObserver);
  if (origin.exitCode !== 0) throw new AdmissionError('ORIGIN_BRANCH_MISSING', `Origin ref is missing: ${originRef}`);
  const ancestor = await runGit(['merge-base', '--is-ancestor', evidenceCommit, originRef], repository.lexical, gitObserver);
  if (ancestor.exitCode !== 0) throw new AdmissionError('EVIDENCE_COMMIT_NOT_PUSHED', 'Evidence commit is not an ancestor of configured origin ref');

  const preflightPath = resolve(evidence.absolute, 'preflight.json');
  const preflightState = await pathState(preflightPath);
  if (!preflightState?.isFile()) throw new AdmissionError('PREFLIGHT_SELF_HASH', 'Preflight record is missing');
  const preflight = JSON.parse(await readFile(preflightPath, 'utf8'));
  if (!verifiedSelfHash(preflight, 'preflightHash')) throw new AdmissionError('PREFLIGHT_SELF_HASH', 'Preflight canonical self-hash mismatch');
  if (preflight.status !== 'ACCEPTED') throw new AdmissionError('PREFLIGHT_STATUS', 'Preflight status is not ACCEPTED');
  const observedToolHashes = {};
  for (const [uri, expected] of Object.entries(preflight.toolHashes ?? {}).sort(([left], [right]) => left.localeCompare(right))) {
    const path = resolve(repository.lexical, uri);
    if (!below(repository.lexical, path) || await pathState(path) === null) throw new AdmissionError('TOOL_HASH', `Tool is missing or outside repository: ${uri}`);
    const observed = await sha256File(path);
    observedToolHashes[uri] = observed;
    if (observed !== expected) throw new AdmissionError('TOOL_HASH', `Tool hash mismatch: ${uri}`);
  }
  if (Object.keys(observedToolHashes).length === 0) throw new AdmissionError('TOOL_HASH', 'Preflight declares no tool hashes');
  const output = await resolveOutputPath(repository, formalOutput);
  const preflightFileSha256 = await sha256File(preflightPath);
  const evidenceIdentityBody = {
    repositoryRelative: evidence.repositoryRelative,
    evidenceCommit,
    originRef,
    originCommit: origin.stdout.trim(),
    preflight: { uri: `${evidence.repositoryRelative}/preflight.json`, sha256: preflightFileSha256, preflightHash: preflight.preflightHash },
    toolHashes: observedToolHashes,
  };
  return {
    status: 'ACCEPTED',
    evidence: { ...evidenceIdentityBody, identityHash: canonicalHash(evidenceIdentityBody) },
    output: {
      repositoryRelative: output.repositoryRelative,
      parentRepositoryRelative: output.parentRepositoryRelative,
      fresh: true,
      absolute: output.absolute,
    },
  };
}
