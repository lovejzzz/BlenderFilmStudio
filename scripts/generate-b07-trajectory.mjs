import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';

const evaluationUri = 'experiments/physics-v0-1/B06.final-evaluation.json';
const evaluationPath = resolve(repositoryRoot, evaluationUri);
const bytes = await readFile(evaluationPath);
const evaluation = JSON.parse(bytes.toString('utf8'));
if (!evaluation.passed || evaluation.trajectory.length !== 132) throw new Error('B06 source evaluation must pass its individual gates and contain 132 samples');
const sha256 = value => createHash('sha256').update(value).digest('hex');
const document = {
  documentType: 'BFS_TRAJECTORY_SPEC', specVersion: '0.1.0', id: 'TRAJECTORY_B07_CANONICAL', targetObject: 'B06_PROP',
  frameRate: { numerator: 24, denominator: 1 }, frameStart: 1, frameEnd: 132, space: 'WORLD',
  source: { experiment: 'B06_PHYSICS_V0_1', structureSha256: 'e18e4d1d15f9f97890354ce5807f4bdce6ed9c74b507e17c8df0c77d14fdfb6e', evaluationUri, evaluationSha256: sha256(bytes) },
  samples: evaluation.trajectory.map(row => ({ frame: row.frame, locationM: row.propCentreWorldM, rotationQuaternionWxyz: row.propRotationQuaternion })),
  acceptance: { maxReplayPositionErrorM: 1e-7, maxReplayRotationErrorDeg: 1e-5 },
  selectionStatus: 'TECHNICAL_CANONICAL_CANDIDATE_NOT_HUMAN_APPROVED',
  security: { networkAccess: false, executableCode: false },
};
const output = resolve(repositoryRoot, 'specs/benchmarks/B07.trajectory.json');
const serialized = `${JSON.stringify(document, null, 2)}\n`;
await writeFile(output, serialized);
process.stdout.write(`B07_TRAJECTORY_WRITTEN ${sha256(serialized)} ${output}\n`);
