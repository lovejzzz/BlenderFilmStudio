import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB37, runB37AnalyzerAttacks } from './lib/b37-worker-containment.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/worker-containment-v0-1');
const result = JSON.parse(await readFile(resolve(experimentRoot, 'results.json'), 'utf8'));
const analysis = analyzeB37(result);
const attacks = runB37AnalyzerAttacks(result);
const audit = {
  schemaVersion: 'bfs.workerContainmentIndependentAudit.v0.1',
  experimentId: 'B37',
  analysis,
  attacks,
  passed: analysis.passed && attacks.length === 9 && attacks.every(attack => attack.passed),
};
await writeFile(resolve(experimentRoot, 'audit.json'), `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B37_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} cells=${result.cells.length} attacks=${attacks.filter(attack => attack.passed).length}/9\n`);
if (!audit.passed) process.exitCode = 1;
