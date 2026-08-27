#!/usr/bin/env node
// Generic scalar-Node B52-D11.1 temporal accumulator.

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const SPEC_SHA256 = 'c4cb343672f53660d7c4ab69ccd489e00bb211e4aa1f489429f7a626ee48c42a';
const INPUTS = {
  previousRgba: ['previous.rgba32', 4],
  currentRgba: ['current.rgba32', 4],
  previousDepth: ['previous-depth.f32', 1],
  currentDepth: ['current-depth.f32', 1],
  previousLayer: ['previous-layer.f32', 1],
  currentLayer: ['current-layer.f32', 1],
  motion: [null, 2],
};
const OUTPUTS = {
  validity: 'validity.u8',
  reason: 'reason.u8',
  resolvedRgba: 'resolved.rgba32',
  naiveRgba: 'naive.rgba32',
  wrongSignRgba: 'wrong-sign.rgba32',
};
const REASONS = { VALID: 0, INVALID_BOUNDS: 1, INVALID_LAYER: 2, INVALID_DEPTH: 3, INVALID_ALPHA: 4 };

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
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

function readFloat32(filename, count) {
  const payload = fs.readFileSync(filename);
  if (payload.length !== count * 4) throw new Error(`unexpected float32 payload size: ${filename}`);
  const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  const values = new Float32Array(count);
  for (let index = 0; index < count; index += 1) values[index] = view.getFloat32(index * 4, true);
  return values;
}

function encodeFloat32(values) {
  const payload = Buffer.alloc(values.length * 4);
  const view = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  for (let index = 0; index < values.length; index += 1) view.setFloat32(index * 4, values[index], true);
  return payload;
}

function accumulate(arrays, width, height, integerizer, sign = 1, naive = false) {
  const resolved = new Float32Array(arrays.currentRgba);
  const validity = new Uint8Array(width * height);
  const reasons = new Uint8Array(width * height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = y * width + x;
      const dx = integerizer(arrays.motion[index * 2]);
      const dy = integerizer(arrays.motion[index * 2 + 1]);
      const qx = x - sign * dx;
      const qy = y + sign * dy;
      let reason;
      if (!(qx >= 0 && qx < width && qy >= 0 && qy < height)) {
        reason = 'INVALID_BOUNDS';
      } else {
        const previousIndex = qy * width + qx;
        if (naive) reason = 'VALID';
        else if (arrays.previousLayer[previousIndex] !== arrays.currentLayer[index]) reason = 'INVALID_LAYER';
        else if (Math.abs(arrays.previousDepth[previousIndex] - arrays.currentDepth[index]) > Math.max(1, arrays.currentDepth[index]) / 1024) reason = 'INVALID_DEPTH';
        else if (arrays.previousRgba[previousIndex * 4 + 3] <= 0 || arrays.currentRgba[index * 4 + 3] <= 0) reason = 'INVALID_ALPHA';
        else reason = 'VALID';
      }
      reasons[index] = REASONS[reason];
      if (reason === 'VALID') {
        validity[index] = 1;
        const previousIndex = qy * width + qx;
        for (let channel = 0; channel < 4; channel += 1) {
          resolved[index * 4 + channel] = Math.fround(
            0.5 * arrays.currentRgba[index * 4 + channel] + 0.5 * arrays.previousRgba[previousIndex * 4 + channel],
          );
        }
      }
    }
  }
  return { validity, reasons, resolved };
}

