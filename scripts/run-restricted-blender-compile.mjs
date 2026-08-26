import { access, mkdir, readFile, readdir, realpath, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { runBudgetedProcess } from './lib/budgeted-process.mjs';
import { createCompileReceipt } from './lib/compile-receipt.mjs';

const profilePath = resolve(repositoryRoot, 'specs/restricted-compile-budget.v0.1.json');
const repositoryRealRoot = await realpath(repositoryRoot);

function assertBelowRepository(absolutePath, label) {
  const pathFromRoot = relative(repositoryRoot, absolutePath);
  if (pathFromRoot === '' || pathFromRoot === '..' || pathFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} must resolve below the repository root`);
}

function assertBelowRealRepository(actualPath, label, allowRoot = false) {
  const pathFromRoot = relative(repositoryRealRoot, actualPath);
  if ((!allowRoot && pathFromRoot === '') || pathFromRoot === '..' || pathFromRoot.startsWith(`..${sep}`)) throw new Error(`${label} resolves outside the repository root`);
}

async function assertTrustedExistingPath(absolutePath, label) {
  assertBelowRepository(absolutePath, label);
  const actualPath = await realpath(absolutePath).catch(() => { throw new Error(`${label} is missing`); });
  assertBelowRealRepository(actualPath, label);
  if (actualPath !== absolutePath) throw new Error(`${label} must not traverse symbolic links`);
  return actualPath;
}

async function assertTrustedOutputPath(absolutePath, label) {
  assertBelowRepository(absolutePath, label);
  let probe = absolutePath;
  let actualPath = null;
  while (!actualPath) {
    actualPath = await realpath(probe).catch(error => {
      if (error?.code !== 'ENOENT') throw error;
      const parent = dirname(probe);
      if (parent === probe) throw error;
      probe = parent;
      return null;
    });
  }
  assertBelowRealRepository(actualPath, label, probe === repositoryRoot);
  if (actualPath !== probe) throw new Error(`${label} must not traverse symbolic links`);
}

async function findBlender() {
  const candidates = [process.env.BLENDER_BIN, '/Applications/Blender.app/Contents/MacOS/Blender', 'blender'].filter(Boolean);
  for (const candidate of candidates) {
    if (candidate === 'blender') return candidate;
    try { await access(candidate, constants.X_OK); return candidate; } catch {}
  }
  throw new Error('Blender executable not found; set BLENDER_BIN');
}

export async function runRestrictedCompile({ plan, outputDir }) {
  const blender = await findBlender();
  const profileBytes = await readFile(profilePath);
  const budgets = JSON.parse(profileBytes);
  const compiler = resolve(repositoryRoot, 'blender/compile_scene.py');
  const ocio = resolve(repositoryRoot, 'color/ocio/cg-config-v4.0.0_aces-v2.0_ocio-v2.5.ocio');
  const trustedPlan = await assertTrustedExistingPath(resolve(plan), 'BuildPlan');
  const trustedOutput = resolve(outputDir);
  await assertTrustedOutputPath(trustedOutput, 'Restricted compile output');
  const existingEntries = await readdir(trustedOutput).catch(error => {
    if (error?.code === 'ENOENT') return [];
    throw error;
  });
  if (existingEntries.length > 0) throw new Error(`Restricted compile output must be empty: found ${existingEntries.sort().join(', ')}`);
  await mkdir(trustedOutput, { recursive: true });
  const result = await runBudgetedProcess({
    command: blender,
    args: ['--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', compiler, '--', '--plan', trustedPlan, '--repository-root', repositoryRoot, '--output-dir', trustedOutput],
    cwd: repositoryRoot, env: { ...process.env, OCIO: ocio }, outputRoot: trustedOutput, budgets,
  });
  return { ...result, budgetProfile: { uri: 'specs/restricted-compile-budget.v0.1.json', sha256: createHash('sha256').update(profileBytes).digest('hex') } };
}

async function main() {
  const args = process.argv.slice(2);
  const option = name => { const index = args.indexOf(name); return index >= 0 ? args[index + 1] : null; };
  const plan = option('--plan');
  const outputDir = option('--output-dir');
  const report = option('--report');
  const receipt = option('--receipt');
  if (!plan || !outputDir || !report || !receipt) throw new Error('Usage: --plan FILE --output-dir DIR --report FILE --receipt FILE');
  const trustedReport = resolve(report);
  const trustedReceipt = resolve(receipt);
  await assertTrustedOutputPath(trustedReport, 'Restricted compile report');
  await assertTrustedOutputPath(trustedReceipt, 'CompileReceipt output');
  if (trustedReport === trustedReceipt) throw new Error('Restricted compile report and CompileReceipt output must be different files');
  const result = await runRestrictedCompile({ plan, outputDir });
  await writeFile(trustedReport, `${JSON.stringify(result, null, 2)}\n`);
  let compileReceipt = null;
  if (result.outcome === 'PASS') {
    compileReceipt = await createCompileReceipt({ planPath: resolve(plan), outputDir: resolve(outputDir), budgetReportPath: trustedReport, budgetResult: result });
    await writeFile(trustedReceipt, `${JSON.stringify(compileReceipt, null, 2)}\n`);
  }
  process.stdout.write(`BFS_RESTRICTED_COMPILE ${result.outcome} ${result.breach?.reason ?? 'WITHIN_BUDGET'}${compileReceipt ? ` ${compileReceipt.receiptHash}` : ''}\n`);
  if (result.outcome !== 'PASS') process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { process.stderr.write(`BFS_RESTRICTED_COMPILE_ERROR ${error.message}\n`); process.exitCode = 1; });
}
