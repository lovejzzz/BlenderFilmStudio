import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB39Evidence, readB39Spec, runB39AnalyzerAttacks } from './lib/b39-linux-worker-architecture-preflight.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/linux-worker-architecture-preflight-v0-1');
const result = JSON.parse(await readFile(resolve(experimentRoot, 'results.json'), 'utf8'));
const spec = await readB39Spec();
const analysis = analyzeB39Evidence(result, spec);
const attacks = runB39AnalyzerAttacks(result, spec);
const audit = {
  schemaVersion: 'bfs.linuxWorkerArchitecturePreflightIndependentAudit.v0.1',
  experimentId: 'B39',
  analysis,
  attacks,
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed
    && attacks.length === spec.frozenAnalyzerAttacks.length
    && attacks.every(attack => attack.passed)
    && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(experimentRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B39_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} attacks=${attacks.filter(attack => attack.passed).length}/15 runtimeOps=${result.runtimeOperationsExecuted.length}\n`);
if (!audit.passed) process.exitCode = 1;
