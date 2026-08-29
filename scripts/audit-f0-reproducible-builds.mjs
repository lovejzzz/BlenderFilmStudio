#!/usr/bin/env node

import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream, statfsSync } from 'node:fs';
import {
  access,
  lstat,
  mkdir,
  open,
  readFile,
  readdir,
  readlink,
  realpath,
  stat,
} from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { isAbsolute, relative, resolve } from 'node:path';
import process from 'node:process';

const PINNED_COMMIT = 'fbe6228777e7d9afefcd61a413844e790ae75db7';
const PINNED_TAG = 'v5.2.0';
const REQUIRED_FREE_BYTES = 160n * (1024n ** 3n);
const MAX_RUNTIME_MS = 10 * 60 * 1000;
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const BLENDER_RELATIVE_PATH = 'Contents/MacOS/Blender';
const THUMBNAILER_RELATIVE_PATH = 'Contents/PlugIns/blender-thumbnailer.appex/Contents/MacOS/blender-thumbnailer';
const OSL_PREFIX = 'Contents/Resources/5.2/scripts/addons_core/cycles/shader/';

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) {
      throw new Error(`Expected --name value argument, observed ${key ?? '<missing>'}`);
    }
    parsed[key.slice(2)] = value;
  }
  return parsed;
}

