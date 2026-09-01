import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { canonicalPlanBytesV2, compileVisualImprovementPlanV2Files, repositoryUriV2, resolveRepositoryUriV2 } from './lib/visual-review-improvement-v2.mjs';

const [packetArgument, assessmentArgument, outputArgument] = process.argv.slice(2);
if (!packetArgument || !assessmentArgument || !outputArgument) throw new Error('usage: node scripts/compile-visual-improvement-plan-v2.mjs <packet.json> <assessment.json> <output.json>');
const packetUri = repositoryUriV2(resolveRepositoryUriV2(packetArgument));
const assessmentUri = repositoryUriV2(resolveRepositoryUriV2(assessmentArgument));
const outputPath = resolveRepositoryUriV2(outputArgument);
const { plan } = await compileVisualImprovementPlanV2Files(packetUri, assessmentUri);
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, canonicalPlanBytesV2(plan), { flag: 'wx' });
process.stdout.write(`BFS_VISUAL_IMPROVEMENT_PLAN_V2 ${plan.decision} ${plan.operations.length} ${plan.planHash}\n`);
