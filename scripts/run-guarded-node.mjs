#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { checkDiskSpace } from './lib/disk-space-guard.mjs';

const [script, ...args] = process.argv.slice(2);

if (!script) {
  process.stderr.write('Usage: node scripts/run-guarded-node.mjs <script> [args...]\n');
  process.exitCode = 64;
} else {
  const guard = await checkDiskSpace({ target: process.cwd() });
  process.stdout.write(`${JSON.stringify(guard)}\n`);

  if (guard.status === 'BLOCKED') {
    process.stderr.write('BFS_DISK_GUARD_BLOCKED: reclaim space or explicitly revise the reserve/projection policy before running this job.\n');
    process.exitCode = 75;
  } else {
    const child = spawn(process.execPath, [resolve(script), ...args], {
      cwd: process.cwd(),
      env: process.env,
      stdio: 'inherit',
    });
    child.on('error', error => {
      process.stderr.write(`BFS_GUARDED_RUN_ERROR ${error.message}\n`);
      process.exitCode = 70;
    });
    child.on('close', (code, signal) => {
      if (signal) {
        process.stderr.write(`BFS_GUARDED_RUN_SIGNAL ${signal}\n`);
        process.exitCode = 70;
      } else {
        process.exitCode = code ?? 70;
      }
    });
  }
}
