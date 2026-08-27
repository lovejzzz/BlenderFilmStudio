#!/usr/bin/env node
/** Independent scalar Node projective subpixel reconstructor for B52-D12. */

import fs from 'node:fs';
import crypto from 'node:crypto';
import process from 'node:process';

const SPEC_SHA256 = 'dd2e990d276e0ee5c2fee9d22cf42c7f84db2b6c1947b1219dceab06a76f66a2';
const INPUTS = {
  previousRgba: ['previous.rgba32', 4], currentRgba: ['current.rgba32', 4],
  previousDepth: ['previous-depth.f32', 1], currentDepth: ['current-depth.f32', 1],
  previousOwner: ['previous-owner.f32', 1], currentOwner: ['current-owner.f32', 1],
  vector: ['vector.xy32', 2],
};
const OUTPUTS = {
  reconstructed: ['reconstructed.rgba32', 'f32'], valid: ['valid.u8', 'u8'],
  expectedVector: ['expected-vector.xy32', 'f32'], predictedCurrentDepth: ['predicted-current-depth.f32', 'f32'],
  predictedPreviousDepth: ['predicted-previous-depth.f32', 'f32'], nearest: ['nearest.rgba32', 'f32'],
  wrongSign: ['wrong-sign.rgba32', 'f32'], directDepthValid: ['direct-depth-valid.u8', 'u8'],
};

function parseArgs() {
  const result = {};
  for (let i = 2; i < process.argv.length; i += 2) result[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
  for (const key of ['spec', 'fixture', 'repeat', 'input-dir', 'adapter-report', 'output-dir', 'report']) if (!(key in result)) throw new Error(`missing --${key}`);
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) throw new Error('repeat outside D12 roster');
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
  const buffer = fs.readFileSync(path);
  const result = new Float32Array(buffer.length / 4);
  for (let i = 0; i < result.length; i++) result[i] = buffer.readFloatLE(i * 4);
  return { buffer, values: result };
}
function encodeF32(values) {
  const buffer = Buffer.alloc(values.length * 4);
  for (let i = 0; i < values.length; i++) buffer.writeFloatLE(values[i], i * 4);
  return buffer;
}

