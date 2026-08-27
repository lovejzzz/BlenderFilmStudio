#!/usr/bin/env node
/** Scalar Node static bilinear consumer for B52-D12.2. */

import crypto from 'node:crypto';
import fs from 'node:fs';
import process from 'node:process';

const SPEC_SHA256 = 'fa63daa0c3b7b3f080a488aa0fc84996fd52cd731efce94ebe28bbc81b55d9d3';
const INPUTS = {
  previousRgba: ['previous.rgba32', 4], currentRgba: ['current.rgba32', 4],
  previousOwner: ['previous-owner.f32', 1], currentOwner: ['current-owner.f32', 1], vector: ['vector.xy32', 2],
};

function parseArgs() {
  const result = {};
  for (let index = 2; index < process.argv.length; index += 2) result[process.argv[index].replace(/^--/, '')] = process.argv[index + 1];
  for (const key of ['spec', 'fixture', 'repeat', 'input-dir', 'adapter-report', 'output-dir', 'report']) if (!(key in result)) throw new Error(`missing --${key}`);
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) throw new Error('repeat outside D12.2 roster');
  return result;
}

function shaBytes(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function shaFile(path) { return shaBytes(fs.readFileSync(path)); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function canonicalHash(value) { return shaBytes(Buffer.from(stable(value))); }
function readF32(path) {
  const buffer = fs.readFileSync(path), values = new Float32Array(buffer.length / 4);
  for (let index = 0; index < values.length; index++) values[index] = buffer.readFloatLE(index * 4);
  return { buffer, values };
}
function encodeF32(values) {
  const buffer = Buffer.alloc(values.length * 4);
  for (let index = 0; index < values.length; index++) buffer.writeFloatLE(values[index], index * 4);
  return buffer;
}
function pixelBase(width, x, y, channels) { return (y * width + x) * channels; }

function main() {
  const args = parseArgs(), specBuffer = fs.readFileSync(args.spec);
  if (shaBytes(specBuffer) !== SPEC_SHA256) throw new Error('B52-D12.2 spec identity mismatch');
  const spec = JSON.parse(specBuffer);
  if (process.version !== spec.runtime.node.version || shaFile(process.execPath) !== spec.runtime.node.sha256) throw new Error('Node runtime identity mismatch');
  const fixture = spec.fixtures.find(row => row.id === args.fixture);
  if (!fixture) throw new Error('fixture outside D12.2 roster');
  if (fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) throw new Error('refusing to overwrite D12.2 consumer output');
  const adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8'));
  const adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) throw new Error('D12.2 adapter identity mismatch');
  const [width, height] = fixture.resolution, arrays = {};
  for (const [name, [filename]] of Object.entries(INPUTS)) {
    const loaded = readF32(`${args['input-dir']}/${filename}`);
    if (shaBytes(loaded.buffer) !== adapter.arrays[name].sha256) throw new Error(`D12.2 adapter array mismatch: ${name}`);
    arrays[name] = loaded.values;
  }
  const previous = arrays.previousRgba, current = arrays.currentRgba;
  const reconstructed = new Float32Array(current), valid = new Uint8Array(width * height);
  const ownerId = Math.fround(fixture.passIndex), margin = 4;
  for (let y = margin; y < height - margin; y++) for (let x = margin; x < width - margin; x++) {
    const pixel = y * width + x, currentBase = pixel * 4;
    if (arrays.currentOwner[pixel] !== ownerId || current[currentBase + 3] <= Math.fround(0.999)) continue;
    const vectorX = arrays.vector[pixel * 2], vectorY = arrays.vector[pixel * 2 + 1];
    const qx = x + vectorX, qy = y - vectorY, x0 = Math.floor(qx), y0 = Math.floor(qy), x1 = x0 + 1, y1 = y0 + 1;
    if (x0 < 0 || y0 < 0 || x1 >= width || y1 >= height) continue;
    const taps = [[y0, x0], [y0, x1], [y1, x0], [y1, x1]];
    if (!taps.every(([ty, tx]) => {
      const tap = ty * width + tx;
      return arrays.previousOwner[tap] === ownerId && previous[tap * 4 + 3] > Math.fround(0.999);
    })) continue;
    const fx = qx - x0, fy = qy - y0;
    const w0 = (1 - fx) * (1 - fy), w1 = fx * (1 - fy), w2 = (1 - fx) * fy, w3 = fx * fy;
    for (let channel = 0; channel < 4; channel++) {
      const v0 = previous[pixelBase(width, x0, y0, 4) + channel], v1 = previous[pixelBase(width, x1, y0, 4) + channel];
      const v2 = previous[pixelBase(width, x0, y1, 4) + channel], v3 = previous[pixelBase(width, x1, y1, 4) + channel];
      reconstructed[currentBase + channel] = Math.fround((((v0 * w0) + (v1 * w1)) + (v2 * w2)) + (v3 * w3));
    }
    valid[pixel] = 1;
  }
  fs.mkdirSync(args['output-dir'], { recursive: true });
  const reconstructedPayload = encodeF32(reconstructed), validPayload = Buffer.from(valid);
  const reconstructedPath = `${args['output-dir']}/reconstructed.rgba32`, validPath = `${args['output-dir']}/valid.u8`;
  fs.writeFileSync(reconstructedPath, reconstructedPayload); fs.writeFileSync(validPath, validPayload);
  const report = {
    schemaVersion: 'bfs.blenderStaticVectorFloorConsumerReport.v0.1', experimentId: spec.experimentId, producer: 'node', fixtureId: args.fixture,
    repeat: args.repeat, pid: process.pid, runtime: { node: process.version, nodeExecutableSha256: shaFile(process.execPath) },
    adapter: { uri: args['adapter-report'], sha256: shaFile(args['adapter-report']), reportHash: adapter.reportHash }, contract: spec.consumer,
    arrays: {
      reconstructed: { uri: reconstructedPath, sha256: shaBytes(reconstructedPayload), bytes: reconstructedPayload.length, shape: [height, width, 4], dtype: 'little-endian-float32' },
      valid: { uri: validPath, sha256: shaBytes(validPayload), bytes: validPayload.length, shape: [height, width], dtype: 'uint8' },
    },
    integrity: 'external dual typed-envelope sidecars', operationCounts: { consumerProcesses: 1, pixelsVisited: width * height, modelCalls: 0, networkCalls: 0 },
  };
  fs.mkdirSync(args.report.slice(0, args.report.lastIndexOf('/')), { recursive: true });
  fs.writeFileSync(args.report, `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`BFS_B52_D122_CONSUMER_NODE_OK fixture=${args.fixture} repeat=${args.repeat} valid=${valid.reduce((a, b) => a + b, 0)}\n`);
}

main();
