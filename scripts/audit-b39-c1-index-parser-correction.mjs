import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB39C1Evidence, readB39C1Spec, runB39C1Attacks } from './lib/b39-c1-index-parser-correction.mjs';

const root = resolve(repositoryRoot, 'experiments/linux-worker-architecture-preflight-v0-2');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const spec = await readB39C1Spec();
const analysis = analyzeB39C1Evidence(result, spec);
const attacks = runB39C1Attacks(result, spec);
const audit = {
  schemaVersion: 'bfs.linuxWorkerArchitecturePreflightIndependentAudit.v0.2',
  experimentId: 'B39-C1',
  analysis,
  attacks,
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === 15 && attacks.every(attack => attack.passed) && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B39_C1_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} attacks=${attacks.filter(a => a.passed).length}/15 runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
