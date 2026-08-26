import { open, readFile, readdir } from 'node:fs/promises';
import { delimiter, resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { validateB35Response } from './lib/b35-human-review.mjs';
import { auditB35PublicState } from './lib/b35-public-state-audit.mjs';

const abort = process.argv.includes('--abort');
const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-2');
const workRoot = resolve(experimentRoot, 'work');
const evidenceRoot = resolve(workRoot, 'private-evidence');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.2.json');
const manifestPath = resolve(evidenceRoot, 'package.manifest.json');
const sealedPath = resolve(workRoot, 'sealed/mapping.sealed.json');
const registryPath = resolve(workRoot, 'sealed/sensitive-hash-registry.sealed.json');
const acceptedRoot = resolve(workRoot, 'responses/accepted');
const ledgerPath = resolve(workRoot, 'responses/accepted-ledger.jsonl');
const outputPath = resolve(workRoot, 'collection-close.json');
const [spec, manifest] = await Promise.all([specPath, manifestPath].map(async path => JSON.parse(await readFile(path, 'utf8'))));
const specSha = await sha256File(specPath);
let names = [];
try { names = (await readdir(acceptedRoot)).filter(name => name.endsWith('.json')).sort(); } catch {}
const responses = await Promise.all(names.map(async name => JSON.parse(await readFile(resolve(acceptedRoot, name), 'utf8'))));
let ledgerEntries = [];
try { ledgerEntries = (await readFile(ledgerPath, 'utf8')).trim().split('\n').filter(Boolean).map(line => JSON.parse(line)); } catch {}
if (ledgerEntries.length !== responses.length) throw new Error('B35 close ledger/file count mismatch');
const validations = responses.map(response => validateB35Response({ spec, specSha, manifest, response }));
if (validations.some(item => !item.valid)) throw new Error(`B35 close contains invalid responses: ${JSON.stringify(validations.filter(item => !item.valid))}`);
if (new Set(responses.map(item => item.responseHash)).size !== responses.length || new Set(responses.map(item => item.sessionId)).size !== responses.length || new Set(responses.map(item => item.viewing.observerId)).size !== responses.length) throw new Error('B35 close contains duplicate response, session or observer');
const expectedSessions = manifest.sessions.map(item => item.sessionId).sort();
const observedSessions = responses.map(item => item.sessionId).sort();
if (!abort && (responses.length !== 18 || JSON.stringify(observedSessions) !== JSON.stringify(expectedSessions))) throw new Error('B35 formal close requires all 18 prepared sessions exactly once');
const publicRoots = (process.env.BFS_B35_PUBLIC_ROOTS || '').split(delimiter).filter(Boolean).map(path => resolve(path));
const leakAudit = await auditB35PublicState({ repositoryRoot, privateEvidenceRoot: evidenceRoot, sealedPath, sessionRoot: resolve(workRoot, 'observer-sessions'), registryPath, publicRoots, requireCleanTrackedTree: true });
if (leakAudit.status !== 'PUBLIC_STATE_LEAK_AUDIT_PASS') throw new Error('B35 collection cannot close after a public-state leak');
const close = {
  documentType: 'BFS_B35_COLLECTION_CLOSE', version: spec.version, studySpecSha256: specSha,
  status: abort ? 'ABORTED_NO_FORMAL_RESULT' : 'CLOSED_18_VALID_RESPONSES',
  closedAtUtc: new Date().toISOString(), acceptedResponseHashes: responses.map(response => response.responseHash).sort(),
  acceptedLedgerSha256: responses.length ? await sha256File(ledgerPath) : null,
  publicStateGitHead: leakAudit.gitHead, sensitiveRegistryCommitment: leakAudit.sensitiveRegistryCommitment,
  preUnblindHumanStatus: abort ? 'NOT_ANALYZED_ABORTED' : 'LOCKED_18_VALID_BALANCED', preUnblindDecisionNotRead: true,
  irreversibleRule: 'This B35 version cannot resume collection after this close record exists.',
};
let handle;
try {
  handle = await open(outputPath, 'wx');
  await handle.writeFile(`${JSON.stringify(close, null, 2)}\n`);
} catch (error) {
  if (error.code === 'EEXIST') throw new Error('B35 collection already closed; immutable close record not overwritten');
  throw error;
} finally { await handle?.close(); }
process.stdout.write(`BFS_B35_COLLECTION_CLOSED status=${close.status} responses=${responses.length} head=${close.publicStateGitHead}\n`);
