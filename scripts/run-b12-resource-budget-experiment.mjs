import { access, mkdir, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';

const experimentRoot = resolve(repositoryRoot, 'experiments/resource-budget-v0-1');
const workRoot = resolve(experimentRoot, 'work');
const fixture = resolve(repositoryRoot, 'scripts/fixtures/b12-resource-worker.mjs');
const profilePath = resolve(repositoryRoot, 'specs/restricted-compile-budget.v0.1.json');
const plan = resolve(repositoryRoot, 'experiments/compiler-v0-1/plans/B01.build-plan.json');
const restrictedCli = resolve(repositoryRoot, 'scripts/run-restricted-blender-compile.mjs');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) { if (candidate === 'blender') return candidate; try { await access(candidate, constants.X_OK); return candidate; } catch {} }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}
const generous = { wallTimeMs: 5000, maxRssBytes: 2147483648, maxLogBytes: 2097152, maxOutputFiles: 64, maxOutputBytes: 134217728, sampleIntervalMs: 50 };
const makeOutput = async name => { const path = resolve(workRoot, name); await mkdir(path, { recursive: true }); return path; };
const runFixture = async (name, mode, budgetOverrides) => {
  const outputRoot = await makeOutput(name);
  return runBudgetedProcess({ command: process.execPath, args: [fixture, '--', '--mode', mode, '--output', outputRoot], cwd: repositoryRoot, outputRoot, budgets: { ...generous, ...budgetOverrides } });
};
const runCommand = (command, args) => new Promise((resolvePromise, reject) => {
  const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  child.stdout.on('data', chunk => { output += chunk; });
  child.stderr.on('data', chunk => { output += chunk; });
  child.on('error', reject);
  child.on('close', code => resolvePromise({ code, output }));
});

await rm(workRoot, { recursive: true, force: true });
await mkdir(workRoot, { recursive: true });
const blender = await findBlender();
const negativeTests = [];

const timeoutRoot = await makeOutput('N_TIMEOUT');
const timeout = await runBudgetedProcess({ command: blender, args: ['--background', '--factory-startup', '--disable-autoexec', '--python-expr', 'import time; time.sleep(2)'], cwd: repositoryRoot, outputRoot: timeoutRoot, budgets: { ...generous, wallTimeMs: 250 } });
negativeTests.push({ id: 'N_TIMEOUT', expectedReason: 'WALL_TIME', pass: timeout.outcome === 'BUDGET_EXCEEDED' && timeout.breach?.reason === 'WALL_TIME' && timeout.termination.requested && timeout.termination.awaited, result: timeout });

const logRoot = await makeOutput('N_LOG_BYTES');
const log = await runBudgetedProcess({ command: blender, args: ['--background', '--factory-startup', '--disable-autoexec', '--python-expr', "import time; print('X' * 262144); time.sleep(2)"], cwd: repositoryRoot, outputRoot: logRoot, budgets: { ...generous, maxLogBytes: 8192 } });
negativeTests.push({ id: 'N_LOG_BYTES', expectedReason: 'LOG_BYTES', pass: log.outcome === 'BUDGET_EXCEEDED' && log.breach?.reason === 'LOG_BYTES' && log.termination.requested && log.termination.awaited, result: log });

for (const [id, mode, override, reason] of [
  ['N_OUTPUT_FILES', 'OUTPUT_FILES', { maxOutputFiles: 4 }, 'OUTPUT_FILES'],
  ['N_OUTPUT_BYTES', 'OUTPUT_BYTES', { maxOutputBytes: 65536 }, 'OUTPUT_BYTES'],
  ['N_RSS', 'RSS', { maxRssBytes: 50331648 }, 'RSS_BYTES'],
]) {
  const result = await runFixture(id, mode, override);
  negativeTests.push({ id, expectedReason: reason, pass: result.outcome === 'BUDGET_EXCEEDED' && result.breach?.reason === reason && result.termination.requested && result.termination.awaited, result });
}
const nonzero = await runFixture('N_NONZERO_EXIT', 'NONZERO_EXIT', {});
negativeTests.push({ id: 'N_NONZERO_EXIT', expectedReason: 'CHILD_FAILED', pass: nonzero.outcome === 'CHILD_FAILED' && nonzero.child.exitCode === 7 && !nonzero.termination.requested, result: nonzero });

