#!/usr/bin/env node

import { createHash } from 'node:crypto';
import {
  chmodSync, closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync,
  renameSync, statSync, unlinkSync, writeFileSync,
} from 'node:fs';
import { dirname, resolve } from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const specPath = resolve(repositoryRoot, 'specs/host-capacity-sentinel.v0.1.json');
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const sourcePlist = resolve(repositoryRoot, 'launchd/com.blenderfilmstudio.capacity-sentinel.plist');
const installedPlist = '/Users/tianxing/Library/LaunchAgents/com.blenderfilmstudio.capacity-sentinel.plist';
const serviceTarget = `gui/${process.getuid()}/${spec.schedule.launchdLabel}`;
const domainTarget = `gui/${process.getuid()}`;
const formalRoot = resolve(repositoryRoot, spec.formalRoot);
const canonical = value => Array.isArray(value)
  ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value);
const sha256 = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => sha256(readFileSync(path));
const withoutHash = value => { const copy = structuredClone(value); delete copy.selfHash; return copy; };
const seal = value => { value.selfHash = sha256(canonical(withoutHash(value))); return value; };
const sleep = ms => new Promise(resolveSleep => setTimeout(resolveSleep, ms));

function run(command, args, timeout = 10000) {
  const result = spawnSync(command, args, { cwd: repositoryRoot, encoding: 'utf8', timeout, maxBuffer: 1024 * 1024, env: { ...process.env, LC_ALL: 'C' } });
  return { exitCode: result.status, signal: result.signal || null, errorCode: result.error?.code || null, stdout: result.stdout || '', stderr: result.stderr || '' };
}

function writeExclusive(path, value, ceiling = 262144) {
  const text = `${JSON.stringify(seal(value), null, 2)}\n`;
  if (Buffer.byteLength(text) > ceiling) throw new Error(`receipt ceiling: ${path}`);
  const fd = openSync(path, 'wx', 0o644);
  try { writeFileSync(fd, text); fsyncSync(fd); } finally { closeSync(fd); }
  const directoryFd = openSync(dirname(path), 'r');
  try { fsyncSync(directoryFd); } finally { closeSync(directoryFd); }
  return { sha256: sha256(text), selfHash: value.selfHash, bytes: Buffer.byteLength(text) };
}

function installBytes() {
  const bytes = readFileSync(sourcePlist);
  const temporary = `${installedPlist}.tmp-${process.pid}`;
  const fd = openSync(temporary, 'wx', 0o644);
  try { writeFileSync(fd, bytes); fsyncSync(fd); } finally { closeSync(fd); }
  chmodSync(temporary, 0o644);
  try { renameSync(temporary, installedPlist); } catch (error) { try { unlinkSync(temporary); } catch {} throw error; }
  const directoryFd = openSync(dirname(installedPlist), 'r');
  try { fsyncSync(directoryFd); } finally { closeSync(directoryFd); }
}

function parsePlist(path) {
  const result = run('/usr/bin/plutil', ['-convert', 'json', '-o', '-', path]);
  if (result.exitCode !== 0) throw new Error(`plist parse failed: ${result.stderr.trim()}`);
  return JSON.parse(result.stdout);
}

function validateTemplate(plist) {
  const expectedArguments = [
    spec.runtime.nodeExecutable,
    `${spec.runtime.repositoryRoot}/scripts/host-capacity-sentinel.mjs`,
    '--quiet',
  ];
  return plist.Label === spec.schedule.launchdLabel
    && canonical(plist.ProgramArguments) === canonical(expectedArguments)
    && plist.WorkingDirectory === spec.runtime.repositoryRoot
    && plist.RunAtLoad === spec.schedule.runAtLoad
    && plist.StartInterval === spec.schedule.intervalSeconds
    && plist.StandardOutPath === '/dev/null' && plist.StandardErrorPath === '/dev/null';
}

function releaseIdentity() {
  const scoped = execFileSync('/usr/bin/git', ['status', '--short', '--', ...spec.releasePaths], { cwd: repositoryRoot, encoding: 'utf8' }).trim();
  const [head, origin] = execFileSync('/usr/bin/git', ['rev-parse', 'HEAD', 'origin/main'], { cwd: repositoryRoot, encoding: 'utf8' }).trim().split('\n');
  execFileSync('/usr/bin/git', ['merge-base', '--is-ancestor', spec.parentCommit, head], { cwd: repositoryRoot });
  return { scoped, head, origin };
}

async function waitForLatest(afterMs) {
  const path = resolve(spec.state.root, spec.state.latestFile);
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (existsSync(path) && statSync(path).mtimeMs >= afterMs) return path;
    await sleep(500);
  }
  throw new Error('sentinel did not produce a fresh live sample');
}

const mode = process.argv[2];
if (!['--dry-run', '--install', '--verify', '--uninstall'].includes(mode)) throw new Error('usage: install-host-capacity-sentinel.mjs --dry-run|--install|--verify|--uninstall');
const template = parsePlist(sourcePlist);
if (!validateTemplate(template)) throw new Error('launchd template does not match frozen spec');
if (process.getuid() !== 501) throw new Error('unexpected user id for frozen launchd domain');
if (shaFile(spec.runtime.nodeExecutable) !== spec.runtime.nodeSha256) throw new Error('node runtime hash mismatch');

if (mode === '--dry-run') {
  const git = releaseIdentity();
  process.stdout.write(`${JSON.stringify({ status: git.scoped || git.head !== git.origin ? 'BLOCKED_RELEASE' : 'READY', git, sourcePlist, installedPlist, serviceTarget, templateValid: true, formalRootAbsent: !existsSync(formalRoot), installedAbsent: !existsSync(installedPlist), stateRootAbsent: !existsSync(spec.state.root) }, null, 2)}\n`);
  process.exit(0);
}

