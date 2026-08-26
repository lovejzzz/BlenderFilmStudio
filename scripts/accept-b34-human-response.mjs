import { appendFile, mkdir, open, readFile, stat } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';
import { validateB34Response } from './lib/b34-human-review.mjs';

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1];
}

const responsePath = resolve(argument('--response', ''));
const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1');
const specPath = resolve(repositoryRoot, 'specs/human-quadrature-review-spec.v0.1.json');
const manifestPath = resolve(argument('--manifest', resolve(experimentRoot, 'evidence/package.manifest.json')));
const sealedPath = resolve(argument('--sealed', resolve(experimentRoot, 'work/sealed/mapping.sealed.json')));
const acceptedRoot = resolve(argument('--accepted-dir', resolve(experimentRoot, 'responses/accepted')));
const ledgerPath = resolve(argument('--ledger', resolve(experimentRoot, 'responses/accepted-ledger.jsonl')));
if (!responsePath || responsePath === resolve('.')) throw new Error('--response is required');

const [spec, manifest, sealed, response] = await Promise.all([specPath, manifestPath, sealedPath, responsePath].map(async path => JSON.parse(await readFile(path, 'utf8'))));
const specSha = await sha256File(specPath);
const validation = validateB34Response({ spec, specSha, manifest, sealed, response });
if (!validation.valid) throw new Error(`B34_RESPONSE_REJECTED ${validation.reason}`);
await mkdir(acceptedRoot, { recursive: true });
const acceptedPath = resolve(acceptedRoot, `${response.sessionId}.${response.responseHash}.json`);
let handle;
try {
  handle = await open(acceptedPath, 'wx');
  await handle.writeFile(`${JSON.stringify(response, null, 2)}\n`);
} catch (error) {
  if (error.code === 'EEXIST') throw new Error('B34_RESPONSE_REJECTED RESPONSE_MUTATION_OR_DUPLICATE');
  throw error;
} finally {
  await handle?.close();
}
const entry = {
  documentType: 'BFS_B34_ACCEPTED_RESPONSE_LEDGER_ENTRY', version: spec.version,
  acceptedAtUtc: new Date().toISOString(), studySpecSha256: specSha,
  packageManifestSha256: await sha256File(manifestPath), sessionId: response.sessionId,
  observerId: response.viewing.observerId, responseHash: response.responseHash,
  acceptedFile: basename(acceptedPath), acceptedFileSha256: await sha256File(acceptedPath),
};
try {
  await stat(ledgerPath);
} catch {
  await mkdir(dirname(ledgerPath), { recursive: true });
}
await appendFile(ledgerPath, `${JSON.stringify(entry)}\n`, { flag: 'a' });
process.stdout.write(`BFS_B34_RESPONSE_ACCEPTED session=${response.sessionId} hash=${response.responseHash}\n`);
