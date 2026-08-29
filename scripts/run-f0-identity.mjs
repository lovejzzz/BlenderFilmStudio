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
  rename,
  stat,
} from 'node:fs/promises';
import { finished } from 'node:stream/promises';
import { basename, isAbsolute, relative, resolve } from 'node:path';
import process from 'node:process';

const BASE_COMMIT = 'fbe6228777e7d9afefcd61a413844e790ae75db7';
const IDENTITY_COMMIT = '0a25790a1cd6feff4bae1b03d81e4c43ec55a0b5';
const DEPENDENCY_COMMIT = '5a140a8ccc8c070221b1b06e2c6f89f136c5758d';
const REQUIRED_FREE_BYTES = 160n * (1024n ** 3n);
const MAX_BUILD_MS = 12 * 60 * 60 * 1000;
const MAX_RUNTIME_MS = 10 * 60 * 1000;
const FROZEN_PATH = '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';
const PRODUCT_NAME = 'Film Studio Engine F0';
const BUNDLE_ID = 'studio.ainativefilm.f0';
const THUMBNAILER_BUNDLE_ID = 'studio.ainativefilm.f0.thumbnailer';
const CONFIG_NAMESPACE = 'FilmStudioEngineF0';
const OFFICIAL_CONFIG_ROOT = '/Users/mengyingli/Library/Application Support/Blender';
const EXPECTED_F0_ROOT = '/Users/mengyingli/Library/Application Support/FilmStudioEngineF0/5.2';

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

function parseTiming(text) {
  const seconds = label => Number(text.match(new RegExp(`^${label}\\s+([0-9.]+)`, 'm'))?.[1] ?? Number.NaN);
  return {
    realSeconds: seconds('real'),
    userSeconds: seconds('user'),
    systemSeconds: seconds('sys'),
    maximumResidentSetSizeBytes: Number(text.match(/^\s*([0-9]+)\s+maximum resident set size/m)?.[1] ?? Number.NaN),
  };
}

