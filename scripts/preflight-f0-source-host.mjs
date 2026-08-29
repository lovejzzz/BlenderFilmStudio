#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { statfsSync } from 'node:fs';
import os from 'node:os';
import process from 'node:process';

const GiB = 1024n ** 3n;
const reservedFreeGiB = 100;
const projectedWritesGiB = 60;
const requiredFreeGiB = reservedFreeGiB + projectedWritesGiB;

function command(name, args = ['--version']) {
  try {
    const path = execFileSync('/usr/bin/env', ['sh', '-c', `command -v ${name}`], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim();
    const version = execFileSync(path, args, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim().split('\n')[0];
    return { found: true, path, version };
  } catch (error) {
    return {
      found: false,
      path: null,
      version: null,
      error: error instanceof Error ? error.message.split('\n')[0] : String(error),
    };
  }
}

function majorMinor(version) {
  const match = version.match(/v?(\d+)\.(\d+)/);
  return match ? [Number(match[1]), Number(match[2])] : [0, 0];
}

const tools = {
  git: command('git'),
  gitLfs: command('git-lfs'),
  cmake: command('cmake'),
  ninja: command('ninja'),
  python3: command('python3'),
  make: command('make'),
  svn: command('svn', ['--version', '--quiet']),
  clang: command('clang'),
  xcodeSelect: command('xcode-select', ['-p']),
};
const requiredToolNames = ['git', 'gitLfs', 'cmake', 'python3', 'make', 'clang', 'xcodeSelect'];

const stat = statfsSync(process.cwd(), { bigint: true });
const freeBytes = stat.bavail * stat.bsize;
const freeGiB = Number(freeBytes / GiB);
const memoryGiB = Number(BigInt(os.totalmem()) / GiB);
const [nodeMajor, nodeMinor] = majorMinor(process.version);
const failures = [];
const warnings = [];

if (process.platform !== 'darwin') failures.push(`platform must be darwin, observed ${process.platform}`);
if (process.arch !== 'arm64') failures.push(`architecture must be arm64, observed ${process.arch}`);
if (nodeMajor < 22 || (nodeMajor === 22 && nodeMinor < 13)) {
  failures.push(`Node.js must be >=22.13.0, observed ${process.version}`);
}
for (const name of requiredToolNames) {
  if (!tools[name].found) failures.push(`required tool not found: ${name}`);
}
if (!tools.ninja.found) warnings.push('ninja is optional; Blender can use the default build generator');
if (!tools.svn.found) warnings.push('svn is not listed as a current macOS prerequisite; record it only if a dependency step requests it');
if (freeGiB < requiredFreeGiB) {
  failures.push(`free disk must be >=${requiredFreeGiB} GiB, observed ${freeGiB} GiB`);
}
if (memoryGiB < 16) failures.push(`physical memory must be >=16 GiB, observed ${memoryGiB} GiB`);
if (memoryGiB < 32) warnings.push('32 GiB or more is recommended for faster native builds and Cycles tests');

const receipt = {
  schemaVersion: '0.1.0',
  protocol: 'F0-SOURCE-FEASIBILITY',
  gate: 'F0.1',
  status: failures.length === 0 ? 'F0_HOST_PREFLIGHT_ACCEPTED' : 'F0_HOST_PREFLIGHT_BLOCKED',
  observedAt: new Date().toISOString(),
  readOnly: true,
  host: {
    hostname: os.hostname(),
    platform: process.platform,
    release: os.release(),
    architecture: process.arch,
    cpuModel: os.cpus()[0]?.model ?? null,
    logicalCpuCount: os.cpus().length,
    memoryGiB,
    node: process.version,
  },
  disk: {
    checkedPath: process.cwd(),
    freeBytes: freeBytes.toString(),
    freeGiB,
    reservedFreeGiB,
    projectedWritesGiB,
    requiredFreeGiB,
  },
  tools,
  sourceBaseline: {
    tag: 'v5.2.0',
    commit: 'fbe6228777e7d9afefcd61a413844e790ae75db7',
  },
  failures,
  warnings,
  note: 'This is a read-only host screen, not the just-in-time admission for a build.',
};

process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
process.exitCode = failures.length === 0 ? 0 : 2;
