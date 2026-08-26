#!/usr/bin/env node
import {
  DEFAULT_PROJECTED_WRITE_GIB,
  DEFAULT_RESERVE_GIB,
  checkDiskSpace,
  evaluateDiskSpace,
  gibToBytes,
} from './lib/disk-space-guard.mjs';

function parseArguments(argv) {
  const options = {
    target: process.cwd(),
    reserveGiB: process.env.BFS_DISK_RESERVE_GIB ?? DEFAULT_RESERVE_GIB,
    projectedWriteGiB: process.env.BFS_PROJECTED_WRITE_GIB ?? DEFAULT_PROJECTED_WRITE_GIB,
    selfTest: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--self-test') options.selfTest = true;
    else if (argument === '--target') options.target = argv[++index];
    else if (argument === '--reserve-gib') options.reserveGiB = argv[++index];
    else if (argument === '--projected-gib') options.projectedWriteGiB = argv[++index];
    else throw new Error(`Unknown argument: ${argument}`);
  }

  return options;
}

function runSelfTest() {
  const base = {
    capacityBytes: gibToBytes(926),
    reserveBytes: gibToBytes(100),
    projectedWriteBytes: gibToBytes(20),
    target: '/test-volume',
  };
  const pass = evaluateDiskSpace({ ...base, availableBytes: gibToBytes(140) });
  const blocked = evaluateDiskSpace({ ...base, availableBytes: gibToBytes(119) });
  if (pass.status !== 'PASS' || blocked.status !== 'BLOCKED') {
    throw new Error('Disk guard self-test failed');
  }
  return {
    documentType: 'BFS_DISK_SPACE_GUARD_SELF_TEST',
    version: '0.1.0',
    status: 'PASS',
    cases: [pass.status, blocked.status],
  };
}

try {
  const options = parseArguments(process.argv.slice(2));
  const result = options.selfTest ? runSelfTest() : await checkDiskSpace(options);
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (result.status === 'BLOCKED') process.exitCode = 75;
} catch (error) {
  process.stderr.write(`BFS_DISK_GUARD_ERROR ${error.message}\n`);
  process.exitCode = 64;
}
