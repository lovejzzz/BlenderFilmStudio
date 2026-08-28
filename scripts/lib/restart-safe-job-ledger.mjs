import { createHash, randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import {
  lstat,
  mkdir,
  open,
  readFile,
  readdir,
  realpath,
  rename,
  rmdir,
  unlink,
} from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const EVENT_FILE_PATTERN = /^(?<sequence>[0-9]{6})-(?<eventType>[A-Z][A-Z0-9_]*)\.json$/;
const HASH_PATTERN = /^[0-9a-f]{64}$/;

export class RestartSafeStateError extends Error {
  constructor(reason, message, context = {}) {
    super(message);
    this.name = 'RestartSafeStateError';
    this.reason = reason;
    this.context = context;
  }
}

function assertJsonValue(value, path = '$') {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || Object.is(value, -0)) {
      throw new RestartSafeStateError('NON_CANONICAL_JSON', `Non-canonical number at ${path}`);
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertJsonValue(item, `${path}[${index}]`));
    return;
  }
  if (typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      if (child === undefined) throw new RestartSafeStateError('NON_CANONICAL_JSON', `Undefined value at ${path}.${key}`);
      assertJsonValue(child, `${path}.${key}`);
    }
    return;
  }
  throw new RestartSafeStateError('NON_CANONICAL_JSON', `Unsupported JSON value at ${path}`);
}

export function sortJson(value) {
  assertJsonValue(value);
  if (Array.isArray(value)) return value.map(sortJson);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, sortJson(value[key])]));
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(sortJson(value));
}

export function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

export async function sha256File(path) {
  return sha256Bytes(await readFile(path));
}

export function recordSelfHash(record, field) {
  const body = structuredClone(record);
  delete body[field];
  return sha256Bytes(Buffer.from(canonicalJson(body)));
}

export function validSelfHash(record, field) {
  return Boolean(record && HASH_PATTERN.test(record[field] ?? '') && record[field] === recordSelfHash(record, field));
}

async function fsyncDirectory(path) {
  const handle = await open(path, 'r');
  try {
    await handle.sync();
  } finally {
    await handle.close();
  }
}

export async function durableMkdir(path) {
  const parent = dirname(path);
  await mkdir(path, { recursive: true });
  await fsyncDirectory(path);
  if (parent !== path) await fsyncDirectory(parent);
}

export async function writeExclusiveDurableJson(path, value) {
  assertJsonValue(value);
  await durableMkdir(dirname(path));
  const bytes = Buffer.from(`${JSON.stringify(value, null, 2)}\n`);
  let handle;
  try {
    handle = await open(path, 'wx', 0o600);
    await handle.writeFile(bytes);
    await handle.sync();
  } catch (error) {
    if (error?.code === 'EEXIST') {
      throw new RestartSafeStateError('AUTHORITATIVE_PATH_EXISTS', `Refusing to overwrite ${path}`);
    }
    throw error;
  } finally {
    if (handle) await handle.close();
  }
  await fsyncDirectory(dirname(path));
  return { bytes: bytes.length, sha256: sha256Bytes(bytes) };
}

export async function writeExclusiveDurableHashed(path, body, hashField) {
  if (Object.hasOwn(body, hashField)) {
    throw new RestartSafeStateError('SELF_HASH_FIELD_PRESENT', `${hashField} must not be supplied by the caller`);
  }
  const record = { ...structuredClone(body), [hashField]: sha256Bytes(Buffer.from(canonicalJson(body))) };
  const file = await writeExclusiveDurableJson(path, record);
  return { record, file };
}

export async function readJson(path) {
  let bytes;
  try {
    bytes = await readFile(path);
  } catch (error) {
    if (error?.code === 'ENOENT') throw new RestartSafeStateError('REQUIRED_FILE_MISSING', `Missing required file ${path}`);
    throw error;
  }
  let value;
  try {
    value = JSON.parse(bytes.toString('utf8'));
  } catch (error) {
    throw new RestartSafeStateError('INVALID_JSON', `Invalid JSON in ${path}: ${error.message}`);
  }
  assertJsonValue(value);
  return { value, bytes, sha256: sha256Bytes(bytes) };
}

