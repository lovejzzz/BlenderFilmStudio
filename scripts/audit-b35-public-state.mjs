import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { auditB35PublicState } from './lib/b35-public-state-audit.mjs';

function argument(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-2');
const workRoot = resolve(experimentRoot, 'work');
const privateEvidenceRoot = resolve(workRoot, 'private-evidence');
const outputPath = resolve(argument('--output', resolve(privateEvidenceRoot, 'public-state-leak-audit.json')));
const publicRoots = [];
for (let index = 0; index < process.argv.length; index += 1) if (process.argv[index] === '--public-root') publicRoots.push(resolve(process.argv[index + 1]));
const audit = await auditB35PublicState({
  repositoryRoot,
  privateEvidenceRoot,
  sealedPath: resolve(workRoot, 'sealed/mapping.sealed.json'),
  sessionRoot: resolve(workRoot, 'observer-sessions'),
  registryPath: resolve(workRoot, 'sealed/sensitive-hash-registry.sealed.json'),
  publicRoots,
  requireCleanTrackedTree: argument('--allow-tracked-dirty', 'false') !== 'true',
});
await writeFile(outputPath, `${JSON.stringify(audit, null, 2)}\n`);
process.stdout.write(`BFS_B35_PUBLIC_STATE ${audit.status} head=${audit.gitHead} sensitive=${audit.sensitiveRegistryCount} matches=${audit.sensitiveMatchCount} privatePaths=${audit.trackedPrivatePathCount}\n`);
if (audit.status !== 'PUBLIC_STATE_LEAK_AUDIT_PASS') {
  const details = JSON.parse(await readFile(outputPath, 'utf8')).privateDetails;
  process.stderr.write(`BFS_B35_PUBLIC_STATE_PRIVATE_DETAILS ${JSON.stringify(details)}\n`);
  process.exitCode = 1;
}
