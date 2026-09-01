import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import {
  canonicalPlanBytes,
  compileVisualImprovementPlanFiles,
  repositoryUri,
  resolveRepositoryUri,
} from './lib/visual-review-improvement.mjs';

const [packetArgument, assessmentArgument, outputArgument] = process.argv.slice(2);
if (!packetArgument || !assessmentArgument || !outputArgument) {
  throw new Error('usage: node scripts/compile-visual-improvement-plan.mjs <packet.json> <assessment.json> <output.json>');
}

const packetUri = repositoryUri(resolveRepositoryUri(packetArgument));
const assessmentUri = repositoryUri(resolveRepositoryUri(assessmentArgument));
const outputPath = resolveRepositoryUri(outputArgument);
const { plan } = await compileVisualImprovementPlanFiles(packetUri, assessmentUri);
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, canonicalPlanBytes(plan), { flag: 'wx' });
process.stdout.write(`BFS_VISUAL_IMPROVEMENT_PLAN ${plan.decision} ${plan.operations.length} ${plan.planHash}\n`);
