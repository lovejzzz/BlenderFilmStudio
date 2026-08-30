#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync, readlinkSync, rmdirSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const repository = resolve(process.argv[2]);
const evidence = resolve(repository, 'experiments/ai-native-studio-f0/F0.7-2026-08-30-mac-m2max-attempt-02');
const staging = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/F0.7-packages-attempt-02/staging/Film Studio Engine F0.app';
const target = '/Users/mengyingli/Applications/Film Studio Engine F0.app';
const expectedDigest = 'c0deb1c7b27d0c4a8639e87235e0a8c94c484b1985c5e081add23d2651e8410a';
const expectedBinary = '58d5c984c58d986d3cf44622ad5876052a67890d0b077dafd4977f6e2b24a71d';
const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
function tree(root, ignoreRuntimeCache = false) {
  const rows = [];
  let files = 0;
  let directories = 0;
  let logicalBytes = 0;
  let ignoredRuntimePycFiles = 0;
  let ignoredRuntimePycacheDirectories = 0;
  const validateRuntimeCache = current => {
    ignoredRuntimePycacheDirectories += 1;
    for (const name of readdirSync(current)) {
      const candidate = resolve(current, name);
      const stat = lstatSync(candidate);
      if (stat.isDirectory() && !stat.isSymbolicLink()) validateRuntimeCache(candidate);
      else if (stat.isFile() && candidate.endsWith('.pyc')) ignoredRuntimePycFiles += 1;
      else throw new Error(`Non-runtime-cache content found in ignored __pycache__: ${candidate}`);
    }
  };
  const walk = (current, prefix = '') => {
    for (const name of readdirSync(current).sort((a, b) => a.localeCompare(b, 'en'))) {
      const path = resolve(current, name);
      const relative = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (ignoreRuntimeCache && stat.isDirectory() && name === '__pycache__') validateRuntimeCache(path);
      else if (stat.isDirectory()) { directories += 1; rows.push({ path: relative, type: 'directory', mode }); walk(path, relative); }
      else if (stat.isSymbolicLink()) rows.push({ path: relative, type: 'symlink', mode, target: readlinkSync(path) });
      else if (stat.isFile()) { files += 1; logicalBytes += stat.size; rows.push({ path: relative, type: 'file', mode, bytes: stat.size, sha256: shaFile(path) }); }
      else rows.push({ path: relative, type: 'other', mode, bytes: stat.size });
    }
  };
  walk(root);
  return { root, files, directories, logicalBytes, digest: shaBytes(`${rows.map(row => JSON.stringify(row)).join('\n')}\n`), ignoredRuntimePycFiles, ignoredRuntimePycacheDirectories };
}
function runningBlender() {
  try { return execFileSync('/usr/bin/pgrep', ['-x', 'Blender'], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean); } catch { return []; }
}
function removeTree(root) {
  if (resolve(root) !== target || dirname(resolve(root)) !== '/Users/mengyingli/Applications') throw new Error('Unsafe cleanup target');
  const walk = path => {
    for (const name of readdirSync(path)) {
      const candidate = resolve(path, name);
      const stat = lstatSync(candidate);
      if (stat.isDirectory() && !stat.isSymbolicLink()) { walk(candidate); rmdirSync(candidate); }
      else unlinkSync(candidate);
    }
  };
  walk(root);
  rmdirSync(root);
}
if (!existsSync(staging) || !existsSync(target)) throw new Error('Staging or exact generated target is missing');
const running = runningBlender();
if (running.length) throw new Error(`Blender is still running: ${running.join(',')}`);
const stagingBefore = tree(staging);
const targetBefore = tree(target);
const targetNormalized = tree(target, true);
if (stagingBefore.digest !== expectedDigest || targetNormalized.digest !== expectedDigest || shaFile(resolve(target, 'Contents/MacOS/Blender')) !== expectedBinary) throw new Error('Generated target differs from staging beyond isolated Python runtime caches');
removeTree(target);
if (existsSync(target)) throw new Error('Generated target remains after cleanup');
const body = {
  schemaVersion: 'bfs.f0.7.failureSafetyCleanup.v0.1', status: 'PASS',
  authorization: 'Previously approved exact generated install target uninstall; this is safety cleanup, not same-ID repair.',
  runningBlenderPidsBefore: running, stagingBefore, targetBefore, targetNormalized,
  allowedRuntimeCacheDrift: {
    pycFiles: targetNormalized.ignoredRuntimePycFiles,
    pycacheDirectories: targetNormalized.ignoredRuntimePycacheDirectories
  },
  exactTargetRemoved: target, targetAbsentAfter: !existsSync(target), stagingRetained: existsSync(staging),
};
writeFileSync(resolve(evidence, 'failure-cleanup.json'), `${JSON.stringify({ ...body, cleanupHash: prettyHash(body) }, null, 2)}\n`, { flag: 'wx' });
console.log(`F0.7 failure cleanup PASS removed=${target}`);
