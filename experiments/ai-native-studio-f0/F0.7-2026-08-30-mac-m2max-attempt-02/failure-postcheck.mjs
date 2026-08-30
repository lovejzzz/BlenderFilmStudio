#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, lstatSync, readFileSync, readdirSync, readlinkSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repository = resolve(process.argv[2]);
const evidence = resolve(repository, 'experiments/ai-native-studio-f0/F0.7-2026-08-30-mac-m2max-attempt-02');
const shaBytes = value => createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(readFileSync(path));
const prettyHash = value => shaBytes(`${JSON.stringify(value, null, 2)}\n`);
function tree(root) {
  if (!existsSync(root)) return { root, state: 'ABSENT', digest: shaBytes('ABSENT') };
  const rows = [];
  let files = 0;
  let directories = 0;
  let logicalBytes = 0;
  const walk = (current, prefix = '') => {
    for (const name of readdirSync(current).sort((a, b) => a.localeCompare(b, 'en'))) {
      const path = resolve(current, name);
      const relative = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(path);
      const mode = stat.mode & 0o7777;
      if (stat.isDirectory()) { directories += 1; rows.push({ path: relative, type: 'directory', mode }); walk(path, relative); }
      else if (stat.isSymbolicLink()) rows.push({ path: relative, type: 'symlink', mode, target: readlinkSync(path) });
      else if (stat.isFile()) { files += 1; logicalBytes += stat.size; rows.push({ path: relative, type: 'file', mode, bytes: stat.size, sha256: shaFile(path) }); }
      else rows.push({ path: relative, type: 'other', mode, bytes: stat.size });
    }
  };
  walk(root);
  return { root, state: 'PRESENT', files, directories, logicalBytes, digest: shaBytes(`${rows.map(row => JSON.stringify(row)).join('\n')}\n`) };
}
function runningBlender() {
  try { return execFileSync('/usr/bin/pgrep', ['-x', 'Blender'], { encoding: 'utf8' }).trim().split(/\s+/).filter(Boolean); } catch { return []; }
}
const identities = {
  sourceProduct: tree('/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/build-f0.6-merge-drill/bin/Film Studio Engine F0.app'),
  installedOfficialBlender: tree('/Applications/Blender.app'),
  officialApplicationSupport: tree('/Users/mengyingli/Library/Application Support/Blender'),
  officialCache: tree('/Users/mengyingli/Library/Caches/Blender'),
  f0ApplicationSupport: tree('/Users/mengyingli/Library/Application Support/FilmStudioEngineF0'),
  f0Cache: tree('/Users/mengyingli/Library/Caches/FilmStudioEngineF0'),
};
const expected = {
  sourceProduct: 'c3a055c025bf8d8e20688447e17ca1fd0c583d555168fba62b3a583c050eddbe',
  installedOfficialBlender: 'bdcf8064f0fae603eed3edabaddff2f5134e40ed49a24bd7ed23f4b36ac94743',
  officialApplicationSupport: 'c97e9a5f1d34065925ff034ab03770e38a87676b9ab1bfc0b29aeff43e6b44bf',
  officialCache: '43c285a9c90490923b3dcd068a15c2b72921c1c7bf76389ce7c1367695864818',
  f0ApplicationSupport: 'd77cc65db6f3577a028e1ab2895e8ecacbe9574a1b734ec0c091af275f51606d',
  f0Cache: 'e2e8c6da1214de5681a73eac7ce06e101111a0a94ec85787b8d2c3b160eceaba',
};
const identityChecks = Object.fromEntries(Object.entries(expected).map(([name, digest]) => [name, identities[name].digest === digest]));
const outputChecks = {
  officialStageOneBlendRetained: existsSync(resolve(evidence, 'roundtrip/official-to-f0/01-official.blend')),
  officialStageOneReportRetained: existsSync(resolve(evidence, 'roundtrip/official-to-f0/01-official-report.json')),
  failedStageTwoBlendAbsent: !existsSync(resolve(evidence, 'roundtrip/official-to-f0/02-f0.blend')),
  failedStageTwoReportAbsent: !existsSync(resolve(evidence, 'roundtrip/official-to-f0/02-f0-report.json')),
  installTargetAbsentAfterSafetyCleanup: !existsSync('/Users/mengyingli/Applications/Film Studio Engine F0.app'),
  newDmgRetained: existsSync('/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-F0-workspace/F0.7-packages-attempt-02/Film-Studio-Engine-F0-5.2.1-unsigned.dmg'),
};
const running = runningBlender();
const passed = Object.values(identityChecks).every(Boolean) && Object.values(outputChecks).every(Boolean) && running.length === 0;
const body = {
  schemaVersion: 'bfs.f0.7.failurePostcheck.v0.1', status: passed ? 'PASS' : 'FAIL',
  independentPostFailureCheck: true, identities, identityChecks, outputChecks, runningBlenderPids: running,
};
writeFileSync(resolve(evidence, 'failure-postcheck.json'), `${JSON.stringify({ ...body, postcheckHash: prettyHash(body) }, null, 2)}\n`, { flag: 'wx' });
if (!passed) throw new Error('F0.7 post-failure safety check failed');
console.log('F0.7 failure postcheck PASS');
