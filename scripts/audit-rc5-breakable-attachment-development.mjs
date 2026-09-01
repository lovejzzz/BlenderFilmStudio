#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const research = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const evidence = path.join(research, "experiments/physical-richness/RC5-2026-09-01-development-attempt-13");
const work = "/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC5-2026-09-01-development-attempt-13";
const product = "/Users/mengyingli/Documents/ChatGPT/BlenderFilmStudio-PostPB7-workspace/RC1-development/source";
const modulePath = path.join(product, "scripts/modules/film_studio_physics_action.py");
const expectedCandidate = "8e18c82548f8716c415e6e1b69fdbbdeef1f1900";

function sha256File(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function objectHash(value, field) {
  const body = { ...value };
  delete body[field];
  return crypto.createHash("sha256").update(canonical(body)).digest("hex");
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function walkFiles(root) {
  const rows = [];
  function visit(current) {
    for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) visit(absolute);
      else if (entry.isFile()) rows.push(absolute);
    }
  }
  visit(root);
  return rows;
}

function manifest(root, excludedNames = new Set()) {
  return walkFiles(root).filter((file) => !excludedNames.has(path.basename(file))).map((file) => ({
    path: path.relative(root, file),
    bytes: fs.statSync(file).size,
    sha256: sha256File(file),
  }));
}