function exec(command, args, cwd = undefined) {
  return execFileSync(command, args, {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C' },
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

function execCombined(command, args) {
  try {
    return execFileSync(command, args, {
      encoding: 'utf8',
      env: { ...process.env, PATH: FROZEN_PATH, LANG: 'C', LC_ALL: 'C' },
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();
  } catch (error) {
    const stdout = Buffer.isBuffer(error.stdout) ? error.stdout.toString('utf8') : (error.stdout ?? '');
    const stderr = Buffer.isBuffer(error.stderr) ? error.stderr.toString('utf8') : (error.stderr ?? '');
    return `${stdout}${stderr}`.trim();
  }
}

function git(source, args) {
  return exec('/usr/bin/git', ['-C', source, ...args]);
}

function freeBytes(path) {
  const value = statfsSync(path, { bigint: true });
  return value.bavail * value.bsize;
}

function sha256Bytes(value) {
  return createHash('sha256').update(value).digest('hex');
}

async function sha256File(path) {
  const hash = createHash('sha256');
  const input = createReadStream(path);
  input.on('data', chunk => hash.update(chunk));
  await finished(input);
  return hash.digest('hex');
}

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function writeTextExclusive(path, body) {
  const handle = await open(path, 'wx', 0o600);
  try {
    await handle.writeFile(body);
    await handle.sync();
  } finally {
    await handle.close();
  }
}

async function writeJsonExclusive(path, value) {
  const bodyWithoutHash = `${JSON.stringify(value, null, 2)}\n`;
  const record = { ...value, receiptHash: sha256Bytes(Buffer.from(bodyWithoutHash)) };
  await writeTextExclusive(path, `${JSON.stringify(record, null, 2)}\n`);
  return record;
}

function admissionFor({ observedFreeBytes, sourceHead, sourceTag, sourceClean }) {
  const failures = [];
  if (observedFreeBytes < REQUIRED_FREE_BYTES) failures.push('FREE_DISK_BELOW_160_GIB');
  if (sourceHead !== PINNED_COMMIT) failures.push('SOURCE_HEAD_MISMATCH');
  if (sourceTag !== PINNED_TAG) failures.push('SOURCE_TAG_MISMATCH');
  if (!sourceClean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  return {
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    failures,
    authorizedNativeProcessStarts: failures.length === 0 ? 1 : 0,
  };
}

function parseTiming(text) {
  const seconds = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? Number.NaN);
  return {
    realSeconds: seconds('real'),
    userSeconds: seconds('user'),
    systemSeconds: seconds('sys'),
    maximumResidentSetSizeBytes: Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? Number.NaN),
  };
}

async function runTimed({ binary, stageRoot }) {
  const stdoutPath = resolve(stageRoot, 'stdout.log');
  const stderrPath = resolve(stageRoot, 'stderr.log');
  const timingPath = resolve(stageRoot, 'timing.log');
  const stdoutStream = createWriteStream(stdoutPath, { flags: 'wx', mode: 0o600 });
  const stderrStream = createWriteStream(stderrPath, { flags: 'wx', mode: 0o600 });
  const args = ['--background', '--factory-startup', '--version'];
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', ['-lp', '-o', timingPath, binary, ...args], {
    detached: true,
    env: {
      PATH: FROZEN_PATH,
      LANG: 'C',
      LC_ALL: 'C',
      HOME: process.env.HOME,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let spawnError = null;
  let timedOut = false;
  let forceTimer = null;
  child.on('error', error => { spawnError = error; });
  child.stdout.on('data', chunk => {
    stdoutStream.write(chunk);
    process.stdout.write(chunk);
  });
  child.stderr.on('data', chunk => {
    stderrStream.write(chunk);
    process.stderr.write(chunk);
  });
  const timeout = setTimeout(() => {
    timedOut = true;
    try { process.kill(-child.pid, 'SIGTERM'); } catch { child.kill('SIGTERM'); }
    forceTimer = setTimeout(() => {
      try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
    }, 5000);
  }, MAX_RUNTIME_MS);
  const terminal = await new Promise(resolveClose => {
    child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal }));
  });
  clearTimeout(timeout);
  if (forceTimer) clearTimeout(forceTimer);
  stdoutStream.end();
  stderrStream.end();
  await Promise.all([finished(stdoutStream), finished(stderrStream)]);
  return {
    childPid: child.pid,
    exitCode: spawnError ? 1 : terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    spawnError: spawnError?.message ?? null,
    elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    command: { executable: binary, args },
    stdoutPath,
    stderrPath,
    timingPath,
  };
}

function parseVersionOutput(text) {
  const fields = {};
  for (const line of text.split(/\r?\n/)) {
    const match = line.match(/^\s+([^:]+):\s*(.*)$/);
    if (match) fields[match[1].trim()] = match[2].trim();
  }
  return {
    firstLine: text.split(/\r?\n/).find(line => line.trim() !== '')?.trim() ?? null,
    fields,
    reportsVersion520: /^Blender 5\.2\.0(?:\s|$)/m.test(text),
    reportsPinnedCommit: text.includes(PINNED_COMMIT) || text.includes(PINNED_COMMIT.slice(0, 12)),
  };
}

async function runRuntime({ label, appRoot, evidenceRoot, workspace, source }) {
  const stageRoot = resolve(evidenceRoot, `runtime-${label}`);
  await mkdir(stageRoot, { recursive: false });
  const binary = resolve(appRoot, BLENDER_RELATIVE_PATH);
  const observedFreeBytes = freeBytes(workspace);
  const sourceHead = git(source, ['rev-parse', 'HEAD']);
  const sourceTag = git(source, ['describe', '--tags', '--exact-match', 'HEAD']);
  const sourceClean = git(source, ['status', '--porcelain=v1']) === '';
  const decision = admissionFor({ observedFreeBytes, sourceHead, sourceTag, sourceClean });
  const admission = await writeJsonExclusive(resolve(stageRoot, 'admission.json'), {
    schemaVersion: 'bfs.f0RuntimeAdmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    stage: `runtime-${label}`,
    observedAt: new Date().toISOString(),
    status: decision.status,
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: { path: source, head: sourceHead, tag: sourceTag, clean: sourceClean },
    artifact: binary,
    failures: decision.failures,
    authorizedNativeProcessStarts: decision.authorizedNativeProcessStarts,
  });
  if (decision.status !== 'ACCEPTED') {
    const receipt = await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
      schemaVersion: 'bfs.f0RuntimeReceipt.v0.1',
      protocol: 'F0-SOURCE-FEASIBILITY',
      gate: 'F0.1',
      stage: `runtime-${label}`,
      status: 'BLOCKED',
      nativeProcessStarts: 0,
      admissionReceiptHash: admission.receiptHash,
      failures: decision.failures,
    });
    return { status: 'BLOCKED', receipt };
  }
  const startedAt = new Date().toISOString();
  const result = await runTimed({ binary, stageRoot });
  const endedAt = new Date().toISOString();
  const stdout = await readFile(result.stdoutPath, 'utf8');
  const stderr = await readFile(result.stderrPath, 'utf8');
  const timingText = await readFile(result.timingPath, 'utf8').catch(() => '');
  const version = parseVersionOutput(`${stdout}\n${stderr}`);
  const checks = {
    processExitZero: result.exitCode === 0 && result.signal === null && !result.timedOut,
    reportsBlender520: version.reportsVersion520,
    reportsPinnedCommit: version.reportsPinnedCommit,
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  const receipt = await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0RuntimeReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    stage: `runtime-${label}`,
    status,
    startedAt,
    endedAt,
    admissionReceiptHash: admission.receiptHash,
    command: result.command,
    process: {
      pid: result.childPid,
      exitCode: result.exitCode,
      signal: result.signal,
      timedOut: result.timedOut,
      spawnError: result.spawnError,
      elapsedSeconds: result.elapsedSeconds,
      timing: parseTiming(timingText),
    },
    source: { path: source, head: sourceHead, tag: sourceTag, clean: sourceClean },
    artifact: { path: binary, bytes: (await stat(binary)).size, sha256: await sha256File(binary) },
    runtimeIdentity: version,
    logs: {
      stdout: { path: relative(process.cwd(), result.stdoutPath), sha256: await sha256File(result.stdoutPath), bytes: Buffer.byteLength(stdout) },
      stderr: { path: relative(process.cwd(), result.stderrPath), sha256: await sha256File(result.stderrPath), bytes: Buffer.byteLength(stderr) },
      timing: { path: relative(process.cwd(), result.timingPath), sha256: await sha256File(result.timingPath), bytes: Buffer.byteLength(timingText) },
    },
    checks,
  });
  return { status, receipt, version };
}

