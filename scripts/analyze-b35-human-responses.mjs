import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { analyzeB35Responses } from './lib/b35-human-review.mjs';

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-2');
const workRoot = resolve(experimentRoot, 'work');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.2.json');
const manifestPath = resolve(argument('--manifest', resolve(workRoot, 'private-evidence/package.manifest.json')));
const sealedPath = resolve(argument('--sealed', resolve(experimentRoot, 'work/sealed/mapping.sealed.json')));
const acceptedRoot = resolve(argument('--accepted-dir', resolve(workRoot, 'responses/accepted')));
const ledgerPath = resolve(argument('--ledger', resolve(workRoot, 'responses/accepted-ledger.jsonl')));
const closePath = resolve(argument('--close-record', resolve(workRoot, 'collection-close.json')));
const outputPath = resolve(argument('--output', resolve(workRoot, 'human-results.private.json')));
const [spec, manifest, sealed, close] = await Promise.all([specPath, manifestPath, sealedPath, closePath].map(async path => JSON.parse(await readFile(path, 'utf8'))));
const specSha = await sha256File(specPath);
let names = [];
try { names = (await readdir(acceptedRoot)).filter(name => name.endsWith('.json')).sort(); } catch {}
const responses = await Promise.all(names.map(async name => JSON.parse(await readFile(resolve(acceptedRoot, name), 'utf8'))));
let entries = [];
try { entries = (await readFile(ledgerPath, 'utf8')).trim().split('\n').filter(Boolean).map(line => JSON.parse(line)); } catch {}
if (entries.length !== responses.length) throw new Error('B35 accepted ledger/file count mismatch');
for (const [index, response] of responses.entries()) {
  const entry = entries.find(item => item.responseHash === response.responseHash);
  if (!entry || entry.studySpecSha256 !== specSha || await sha256File(resolve(acceptedRoot, entry.acceptedFile)) !== entry.acceptedFileSha256) throw new Error(`B35 accepted ledger binding mismatch at response ${index}`);
}
if (close.documentType !== 'BFS_B35_COLLECTION_CLOSE' || close.studySpecSha256 !== specSha) throw new Error('B35 collection close binding mismatch');
if (close.status === 'ABORTED_NO_FORMAL_RESULT') {
  const result = { documentType: 'BFS_B35_HUMAN_REVIEW_RESULT', version: spec.version, analyzedAtUtc: new Date().toISOString(), studySpecSha256: specSha, status: close.status, decision: null, validResponseCount: responses.length, nonClaims: spec.nonClaims };
  await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`BFS_B35_HUMAN_ANALYSIS status=${result.status} decision=NONE responses=${responses.length}\n`);
  process.exit(0);
}
if (close.status !== 'CLOSED_18_VALID_RESPONSES' || responses.length !== 18) throw new Error('B35 collection is not formally closed at 18 valid responses');
const lockedHashes = [...responses.map(response => response.responseHash)].sort();
if (JSON.stringify(close.acceptedResponseHashes) !== JSON.stringify(lockedHashes)) throw new Error('B35 collection close response set mismatch');
const analysis = analyzeB35Responses({ spec, specSha, manifest, sealed, responses });
const result = {
  documentType: 'BFS_B35_HUMAN_REVIEW_RESULT', version: spec.version,
  analyzedAtUtc: new Date().toISOString(), studySpecSha256: specSha,
  packageManifestSha256: await sha256File(manifestPath), acceptedLedgerSha256: entries.length ? await sha256File(ledgerPath) : null,
  ...analysis, nonClaims: spec.nonClaims,
};
await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B35_HUMAN_ANALYSIS status=${result.status} decision=${result.decision ?? 'NONE'} responses=${responses.length}\n`);
if (result.status === 'INVALID_REVIEW') process.exitCode = 1;