export async function resolveContainedPath(root, spelling, { mustExist = true, allowRoot = false } = {}) {
  if (typeof spelling !== 'string' || spelling.length === 0 || isAbsolute(spelling)) {
    throw new RestartSafeStateError('PATH_NOT_RELATIVE', 'Path spelling must be non-empty and repository-relative');
  }
  const lexicalRoot = resolve(root);
  const lexical = resolve(lexicalRoot, spelling);
  const fromRoot = relative(lexicalRoot, lexical);
  if ((!allowRoot && fromRoot === '') || fromRoot === '..' || fromRoot.startsWith(`..${sep}`) || isAbsolute(fromRoot)) {
    throw new RestartSafeStateError('PATH_OUTSIDE_ROOT', `Path escapes root: ${spelling}`);
  }
  const state = await lstat(lexical).catch(error => {
    if (error?.code === 'ENOENT') return null;
    throw error;
  });
  if (mustExist && !state) throw new RestartSafeStateError('REQUIRED_FILE_MISSING', `Missing path ${spelling}`);
  if (state?.isSymbolicLink()) throw new RestartSafeStateError('SYMLINK_ALIAS', `Symbolic links are forbidden: ${spelling}`);
  if (state) {
    const actualRoot = await realpath(lexicalRoot);
    const actual = await realpath(lexical);
    const actualFromRoot = relative(actualRoot, actual);
    if ((!allowRoot && actualFromRoot === '') || actualFromRoot === '..' || actualFromRoot.startsWith(`..${sep}`) || isAbsolute(actualFromRoot)) {
      throw new RestartSafeStateError('PATH_OUTSIDE_ROOT', `Real path escapes root: ${spelling}`);
    }
    const expectedActual = resolve(actualRoot, fromRoot);
    if (actual !== expectedActual) throw new RestartSafeStateError('SYMLINK_ALIAS', `Path traverses a symbolic link below the trusted root: ${spelling}`);
  }
  return lexical;
}

export async function readManifest(jobRoot) {
  const path = resolve(jobRoot, 'job-manifest.json');
  const { value, bytes, sha256 } = await readJson(path);
  if (value.schemaVersion !== 'bfs.restartSafeProductionJobManifest.v0.1') {
    throw new RestartSafeStateError('MANIFEST_SCHEMA', 'Unexpected job manifest schema');
  }
  if (!validSelfHash(value, 'manifestHash')) {
    throw new RestartSafeStateError('MANIFEST_SELF_HASH', 'Job manifest self-hash mismatch');
  }
  return { path, manifest: value, bytes, sha256 };
}

export async function createManifest(jobRoot, body) {
  await durableMkdir(jobRoot);
  const path = resolve(jobRoot, 'job-manifest.json');
  const { record, file } = await writeExclusiveDurableHashed(path, {
    schemaVersion: 'bfs.restartSafeProductionJobManifest.v0.1',
    ...structuredClone(body),
  }, 'manifestHash');
  return { path, manifest: record, file };
}

function eventFileName(sequence, eventType) {
  if (!Number.isSafeInteger(sequence) || sequence < 1 || sequence > 999999) {
    throw new RestartSafeStateError('LEDGER_SEQUENCE', `Invalid event sequence ${sequence}`);
  }
  if (!/^[A-Z][A-Z0-9_]*$/.test(eventType)) {
    throw new RestartSafeStateError('LEDGER_EVENT_TYPE', `Invalid event type ${eventType}`);
  }
  return `${String(sequence).padStart(6, '0')}-${eventType}.json`;
}

