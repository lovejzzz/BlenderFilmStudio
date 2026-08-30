#!/usr/bin/env node

import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync, readlinkSync, statSync, writeFileSync } from 'node:fs';
import { basename, resolve } from 'node:path';

const repository = resolve(process.argv[2]);
const evidenceRelative = process.argv[3];
if (!repository || !evidenceRelative) throw new Error('Usage: audit-f07.mjs <repository-root> <evidence-root-relative>');
const evidence = resolve(repository, evidenceRelative);
const sourceApp = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-f0.6-merge-drill/bin/Film Studio Engine F0.app';
const stagingApp = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/F0.7-packages-attempt-02/staging/Film Studio Engine F0.app';
const dmg = '/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/F0.7-packages-attempt-02/Film-Studio-Engine-F0-5.2.1-unsigned.dmg';
const installApp = '/Users/mengyingli/Applications/Film Studio Engine F0.app';
const officialApp = '/Applications/Blender.app';
const officialConfig = '/Users/mengyingli/Library/Application Support/Blender';
const officialCache = '/Users/mengyingli/Library/Caches/Blender';
const f0Config = '/Users/mengyingli/Library/Application Support/FilmStudioEngineF0';
const f0Cache = '/Users/mengyingli/Library/Caches/FilmStudioEngineF0';
const expected = {
  sourceTree: 'c3a055c025bf8d8e20688447e17ca1fd0c583d555168fba62b3a583c050eddbe',
  productBinary: '58d5c984c58d986d3cf44622ad5876052a67890d0b077dafd4977f6e2b24a71d',
  officialRuntimeBinary: 'cf0fa6bb8cca9621d39637dfbcfa9990abcbf9ccaafc5edd8306967d9aaaad3e',
  officialAppTree: 'bdcf8064f0fae603eed3edabaddff2f5134e40ed49a24bd7ed23f4b36ac94743',
  officialConfig: '455fea8df82bcba3c0503eb4abd346295620bb471179045e29aa1c8eaa4f1107',
  officialCache: '43c285a9c90490923b3dcd068a15c2b72921c1c7bf76389ce7c1367695864818',
  f0Config: 'd77cc65db6f3577a028e1ab2895e8ecacbe9574a1b734ec0c091af275f51606d',
  f0Cache: 'e2e8c6da1214de5681a73eac7ce06e101111a0a94ec85787b8d2c3b160eceaba',
};
const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function validSelf(path, field, canonicalHash = false) {
  const value = JSON.parse(readFileSync(path));
  const observed = value[field];
  delete value[field];
  return observed === (canonicalHash ? shaBytes(canonical(value)) : prettyHash(value));
}
function treeIdentity(root) {
  if (!existsSync(root)) return { state: 'ABSENT', files: 0, directories: 0, logicalBytes: 0, digest: shaBytes('ABSENT') };
  const rows = [];
  let files = 0;
  let directories = 0;
  let logicalBytes = 0;
  const walk = (current, prefix = '') => {
    for (const name of readdirSync(current).sort((a, b) => a.localeCompare(b, 'en'))) {
      const path = resolve(current, name);
      const rel = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (stat.isDirectory()) { directories += 1; rows.push({ path: rel, type: 'directory', mode }); walk(path, rel); }
      else if (stat.isSymbolicLink()) rows.push({ path: rel, type: 'symlink', mode, target: readlinkSync(path) });
      else if (stat.isFile()) { files += 1; logicalBytes += stat.size; rows.push({ path: rel, type: 'file', mode, bytes: stat.size, sha256: shaFile(path) }); }
      else rows.push({ path: rel, type: 'other', mode, bytes: stat.size });
    }
  };
  walk(root);
  return { state: 'PRESENT', files, directories, logicalBytes, digest: shaBytes(`${rows.map(row => JSON.stringify(row)).join('\n')}\n`) };
}
const load = relativePath => JSON.parse(readFileSync(resolve(evidence, relativePath)));
const checks = {};
const check = (name, value) => { checks[name] = Boolean(value); };

for (const [file, field] of [
  ['tool-freeze.json', 'freezeHash'], ['formal-start.json', 'formalStartHash'], ['package/01-import.json', 'importHash'],
  ['package-manifest.json', 'manifestHash'], ['roundtrip.json', 'roundtripHash'],
  ['install-uninstall.json', 'installUninstallHash'], ['configuration-isolation.json', 'configurationHash'],
]) check(`self:${file}`, validSelf(resolve(evidence, file), field));

