import { createReadStream } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { analyzeB36, runB36AnalyzerAttacks } from './lib/b36-autoexec-boundary.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/autoexec-boundary-v0-1');
const resultsPath = resolve(experimentRoot, 'results.json');
const auditPath = resolve(experimentRoot, 'audit.json');
const result = JSON.parse(await readFile(resultsPath, 'utf8'));
const fileSha256 = path => new Promise((acceptPromise, rejectPromise) => {
  const hash = createHash('sha256');
  const stream = createReadStream(path);
  stream.on('data', chunk => hash.update(chunk));
  stream.on('error', rejectPromise);
  stream.on('end', () => acceptPromise(hash.digest('hex')));
});
const sourcePath = resolve(repositoryRoot, result.sourceBlendPath);
const observedSourceSha256 = await fileSha256(sourcePath);
const analysis = analyzeB36(result);
const attacks = runB36AnalyzerAttacks(result);
const audit = {
  schemaVersion: 'bfs.autoexecBoundaryIndependentAudit.v0.1',
  experimentId: 'B36',
  observedSourceSha256,
  sourceMatchesRecordedPreAndPost: observedSourceSha256 === result.sourceBlendSha256Pre && observedSourceSha256 === result.sourceBlendSha256Post,
  analysis,
  attacks,
  passed: analysis.passed && attacks.length === 7 && attacks.every(attack => attack.passed),
};
await writeFile(auditPath, `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(
  `BFS_B36_AUDIT ${audit.passed ? 'PASS' : 'FAIL'} cells=${result.cells.length} `
  + `sourceExact=${audit.sourceMatchesRecordedPreAndPost} attacks=${attacks.filter(attack => attack.passed).length}/7\n`,
);
if (!audit.passed) process.exitCode = 1;