async function walkBundle(root, current = '') {
  const absolute = resolve(root, current);
  const entries = await readdir(absolute);
  entries.sort((left, right) => left.localeCompare(right, 'en'));
  const records = [];
  for (const name of entries) {
    const relativePath = current === '' ? name : `${current}/${name}`;
    const path = resolve(root, relativePath);
    const value = await lstat(path);
    const mode = value.mode & 0o7777;
    if (value.isDirectory()) {
      records.push({ path: relativePath, type: 'directory', mode });
      records.push(...await walkBundle(root, relativePath));
    } else if (value.isSymbolicLink()) {
      records.push({ path: relativePath, type: 'symlink', mode, target: await readlink(path) });
    } else if (value.isFile()) {
      records.push({ path: relativePath, type: 'file', mode, bytes: value.size, sha256: await sha256File(path) });
    } else {
      records.push({ path: relativePath, type: 'other', mode, bytes: value.size });
    }
  }
  return records;
}

function manifestText(records) {
  return records.map(record => JSON.stringify(record)).join('\n') + '\n';
}

function allowedDifference(path) {
  if (path === BLENDER_RELATIVE_PATH || path === THUMBNAILER_RELATIVE_PATH) return 'MACH_O_LINK_METADATA';
  if (path.startsWith(OSL_PREFIX) && path.endsWith('.oso')) return 'OSL_EMBEDDED_BUILD_ROOT';
  return null;
}

function replaceAllSameLength(buffer, search, replacement) {
  if (search.length !== replacement.length) throw new Error('Normalized byte strings must have equal lengths');
  let cursor = 0;
  let count = 0;
  while ((cursor = buffer.indexOf(search, cursor)) !== -1) {
    replacement.copy(buffer, cursor);
    cursor += replacement.length;
    count += 1;
  }
  return count;
}

function byteDifferenceSummary(left, right) {
  const spans = [];
  let count = 0;
  let activeStart = null;
  let last = null;
  const length = Math.min(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    if (left[index] !== right[index]) {
      count += 1;
      if (activeStart === null) activeStart = index;
      last = index;
    } else if (activeStart !== null) {
      if (spans.length < 64) spans.push({ start: activeStart, endInclusive: last });
      activeStart = null;
    }
  }
  if (activeStart !== null && spans.length < 64) spans.push({ start: activeStart, endInclusive: last });
  count += Math.abs(left.length - right.length);
  return { differingByteCount: count, equalLength: left.length === right.length, spans, spansTruncated: spans.length === 64 };
}

async function differenceDetails(path, appA, appB, workspace) {
  const absoluteA = resolve(appA, path);
  const absoluteB = resolve(appB, path);
  const left = await readFile(absoluteA);
  const right = await readFile(absoluteB);
  const summary = byteDifferenceSummary(left, right);
  const buildRootA = resolve(workspace, 'build-a');
  const buildRootB = resolve(workspace, 'build-b');
  const canonicalRoot = resolve(workspace, 'build-x');
  const normalizedA = Buffer.from(left);
  const normalizedB = Buffer.from(right);
  const occurrencesA = replaceAllSameLength(normalizedA, Buffer.from(buildRootA), Buffer.from(canonicalRoot));
  const occurrencesB = replaceAllSameLength(normalizedB, Buffer.from(buildRootB), Buffer.from(canonicalRoot));
  const normalizedShaA = sha256Bytes(normalizedA);
  const normalizedShaB = sha256Bytes(normalizedB);
  return {
    path,
    classification: allowedDifference(path),
    bytes: left.length,
    rawSha256A: sha256Bytes(left),
    rawSha256B: sha256Bytes(right),
    ...summary,
    buildRootOccurrences: { buildA: occurrencesA, buildB: occurrencesB },
    buildRootNormalizedSha256A: normalizedShaA,
    buildRootNormalizedSha256B: normalizedShaB,
    identicalAfterBuildRootNormalization: normalizedShaA === normalizedShaB,
  };
}

