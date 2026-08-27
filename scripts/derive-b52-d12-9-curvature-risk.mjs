#!/usr/bin/env node
/** Node producer for the exploratory B52-D12.9-D1 Q30 curvature risk. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const Q24 = 1n << 24n;
const Q30 = 1n << 30n;
const UINT32_MAX = (1n << 32n) - 1n;

function arg(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) throw new Error(`missing ${name}`);
  return process.argv[index + 1];
}
function shaBytes(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function shaFile(filePath) { return shaBytes(fs.readFileSync(filePath)); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value !== null && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  if (typeof value === "number" && Number.isFinite(value) && value !== 0 && Math.abs(value) < 1e-4) {
    const [mantissa, exponent] = value.toExponential().split("e");
    const sign = exponent.startsWith("-") ? "-" : "+";
    return `${mantissa}e${sign}${Math.abs(Number(exponent)).toString().padStart(2, "0")}`;
  }
  return JSON.stringify(value);
}
function canonicalHash(value) { return shaBytes(Buffer.from(stable(value))); }
function validateReport(filePath) {
  const report = JSON.parse(fs.readFileSync(filePath, "utf8"));
  const body = Object.fromEntries(Object.entries(report).filter(([key]) => key !== "reportHash"));
  if (report.reportHash !== canonicalHash(body)) throw new Error(`report self-hash mismatch: ${filePath}`);
  return report;
}
function load(filePath, expectedSha) {
  const payload = fs.readFileSync(filePath);
  if (shaBytes(payload) !== expectedSha) throw new Error(`array hash mismatch: ${filePath}`);
  return payload;
}
function exactScaled(value, scale, label) {
  const scaled = value * Number(scale);
  if (!Number.isInteger(scaled)) throw new Error(`non-canonical ${label}: ${value}`);
  return BigInt(scaled);
}
function ceilDiv(numerator, denominator) { return (numerator + denominator - 1n) / denominator; }
function float32(payload) { return new Float32Array(payload.buffer, payload.byteOffset, payload.byteLength / 4); }
function uint8(payload) { return new Uint8Array(payload.buffer, payload.byteOffset, payload.byteLength); }
function f32(array, width, channels, y, x, channel = 0) { return array[(y * width + x) * channels + channel]; }

const specPath = path.resolve(arg("--spec"));
const sourceRoot = path.resolve(arg("--source-root"));
const outputRoot = path.resolve(arg("--output-root"));
const reportPath = path.resolve(arg("--report"));
if (fs.existsSync(outputRoot) || fs.existsSync(reportPath)) throw new Error("refusing to overwrite D12.9-D1 Node output");
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
if (shaFile(process.execPath) !== spec.runtime.node.sha256 || process.version !== spec.runtime.node.version) throw new Error("Node runtime identity mismatch");
const parentSpec = JSON.parse(fs.readFileSync(path.resolve(spec.sourceEvidence.spec.uri), "utf8"));
const fixtureById = new Map(parentSpec.fixtures.map((row) => [row.id, row]));
const outputRecords = {};
for (const fixtureId of spec.sourceEvidence.fixtures) {
  const fixture = fixtureById.get(fixtureId);
  const [width, height] = fixture.resolution;
  const adapterDir = path.join(sourceRoot, "adapters", fixtureId, "R1");
  const consumerDir = path.join(sourceRoot, "consumers", "python", fixtureId, "R1");
  const adapterReportPath = path.join(adapterDir, "report.json");
  const consumerReportPath = path.join(consumerDir, "report.json");
  const adapter = validateReport(adapterReportPath);
  const consumer = validateReport(consumerReportPath);
  const previousPayload = load(path.join(adapterDir, "arrays", "previous.rgba32"), adapter.arrays.previousRgba.sha256);
  const ownerPayload = load(path.join(adapterDir, "arrays", "previous-owner.f32"), adapter.arrays.previousOwner.sha256);
  const vectorPayload = load(path.join(adapterDir, "arrays", "vector.xy32"), adapter.arrays.vector.sha256);
  const radius2Payload = load(path.join(consumerDir, "arrays", "radius2-interior.u8"), consumer.arrays.radius2Interior.sha256);
  const previous = float32(previousPayload);
  const previousOwner = float32(ownerPayload);
  const vector = float32(vectorPayload);
  const radius2 = uint8(radius2Payload);
  const eligible = new Uint8Array(width * height);
  const accepted = new Uint8Array(width * height);
  const risk = new Uint32Array(width * height * 3);
  let radius2Count = 0;
  for (let y = 0; y < height; y += 1) for (let x = 0; x < width; x += 1) {
    const pixel = y * width + x;
    if (radius2[pixel] === 0) continue;
    radius2Count += 1;
    const qx = x + f32(vector, width, 2, y, x, 0);
    const qy = y - f32(vector, width, 2, y, x, 1);
    const x0 = Math.floor(qx), y0 = Math.floor(qy);
    if (x0 - 1 < 0 || x0 + 2 >= width || y0 - 1 < 0 || y0 + 2 >= height) continue;
    const owner = f32(previousOwner, width, 1, y0, x0);
    let supportOk = true;
    for (let sy = y0 - 1; sy <= y0 + 2; sy += 1) for (let sx = x0 - 1; sx <= x0 + 2; sx += 1) {
      if (f32(previousOwner, width, 1, sy, sx) !== owner || !(f32(previous, width, 4, sy, sx, 3) > Math.fround(0.999))) supportOk = false;
    }
    if (!supportOk) continue;
    const fx = exactScaled(qx - x0, Q24, "motion fraction x");
    const fy = exactScaled(qy - y0, Q24, "motion fraction y");
    eligible[pixel] = 1;
    for (let channel = 0; channel < 3; channel += 1) {
      const color = (yy, xx) => exactScaled(f32(previous, width, 4, yy, xx, channel), Q30, "Q30 RGB");
      let mx = 0n, my = 0n;
      for (const yy of [y0, y0 + 1]) for (const xx of [x0, x0 + 1]) {
        const value = color(yy, xx - 1) - 2n * color(yy, xx) + color(yy, xx + 1);
        const absolute = value < 0n ? -value : value;
        if (absolute > mx) mx = absolute;
      }
      for (const xx of [x0, x0 + 1]) for (const yy of [y0, y0 + 1]) {
        const value = color(yy - 1, xx) - 2n * color(yy, xx) + color(yy + 1, xx);
        const absolute = value < 0n ? -value : value;
        if (absolute > my) my = absolute;
      }
      const numerator = 2n * (fx * (Q24 - fx) * mx + fy * (Q24 - fy) * my);
      const units = ceilDiv(numerator, Q24 * Q24) + BigInt(spec.candidate.roundingAllowanceQ30);
      risk[pixel * 3 + channel] = Number(units > UINT32_MAX ? UINT32_MAX : units);
    }
    const maximum = Math.max(risk[pixel * 3], risk[pixel * 3 + 1], risk[pixel * 3 + 2]);
    accepted[pixel] = Number(maximum <= spec.candidate.riskThresholdQ30Inclusive);
  }
  const fixtureDir = path.join(outputRoot, fixtureId);
  fs.mkdirSync(fixtureDir, { recursive: true });
  const arrays = {};
  for (const [name, array, filename, dtype] of [
    ["eligible", eligible, "eligible.u8", "uint8"],
    ["accepted", accepted, "accepted.u8", "uint8"],
    ["riskQ30", risk, "risk.q30.u32", "little-endian-uint32"],
  ]) {
    const payload = Buffer.from(array.buffer, array.byteOffset, array.byteLength);
    const target = path.join(fixtureDir, filename);
    fs.writeFileSync(target, payload);
    arrays[name] = { uri: target, sha256: shaBytes(payload), bytes: payload.length, shape: name === "riskQ30" ? [height, width, 3] : [height, width], dtype };
  }
  outputRecords[fixtureId] = {
    adapterReport: { uri: adapterReportPath, sha256: shaFile(adapterReportPath), reportHash: adapter.reportHash },
    consumerReport: { uri: consumerReportPath, sha256: shaFile(consumerReportPath), reportHash: consumer.reportHash },
    arrays,
    counts: { radius2: radius2Count, eligible: eligible.reduce((a, b) => a + b, 0), accepted: accepted.reduce((a, b) => a + b, 0) },
  };
}
const body = {
  schemaVersion: "bfs.blenderMotionAwareCurvatureRiskProducerReport.v0.1",
  experimentId: spec.experimentId,
  producer: "node",
  pid: process.pid,
  candidate: spec.candidate,
  fixtures: outputRecords,
  operationCounts: { modelCalls: 0, networkCalls: 0 },
};
const report = { ...body, reportHash: canonicalHash(body) };
fs.mkdirSync(path.dirname(reportPath), { recursive: true });
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
process.stdout.write(`BFS_B52_D129_D1_NODE_OK fixtures=${Object.keys(outputRecords).length}\n`);
