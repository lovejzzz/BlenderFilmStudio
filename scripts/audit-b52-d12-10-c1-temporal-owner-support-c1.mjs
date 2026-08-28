#!/usr/bin/env node
/** Corrected independent Node audit for the B52-D12.10-C1 result. */
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { basename, join, relative, resolve } from "node:path";
import process from "node:process";

const EXPECTED_SPEC_SHA = "2ba1edd74fef18eacfa1c170cab4e35f80afc575eaef1ffe3500428553555403";
const EXPECTED_D1_SHA = "9cb5a01d7dbeba357e8a371be0f5b75e5837291ef6d6cc829b74eb425a7e08d4";
const EXPECTED_RESULT_SHA = "90e8a4d72c0224e4195cd6a52ea193d93211d6dfe368ed7efdd1c3d421d393c8";

function parseArgs(argv) {
  const values = {};
  for (let index = 2; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith("--") || argv[index + 1] === undefined) throw new Error("invalid D12.10-C1 audit arguments");
    values[argv[index].slice(2)] = argv[index + 1];
  }
  for (const name of ["spec", "d1-result", "result", "d1-payload-root", "payload-root", "output"]) {
    if (!values[name]) throw new Error(`missing --${name}`);
  }
  return values;
}

function shaBytes(value) {
  return createHash("sha256").update(value).digest("hex");
}

