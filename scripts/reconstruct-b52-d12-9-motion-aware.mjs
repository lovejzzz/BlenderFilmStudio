#!/usr/bin/env node
/** Scalar Node structural-validity and adaptive-risk consumer for B52-D12.9-H1. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SPEC_SHA256 = 'c2756a20e314cf470698ef7af6160154b8d7e2d5e8531ce6591b2509a8730dbc';
const Q24 = 1n << 24n, Q30 = 1n << 30n, UINT32_MAX = (1n << 32n) - 1n;
const INPUTS = {
  previousRgba: ['previous.rgba32', 4], currentRgba: ['current.rgba32', 4],
  previousDepth: ['previous-depth.f32', 1], currentDepth: ['current-depth.f32', 1],
  previousOwner: ['previous-owner.f32', 1], currentOwner: ['current-owner.f32', 1],
  vector: ['vector.xy32', 2], vectorNext: ['vector-next.xy32', 2],
};
const OUTPUTS = {
  acceptedReconstructed: ['accepted-reconstructed.rgba32', 'f32'], reason: ['reason.u8', 'u8'],
  analyticOwner: ['analytic-owner.u8', 'u8'], structuralValid: ['structural-valid.u8', 'u8'],
  radius2Interior: ['radius2-interior.u8', 'u8'], supportEligible: ['support-eligible.u8', 'u8'],
  supportRejected: ['support-rejected.u8', 'u8'], accepted: ['accepted.u8', 'u8'],
  riskRejected: ['risk-rejected.u8', 'u8'], riskQ30: ['risk.q30.u32', 'u32'],
};
const REASONS = {UNREGISTERED: 0, INVALID_CURRENT_ORACLE: 1, INVALID_BOUNDS: 2, INVALID_OWNER: 3, INVALID_ALPHA: 4, INVALID_DEPTH: 5, VALID: 6};

function shaBytes(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function shaFile(filePath) { return shaBytes(fs.readFileSync(filePath)); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function canonicalHash(value) { return shaBytes(Buffer.from(stable(value))); }
function parseArgs() {
  const result = {};
  for (let index = 2; index < process.argv.length; index += 2) {
    const key = process.argv[index];
    if (!key.startsWith('--') || index + 1 >= process.argv.length) throw new Error('invalid D12.9-H1 arguments');
    result[key.slice(2)] = process.argv[index + 1];
  }
  for (const key of ['spec', 'fixture', 'repeat', 'input-dir', 'adapter-report', 'output-dir', 'report']) if (!(key in result)) throw new Error(`missing --${key}`);
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) throw new Error('invalid D12.9-H1 repeat');
  return result;
}
function readF32(filePath, expectedCount) {
  const payload = fs.readFileSync(filePath);
  if (payload.length !== expectedCount * 4) throw new Error(`D12.9-H1 float32 length mismatch: ${filePath}`);
  const result = new Float32Array(expectedCount);
  for (let index = 0; index < expectedCount; index++) result[index] = payload.readFloatLE(index * 4);
  return [result, payload];
}
function rotationXyz(values) {
  const [x, y, z] = values.map(Number); const cx = Math.cos(x), sx = Math.sin(x), cy = Math.cos(y), sy = Math.sin(y), cz = Math.cos(z), sz = Math.sin(z);
  return [[cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx], [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx], [-sy, cy * sx, cy * cx]];
}
function transform(row) { return [row.location.map(Number), rotationXyz(row.rotationEuler)]; }
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const subtract = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a, value) => [a[0] * value, a[1] * value, a[2] * value];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
function matVec(matrix, vector) { return [0, 1, 2].map(row => matrix[row][0] * vector[0] + matrix[row][1] * vector[1] + matrix[row][2] * vector[2]); }
function matTVec(matrix, vector) { return [0, 1, 2].map(column => matrix[0][column] * vector[0] + matrix[1][column] * vector[1] + matrix[2][column] * vector[2]); }
function project(point, cameraTransform, width, height, lens, sensorWidth) {
  const cameraPoint = matTVec(cameraTransform[1], subtract(point, cameraTransform[0])); const depth = -cameraPoint[2];
  if (depth <= 0) return null;
  const sensorHeight = sensorWidth * height / width; const u = 0.5 + lens * cameraPoint[0] / (depth * sensorWidth); const vBottom = 0.5 + lens * cameraPoint[1] / (depth * sensorHeight);
  return [u * width - 0.5, (1 - vBottom) * height - 0.5, depth];
}
function dimensions(spec, owner) { return spec.sceneContract.surfaces[owner.role === 'background' ? 'backgroundSizeWorld' : 'occluderSizeWorld'].map(Number); }
function oraclePixel(spec, fixture, x, y) {
  const [width, height] = fixture.resolution; const cameraSpec = spec.sceneContract.camera; const lens = Number(cameraSpec.lensMm), sensorWidth = Number(cameraSpec.sensorWidthMm), sensorHeight = sensorWidth * height / width;
  const currentCamera = transform(fixture.cameraByFrame['1']), previousCamera = transform(fixture.cameraByFrame['0']);
  const u = (x + 0.5) / width, vBottom = 1 - (y + 0.5) / height;
  const cameraDirection = [(u - 0.5) * sensorWidth / lens, (vBottom - 0.5) * sensorHeight / lens, -1]; const worldDirection = matVec(currentCamera[1], cameraDirection); const candidates = [];
  fixture.owners.forEach((owner, zeroIndex) => {
    const currentOwner = transform(owner.transformByFrame['1']), normal = matVec(currentOwner[1], [0, 0, 1]), denominator = dot(worldDirection, normal);
    if (Math.abs(denominator) < 1e-12) return;
    const distance = dot(subtract(currentOwner[0], currentCamera[0]), normal) / denominator; if (distance <= 0) return;
    const worldPoint = add(currentCamera[0], scale(worldDirection, distance)); const localPoint = matTVec(currentOwner[1], subtract(worldPoint, currentOwner[0])); const [sizeX, sizeY] = dimensions(spec, owner);
    if (Math.abs(localPoint[0]) <= sizeX / 2 && Math.abs(localPoint[1]) <= sizeY / 2) {
      const projected = project(worldPoint, currentCamera, width, height, lens, sensorWidth); if (projected) candidates.push([projected[2], zeroIndex + 1, owner, localPoint]);
    }
  });
  if (!candidates.length) return null; candidates.sort((left, right) => left[0] - right[0]); const [currentDepth, ownerIndex, owner, localPoint] = candidates[0];
  const previousOwner = transform(owner.transformByFrame['0']); const previousWorld = add(previousOwner[0], matVec(previousOwner[1], localPoint)); const previous = project(previousWorld, previousCamera, width, height, lens, sensorWidth); if (!previous) return null;
  return {ownerIndex, passIndex: Math.fround(owner.passIndex), expectedVector: [previous[0] - x, y - previous[1]], currentDepth, previousDepth: previous[2]};
}
function tapsAndWeights(qx, qy, width, height) {
  const x0 = Math.floor(qx), y0 = Math.floor(qy); if (x0 < 0 || y0 < 0 || x0 + 1 >= width || y0 + 1 >= height) return null;
  const fx = qx - x0, fy = qy - y0; return {taps: [[y0, x0], [y0, x0 + 1], [y0 + 1, x0], [y0 + 1, x0 + 1]], weights: [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy]};
}
function weighted(values, weights) { return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]; }
function encode(array, type) {
  if (type === 'u8') return Buffer.from(array);
  const payload = Buffer.alloc(array.length * 4);
  for (let index = 0; index < array.length; index++) type === 'u32' ? payload.writeUInt32LE(array[index], index * 4) : payload.writeFloatLE(array[index], index * 4);
  return payload;
}
function exactScaled(value, scale, label) { const scaled = value * Number(scale); if (!Number.isInteger(scaled)) throw new Error(`D12.9-H1 non-canonical ${label}: ${value}`); return BigInt(scaled); }
function ceilDiv(numerator, denominator) { return (numerator + denominator - 1n) / denominator; }
function main() {
  const args = parseArgs(), spec = JSON.parse(fs.readFileSync(args.spec, 'utf8'));
  if (shaFile(args.spec) !== SPEC_SHA256 || shaFile(process.execPath) !== spec.runtime.node.sha256 || process.version !== spec.runtime.node.version) throw new Error('D12.9-H1 Node/spec identity mismatch');
  const fixture = spec.fixtures.find(row => row.id === args.fixture); if (!fixture || fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) throw new Error('D12.9-H1 consumer fixture or output invalid');
  const adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8')), adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) throw new Error('D12.9-H1 adapter identity mismatch');
  const [width, height] = fixture.resolution, pixels = width * height, arrays = {};
  for (const [name, [filename, channels]] of Object.entries(INPUTS)) { const [value, payload] = readF32(path.join(args['input-dir'], filename), pixels * channels); if (shaBytes(payload) !== adapter.arrays[name].sha256) throw new Error(`D12.9-H1 input hash mismatch: ${name}`); arrays[name] = value; }
  const outputs = {acceptedReconstructed: new Float32Array(arrays.currentRgba), reason: new Uint8Array(pixels), analyticOwner: new Uint8Array(pixels), structuralValid: new Uint8Array(pixels), radius2Interior: new Uint8Array(pixels), supportEligible: new Uint8Array(pixels), supportRejected: new Uint8Array(pixels), accepted: new Uint8Array(pixels), riskRejected: new Uint8Array(pixels), riskQ30: new Uint32Array(pixels * 3)};
  const threshold = Number(spec.frozenGates.risk.riskThresholdQ30Inclusive), rgba = (pixel, channel) => pixel * 4 + channel, xy = (pixel, channel) => pixel * 2 + channel;
  function neighborhood(x, y, radius, owner) { if (x < radius || y < radius || x >= width - radius || y >= height - radius) return false; for (let ty = y - radius; ty <= y + radius; ty++) for (let tx = x - radius; tx <= x + radius; tx++) { const pixel = ty * width + tx; if (arrays.currentOwner[pixel] !== owner || arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999)) return false; } return true; }
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const pixel = y * width + x, oracle = oraclePixel(spec, fixture, x, y); if (!oracle) { outputs.reason[pixel] = REASONS.INVALID_CURRENT_ORACLE; continue; }
    outputs.analyticOwner[pixel] = oracle.ownerIndex;
    const currentOk = arrays.currentOwner[pixel] === oracle.passIndex && Math.abs(arrays.currentDepth[pixel] - oracle.currentDepth) <= Math.max(1, oracle.currentDepth) / 1024; if (!currentOk) { outputs.reason[pixel] = REASONS.INVALID_CURRENT_ORACLE; continue; }
    const vectorX = arrays.vector[xy(pixel, 0)], vectorY = arrays.vector[xy(pixel, 1)], qx = x + vectorX, qy = y - vectorY, sample = tapsAndWeights(qx, qy, width, height); if (!sample) { outputs.reason[pixel] = REASONS.INVALID_BOUNDS; continue; }
    const tapPixels = sample.taps.map(([ty, tx]) => ty * width + tx); if (!tapPixels.every(tap => arrays.previousOwner[tap] === oracle.passIndex)) { outputs.reason[pixel] = REASONS.INVALID_OWNER; continue; }
    if (arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999) || !tapPixels.every(tap => arrays.previousRgba[rgba(tap, 3)] > Math.fround(0.999))) { outputs.reason[pixel] = REASONS.INVALID_ALPHA; continue; }
    const sampledDepth = weighted(tapPixels.map(tap => arrays.previousDepth[tap]), sample.weights); if (Math.abs(sampledDepth - oracle.previousDepth) > Math.max(1, oracle.previousDepth) / 1024) { outputs.reason[pixel] = REASONS.INVALID_DEPTH; continue; }
    outputs.reason[pixel] = REASONS.VALID; outputs.structuralValid[pixel] = 1; const r2 = neighborhood(x, y, 2, oracle.passIndex); outputs.radius2Interior[pixel] = Number(r2); if (!r2) continue;
    const [y0, x0] = sample.taps[0]; if (x0 - 1 < 0 || x0 + 2 >= width || y0 - 1 < 0 || y0 + 2 >= height) { outputs.supportRejected[pixel] = 1; continue; }
    const supportOwner = arrays.previousOwner[y0 * width + x0]; let supportOk = true;
    for (let sy = y0 - 1; sy <= y0 + 2; sy++) for (let sx = x0 - 1; sx <= x0 + 2; sx++) { const supportPixel = sy * width + sx; if (arrays.previousOwner[supportPixel] !== supportOwner || !(arrays.previousRgba[rgba(supportPixel, 3)] > Math.fround(0.999))) supportOk = false; }
    if (!supportOk) { outputs.supportRejected[pixel] = 1; continue; } outputs.supportEligible[pixel] = 1;
    const fx = exactScaled(qx - x0, Q24, 'motion fraction x'), fy = exactScaled(qy - y0, Q24, 'motion fraction y');
    const reconstructed = new Float32Array(4); for (let channel = 0; channel < 4; channel++) {
      const values = tapPixels.map(tap => arrays.previousRgba[rgba(tap, channel)]); reconstructed[channel] = Math.fround(weighted(values, sample.weights));
      if (channel < 3) {
        const color = (yy, xx) => exactScaled(arrays.previousRgba[rgba(yy * width + xx, channel)], Q30, 'Q30 RGB'); let mx = 0n, my = 0n;
        for (const yy of [y0, y0 + 1]) for (const xx of [x0, x0 + 1]) { const value = color(yy, xx - 1) - 2n * color(yy, xx) + color(yy, xx + 1), absolute = value < 0n ? -value : value; if (absolute > mx) mx = absolute; }
        for (const xx of [x0, x0 + 1]) for (const yy of [y0, y0 + 1]) { const value = color(yy - 1, xx) - 2n * color(yy, xx) + color(yy + 1, xx), absolute = value < 0n ? -value : value; if (absolute > my) my = absolute; }
        const numerator = 2n * (fx * (Q24 - fx) * mx + fy * (Q24 - fy) * my), units = ceilDiv(numerator, Q24 * Q24) + 512n; outputs.riskQ30[pixel * 3 + channel] = Number(units > UINT32_MAX ? UINT32_MAX : units);
      }
    }
    const riskMax = Math.max(outputs.riskQ30[pixel * 3], outputs.riskQ30[pixel * 3 + 1], outputs.riskQ30[pixel * 3 + 2]); if (riskMax <= threshold) { outputs.accepted[pixel] = 1; for (let channel = 0; channel < 4; channel++) outputs.acceptedReconstructed[rgba(pixel, channel)] = reconstructed[channel]; } else outputs.riskRejected[pixel] = 1;
  }
  fs.mkdirSync(args['output-dir'], {recursive: true}); const records = {};
  for (const [name, [filename, type]] of Object.entries(OUTPUTS)) { const payload = encode(outputs[name], type), target = path.join(args['output-dir'], filename); fs.writeFileSync(target, payload); records[name] = {uri: target, sha256: shaBytes(payload), bytes: payload.length, shape: name === 'acceptedReconstructed' ? [height, width, 4] : name === 'riskQ30' ? [height, width, 3] : [height, width], dtype: type === 'u8' ? 'uint8' : type === 'u32' ? 'little-endian-uint32' : 'little-endian-float32'}; }
  const body = {schemaVersion: 'bfs.blenderMotionAwareCurvatureRiskConsumerReport.v0.1', experimentId: spec.experimentId, producer: 'node', fixtureId: args.fixture, repeat: args.repeat, pid: process.pid, runtime: {node: process.version, nodeExecutableSha256: shaFile(process.execPath)}, adapter: {uri: args['adapter-report'], sha256: shaFile(args['adapter-report']), reportHash: adapter.reportHash}, reasonCodes: REASONS, projectionContract: spec.projectionOracle, structuralContract: spec.structuralValidity, candidateContract: spec.candidateContract, arrays: records, operationCounts: {consumerProcesses: 1, pixelsVisited: pixels, modelCalls: 0, networkCalls: 0}};
  const report = {...body, reportHash: canonicalHash(body)}; fs.mkdirSync(path.dirname(args.report), {recursive: true}); fs.writeFileSync(args.report, `${JSON.stringify(report, null, 2)}\n`); console.log(`BFS_B52_D129_CONSUMER_NODE_OK fixture=${args.fixture} repeat=${args.repeat}`);
}
main();