export async function readLedger(jobRoot, expectedJobId = null) {
  const eventsRoot = resolve(jobRoot, 'events');
  const entries = await readdir(eventsRoot, { withFileTypes: true }).catch(error => {
    if (error?.code === 'ENOENT') return [];
    throw error;
  });
  const parsed = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile()) throw new RestartSafeStateError('LEDGER_ROSTER', `Ledger contains a non-file entry: ${entry.name}`);
    const match = EVENT_FILE_PATTERN.exec(entry.name);
    if (!match) throw new RestartSafeStateError('LEDGER_ROSTER', `Unexpected ledger file: ${entry.name}`);
    parsed.push({ entry, sequence: Number.parseInt(match.groups.sequence, 10), eventType: match.groups.eventType });
  }
  let previousEventHash = null;
  const events = [];
  for (let index = 0; index < parsed.length; index += 1) {
    const row = parsed[index];
    const expectedSequence = index + 1;
    if (row.sequence !== expectedSequence) {
      throw new RestartSafeStateError('LEDGER_SEQUENCE', `Expected ledger sequence ${expectedSequence}, found ${row.sequence}`);
    }
    if (row.entry.name !== eventFileName(expectedSequence, row.eventType)) {
      throw new RestartSafeStateError('LEDGER_FILE_NAME', `Non-canonical ledger file name ${row.entry.name}`);
    }
    const path = resolve(eventsRoot, row.entry.name);
    const { value, bytes, sha256 } = await readJson(path);
    if (value.schemaVersion !== 'bfs.restartSafeProductionJobEvent.v0.1') {
      throw new RestartSafeStateError('LEDGER_SCHEMA', `Unexpected event schema at sequence ${expectedSequence}`);
    }
    if (value.sequence !== expectedSequence || value.eventType !== row.eventType) {
      throw new RestartSafeStateError('LEDGER_FILE_BINDING', `Event body does not match file name at sequence ${expectedSequence}`);
    }
    if (expectedJobId !== null && value.jobId !== expectedJobId) {
      throw new RestartSafeStateError('LEDGER_JOB_ID', `Event job ID mismatch at sequence ${expectedSequence}`);
    }
    if (value.previousEventHash !== previousEventHash) {
      throw new RestartSafeStateError('LEDGER_PREVIOUS_HASH', `Event chain mismatch at sequence ${expectedSequence}`);
    }
    if (!validSelfHash(value, 'eventHash')) {
      throw new RestartSafeStateError('LEDGER_EVENT_HASH', `Event self-hash mismatch at sequence ${expectedSequence}`);
    }
    previousEventHash = value.eventHash;
    events.push({ path, name: row.entry.name, event: value, bytes, sha256 });
  }
  return { eventsRoot, events, headEventHash: previousEventHash };
}

export async function appendLedgerEvent(jobRoot, body) {
  const { manifest } = await readManifest(jobRoot);
  const ledger = await readLedger(jobRoot, manifest.jobId);
  const sequence = ledger.events.length + 1;
  const eventBody = {
    schemaVersion: 'bfs.restartSafeProductionJobEvent.v0.1',
    jobId: manifest.jobId,
    sequence,
    eventType: body.eventType,
    stageId: body.stageId ?? null,
    attemptId: body.attemptId ?? null,
    previousEventHash: ledger.headEventHash,
    payload: structuredClone(body.payload ?? {}),
  };
  const path = resolve(jobRoot, 'events', eventFileName(sequence, body.eventType));
  const { record, file } = await writeExclusiveDurableHashed(path, eventBody, 'eventHash');
  return { path, event: record, file };
}

export async function writeStageReceipt(jobRoot, stageId, attemptId, body) {
  const path = resolve(jobRoot, 'stages', stageId, 'receipt.json');
  const { manifest } = await readManifest(jobRoot);
  const { record, file } = await writeExclusiveDurableHashed(path, {
    schemaVersion: 'bfs.restartSafeProductionStageReceipt.v0.1',
    jobId: manifest.jobId,
    stageId,
    attemptId,
    ...structuredClone(body),
  }, 'receiptHash');
  return { path, receipt: record, file };
}

