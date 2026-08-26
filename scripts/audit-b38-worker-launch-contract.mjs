import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB38Evidence, readB38Spec, runB38AnalyzerAttacks } from './lib/b38-worker-launch-contract.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/worker-launch-contract-v0-1');
const result = JSON.parse(await readFile(resolve(experimentRoot, 'results.json'), 'utf8'));
const spec = await readB38Spec();
const analysis = analyzeB38Evidence(result, spec);
const attacks = runB38AnalyzerAttacks(result, spec);
const audit = {
  schemaVersion: 'bfs.workerLaunchContractIndependentAudit.v0.1',
  experimentId: 'B38',
  analysis,
  attacks,
  recordedAttacksMatch: JSON.stringify(attacks) === JSON.stringify(result.attacks),
  passed: analysis.passed && attacks.length === spec.frozenAnalyzerAttacks.length
    && attacks.every(attack => attack.passed) && JSON.stringify(attacks) === JSON.stringify(result.attacks),
};
await writeFile(resolve(experimentRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B38_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} fixtures=${result.fixtures.length} attacks=${attacks.filter(attack => attack.passed).length}/25\n`);
if (!audit.passed) process.exitCode = 1;