if (mode === '--verify') {
  const service = run('/bin/launchctl', ['print', serviceTarget]);
  const latestPath = resolve(spec.state.root, spec.state.latestFile);
  process.stdout.write(`${JSON.stringify({ installed: existsSync(installedPlist), bytesExact: existsSync(installedPlist) && shaFile(installedPlist) === shaFile(sourcePlist), serviceLoaded: service.exitCode === 0, latestExists: existsSync(latestPath), serviceTarget }, null, 2)}\n`);
  process.exit(service.exitCode === 0 && existsSync(installedPlist) && existsSync(latestPath) ? 0 : 75);
}

if (mode === '--uninstall') {
  const bootout = run('/bin/launchctl', ['bootout', serviceTarget]);
  let removed = false;
  if (existsSync(installedPlist)) { unlinkSync(installedPlist); removed = true; }
  process.stdout.write(`${JSON.stringify({ status: 'UNINSTALLED', serviceTarget, bootoutExitCode: bootout.exitCode, plistRemoved: removed, stateRetained: existsSync(spec.state.root) })}\n`);
  process.exit(0);
}

if (existsSync(formalRoot) || existsSync(installedPlist) || existsSync(spec.state.root)) throw new Error('installation target is not fresh');
const git = releaseIdentity();
if (git.scoped || git.head !== git.origin) throw new Error('release identity preflight failed');
mkdirSync(formalRoot, { recursive: false });
const start = {
  schemaVersion: 'bfs.host-capacity-sentinel-install-start.v0.1', experimentId: spec.experimentId,
  startedAt: new Date().toISOString(), specSha256: shaFile(specPath), git,
  parentEvidence: { resultsSha256: shaFile(resolve(repositoryRoot, spec.parentEvidence.resultsPath)), auditSha256: shaFile(resolve(repositoryRoot, spec.parentEvidence.auditPath)) },
  targets: { sourcePlist, installedPlist, serviceTarget, stateRoot: spec.state.root }, selfHash: '',
};
const startReceipt = writeExclusive(resolve(formalRoot, 'start.json'), start);
let bootstrapped = false;
try {
  installBytes();
  const installedAt = Date.now();
  const bootstrap = run('/bin/launchctl', ['bootstrap', domainTarget, installedPlist]);
  if (bootstrap.exitCode !== 0) throw new Error(`launchctl bootstrap failed: ${bootstrap.stderr.trim()}`);
  bootstrapped = true;
  const firstLatestPath = await waitForLatest(installedAt);
  const firstLatestModifiedMs = statSync(firstLatestPath).mtimeMs;
  const kickstart = run('/bin/launchctl', ['kickstart', '-k', serviceTarget]);
  if (kickstart.exitCode !== 0) throw new Error(`launchctl kickstart failed: ${kickstart.stderr.trim()}`);
  const latestPath = await waitForLatest(firstLatestModifiedMs + 1);
  await sleep(1000);
  const historyPath = resolve(spec.state.root, spec.state.historyFile);
  const latestText = readFileSync(latestPath, 'utf8');
  const historyText = readFileSync(historyPath, 'utf8');
  const latest = JSON.parse(latestText);
  const history = JSON.parse(historyText);
  const service = run('/bin/launchctl', ['print', serviceTarget]);
  if (service.exitCode !== 0) throw new Error('installed service is not loaded');
  const install = {
    schemaVersion: 'bfs.host-capacity-sentinel-install.v0.1', experimentId: spec.experimentId,
    completedAt: new Date().toISOString(),
    startReceipt, installedPlist: { path: installedPlist, sha256: shaFile(installedPlist), bytes: statSync(installedPlist).size },
    service: { target: serviceTarget, loaded: true, printSha256: sha256(service.stdout), printBytes: Buffer.byteLength(service.stdout) },
    liveState: {
      latest: { path: latestPath, sha256: sha256(latestText), selfHash: latest.selfHash, bytes: Buffer.byteLength(latestText), severity: latest.classification?.severity },
      history: { path: historyPath, sha256: sha256(historyText), selfHash: history.selfHash, bytes: Buffer.byteLength(historyText), samples: history.samples?.length },
    },
    actions: { plistCreates: 1, bootstrapCalls: 1, kickstartCalls: 1, deletions: 0, cleanupOperations: 0, serviceRestarts: 0, dockerCalls: 0, blenderProcesses: 0, networkCalls: 0, modelCalls: 0 },
    reversible: { uninstallCommand: `${spec.runtime.nodeExecutable} ${spec.runtime.repositoryRoot}/scripts/install-host-capacity-sentinel.mjs --uninstall`, stateRetainedOnUninstall: true },
    selfHash: '',
  };
  writeExclusive(resolve(formalRoot, 'install.json'), install);
  process.stdout.write(`${JSON.stringify({ status: 'INSTALLED', severity: install.liveState.latest.severity, serviceTarget, installedPlist, formalRoot: spec.formalRoot })}\n`);
} catch (error) {
  if (bootstrapped) run('/bin/launchctl', ['bootout', serviceTarget]);
  if (existsSync(installedPlist)) unlinkSync(installedPlist);
  writeExclusive(resolve(formalRoot, 'failure.json'), { schemaVersion: 'bfs.host-capacity-sentinel-install-failure.v0.1', failedAt: new Date().toISOString(), error: error.message, rollback: { serviceBootedOut: bootstrapped, plistRemoved: !existsSync(installedPlist), stateRetained: existsSync(spec.state.root) }, selfHash: '' });
  throw error;
}