async function runTimed({ command, args, cwd, stageRoot, timeoutMs, env = {} }) {
  const stdoutPath = resolve(stageRoot, 'stdout.log');
  const stderrPath = resolve(stageRoot, 'stderr.log');
  const timingPath = resolve(stageRoot, 'timing.log');
  const stdoutStream = createWriteStream(stdoutPath, { flags: 'wx', mode: 0o600 });
  const stderrStream = createWriteStream(stderrPath, { flags: 'wx', mode: 0o600 });
  const started = process.hrtime.bigint();
  const child = spawn('/usr/bin/time', ['-lp', '-o', timingPath, command, ...args], {
    cwd,
    detached: true,
    env: {
      ...process.env,
      PATH: FROZEN_PATH,
      LANG: 'C',
      LC_ALL: 'C',
      ...env,
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
  }, timeoutMs);
  const terminal = await new Promise(resolveClose => {
    child.on('close', (exitCode, signal) => resolveClose({ exitCode, signal }));
  });
  clearTimeout(timeout);
  if (forceTimer) clearTimeout(forceTimer);
  stdoutStream.end();
  stderrStream.end();
  await Promise.all([finished(stdoutStream), finished(stderrStream)]);
  return {
    pid: child.pid,
    exitCode: spawnError ? 1 : terminal.exitCode,
    signal: terminal.signal,
    timedOut,
    spawnError: spawnError?.message ?? null,
    elapsedSeconds: Number(process.hrtime.bigint() - started) / 1e9,
    command: { executable: command, args, cwd },
    stdoutPath,
    stderrPath,
    timingPath,
  };
}

function sourceIdentity(source) {
  const head = git(source, ['rev-parse', 'HEAD']);
  const parent = git(source, ['rev-parse', 'HEAD^']);
  const branch = git(source, ['branch', '--show-current']);
  const status = git(source, ['status', '--porcelain=v1']);
  const dependency = git(source, ['submodule', 'status', '--', 'lib/macos_arm64']);
  return {
    path: source,
    head,
    parent,
    branch,
    clean: status === '',
    status,
    dependency,
  };
}

function sourceFailures(identity) {
  const failures = [];
  if (identity.head !== IDENTITY_COMMIT) failures.push('SOURCE_HEAD_MISMATCH');
  if (identity.parent !== BASE_COMMIT) failures.push('SOURCE_PARENT_MISMATCH');
  if (identity.branch !== 'codex/f0.2-independent-identity') failures.push('SOURCE_BRANCH_MISMATCH');
  if (!identity.clean) failures.push('SOURCE_WORKTREE_NOT_CLEAN');
  if (!identity.dependency.includes(DEPENDENCY_COMMIT)) failures.push('DEPENDENCY_COMMIT_MISMATCH');
  return failures;
}

function launchOverrideFailures(env) {
  const failures = [];
  for (const name of [
    'BLENDER_USER_RESOURCES',
    'BLENDER_USER_CONFIG',
    'BLENDER_USER_SCRIPTS',
    'BLENDER_USER_EXTENSIONS',
    'BLENDER_USER_DATAFILES',
  ]) {
    if (env[name]) failures.push(`UNEXPECTED_${name}`);
  }
  return failures;
}

async function writeAdmission({ path, label, workspace, source, artifact = null, env = process.env }) {
  const identity = sourceIdentity(source);
  const observedFreeBytes = freeBytes(workspace);
  const failures = sourceFailures(identity);
  if (observedFreeBytes < REQUIRED_FREE_BYTES) failures.push('FREE_DISK_BELOW_160_GIB');
  failures.push(...launchOverrideFailures(env));
  if (artifact && !(await exists(artifact))) failures.push('ARTIFACT_MISSING');
  return writeJsonExclusive(path, {
    schemaVersion: 'bfs.f0IdentityAdmission.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    label,
    observedAt: new Date().toISOString(),
    status: failures.length === 0 ? 'ACCEPTED' : 'BLOCKED',
    requiredFreeBytes: REQUIRED_FREE_BYTES.toString(),
    observedFreeBytes: observedFreeBytes.toString(),
    source: identity,
    artifact,
    userOverrides: Object.fromEntries(
      Object.entries(env).filter(([name]) => name.startsWith('BLENDER_USER_')),
    ),
    failures,
    authorizedNativeJobStarts: failures.length === 0 ? 1 : 0,
  });
}

async function logIdentity(repositoryRoot, result) {
  const stdout = await readFile(result.stdoutPath, 'utf8');
  const stderr = await readFile(result.stderrPath, 'utf8');
  const timingText = await readFile(result.timingPath, 'utf8').catch(() => '');
  return {
    stdout,
    stderr,
    timing: parseTiming(timingText),
    files: {
      stdout: {
        path: relative(repositoryRoot, result.stdoutPath),
        bytes: Buffer.byteLength(stdout),
        sha256: await sha256File(result.stdoutPath),
      },
      stderr: {
        path: relative(repositoryRoot, result.stderrPath),
        bytes: Buffer.byteLength(stderr),
        sha256: await sha256File(result.stderrPath),
      },
      timing: {
        path: relative(repositoryRoot, result.timingPath),
        bytes: Buffer.byteLength(timingText),
        sha256: await sha256File(result.timingPath),
      },
    },
  };
}

async function runBuild({ repositoryRoot, evidenceRoot, workspace, source }) {
  const stageRoot = resolve(evidenceRoot, 'build');
  await mkdir(stageRoot, { recursive: false });
  const buildRoot = resolve(workspace, 'build-f0.2-identity');
  const sourceApp = resolve(buildRoot, 'bin', 'Blender.app');
  const finalApp = resolve(buildRoot, 'bin', `${PRODUCT_NAME}.app`);
  const preFailures = [];
  if (await exists(buildRoot)) preFailures.push('BUILD_ROOT_ALREADY_EXISTS');
  const admission = await writeAdmission({
    path: resolve(stageRoot, 'admission.json'),
    label: 'clean-identity-build',
    workspace,
    source,
  });
  preFailures.push(...admission.failures);
  if (preFailures.length > 0) {
    await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
      schemaVersion: 'bfs.f0IdentityBuildReceipt.v0.1',
      protocol: 'F0-SOURCE-FEASIBILITY',
      gate: 'F0.2',
      status: 'BLOCKED',
      admissionReceiptHash: admission.receiptHash,
      nativeJobStarts: 0,
      failures: [...new Set(preFailures)],
    });
    process.stdout.write(`F0_IDENTITY_BUILD_BLOCKED failures=${[...new Set(preFailures)].join(',')} native=0\n`);
    process.exitCode = 2;
    return;
  }

  const freeBytesBefore = freeBytes(workspace);
  const startedAt = new Date().toISOString();
  const result = await runTimed({
    command: '/usr/bin/make',
    args: [`BUILD_DIR=${buildRoot}`, 'NPROCS=12'],
    cwd: source,
    stageRoot,
    timeoutMs: MAX_BUILD_MS,
  });
  const endedAt = new Date().toISOString();
  const logs = await logIdentity(repositoryRoot, result);
  const buildSucceeded = result.exitCode === 0 && result.signal === null && !result.timedOut;
  const sourceAppExists = await exists(sourceApp);
  let packageAdmission = null;
  let packaged = false;
  let packageFailure = null;
  if (buildSucceeded && sourceAppExists) {
    packageAdmission = await writeAdmission({
      path: resolve(stageRoot, 'package-admission.json'),
      label: 'bundle-directory-rename',
      workspace,
      source,
      artifact: sourceApp,
    });
    if (packageAdmission.status === 'ACCEPTED' && !(await exists(finalApp))) {
      await rename(sourceApp, finalApp);
      packaged = true;
    } else {
      packageFailure = packageAdmission.status !== 'ACCEPTED'
        ? packageAdmission.failures.join(',')
        : 'FINAL_BUNDLE_ALREADY_EXISTS';
    }
  }
  const identityAfter = sourceIdentity(source);
  const checks = {
    processExitZero: buildSucceeded,
    sourceAppProduced: sourceAppExists,
    packageAdmissionAccepted: packageAdmission?.status === 'ACCEPTED',
    finalBundleRenamed: packaged && await exists(finalApp),
    sourceStillClean: identityAfter.clean,
    sourceHeadUnchanged: identityAfter.head === IDENTITY_COMMIT,
  };
  const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
  const binary = resolve(finalApp, 'Contents', 'MacOS', 'Blender');
  await writeJsonExclusive(resolve(stageRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0IdentityBuildReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status,
    startedAt,
    endedAt,
    admissionReceiptHash: admission.receiptHash,
    packageAdmissionReceiptHash: packageAdmission?.receiptHash ?? null,
    command: result.command,
    process: {
      pid: result.pid,
      exitCode: result.exitCode,
      signal: result.signal,
      timedOut: result.timedOut,
      spawnError: result.spawnError,
      elapsedSeconds: result.elapsedSeconds,
      timing: logs.timing,
    },
    resources: {
      freeBytesBefore: freeBytesBefore.toString(),
      freeBytesAfter: freeBytes(workspace).toString(),
    },
    source: identityAfter,
    artifact: {
      app: finalApp,
      binary,
      exists: await exists(binary),
      binaryBytes: await exists(binary) ? (await stat(binary)).size : null,
      binarySha256: await exists(binary) ? await sha256File(binary) : null,
    },
    logs: logs.files,
    checks,
    failures: packageFailure ? [packageFailure] : [],
  });
  process.stdout.write(`F0_IDENTITY_BUILD_${status} seconds=${result.elapsedSeconds.toFixed(3)} app=${finalApp}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

async function walkTree(root, current = '') {
  const absolute = resolve(root, current);
  const names = await readdir(absolute);
  names.sort((left, right) => left.localeCompare(right, 'en'));
  const records = [];
  for (const name of names) {
    const relativePath = current ? `${current}/${name}` : name;
    const path = resolve(root, relativePath);
    const value = await lstat(path);
    const mode = value.mode & 0o7777;
    if (value.isDirectory()) {
      records.push({ path: relativePath, type: 'directory', mode });
      records.push(...await walkTree(root, relativePath));
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

async function treeIdentity(root) {
  if (!(await exists(root))) {
    return { root, state: 'ABSENT', entries: 0, digest: sha256Bytes(Buffer.from('ABSENT')) };
  }
  const records = await walkTree(root);
  const manifest = `${records.map(record => JSON.stringify(record)).join('\n')}\n`;
  return {
    root,
    state: 'PRESENT',
    entries: records.length,
    digest: sha256Bytes(Buffer.from(manifest)),
    manifestSha256: sha256Bytes(Buffer.from(manifest)),
  };
}

function plistRaw(plist, key) {
  try {
    return exec('/usr/bin/plutil', ['-extract', key, 'raw', plist]);
  } catch {
    return null;
  }
}

function parseMarker(text, prefix) {
  const line = text.split(/\r?\n/).find(value => value.startsWith(prefix));
  return line ? JSON.parse(line.slice(prefix.length)) : null;
}

function pngDimensions(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (buffer.length < 24 || !buffer.subarray(0, 8).equals(signature)) return null;
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

async function runAudit({ repositoryRoot, evidenceRoot, workspace, source }) {
  const app = resolve(workspace, 'build-f0.2-identity', 'bin', `${PRODUCT_NAME}.app`);
  const binary = resolve(app, 'Contents', 'MacOS', 'Blender');
  const plist = resolve(app, 'Contents', 'Info.plist');
  const thumbnailPlist = resolve(
    app,
    'Contents',
    'PlugIns',
    'blender-thumbnailer.appex',
    'Contents',
    'Info.plist',
  );
  const icon = resolve(app, 'Contents', 'Resources', 'blender_icon_legacy.icns');
  const topbar = resolve(app, 'Contents', 'Resources', '5.2', 'scripts', 'startup', 'bl_ui', 'space_topbar.py');
  for (const path of [app, binary, plist, thumbnailPlist, icon, topbar]) {
    if (!(await exists(path))) throw new Error(`Required bundle artifact missing: ${path}`);
  }

  const negativeRoot = resolve(evidenceRoot, 'negative-control');
  await mkdir(negativeRoot, { recursive: false });
  const injectedEnv = {
    ...process.env,
    BLENDER_USER_CONFIG: `${OFFICIAL_CONFIG_ROOT}/5.2/config`,
  };
  const injectedFailures = launchOverrideFailures(injectedEnv);
  const negative = await writeJsonExclusive(resolve(negativeRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0IdentityNegativeControl.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status: injectedFailures.includes('UNEXPECTED_BLENDER_USER_CONFIG') ? 'PASS' : 'FAIL',
    observedAt: new Date().toISOString(),
    injectedEnvironment: {
      BLENDER_USER_CONFIG: injectedEnv.BLENDER_USER_CONFIG,
    },
    decision: injectedFailures.length > 0 ? 'BLOCKED_CONFIG_NAMESPACE_COLLISION' : 'ACCEPTED',
    failures: injectedFailures,
    blenderProcessStarts: 0,
    expectedBlenderProcessStarts: 0,
    guardFunction: 'launchOverrideFailures',
  });

  const officialBefore = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const configRuntimeRoot = resolve(evidenceRoot, 'runtime-config');
  await mkdir(configRuntimeRoot, { recursive: false });
  const configAdmission = await writeAdmission({
    path: resolve(configRuntimeRoot, 'admission.json'),
    label: 'configuration-save-reset',
    workspace,
    source,
    artifact: binary,
  });
  if (configAdmission.status !== 'ACCEPTED') {
    throw new Error(`Configuration runtime blocked: ${configAdmission.failures.join(',')}`);
  }
  const configExpression = [
    'import bpy, json',
    "kinds = ('CONFIG', 'SCRIPTS', 'DATAFILES', 'EXTENSIONS')",
    'paths = {kind: bpy.utils.user_resource(kind, create=True) for kind in kinds}',
    'print("F0_CONFIG_PATHS=" + json.dumps(paths, sort_keys=True), flush=True)',
    'bpy.context.preferences.view.show_splash = not bpy.context.preferences.view.show_splash',
    'saved = bpy.ops.wm.save_userpref()',
    'reset = bpy.ops.wm.read_factory_userpref()',
    'saved_after_reset = bpy.ops.wm.save_userpref()',
    'print("F0_CONFIG_ACTIONS=" + json.dumps({"saved": sorted(saved), "reset": sorted(reset), "savedAfterReset": sorted(saved_after_reset)}, sort_keys=True), flush=True)',
  ].join('; ');
  const configStartedAt = new Date().toISOString();
  const configResult = await runTimed({
    command: binary,
    args: ['--background', '--python-expr', configExpression],
    cwd: resolve(workspace, 'build-f0.2-identity'),
    stageRoot: configRuntimeRoot,
    timeoutMs: MAX_RUNTIME_MS,
  });
  const configEndedAt = new Date().toISOString();
  const configLogs = await logIdentity(repositoryRoot, configResult);
  const combinedConfigOutput = `${configLogs.stdout}\n${configLogs.stderr}`;
  const paths = parseMarker(combinedConfigOutput, 'F0_CONFIG_PATHS=');
  const actions = parseMarker(combinedConfigOutput, 'F0_CONFIG_ACTIONS=');
  const actionsSucceeded =
    actions !== null &&
    ['saved', 'reset', 'savedAfterReset'].every(name => actions[name]?.includes('FINISHED'));
  const officialAfterConfig = await treeIdentity(OFFICIAL_CONFIG_ROOT);
  const f0AfterConfig = await treeIdentity(EXPECTED_F0_ROOT);
  const configReceipt = await writeJsonExclusive(resolve(configRuntimeRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0IdentityRuntimeReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status: configResult.exitCode === 0 && paths && actionsSucceeded ? 'PASS' : 'FAIL',
    startedAt: configStartedAt,
    endedAt: configEndedAt,
    admissionReceiptHash: configAdmission.receiptHash,
    command: configResult.command,
    process: {
      pid: configResult.pid,
      exitCode: configResult.exitCode,
      signal: configResult.signal,
      timedOut: configResult.timedOut,
      spawnError: configResult.spawnError,
      elapsedSeconds: configResult.elapsedSeconds,
      timing: configLogs.timing,
    },
    resolvedPaths: paths,
    actions,
    actionsSucceeded,
    logs: configLogs.files,
  });

  const guiRoot = resolve(evidenceRoot, 'runtime-gui');
  await mkdir(guiRoot, { recursive: false });
  const screenshotPath = resolve(evidenceRoot, 'screenshots', 'app-splash.png');
  const screenshotScript = resolve(evidenceRoot, 'screenshots', 'capture-app-splash.py');
  if (await exists(screenshotPath)) throw new Error(`Screenshot already exists: ${screenshotPath}`);
  await writeTextExclusive(screenshotScript, [
    'import bpy',
    '',
    `SCREENSHOT_PATH = ${JSON.stringify(screenshotPath)}`,
    '',
    'def capture_and_exit():',
    '    try:',
    '        result = bpy.ops.screen.screenshot(filepath=SCREENSHOT_PATH)',
    '        print(f"F0_SCREENSHOT_RESULT={sorted(result)}", flush=True)',
    '    finally:',
    '        bpy.ops.wm.quit_blender()',
    '    return None',
    '',
    'bpy.app.timers.register(capture_and_exit, first_interval=4.0)',
    '',
  ].join('\n'));
  const guiAdmission = await writeAdmission({
    path: resolve(guiRoot, 'admission.json'),
    label: 'gui-splash-screenshot',
    workspace,
    source,
    artifact: binary,
  });
  if (guiAdmission.status !== 'ACCEPTED') {
    throw new Error(`GUI runtime blocked: ${guiAdmission.failures.join(',')}`);
  }
  const guiStartedAt = new Date().toISOString();
  const guiResult = await runTimed({
    command: binary,
    args: ['--python', screenshotScript],
    cwd: resolve(workspace, 'build-f0.2-identity'),
    stageRoot: guiRoot,
    timeoutMs: MAX_RUNTIME_MS,
  });
  const guiEndedAt = new Date().toISOString();
  const guiLogs = await logIdentity(repositoryRoot, guiResult);
  const screenshotExists = await exists(screenshotPath);
  const screenshotBytes = screenshotExists ? await readFile(screenshotPath) : null;
  const guiReceipt = await writeJsonExclusive(resolve(guiRoot, 'receipt.json'), {
    schemaVersion: 'bfs.f0IdentityGuiReceipt.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status: guiResult.exitCode === 0 && screenshotExists ? 'PASS' : 'FAIL',
    startedAt: guiStartedAt,
    endedAt: guiEndedAt,
    admissionReceiptHash: guiAdmission.receiptHash,
    command: guiResult.command,
    process: {
      pid: guiResult.pid,
      exitCode: guiResult.exitCode,
      signal: guiResult.signal,
      timedOut: guiResult.timedOut,
      spawnError: guiResult.spawnError,
      elapsedSeconds: guiResult.elapsedSeconds,
      timing: guiLogs.timing,
    },
    screenshot: screenshotExists ? {
      path: relative(repositoryRoot, screenshotPath),
      bytes: screenshotBytes.length,
      sha256: sha256Bytes(screenshotBytes),
      dimensions: pngDimensions(screenshotBytes),
    } : null,
    logs: guiLogs.files,
  });
  const officialAfterAll = await treeIdentity(OFFICIAL_CONFIG_ROOT);

  const topbarText = await readFile(topbar, 'utf8');
  const sourceIcon = resolve(source, 'release', 'darwin', 'Blender.app', 'Contents', 'Resources', 'blender_icon_legacy.icns');
  const sourceSplash = resolve(source, 'release', 'datafiles', 'splash.png');
  const bundleChecks = {
    physicalBundleName: basename(app) === `${PRODUCT_NAME}.app`,
    bundleName: plistRaw(plist, 'CFBundleName') === PRODUCT_NAME,
    bundleDisplayName: plistRaw(plist, 'CFBundleDisplayName') === PRODUCT_NAME,
    bundleIdentifier: plistRaw(plist, 'CFBundleIdentifier') === BUNDLE_ID,
    liquidGlassIconKeyRemoved: plistRaw(plist, 'CFBundleIconName') === null,
    thumbnailerName: plistRaw(thumbnailPlist, 'CFBundleDisplayName') === `${PRODUCT_NAME} Thumbnailer`,
    thumbnailerBundleIdentifier: plistRaw(thumbnailPlist, 'CFBundleIdentifier') === THUMBNAILER_BUNDLE_ID,
    topbarProductName: topbarText.includes('text="Film Studio Engine F0"') && topbarText.includes('bl_label = "Film Studio Engine F0"'),
    iconMatchesIdentitySource: await sha256File(icon) === await sha256File(sourceIcon),
    sourceSplashMatchesProvenance: await sha256File(sourceSplash) === '5d8b343b125aca7161dcf4e753b9fb39498c182667aa522252dcd9a9f56982cf',
    runtimeReportsProductName: combinedConfigOutput.includes('Film Studio Engine F0 5.2.0'),
    runtimeReportsIdentityCommit: combinedConfigOutput.includes(IDENTITY_COMMIT) || combinedConfigOutput.includes(IDENTITY_COMMIT.slice(0, 12)),
  };
  const bundleStatus = Object.values(bundleChecks).every(Boolean) ? 'PASS' : 'FAIL';
  const bundleInspection = await writeJsonExclusive(resolve(evidenceRoot, 'bundle-inspection.json'), {
    schemaVersion: 'bfs.f0BundleInspection.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status: bundleStatus,
    observedAt: new Date().toISOString(),
    app,
    plist: {
      CFBundleExecutable: plistRaw(plist, 'CFBundleExecutable'),
      CFBundleName: plistRaw(plist, 'CFBundleName'),
      CFBundleDisplayName: plistRaw(plist, 'CFBundleDisplayName'),
      CFBundleIdentifier: plistRaw(plist, 'CFBundleIdentifier'),
      CFBundleGetInfoString: plistRaw(plist, 'CFBundleGetInfoString'),
      CFBundleIconFile: plistRaw(plist, 'CFBundleIconFile'),
      CFBundleIconName: plistRaw(plist, 'CFBundleIconName'),
    },
    thumbnailer: {
      CFBundleName: plistRaw(thumbnailPlist, 'CFBundleName'),
      CFBundleDisplayName: plistRaw(thumbnailPlist, 'CFBundleDisplayName'),
      CFBundleIdentifier: plistRaw(thumbnailPlist, 'CFBundleIdentifier'),
    },
    artifacts: {
      binary: { path: binary, bytes: (await stat(binary)).size, sha256: await sha256File(binary) },
      icon: { path: icon, bytes: (await stat(icon)).size, sha256: await sha256File(icon) },
      sourceIcon: { path: sourceIcon, sha256: await sha256File(sourceIcon) },
      sourceSplash: { path: sourceSplash, sha256: await sha256File(sourceSplash) },
      topbar: { path: topbar, sha256: await sha256File(topbar) },
    },
    checks: bundleChecks,
  });

  const expectedPaths = {
    CONFIG: `${EXPECTED_F0_ROOT}/config`,
    SCRIPTS: `${EXPECTED_F0_ROOT}/scripts`,
    DATAFILES: `${EXPECTED_F0_ROOT}/datafiles`,
    EXTENSIONS: `${EXPECTED_F0_ROOT}/extensions`,
  };
  const configChecks = {
    configRuntimePassed: configReceipt.status === 'PASS',
    resolvedPathsExact:
      paths !== null &&
      Object.entries(expectedPaths).every(([name, expected]) => paths[name] === expected),
    f0ConfigurationRootCreated: f0AfterConfig.state === 'PRESENT',
    officialStateUnchangedAfterSaveReset:
      officialBefore.state === officialAfterConfig.state && officialBefore.digest === officialAfterConfig.digest,
    officialStateUnchangedAfterGui:
      officialBefore.state === officialAfterAll.state && officialBefore.digest === officialAfterAll.digest,
    negativeControlPassed: negative.status === 'PASS' && negative.blenderProcessStarts === 0,
    guiScreenshotPassed: guiReceipt.status === 'PASS',
  };
  const configurationStatus = Object.values(configChecks).every(Boolean) ? 'PASS' : 'FAIL';
  const configuration = await writeJsonExclusive(resolve(evidenceRoot, 'configuration-isolation.json'), {
    schemaVersion: 'bfs.f0ConfigurationIsolation.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status: configurationStatus,
    observedAt: new Date().toISOString(),
    configurationNamespace: CONFIG_NAMESPACE,
    expectedF0Root: EXPECTED_F0_ROOT,
    expectedPaths,
    resolvedPaths: paths,
    actions,
    official: {
      before: officialBefore,
      afterConfigurationSaveAndReset: officialAfterConfig,
      afterAllF0Launches: officialAfterAll,
    },
    f0AfterConfigurationSaveAndReset: f0AfterConfig,
    crossBindings: {
      configRuntimeReceiptHash: configReceipt.receiptHash,
      guiRuntimeReceiptHash: guiReceipt.receiptHash,
      negativeControlReceiptHash: negative.receiptHash,
    },
    checks: configChecks,
  });
  const status = bundleStatus === 'PASS' && configurationStatus === 'PASS' ? 'PASS' : 'FAIL';
  await writeJsonExclusive(resolve(evidenceRoot, 'audit-summary.json'), {
    schemaVersion: 'bfs.f0IdentityAuditSummary.v0.1',
    protocol: 'F0-SOURCE-FEASIBILITY',
    gate: 'F0.2',
    status,
    observedAt: new Date().toISOString(),
    crossBindings: {
      bundleInspectionReceiptHash: bundleInspection.receiptHash,
      configurationIsolationReceiptHash: configuration.receiptHash,
      negativeControlReceiptHash: negative.receiptHash,
      configRuntimeReceiptHash: configReceipt.receiptHash,
      guiRuntimeReceiptHash: guiReceipt.receiptHash,
    },
    checks: {
      bundleInspection: bundleStatus === 'PASS',
      configurationIsolation: configurationStatus === 'PASS',
    },
  });
  process.stdout.write(`F0_IDENTITY_AUDIT_${status} app=${app} screenshot=${screenshotExists}\n`);
  if (status !== 'PASS') process.exitCode = 1;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  for (const required of ['stage', 'source', 'workspace', 'evidence-root']) {
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
  if (relative(evidenceBase, evidenceRoot).startsWith('..')) {
    throw new Error('Evidence root must stay under experiments/ai-native-studio-f0');
  }
  if (!relative(repositoryRoot, workspace).startsWith('..')) {
    throw new Error('External workspace must stay outside the research repository');
  }
  if (relative(workspace, source).startsWith('..')) {
    throw new Error('Source must stay inside the external workspace');
  }
  if (args.stage === 'build') {
    await runBuild({ repositoryRoot, evidenceRoot, workspace, source });
  } else if (args.stage === 'audit') {
    await runAudit({ repositoryRoot, evidenceRoot, workspace, source });
  } else {
    throw new Error(`Unsupported --stage ${args.stage}`);
  }
}

main().catch(error => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
