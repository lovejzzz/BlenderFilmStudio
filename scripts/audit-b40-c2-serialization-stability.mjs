import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { analyzeB40C2Evidence, readB40C2Spec, roundTripB40C2, runB40C2Attacks } from './lib/b40-c2-serialization-stability.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-admission-v0-3');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const correctionSpec = await readB40C2Spec();
const baseSpec = await readB40Spec();
const analysis = await analyzeB40C2Evidence(result, correctionSpec, baseSpec);
const attacks = await runB40C2Attacks(result, correctionSpec, baseSpec);
const roundTrip = roundTripB40C2(result);
const roundTripAnalysis = await analyzeB40C2Evidence(roundTrip, correctionSpec, baseSpec);
const roundTripAttacks = await runB40C2Attacks(roundTrip, correctionSpec, baseSpec);
const audit = {
  schemaVersion: 'bfs.workerHostCapacityIndependentAudit.v0.3', experimentId: 'B40-C2', analysis, attacks,
  roundTripAnalysisEqual: JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis),
  roundTripAttackVectorEqual: JSON.stringify(attacks) === JSON.stringify(roundTripAttacks),
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === 14 && attacks.every(attack => attack.passed)
    && JSON.stringify(analysis) === JSON.stringify(roundTripAnalysis)
    && JSON.stringify(attacks) === JSON.stringify(roundTripAttacks)
    && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B40_C2_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} blockers=${result.decision.reasons.length} attacks=${attacks.filter(a => a.passed).length}/14 roundTrip=${audit.roundTripAttackVectorEqual ? 'PASS' : 'FAIL'} runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