const args = argumentsFrom(process.argv.slice(2));
const required = ['--spec', '--fixture', '--repeat', '--input-dir', '--adapter-report', '--quantized-motion', '--quantizer-report', '--output-dir', '--report'];
if (required.some(key => !args[key])) throw new Error('missing required D11 accumulator argument');
const spec = JSON.parse(fs.readFileSync(args['--spec'], 'utf8'));
const fixture = spec.fixtures.find(item => item.id === args['--fixture']);
const repeat = Number(args['--repeat']);
if (shaFile(args['--spec']) !== SPEC_SHA256 || !fixture || ![1, 2].includes(repeat)) throw new Error('B52-D11.1 spec, fixture or repeat identity mismatch');
if (shaFile(process.execPath) !== spec.runtime.node.sha256) throw new Error('Node runtime identity mismatch');
if (fs.existsSync(args['--output-dir']) || fs.existsSync(args['--report'])) throw new Error('refusing to overwrite D11 Node accumulator output');
const adapter = JSON.parse(fs.readFileSync(args['--adapter-report'], 'utf8'));
const adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
if (adapter.reportHash !== sha(Buffer.from(stable(adapterBody))) || adapter.fixtureId !== args['--fixture'] || adapter.repeat !== repeat) throw new Error('adapter report identity mismatch');
const quantizer = JSON.parse(fs.readFileSync(args['--quantizer-report'], 'utf8'));
const quantizerBody = Object.fromEntries(Object.entries(quantizer).filter(([key]) => key !== 'reportHash'));
if (quantizer.reportHash !== sha(Buffer.from(stable(quantizerBody)))) throw new Error('quantizer report self-hash mismatch');
if (quantizer.producer !== 'node' || quantizer.fixtureId !== args['--fixture'] || quantizer.repeat !== repeat) throw new Error('Node quantizer report identity mismatch');
const rawMotionPath = path.join(args['--input-dir'], 'motion.xy32');
if (quantizer.input.sha256 !== shaFile(rawMotionPath) || quantizer.output.sha256 !== shaFile(args['--quantized-motion'])) {
  throw new Error('Node quantizer input/output binding mismatch');
}

const [width, height] = spec.scene.resolution;
const arrays = {};
const inputs = {};
for (const [name, [filename, components]] of Object.entries(INPUTS)) {
  const inputPath = name === 'motion' ? args['--quantized-motion'] : path.join(args['--input-dir'], filename);
  if (name === 'motion') {
    if (quantizer.output.sha256 !== shaFile(inputPath)) throw new Error('quantized motion binding mismatch');
  } else if (adapter.arrays[name].sha256 !== shaFile(inputPath)) throw new Error(`adapter array binding mismatch: ${name}`);
  arrays[name] = readFloat32(inputPath, width * height * components);
  const stat = fs.statSync(inputPath);
  inputs[name] = { uri: inputPath, sha256: shaFile(inputPath), bytes: stat.size };
}

const base = accumulate(arrays, width, height, Math.trunc);
const naive = accumulate(arrays, width, height, Math.trunc, 1, true);
const wrong = accumulate(arrays, width, height, Math.trunc, -1, false);
const payloads = {
  validity: Buffer.from(base.validity),
  reason: Buffer.from(base.reasons),
  resolvedRgba: encodeFloat32(base.resolved),
  naiveRgba: encodeFloat32(naive.resolved),
  wrongSignRgba: encodeFloat32(wrong.resolved),
};
fs.mkdirSync(args['--output-dir'], { recursive: true });
const records = {};
for (const [name, filename] of Object.entries(OUTPUTS)) {
  const outputPath = path.join(args['--output-dir'], filename);
  fs.writeFileSync(outputPath, payloads[name]);
  records[name] = { uri: outputPath, sha256: shaFile(outputPath), bytes: payloads[name].length };
}
const validPixels = base.validity.reduce((sum, value) => sum + value, 0);
const body = {
  schemaVersion: 'bfs.blenderNearestIntegerTemporalRecoveryNodeAccumulatorReport.v0.1',
  experimentId: spec.experimentId,
  fixtureId: args['--fixture'],
  repeat,
  producer: 'node',
  pid: process.pid,
  runtime: { node: process.version, nodeExecutableSha256: shaFile(process.execPath) },
  adapterReport: { uri: args['--adapter-report'], sha256: shaFile(args['--adapter-report']) },
  quantizerReport: { uri: args['--quantizer-report'], sha256: shaFile(args['--quantizer-report']) },
  inputs,
  integerization: 'JavaScript Math.trunc() toward zero',
  outputs: records,
  metrics: {
    validPixels,
    invalidPixels: base.validity.length - validPixels,
    quantizedMotionIntegral: Array.from(arrays.motion).every(value => Number.isFinite(value) && value === Math.trunc(value)),
  },
  operationCounts: { pythonAccumulatorProcesses: 0, nodeAccumulatorProcesses: 1, modelCalls: 0, networkCalls: 0 },
};
const report = { ...body, reportHash: sha(Buffer.from(stable(body))) };
fs.mkdirSync(path.dirname(args['--report']), { recursive: true });
fs.writeFileSync(args['--report'], `${JSON.stringify(report, null, 2)}\n`);
console.log(`BFS_B52_D11_1_NODE_OK fixture=${args['--fixture']} repeat=${repeat} valid=${validPixels}/${base.validity.length} resolved=${records.resolvedRgba.sha256}`);
