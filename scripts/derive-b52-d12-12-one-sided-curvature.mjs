#!/usr/bin/env node
/** Independent scalar Node implementation of B52-D12.12-D1. */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const SPEC_SHA256 = 'f179b4cea6c8d3bc19b4cf2534055ef98b3fa8dac9954bfeae28bc2a237dd640';
const Q24 = 1n << 24n;
const Q30 = 1n << 30n;
const UINT32_MAX = (1n << 32n) - 1n;
const INPUTS = {
  previousRgba: ['previous.rgba32', 4], currentRgba: ['current.rgba32', 4],
  previousDepth: ['previous-depth.f32', 1], currentDepth: ['current-depth.f32', 1],
  previousOwner: ['previous-owner.f32', 1], currentOwner: ['current-owner.f32', 1], vector: ['vector.xy32', 2],
};
const CONTROL_OUTPUTS = {
  structuralValid: 'structural-valid.u8', radius2Interior: 'radius2-interior.u8',
  bilinearSupport: 'bilinear-support.u8', fullStencil: 'full-stencil.u8', localizedOpportunity: 'localized-opportunity.u8',
};
const FACTOR_OUTPUTS = {
  oneSidedEligible: ['one-sided-eligible.u8', 'u8'], oneSidedUnavailable: ['one-sided-unavailable.u8', 'u8'],
  accepted: ['accepted.u8', 'u8'], riskQ30: ['risk.q30.u32', 'u32'], acceptedReconstructed: ['accepted-reconstructed.rgba32', 'f32'],
};

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
    if (!key.startsWith('--') || index + 1 >= process.argv.length) throw new Error('invalid D12.12-D1 arguments');
    result[key.slice(2)] = process.argv[index + 1];
  }
  for (const key of ['spec', 'fixture', 'repeat', 'input-dir', 'adapter-report', 'localization-classification', 'output-dir', 'report']) if (!(key in result)) throw new Error(`missing --${key}`);
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) throw new Error('invalid D12.12-D1 repeat');
  return result;
}
function readF32(filePath, expectedCount) {
  const payload = fs.readFileSync(filePath);
  if (payload.length !== expectedCount * 4) throw new Error(`D12.12-D1 float32 length mismatch: ${filePath}`);
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
  const cameraDirection = [(u - 0.5) * sensorWidth / lens, (vBottom - 0.5) * sensorHeight / lens, -1], worldDirection = matVec(currentCamera[1], cameraDirection), candidates = [];
  fixture.owners.forEach((owner, zeroIndex) => {
    const currentOwner = transform(owner.transformByFrame['1']), normal = matVec(currentOwner[1], [0, 0, 1]), denominator = dot(worldDirection, normal);
    if (Math.abs(denominator) < 1e-12) return;
    const distance = dot(subtract(currentOwner[0], currentCamera[0]), normal) / denominator; if (distance <= 0) return;
    const worldPoint = add(currentCamera[0], scale(worldDirection, distance)), localPoint = matTVec(currentOwner[1], subtract(worldPoint, currentOwner[0])), [sizeX, sizeY] = dimensions(spec, owner);
    if (Math.abs(localPoint[0]) <= sizeX / 2 && Math.abs(localPoint[1]) <= sizeY / 2) {
      const projected = project(worldPoint, currentCamera, width, height, lens, sensorWidth); if (projected) candidates.push([projected[2], zeroIndex + 1, owner, localPoint]);
    }
  });
  if (!candidates.length) return null;
  candidates.sort((left, right) => left[0] - right[0]); const [currentDepth, ownerIndex, owner, localPoint] = candidates[0];
  const previousOwner = transform(owner.transformByFrame['0']), previousWorld = add(previousOwner[0], matVec(previousOwner[1], localPoint)), previous = project(previousWorld, previousCamera, width, height, lens, sensorWidth);
  if (!previous) return null;
  return {ownerIndex, ownerToken: Math.fround(owner.passIndex), currentDepth, previousDepth: previous[2], expectedVector: [previous[0] - x, y - previous[1]]};
}
function tapsAndWeights(qx, qy, width, height) {
  const x0 = Math.floor(qx), y0 = Math.floor(qy); if (x0 < 0 || y0 < 0 || x0 + 1 >= width || y0 + 1 >= height) return null;
  const fx = qx - x0, fy = qy - y0;
  return {taps: [[y0, x0], [y0, x0 + 1], [y0 + 1, x0], [y0 + 1, x0 + 1]], weights: [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy], x0, y0, fx, fy};
}
function weighted(values, weights) { return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]; }
function exactScaled(value, scaleValue, label) { const scaled = value * Number(scaleValue); if (!Number.isInteger(scaled)) throw new Error(`non-canonical ${label}: ${value}`); return BigInt(scaled); }
function absolute(value) { return value < 0n ? -value : value; }
function ceilDiv(numerator, denominator) { return (numerator + denominator - 1n) / denominator; }
function encode(array, type) {
  if (type === 'u8') return Buffer.from(array);
  const payload = Buffer.alloc(array.length * 4);
  for (let index = 0; index < array.length; index++) type === 'u32' ? payload.writeUInt32LE(array[index], index * 4) : payload.writeFloatLE(array[index], index * 4);
  return payload;
}
function writeArray(filePath, array, type, shape) {
  const payload = encode(array, type); fs.mkdirSync(path.dirname(filePath), {recursive: true}); fs.writeFileSync(filePath, payload);
  return {uri: filePath, sha256: shaBytes(payload), bytes: payload.length, shape, dtype: type};
}