const packageAdmissions = readdirSync(resolve(evidence, 'package')).filter(name => /^\d\d-.*-admission\.json$/.test(name)).sort();
const nativeAdmissions = readdirSync(resolve(evidence, 'processes')).filter(name => /^\d\d-.*-admission\.json$/.test(name)).sort();
const processReceipts = readdirSync(resolve(evidence, 'processes')).filter(name => /^\d\d-.*\.json$/.test(name) && !name.endsWith('-admission.json')).sort();
check('packageAdmissionCount', packageAdmissions.length === 4);
check('nativeAdmissionCount', nativeAdmissions.length === 6);
check('processReceiptCount', processReceipts.length === 6);
for (const name of packageAdmissions) {
  const path = resolve(evidence, 'package', name);
  const value = JSON.parse(readFileSync(path));
  check(`packageAdmission:${name}`, validSelf(path, 'admissionHash') && value.status === 'ACCEPTED' && value.runningBlenderPidsBefore.length === 0);
}
for (const name of nativeAdmissions) {
  const path = resolve(evidence, 'processes', name);
  const value = JSON.parse(readFileSync(path));
  check(`nativeAdmission:${name}`, validSelf(path, 'admissionHash') && value.status === 'ACCEPTED' && value.runningBlenderPidsBefore.length === 0 && value.maximumConcurrentNativeProcesses === 1);
}
const expectedRuntimeHashes = [
  expected.officialRuntimeBinary, expected.productBinary, expected.officialRuntimeBinary,
  expected.productBinary, expected.officialRuntimeBinary, expected.productBinary,
];
for (const [index, name] of processReceipts.entries()) {
  const path = resolve(evidence, 'processes', name);
  const value = JSON.parse(readFileSync(path));
  check(`process:${name}`, validSelf(path, 'processHash') && value.status === 'PASS' && value.sequence === index + 1 && value.runtimeBinarySha256 === expectedRuntimeHashes[index] && value.exitCode === 0 && !value.timeout && value.timing.realSeconds <= 60 && value.timing.maximumResidentSetSizeBytes <= 2147483648 && value.renderCalls === 0 && value.mouseInteractions === 0);
  for (const log of Object.values(value.logs)) check(`processLog:${name}:${log.path}`, statSync(resolve(evidence, log.path)).size === log.bytes && shaFile(resolve(evidence, log.path)) === log.sha256);
}

const reportFiles = [
  'roundtrip/official-to-f0/01-official-report.json', 'roundtrip/official-to-f0/02-f0-report.json',
  'roundtrip/official-to-f0/03-official-report.json', 'roundtrip/f0-to-official/04-f0-report.json',
  'roundtrip/f0-to-official/05-official-report.json', 'roundtrip/f0-to-official/06-f0-reopen-report.json',
];
const reports = reportFiles.map(path => {
  check(`stageSelf:${path}`, validSelf(resolve(evidence, path), 'reportHash', true));
  return load(path);
});
const core = reports[0].coreSemanticSha256;
check('coreSemanticExact', reports.every(report => report.status === 'PASS' && report.coreSemanticSha256 === core && report.renderCalls === 0 && report.mouseInteractions === 0));
check('officialRuntimeIdentity', [0, 2, 4].every(index => reports[index].runtime.version === '5.2.0 LTS' && reports[index].runtime.buildHash === 'fbe6228777e7'));
check('f0RuntimeIdentity', [1, 3, 5].every(index => reports[index].runtime.version === '5.2.1 LTS' && reports[index].runtime.buildHash === 'fa1b578bb421'));
check('missingMetadataGraceful', reports[1].missingOptionalMetadataGraceful === true && reports[1].optionalMetadataBeforeSave.metadataSha256 === null);
const metadata = reports[3].optionalMetadataBeforeSave.metadataSha256;
check('typedMetadataCreated', typeof metadata === 'string' && metadata.length === 64);
check('metadataPreservedOrDropped', [4, 5].every(index => [null, metadata].includes(reports[index].optionalMetadataBeforeSave.metadataSha256)));
for (const [index, report] of reports.entries()) {
  if (report.input) check(`inputImmutable:${index + 1}`, shaFile(resolve(repository, report.input.uri)) === report.input.sha256BeforeAndAfter);
  if (report.output) check(`outputExact:${index + 1}`, statSync(resolve(repository, report.output.uri)).size === report.output.bytes && shaFile(resolve(repository, report.output.uri)) === report.output.sha256 && report.output.bytes <= 16777216);
}
for (const index of [1, 3, 5]) {
  for (const [kind, path] of Object.entries(reports[index].resourcePaths)) {
    check(`f0ResourcePath:${index + 1}:${kind}`, typeof path === 'string' && path.startsWith(`${f0Config}/`));
  }
}
const officialSandbox = resolve(evidence, 'sandbox/official-user');
for (const index of [0, 2, 4]) {
  for (const [kind, path] of Object.entries(reports[index].resourcePaths)) {
    check(`officialSandboxPath:${index + 1}:${kind}`, typeof path === 'string' && path.startsWith(`${officialSandbox}/`));
  }
}

