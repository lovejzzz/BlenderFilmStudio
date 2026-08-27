#!/usr/bin/env node
// Bounded scalar-Node motion quantizer for B52-D11.1.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const SPEC_SHA256 = 'c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a';

function argumentsFrom(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) values[argv[index]] = argv[index + 1];
  return values;
}

function sha(payload) {
  return crypto.createHash('sha256').update(payload).digest('hex');
}

function shaFile(filename) {
  return sha(fs.readFileSync(filename));
}

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function nearestInteger(value) {
  return value >= 0 ? Math.floor(value + 0.5) : Math.ceil(value - 0.5);
}

function quantize(payload, radius) {
  if (payload.length % 4 !== 0) throw new Error('motion payload is not a whole little-endian float32 array');
  const input = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  const output = Buffer.alloc(payload.length);
  const outputView = new DataView(output.buffer, output.byteOffset, output.byteLength);
  let maximumError = 0;
  for (let index = 0; index < payload.length / 4; index += 1) {
    const value = input.getFloat32(index * 4, true);
    if (!Number.isFinite(value)) throw new Error(`QUANTIZER_DOMAIN nonfinite component=${index}`);
    const candidate = nearestInteger(value);
    const error = Math.abs(value - candidate);
    if (error > radius) {
      throw new Error(`QUANTIZER_DOMAIN component=${index} value=${value} candidate=${candidate} error=${error} radius=${radius}`);
    }
    maximumError = Math.max(maximumError, error);
    outputView.setFloat32(index * 4, candidate === 0 ? 0 : candidate, true);
  }
  const idempotent = quantizeIntegral(output);
  if (!idempotent.equals(output)) throw new Error('quantizer idempotence failure');
  return { output, maximumError };
}

function quantizeIntegral(payload) {
  const input = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  const output = Buffer.alloc(payload.length);
  const outputView = new DataView(output.buffer, output.byteOffset, output.byteLength);
  for (let index = 0; index < payload.length / 4; index += 1) {
    const value = input.getFloat32(index * 4, true);
    const candidate = nearestInteger(value);
    outputView.setFloat32(index * 4, candidate === 0 ? 0 : candidate, true);
  }
  return output;
}

const args = argumentsFrom(process.argv.slice(2));
const required = ['--spec', '--fixture', '--repeat', '--input', '--adapter-report', '--output', '--report'];
if (required.some(key => !args[key])) throw new Error('missing required D11.1 quantizer argument');
const spec = JSON.parse(fs.readFileSync(args['--spec'], 'utf8'));
const fixture = spec.fixtures.find(item => item.id === args['--fixture']);
const repeat = Number(args['--repeat']);
if (shaFile(args['--spec']) !== SPEC_SHA256 || !fixture || ![1, 2].includes(repeat)) {
  throw new Error('B52-D11.1 spec, fixture or repeat identity mismatch');
}
if (shaFile(process.execPath) !== spec.runtime.node.sha256) throw new Error('Node runtime identity mismatch');
if (fs.existsSync(args['--output']) || fs.existsSync(args['--report'])) {
  throw new Error('refusing to overwrite D11.1 Node quantizer output');
}

const adapter = JSON.parse(fs.readFileSync(args['--adapter-report'], 'utf8'));
const adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
if (adapter.reportHash !== sha(Buffer.from(stable(adapterBody)))) throw new Error('adapter report self-hash mismatch');
if (adapter.fixtureId !== args['--fixture'] || adapter.repeat !== repeat) throw new Error('adapter report cell mismatch');
if (adapter.arrays.motion.sha256 !== shaFile(args['--input'])) throw new Error('adapter motion binding mismatch');

const [width, height] = spec.scene.resolution;
const payload = fs.readFileSync(args['--input']);
if (payload.length !== width * height * 2 * 4) throw new Error('motion input size mismatch');
const radius = spec.quantizerContract.acceptanceRadiusPixels;
const { output, maximumError } = quantize(payload, radius);

fs.mkdirSync(path.dirname(args['--output']), { recursive: true });
fs.writeFileSync(args['--output'], output);
const outputRecord = {
  uri: args['--output'], sha256: shaFile(args['--output']), bytes: output.length,
  shape: [height, width, 2], dtype: 'little-endian-float32',
};
const body = {
  schemaVersion: 'bfs.blenderNearestIntegerTemporalRecoveryNodeQuantizerReport.v0.1',
  experimentId: spec.experimentId,
  fixtureId: args['--fixture'],
  repeat,
  producer: 'node',
  pid: process.pid,
  runtime: { node: process.version, nodeExecutableSha256: shaFile(process.execPath) },
  adapterReport: { uri: args['--adapter-report'], sha256: shaFile(args['--adapter-report']) },
  input: { uri: args['--input'], sha256: shaFile(args['--input']), bytes: payload.length },
  output: outputRecord,
  quantizer: {
    candidate: 'value >= 0 ? floor(value + 0.5) : ceil(value - 0.5)',
    acceptanceRadiusPixels: radius,
    wholeArrayAccepted: true,
    positiveZeroCanonical: true,
    idempotent: true,
  },
  metrics: { componentCount: payload.length / 4, maximumAbsoluteQuantizationErrorPixelsDecimal: maximumError.toFixed(18) },
  operationCounts: { pythonQuantizerProcesses: 0, nodeQuantizerProcesses: 1, modelCalls: 0, networkCalls: 0 },
};
const report = { ...body, reportHash: sha(Buffer.from(stable(body))) };
fs.mkdirSync(path.dirname(args['--report']), { recursive: true });
fs.writeFileSync(args['--report'], `${JSON.stringify(report, null, 2)}\n`);
console.log(
  `BFS_B52_D11_1_NODE_QUANTIZER_OK fixture=${args['--fixture']} repeat=${repeat} `
  + `components=${payload.length / 4} maxError=${maximumError} output=${outputRecord.sha256}`,
);
