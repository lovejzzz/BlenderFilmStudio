import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB40Evidence, readB40Spec, runB40Attacks } from './lib/b40-worker-host-capacity-admission.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-1');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const spec = await readB40Spec();
const analysis = analyzeB40Evidence(result, spec);
const attacks = runB40Attacks(result, spec);
const audit = {
  schemaVersion: 'bfs.workerHostCapacityIndependentAudit.v0.1',
  experimentId: 'B40',
  analysis,
  attacks,
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === 14 && attacks.every(attack => attack.passed) && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B40_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} blockers=${result.decision.reasons.length} attacks=${attacks.filter(a => a.passed).length}/14 runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