export async function readStageReceipt(jobRoot, stageId) {
  const path = resolve(jobRoot, 'stages', stageId, 'receipt.json');
  const { value, bytes, sha256 } = await readJson(path);
  if (value.schemaVersion !== 'bfs.restartSafeProductionStageReceipt.v0.1') {
    throw new RestartSafeStateError('STAGE_RECEIPT_SCHEMA', `Unexpected stage receipt schema for ${stageId}`);
  }
  if (value.stageId !== stageId || !validSelfHash(value, 'receiptHash')) {
    throw new RestartSafeStateError('STAGE_RECEIPT_SELF_HASH', `Invalid stage receipt for ${stageId}`);
  }
  return { path, receipt: value, bytes, sha256 };
}

export async function verifyStageCompletionReference(jobRoot, event) {
  if (event.eventType !== 'STAGE_COMPLETED') {
    throw new RestartSafeStateError('STAGE_EVENT_TYPE', 'Completion verification requires STAGE_COMPLETED');
  }
  const reference = event.payload?.receipt;
  if (!reference || typeof reference.uri !== 'string' || !HASH_PATTERN.test(reference.sha256 ?? '') || !HASH_PATTERN.test(reference.receiptHash ?? '')) {
    throw new RestartSafeStateError('STAGE_RECEIPT_REFERENCE', `Malformed receipt reference for ${event.stageId}`);
  }
  const path = await resolveContainedPath(jobRoot, reference.uri);
  const { value, sha256 } = await readJson(path);
  if (sha256 !== reference.sha256 || value.receiptHash !== reference.receiptHash || !validSelfHash(value, 'receiptHash')) {
    throw new RestartSafeStateError('STAGE_RECEIPT_REFERENCE', `Receipt reference mismatch for ${event.stageId}`);
  }
  if (value.jobId !== event.jobId || value.stageId !== event.stageId || value.attemptId !== event.attemptId || value.status !== 'COMPLETED' || value.promotable !== true) {
    throw new RestartSafeStateError('STAGE_RECEIPT_SEMANTICS', `Invalid completed receipt semantics for ${event.stageId}`);
  }
  return { path, receipt: value, sha256 };
}

export async function verifyAttemptTerminalReference(jobRoot, event) {
  if (!['STAGE_FAILED', 'STAGE_ABANDONED'].includes(event.eventType)) {
    throw new RestartSafeStateError('STAGE_EVENT_TYPE', 'Attempt terminal verification requires STAGE_FAILED or STAGE_ABANDONED');
  }
  const reference = event.payload?.receipt;
  if (!reference || typeof reference.uri !== 'string' || !HASH_PATTERN.test(reference.sha256 ?? '') || !HASH_PATTERN.test(reference.receiptHash ?? '')) {
    throw new RestartSafeStateError('ATTEMPT_RECEIPT_REFERENCE', `Malformed attempt receipt reference for ${event.stageId}`);
  }
  const path = await resolveContainedPath(jobRoot, reference.uri);
  const { value, sha256 } = await readJson(path);
  const expectedStatus = event.eventType === 'STAGE_FAILED' ? 'FAILED' : 'ABANDONED';
  if (value.schemaVersion !== 'bfs.restartSafeProductionAttemptReceipt.v0.1'
    || sha256 !== reference.sha256 || value.receiptHash !== reference.receiptHash || !validSelfHash(value, 'receiptHash')) {
    throw new RestartSafeStateError('ATTEMPT_RECEIPT_REFERENCE', `Attempt receipt reference mismatch for ${event.stageId}`);
  }
  if (value.jobId !== event.jobId || value.stageId !== event.stageId || value.attemptId !== event.attemptId
    || value.status !== expectedStatus || value.promotable !== false) {
    throw new RestartSafeStateError('ATTEMPT_RECEIPT_SEMANTICS', `Invalid ${expectedStatus} receipt semantics for ${event.stageId}`);
  }
  return { path, receipt: value, sha256 };
}

