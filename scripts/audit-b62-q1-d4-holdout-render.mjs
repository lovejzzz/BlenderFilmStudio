#!/usr/bin/env node
import { createHash } from "node:crypto";
import { open, readFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url))),
  SPEC_URI = "specs/b62-camera-quality-holdout-render-validation.v0.1.json",
  PROTOCOL_URI =
    "research/2026-08-29-b62-d4-holdout-render-validation-protocol.md",
  CORRECTION_URI =
    "specs/b62-camera-quality-d4-c1-layered-action-api.v0.1.json",
  CORRECTION_PROTOCOL_URI =
    "research/2026-08-29-b62-d4-c1-layered-action-api-correction.md",
  CORRECTION2_URI =
    "specs/b62-camera-quality-d4-c2-cross-runtime-float-canonicalization.v0.1.json",
  CORRECTION2_PROTOCOL_URI =
    "research/2026-08-29-b62-d4-c2-cross-runtime-float-canonicalization.md",
  ROOT_URI = "experiments/b62-camera-quality-holdout-render-v0-3";
const TOOLS = [
  "blender/build_b62_q1_d4_corrected_scene.py",
  "blender/render_b62_q1_d4_holdout_pairs.py",
  "blender/audit_b62_q1_d4_scene_and_pixels.py",
  "scripts/run-b62-q1-d4-holdout-render.mjs",
  "scripts/audit-b62-q1-d4-holdout-render.mjs",
];
function canonicalize(v) {
  if (typeof v === "number" && !Number.isInteger(v)) {
    const b = new ArrayBuffer(8),
      d = new DataView(b);
    d.setFloat64(0, v, false);
    return {
      $f64be: [...new Uint8Array(b)]
        .map((x) => x.toString(16).padStart(2, "0"))
        .join(""),
    };
  }
  if (Array.isArray(v)) return v.map(canonicalize);
  if (v && typeof v === "object")
    return Object.fromEntries(
      Object.entries(v)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([k, x]) => [k, canonicalize(x)]),
    );
  return v;
}
const canonical = (v) => JSON.stringify(canonicalize(v)),
  hashBytes = (v) => createHash("sha256").update(v).digest("hex"),
  hashFile = async (p) => hashBytes(await readFile(p));
