#!/usr/bin/env node
/** Scalar Node decision consumer for B52-D12.14-H2. */
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import process from "node:process";

const SPEC_SHA256 = "2961f621b38f934cffaa7abe36deaaa5e01e7505d6361985039d0380578d244b";
const CORRECTION_SHA256 = "9b6fdcedd571ad1ec7fb8d02bc7c6a630014d204de02f4a8b74bf5509c625a92";
const INPUTS = {
  previousRgba: ["previous.rgba32", 4], currentRgba: ["current.rgba32", 4],
  previousDepth: ["previous-depth.f32", 1], currentDepth: ["current-depth.f32", 1],
  previousOwner: ["previous-owner.f32", 1], currentOwner: ["current-owner.f32", 1], vector: ["vector.xy32", 2],
};
const CONTROL_OUTPUTS = {
  registered: ["registered.u8", "u1"], bilinearSupport: ["bilinear-support.u8", "u1"],
  directZValid: ["direct-z-valid.u8", "u1"], inverseDepthValid: ["inverse-depth-valid.u8", "u1"],
  projectiveDepthRescued: ["projective-depth-rescued.u8", "u1"], radius2Interior: ["radius2-interior.u8", "u1"],
  neitherHorizontal: ["neither-horizontal.u8", "u1"], oneSidedUnavailable: ["one-sided-unavailable.u8", "u1"],
  consumerPredictedDepth: ["consumer-predicted-depth.f32", "<f4"], directZSample: ["direct-z-sample.f32", "<f4"],
  inverseDepthSample: ["inverse-depth-sample.f32", "<f4"],
};
const DECISION_OUTPUTS = {
  accepted: ["accepted.u8", "u1"], reason: ["reason.u8", "u1"], reconstructed: ["reconstructed.rgba32", "<f4"],
};

