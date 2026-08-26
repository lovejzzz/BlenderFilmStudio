import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { readB40C2Spec } from './lib/b40-c2-serialization-stability.mjs';
import { analyzeB40C3Evidence, readB40C3Spec, roundTripB40C2, runB40C3Attacks } from './lib/b40-c3-failure-projection.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-4');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const c3Spec = await readB40C3Spec();
const c2Spec = await readB40C2Spec();
const baseSpec = await readB40Spec();
const analysis = await analyzeB40C3Evidence(result, c3Spec, c2Spec, baseSpec);
const attacks = await runB40C3Attacks(result, c3Spec, c2Spec, baseSpec);
const roundTrip = roundTripB40C2(result);
const roundTripAnalysis = await analyzeB40C3Evidence(roundTrip, c3Spec, c2Spec, baseSpec);
const roundTripAttacks = await runB40C3Attacks(roundTrip, c3Spec, c2Spec, baseSpec);
const audit = {
  schemaVersion: 'bfs.workerHostCapacityIndependentAudit.v0.4', experimentId: 'B40-C3', analysis, attacks,
  roundTripAnalysisEqual: JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis),
  roundTripAttackVectorEqual: JSON.stringify(attacks) === JSON.stringify(roundTripAttacks),
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === 14 && attacks.every(attack => attack.passed)
    && JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis)
    && JSON.stringify(attacks) === JSON.stringify(roundTripAttacks)
    && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B40_C3_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} blockers=${result.decision.reasons.length} attacks=${attacks.filter(a => a.passed).length}/14 replay=${audit.roundTripAttackVectorEqual ? 'PASS' : 'FAIL'} runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
