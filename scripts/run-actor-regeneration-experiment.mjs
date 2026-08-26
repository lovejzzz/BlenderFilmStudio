import { access, readFile, writeFile, mkdir } from 'node:fs/promises';
import { constants } from 'node:fs';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

const repositoryRoot = resolve(import.meta.dirname, '..');
const generator = resolve(repositoryRoot, 'blender/generate_actor_benchmark.py');
const runRoot = resolve(repositoryRoot, 'experiments/actor-v0-1/runs/regeneration');
const assetOutput = resolve(runRoot, 'B03-lead.blend');
const motionOutput = resolve(runRoot, 'body-idle.blend');
const reportOutput = resolve(runRoot, 'report.json');
const summaryOutput = resolve(repositoryRoot, 'experiments/actor-v0-1/regeneration.json');

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try {
      await access(candidate, constants.X_OK);
      return candidate;
    } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; process.stdout.write(chunk); });
    child.stderr.on('data', chunk => { stderr += chunk; process.stderr.write(chunk); });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ stdout, stderr }) : reject(new Error(`${command} exited ${code}`)));
  });
}

function semanticSignature(report) {
  return {
    motionSha256: report.motion.sha256,
    restPoseSha256: report.identity.restPoseSha256,
    topologySha256: report.identity.topologySha256,
    shapeKeySetSha256: report.identity.shapeKeySetSha256,
    identitySha256: report.identity.identitySha256,
  };
}

const blender = await findBlender();
await mkdir(runRoot, { recursive: true });
const reports = [];
for (const label of ['run-a', 'run-b']) {
  await run(blender, [
    '--background', '--factory-startup', '--python', generator, '--',
    '--asset-output', assetOutput,
    '--motion-output', motionOutput,
    '--report-output', reportOutput,
  ]);
  const report = JSON.parse(await readFile(reportOutput, 'utf8'));
  reports.push({ label, assetSha256: report.asset.sha256, semantic: semanticSignature(report) });
}
const semanticJson = reports.map(item => JSON.stringify(item.semantic));
const summary = {
  documentType: 'BFS_ACTOR_REGENERATION_EXPERIMENT',
  experimentVersion: '0.1.0',
  executedAtUtc: new Date().toISOString(),
  blender: '5.2.0 LTS',
  runs: reports,
  results: {
    binaryAssetShaEqual: reports[0].assetSha256 === reports[1].assetSha256,
    semanticIdentityEqual: semanticJson[0] === semanticJson[1],
    motionLibraryShaEqual: reports[0].semantic.motionSha256 === reports[1].semantic.motionSha256,
  },
  conclusion: 'Blender library serialization is not treated as a canonical semantic identity. ActorSpec pins the chosen binary asset, while regeneration equivalence is measured with normalized rig, topology, Shape Key, and motion hashes.',
};
await writeFile(summaryOutput, `${JSON.stringify(summary, null, 2)}\n`);
console.log(`BFS_ACTOR_REGENERATION_COMPLETE ${JSON.stringify(summary.results)}`);
if (!summary.results.semanticIdentityEqual || !summary.results.motionLibraryShaEqual) process.exitCode = 1;