function shaFile(path) {
  return shaBytes(readFileSync(path));
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function canon(value) {
  return shaBytes(Buffer.from(JSON.stringify(stable(value))));
}

function selfOk(value, field) {
  const copy = structuredClone(value);
  delete copy[field];
  return value[field] === canon(copy);
}

function walk(root, current = root) {
  const output = [];
  for (const name of readdirSync(current).sort()) {
    const path = join(current, name);
    if (statSync(path).isDirectory()) output.push(...walk(root, path));
    else output.push(relative(root, path));
  }
  return output;
}

function core(row) {
  const ownerFields = ["radius2", "trueOwnerBilinear", "trueOwnerFullStencil", "accepted", "acceptedOutsideTrueOwnerBilinear"];
  return {
    cell: row.cell,
    fixtureId: row.fixtureId,
    repeat: row.repeat,
    currentOraclePayloadIdentity: row.currentOraclePayloadIdentity,
    classificationPartition: row.classificationPartition,
    radius2: row.radius2,
    classes: row.classes,
    objectIndexBilinearAlias: row.objectIndexBilinearAlias,
    objectIndexCurvatureAlias: row.objectIndexCurvatureAlias,
    oneSidedStencilOpportunity: row.oneSidedStencilOpportunity,
    riskAfterTrueOwnerFullStencil: row.riskAfterTrueOwnerFullStencil,
    accepted: row.accepted,
    acceptedOutsideTrueOwnerBilinear: row.acceptedOutsideTrueOwnerBilinear,
    owners: Object.fromEntries(Object.entries(row.owners).sort().map(([id, owner]) => [id, Object.fromEntries(ownerFields.map((field) => [field, owner[field]]))])),
  };
}

function closeRatio(value, numerator, denominator) {
  if (denominator === 0) return value === null;
  return typeof value === "number" && Number.isFinite(value) && Math.abs(value - numerator / denominator) <= 1e-15;
}

function rowOk(row) {
  for (const item of [row, ...Object.values(row.owners)]) {
    if (item.accepted !== item.acceptedWithinTrueOwnerBilinear + item.acceptedOutsideTrueOwnerBilinear) return false;
    if (item.acceptedWithinTrueOwnerBilinear !== item.acceptedWithinTrueOwnerFullStencil + item.acceptedWithinTrueOwnerExtraStencilMismatch) return false;
    if (!(0 <= item.acceptedWithinTrueOwnerFullStencil && item.acceptedWithinTrueOwnerFullStencil <= item.trueOwnerFullStencil && item.trueOwnerFullStencil <= item.trueOwnerBilinear && item.trueOwnerBilinear <= item.radius2)) return false;
    if (!closeRatio(item.acceptedToRadius2, item.accepted, item.radius2)) return false;
    if (!closeRatio(item.acceptedToTrueOwnerBilinear, item.acceptedWithinTrueOwnerBilinear, item.trueOwnerBilinear)) return false;
    if (!closeRatio(item.acceptedToTrueOwnerFullStencil, item.acceptedWithinTrueOwnerFullStencil, item.trueOwnerFullStencil)) return false;
    for (const ratio of [item.acceptedToRadius2, item.acceptedToTrueOwnerBilinear, item.acceptedToTrueOwnerFullStencil]) {
      if (ratio !== null && (!(typeof ratio === "number") || !Number.isFinite(ratio) || ratio < 0 || ratio > 1)) return false;
    }
  }
  return true;
}

function resultOk(candidate, d1, spec) {
  const d1Rows = new Map(d1.cells.map((row) => [row.cell, core(row)]));
  if (candidate.cells.length !== d1Rows.size || JSON.stringify(stable(candidate.payloadHashes)) !== JSON.stringify(stable(d1.payloadHashes))) return false;
  for (const row of candidate.cells) {
    if (!d1Rows.has(row.cell) || JSON.stringify(stable(core(row))) !== JSON.stringify(stable(d1Rows.get(row.cell))) || !rowOk(row)) return false;
  }
  const checks = candidate.checks ?? [];
  const attacks = candidate.mutationAttacks ?? [];
  if (!candidate.passed || candidate.verdict !== spec.decision.localizedVerdict || checks.length !== candidate.checkTotal || checks.filter((row) => row.passed).length !== candidate.checkPassed || candidate.checkPassed !== candidate.checkTotal) return false;
  if (attacks.length < spec.attacks.minimumRegisteredAttacks || new Set(attacks.map((row) => row.id)).size !== attacks.length || attacks.some((row) => row.passed !== true) || candidate.mutationAttackPassed !== attacks.length || candidate.mutationAttackTotal !== attacks.length) return false;
  if (candidate.operationCounts.blenderRenderCalls !== 0 || candidate.operationCounts.modelCalls !== 0 || candidate.operationCounts.networkCalls !== 0) return false;
  const sameIndex = candidate.cells.find((row) => row.cell === "SAME_INDEX_DEPTH_CROSSING_179X113/R1");
  return sameIndex?.acceptedOutsideTrueOwnerBilinear === 15;
}

const args = parseArgs(process.argv);
const paths = Object.fromEntries(Object.entries(args).map(([name, value]) => [name, resolve(value)]));
if (basename(paths.output) !== "audit-c1.json" || statSync(paths.output, { throwIfNoEntry: false })) throw new Error("D12.10-C1 corrected audit output freshness mismatch");
const spec = JSON.parse(readFileSync(paths.spec, "utf8"));
const d1 = JSON.parse(readFileSync(paths["d1-result"], "utf8"));
const result = JSON.parse(readFileSync(paths.result, "utf8"));
const payloadFiles = walk(paths["payload-root"]);
const d1PayloadFiles = walk(paths["d1-payload-root"]);
const actualPayloadIdentity = JSON.stringify(payloadFiles) === JSON.stringify(d1PayloadFiles) && payloadFiles.every((name) => shaFile(join(paths["payload-root"], name)) === shaFile(join(paths["d1-payload-root"], name)));
const declaredPayloadChecks = [];
for (const [fixtureId, repeats] of Object.entries(result.payloadHashes)) {
  for (const [repeat, hashes] of Object.entries(repeats)) {
    const names = { previousToken: "previous-token.u8", currentToken: "current-token.u8", classification: "classification.u8", trueOwnerBilinear: "true-owner-bilinear.u8", trueOwnerFullStencil: "true-owner-full-stencil.u8" };
    for (const [key, filename] of Object.entries(names)) declaredPayloadChecks.push(shaFile(join(paths["payload-root"], fixtureId, `R${repeat}`, filename)) === hashes[key]);
  }
}
const independentAttacks = [];
const attackMutations = [
  ["accepted intersection", (value) => { value.cells[4].acceptedWithinTrueOwnerBilinear += 1; }],
  ["full intersection", (value) => { value.cells[4].acceptedWithinTrueOwnerFullStencil += 1; }],
  ["outside alias", (value) => { value.cells[4].acceptedOutsideTrueOwnerBilinear = 0; }],
  ["ratio above one", (value) => { value.cells[4].acceptedToTrueOwnerFullStencil = 1.1; }],
  ["ratio below zero", (value) => { value.cells[4].acceptedToTrueOwnerBilinear = -0.1; }],
  ["D1 class identity", (value) => { value.cells[4].classes.TRUE_OWNER_BILINEAR_MISMATCH.pixels = 0; }],
  ["payload identity", (value) => { value.payloadHashes[Object.keys(value.payloadHashes)[0]]["1"].classification = "0".repeat(64); }],
  ["verdict", (value) => { value.verdict = spec.decision.notLocalizedVerdict; }],
  ["formal attack roster", (value) => { value.mutationAttacks = []; value.mutationAttackTotal = 0; value.mutationAttackPassed = 0; }],
  ["operation count", (value) => { value.operationCounts.networkCalls = 1; }],
  ["owner decomposition", (value) => { Object.values(value.cells[4].owners)[0].acceptedWithinTrueOwnerBilinear += 1; }],
];
for (const [target, mutate] of attackMutations) {
  const candidate = structuredClone(result);
  mutate(candidate);
  const unhashed = structuredClone(candidate);
  delete unhashed.analysisHash;
  candidate.analysisHash = canon(unhashed);
  independentAttacks.push({ target, passed: !resultOk(candidate, d1, spec) });
}
const checks = [
  ["SPEC_AND_D1_HASH", shaFile(paths.spec) === EXPECTED_SPEC_SHA && shaFile(paths["d1-result"]) === EXPECTED_D1_SHA],
  ["RESULT_FILE_SHA_BINDING", shaFile(paths.result) === EXPECTED_RESULT_SHA],
  ["ACTUAL_PAYLOAD_BYTE_IDENTITY", actualPayloadIdentity],
  ["DECLARED_PAYLOAD_HASHES", declaredPayloadChecks.length === 40 && declaredPayloadChecks.every(Boolean)],
  ["D1_CLASSIFICATION_IDENTITY", result.cells.every((row) => JSON.stringify(stable(core(row))) === JSON.stringify(stable(d1.cells.find((old) => old.cell === row.cell) && core(d1.cells.find((old) => old.cell === row.cell)))))],
  ["SET_AND_RATIO_REPLAY", result.cells.every(rowOk)],
  ["RESULT_DECISION_AND_TOTALITY", resultOk(result, d1, spec)],
  ["FORMAL_ATTACK_TARGETS", spec.attacks.requiredNewTargets.every((target) => result.mutationAttacks.some((row) => row.target === target) || (target === "emit a ratio below zero or above one" && result.mutationAttacks.some((row) => row.target === "emit ratio below zero") && result.mutationAttacks.some((row) => row.target === "emit ratio above one")))],
  ["INDEPENDENT_ATTACKS", independentAttacks.every((row) => row.passed)],
  ["MODEL_NETWORK_RENDER_ZERO", result.operationCounts.blenderRenderCalls === 0 && result.operationCounts.modelCalls === 0 && result.operationCounts.networkCalls === 0],
];
const body = {
  schemaVersion: "bfs.blenderTemporalOwnerSupportLocalizationCorrectionAudit.v0.1-c1",
  experimentId: spec.experimentId,
  auditPid: process.pid,
  passed: checks.every(([, passed]) => passed),
  checks: checks.map(([id, passed]) => ({ id, passed })),
  checkPassed: checks.filter(([, passed]) => passed).length,
  checkTotal: checks.length,
  resultAnalysisHash: result.analysisHash,
  resultSha256: shaFile(paths.result),
  d1ResultSha256: shaFile(paths["d1-result"]),
  payloadFileCount: payloadFiles.length,
  declaredPayloadChecks: declaredPayloadChecks.length,
  independentAttacks,
  independentAttackPassed: independentAttacks.filter((row) => row.passed).length,
  independentAttackTotal: independentAttacks.length,
  operationCounts: { auditProcesses: 1, blenderRenderCalls: 0, modelCalls: 0, networkCalls: 0 },
};
const audit = { ...body, auditHash: canon(body) };
writeFileSync(paths.output, `${JSON.stringify(stable(audit), null, 2)}\n`);
console.log(`BFS_B52_D1210_C1_AUDIT passed=${audit.passed} checks=${audit.checkPassed}/${audit.checkTotal} attacks=${audit.independentAttackPassed}/${audit.independentAttackTotal} hash=${audit.auditHash}`);
process.exit(audit.passed ? 0 : 1);