function req(x, m) {
  if (!x) throw new Error(m);
}
function pathFor(uri) {
  req(
    uri && !uri.startsWith("/") && !uri.split("/").includes(".."),
    `unsafe ${uri}`,
  );
  const p = resolve(repositoryRoot, uri);
  req(!relative(repositoryRoot, p).startsWith("../"), `escaped ${uri}`);
  return p;
}
async function json(uri) {
  return JSON.parse(await readFile(pathFor(uri), "utf8"));
}
function validSelf(v, f) {
  if (!v || !/^[0-9a-f]{64}$/.test(v[f] ?? "")) return false;
  const c = structuredClone(v),
    e = c[f];
  delete c[f];
  return hashBytes(canonical(c)) === e;
}
async function writeHashed(p, v, f) {
  const b = structuredClone(v);
  b[f] = hashBytes(canonical(b));
  const h = await open(p, "wx", 0o600);
  try {
    await h.writeFile(`${JSON.stringify(b, null, 2)}\n`);
    await h.sync();
  } finally {
    await h.close();
  }
  return b;
}
function parse(a) {
  req(
    a.length === 4 &&
      a[0] === "--root" &&
      a[1] === ROOT_URI &&
      a[2] === "--tool-freeze-commit" &&
      /^[0-9a-f]{40}$/.test(a[3]),
    "args",
  );
  return a[3];
}
function processPass(p, id, maxWall, spec) {
  return (
    validSelf(p, "processHash") &&
    p.processId === id &&
    p.result?.outcome === "PASS" &&
    p.result?.breach === null &&
    p.result?.child?.exitCode === 0 &&
    p.result?.metrics?.elapsedMs <= maxWall * 1000 &&
    p.result?.metrics?.peakSampledRssBytes <=
      spec.processBudget.maximumPeakResidentSetSizeBytesPerBlender &&
    p.result?.metrics?.logBytes <=
      spec.processBudget.maximumCombinedLogBytesPerChild
  );
}
export async function audit(argv) {
  const freeze = parse(argv),
    root = pathFor(ROOT_URI),
    spec = await json(SPEC_URI),
    correction = await json(CORRECTION_URI),
    correction2 = await json(CORRECTION2_URI),
    admission = await json(`${ROOT_URI}/admission.json`),
    build = await json(`${ROOT_URI}/build.json`),
    render = await json(`${ROOT_URI}/render.json`),
    independent = await json(`${ROOT_URI}/independent.json`),
    buildProcess = await json(`${ROOT_URI}/processes/BUILD.json`),
    renderProcess = await json(`${ROOT_URI}/processes/RENDER.json`),
    independentProcess = await json(`${ROOT_URI}/processes/INDEPENDENT.json`);
  req(
    spec.experimentId === "B62-Q1-D4" &&
      spec.statusBeforeToolCreation === "PREREGISTERED",
    "spec",
  );
  req(
    correction.correctionId === "B62-Q1-D4-C1" &&
      correction.authorizedChanges.retryRoot ===
        "experiments/b62-camera-quality-holdout-render-v0-2",
    "C1 correction",
  );
  req(
    correction2.correctionId === "B62-Q1-D4-C2" &&
      correction2.authorizedChanges.retryRoot === ROOT_URI,
    "C2 correction",
  );
  req(
    validSelf(admission, "admissionHash") &&
      admission.status === "ADMITTED" &&
      admission.toolFreezeCommit === freeze,
    "admission",
  );
  req(
    admission.bindings.spec.sha256 === (await hashFile(pathFor(SPEC_URI))) &&
      admission.bindings.protocol.sha256 ===
        (await hashFile(pathFor(PROTOCOL_URI))) &&
      admission.bindings.correction.sha256 ===
        (await hashFile(pathFor(CORRECTION_URI))) &&
      admission.bindings.correctionProtocol.sha256 ===
        (await hashFile(pathFor(CORRECTION_PROTOCOL_URI))) &&
      admission.bindings.correction2.sha256 ===
        (await hashFile(pathFor(CORRECTION2_URI))) &&
      admission.bindings.correction2Protocol.sha256 ===
        (await hashFile(pathFor(CORRECTION2_PROTOCOL_URI))),
    "spec binding",
  );
  req(
    canonical(admission.bindings.retainedFailureTree) ===
      canonical(correction.retainedFailure.tree),
    "retained binding",
  );
  req(
    canonical(admission.bindings.retainedFailureTreeC2) ===
      canonical(correction2.retainedFailure.tree),
    "retained C2 binding",
  );
  for (const uri of TOOLS)
    req(
      admission.bindings.tools[uri] === (await hashFile(pathFor(uri))),
      `tool ${uri}`,
    );
  req(
    validSelf(build, "reportHash") &&
      validSelf(render, "reportHash") &&
      validSelf(independent, "reportHash"),
    "report hashes",
  );
  req(
    processPass(
      buildProcess,
      "BUILD",
      spec.processBudget.maximumWallSecondsBuild,
      spec,
    ) &&
      processPass(
        renderProcess,
        "RENDER",
        spec.processBudget.maximumWallSecondsRender,
        spec,
      ) &&
      processPass(
        independentProcess,
        "INDEPENDENT",
        spec.processBudget.maximumWallSecondsIndependentAudit,
        spec,
      ),
    "processes",
  );
  const derived = resolve(root, spec.output.derivedScene);
  req(
    (await hashFile(derived)) === build.derived.sha256 &&
      independent.derivedScene.sha256 === build.derived.sha256,
    "derived identity",
  );
  const expectedCells = spec.holdout.frames.flatMap((frame) =>
      spec.holdout.pairedConditions.map((condition) => `${frame}|${condition}`),
    ),
    renderCells = render.renders.map((row) => `${row.frame}|${row.condition}`),
    geometryCells = independent.geometry.map(
      (row) => `${row.frame}|${row.condition}`,
    );
  const renderRoster = canonical(renderCells) === canonical(expectedCells),
    geometryRoster = canonical(geometryCells) === canonical(expectedCells);
  let outputHashes = true,
    pixelsValid = true;
  for (const row of render.renders) {
    const exr = resolve(root, row.exr.uri),
      png = resolve(root, row.png.uri);
    outputHashes =
      outputHashes &&
      (await hashFile(exr)) === row.exr.sha256 &&
      (await hashFile(png)) === row.png.sha256;
    pixelsValid =
      pixelsValid &&
      row.combined.width === 960 &&
      row.combined.height === 540 &&
      row.combined.nonFiniteCount === 0 &&
      row.combined.rgbDynamicRange > 1e-6;
  }
  const independentPixels = independent.pixels.every(
    (row) =>
      row.combined.width === 960 &&
      row.combined.height === 540 &&
      row.combined.nonFiniteCount === 0 &&
      row.combined.rgbDynamicRange > 1e-6,
  );
  const pairDifferent =
    render.pairs.length === 6 && render.pairs.every((row) => row.different);
  const correctedAllPass = independent.outcome.correctedAllPass === true,
    originalAllFail = independent.outcome.originalAllFail === true;
  const supported = correctedAllPass && originalAllFail && pairDifferent;
  const scientificVerdict = supported
    ? spec.decision.supportedVerdict
    : spec.decision.rejectedVerdict;
  const checks = [
    ["SPEC_C1_C2_ADMISSION_PARENT_BOUND", true],
    ["TOOL_FREEZE_HASHES_EXACT", true],
    ["C1_FROZEN_RENDER_AND_AUDIT_TOOLS_EXACT", true],
    ["THREE_FRESH_BLENDER_PROCESSES_PASS", true],
    [
      "BLENDER_IDENTITY_EXACT",
      [build, render, independent].every(
        (row) =>
          `Blender ${row.blender.version}` === spec.runtime.blender.version &&
          row.blender.buildHash === spec.runtime.blender.buildHash,
      ),
    ],
    ["DERIVED_SCENE_IDENTITY_EXACT", true],
    [
      "CAMERA_BAKE_96_FRAMES_EXACT",
      build.bake.length === 96 &&
        independent.bake.length === 96 &&
        Math.max(...independent.bake.map((row) => row.maxLocationError)) <=
          1e-6,
    ],
    ["HOLDOUT_RENDER_ROSTER_12_EXACT", renderRoster],
    ["HOLDOUT_GEOMETRY_ROSTER_12_EXACT", geometryRoster],
    [
      "CYCLES_SETTINGS_EXACT",
      render.settings.engine === "CYCLES" &&
        render.settings.device === "CPU" &&
        canonical(render.settings.resolution) === "[960,540]" &&
        render.settings.samples === 16 &&
        render.settings.seed === 62004,
    ],
    ["OUTPUT_FILE_HASHES_EXACT", outputHashes],
    ["RENDER_PIXELS_VALID", pixelsValid],
    [
      "INDEPENDENT_PIXEL_DECODE_AGREES",
      independentPixels &&
        independent.pixels.every((row) => {
          const source = render.renders.find(
            (x) => x.frame === row.frame && x.condition === row.condition,
          );
          return (
            source &&
            source.combined.sha256 === row.combined.sha256 &&
            source.exr.sha256 === row.exrSha256
          );
        }),
    ],
    ["PAIR_PIXEL_DIGESTS_DIFFER", pairDifferent],
    [
      "ZERO_MODEL_NETWORK_DOCKER",
      [build, render, independent].every(
        (row) =>
          row.operations.modelCalls === 0 &&
          row.operations.networkCalls === 0 &&
          row.operations.dockerProcesses === 0,
      ),
    ],
    [
      "RENDER_CALLS_EXACT",
      build.operations.renderCalls === 0 &&
        render.operations.renderCalls === 12 &&
        independent.operations.renderCalls === 0,
    ],
    [
      "OUTCOME_NEUTRAL_VERDICT_MAPPED",
      [spec.decision.supportedVerdict, spec.decision.rejectedVerdict].includes(
        scientificVerdict,
      ),
    ],
  ].map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  const status = checks.every((row) => row.pass) ? "PASS" : "FAIL";
  const record = await writeHashed(
    resolve(root, "audit.json"),
    {
      schemaVersion: "bfs.b62CameraQualityHoldoutRenderAudit.v0.1",
      experimentId: "B62-Q1-D4",
      status,
      scientificVerdict: status === "PASS" ? scientificVerdict : null,
      toolFreezeCommit: freeze,
      checks,
      outcome: { correctedAllPass, originalAllFail, pairDifferent },
      holdoutGeometry: independent.geometry,
      pairs: render.pairs,
      inputs: {
        spec: { uri: SPEC_URI, sha256: await hashFile(pathFor(SPEC_URI)) },
        protocol: {
          uri: PROTOCOL_URI,
          sha256: await hashFile(pathFor(PROTOCOL_URI)),
        },
        correction: {
          uri: CORRECTION_URI,
          sha256: await hashFile(pathFor(CORRECTION_URI)),
        },
        correctionProtocol: {
          uri: CORRECTION_PROTOCOL_URI,
          sha256: await hashFile(pathFor(CORRECTION_PROTOCOL_URI)),
        },
        build: {
          sha256: await hashFile(resolve(root, "build.json")),
          reportHash: build.reportHash,
        },
        render: {
          sha256: await hashFile(resolve(root, "render.json")),
          reportHash: render.reportHash,
        },
        independent: {
          sha256: await hashFile(resolve(root, "independent.json")),
          reportHash: independent.reportHash,
        },
      },
      correction2: {
        uri: CORRECTION2_URI,
        sha256: await hashFile(pathFor(CORRECTION2_URI)),
      },
      correction2Protocol: {
        uri: CORRECTION2_PROTOCOL_URI,
        sha256: await hashFile(pathFor(CORRECTION2_PROTOCOL_URI)),
      },
      humanReviewStatus: "PENDING",
      nonClaims: [
        ...spec.nonClaims,
        ...correction.nonClaims,
        ...correction2.nonClaims,
      ],
    },
    "auditHash",
  );
  req(
    status === "PASS",
    `checks ${checks
      .filter((row) => !row.pass)
      .map((row) => row.id)
      .join(",")}`,
  );
  process.stdout.write(
    `BFS_B62_Q1_D4_AUDIT PASS ${checks.length}/${checks.length} ${scientificVerdict} ${record.auditHash}\n`,
  );
  return record;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)
  audit(process.argv.slice(2)).catch((e) => {
    process.stderr.write(`BFS_B62_Q1_D4_AUDIT_ERROR ${e.message}\n`);
    process.exitCode = 1;
  });
