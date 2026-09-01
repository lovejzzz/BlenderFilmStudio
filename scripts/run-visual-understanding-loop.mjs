import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdir, readFile, writeFile, lstat } from 'node:fs/promises';
import { resolve } from 'node:path';
import {
  canonicalPlanBytes,
  compileVisualImprovementPlanFiles,
  repositoryUri,
  resolveRepositoryUri,
  sha256File,
} from './lib/visual-review-improvement.mjs';
import { canonicalize, canonicalJson, repositoryRoot, sha256 } from './lib/scene-spec.mjs';

const execFileAsync = promisify(execFile);
const freezeUri = 'specs/ai-native-studio-visual-understanding-tool-freeze-c2.v0.3.json';

function requireCondition(condition, message) {
  if (!condition) throw new Error(message);
}

function parseArguments(argv) {
  requireCondition(argv.length === 6, 'packet, assessment and output-root are required exactly once');
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    requireCondition(['--packet', '--assessment', '--output-root'].includes(key) && value, `invalid argument ${key ?? ''}`);
    const name = key.slice(2);
    requireCondition(!(name in values), `duplicate argument ${key}`);
    values[name] = value;
  }
  requireCondition(Object.keys(values).length === 3, 'packet, assessment and output-root are required exactly once');
  return values;
}

async function verifyFreeze() {
  const freezePath = resolveRepositoryUri(freezeUri);
  const freezeBytes = await readFile(freezePath);
  const freeze = JSON.parse(freezeBytes);
  requireCondition(freeze.schemaVersion === 'bfs.visualUnderstandingToolFreezeC2.v0.3', 'tool freeze schema mismatch');
  requireCondition(freeze.freezeHash === selfHash(freeze, 'freezeHash'), 'tool freeze self hash mismatch');
  for (const input of freeze.inputs) {
    requireCondition(await sha256File(resolveRepositoryUri(input.uri)) === input.sha256, `frozen input drift ${input.uri}`);
  }
  const { stdout } = await execFileAsync('git', ['show', `HEAD:${freezeUri}`], { cwd: repositoryRoot, encoding: 'buffer', maxBuffer: 8 * 1024 * 1024 });
  requireCondition(sha256(stdout) === sha256(freezeBytes), 'tool freeze is not exact at HEAD');
  return { freeze, freezeSha256: sha256(freezeBytes) };
}

function selfHash(value, key) {
  const projection = structuredClone(value);
  delete projection[key];
  return sha256(canonicalJson(projection));
}

const args = parseArguments(process.argv.slice(2));
const packetUri = repositoryUri(resolveRepositoryUri(args.packet));
const assessmentUri = repositoryUri(resolveRepositoryUri(args.assessment));
const outputRootUri = repositoryUri(resolveRepositoryUri(args['output-root']));
requireCondition(outputRootUri.startsWith('experiments/visual-understanding-loop/'), 'output root must be under experiments/visual-understanding-loop/');
const outputRoot = resolve(repositoryRoot, outputRootUri);
try {
  await lstat(outputRoot);
  throw new Error(`output root already exists: ${outputRootUri}`);
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}

const freeze = await verifyFreeze();
const first = await compileVisualImprovementPlanFiles(packetUri, assessmentUri);
const second = await compileVisualImprovementPlanFiles(packetUri, assessmentUri);
const firstBytes = canonicalPlanBytes(first.plan);
const secondBytes = canonicalPlanBytes(second.plan);
requireCondition(firstBytes.equals(secondBytes), 'repeated plan bytes differ');
const testRun = await execFileAsync(process.execPath, ['--test', 'tests/visual-review-improvement.test.mjs'], {
  cwd: repositoryRoot,
  encoding: 'utf8',
  maxBuffer: 8 * 1024 * 1024,
});
requireCondition(testRun.stderr === '' && testRun.stdout.includes('# pass 19') && testRun.stdout.includes('# fail 0'), 'contract tests did not pass 19/19');

await mkdir(resolve(outputRoot, 'logs'), { recursive: true });
await writeFile(resolve(outputRoot, 'visual-improvement-plan.json'), firstBytes, { flag: 'wx' });
await writeFile(resolve(outputRoot, 'logs/contract-tests.tap'), testRun.stdout, { flag: 'wx' });

const packetSha256 = await sha256File(resolveRepositoryUri(packetUri));
const assessmentSha256 = await sha256File(resolveRepositoryUri(assessmentUri));
const planSha256 = await sha256File(resolve(outputRoot, 'visual-improvement-plan.json'));
const testsSha256 = await sha256File(resolve(outputRoot, 'logs/contract-tests.tap'));
const receipt = {
  schemaVersion: 'bfs.visualUnderstandingLoopReceipt.v0.1',
  experimentId: 'PC4-VU1',
  status: 'PASS_PENDING_INDEPENDENT_AUDIT',
  preregistration: freeze.freeze.preregistration,
  toolFreeze: { uri: freezeUri, sha256: freeze.freezeSha256 },
  inputs: {
    packet: { uri: packetUri, sha256: packetSha256 },
    assessment: { uri: assessmentUri, sha256: assessmentSha256 },
    sceneSha256: first.plan.source.sceneSha256,
  },
  outputs: {
    plan: { uri: `${outputRootUri}/visual-improvement-plan.json`, sha256: planSha256, planHash: first.plan.planHash },
    contractTests: { uri: `${outputRootUri}/logs/contract-tests.tap`, sha256: testsSha256, passed: 19, failed: 0 },
  },
  compiler: {
    repeatedCanonicalBytesExact: true,
    decision: first.plan.decision,
    operationCount: first.plan.operations.length,
    preservationCount: first.plan.preservations.length,
    deferredIssueCount: first.plan.deferredIssues.length,
    rerenderFrameCount: first.plan.rerenderSet.length,
  },
  operationCounts: {
    nodeRunnerProcesses: 1,
    nodeTestProcesses: 1,
    blenderStarts: 0,
    renders: 0,
    sceneMutations: 0,
    networkCalls: 0,
    modelCallsDuringCompilerExecution: 0,
    shellOrPythonFromAssessment: 0,
  },
  authority: first.plan.authority,
  receiptHash: '',
};
receipt.receiptHash = selfHash(receipt, 'receiptHash');
await writeFile(resolve(outputRoot, 'receipt.json'), `${JSON.stringify(canonicalize(receipt), null, 2)}\n`, { flag: 'wx' });
process.stdout.write(`BFS_VISUAL_UNDERSTANDING_LOOP PASS_PENDING_INDEPENDENT_AUDIT ${first.plan.planHash} ${receipt.receiptHash}\n`);