function shaBytes(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function shaFile(file) { return shaBytes(fs.readFileSync(file)); }
function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(key => [key, sorted(value[key])]));
  return value;
}
function canonicalHash(value) { return shaBytes(Buffer.from(JSON.stringify(sorted(value)))); }
function args() {
  const values = {};
  for (let i = 2; i < process.argv.length; i += 2) values[process.argv[i].replace(/^--/, "")] = process.argv[i + 1];
  for (const key of ["spec", "correction", "fixture", "repeat", "input-dir", "output-dir", "report"]) if (!(key in values)) throw new Error(`missing --${key}`);
  values.repeat = Number(values.repeat);
  if (![1, 2].includes(values.repeat)) throw new Error("invalid repeat");
  return values;
}
function rotationXYZ(values) {
  const [x, y, z] = values.map(Number), cx = Math.cos(x), sx = Math.sin(x), cy = Math.cos(y), sy = Math.sin(y), cz = Math.cos(z), sz = Math.sin(z);
  return [
    [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
    [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
    [-sy, cy * sx, cy * cx],
  ];
}
function transform(row) { return [row.location.map(Number), rotationXYZ(row.rotationEuler)]; }
function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
function subtract(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function matVec(m, v) { return m.map(row => row[0] * v[0] + row[1] * v[1] + row[2] * v[2]); }
function matTVec(m, v) { return [0, 1, 2].map(column => m[0][column] * v[0] + m[1][column] * v[1] + m[2][column] * v[2]); }
function ownerForToken(spec, token) { return spec.fixture.owners.find(owner => Math.fround(owner.materialPassIndex) === token) ?? null; }
function ownerTransform(spec, owner, frame) { return transform(spec.sceneContract[owner.role].transformByFrame[String(frame)]); }
function cameraTransform(spec, frame) {
  const camera = spec.sceneContract.camera;
  return transform({location: camera.locationByFrame[String(frame)], rotationEuler: camera.rotationEulerByFrame[String(frame)]});
}
function consumerPredictedDepth(spec, owner, x, y, currentDepth, width, height) {
  if (!Number.isFinite(currentDepth) || currentDepth <= 0) return null;
  const camera = spec.sceneContract.camera, lens = Number(camera.lensMm), sensorWidth = Number(camera.sensorWidthMm), sensorHeight = sensorWidth * height / width;
  const u = (x + 0.5) / width, vBottom = 1 - (y + 0.5) / height;
  const cameraPoint = [(u - 0.5) * sensorWidth / lens * currentDepth, (vBottom - 0.5) * sensorHeight / lens * currentDepth, -currentDepth];
  const currentCamera = cameraTransform(spec, 1), currentWorld = add(currentCamera[0], matVec(currentCamera[1], cameraPoint));
  const currentOwner = ownerTransform(spec, owner, 1), local = matTVec(currentOwner[1], subtract(currentWorld, currentOwner[0]));
  const previousOwner = ownerTransform(spec, owner, 0), previousWorld = add(previousOwner[0], matVec(previousOwner[1], local));
  const previousCamera = cameraTransform(spec, 0), previousCameraPoint = matTVec(previousCamera[1], subtract(previousWorld, previousCamera[0]));
  const depth = -previousCameraPoint[2];
  return Number.isFinite(depth) && depth > 0 ? depth : null;
}
function tapsAndWeights(qx, qy, width, height) {
  const x0 = Math.floor(qx), y0 = Math.floor(qy);
  if (x0 < 0 || y0 < 0 || x0 + 1 >= width || y0 + 1 >= height) return null;
  const fx = qx - x0, fy = qy - y0;
  return {taps: [[y0, x0], [y0, x0 + 1], [y0 + 1, x0], [y0 + 1, x0 + 1]], weights: [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy], x0, y0};
}
function weighted(values, weights) { return ((values[0] * weights[0] + values[1] * weights[1]) + values[2] * weights[2]) + values[3] * weights[3]; }
function floatArray(buffer) { return new Float32Array(buffer.buffer, buffer.byteOffset, buffer.byteLength / 4); }
function index2(y, x, width) { return y * width + x; }
function index3(y, x, width, channels, channel) { return (y * width + x) * channels + channel; }
function sameOwner(arrays, y, x, owner, width, height) {
  return x >= 0 && y >= 0 && x < width && y < height && arrays.previousOwner[index2(y, x, width)] === owner && arrays.previousRgba[index3(y, x, width, 4, 3)] > Math.fround(0.999);
}
function currentRadius2(arrays, x, y, owner, width, height) {
  if (x < 2 || y < 2 || x >= width - 2 || y >= height - 2) return false;
  for (let yy = y - 2; yy <= y + 2; yy++) for (let xx = x - 2; xx <= x + 2; xx++) {
    if (arrays.currentOwner[index2(yy, xx, width)] !== owner || arrays.currentRgba[index3(yy, xx, width, 4, 3)] <= Math.fround(0.999)) return false;
  }
  return true;
}
function floatBuffer(values) {
  const buffer = Buffer.alloc(values.length * 4);
  for (let i = 0; i < values.length; i++) buffer.writeFloatLE(values[i], i * 4);
  return buffer;
}
function writeArray(file, value, dtype, shape) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  const payload = dtype === "u1" ? Buffer.from(value.buffer, value.byteOffset, value.byteLength) : floatBuffer(value);
  fs.writeFileSync(file, payload);
  return {uri: file, sha256: shaBytes(payload), bytes: payload.length, shape, dtype};
}
function sumMask(mask) { let sum = 0; for (const value of mask) sum += value; return sum; }

function main() {
  const cli = args();
  if (shaFile(cli.spec) !== SPEC_SHA256 || shaFile(cli.correction) !== CORRECTION_SHA256 || fs.existsSync(cli["output-dir"]) || fs.existsSync(cli.report)) throw new Error("H2 Node identity/output freshness failure");
  const spec = JSON.parse(fs.readFileSync(cli.spec, "utf8"));
  if (cli.fixture !== spec.fixture.id || path.basename(cli["input-dir"]) !== "decision" || !fs.statSync(cli["input-dir"]).isDirectory()) throw new Error("H2 Node fixture/input boundary mismatch");
  if (shaFile(process.execPath) !== spec.runtime.node.sha256 || process.version !== spec.runtime.node.version) throw new Error("H2 Node runtime mismatch");
  const [width, height] = spec.sceneContract.render.resolution, pixels = width * height;
  const arrays = {}, inputRecords = {};
  for (const [name, [filename, channels]] of Object.entries(INPUTS)) {
    const file = path.join(cli["input-dir"], filename), buffer = fs.readFileSync(file), expected = pixels * channels * 4;
    if (buffer.length !== expected) throw new Error(`H2 Node input bytes mismatch ${name}`);
    arrays[name] = floatArray(buffer);
    inputRecords[name] = {filename, sha256: shaBytes(buffer), bytes: buffer.length, shape: channels > 1 ? [height, width, channels] : [height, width]};
  }
  const masks = {};
  for (const name of ["registered", "bilinearSupport", "directZValid", "inverseDepthValid", "projectiveDepthRescued", "radius2Interior", "neitherHorizontal", "oneSidedUnavailable", "accepted"]) masks[name] = new Uint8Array(pixels);
  const reason = new Uint8Array(pixels), predicted = new Float32Array(pixels), directSample = new Float32Array(pixels), inverseSample = new Float32Array(pixels);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const i = index2(y, x, width), ownerToken = arrays.currentOwner[i], owner = ownerForToken(spec, ownerToken), alpha = arrays.currentRgba[index3(y, x, width, 4, 3)];
    if (!owner || ownerToken === Math.fround(0) || alpha <= Math.fround(0.999)) continue;
    const values = [arrays.currentRgba[index3(y, x, width, 4, 0)], arrays.currentRgba[index3(y, x, width, 4, 1)], arrays.currentRgba[index3(y, x, width, 4, 2)], alpha, arrays.currentDepth[i], arrays.vector[index3(y, x, width, 2, 0)], arrays.vector[index3(y, x, width, 2, 1)]];
    if (!values.every(Number.isFinite)) continue;
    masks.registered[i] = 1;
    const qx = x + arrays.vector[index3(y, x, width, 2, 0)], qy = y - arrays.vector[index3(y, x, width, 2, 1)], sample = tapsAndWeights(qx, qy, width, height);
    if (!sample) { reason[i] = 2; continue; }
    if (!sample.taps.every(([yy, xx]) => sameOwner(arrays, yy, xx, ownerToken, width, height))) { reason[i] = 3; continue; }
    const depths = sample.taps.map(([yy, xx]) => arrays.previousDepth[index2(yy, xx, width)]);
    if (!depths.every(value => Number.isFinite(value) && value > 0)) { reason[i] = 4; continue; }
    masks.bilinearSupport[i] = 1;
    const predictedDepth = consumerPredictedDepth(spec, owner, x, y, arrays.currentDepth[i], width, height);
    if (predictedDepth === null) { reason[i] = 4; continue; }
    const direct = weighted(depths, sample.weights), reciprocal = weighted(depths.map(value => 1 / value), sample.weights), inverse = reciprocal > 0 && Number.isFinite(reciprocal) ? 1 / reciprocal : NaN;
    predicted[i] = Math.fround(predictedDepth); directSample[i] = Math.fround(direct); inverseSample[i] = Math.fround(Number.isFinite(inverse) ? inverse : 0);
    const tolerance = Math.max(1, predictedDepth) / 1024, directValid = Math.abs(direct - predictedDepth) <= tolerance, inverseValid = Number.isFinite(inverse) && Math.abs(inverse - predictedDepth) <= tolerance;
    masks.directZValid[i] = Number(directValid); masks.inverseDepthValid[i] = Number(inverseValid); masks.projectiveDepthRescued[i] = Number(inverseValid && !directValid);
    if (!inverseValid) { reason[i] = 4; continue; }
    if (!currentRadius2(arrays, x, y, ownerToken, width, height)) { reason[i] = 5; continue; }
    masks.radius2Interior[i] = 1;
    const horizontal = [sample.y0, sample.y0 + 1].map(yy => [sameOwner(arrays, yy, sample.x0 - 1, ownerToken, width, height), sameOwner(arrays, yy, sample.x0 + 2, ownerToken, width, height)]);
    const vertical = [sample.x0, sample.x0 + 1].map(xx => [sameOwner(arrays, sample.y0 - 1, xx, ownerToken, width, height), sameOwner(arrays, sample.y0 + 2, xx, ownerToken, width, height)]);
    const neitherHorizontal = horizontal.some(([left, right]) => !left && !right), neitherVertical = vertical.some(([top, bottom]) => !top && !bottom);
    masks.neitherHorizontal[i] = Number(neitherHorizontal);
    if (neitherHorizontal || neitherVertical) { masks.oneSidedUnavailable[i] = 1; reason[i] = 6; continue; }
    reason[i] = 7;
  }
  fs.mkdirSync(cli["output-dir"], {recursive: false});
  const controlValues = {...masks, consumerPredictedDepth: predicted, directZSample: directSample, inverseDepthSample: inverseSample};
  const controlRecords = {};
  for (const [name, [filename, dtype]] of Object.entries(CONTROL_OUTPUTS)) controlRecords[name] = writeArray(path.join(cli["output-dir"], "control", filename), controlValues[name], dtype, [height, width]);
  const decisionValues = {...masks, reason, reconstructed: arrays.currentRgba};
  const decisionRecords = {};
  for (const [name, [filename, dtype]] of Object.entries(DECISION_OUTPUTS)) decisionRecords[name] = writeArray(path.join(cli["output-dir"], "decision", filename), decisionValues[name], dtype, name === "reconstructed" ? [height, width, 4] : [height, width]);
  const counts = Object.fromEntries(Object.entries(masks).map(([name, value]) => [name, sumMask(value)]));
  const body = {
    schemaVersion: "bfs.blenderMaterialOwnerProjectiveDepthConsumer.v0.1", experimentId: spec.experimentId, specSha256: SPEC_SHA256, correctionSha256: CORRECTION_SHA256,
    producer: "node", fixtureId: cli.fixture, repeat: cli.repeat, pid: process.pid,
    runtime: {node: process.version, nodeExecutableSha256: shaFile(process.execPath)},
    inputBoundary: {directoryName: path.basename(cli["input-dir"]), positionAvailable: false, objectIndexAvailable: false, arrays: inputRecords},
    controlArrays: controlRecords, decisionArrays: decisionRecords, counts,
    reasonCodes: {NOT_REGISTERED: 0, INVALID_BOUNDS: 2, INVALID_OWNER: 3, INVALID_PROJECTIVE_DEPTH: 4, OUTSIDE_RADIUS2: 5, SUPPORT_UNAVAILABLE: 6, RISK_REJECTED: 7, ACCEPTED: 8},
    operationCounts: {consumerProcesses: 1, pixelsVisited: pixels, blenderRenderCalls: 0, modelCalls: 0, networkCalls: 0},
  };
  const report = {...body, reportHash: canonicalHash(body)};
  fs.mkdirSync(path.dirname(cli.report), {recursive: true}); fs.writeFileSync(cli.report, JSON.stringify(sorted(report), null, 2) + "\n");
  console.log(`BFS_D1214H2_NODE repeat=${cli.repeat} rescued=${counts.projectiveDepthRescued} neither=${counts.neitherHorizontal}`);
}

main();