function rotationXyz(values) {
  const [x, y, z] = values.map(Number);
  const cx = Math.cos(x), sx = Math.sin(x), cy = Math.cos(y), sy = Math.sin(y), cz = Math.cos(z), sz = Math.sin(z);
  return [
    [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
    [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
    [-sy, cy * sx, cy * cx],
  ];
}
function transform(fixture, kind, frame) {
  const row = fixture[`${kind}ByFrame`][String(frame)];
  return [row.location.map(Number), rotationXyz(row.rotationEuler)];
}
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const subtract = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a, v) => [a[0] * v, a[1] * v, a[2] * v];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const matVec = (m, v) => [
  m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
  m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
  m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
];
const matTVec = (m, v) => [
  m[0][0] * v[0] + m[1][0] * v[1] + m[2][0] * v[2],
  m[0][1] * v[0] + m[1][1] * v[1] + m[2][1] * v[2],
  m[0][2] * v[0] + m[1][2] * v[1] + m[2][2] * v[2],
];

function project(point, cameraLocation, cameraRotation, width, height, lens, sensorWidth) {
  const cameraPoint = matTVec(cameraRotation, subtract(point, cameraLocation));
  const depth = -cameraPoint[2];
  if (depth <= 0) throw new Error('surface point behind D12 camera');
  const sensorHeight = sensorWidth * height / width;
  const u = 0.5 + lens * cameraPoint[0] / (depth * sensorWidth);
  const vBottom = 0.5 + lens * cameraPoint[1] / (depth * sensorHeight);
  return [u * width - 0.5, (1 - vBottom) * height - 0.5, depth];
}

function oraclePixel(fixture, scene, x, y) {
  const [width, height] = scene.resolution;
  const lens = Number(scene.camera.lensMm), sensorWidth = Number(scene.camera.sensorWidthMm), sensorHeight = sensorWidth * height / width;
  const [cameraCurrentLocation, cameraCurrentRotation] = transform(fixture, 'camera', 1);
  const [surfaceCurrentLocation, surfaceCurrentRotation] = transform(fixture, 'surface', 1);
  const u = (x + 0.5) / width, vBottom = 1 - (y + 0.5) / height;
  const cameraDirection = [(u - 0.5) * sensorWidth / lens, (vBottom - 0.5) * sensorHeight / lens, -1];
  const worldDirection = matVec(cameraCurrentRotation, cameraDirection);
  const planeNormal = matVec(surfaceCurrentRotation, [0, 0, 1]);
  const denominator = dot(worldDirection, planeNormal);
  if (Math.abs(denominator) < 1e-12) throw new Error('D12 ray parallel to plane');
  const distance = dot(subtract(surfaceCurrentLocation, cameraCurrentLocation), planeNormal) / denominator;
  const currentWorld = add(cameraCurrentLocation, scale(worldDirection, distance));
  const local = matTVec(surfaceCurrentRotation, subtract(currentWorld, surfaceCurrentLocation));
  const [surfacePreviousLocation, surfacePreviousRotation] = transform(fixture, 'surface', 0);
  const previousWorld = add(surfacePreviousLocation, matVec(surfacePreviousRotation, local));
  const [cameraPreviousLocation, cameraPreviousRotation] = transform(fixture, 'camera', 0);
  const [previousX, previousY, previousDepth] = project(previousWorld, cameraPreviousLocation, cameraPreviousRotation, width, height, lens, sensorWidth);
  const [, , currentDepth] = project(currentWorld, cameraCurrentLocation, cameraCurrentRotation, width, height, lens, sensorWidth);
  return [previousX - x, y - previousY, currentDepth, previousDepth];
}

function pixelBase(width, x, y, channels) { return (y * width + x) * channels; }
function bilinear(image, channels, width, height, qx, qy) {
  const x0 = Math.floor(qx), y0 = Math.floor(qy);
  if (x0 < 0 || y0 < 0 || x0 + 1 >= width || y0 + 1 >= height) return { value: new Float32Array(channels), taps: [x0, y0, x0 + 1, y0 + 1], valid: false };
  const fx = qx - x0, fy = qy - y0;
  const weights = [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy];
  const coordinates = [[x0, y0], [x0 + 1, y0], [x0, y0 + 1], [x0 + 1, y0 + 1]];
  const value = new Float32Array(channels);
  for (let channel = 0; channel < channels; channel++) {
    const values = coordinates.map(([tx, ty]) => image[pixelBase(width, tx, ty, channels) + channel]);
    value[channel] = values[0] * weights[0] + values[1] * weights[1] + values[2] * weights[2] + values[3] * weights[3];
  }
  return { value, taps: [x0, y0, x0 + 1, y0 + 1], valid: true };
}
function roundEven(value) {
  const lower = Math.floor(value), fraction = value - lower;
  if (fraction < 0.5) return lower;
  if (fraction > 0.5) return lower + 1;
  return lower % 2 === 0 ? lower : lower + 1;
}
function quantile(values, q) {
  const sorted = [...values].sort((a, b) => a - b);
  const index = (sorted.length - 1) * q, lower = Math.floor(index), upper = Math.ceil(index), fraction = index - lower;
  return sorted[lower] * (1 - fraction) + sorted[upper] * fraction;
}
function metric(reconstructed, current, mask, width, height) {
  const signed = [[], [], []], absolute = [], squared = [];
  for (let i = 0; i < width * height; i++) if (mask[i]) for (let c = 0; c < 3; c++) {
    const error = reconstructed[i * 4 + c] - current[i * 4 + c];
    signed[c].push(error); absolute.push(Math.abs(error)); squared.push(error * error);
  }
  const mse = squared.reduce((a, b) => a + b, 0) / squared.length;
  return {
    maximum: Math.max(...absolute), p99: quantile(absolute, 0.99), rmse: Math.sqrt(mse),
    absoluteSignedMeanPerChannel: signed.map(values => Math.abs(values.reduce((a, b) => a + b, 0) / values.length)),
    psnrUnitRangeDb: mse === 0 ? 999 : -10 * Math.log10(mse),
  };
}

function main() {
  const args = parseArgs();
  const specBuffer = fs.readFileSync(args.spec);
  if (shaBytes(specBuffer) !== SPEC_SHA256) throw new Error('B52-D12 spec identity mismatch');
  const spec = JSON.parse(specBuffer);
  if (process.version !== spec.runtime.node.version || shaFile(process.execPath) !== spec.runtime.node.sha256) throw new Error('Node runtime identity mismatch');
  const fixture = spec.fixtures.find(item => item.id === args.fixture);
  if (!fixture) throw new Error('fixture outside frozen D12 roster');
  if (fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) throw new Error('refusing to overwrite D12 reconstruction');
  const adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8'));
  const adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) throw new Error('D12 adapter report mismatch');
  const [width, height] = spec.scene.resolution;
  const arrays = {};
  for (const [name, [filename]] of Object.entries(INPUTS)) {
    const path = `${args['input-dir']}/${filename}`, loaded = readF32(path);
    if (shaBytes(loaded.buffer) !== adapter.arrays[name].sha256) throw new Error(`D12 adapter array hash mismatch: ${name}`);
    arrays[name] = loaded.values;
  }
  const pixels = width * height, current = arrays.currentRgba, previous = arrays.previousRgba;
  const outputs = {
    reconstructed: new Float32Array(current), valid: new Uint8Array(pixels), expectedVector: new Float32Array(pixels * 2),
    predictedCurrentDepth: new Float32Array(pixels), predictedPreviousDepth: new Float32Array(pixels),
    nearest: new Float32Array(current), wrongSign: new Float32Array(current), directDepthValid: new Uint8Array(pixels),
  };
  const ownerId = Math.fround(fixture.passIndex), margin = 4;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const pixel = y * width + x, [expectedX, expectedY, predictedCurrentDepth, predictedPreviousDepth] = oraclePixel(fixture, spec.scene, x, y);
    outputs.expectedVector[pixel * 2] = expectedX; outputs.expectedVector[pixel * 2 + 1] = expectedY;
    outputs.predictedCurrentDepth[pixel] = predictedCurrentDepth; outputs.predictedPreviousDepth[pixel] = predictedPreviousDepth;
    const vectorX = arrays.vector[pixel * 2], vectorY = arrays.vector[pixel * 2 + 1], qx = x + vectorX, qy = y - vectorY;
    const sampled = bilinear(previous, 4, width, height, qx, qy);
    const sampledDepth = bilinear(arrays.previousDepth, 1, width, height, qx, qy);
    const wrong = bilinear(previous, 4, width, height, x - vectorX, y + vectorY);
    if (wrong.valid) for (let c = 0; c < 4; c++) outputs.wrongSign[pixel * 4 + c] = wrong.value[c];
    const nearestX = roundEven(qx), nearestY = roundEven(qy), nearestBounds = nearestX >= 0 && nearestY >= 0 && nearestX < width && nearestY < height;
    if (nearestBounds) for (let c = 0; c < 4; c++) outputs.nearest[pixel * 4 + c] = previous[pixelBase(width, nearestX, nearestY, 4) + c];
    const [x0, y0, x1, y1] = sampled.taps;
    const interior = x >= margin && x < width - margin && y >= margin && y < height - margin;
    const currentMeta = arrays.currentOwner[pixel] === ownerId && current[pixel * 4 + 3] > Math.fround(0.999);
    let previousMeta = false;
    if (sampled.valid) previousMeta = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].every(([tx, ty]) => {
      const tapPixel = ty * width + tx;
      return arrays.previousOwner[tapPixel] === ownerId && previous[tapPixel * 4 + 3] > Math.fround(0.999);
    });
    const currentTolerance = Math.max(1, predictedCurrentDepth) / 1024, previousTolerance = Math.max(1, predictedPreviousDepth) / 1024;
    const currentDepthOk = Math.abs(arrays.currentDepth[pixel] - predictedCurrentDepth) <= currentTolerance;
    const previousDepthOk = sampledDepth.valid && Math.abs(sampledDepth.value[0] - predictedPreviousDepth) <= previousTolerance;
    const valid = interior && sampled.valid && nearestBounds && currentMeta && previousMeta && currentDepthOk && previousDepthOk;
    if (valid) {
      outputs.valid[pixel] = 1;
      for (let c = 0; c < 4; c++) outputs.reconstructed[pixel * 4 + c] = sampled.value[c];
      const directTolerance = Math.max(1, arrays.currentDepth[pixel]) / 1024;
      outputs.directDepthValid[pixel] = Math.abs(sampledDepth.value[0] - arrays.currentDepth[pixel]) <= directTolerance ? 1 : 0;
    }
  }
  const mask = outputs.valid, validPixels = mask.reduce((a, b) => a + b, 0);
  if (validPixels === 0) throw new Error('D12 reconstruction produced no valid pixels');
  const endpointAbsolute = [], fractional = []; let movingPixels = 0, directRejected = 0;
  for (let i = 0; i < pixels; i++) if (mask[i]) {
    const ex = outputs.expectedVector[i * 2], ey = outputs.expectedVector[i * 2 + 1], moving = Math.hypot(ex, ey) > 1e-8;
    if (moving) {
      movingPixels++;
      for (let c = 0; c < 2; c++) {
        const value = arrays.vector[i * 2 + c]; endpointAbsolute.push(Math.abs(value - outputs.expectedVector[i * 2 + c])); fractional.push(Math.abs(value - Math.round(value)));
      }
    }
    if (!outputs.directDepthValid[i]) directRejected++;
  }
  if (movingPixels === 0) for (let i = 0; i < pixels; i++) if (mask[i]) for (let c = 0; c < 2; c++) {
    const value = arrays.vector[i * 2 + c]; endpointAbsolute.push(Math.abs(value - outputs.expectedVector[i * 2 + c])); fractional.push(Math.abs(value - Math.round(value)));
  }
  fs.mkdirSync(args['output-dir'], { recursive: false });
  const records = {};
  for (const [name, [filename, dtype]] of Object.entries(OUTPUTS)) {
    const payload = dtype === 'u8' ? Buffer.from(outputs[name]) : encodeF32(outputs[name]);
    const target = `${args['output-dir']}/${filename}`; fs.writeFileSync(target, payload);
    records[name] = { uri: target, sha256: shaBytes(payload), bytes: payload.length, shape: name === 'reconstructed' || name === 'nearest' || name === 'wrongSign' ? [height, width, 4] : name === 'expectedVector' ? [height, width, 2] : [height, width], dtype: dtype === 'u8' ? 'uint8' : 'little-endian-float32' };
  }
  const body = {
    schemaVersion: 'bfs.blenderProjectiveSubpixelReconstructorReport.v0.1', experimentId: spec.experimentId, producer: 'node', fixtureId: args.fixture, repeat: args.repeat, pid: process.pid,
    runtime: { node: process.version, nodeExecutableSha256: shaFile(process.execPath) },
    adapter: { uri: args['adapter-report'], sha256: shaFile(args['adapter-report']), reportHash: adapter.reportHash }, formula: spec.projectionOracle, kernel: spec.reconstruction.kernel,
    measurements: {
      validPixels, movingPixels, fractionalComponentFractionBeyond1Over1024: fractional.filter(v => v > 1 / 1024).length / fractional.length,
      fractionalDistanceP50: quantile(fractional, 0.5), vectorEndpointMaximum: Math.max(...endpointAbsolute), vectorEndpointP99: quantile(endpointAbsolute, 0.99),
      directDepthIdentityRejectedPixels: directRejected, directDepthIdentityRejectedFraction: directRejected / validPixels,
      correct: metric(outputs.reconstructed, current, mask, width, height), nearest: metric(outputs.nearest, current, mask, width, height), wrongSign: metric(outputs.wrongSign, current, mask, width, height),
    },
    arrays: records, operationCounts: { reconstructorProcesses: 1, pixelsVisited: pixels, modelCalls: 0, networkCalls: 0 },
  };
  const report = { ...body, reportHash: canonicalHash(body) };
  fs.mkdirSync(args.report.slice(0, args.report.lastIndexOf('/')), { recursive: true });
  fs.writeFileSync(args.report, `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`BFS_B52_D12_RECONSTRUCT_NODE_OK fixture=${args.fixture} repeat=${args.repeat} valid=${validPixels}\n`);
}

main();