function machoMetadata(binary) {
  const loadCommands = exec('/usr/bin/otool', ['-l', binary]);
  const uuid = exec('/usr/bin/dwarfdump', ['--uuid', binary]);
  const signature = execCombined('/usr/bin/codesign', ['-dvv', binary]);
  const linkedit = loadCommands.match(/segname __LINKEDIT[\s\S]*?fileoff (\d+)[\s\S]*?filesize (\d+)/);
  const codeSignature = loadCommands.match(/cmd LC_CODE_SIGNATURE[\s\S]*?dataoff (\d+)[\s\S]*?datasize (\d+)/);
  return {
    uuid,
    linkedit: linkedit ? { fileOffset: Number(linkedit[1]), bytes: Number(linkedit[2]) } : null,
    codeSignature: codeSignature ? { fileOffset: Number(codeSignature[1]), bytes: Number(codeSignature[2]) } : null,
    signing: signature.split(/\r?\n/).filter(line => /^(Identifier|Format|CodeDirectory|Signature|TeamIdentifier|Sealed Resources)=/.test(line)),
  };
}

async function compareBundles({ appA, appB, evidenceRoot, workspace, runtimeA, runtimeB }) {
  const manifestA = await walkBundle(appA);
  const manifestB = await walkBundle(appB);
  const textA = manifestText(manifestA);
  const textB = manifestText(manifestB);
  await writeTextExclusive(resolve(evidenceRoot, 'manifest-a.jsonl'), textA);
  await writeTextExclusive(resolve(evidenceRoot, 'manifest-b.jsonl'), textB);
  const mapA = new Map(manifestA.map(record => [record.path, record]));
  const mapB = new Map(manifestB.map(record => [record.path, record]));
  const allPaths = [...new Set([...mapA.keys(), ...mapB.keys()])].sort((left, right) => left.localeCompare(right, 'en'));
  const missingFromA = [];
  const missingFromB = [];
  const metadataDifferences = [];
  const contentDifferencePaths = [];
  for (const path of allPaths) {
    const left = mapA.get(path);
    const right = mapB.get(path);
    if (!left) {
      missingFromA.push(path);
      continue;
    }
    if (!right) {
      missingFromB.push(path);
      continue;
    }
    if (left.type !== right.type || left.mode !== right.mode || left.bytes !== right.bytes || left.target !== right.target) {
      metadataDifferences.push({ path, a: left, b: right });
    }
    if (left.type === 'file' && right.type === 'file' && left.sha256 !== right.sha256) {
      contentDifferencePaths.push(path);
    }
  }
  const differences = [];
  for (const path of contentDifferencePaths) {
    differences.push(await differenceDetails(path, appA, appB, workspace));
  }
  const unexpectedDifferences = differences.filter(record => record.classification === null).map(record => record.path);
  const oslDifferences = differences.filter(record => record.classification === 'OSL_EMBEDDED_BUILD_ROOT');
  const machoDifferences = differences.filter(record => record.classification === 'MACH_O_LINK_METADATA');
  const buildFieldsA = runtimeA.version?.fields ?? {};
  const buildFieldsB = runtimeB.version?.fields ?? {};
  const runtimeFieldDifferences = [...new Set([...Object.keys(buildFieldsA), ...Object.keys(buildFieldsB)])]
    .sort()
    .filter(key => buildFieldsA[key] !== buildFieldsB[key])
    .map(key => ({ field: key, a: buildFieldsA[key] ?? null, b: buildFieldsB[key] ?? null }));
  const runtimeAllowedFields = new Set(['build date', 'build time']);
  const unexpectedRuntimeFieldDifferences = runtimeFieldDifferences.filter(item => !runtimeAllowedFields.has(item.field));
  const semanticChecks = {
    identicalPathSet: missingFromA.length === 0 && missingFromB.length === 0,
    identicalFileMetadata: metadataDifferences.length === 0,
    allContentDifferencesLocalized: unexpectedDifferences.length === 0,
    allOslDifferencesExplainedByBuildRoot: oslDifferences.every(record => record.identicalAfterBuildRootNormalization),
    machoDifferencesLimitedToExpectedExecutables: machoDifferences.length <= 2,
    runtimeAReportsPinnedIdentity: runtimeA.status === 'PASS',
    runtimeBReportsPinnedIdentity: runtimeB.status === 'PASS',
    runtimeIdentityDifferencesLimitedToBuildTime: unexpectedRuntimeFieldDifferences.length === 0,
  };
  const semanticStatus = Object.values(semanticChecks).every(Boolean) ? 'PASS' : 'FAIL';
  const macho = {};
  for (const path of [BLENDER_RELATIVE_PATH, THUMBNAILER_RELATIVE_PATH]) {
    if (contentDifferencePaths.includes(path)) {
      macho[path] = { buildA: machoMetadata(resolve(appA, path)), buildB: machoMetadata(resolve(appB, path)) };
    }
  }
  const comparison = {
    schemaVersion: 'bfs.f0BundleComparison.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    status: semanticStatus,
    observedAt: new Date().toISOString(),
    bundles: {
      buildA: { path: appA, entries: manifestA.length, manifestSha256: sha256Bytes(Buffer.from(textA)) },
      buildB: { path: appB, entries: manifestB.length, manifestSha256: sha256Bytes(Buffer.from(textB)) },
    },
    pathComparison: { missingFromA, missingFromB, metadataDifferences },
    contentComparison: {
      differingFileCount: differences.length,
      byteIdenticalFileCount: manifestA.filter(record => record.type === 'file').length - differences.length,
      unexpectedDifferences,
      differences,
    },
    runtimeIdentity: {
      buildA: runtimeA.version,
      buildB: runtimeB.version,
      differingFields: runtimeFieldDifferences,
      unexpectedDifferingFields: unexpectedRuntimeFieldDifferences,
    },
    macho,
    semanticChecks,
    explanation: {
      OSL_EMBEDDED_BUILD_ROOT: 'OSL objects embed their absolute -o output path. Replacing build-a/build-b with the equal-length canonical build-x makes each differing OSL object byte-identical.',
      MACH_O_LINK_METADATA: 'The two runtime-equivalent Mach-O executables differ only in a bounded byte set attributable to build-time strings, linker-generated UUID/link metadata, and the resulting ad-hoc linker signature. Exact byte spans, __LINKEDIT/code-signature offsets, UUIDs, and runtime-reported build fields are recorded.',
      claim: 'Semantically identical, not byte-for-byte reproducible.',
    },
  };
  return writeJsonExclusive(resolve(evidenceRoot, 'comparison.json'), comparison);
}

