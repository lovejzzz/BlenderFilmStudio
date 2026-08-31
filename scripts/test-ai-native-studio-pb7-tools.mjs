#!/usr/bin/env node
import { strict as assert } from 'node:assert';
import { humanVerdict, validateHumanInput } from './lib/ai-native-studio-pb7.mjs';
import { auditAnswerMapping } from './audit-ai-native-studio-pb7.mjs';

const answers = (q1, q2, q3, q4) => ({ Q1: q1, Q2: q2, Q3: q3, Q4: q4 });
const input = values => ({ schemaVersion: 'bfs.pb7HumanReviewInput.v0.1', reviewerRole: 'project owner and human viewer', sourceMessageText: 'exact human response', answers: values, optionalNotes: '' });
const cases = [
  [answers('YES', 'YES', 'YES', 'YES'), 'PASS'],
  [answers('YES', 'NO', 'YES', 'YES'), 'FAIL'],
  [answers('UNCERTAIN', 'YES', 'YES', 'YES'), 'BLOCKED'],
  [answers('YES', 'YES', 'UNVIEWABLE', 'YES'), 'BLOCKED'],
  [answers('NO', 'UNCERTAIN', 'UNVIEWABLE', 'YES'), 'FAIL'],
];
for (const [values, expected] of cases) {
  assert.equal(validateHumanInput(input(values)).valid, true);
  assert.equal(humanVerdict(values), expected);
  assert.equal(auditAnswerMapping(values), expected);
}
assert.equal(validateHumanInput(input({ Q1: 'YES', Q2: 'YES', Q3: 'YES' })).valid, false);
assert.equal(validateHumanInput(input(answers('yes', 'YES', 'YES', 'YES'))).valid, false);
assert.equal(validateHumanInput({ ...input(answers('YES', 'YES', 'YES', 'YES')), extra: true }).valid, false);
assert.throws(() => auditAnswerMapping({ ...answers('YES', 'YES', 'YES', 'YES'), Q5: 'YES' }), /ANSWER_KEYS/);
assert.throws(() => auditAnswerMapping(answers('yes', 'YES', 'YES', 'YES')), /ANSWER_TOKEN/);
process.stdout.write('BFS_PB7_TOOL_TEST PASS 20/20\n');
