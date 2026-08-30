#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { statfsSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((rows, item, index, all) => item.startsWith('--') ? [...rows, [item.slice(2), all[index + 1]]] : rows, []));
if (!args.root || !args.id || !args.output || !args.sequence) throw new Error('Usage: --root <evidence> --id <id> --output <path-or-NONE> --sequence <1..5>');
const root = resolve(args.root);
const filesystem = statfsSync(root, { bigint: true });
const freeBytes = filesystem.bavail * filesystem.bsize;
const requiredBytes = 160n * 1024n ** 3n;
let running = [];
try { running = execFileSync('/usr/bin/pgrep', ['-x', 'Blender'], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean); } catch {}
const outputAbsent = args.output === 'NONE' ? true : !await import('node:fs').then(fs => fs.existsSync(resolve(args.output)));
const body = {
  schemaVersion: 'bfs.f0.4.productStartAdmission.v0.1', id: args.id, formalProductStart: Number(args.sequence),
  status: freeBytes >= requiredBytes && running.length === 0 && outputAbsent ? 'ACCEPTED' : 'REJECTED',
  freeBytes: String(freeBytes), requiredBytes: String(requiredBytes), runningBlenderPidsBefore: running,
  maximumConcurrentProductProcesses: 1, output: args.output, outputAbsentBefore: outputAbsent,
};
body.admissionHash = createHash('sha256').update(JSON.stringify(Object.fromEntries(Object.entries(body).sort()))).digest('hex');
writeFileSync(resolve(root, 'admissions', `${args.id}.json`), `${JSON.stringify(body, null, 2)}\n`, { flag: 'wx' });
console.log(`F04_ADMISSION ${body.status} ${args.id} free=${body.freeBytes}`);
if (body.status !== 'ACCEPTED') process.exitCode = 1;
