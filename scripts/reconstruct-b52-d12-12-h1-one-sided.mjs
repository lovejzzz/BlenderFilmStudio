#!/usr/bin/env node
/** Independent scalar Node consumer for B52-D12.12-H1. */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const SPEC_SHA256 = 'b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648';
const Q24 = 1n << 24n;
const Q30 = 1n << 30n;
const UINT32_MAX = (1n << 32n) - 1n;
const INPUTS = {
  previousRgba: ['previous.rgba32', 4],
  currentRgba: ['current.rgba32', 4],
  previousDepth: ['previous-depth.f32', 1],
  currentDepth: ['current-depth.f32', 1],
  previousOwner: ['previous-owner.f32', 1],
  currentOwner: ['current-owner.f32', 1],
  previousObjectIndex: ['previous-object-index.f32', 1],
  currentObjectIndex: ['current-object-index.f32', 1],
  vector: ['vector.xy32', 2],
};
const CONTROL_OUTPUTS = {
  registered: ['registered.u8', 'u1'],
  structuralValid: ['structural-valid.u8', 'u1'],
  radius2Interior: ['radius2-interior.u8', 'u1'],
  bilinearSupport: ['bilinear-support.u8', 'u1'],
  fullStencil: ['full-stencil.u8', 'u1'],
  directionLeft: ['direction-left.u8', 'u1'],
  directionRight: ['direction-right.u8', 'u1'],
  directionTop: ['direction-top.u8', 'u1'],
  directionBottom: ['direction-bottom.u8', 'u1'],
  neitherHorizontal: ['neither-horizontal.u8', 'u1'],
  analyticValidHistory: ['analytic-valid-history.u8', 'u1'],
  symmetricAccepted: ['symmetric-accepted.u8', 'u1'],
  symmetricRiskQ30: ['symmetric-risk.q30.u32', '<u4'],
};
const DECISION_OUTPUTS = {
  oneSidedEligible: ['one-sided-eligible.u8', 'u1'],
  oneSidedUnavailable: ['one-sided-unavailable.u8', 'u1'],
  accepted: ['accepted.u8', 'u1'],
  reason: ['reason.u8', 'u1'],
  riskQ30: ['risk.q30.u32', '<u4'],
  reconstructed: ['reconstructed.rgba32', '<f4'],
};

function shaBytes(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function shaFile(filePath) {
  return shaBytes(fs.readFileSync(filePath));
}

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function canonicalHash(value) {
  return shaBytes(Buffer.from(stable(value)));
}

function parseArgs() {
  const result = {};
  for (let index = 2; index < process.argv.length; index += 2) {
    const key = process.argv[index];
    if (!key.startsWith('--') || index + 1 >= process.argv.length) throw new Error('invalid D12.12-H1 arguments');
    result[key.slice(2)] = process.argv[index + 1];
  }
  for (const key of ['spec', 'fixture', 'repeat', 'input-dir', 'adapter-report', 'output-dir', 'report']) {
    if (!(key in result)) throw new Error(`missing --${key}`);
  }
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) throw new Error('invalid D12.12-H1 repeat');
  return result;
}

function readF32(filePath, expectedCount) {
  const payload = fs.readFileSync(filePath);
  if (payload.length !== expectedCount * 4) throw new Error(`D12.12-H1 float32 length mismatch: ${filePath}`);
  const result = new Float32Array(expectedCount);
  for (let index = 0; index < expectedCount; index++) result[index] = payload.readFloatLE(index * 4);
  return [result, payload];
}

