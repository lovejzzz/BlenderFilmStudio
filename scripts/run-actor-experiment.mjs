import { spawn } from 'node:child_process';
import { access, mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { actorFixturePath, validateActorSpec } from './lib/actor-spec.mjs';
import { readJson, repositoryRoot } from './lib/scene-spec.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/actor-v0-1');
const runsRoot = resolve(experimentRoot, 'runs');
const specPath = resolve(repositoryRoot, 'specs/benchmarks/B03.actor.json');
const auditScript = resolve(repositoryRoot, 'blender/audit_actor_asset.py');
const injectScript = resolve(repositoryRoot, 'blender/inject_unsafe_actor_fixture.py');
const unsafeAssetPath = resolve(repositoryRoot, 'assets/characters/B03-lead-unsafe.blend');

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate); return candidate; } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

function runProcess(command, args, { expectSuccess = true } = {}) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', chunk => { stdout += chunk; process.stdout.write(chunk); });
    child.stderr.on('data', chunk => { stderr += chunk; process.stderr.write(chunk); });
    child.on('error', reject);
    child.on('close', code => {
      const result = { code, stdout, stderr };
      if (expectSuccess && code !== 0) reject(new Error(`Process failed (${code}):\n${stdout}\n${stderr}`));
      else resolvePromise(result);
    });
  });
}

function auditArgs(blender, actorSpec, output) {
  return [blender, [
    '--factory-startup', '--background', '--python', auditScript, '--',
    '--spec', actorSpec, '--repository-root', repositoryRoot, '--output', output,
  ]];
}

async function main() {
  const blender = await findBlender();
  await mkdir(runsRoot, { recursive: true });
  const fixtureSuite = await readJson(actorFixturePath);
  const fixtureResults = fixtureSuite.cases.map(fixture => {
    const document = structuredClone(fixtureSuite.base);
    for (const mutation of fixture.mutations) {
      const segments = mutation.path.slice(1).split('/');
      const key = segments.pop();
      let parent = document;
      for (const segment of segments) parent = parent[segment];
      if (mutation.op === 'set') parent[key] = structuredClone(mutation.value);
      else if (mutation.op === 'delete') delete parent[key];
      else if (mutation.op === 'append') parent[key].push(structuredClone(mutation.value));
    }
    const validation = validateActorSpec(document);
    return {
      id: fixture.id,
      passed: validation.valid === fixture.expectedValid
        && (fixture.expectedCode === undefined || validation.errors.some(error => error.code === fixture.expectedCode)),
    };
  });

  const baseSpec = await readJson(specPath);
  const baseValidation = validateActorSpec(baseSpec);
  if (!baseValidation.valid) throw new Error(`B03 ActorSpec invalid: ${JSON.stringify(baseValidation.errors)}`);
  const cleanAuditPath = resolve(experimentRoot, 'audit.json');
  const [cleanCommand, cleanArgs] = auditArgs(blender, specPath, cleanAuditPath);
  await runProcess(cleanCommand, cleanArgs);
  const cleanAudit = await readJson(cleanAuditPath);

  const unsafeFixtureReport = resolve(runsRoot, 'unsafe-fixture.json');
  await runProcess(blender, [
    '--factory-startup', '--background', '--python', injectScript, '--',
    '--input', resolve(repositoryRoot, baseSpec.actor.assetUri), '--output', unsafeAssetPath, '--report', unsafeFixtureReport,
  ]);
  const unsafeFixture = await readJson(unsafeFixtureReport);
  const unsafeSpec = structuredClone(baseSpec);
  unsafeSpec.actor.assetUri = 'assets/characters/B03-lead-unsafe.blend';
  unsafeSpec.actor.assetSha256 = unsafeFixture.sha256;
  const unsafeSpecPath = resolve(runsRoot, 'unsafe.actor.json');
  await writeFile(unsafeSpecPath, `${JSON.stringify(unsafeSpec, null, 2)}\n`);
  const unsafeSchemaValid = validateActorSpec(unsafeSpec).valid;
  const unsafeAuditPath = resolve(runsRoot, 'unsafe.audit.json');
  const [unsafeCommand, unsafeArgs] = auditArgs(blender, unsafeSpecPath, unsafeAuditPath);
  const unsafeRun = await runProcess(unsafeCommand, unsafeArgs, { expectSuccess: false });
  const unsafeAudit = await readJson(unsafeAuditPath);
  const unsafeDriverRejected = unsafeRun.code !== 0
    && unsafeAudit.checks.some(check => check.id === 'A11_DRIVER_POLICY' && !check.passed);

  const tamperedSpec = structuredClone(baseSpec);
  tamperedSpec.rig.restPoseSha256 = `0${tamperedSpec.rig.restPoseSha256.slice(1)}`;
  const tamperedSpecPath = resolve(runsRoot, 'tampered-identity.actor.json');
  await writeFile(tamperedSpecPath, `${JSON.stringify(tamperedSpec, null, 2)}\n`);
  const tamperedAuditPath = resolve(runsRoot, 'tampered-identity.audit.json');
  const [tamperedCommand, tamperedArgs] = auditArgs(blender, tamperedSpecPath, tamperedAuditPath);
  const tamperedRun = await runProcess(tamperedCommand, tamperedArgs, { expectSuccess: false });
  const tamperedAudit = await readJson(tamperedAuditPath);
  const tamperedIdentityRejected = tamperedRun.code !== 0
    && tamperedAudit.checks.some(check => check.id === 'A05_REST_POSE_HASH' && !check.passed);

  const report = {
    documentType: 'BFS_ACTOR_EXPERIMENT',
    experimentVersion: '0.1.0',
    executedAtUtc: new Date().toISOString(),
    environment: { blender: cleanAudit.blender.version, platform: `${process.platform}-${process.arch}`, node: process.version },
    fixtureSuite: { passed: fixtureResults.filter(item => item.passed).length, total: fixtureResults.length },
    cleanAsset: {
      allChecksPassed: cleanAudit.allChecksPassed,
      checkCount: cleanAudit.checks.length,
      identitySha256: cleanAudit.identity.identitySha256,
    },
    negativeTests: {
      unsafeActorSpecSchemaValid: unsafeSchemaValid,
      unsafeFullPythonDriverRejectedByAssetAudit: unsafeDriverRejected,
      tamperedRestPoseRejectedByAssetAudit: tamperedIdentityRejected,
    },
    allAcceptanceChecksPassed: fixtureResults.every(item => item.passed)
      && cleanAudit.allChecksPassed && unsafeSchemaValid && unsafeDriverRejected && tamperedIdentityRejected,
    explicitNonClaims: [
      'The B03 technical mannequin is not a photoreal human.',
      'A conforming rig does not prove natural acting, facial fidelity, or mesh-level contact.',
      'This isolated asset audit does not validate external targets; B03 SceneSpec v0.2 performs that separate scene-level evaluation.',
    ],
  };
  await writeFile(resolve(experimentRoot, 'results.json'), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`BFS_ACTOR_EXPERIMENT_COMPLETE ${JSON.stringify(report)}\n`);
  if (!report.allAcceptanceChecksPassed) process.exitCode = 1;
}

main().catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
