import { appendFile, mkdir, open, readFile, stat, writeFile } from 'node:fs/promises';
import { basename, delimiter, dirname, resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { validateB35Response } from './lib/b35-human-review.mjs';
import { auditB35PublicState } from './lib/b35-public-state-audit.mjs';

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const responsePath = resolve(argument('--response', ''));
const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-2');
const workRoot = resolve(experimentRoot, 'work');
const privateEvidenceRoot = resolve(workRoot, 'private-evidence');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.2.json');
const manifestPath = resolve(argument('--manifest', resolve(privateEvidenceRoot, 'package.manifest.json')));
const sealedPath = resolve(argument('--sealed', resolve(experimentRoot, 'work/sealed/mapping.sealed.json')));
const registryPath = resolve(argument('--registry', resolve(workRoot, 'sealed/sensitive-hash-registry.sealed.json')));
const acceptedRoot = resolve(argument('--accepted-dir', resolve(workRoot, 'responses/accepted')));
const ledgerPath = resolve(argument('--ledger', resolve(workRoot, 'responses/accepted-ledger.jsonl')));
if (!responsePath || responsePath === resolve('.')) throw new Error('--response is required');

const [spec, manifest, sealed, response] = await Promise.all([specPath, manifestPath, sealedPath, responsePath].map(async path => JSON.parse(await readFile(path, 'utf8'))));
const specSha = await sha256File(specPath);
const validation = validateB35Response({ spec, specSha, manifest, sealed, response });
if (!validation.valid) throw new Error(`B35_RESPONSE_REJECTED ${validation.reason}`);
const publicRoots = (process.env.BFS_B35_PUBLIC_ROOTS || '').split(delimiter).filter(Boolean).map(path => resolve(path));
const leakAudit = await auditB35PublicState({
  repositoryRoot, privateEvidenceRoot, sealedPath,
  sessionRoot: resolve(workRoot, 'observer-sessions'), registryPath, publicRoots,
  requireCleanTrackedTree: true,
});
if (leakAudit.status !== 'PUBLIC_STATE_LEAK_AUDIT_PASS') throw new Error('B35_RESPONSE_REJECTED PUBLIC_STATE_LEAK_GATE');
const auditRoot = resolve(workRoot, 'audits');
await mkdir(auditRoot, { recursive: true });
await writeFile(resolve(auditRoot, `preaccept-${response.sessionId}-${Date.now()}.json`), `${JSON.stringify(leakAudit, null, 2)}\n`);
await mkdir(acceptedRoot, { recursive: true });
const acceptedPath = resolve(acceptedRoot, `${response.sessionId}.${response.responseHash}.json`);
let handle;
try {
  handle = await open(acceptedPath, 'wx');
  await handle.writeFile(`${JSON.stringify(response, null, 2)}\n`);
} catch (error) {
  if (error.code === 'EEXIST') throw new Error('B35_RESPONSE_REJECTED RESPONSE_MUTATION_OR_DUPLICATE');
  throw error;
} finally {
  await handle?.close();
}
const entry = {
  documentType: 'BFS_B35_ACCEPTED_RESPONSE_LEDGER_ENTRY', version: spec.version,
  acceptedAtUtc: new Date().toISOString(), studySpecSha256: specSha,
  packageManifestSha256: await sha256File(manifestPath), sessionId: response.sessionId,
  observerId: response.viewing.observerId, responseHash: response.responseHash,
  publicStateGitHead: leakAudit.gitHead, sensitiveRegistryCommitment: leakAudit.sensitiveRegistryCommitment,
  acceptedFile: basename(acceptedPath), acceptedFileSha256: await sha256File(acceptedPath),
};
try {
  await stat(ledgerPath);
} catch {
  await mkdir(dirname(ledgerPath), { recursive: true });
}
await appendFile(ledgerPath, `${JSON.stringify(entry)}\n`, { flag: 'a' });
process.stdout.write(`BFS_B35_RESPONSE_ACCEPTED session=${response.sessionId} hash=${response.responseHash}\n`);
