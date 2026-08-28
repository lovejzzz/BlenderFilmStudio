#!/usr/bin/env node
/** Independent Node threshold consumer for B52-D12.13-D1. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { execFileSync } from "node:child_process";

const SPEC_SHA256 = "e9d79a2ec54acaf36a0df1168ea71102b0b94ab66f4e10f1cda56dbd1ea70c00";
const PARENT_SPEC_SHA256 = "b0defadbd120f77dfe81bfa16d9dfd4e3a4d4a15ad1c8ddd1176d21f2e13b648";
const PARENT_SUBTREE = "de1ac6a394a3963a158d0e3432d5dfb89aaf9a87";

function fail(message) { throw new Error(`D12.13-D1 ${message}`); }
function shaBytes(value) { return crypto.createHash("sha256").update(value).digest("hex"); }
function shaFile(uri) { return shaBytes(fs.readFileSync(uri)); }
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
function canonicalHash(value) { return shaBytes(Buffer.from(canonical(value))); }
function parseArguments(argv) {
  const result = {};
  for (let index = 2; index < argv.length; index += 2) {
    if (!argv[index].startsWith("--") || index + 1 >= argv.length) fail("invalid arguments");
    result[argv[index].slice(2)] = argv[index + 1];
  }
  for (const key of ["spec", "parent-root", "fixture", "repeat", "output"]) if (!(key in result)) fail(`missing --${key}`);
  result.repeat = Number(result.repeat);
  if (![1, 2].includes(result.repeat)) fail("repeat outside frozen roster");
  return result;
}
function readJson(uri) { return JSON.parse(fs.readFileSync(uri, "utf8")); }
function verifyRecord(record, label) {
  const payload = fs.readFileSync(record.uri);
  if (shaBytes(payload) !== record.sha256 || payload.length !== record.bytes) fail(`input binding failed: ${label}`);
  return payload;
}
function arrayRecord(uri, payload, dtype, shape) {
  fs.mkdirSync(path.dirname(uri), { recursive: true });
  fs.writeFileSync(uri, payload);
  return { uri, sha256: shaBytes(payload), bytes: payload.length, dtype, shape };
}
function withoutKeys(value, keys) {
  return Object.fromEntries(Object.entries(value).filter(([key]) => !keys.includes(key)));
}

const cli = parseArguments(process.argv);
if (fs.existsSync(cli.output)) fail("Node output must not pre-exist");
if (shaFile(cli.spec) !== SPEC_SHA256) fail("spec identity failed");
const spec = readJson(cli.spec);
if (!spec.inputContract.fixtures.includes(cli.fixture)) fail("fixture outside frozen roster");
const parentSpecUri = spec.parents.h1Spec.uri;
if (shaFile(parentSpecUri) !== PARENT_SPEC_SHA256) fail("H1 spec identity failed");
for (const key of ["h1Result", "h1Audit", "h1Receipt"]) {
  const row = spec.parents[key];
  if (shaFile(row.uri) !== row.sha256) fail("H1 evidence identity failed");
}
const subtree = execFileSync("git", ["rev-parse", `HEAD:${spec.parents.h1FormalRoot.uri}`], { encoding: "utf8" }).trim();
if (subtree !== PARENT_SUBTREE) fail("H1 formal subtree changed");

const h1Spec = readJson(parentSpecUri);
const fixture = h1Spec.fixtures.find((row) => row.id === cli.fixture);
if (!fixture) fail("fixture missing from H1 spec");
const [width, height] = fixture.resolution;
const pixels = width * height;
const repeatLabel = `R${cli.repeat}`;
const adapterUri = path.join(cli["parent-root"], "adapters", cli.fixture, repeatLabel, "report.json");
const h1Uri = path.join(cli["parent-root"], "consumers", "python", cli.fixture, repeatLabel, "report.json");
const adapter = readJson(adapterUri);
const h1 = readJson(h1Uri);
if (canonicalHash(withoutKeys(adapter, ["reportHash"])) !== adapter.reportHash) fail("adapter report self-hash failed");
if (canonicalHash(withoutKeys(h1, ["reportHash"])) !== h1.reportHash) fail("H1 report self-hash failed");

const adapterKeys = { currentRgba: "current.rgba32", currentOwner: "current-owner.f32" };
const controlKeys = {
  radius2Interior: "radius2-interior.u8", fullStencil: "full-stencil.u8",
  directionLeft: "direction-left.u8", directionRight: "direction-right.u8",
  directionTop: "direction-top.u8", directionBottom: "direction-bottom.u8",
  neitherHorizontal: "neither-horizontal.u8", analyticValidHistory: "analytic-valid-history.u8",
};
const decisionKeys = {
  oneSidedEligible: "one-sided-eligible.u8", riskQ30: "risk.q30.u32", reconstructed: "reconstructed.rgba32",
};
const payloads = {};
const inputBindings = {};
for (const [key, label] of Object.entries(adapterKeys)) {
  const record = adapter.arrays[key];
  payloads[label] = verifyRecord(record, label);
  inputBindings[label] = { uri: record.uri, sha256: record.sha256 };
}
for (const [section, mapping] of [["controlArrays", controlKeys], ["decisionArrays", decisionKeys]]) {
  for (const [key, label] of Object.entries(mapping)) {
    const record = h1[section][key];
    payloads[label] = verifyRecord(record, label);
    inputBindings[label] = { uri: record.uri, sha256: record.sha256 };
  }
}
const expectedLengths = {
  "current.rgba32": pixels * 16, "current-owner.f32": pixels * 4,
  "risk.q30.u32": pixels * 12, "reconstructed.rgba32": pixels * 16,
  "one-sided-eligible.u8": pixels,
};
for (const label of Object.values(controlKeys)) expectedLengths[label] = pixels;
for (const [label, expected] of Object.entries(expectedLengths)) if (payloads[label].length !== expected) fail(`array length failed: ${label}`);

fs.mkdirSync(cli.output, { recursive: true });
const sharedArrays = {
  eligible: arrayRecord(path.join(cli.output, "shared", "eligible.u8"), payloads["one-sided-eligible.u8"], "u1", [height, width]),
  riskQ30: arrayRecord(path.join(cli.output, "shared", "risk.q30.u32"), payloads["risk.q30.u32"], "<u4", [height, width, 3]),
};
const thresholdArrays = {};
for (const threshold of spec.thresholdFamily.candidateThresholdsQ30Descending) {
  const accepted = Buffer.alloc(pixels);
  const reconstructed = Buffer.from(payloads["current.rgba32"]);
  let acceptedCount = 0;
  for (let index = 0; index < pixels; index += 1) {
    let use = payloads["one-sided-eligible.u8"][index] !== 0;
    for (let channel = 0; channel < 3 && use; channel += 1) {
      use = payloads["risk.q30.u32"].readUInt32LE((index * 3 + channel) * 4) <= threshold;
    }
    if (use) {
      accepted[index] = 1;
      acceptedCount += 1;
      payloads["reconstructed.rgba32"].copy(reconstructed, index * 16, index * 16, index * 16 + 16);
    }
  }
  const base = path.join(cli.output, `threshold-${threshold}`);
  thresholdArrays[String(threshold)] = {
    accepted: arrayRecord(path.join(base, "accepted.u8"), accepted, "u1", [height, width]),
    reconstructed: arrayRecord(path.join(base, "reconstructed.rgba32"), reconstructed, "<f4", [height, width, 4]),
    acceptedCount,
  };
}
const report = {
  schemaVersion: "bfs.blenderMaterialOwnerQualityCouplingConsumerReport.v0.1",
  experimentId: spec.experimentId,
  specSha256: SPEC_SHA256,
  producer: "node",
  fixtureId: cli.fixture,
  repeat: cli.repeat,
  resolution: [width, height],
  thresholdsQ30Descending: spec.thresholdFamily.candidateThresholdsQ30Descending,
  parentReports: {
    adapter: { uri: adapterUri, sha256: shaFile(adapterUri), normalizedHash: canonicalHash(withoutKeys(adapter, ["pid", "reportHash", "runtime"])) },
    h1Consumer: { uri: h1Uri, sha256: shaFile(h1Uri), normalizedHash: canonicalHash(withoutKeys(h1, ["pid", "reportHash", "runtime"])) },
  },
  inputBindings,
  sharedArrays,
  thresholdArrays,
  operationCounts: {
    consumerProcesses: 1, pixelsVisited: pixels, thresholdsEvaluated: Object.keys(thresholdArrays).length,
    blenderRenderCalls: 0, modelCalls: 0, networkCalls: 0,
  },
  runtime: { node: process.version, nodeExecutableSha256: shaFile(process.execPath) },
  pid: process.pid,
};
report.reportHash = canonicalHash(report);
fs.writeFileSync(path.join(cli.output, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