function pngDimensions(file) {
  const bytes = fs.readFileSync(file);
  if (bytes.length < 24 || bytes.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") return null;
  return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
}

function writeJson(file, value) {
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

const receipt = readJson(path.join(evidence, "receipt.json"));
const build = readJson(path.join(evidence, "B1-build.json"));
const reopen = readJson(path.join(evidence, "B1-reopen.json"));
const regression = readJson(path.join(evidence, "regression-negative.json"));
const render = readJson(path.join(evidence, "render.json"));
const review = readJson(path.join(evidence, "direct-visual-review.json"));
const result = build.result;
const physics = result.physics;
const attachment = physics.breakableAttachment;
const contactReadability = result.cinematography.contact.secondaryReadability;
const effectReadability = result.cinematography.effect.secondaryReadability;
const frameFiles = render.clip.frames.map((row) => row.path);
const stillFiles = render.stills.map((row) => row.path);
const imageFiles = [...stillFiles, ...frameFiles];
const retainedFailures = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12].map((number) =>
  path.join(research, `experiments/physical-richness/RC5-2026-09-01-development-attempt-${String(number).padStart(2, "0")}/failure.json`)
);
const attempt11Review = readJson(path.join(research, "experiments/physical-richness/RC5-2026-09-01-development-attempt-11/direct-visual-review.json"));
const productHead = execFileSync("git", ["rev-parse", "HEAD"], { cwd: product, encoding: "utf8" }).trim();
const productStatus = execFileSync("git", ["status", "--short"], { cwd: product, encoding: "utf8" }).trim();

const checks = {
  exactRoots: fs.realpathSync(evidence) === evidence && fs.realpathSync(work) === work,
  retainedFailures: retainedFailures.every((file) => fs.existsSync(file)) && attempt11Review.status === "FAIL" && attempt11Review.yesCount === 5,
  receiptSelfHash: receipt.receiptHash === objectHash(receipt, "receiptHash"),
  directReviewSelfHash: review.reviewHash === objectHash(review, "reviewHash"),
  evidenceBinding: receipt.evidence.buildSha256 === sha256File(path.join(evidence, "B1-build.json")) && receipt.evidence.reopenSha256 === sha256File(path.join(evidence, "B1-reopen.json")) && receipt.evidence.regressionNegativeSha256 === sha256File(path.join(evidence, "regression-negative.json")) && receipt.evidence.renderSha256 === sha256File(path.join(evidence, "render.json")) && receipt.evidence.directVisualReviewSha256 === sha256File(path.join(evidence, "direct-visual-review.json")),
  productCandidateBinding: productHead === expectedCandidate && productStatus === "" && receipt.productCandidateCommit === expectedCandidate && sha256File(modulePath) === receipt.candidate.sha256,
  runnerAndFixtureBinding: sha256File(path.join(research, receipt.runner.path)) === receipt.runner.sha256 && sha256File(path.join(research, receipt.fixture.uri)) === receipt.fixture.fileSha256,
  buildTwentyOfTwenty: build.status === "PASS" && build.checkCount === 20 && build.passCount === 20 && Object.values(build.checks).every(Boolean),
  exactResultHash: result.resultHash === "6bc858c6a853f1b306575762728e8c1afc404b40db85dbbe8ae0e119440ac74c" && render.resultHash === result.resultHash,
  frozenProjection: crypto.createHash("sha256").update(canonical(result.physics)).digest("hex") === "97b0fefaa1f7046eb3ec79ae849c965f3552b18cc8412bd7a027e0bf652c872e" && crypto.createHash("sha256").update(canonical(result.authority)).digest("hex") === "799f6997c5bcb61ec42f2c8a06dd1e58d946095efa0efae7f32a8061de11de16" && crypto.createHash("sha256").update(canonical(result.mechanism)).digest("hex") === "e46fe996baa4ea181426fbe70345f2a3ebbf44c855c917b8381ca38e548b5be0" && crypto.createHash("sha256").update(canonical(result.physicalArchetypes)).digest("hex") === "3c610d0b6e66a3d8fb1b345bd4de7348cb06e879f1e931b2c2c4785a9f0339ff",
  bulletBreakableAttachment: attachment.source === "BLENDER_BULLET_BREAKABLE_FIXED_CONSTRAINT" && attachment.constraintType === "FIXED" && attachment.breakingEnabled === true && attachment.detachmentFrame === 24 && attachment.maximumAttachmentSeparationMeters === 0.12205441,
  derivedUniqueTarget: attachment.attachmentTarget === "CAUSAL_TARGET_002" && attachment.attachmentTargetDerivation.source === "METRIC_INITIAL_CONDITIONS_BEFORE_SCENE_MUTATION" && attachment.attachmentTargetDerivation.uniquenessMarginMeters > 0.14,
  solverAuthority: Object.entries(result.authority).filter(([key]) => /authored|keyframes|networkCalls|lightAnimationChannels|arbitraryExecutableAuthority/.test(key)).every(([, value]) => value === 0),
  physicalResponse: physics.contactFrame === 16 && physics.respondingTargetCount === 3 && physics.settledWindowStartFrame === 132 && physics.settledGroupFrame === 141 && attachment.maximumFloorPenetrationMeters < 0.005,
  moldedContactGeometry: result.mechanism.contactGeometry.preset === "MOLDED_HOUSEHOLD_GLASS_WITH_CONTACT_OVALITY" && result.mechanism.contactGeometry.radialAmplitudeMeters === 0.00045 && result.mechanism.contactGeometry.visibleMeshIsCollisionHullSource === true && result.mechanism.contactGeometry.solverSleep === false,
  derivedSecondaryCamera: contactReadability.source === "BOUNDED_PROJECTED_SECONDARY_READABILITY" && effectReadability.source === "BOUNDED_PROJECTED_SECONDARY_READABILITY" && contactReadability.candidateCameraObjectCount === 1 && contactReadability.candidateCameraObjectDeletions === 0 && effectReadability.candidateCameraObjectCount === 1 && effectReadability.candidateCameraObjectDeletions === 0 && contactReadability.azimuthDegrees === 135 && effectReadability.azimuthDegrees === 135,
  reopenSevenOfSeven: reopen.status === "PASS" && Object.keys(reopen.checks).length === 7 && Object.values(reopen.checks).every(Boolean) && reopen.maximumActorLocationDeltaMeters < 1e-8 && reopen.maximumCapLocationDeltaMeters < 1e-8 && reopen.maximumCapAngularDeltaDegrees < 1e-8 && reopen.maximumTargetTiltDeltaDegrees < 1e-8,
  regressionsExact: regression.status === "PASS" && regression.regressions.map((row) => row.resultHash).join(",") === "016ccd803ef9aecc0bce6e0dd91d98472b7a6b6304e1c083e236058e39dc5925,05c72eeff8279ac812d9e2b2ea4565bd2cc2d8f7cd2844e6ffdade06556c8409,064150af89de723f09802750b3b9282465d5acca4539ef9fd6221c91603f8c98" && regression.regressions.every((row) => row.status === "PASS"),
  negativeControls: regression.negativeControls.length === 12 && regression.negativeControls.every((row) => row.passed === true),
  renderRoster: render.status === "PASS_RENDER_COMPLETE" && render.stills.length === 3 && render.clip.frameCount === 48 && render.clip.frames.length === 48 && render.counts.blendSaves === 0 && render.counts.sceneMutations === 0,
  renderedFileHashes: render.stills.every((row) => sha256File(row.path) === row.sha256) && render.clip.frames.every((row) => sha256File(row.path) === row.sha256),
  imageDimensions: imageFiles.every((file) => JSON.stringify(pngDimensions(file)) === "[1280,720]"),
  visualReviewTenOfTen: review.status === "PASS" && review.yesCount === 10 && review.noCount === 0 && review.visualArtifacts.framesInspected === 48 && review.questions.every((row) => row.verdict === "YES"),
  reviewArtifactHashes: sha256File(path.join(evidence, "contact-clip.mp4")) === review.visualArtifacts.contactClipSha256 && [1, 2, 3, 4].every((number, index) => sha256File(path.join(evidence, `contact-sheet-${number}.png`)) === review.visualArtifacts.contactSheetSha256[index]),
  singleBlendAndNoWorkMedia: walkFiles(work).filter((file) => file.endsWith(".blend")).length === 1 && sha256File(path.join(work, "RC5_B1_BREAKABLE_ATTACHMENT.blend")) === receipt.evidence.blendSha256 && walkFiles(work).every((file) => !/\.(png|jpe?g|exr|mov|mp4)$/i.test(file)),
  boundedCountsAndNoNetwork: receipt.counts.productStarts === 4 && receipt.counts.renderCalls === 51 && receipt.counts.networkCalls === 0 && receipt.counts.engineRemoteWrites === 0 && build.counts.networkCalls === 0 && reopen.counts.networkCalls === 0 && regression.counts.networkCalls === 0 && render.counts.networkCalls === 0,
  resourceCeilings: receipt.resources.workRootWithin8589934592 && receipt.resources.evidenceRootWithin1073741824 && receipt.resources.freeReserveAbove107374182400,
};

const evidenceManifestPath = path.join(evidence, "evidence-manifest.json");
const workManifestPath = path.join(evidence, "work-manifest.json");
writeJson(evidenceManifestPath, manifest(evidence, new Set(["audit.json", "evidence-manifest.json", "work-manifest.json"])));
writeJson(workManifestPath, manifest(work));

const output = {
  schemaVersion: "bfs.rc5BreakableAttachmentDevelopmentAudit.v0.1",
  status: Object.values(checks).every(Boolean) ? "PASS" : "FAIL",
  checks,
  checkCount: Object.keys(checks).length,
  passCount: Object.values(checks).filter(Boolean).length,
  candidateCommit: expectedCandidate,
  resultHash: result.resultHash,
  receiptHash: receipt.receiptHash,
  directVisualReviewHash: review.reviewHash,
  evidenceManifestSha256: sha256File(evidenceManifestPath),
  workManifestSha256: sha256File(workManifestPath),
  auditorSha256: sha256File(fileURLToPath(import.meta.url)),
};
output.auditHash = objectHash(output, "auditHash");
writeJson(path.join(evidence, "audit.json"), output);
process.stdout.write(`${canonical(output)}\n`);
if (output.status !== "PASS") process.exitCode = 1;