function main() {
  const args = parseArgs();
  if (shaFile(args.spec) !== SPEC_SHA256 || fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) throw new Error('D12.12-D1 spec identity or fresh output violation');
  const spec = JSON.parse(fs.readFileSync(args.spec, 'utf8')), i1Path = spec.parents.materialOwnerSpec.uri;
  if (shaFile(i1Path) !== spec.parents.materialOwnerSpec.sha256) throw new Error('D12.12-D1 I1 spec identity mismatch');
  const i1Spec = JSON.parse(fs.readFileSync(i1Path, 'utf8')), h1Spec = JSON.parse(fs.readFileSync(i1Spec.parents.h1Spec.uri, 'utf8'));
  if (shaFile(process.execPath) !== spec.execution.node.sha256 || process.version !== spec.execution.node.version) throw new Error('D12.12-D1 Node runtime identity mismatch');
  const sourceFixture = h1Spec.fixtures.find(row => row.id === args.fixture), fixture = sourceFixture ? JSON.parse(JSON.stringify(sourceFixture)) : null;
  if (!fixture) throw new Error('unknown D12.12 fixture');
  for (const owner of fixture.owners) owner.passIndex = i1Spec.materialOwnerTokens.assignments[owner.analyticOwnerId];
  const [width, height] = fixture.resolution, pixels = width * height, adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8')), adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) throw new Error('D12.12-D1 adapter report mismatch');
  const arrays = {};
  for (const [name, [filename, channels]] of Object.entries(INPUTS)) { const [value, payload] = readF32(path.join(args['input-dir'], filename), pixels * channels); if (shaBytes(payload) !== adapter.arrays[name].sha256) throw new Error(`D12.12-D1 input hash mismatch: ${name}`); arrays[name] = value; }
  const localizationResult = JSON.parse(fs.readFileSync(spec.parents.ownerSupportLocalizationResult.uri, 'utf8')), localizationPayload = fs.readFileSync(args['localization-classification']), expectedLocalizationSha = localizationResult.payloadHashes[args.fixture][String(args.repeat)].classification;
  if (shaBytes(localizationPayload) !== expectedLocalizationSha || localizationPayload.length !== pixels) throw new Error('D12.12-D1 localization classification identity mismatch');
  const localizedOpportunity = new Uint8Array(pixels); for (let pixel = 0; pixel < pixels; pixel++) localizedOpportunity[pixel] = Number(localizationPayload[pixel] === 2);
  const structuralValid = new Uint8Array(pixels), radius2Interior = new Uint8Array(pixels), bilinearSupport = new Uint8Array(pixels), fullStencil = new Uint8Array(pixels), oneSidedEligible = new Uint8Array(pixels), oneSidedUnavailable = new Uint8Array(pixels);
  const factors = spec.candidateFamily.inflationFactors, threshold = Number(spec.frozenBaseline.riskThresholdQ30Inclusive), allowance = BigInt(spec.frozenBaseline.roundingAllowanceQ30), factorData = {};
  for (const factor of factors) factorData[factor] = {accepted: new Uint8Array(pixels), riskQ30: new Uint32Array(pixels * 3), acceptedReconstructed: new Float32Array(arrays.currentRgba)};
  const rgba = (pixel, channel) => pixel * 4 + channel, xy = (pixel, channel) => pixel * 2 + channel;
  function validTap(y, x, owner) { if (x < 0 || y < 0 || x >= width || y >= height) return false; const pixel = y * width + x; return arrays.previousOwner[pixel] === owner && arrays.previousRgba[rgba(pixel, 3)] > Math.fround(0.999); }
  function radius2(x, y, owner) { if (x < 2 || y < 2 || x >= width - 2 || y >= height - 2) return false; for (let ty = y - 2; ty <= y + 2; ty++) for (let tx = x - 2; tx <= x + 2; tx++) { const pixel = ty * width + tx; if (arrays.currentOwner[pixel] !== owner || arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999)) return false; } return true; }
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const pixel = y * width + x, oracle = oraclePixel(h1Spec, fixture, x, y); if (!oracle) continue;
    const owner = oracle.ownerToken, currentTolerance = Math.max(1, oracle.currentDepth) / 1024;
    if (arrays.currentOwner[pixel] !== owner || Math.abs(arrays.currentDepth[pixel] - oracle.currentDepth) > currentTolerance) continue;
    const vectorX = arrays.vector[xy(pixel, 0)], vectorY = arrays.vector[xy(pixel, 1)], qx = x + vectorX, qy = y - vectorY, sample = tapsAndWeights(qx, qy, width, height); if (!sample) continue;
    const tapPixels = sample.taps.map(([ty, tx]) => ty * width + tx);
    if (!tapPixels.every(tap => arrays.previousOwner[tap] === owner)) continue;
    if (arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999) || !tapPixels.every(tap => arrays.previousRgba[rgba(tap, 3)] > Math.fround(0.999))) continue;
    const sampledDepth = weighted(tapPixels.map(tap => arrays.previousDepth[tap]), sample.weights); if (Math.abs(sampledDepth - oracle.previousDepth) > Math.max(1, oracle.previousDepth) / 1024) continue;
    structuralValid[pixel] = 1; bilinearSupport[pixel] = 1; if (!radius2(x, y, owner)) continue; radius2Interior[pixel] = 1;
    const {x0, y0, fx, fy} = sample; let full = true;
    for (let ty = y0 - 1; ty <= y0 + 2; ty++) for (let tx = x0 - 1; tx <= x0 + 2; tx++) if (!validTap(ty, tx, owner)) full = false;
    fullStencil[pixel] = Number(full);
    const horizontal = [[validTap(y0, x0 - 1, owner), validTap(y0, x0 + 2, owner)], [validTap(y0 + 1, x0 - 1, owner), validTap(y0 + 1, x0 + 2, owner)]];
    const vertical = [[validTap(y0 - 1, x0, owner), validTap(y0 + 2, x0, owner)], [validTap(y0 - 1, x0 + 1, owner), validTap(y0 + 2, x0 + 1, owner)]];
    if (horizontal.some(row => !row[0] && !row[1]) || vertical.some(column => !column[0] && !column[1])) { oneSidedUnavailable[pixel] = 1; continue; }
    oneSidedEligible[pixel] = 1;
    const fxQ24 = exactScaled(fx, Q24, 'motion fraction x'), fyQ24 = exactScaled(fy, Q24, 'motion fraction y'), reconstructed = new Float32Array(4);
    for (let channel = 0; channel < 4; channel++) reconstructed[channel] = Math.fround(weighted(tapPixels.map(tap => arrays.previousRgba[rgba(tap, channel)]), sample.weights));
    for (let channel = 0; channel < 3; channel++) {
      const color = (yy, xx) => exactScaled(arrays.previousRgba[rgba(yy * width + xx, channel)], Q30, 'Q30 RGB');
      const horizontalValues = horizontal.map(([left, right], rowIndex) => { const yy = y0 + rowIndex, values = []; if (left) values.push(absolute(color(yy, x0 - 1) - 2n * color(yy, x0) + color(yy, x0 + 1))); if (right) values.push(absolute(color(yy, x0) - 2n * color(yy, x0 + 1) + color(yy, x0 + 2))); return [values, values.length === 1]; });
      const verticalValues = vertical.map(([top, bottom], columnIndex) => { const xx = x0 + columnIndex, values = []; if (top) values.push(absolute(color(y0 - 1, xx) - 2n * color(y0, xx) + color(y0 + 1, xx))); if (bottom) values.push(absolute(color(y0, xx) - 2n * color(y0 + 1, xx) + color(y0 + 2, xx))); return [values, values.length === 1]; });
      for (const factor of factors) {
        let mx = 0n, my = 0n;
        for (const [values, oneSided] of horizontalValues) { let value = values.reduce((left, right) => left > right ? left : right); if (oneSided) value *= BigInt(factor); if (value > mx) mx = value; }
        for (const [values, oneSided] of verticalValues) { let value = values.reduce((left, right) => left > right ? left : right); if (oneSided) value *= BigInt(factor); if (value > my) my = value; }
        const numerator = 2n * (fxQ24 * (Q24 - fxQ24) * mx + fyQ24 * (Q24 - fyQ24) * my), units = ceilDiv(numerator, Q24 * Q24) + allowance;
        factorData[factor].riskQ30[pixel * 3 + channel] = Number(units > UINT32_MAX ? UINT32_MAX : units);
      }
    }
    for (const factor of factors) {
      const data = factorData[factor], riskMaximum = Math.max(data.riskQ30[pixel * 3], data.riskQ30[pixel * 3 + 1], data.riskQ30[pixel * 3 + 2]);
      if (riskMaximum <= threshold) { data.accepted[pixel] = 1; for (let channel = 0; channel < 4; channel++) data.acceptedReconstructed[rgba(pixel, channel)] = reconstructed[channel]; }
    }
  }
  for (let pixel = 0; pixel < pixels; pixel++) if (radius2Interior[pixel] && !oneSidedEligible[pixel]) oneSidedUnavailable[pixel] = 1;
  fs.mkdirSync(args['output-dir'], {recursive: true});
  const controlValues = {structuralValid, radius2Interior, bilinearSupport, fullStencil, localizedOpportunity}, controlArrays = {};
  for (const [name, filename] of Object.entries(CONTROL_OUTPUTS)) controlArrays[name] = writeArray(path.join(args['output-dir'], 'control', filename), controlValues[name], 'u8', [height, width]);
  const factorArrays = {};
  for (const factor of factors) {
    const values = {oneSidedEligible, oneSidedUnavailable, ...factorData[factor]}, records = {};
    for (const [name, [filename, type]] of Object.entries(FACTOR_OUTPUTS)) records[name] = writeArray(path.join(args['output-dir'], `factor-${String(factor).padStart(2, '0')}`, filename), values[name], type, name === 'riskQ30' ? [height, width, 3] : name === 'acceptedReconstructed' ? [height, width, 4] : [height, width]);
    factorArrays[String(factor)] = records;
  }
  const body = {schemaVersion: 'bfs.blenderMaterialOwnerOneSidedCurvatureConsumerReport.v0.1', experimentId: spec.experimentId, producer: 'node', fixtureId: args.fixture, repeat: args.repeat, pid: process.pid, runtime: {node: process.version, nodeExecutableSha256: shaFile(process.execPath)}, adapter: {uri: args['adapter-report'], sha256: shaFile(args['adapter-report']), reportHash: adapter.reportHash}, localizationClassification: {uri: args['localization-classification'], sha256: shaBytes(localizationPayload)}, inflationFactors: factors, controlArrays, factorArrays, operationCounts: {consumerProcesses: 1, pixelsVisited: pixels, blenderRenderCalls: 0, modelCalls: 0, networkCalls: 0}};
  const report = {...body, reportHash: canonicalHash(body)}; fs.mkdirSync(path.dirname(args.report), {recursive: true}); fs.writeFileSync(args.report, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`BFS_B52_D1212_NODE fixture=${args.fixture} repeat=${args.repeat} factors=${factors.length}`);
}

main();