const manifest = load('package-manifest.json');
const normalized = treeIdentity(stagingApp);
check('sourceProductUnchanged', treeIdentity(sourceApp).digest === expected.sourceTree && shaFile(resolve(sourceApp, 'Contents/MacOS/Blender')) === expected.productBinary);
check('normalizedPayloadExact', normalized.digest === manifest.normalizedPayload.digest && normalized.files === 5487 && shaFile(resolve(stagingApp, 'Contents/MacOS/Blender')) === expected.productBinary);
check('dmgExact', existsSync(dmg) && statSync(dmg).size === manifest.dmg.bytes && shaFile(dmg) === manifest.dmg.sha256 && manifest.dmg.hdiutilVerified === true);
check('unsignedBoundary', manifest.status === 'PASS_UNSIGNED_RESEARCH_PACKAGE' && manifest.signature.classification === 'ADHOC_LINKER_SIGNED' && manifest.gatekeeper.classification === 'EXPECTED_REJECTION_RETAINED' && manifest.gatekeeper.spctlExitCode !== 0 && !manifest.publicDistributionClaimed && !manifest.developerIdUsed && !manifest.notarizationSubmitted && !manifest.gatekeeperBypassed);
check('crossBoundPackage', manifest.crossBoundFromAttempt02?.fileSha256 === '6a32cedbf248dec0abfdddb100665b608a2855c314ed67182a6d2d3d651d600f' && manifest.crossBoundFromAttempt02?.manifestHash === 'fc3c6dbd7188958b5d92608675e16dad28ab97d3413df5aa43a4aadb1fa3d6e8');
const codesignText = `${readFileSync(resolve(evidence, 'package/03-codesign.stdout.log'), 'utf8')}\n${readFileSync(resolve(evidence, 'package/03-codesign.stderr.log'), 'utf8')}`;
const spctlText = `${readFileSync(resolve(evidence, 'package/03-spctl.stdout.log'), 'utf8')}\n${readFileSync(resolve(evidence, 'package/03-spctl.stderr.log'), 'utf8')}`;
check('signatureEvidence', /Signature=adhoc|TeamIdentifier=not set/.test(codesignText));
check('gatekeeperRejectionEvidence', /rejected|code has no resources|not valid/i.test(spctlText));

const install = load('install-uninstall.json');
check('installUninstall', install.status === 'PASS' && install.absentBeforeInstall && install.exactGeneratedDestinationRemoved && install.absentAfterUninstall && install.officialBlenderUnchanged && !existsSync(installApp));
const configuration = load('configuration-isolation.json');
check('officialAppUnchanged', treeIdentity(officialApp).digest === expected.officialAppTree);
check('officialConfigUnchanged', treeIdentity(officialConfig).digest === expected.officialConfig && treeIdentity(officialCache).digest === expected.officialCache);
check('f0ConfigUnchanged', treeIdentity(f0Config).digest === expected.f0Config && treeIdentity(f0Cache).digest === expected.f0Cache);
check('configurationReceipt', configuration.status === 'PASS' && configuration.officialRootsExact && configuration.independentF0RootsExact);
check('officialSandboxRetained', configuration.officialSandbox?.state === 'PRESENT' && configuration.officialSandbox?.root === officialSandbox);
const roundtrip = load('roundtrip.json');
check('roundtripReceipt', roundtrip.status === 'PASS' && roundtrip.formalProductStarts === 6 && roundtrip.maximumFormalProductStarts === 6 && roundtrip.coreSemanticSha256 === core && roundtrip.coreSemanticExactAtAllSixBoundaries && roundtrip.officialToF0ToOfficial.status === 'PASS' && roundtrip.f0ToOfficial.status === 'PASS' && roundtrip.zeroRenderCalls && roundtrip.zeroMouseInteractions && roundtrip.networkCalls === 0 && roundtrip.modelCalls === 0);

const failures = Object.entries(checks).filter(([, passed]) => !passed).map(([name]) => name);
const body = {
  schemaVersion: 'bfs.f0.7.independentAudit.v0.1', experimentId: basename(evidence),
  status: failures.length ? 'FAIL' : 'PASS', independentImplementation: true,
  importsRunnerOrStageTool: false, checks, failures,
  observed: { coreSemanticSha256: core, typedMetadataSha256: metadata, normalizedPayloadDigest: normalized.digest, dmgSha256: manifest.dmg.sha256, packageAdmissions: packageAdmissions.length, nativeAdmissions: nativeAdmissions.length, productStarts: processReceipts.length },
  claimCeilingRespected: true,
};
writeFileSync(resolve(evidence, 'audit.json'), `${JSON.stringify({ ...body, auditHash: prettyHash(body) }, null, 2)}\n`, { flag: 'wx' });
if (failures.length) throw new Error(`F0.7 independent audit failed: ${failures.join(', ')}`);
console.log(`F0.7_AUDIT PASS checks=${Object.keys(checks).length} core=${core}`);