export async function deriveJobState(jobRoot) {
  const { manifest, sha256: manifestFileSha256 } = await readManifest(jobRoot);
  const ledger = await readLedger(jobRoot, manifest.jobId);
  const expectedStages = manifest.stageDag.map(row => row.id);
  const stageState = Object.fromEntries(expectedStages.map(id => [id, { id, status: 'PENDING', attempts: [], completed: null }]));
  for (const row of ledger.events) {
    const event = row.event;
    if (event.stageId === null) continue;
    const stage = stageState[event.stageId];
    if (!stage) throw new RestartSafeStateError('UNKNOWN_STAGE', `Ledger references unknown stage ${event.stageId}`);
    if (event.eventType === 'STAGE_STARTED') {
      if (stage.completed) throw new RestartSafeStateError('COMPLETED_STAGE_RESTARTED', `Completed stage ${event.stageId} was started again`);
      if (stage.attempts.some(item => item.attemptId === event.attemptId)) {
        throw new RestartSafeStateError('ATTEMPT_ID_REUSED', `Attempt ID reused for ${event.stageId}`);
      }
      stage.attempts.push({ attemptId: event.attemptId, status: 'STARTED', startEventHash: event.eventHash });
      stage.status = 'STARTED';
    } else if (['STAGE_FAILED', 'STAGE_ABANDONED'].includes(event.eventType)) {
      const attempt = stage.attempts.find(item => item.attemptId === event.attemptId);
      if (!attempt || attempt.status !== 'STARTED') throw new RestartSafeStateError('ATTEMPT_TRANSITION', `Invalid ${event.eventType} transition for ${event.stageId}`);
      const terminal = await verifyAttemptTerminalReference(jobRoot, event);
      attempt.status = event.eventType === 'STAGE_FAILED' ? 'FAILED' : 'ABANDONED';
      attempt.terminalEventHash = event.eventHash;
      attempt.terminalReceipt = terminal;
      stage.status = attempt.status;
    } else if (event.eventType === 'STAGE_COMPLETED') {
      const attempt = stage.attempts.find(item => item.attemptId === event.attemptId);
      if (!attempt || attempt.status !== 'STARTED') throw new RestartSafeStateError('ATTEMPT_TRANSITION', `Invalid completion transition for ${event.stageId}`);
      const completion = await verifyStageCompletionReference(jobRoot, event);
      attempt.status = 'COMPLETED';
      attempt.terminalEventHash = event.eventHash;
      stage.status = 'COMPLETED';
      stage.completed = { ...completion, eventHash: event.eventHash, attemptId: event.attemptId };
    } else if (event.eventType === 'STAGE_SKIPPED_VERIFIED') {
      if (!stage.completed) throw new RestartSafeStateError('SKIP_WITHOUT_COMPLETION', `Stage ${event.stageId} was skipped without a verified completion`);
    }
  }
  for (const stage of manifest.stageDag) {
    if (stageState[stage.id].status === 'COMPLETED') {
      for (const dependency of stage.dependsOn) {
        if (stageState[dependency]?.status !== 'COMPLETED') {
          throw new RestartSafeStateError('STAGE_DEPENDENCY', `Completed stage ${stage.id} has incomplete dependency ${dependency}`);
        }
      }
    }
  }
  return { manifest, manifestFileSha256, ledger, stages: stageState };
}

async function psField(pid, field) {
  try {
    const result = await execFileAsync('/bin/ps', ['-p', String(pid), '-o', `${field}=`], {
      encoding: 'utf8', timeout: 2000, env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C' },
    });
    return result.stdout.trim();
  } catch (error) {
    if ([1, 3].includes(error?.code)) return null;
    throw error;
  }
}

export async function readProcessIdentity(pid) {
  if (!Number.isSafeInteger(pid) || pid <= 0) throw new RestartSafeStateError('PROCESS_PID', `Invalid PID ${pid}`);
  const [start, executable, argv, parent] = await Promise.all([
    psField(pid, 'lstart'), psField(pid, 'comm'), psField(pid, 'args'), psField(pid, 'ppid'),
  ]);
  if ([start, executable, argv, parent].every(value => value === null)) return { pid, live: false };
  if ([start, executable, argv, parent].some(value => value === null || value.length === 0)) {
    throw new RestartSafeStateError('PROCESS_IDENTITY_AMBIGUOUS', `Could not read complete identity for PID ${pid}`);
  }
  const body = { pid, parentPid: Number.parseInt(parent, 10), start, executable, argv, argvSha256: sha256Bytes(Buffer.from(argv)) };
  return { ...body, live: true, identityHash: sha256Bytes(Buffer.from(canonicalJson(body))) };
}

