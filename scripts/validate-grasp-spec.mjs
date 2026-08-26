import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { repositoryRoot } from './lib/scene-spec.mjs';

const schemaPath = resolve(repositoryRoot, 'specs/grasp-spec.v0.1.schema.json');
const defaultFixture = resolve(repositoryRoot, 'specs/benchmarks/B05.grasp.json');
const schema = JSON.parse(await readFile(schemaPath, 'utf8'));
const ajv = new Ajv2020({ allErrors: true, strict: true, formats: { 'date-time': true } });
const validateSchema = ajv.compile(schema);

function semanticErrors(document) {
  const errors = [];
  const fingerIds = new Set();
  const roles = new Set();
  const tipByFinger = new Map();
  for (const finger of document.fingerChains ?? []) {
    if (fingerIds.has(finger.id)) errors.push(`duplicate finger id ${finger.id}`);
    if (roles.has(finger.role)) errors.push(`duplicate finger role ${finger.role}`);
    fingerIds.add(finger.id);
    roles.add(finger.role);
    tipByFinger.set(finger.id, finger.tipSocket);
    for (const bone of finger.bones ?? []) {
      if (bone.minimumDeg > bone.maximumDeg) errors.push(`${finger.id}.${bone.boneSemantic} minimumDeg exceeds maximumDeg`);
      if (bone.restDeg < bone.minimumDeg || bone.restDeg > bone.maximumDeg) errors.push(`${finger.id}.${bone.boneSemantic} restDeg is outside joint limits`);
    }
  }

  const contactIds = new Set();
  for (const patch of document.contactPatches ?? []) {
    if (contactIds.has(patch.id)) errors.push(`duplicate contact id ${patch.id}`);
    contactIds.add(patch.id);
    if (!fingerIds.has(patch.fingerRef)) errors.push(`${patch.id} references missing finger ${patch.fingerRef}`);
    if (tipByFinger.get(patch.fingerRef) !== patch.tipSocket) errors.push(`${patch.id} tipSocket does not match ${patch.fingerRef}`);
    const length = Math.hypot(...(patch.targetNormalLocal ?? []));
    if (Math.abs(length - 1) > 1e-6) errors.push(`${patch.id} targetNormalLocal is not unit length`);
    if (patch.separationRangeM?.minimum > patch.separationRangeM?.maximum) errors.push(`${patch.id} separation minimum exceeds maximum`);
  }

  const orderedPhases = ['approach', 'closure', 'hold', 'release'].map(id => ({ id, ...document.phases?.[id] }));
  for (const phase of orderedPhases) if (phase.start > phase.end) errors.push(`${phase.id} phase start exceeds end`);
  for (let index = 1; index < orderedPhases.length; index += 1) {
    if (orderedPhases[index].start <= orderedPhases[index - 1].end) errors.push(`${orderedPhases[index].id} phase overlaps or reverses ${orderedPhases[index - 1].id}`);
  }

  if ((document.acceptance?.minimumActiveContacts ?? 0) > (document.contactPatches?.length ?? 0)) errors.push('minimumActiveContacts exceeds declared contact patch count');
  const normals = (document.contactPatches ?? []).map(patch => patch.targetNormalLocal);
  let maximumAngle = 0;
  for (let left = 0; left < normals.length; left += 1) for (let right = left + 1; right < normals.length; right += 1) {
    const dot = Math.max(-1, Math.min(1, normals[left].reduce((sum, value, axis) => sum + value * normals[right][axis], 0)));
    maximumAngle = Math.max(maximumAngle, Math.acos(dot) * 180 / Math.PI);
  }
  if (maximumAngle < (document.acceptance?.minimumOpposingNormalAngleDeg ?? 180)) errors.push(`maximum opposing-normal angle ${maximumAngle.toFixed(6)} deg is below threshold`);
  return errors;
}

function validateDocument(document) {
  const schemaPass = validateSchema(document);
  const schemaErrors = schemaPass ? [] : (validateSchema.errors ?? []).map(error => `${error.instancePath || '/'} ${error.message}`);
  const semantics = schemaPass ? semanticErrors(document) : [];
  return { pass: schemaPass && semantics.length === 0, schemaErrors, semanticErrors: semantics };
}

const clone = value => JSON.parse(JSON.stringify(value));
function runSelfTest(validFixture) {
  const mutations = [
    ['GENERIC_LIMIT_SOURCE', doc => { doc.solverPolicy.jointLimitSource = 'LIMIT_ROTATION_CONSTRAINT'; }],
    ['REVERSED_JOINT_RANGE', doc => { doc.fingerChains[0].bones[0].minimumDeg = 80; }],
    ['REST_OUTSIDE_LIMIT', doc => { doc.fingerChains[0].bones[0].restDeg = 90; }],
    ['NON_UNIT_NORMAL', doc => { doc.contactPatches[0].targetNormalLocal = [-2, 0, 0]; }],
    ['PARALLEL_NORMALS', doc => { doc.contactPatches[0].targetNormalLocal = [1, 0, 0]; }],
    ['MISSING_FINGER_REF', doc => { doc.contactPatches[0].fingerRef = 'FINGER_MISSING'; }],
    ['OVERLAPPING_PHASES', doc => { doc.phases.closure.start = 30; }],
    ['STRETCH_ENABLED', doc => { doc.solverPolicy.allowStretch = true; }],
  ];
  return mutations.map(([id, mutate]) => {
    const document = clone(validFixture);
    mutate(document);
    const result = validateDocument(document);
    return { id, rejected: !result.pass, errors: [...result.schemaErrors, ...result.semanticErrors] };
  });
}

const args = process.argv.slice(2);
const outputIndex = args.indexOf('--output');
const outputPath = outputIndex >= 0 && args[outputIndex + 1] ? resolve(process.cwd(), args[outputIndex + 1]) : null;
const fixtureArg = args.find((value, index) => !value.startsWith('--') && index !== outputIndex + 1);
const fixturePath = fixtureArg ? resolve(process.cwd(), fixtureArg) : defaultFixture;
const document = JSON.parse(await readFile(fixturePath, 'utf8'));
const result = validateDocument(document);
if (!result.pass) {
  process.stderr.write(`${JSON.stringify({ fixturePath, ...result }, null, 2)}\n`);
  process.exitCode = 1;
} else if (args.includes('--self-test')) {
  const tests = runSelfTest(document);
  const passed = tests.every(test => test.rejected);
  const serialized = `${JSON.stringify({ documentType: 'BFS_GRASP_SPEC_VALIDATOR_SELF_TEST', fixturePath: fixturePath.replace(`${repositoryRoot}/`, ''), validFixturePassed: true, tests, passed }, null, 2)}\n`;
  if (outputPath) await writeFile(outputPath, serialized);
  process.stdout.write(serialized);
  if (!passed) process.exitCode = 1;
} else {
  process.stdout.write(`GRASP_SPEC_OK ${fixturePath}\n`);
}
