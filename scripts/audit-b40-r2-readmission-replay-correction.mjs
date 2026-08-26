import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { canonicalJson } from './lib/receipt-format.mjs';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { readB40Spec } from './lib/b40-worker-host-capacity-admission.mjs';
import { readB40R1Spec } from './lib/b40-r1-worker-host-capacity-readmission.mjs';
import { analyzeB40R2Evidence, readB40R2Spec, roundTripB40R2, runB40R2Attacks } from './lib/b40-r2-readmission-replay-correction.mjs';

const root = resolve(repositoryRoot, 'experiments/worker-host-capacity-readmission-v0-2');
const result = JSON.parse(await readFile(resolve(root, 'results.json'), 'utf8'));
const r2Spec = await readB40R2Spec();
const r1Spec = await readB40R1Spec();
const baseSpec = await readB40Spec();
const analysis = await analyzeB40R2Evidence(result, r2Spec, r1Spec, baseSpec);
const attacks = await runB40R2Attacks(result, r2Spec, r1Spec, baseSpec);
const roundTrip = roundTripB40R2(result);
const roundTripAnalysis = await analyzeB40R2Evidence(roundTrip, r2Spec, r1Spec, baseSpec);
const roundTripAttacks = await runB40R2Attacks(roundTrip, r2Spec, r1Spec, baseSpec);
const audit = {
  schemaVersion: 'bfs.workerHostCapacityReadmissionIndependentAudit.v0.2', experimentId: 'B40-R2', analysis, attacks,
  evidenceCanonicalEqual: canonicalJson(result) === canonicalJson(roundTrip),
  roundTripAnalysisEqual: canonicalJson(analysis) === canonicalJson(roundTripAnalysis),
  roundTripAttackVectorEqual: canonicalJson(attacks) === canonicalJson(roundTripAttacks),
  recordedAttacksMatch: canonicalJson(attacks) === canonicalJson(result.attacks),
  recordedDiagnosticsMatch: result.replayDiagnostics?.evidenceCanonicalEqual === (canonicalJson(result) === canonicalJson(roundTrip))
    && result.replayDiagnostics?.analysisEqual === (canonicalJson(analysis) === canonicalJson(roundTripAnalysis))
    && result.replayDiagnostics?.attackVectorEqual === (canonicalJson(attacks) === canonicalJson(roundTripAttacks)),
};
audit.passed = analysis.passed && attacks.length === 16 && attacks.every(attack => attack.passed)
  && audit.evidenceCanonicalEqual && audit.roundTripAnalysisEqual && audit.roundTripAttackVectorEqual
  && audit.recordedAttacksMatch && audit.recordedDiagnosticsMatch;
await writeFile(resolve(root, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B40_R2_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} blockers=${result.decision.reasons.length} attacks=${attacks.filter(a => a.passed).length}/16 replay=${audit.roundTripAttackVectorEqual ? 'PASS' : 'FAIL'} diagnostics=${audit.recordedDiagnosticsMatch ? 'MATCH' : 'MISMATCH'} runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