export async function compareRecordedProcess(recorded) {
  if (!recorded || !Number.isSafeInteger(recorded.pid) || !HASH_PATTERN.test(recorded.identityHash ?? '')) {
    throw new RestartSafeStateError('PROCESS_IDENTITY_AMBIGUOUS', 'Recorded process identity is incomplete');
  }
  const observed = await readProcessIdentity(recorded.pid);
  if (!observed.live) return { state: 'DEAD', recorded, observed };
  if (observed.identityHash !== recorded.identityHash) return { state: 'PID_REUSED_OR_CHANGED', recorded, observed };
  return { state: 'LIVE_MATCH', recorded, observed };
}

async function readLeaseOwner(lockRoot) {
  const path = resolve(lockRoot, 'owner.json');
  const { value } = await readJson(path);
  if (value.schemaVersion !== 'bfs.restartSafeWriterLease.v0.1' || !validSelfHash(value, 'leaseHash')) {
    throw new RestartSafeStateError('WRITER_LEASE_INVALID', 'Writer lease owner record is invalid');
  }
  return value;
}

export async function acquireWriterLease(jobRoot, { allowReclaimDead = false } = {}) {
  const lockRoot = resolve(jobRoot, '.writer-lock');
  try {
    await mkdir(lockRoot);
  } catch (error) {
    if (error?.code !== 'EEXIST') throw error;
    const owner = await readLeaseOwner(lockRoot);
    const comparison = await compareRecordedProcess(owner.process);
    if (comparison.state === 'LIVE_MATCH') {
      throw new RestartSafeStateError('LIVE_WRITER', `Job already has live writer PID ${owner.process.pid}`, { owner });
    }
    if (comparison.state === 'PID_REUSED_OR_CHANGED') {
      throw new RestartSafeStateError('PROCESS_IDENTITY_AMBIGUOUS', `Writer PID ${owner.process.pid} was reused or changed`, { owner, observed: comparison.observed });
    }
    if (!allowReclaimDead) {
      throw new RestartSafeStateError('STALE_WRITER_LEASE', 'Dead writer lease requires explicit recovery');
    }
    const stalePath = resolve(jobRoot, `.writer-lock.stale-${owner.token}`);
    try {
      await rename(lockRoot, stalePath);
    } catch (renameError) {
      throw new RestartSafeStateError('WRITER_LEASE_RACE', `Could not quarantine stale writer lease: ${renameError.message}`);
    }
    await fsyncDirectory(jobRoot);
    try {
      await mkdir(lockRoot);
    } catch (mkdirError) {
      throw new RestartSafeStateError('WRITER_LEASE_RACE', `Could not acquire writer lease after quarantine: ${mkdirError.message}`);
    }
  }
  await fsyncDirectory(jobRoot);
  const token = randomUUID();
  const writerProcess = await readProcessIdentity(globalThis.process.pid);
  if (!writerProcess.live) throw new RestartSafeStateError('PROCESS_IDENTITY_AMBIGUOUS', 'Current writer process identity is unavailable');
  const { record } = await writeExclusiveDurableHashed(resolve(lockRoot, 'owner.json'), {
    schemaVersion: 'bfs.restartSafeWriterLease.v0.1', token, process: writerProcess,
  }, 'leaseHash');
  return { lockRoot, token, owner: record };
}

export async function releaseWriterLease(lease) {
  const owner = await readLeaseOwner(lease.lockRoot);
  if (owner.token !== lease.token) throw new RestartSafeStateError('WRITER_LEASE_TOKEN', 'Writer lease token mismatch');
  await unlink(resolve(lease.lockRoot, 'owner.json'));
  await rmdir(lease.lockRoot);
  await fsyncDirectory(dirname(lease.lockRoot));
}