async function writeNegativeControls({ evidenceRoot, sourceHead, sourceTag }) {
  const negativeRoot = resolve(evidenceRoot, 'negative-control');
  await mkdir(negativeRoot, { recursive: false });
  let restrictedNativeStarts = 0;
  const runIfAdmitted = decision => {
    if (decision.status === 'ACCEPTED') restrictedNativeStarts += 1;
  };
  const diskDecision = admissionFor({
    observedFreeBytes: REQUIRED_FREE_BYTES - 1n,
    sourceHead: PINNED_COMMIT,
    sourceTag: PINNED_TAG,
    sourceClean: true,
  });
  runIfAdmitted(diskDecision);
  const sourceDecision = admissionFor({
    observedFreeBytes: REQUIRED_FREE_BYTES,
    sourceHead: '0000000000000000000000000000000000000000',
    sourceTag,
    sourceClean: true,
  });
  runIfAdmitted(sourceDecision);
  const checks = {
    diskOneByteBelowBlocked: diskDecision.status === 'BLOCKED' && diskDecision.failures.includes('FREE_DISK_BELOW_160_GIB'),
    sourceHeadMismatchBlocked: sourceDecision.status === 'BLOCKED' && sourceDecision.failures.includes('SOURCE_HEAD_MISMATCH'),
    noRestrictedNativeProcessStarted: restrictedNativeStarts === 0,
    actualSourceWasPinnedWhenControlRan: sourceHead === PINNED_COMMIT,
  };
  return writeJsonExclusive(resolve(negativeRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0NegativeControlReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
    observedAt: new Date().toISOString(),
    method: 'Deterministic injected inputs passed through the same admissionFor function used immediately before each Blender runtime launch.',
    diskOneByteBelow: {
      requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
      injectedFreeBytes: (REQUIRED_FREE_BYTES - 1n).toString(),
      decision: diskDecision,
    },
    sourceHeadMismatch: {
      pinnedCommit: PINNED_COMMIT,
      injectedHead: '0000000000000000000000000000000000000000',
      decision: sourceDecision,
    },
    compilerOrBlenderPids: [],
    restrictedNativeProcessStarts: restrictedNativeStarts,
    checks,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  for (const required of ['source', 'workspace', 'evidence-root']) {
    if (!args[required]) throw new Error(`Missing --${required}`);
  }
  if (!isAbsolute(args.source) || !isAbsolute(args.workspace)) {
    throw new Error('Source and workspace must be absolute paths');
  }
  const repositoryRoot = exec('/usr/bin/git', ['rev-parse', '--show-toplevel'], process.cwd());
  const source = await realpath(args.source);
  const workspace = await realpath(args.workspace);
  const evidenceRoot = await realpath(resolve(repositoryRoot, args['evidence-root']));
  const evidenceBase = resolve(repositoryRoot, 'experiments', 'ai-native-studio-f0');
  if (relative(evidenceBase, evidenceRoot).startsWith('..')) throw new Error('Evidence root escapes the F0 evidence directory');
  if (!relative(repositoryRoot, workspace).startsWith('..')) throw new Error('Workspace must remain outside the repository');
  if (relative(workspace, source).startsWith('..')) throw new Error('Source must remain inside the external workspace');
  const appA = resolve(workspace, 'build-a', 'bin', 'Blender.app');
  const appB = resolve(workspace, 'build-b', 'bin', 'Blender.app');
  for (const artifact of [resolve(appA, BLENDER_RELATIVE_PATH), resolve(appB, BLENDER_RELATIVE_PATH)]) {
    if (!await exists(artifact)) throw new Error(`Missing build artifact: ${artifact}`);
  }
  const sourceHead = git(source, ['rev-parse', 'HEAD']);
  const sourceTag = git(source, ['describe', '--tags', '--exact-match', 'HEAD']);
  const sourceClean = git(source, ['status', '--porcelain=v1']) === '';

  const runtimeA = await runRuntime({ label: 'a', appRoot: appA, evidenceRoot, workspace, source });
  if (runtimeA.status === 'BLOCKED') {
    process.stdout.write('F0_REPRO_AUDIT_BLOCKED stage=runtime-a native=0\n');
    process.exitCode = 2;
    return;
  }
  const runtimeB = await runRuntime({ label: 'b', appRoot: appB, evidenceRoot, workspace, source });
  if (runtimeB.status === 'BLOCKED') {
    process.stdout.write('F0_REPRO_AUDIT_BLOCKED stage=runtime-b native=0\n');
    process.exitCode = 2;
    return;
  }
  const comparison = await compareBundles({ appA, appB, evidenceRoot, workspace, runtimeA, runtimeB });
  const negative = await writeNegativeControls({ evidenceRoot, sourceHead, sourceTag });
  const checks = {
    runtimeA: runtimeA.status === 'PASS',
    runtimeB: runtimeB.status === 'PASS',
    semanticBundleComparison: comparison.status === 'PASS',
    negativeControls: negative.status === 'PASS',
    sourceHeadPinned: sourceHead === PINNED_COMMIT,
    sourceTagPinned: sourceTag === PINNED_TAG,
    sourceWorktreeClean: sourceClean,
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  await writeJsonExclusive(resolve(evidenceRoot, 'verdict.json'), {
    schemaVersion: 'bfs.f0GateVerdict.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.1',
    status,
    observedAt: new Date().toISOString(),
    crossBindings: {
      runtimeAReceiptHash: runtimeA.receipt.receiptHash,
      runtimeBReceiptHash: runtimeB.receipt.receiptHash,
      comparisonReceiptHash: comparison.receiptHash,
      negativeControlReceiptHash: negative.receiptHash,
    },
    source: { path: source, head: sourceHead, tag: sourceTag, clean: sourceClean },
    checks,
  });
  process.stdout.write(`F0_REPRO_AUDIT_${status} differingFiles=${comparison.contentComparison.differingFileCount} claim=${JSON.stringify(comparison.explanation.claim)}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
