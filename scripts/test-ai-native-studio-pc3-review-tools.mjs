#!/usr/bin/env node
import { validateHumanInput } from './lib/ai-native-studio-pc3-review.mjs';
import { auditAnswerMapping } from './audit-ai-native-studio-pc3-review.mjs';

const base = { schemaVersion: 'bfs.pc3HumanReviewInput.v0.1', reviewerRole: 'project-owner', sourceMessageText: 'YES YES YES YES', answers: { Q1: 'YES', Q2: 'YES', Q3: 'YES', Q4: 'YES' }, optionalNotes: '' };
const cases = [];
const gate = (id, pass) => cases.push({ id, pass: Boolean(pass) });
gate('RECORDER_ALL_YES_PASS', validateHumanInput(base).verdict === 'PASS'); gate('AUDITOR_ALL_YES_PASS', auditAnswerMapping(base.answers) === 'PASS');
for (const id of ['Q1', 'Q2', 'Q3', 'Q4']) { const input = structuredClone(base); input.answers[id] = 'NO'; gate(`RECORDER_${id}_NO_FAIL`, validateHumanInput(input).verdict === 'FAIL'); gate(`AUDITOR_${id}_NO_FAIL`, auditAnswerMapping(input.answers) === 'FAIL'); }
for (const token of ['yes', 'UNCERTAIN', 'UNVIEWABLE', 'MAYBE']) { const input = structuredClone(base); input.answers.Q1 = token; gate(`RECORDER_REJECT_${token}`, !validateHumanInput(input).valid); let rejected = false; try { auditAnswerMapping(input.answers); } catch { rejected = true; } gate(`AUDITOR_REJECT_${token}`, rejected); }
{ const input = structuredClone(base); delete input.answers.Q4; gate('RECORDER_MISSING', !validateHumanInput(input).valid); let rejected = false; try { auditAnswerMapping(input.answers); } catch { rejected = true; } gate('AUDITOR_MISSING', rejected); }
{ const input = structuredClone(base); input.extra = true; gate('RECORDER_EXTRA_TOP', !validateHumanInput(input).valid); }
{ const input = structuredClone(base); input.answers.Q5 = 'YES'; gate('RECORDER_EXTRA_ANSWER', !validateHumanInput(input).valid); let rejected = false; try { auditAnswerMapping(input.answers); } catch { rejected = true; } gate('AUDITOR_EXTRA_ANSWER', rejected); }
const passed = cases.filter(row => row.pass).length; if (passed !== cases.length) { process.stderr.write(`${JSON.stringify(cases.filter(row => !row.pass))}\n`); process.exitCode = 1; } else process.stdout.write(`BFS_PC3_REVIEW_TOOL_TEST PASS ${passed}/${cases.length}\n`);
