import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { analyzeB40C1Evidence, readB40C1Spec, runB40C1Attacks } from './lib/b40-c1-binfmt-parser-correction.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-2');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const correctionSpec = await readB40C1Spec();
const baseSpec = await readB40Spec();
const analysis = await analyzeB40C1Evidence(result, correctionSpec, baseSpec);
const attacks = await runB40C1Attacks(result, correctionSpec, baseSpec);
const audit = {
  schemaVersion: 'bfs.workerHostCapacityIndependentAudit.v0.2', experimentId: 'B40-C1', analysis, attacks,
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === 14 && attacks.every(attack => attack.passed) && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B40_C1_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} blockers=${result.decision.reasons.length} attacks=${attacks.filter(a => a.passed).length}/14 runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