const positiveOutput = await makeOutput('B01-positive');
const positiveReport = resolve(workRoot, 'B01-positive.budget.json');
const positiveCli = await runCommand(process.execPath, [restrictedCli, '--plan', plan, '--output-dir', positiveOutput, '--report', positiveReport]);
const positive = JSON.parse(await readFile(positiveReport, 'utf8'));
const manifest = positive.outcome === 'PASS' ? JSON.parse(await readFile(resolve(positiveOutput, 'scene.manifest.json'), 'utf8')) : null;
const expectedStructure = 'c699fc27230d8dc378a9d4e6aa23a6425cc7007c0ee33a3172b6928f8e1b7f0b';
const positiveControl = { pass: positiveCli.code === 0 && positive.outcome === 'PASS' && manifest?.structureHash === expectedStructure, cliExitCode: positiveCli.code, cliOutput: positiveCli.output, expectedStructureHash: expectedStructure, observedStructureHash: manifest?.structureHash ?? null, result: positive };
const uniqueEscape = `${process.pid}-${Date.now()}`;
const escapedReport = `/tmp/bfs-b12-report-escape-${uniqueEscape}.json`;
const escapedOutput = `/tmp/bfs-b12-output-escape-${uniqueEscape}`;
const safeRegressionReport = resolve(workRoot, 'path-regression.report.json');
const reportEscapeCli = await runCommand(process.execPath, [restrictedCli, '--plan', plan, '--output-dir', resolve(workRoot, 'REPORT_ESCAPE-output'), '--report', escapedReport]);
const outputEscapeCli = await runCommand(process.execPath, [restrictedCli, '--plan', plan, '--output-dir', escapedOutput, '--report', safeRegressionReport]);
const planSymlink = resolve(workRoot, 'B01-plan-symlink.json');
await symlink(plan, planSymlink);
const planSymlinkCli = await runCommand(process.execPath, [restrictedCli, '--plan', planSymlink, '--output-dir', resolve(workRoot, 'PLAN_SYMLINK-output'), '--report', safeRegressionReport]);
const escapedReportExists = await access(escapedReport, constants.F_OK).then(() => true).catch(() => false);
const escapedOutputExists = await access(escapedOutput, constants.F_OK).then(() => true).catch(() => false);
const pathSecurityTests = [
  { id: 'REPORT_ESCAPE', pass: reportEscapeCli.code !== 0 && reportEscapeCli.output.includes('Restricted compile report must resolve below the repository root') && !escapedReportExists, observed: reportEscapeCli.output.trim(), externalTargetExists: escapedReportExists },
  { id: 'OUTPUT_ESCAPE', pass: outputEscapeCli.code !== 0 && outputEscapeCli.output.includes('Restricted compile output must resolve below the repository root') && !escapedOutputExists, observed: outputEscapeCli.output.trim(), externalTargetExists: escapedOutputExists },
  { id: 'PLAN_SYMLINK', pass: planSymlinkCli.code !== 0 && planSymlinkCli.output.includes('BuildPlan must not traverse symbolic links'), observed: planSymlinkCli.output.trim(), externalTargetExists: false },
];
const pathSecurityRegression = { pass: pathSecurityTests.every(test => test.pass), tests: pathSecurityTests };
const profileBytes = await readFile(profilePath);
const report = {
  documentType: 'BFS_B12_RESOURCE_BUDGET_EXPERIMENT', version: '0.1.0', executedAtUtc: new Date().toISOString(),
  environment: { platform: `${process.platform}-${process.arch}`, node: process.version },
  profile: { uri: 'specs/restricted-compile-budget.v0.1.json', sha256: createHash('sha256').update(profileBytes).digest('hex'), value: JSON.parse(profileBytes) },
  negativeTests, positiveControl, pathSecurityRegression,
  allNegativeTestsPassed: negativeTests.every(test => test.pass),
  formalB12Complete: negativeTests.every(test => test.pass) && positiveControl.pass && pathSecurityRegression.pass,
  nonClaimsPreserved: true,
};
await writeFile(resolve(experimentRoot, 'results.json'), serialize(report));
process.stdout.write(`BFS_B12_RESOURCE_BUDGET ${report.formalB12Complete ? 'FORMAL_TRUE' : 'FAILED'} ${negativeTests.filter(test => test.pass).length}/${negativeTests.length} negatives\n`);
if (!report.formalB12Complete) process.exitCode = 1;
