#!/usr/bin/env node
/** Scalar Node structural-validity and adaptive-risk consumer for B52-D12.8. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const SPEC_SHA256 = 'd7e7c0ee0bd7f512766188eabda9fa0dccb098a0729b26487aa38bee97d6aea6';
const INPUTS = {
  previousRgba: ['previous.rgba32', 4], currentRgba: ['current.rgba32', 4],
  previousDepth: ['previous-depth.f32', 1], currentDepth: ['current-depth.f32', 1],
  previousOwner: ['previous-owner.f32', 1], currentOwner: ['current-owner.f32', 1],
  vector: ['vector.xy32', 2], vectorNext: ['vector-next.xy32', 2],
};
const OUTPUTS = {
  adaptiveReconstructed: ['adaptive-reconstructed.rgba32', 'f32'], reason: ['reason.u8', 'u8'],
  analyticOwner: ['analytic-owner.u8', 'u8'], structuralValid: ['structural-valid.u8', 'u8'],
  radius2Interior: ['radius2-interior.u8', 'u8'], radius3Interior: ['radius3-interior.u8', 'u8'],
  adaptiveInterior: ['adaptive-interior.u8', 'u8'], adaptiveRejected: ['adaptive-rejected.u8', 'u8'],
  riskRgb: ['risk.rgb64', 'f64'],
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
    if (!key.startsWith('--') || index + 1 >= process.argv.length) throw new Error('invalid D12.8 arguments');
    result[key.slice(2)] = process.argv[index + 1];
  }
  for (const key of ['spec', 'fixture', 'repeat', 'input-dir', 'adapter-report', 'output-dir', 'report']) if (!(key in result)) throw new Error(`missing --${key}`);
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) throw new Error('invalid D12.8 repeat');
  return result;
}
function readF32(filePath, expectedCount) {
  const payload = fs.readFileSync(filePath);
  if (payload.length !== expectedCount * 4) throw new Error(`D12.8 float32 length mismatch: ${filePath}`);
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
function f32Ulp(value) {
  const buffer = Buffer.alloc(4); buffer.writeFloatLE(Math.fround(value), 0); let bits = buffer.readUInt32LE(0); if ((bits & 0x7fffffff) === 0) return 2 ** -149;
  bits += (bits & 0x80000000) ? -1 : 1; const next = Buffer.alloc(4); next.writeUInt32LE(bits >>> 0, 0); return Math.abs(next.readFloatLE(0) - Math.fround(value));
}
function encode(array, type) {
  if (type === 'u8') return Buffer.from(array);
  const bytes = type === 'f64' ? 8 : 4, payload = Buffer.alloc(array.length * bytes);
  for (let index = 0; index < array.length; index++) type === 'f64' ? payload.writeDoubleLE(array[index], index * 8) : payload.writeFloatLE(array[index], index * 4);
  return payload;
}
function main() {
  const args = parseArgs(), spec = JSON.parse(fs.readFileSync(args.spec, 'utf8'));
  if (shaFile(args.spec) !== SPEC_SHA256 || shaFile(process.execPath) !== spec.runtime.node.sha256 || process.version !== spec.runtime.node.version) throw new Error('D12.8 Node/spec identity mismatch');
  const fixture = spec.fixtures.find(row => row.id === args.fixture); if (!fixture || fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) throw new Error('D12.8 consumer fixture or output invalid');
  const adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8')), adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) throw new Error('D12.8 adapter identity mismatch');
  const [width, height] = fixture.resolution, pixels = width * height, arrays = {};
  for (const [name, [filename, channels]] of Object.entries(INPUTS)) { const [value, payload] = readF32(path.join(args['input-dir'], filename), pixels * channels); if (shaBytes(payload) !== adapter.arrays[name].sha256) throw new Error(`D12.8 input hash mismatch: ${name}`); arrays[name] = value; }
  const outputs = {adaptiveReconstructed: new Float32Array(arrays.currentRgba), reason: new Uint8Array(pixels), analyticOwner: new Uint8Array(pixels), structuralValid: new Uint8Array(pixels), radius2Interior: new Uint8Array(pixels), radius3Interior: new Uint8Array(pixels), adaptiveInterior: new Uint8Array(pixels), adaptiveRejected: new Uint8Array(pixels), riskRgb: new Float64Array(pixels * 3)};
  const threshold = Number(spec.frozenGates.adaptiveQuality.rgbMaximum), rgba = (pixel, channel) => pixel * 4 + channel, xy = (pixel, channel) => pixel * 2 + channel;
  function neighborhood(x, y, radius, owner) { if (x < radius || y < radius || x >= width - radius || y >= height - radius) return false; for (let ty = y - radius; ty <= y + radius; ty++) for (let tx = x - radius; tx <= x + radius; tx++) { const pixel = ty * width + tx; if (arrays.currentOwner[pixel] !== owner || arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999)) return false; } return true; }
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const pixel = y * width + x, oracle = oraclePixel(spec, fixture, x, y); if (!oracle) { outputs.reason[pixel] = REASONS.INVALID_CURRENT_ORACLE; continue; }
    outputs.analyticOwner[pixel] = oracle.ownerIndex;
    const currentOk = arrays.currentOwner[pixel] === oracle.passIndex && Math.abs(arrays.currentDepth[pixel] - oracle.currentDepth) <= Math.max(1, oracle.currentDepth) / 1024; if (!currentOk) { outputs.reason[pixel] = REASONS.INVALID_CURRENT_ORACLE; continue; }
    const vectorX = arrays.vector[xy(pixel, 0)], vectorY = arrays.vector[xy(pixel, 1)], sample = tapsAndWeights(x + vectorX, y - vectorY, width, height); if (!sample) { outputs.reason[pixel] = REASONS.INVALID_BOUNDS; continue; }
    const tapPixels = sample.taps.map(([ty, tx]) => ty * width + tx); if (!tapPixels.every(tap => arrays.previousOwner[tap] === oracle.passIndex)) { outputs.reason[pixel] = REASONS.INVALID_OWNER; continue; }
    if (arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999) || !tapPixels.every(tap => arrays.previousRgba[rgba(tap, 3)] > Math.fround(0.999))) { outputs.reason[pixel] = REASONS.INVALID_ALPHA; continue; }
    const sampledDepth = weighted(tapPixels.map(tap => arrays.previousDepth[tap]), sample.weights); if (Math.abs(sampledDepth - oracle.previousDepth) > Math.max(1, oracle.previousDepth) / 1024) { outputs.reason[pixel] = REASONS.INVALID_DEPTH; continue; }
    outputs.reason[pixel] = REASONS.VALID; outputs.structuralValid[pixel] = 1; const r2 = neighborhood(x, y, 2, oracle.passIndex), r3 = neighborhood(x, y, 3, oracle.passIndex); outputs.radius2Interior[pixel] = Number(r2); outputs.radius3Interior[pixel] = Number(r3); if (!r2) continue;
    const reconstructed = new Float32Array(4); for (let channel = 0; channel < 4; channel++) { const values = tapPixels.map(tap => arrays.previousRgba[rgba(tap, channel)]); reconstructed[channel] = Math.fround(weighted(values, sample.weights)); if (channel < 3) { const center = arrays.currentRgba[rgba(pixel, channel)]; outputs.riskRgb[pixel * 3 + channel] = sample.weights.reduce((sum, weight, index) => sum + Math.abs(weight) * Math.abs(values[index] - center), 0) + f32Ulp(reconstructed[channel]); } }
    const riskMax = Math.max(outputs.riskRgb[pixel * 3], outputs.riskRgb[pixel * 3 + 1], outputs.riskRgb[pixel * 3 + 2]); if (riskMax <= threshold) { outputs.adaptiveInterior[pixel] = 1; for (let channel = 0; channel < 4; channel++) outputs.adaptiveReconstructed[rgba(pixel, channel)] = reconstructed[channel]; } else outputs.adaptiveRejected[pixel] = 1;
  }
  fs.mkdirSync(args['output-dir'], {recursive: true}); const records = {};
  for (const [name, [filename, type]] of Object.entries(OUTPUTS)) { const payload = encode(outputs[name], type), target = path.join(args['output-dir'], filename); fs.writeFileSync(target, payload); records[name] = {uri: target, sha256: shaBytes(payload), bytes: payload.length, shape: name === 'adaptiveReconstructed' ? [height, width, 4] : name === 'riskRgb' ? [height, width, 3] : [height, width], dtype: type === 'u8' ? 'uint8' : type === 'f64' ? 'little-endian-float64' : 'little-endian-float32'}; }
  const body = {schemaVersion: 'bfs.blenderProjectiveMotionDisocclusionConsumerReport.v0.1', experimentId: spec.experimentId, producer: 'node', fixtureId: args.fixture, repeat: args.repeat, pid: process.pid, runtime: {node: process.version, nodeExecutableSha256: shaFile(process.execPath)}, adapter: {uri: args['adapter-report'], sha256: shaFile(args['adapter-report']), reportHash: adapter.reportHash}, reasonCodes: REASONS, projectionContract: spec.projectionOracle, structuralContract: spec.structuralValidity, candidateContract: spec.candidateContract, arrays: records, operationCounts: {consumerProcesses: 1, pixelsVisited: pixels, modelCalls: 0, networkCalls: 0}};
  const report = {...body, reportHash: canonicalHash(body)}; fs.mkdirSync(path.dirname(args.report), {recursive: true}); fs.writeFileSync(args.report, `${JSON.stringify(report, null, 2)}\n`); console.log(`BFS_B52_D128_CONSUMER_NODE_OK fixture=${args.fixture} repeat=${args.repeat}`);
}
main();
