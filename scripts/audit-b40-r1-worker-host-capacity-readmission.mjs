import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { analyzeB40R1Evidence, readB40R1Spec, roundTripB40R1, runB40R1Attacks } from './lib/b40-r1-worker-host-capacity-readmission.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-readmission-v0-1');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const spec = await readB40R1Spec();
const baseSpec = await readB40Spec();
const analysis = await analyzeB40R1Evidence(result, spec, baseSpec);
const attacks = await runB40R1Attacks(result, spec, baseSpec);
const roundTrip = roundTripB40R1(result);
const roundTripAnalysis = await analyzeB40R1Evidence(roundTrip, spec, baseSpec);
const roundTripAttacks = await runB40R1Attacks(roundTrip, spec, baseSpec);
const audit = {
  schemaVersion: 'bfs.workerHostCapacityReadmissionIndependentAudit.v0.1', experimentId: 'B40-R1', analysis, attacks,
  roundTripAnalysisEqual: JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis),
  roundTripAttackVectorEqual: JSON.stringify(attacks) === JSON.stringify(roundTripAttacks),
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === 16 && attacks.every(attack => attack.passed)
    && JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis)
    && JSON.stringify(attacks) === JSON.stringify(roundTripAttacks)
    && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B40_R1_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} blockers=${result.decision.reasons.length} attacks=${attacks.filter(a => a.passed).length}/16 replay=${audit.roundTripAttackVectorEqual ? 'PASS' : 'FAIL'} runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
