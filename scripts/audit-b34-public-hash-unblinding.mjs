import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256File } from './lib/receipt-format.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/human-quadrature-review-v0-1');
const manifestPath = resolve(experimentRoot, 'evidence/package.manifest.json');
const sessionRoot = resolve(experimentRoot, 'work/observer-sessions');
const outputIndex = process.argv.indexOf('--output');
const outputPath = resolve(outputIndex === -1 ? resolve(experimentRoot, 'evidence/public-hash-unblinding-audit.json') : process.argv[outputIndex + 1]);
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
const methodByCarrierSha = Object.fromEntries(manifest.carriers.map(item => [item.sha256, item.method]));
if (Object.keys(methodByCarrierSha).length !== 3) throw new Error('Public package manifest does not expose three unique method carrier hashes');

const recovered = [];
for (const session of manifest.sessions) {
  const htmlPath = resolve(sessionRoot, session.sessionId, 'index.html');
  const html = await readFile(htmlPath, 'utf8');
  const match = html.match(/const DATA=(\{.*?\});const video=/s);
  if (!match) throw new Error(`Cannot recover public DATA from ${session.sessionId}`);
  const data = JSON.parse(match[1]);
  const mapping = data.visibleCarriers.map(item => ({
    visibleLabel: item.label,
    observerVisibleCarrierSha256: item.sha256,
    recoveredMethod: methodByCarrierSha[item.sha256] ?? null,
  }));
  recovered.push({
    sessionId: session.sessionId,
    observerHtmlSha256: await sha256File(htmlPath),
    allThreeMethodsRecoveredWithoutSealedMapping: mapping.length === 3 && mapping.every(item => item.recoveredMethod !== null) && new Set(mapping.map(item => item.recoveredMethod)).size === 3,
    mapping,
  });
}
const allSessionsRecovered = recovered.length === 18 && recovered.every(item => item.allThreeMethodsRecoveredWithoutSealedMapping);
const result = {
  documentType: 'BFS_B34_PUBLIC_HASH_UNBLINDING_AUDIT', version: manifest.version,
  auditedAtUtc: new Date().toISOString(), packageManifestSha256: await sha256File(manifestPath),
  attackKnowledge: ['public tracked package.manifest.json', 'one distributed observer session index.html'],
  forbiddenKnowledgeNotUsed: ['sealed mapping file', 'mapping salts', 'unblinded analyzer output'],
  joinKey: 'carrier SHA-256', sessionsAudited: recovered.length, sessionsFullyRecovered: recovered.filter(item => item.allThreeMethodsRecoveredWithoutSealedMapping).length,
  status: allSessionsRecovered ? 'PUBLIC_HASH_JOIN_UNBLINDS_ALL_SESSIONS' : 'PUBLIC_HASH_JOIN_DID_NOT_RECOVER_ALL_SESSIONS',
  formalHumanStudyDisposition: allSessionsRecovered ? 'DO_NOT_COLLECT_FORMAL_HUMAN_RESPONSES_FROM_B34_PUBLIC_EVIDENCE_STATE' : 'REQUIRES_FURTHER_AUDIT',
  falsifiedAssumption: 'Absence of source labels and sealed mapping from the observer package is sufficient blinding after method-labelled carrier hashes are publicly committed.',
  requiredMitigation: 'Create a new visual realization and withhold every method-labelled output, carrier, decoded-frame and pixel hash until all preregistered responses are hash-locked. Publicly commit only the protocol and non-unblinding tool identities before collection.',
  recovered,
};
await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`BFS_B34_PUBLIC_HASH_UNBLINDING status=${result.status} sessions=${result.sessionsFullyRecovered}/${result.sessionsAudited} disposition=${result.formalHumanStudyDisposition}\n`);
if (!allSessionsRecovered) process.exitCode = 1;