function rotationXyz(values) {
  const [x, y, z] = values.map(Number);
  const cx = Math.cos(x), sx = Math.sin(x);
  const cy = Math.cos(y), sy = Math.sin(y);
  const cz = Math.cos(z), sz = Math.sin(z);
  return [
    [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
    [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
    [-sy, cy * sx, cy * cx],
  ];
}

function transform(row) {
  return [row.location.map(Number), rotationXyz(row.rotationEuler)];
}

const add = (left, right) => [left[0] + right[0], left[1] + right[1], left[2] + right[2]];
const subtract = (left, right) => [left[0] - right[0], left[1] - right[1], left[2] - right[2]];
const scale = (vector, value) => [vector[0] * value, vector[1] * value, vector[2] * value];
const dot = (left, right) => left[0] * right[0] + left[1] * right[1] + left[2] * right[2];

function matVec(matrix, vector) {
  return [0, 1, 2].map((row) => matrix[row][0] * vector[0] + matrix[row][1] * vector[1] + matrix[row][2] * vector[2]);
}

function matTVec(matrix, vector) {
  return [0, 1, 2].map((column) => matrix[0][column] * vector[0] + matrix[1][column] * vector[1] + matrix[2][column] * vector[2]);
}

function project(point, cameraTransform, width, height, lens, sensorWidth) {
  const cameraPoint = matTVec(cameraTransform[1], subtract(point, cameraTransform[0]));
  const depth = -cameraPoint[2];
  if (depth <= 0) return null;
  const sensorHeight = sensorWidth * height / width;
  const u = 0.5 + lens * cameraPoint[0] / (depth * sensorWidth);
  const vBottom = 0.5 + lens * cameraPoint[1] / (depth * sensorHeight);
  return [u * width - 0.5, (1 - vBottom) * height - 0.5, depth];
}

function surfaceAt(spec, fixture, frame, pixelX, pixelY) {
  const [width, height] = fixture.resolution;
  const cameraSpec = spec.sceneContract.camera;
  const lens = Number(cameraSpec.lensMm), sensorWidth = Number(cameraSpec.sensorWidthMm);
  const sensorHeight = sensorWidth * height / width;
  const camera = transform(fixture.cameraByFrame[String(frame)]);
  const u = (pixelX + 0.5) / width;
  const vBottom = 1 - (pixelY + 0.5) / height;
  const cameraDirection = [(u - 0.5) * sensorWidth / lens, (vBottom - 0.5) * sensorHeight / lens, -1];
  const worldDirection = matVec(camera[1], cameraDirection);
  const candidates = [];
  for (const owner of fixture.owners) {
    const ownerTransform = transform(owner.transformByFrame[String(frame)]);
    const normal = matVec(ownerTransform[1], [0, 0, 1]);
    const denominator = dot(worldDirection, normal);
    if (Math.abs(denominator) < 1e-12) continue;
    const distance = dot(subtract(ownerTransform[0], camera[0]), normal) / denominator;
    if (distance <= 0) continue;
    const worldPoint = add(camera[0], scale(worldDirection, distance));
    const localPoint = matTVec(ownerTransform[1], subtract(worldPoint, ownerTransform[0]));
    const [sizeX, sizeY] = owner.sizeWorld.map(Number);
    if (Math.abs(localPoint[0]) <= sizeX / 2 && Math.abs(localPoint[1]) <= sizeY / 2) {
      const projected = project(worldPoint, camera, width, height, lens, sensorWidth);
      if (projected) candidates.push([projected[2], owner, localPoint]);
    }
  }
  if (!candidates.length) return null;
  candidates.sort((left, right) => left[0] - right[0]);
  return candidates[0];
}

function oraclePixel(spec, fixture, x, y) {
  const [width, height] = fixture.resolution;
  const cameraSpec = spec.sceneContract.camera;
  const lens = Number(cameraSpec.lensMm), sensorWidth = Number(cameraSpec.sensorWidthMm);
  const current = surfaceAt(spec, fixture, 1, x, y);
  if (!current) return null;
  const [currentDepth, owner, localPoint] = current;
  const previousOwner = transform(owner.transformByFrame['0']);
  const previousWorld = add(previousOwner[0], matVec(previousOwner[1], localPoint));
  const previousCamera = transform(fixture.cameraByFrame['0']);
  const previous = project(previousWorld, previousCamera, width, height, lens, sensorWidth);
  if (!previous) return null;
  const [previousX, previousY, previousDepth] = previous;
  let visible = null;
  if (previousX >= -0.5 && previousX < width - 0.5 && previousY >= -0.5 && previousY < height - 0.5) {
    visible = surfaceAt(spec, fixture, 0, previousX, previousY);
  }
  const validHistory = Boolean(
    visible
    && visible[1].analyticOwnerId === owner.analyticOwnerId
    && Math.abs(visible[0] - previousDepth) <= Math.max(1, previousDepth) / 4096,
  );
  return {
    ownerToken: Math.fround(owner.materialPassIndex),
    objectIndex: Math.fround(owner.objectPassIndex),
    currentDepth,
    previousDepth,
    previousX,
    previousY,
    expectedVector: [previousX - x, y - previousY],
    validHistory,
  };
}

function tapsAndWeights(qx, qy, width, height) {
  const x0 = Math.floor(qx), y0 = Math.floor(qy);
  if (x0 < 0 || y0 < 0 || x0 + 1 >= width || y0 + 1 >= height) return null;
  const fx = qx - x0, fy = qy - y0;
  return {
    taps: [[y0, x0], [y0, x0 + 1], [y0 + 1, x0], [y0 + 1, x0 + 1]],
    weights: [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy],
    x0, y0, fx, fy,
  };
}

function weighted(values, weights) {
  return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3];
}

function exactScaled(value, scaleValue, label) {
  const scaled = value * Number(scaleValue);
  if (!Number.isInteger(scaled)) throw new Error(`non-canonical ${label}: ${value}`);
  return BigInt(scaled);
}

function absolute(value) {
  return value < 0n ? -value : value;
}

function ceilDiv(numerator, denominator) {
  return (numerator + denominator - 1n) / denominator;
}

function encode(array, dtype) {
  if (dtype === 'u1') return Buffer.from(array);
  const payload = Buffer.alloc(array.length * 4);
  for (let index = 0; index < array.length; index++) {
    if (dtype === '<u4') payload.writeUInt32LE(array[index], index * 4);
    else payload.writeFloatLE(array[index], index * 4);
  }
  return payload;
}

function writeArray(filePath, array, dtype, shape) {
  const payload = encode(array, dtype);
  fs.mkdirSync(path.dirname(filePath), {recursive: true});
  fs.writeFileSync(filePath, payload);
  return {uri: filePath, sha256: shaBytes(payload), bytes: payload.length, shape, dtype};
}

function main() {
  const args = parseArgs();
  if (shaFile(args.spec) !== SPEC_SHA256 || fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) {
    throw new Error('D12.12-H1 spec identity or fresh consumer output violation');
  }
  const spec = JSON.parse(fs.readFileSync(args.spec, 'utf8'));
  if (shaFile(process.execPath) !== spec.runtime.node.sha256 || process.version !== spec.runtime.node.version) {
    throw new Error('D12.12-H1 Node runtime identity mismatch');
  }
  const fixture = spec.fixtures.find((row) => row.id === args.fixture);
  if (!fixture) throw new Error('unknown D12.12-H1 fixture');
  const [width, height] = fixture.resolution, pixels = width * height;
  const adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8'));
  const adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) {
    throw new Error('D12.12-H1 adapter report mismatch');
  }
  const arrays = {};
  for (const [name, [filename, channels]] of Object.entries(INPUTS)) {
    const [value, payload] = readF32(path.join(args['input-dir'], filename), pixels * channels);
    if (shaBytes(payload) !== adapter.arrays[name].sha256) throw new Error(`D12.12-H1 input hash mismatch: ${name}`);
    arrays[name] = value;
  }

  const masks = {};
  for (const name of [
    'registered', 'structuralValid', 'radius2Interior', 'bilinearSupport', 'fullStencil',
    'directionLeft', 'directionRight', 'directionTop', 'directionBottom', 'neitherHorizontal',
    'analyticValidHistory', 'symmetricAccepted', 'oneSidedEligible', 'oneSidedUnavailable', 'accepted',
  ]) masks[name] = new Uint8Array(pixels);
  const reason = new Uint8Array(pixels);
  const risk = new Uint32Array(pixels * 3);
  const symmetricRisk = new Uint32Array(pixels * 3);
  const reconstructed = new Float32Array(arrays.currentRgba);
  const threshold = Number(spec.frozenCandidate.riskThresholdQ30Inclusive);
  const allowance = BigInt(spec.frozenCandidate.roundingAllowanceQ30);
  const rgba = (pixel, channel) => pixel * 4 + channel;
  const xy = (pixel, channel) => pixel * 2 + channel;
  const rgb = (pixel, channel) => pixel * 3 + channel;

  function validTap(y, x, owner) {
    if (x < 0 || y < 0 || x >= width || y >= height) return false;
    const pixel = y * width + x;
    return arrays.previousOwner[pixel] === owner && arrays.previousRgba[rgba(pixel, 3)] > Math.fround(0.999);
  }

  function currentRadius2(x, y, owner) {
    if (x < 2 || y < 2 || x >= width - 2 || y >= height - 2) return false;
    for (let ty = y - 2; ty <= y + 2; ty++) {
      for (let tx = x - 2; tx <= x + 2; tx++) {
        const pixel = ty * width + tx;
        if (arrays.currentOwner[pixel] !== owner || arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999)) return false;
      }
    }
    return true;
  }

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const pixel = y * width + x;
      const ownerValue = arrays.currentOwner[pixel];
      if (ownerValue === Math.fround(0) || arrays.currentRgba[rgba(pixel, 3)] <= Math.fround(0.999)) continue;
      masks.registered[pixel] = 1;
      const oracle = oraclePixel(spec, fixture, x, y);
      if (!oracle) {
        reason[pixel] = 1;
        continue;
      }
      masks.analyticValidHistory[pixel] = Number(oracle.validHistory);
      const tolerance = Math.max(1, oracle.currentDepth) / 1024;
      if (
        ownerValue !== oracle.ownerToken
        || arrays.currentObjectIndex[pixel] !== oracle.objectIndex
        || Math.abs(arrays.currentDepth[pixel] - oracle.currentDepth) > tolerance
      ) {
        reason[pixel] = 1;
        continue;
      }
      const vectorX = arrays.vector[xy(pixel, 0)], vectorY = arrays.vector[xy(pixel, 1)];
      const sample = tapsAndWeights(x + vectorX, y - vectorY, width, height);
      if (!sample) {
        reason[pixel] = 2;
        continue;
      }
      const tapPixels = sample.taps.map(([ty, tx]) => ty * width + tx);
      if (!tapPixels.every((tap) => arrays.previousOwner[tap] === ownerValue)) {
        reason[pixel] = 3;
        continue;
      }
      if (!tapPixels.every((tap) => arrays.previousRgba[rgba(tap, 3)] > Math.fround(0.999))) {
        reason[pixel] = 3;
        continue;
      }
      masks.bilinearSupport[pixel] = 1;
      const sampledDepth = weighted(tapPixels.map((tap) => arrays.previousDepth[tap]), sample.weights);
      if (Math.abs(sampledDepth - oracle.previousDepth) > Math.max(1, oracle.previousDepth) / 1024) {
        reason[pixel] = 4;
        continue;
      }
      masks.structuralValid[pixel] = 1;
      if (!currentRadius2(x, y, ownerValue)) {
        reason[pixel] = 5;
        continue;
      }
      masks.radius2Interior[pixel] = 1;
      const {x0, y0, fx, fy} = sample;
      const horizontal = [
        [validTap(y0, x0 - 1, ownerValue), validTap(y0, x0 + 2, ownerValue)],
        [validTap(y0 + 1, x0 - 1, ownerValue), validTap(y0 + 1, x0 + 2, ownerValue)],
      ];
      const vertical = [
        [validTap(y0 - 1, x0, ownerValue), validTap(y0 + 2, x0, ownerValue)],
        [validTap(y0 - 1, x0 + 1, ownerValue), validTap(y0 + 2, x0 + 1, ownerValue)],
      ];
      const full = horizontal.every(([left, right]) => left && right) && vertical.every(([top, bottom]) => top && bottom);
      masks.fullStencil[pixel] = Number(full);
      const verticalFull = vertical.every(([top, bottom]) => top && bottom);
      const horizontalFull = horizontal.every(([left, right]) => left && right);
      masks.directionLeft[pixel] = Number(horizontal.every(([left, right]) => !left && right) && verticalFull);
      masks.directionRight[pixel] = Number(horizontal.every(([left, right]) => left && !right) && verticalFull);
      masks.directionTop[pixel] = Number(vertical.every(([top, bottom]) => !top && bottom) && horizontalFull);
      masks.directionBottom[pixel] = Number(vertical.every(([top, bottom]) => top && !bottom) && horizontalFull);
      masks.neitherHorizontal[pixel] = Number(horizontal.some(([left, right]) => !left && !right));
      if (horizontal.some(([left, right]) => !left && !right) || vertical.some(([top, bottom]) => !top && !bottom)) {
        masks.oneSidedUnavailable[pixel] = 1;
        reason[pixel] = 6;
        continue;
      }
      masks.oneSidedEligible[pixel] = 1;
      const fxQ24 = exactScaled(fx, Q24, 'motion fraction x');
      const fyQ24 = exactScaled(fy, Q24, 'motion fraction y');
      const bilinear = new Float32Array(4);
      for (let channel = 0; channel < 4; channel++) {
        bilinear[channel] = Math.fround(weighted(tapPixels.map((tap) => arrays.previousRgba[rgba(tap, channel)]), sample.weights));
      }

      for (let channel = 0; channel < 3; channel++) {
        const color = (yy, xx) => exactScaled(arrays.previousRgba[rgba(yy * width + xx, channel)], Q30, 'Q30 RGB');
        const rowValues = horizontal.map(([left, right], rowIndex) => {
          const yy = y0 + rowIndex, values = [];
          if (left) values.push(absolute(color(yy, x0 - 1) - 2n * color(yy, x0) + color(yy, x0 + 1)));
          if (right) values.push(absolute(color(yy, x0) - 2n * color(yy, x0 + 1) + color(yy, x0 + 2)));
          return values;
        });
        const columnValues = vertical.map(([top, bottom], columnIndex) => {
          const xx = x0 + columnIndex, values = [];
          if (top) values.push(absolute(color(y0 - 1, xx) - 2n * color(y0, xx) + color(y0 + 1, xx)));
          if (bottom) values.push(absolute(color(y0, xx) - 2n * color(y0 + 1, xx) + color(y0 + 2, xx)));
          return values;
        });
        const mx = rowValues.map((values) => values.reduce((left, right) => left > right ? left : right)).reduce((left, right) => left > right ? left : right);
        const my = columnValues.map((values) => values.reduce((left, right) => left > right ? left : right)).reduce((left, right) => left > right ? left : right);
        const numerator = 2n * (fxQ24 * (Q24 - fxQ24) * mx + fyQ24 * (Q24 - fyQ24) * my);
        const units = ceilDiv(numerator, Q24 * Q24) + allowance;
        const stored = Number(units > UINT32_MAX ? UINT32_MAX : units);
        risk[rgb(pixel, channel)] = stored;
        if (full) symmetricRisk[rgb(pixel, channel)] = stored;
      }
      if (full && Math.max(symmetricRisk[rgb(pixel, 0)], symmetricRisk[rgb(pixel, 1)], symmetricRisk[rgb(pixel, 2)]) <= threshold) {
        masks.symmetricAccepted[pixel] = 1;
      }
      if (Math.max(risk[rgb(pixel, 0)], risk[rgb(pixel, 1)], risk[rgb(pixel, 2)]) <= threshold) {
        masks.accepted[pixel] = 1;
        reason[pixel] = 8;
        for (let channel = 0; channel < 4; channel++) reconstructed[rgba(pixel, channel)] = bilinear[channel];
      } else {
        reason[pixel] = 7;
      }
    }
  }

  for (let pixel = 0; pixel < pixels; pixel++) {
    if (masks.radius2Interior[pixel] && !masks.oneSidedEligible[pixel]) masks.oneSidedUnavailable[pixel] = 1;
  }
  fs.mkdirSync(args['output-dir'], {recursive: true});
  const controlValues = {...masks, symmetricRiskQ30: symmetricRisk};
  const controlArrays = {};
  for (const [name, [filename, dtype]] of Object.entries(CONTROL_OUTPUTS)) {
    controlArrays[name] = writeArray(
      path.join(args['output-dir'], 'control', filename),
      controlValues[name],
      dtype,
      name === 'symmetricRiskQ30' ? [height, width, 3] : [height, width],
    );
  }
  const decisionValues = {...masks, reason, riskQ30: risk, reconstructed};
  const decisionArrays = {};
  for (const [name, [filename, dtype]] of Object.entries(DECISION_OUTPUTS)) {
    decisionArrays[name] = writeArray(
      path.join(args['output-dir'], 'decision', filename),
      decisionValues[name],
      dtype,
      name === 'riskQ30' ? [height, width, 3] : name === 'reconstructed' ? [height, width, 4] : [height, width],
    );
  }
  const body = {
    schemaVersion: 'bfs.blenderMaterialOwnerOneSidedCurvatureHoldoutConsumerReport.v0.1',
    experimentId: spec.experimentId,
    specSha256: SPEC_SHA256,
    producer: 'node',
    fixtureId: args.fixture,
    repeat: args.repeat,
    pid: process.pid,
    runtime: {node: process.version, nodeExecutableSha256: shaFile(process.execPath)},
    adapter: {uri: args['adapter-report'], sha256: shaFile(args['adapter-report']), reportHash: adapter.reportHash},
    factor: 1,
    controlArrays,
    decisionArrays,
    reasonCodes: {
      NOT_REGISTERED: 0,
      INVALID_CURRENT_ORACLE: 1,
      INVALID_BOUNDS: 2,
      INVALID_OWNER: 3,
      INVALID_DEPTH: 4,
      OUTSIDE_RADIUS2: 5,
      SUPPORT_UNAVAILABLE: 6,
      RISK_REJECTED: 7,
      ACCEPTED: 8,
    },
    operationCounts: {consumerProcesses: 1, pixelsVisited: pixels, blenderRenderCalls: 0, modelCalls: 0, networkCalls: 0},
  };
  const report = {...body, reportHash: canonicalHash(body)};
  fs.mkdirSync(path.dirname(args.report), {recursive: true});
  fs.writeFileSync(args.report, `${JSON.stringify(report, null, 2)}\n`);
  const acceptedCount = masks.accepted.reduce((sum, value) => sum + value, 0);
  console.log(`BFS_B52_D1212H1_NODE fixture=${args.fixture} repeat=${args.repeat} accepted=${acceptedCount}`);
}

main();
