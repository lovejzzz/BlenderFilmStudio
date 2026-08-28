#!/usr/bin/env node
/** Independent scalar Node oracle for B52-D12.14-C1. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const SPEC_SHA256 = "fd3fe2808346c49a87183b3ed215b07abcbaf4058df13d055cc893b482ae30f5";
const TARGETS = [
  "TOP_MISSING_BOTTOM_AVAILABLE",
  "BOTTOM_MISSING_TOP_AVAILABLE",
  "NEITHER_HORIZONTAL_AVAILABLE",
];
const TARGET_CODE = new Map(TARGETS.map((name, index) => [name, index + 1]));
const MASK_NAMES = [
  "current-interior",
  "bilinear-support",
  "direction-left",
  "direction-right",
  "direction-top",
  "direction-bottom",
  "neither-horizontal",
  "full-stencil",
  "target",
  "non-target-one-sided",
];

function shaFile(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortValue(value[key])]));
  }
  return value;
}

function canonicalBytes(value) {
  return Buffer.from(JSON.stringify(sortValue(value)));
}

function canonicalHash(value) {
  return crypto.createHash("sha256").update(canonicalBytes(value)).digest("hex");
}

function fixed(value) {
  return Math.floor(value * 1_000_000 + 0.5);
}

function inside(rect, x, y) {
  return rect[0] <= x && x <= rect[2] && rect[1] <= y && y <= rect[3];
}

function targetPrefix(target) {
  return new Map([
    ["TOP_MISSING_BOTTOM_AVAILABLE", "TOP"],
    ["BOTTOM_MISSING_TOP_AVAILABLE", "BOTTOM"],
    ["NEITHER_HORIZONTAL_AVAILABLE", "NEITHER"],
  ]).get(target);
}

function candidateId(target, ordinal) {
  return `${targetPrefix(target)}-${String(ordinal).padStart(6, "0")}`;
}

function directionalMasks(candidate, keepMasks = false) {
  const [width, height] = candidate.resolution;
  const currentRect = candidate.currentRect;
  const previousRect = candidate.previousRect;
  const currentCenter = candidate.currentCenter;
  const previousCenter = candidate.previousCenter;
  const [scaleX, scaleY] = candidate.scale;
  const masks = keepMasks ? Object.fromEntries(MASK_NAMES.map((name) => [name, new Uint8Array(width * height)])) : null;
  const counts = Object.fromEntries(MASK_NAMES.map((name) => [name, 0]));
  const mark = (name, index, value) => {
    if (value) {
      counts[name] += 1;
      if (masks) masks[name][index] = 1;
    }
  };
  for (let y = 2; y < height - 2; y += 1) {
    for (let x = 2; x < width - 2; x += 1) {
      const interior = inside(currentRect, x - 2, y - 2) && inside(currentRect, x + 2, y + 2);
      if (!interior) continue;
      const index = y * width + x;
      mark("current-interior", index, true);
      const previousX = previousCenter[0] + (x - currentCenter[0]) / scaleX;
      const previousY = previousCenter[1] + (y - currentCenter[1]) / scaleY;
      const x0 = Math.floor(previousX);
      const y0 = Math.floor(previousY);
      const taps = [[x0, y0], [x0 + 1, y0], [x0, y0 + 1], [x0 + 1, y0 + 1]];
      const bilinear = taps.every(([px, py]) => 0 <= px && px < width && 0 <= py && py < height && inside(previousRect, px, py));
      mark("bilinear-support", index, bilinear);
      if (!bilinear) continue;
      const left0 = x0 - 1 >= 0 && inside(previousRect, x0 - 1, y0);
      const right0 = x0 + 2 < width && inside(previousRect, x0 + 2, y0);
      const left1 = x0 - 1 >= 0 && inside(previousRect, x0 - 1, y0 + 1);
      const right1 = x0 + 2 < width && inside(previousRect, x0 + 2, y0 + 1);
      const left = left0 && left1;
      const right = right0 && right1;
      const top = y0 - 1 >= 0 && inside(previousRect, x0, y0 - 1) && inside(previousRect, x0 + 1, y0 - 1);
      const bottom = y0 + 2 < height && inside(previousRect, x0, y0 + 2) && inside(previousRect, x0 + 1, y0 + 2);
      const values = {
        "direction-left": !left && right && top && bottom,
        "direction-right": left && !right && top && bottom,
        "direction-top": !top && bottom && left && right,
        "direction-bottom": top && !bottom && left && right,
        "neither-horizontal": (!left0 && !right0) || (!left1 && !right1),
        "full-stencil": left && right && top && bottom,
      };
      for (const [name, value] of Object.entries(values)) mark(name, index, value);
      const targetName = new Map([
        ["TOP_MISSING_BOTTOM_AVAILABLE", "direction-top"],
        ["BOTTOM_MISSING_TOP_AVAILABLE", "direction-bottom"],
        ["NEITHER_HORIZONTAL_AVAILABLE", "neither-horizontal"],
      ]).get(candidate.target);
      const target = values[targetName];
      const nonTarget = Object.entries(values).some(([name, value]) => name !== targetName && name !== "full-stencil" && value);
      mark("target", index, target);
      mark("non-target-one-sided", index, nonTarget);
    }
  }
  return { counts, masks };
}

function verticalCandidates(spec, target) {
  const grid = spec.searchSpace.vertical;
  const [width, height] = grid.resolutionByTarget[target];
  const centerX = (width - 1) / 2;
  const centerY = (height - 1) / 2;
  const rows = [];
  let ordinal = 0;
  for (const currentWidth of grid.currentWidthPixels) {
    for (const currentHeight of grid.currentHeightPixels) {
      for (const scaleX of grid.scaleX) {
        for (const [scaleYIndex, scaleY] of grid.scaleY.entries()) {
          for (const [phaseIndex, phase] of grid.targetEdgePhase.entries()) {
            for (const orthogonalOffset of grid.orthogonalCenterOffsetPixels) {
              for (const currentAxisOffset of grid.targetAxisCurrentCenterOffsetPixels) {
                const currentCenter = [centerX, centerY + currentAxisOffset];
                const currentRect = [
                  currentCenter[0] - currentWidth / 2,
                  currentCenter[1] - currentHeight / 2,
                  currentCenter[0] + currentWidth / 2,
                  currentCenter[1] + currentHeight / 2,
                ];
                const previousWidth = currentWidth / scaleX;
                const previousHeight = currentHeight / scaleY;
                const anchor = Math.floor((height - previousHeight) / 2) + phase;
                let previousTop;
                let previousBottom;
                if (target === "TOP_MISSING_BOTTOM_AVAILABLE") {
                  previousTop = anchor;
                  previousBottom = previousTop + previousHeight;
                } else {
                  previousBottom = height - 1 - anchor;
                  previousTop = previousBottom - previousHeight;
                }
                const previousCenter = [centerX + orthogonalOffset, (previousTop + previousBottom) / 2];
                const previousRect = [
                  previousCenter[0] - previousWidth / 2,
                  previousTop,
                  previousCenter[0] + previousWidth / 2,
                  previousBottom,
                ];
                rows.push({
                  id: candidateId(target, ordinal), ordinal, target, resolution: [width, height],
                  currentRect, previousRect, currentCenter, previousCenter, scale: [scaleX, scaleY],
                  phaseIndex, scaleIndex: scaleYIndex,
                  neighborhoodKey: [fixed(currentWidth), fixed(currentHeight), fixed(scaleX), fixed(scaleY), fixed(orthogonalOffset), fixed(currentAxisOffset)],
                });
                ordinal += 1;
              }
            }
          }
        }
      }
    }
  }
  return rows;
}

function neitherCandidates(spec) {
  const target = "NEITHER_HORIZONTAL_AVAILABLE";
  const grid = spec.searchSpace.neitherHorizontal;
  const [width, height] = grid.resolution;
  const centerX = (width - 1) / 2;
  const centerY = (height - 1) / 2;
  const rows = [];
  let ordinal = 0;
  for (const currentWidth of grid.currentWidthPixels) {
    for (const currentHeight of grid.currentHeightPixels) {
      for (const previousWidth of grid.previousWidthPixels) {
        for (const previousHeight of grid.previousHeightPixels) {
          for (const [phaseIndex, phase] of grid.previousCenterPhaseX.entries()) {
            for (const previousOffsetY of grid.previousCenterOffsetY) {
              const currentCenter = [centerX, centerY];
              const previousCenter = [Math.floor(centerX) + phase, centerY + previousOffsetY];
              const currentRect = [
                currentCenter[0] - currentWidth / 2,
                currentCenter[1] - currentHeight / 2,
                currentCenter[0] + currentWidth / 2,
                currentCenter[1] + currentHeight / 2,
              ];
              const previousRect = [
                previousCenter[0] - previousWidth / 2,
                previousCenter[1] - previousHeight / 2,
                previousCenter[0] + previousWidth / 2,
                previousCenter[1] + previousHeight / 2,
              ];
              rows.push({
                id: candidateId(target, ordinal), ordinal, target, resolution: [width, height],
                currentRect, previousRect, currentCenter, previousCenter,
                scale: [currentWidth / previousWidth, currentHeight / previousHeight], phaseIndex,
                neighborhoodKey: [fixed(currentWidth), fixed(currentHeight), fixed(previousWidth), fixed(previousHeight), fixed(previousOffsetY)],
              });
              ordinal += 1;
            }
          }
        }
      }
    }
  }
  return rows;
}

function rowPayload(candidate, counts, neighborhoodMinimum, passed) {
  return [
    TARGET_CODE.get(candidate.target), candidate.ordinal, ...candidate.resolution,
    ...candidate.currentRect.map(fixed), ...candidate.previousRect.map(fixed),
    fixed(candidate.currentCenter[0]), fixed(candidate.currentCenter[1]),
    fixed(candidate.previousCenter[0]), fixed(candidate.previousCenter[1]),
    fixed(candidate.scale[0]), fixed(candidate.scale[1]),
    counts["current-interior"], counts["bilinear-support"],
    counts["direction-left"], counts["direction-right"], counts["direction-top"], counts["direction-bottom"],
    counts["neither-horizontal"], counts["full-stencil"], counts.target, counts["non-target-one-sided"],
    neighborhoodMinimum, Number(passed),
  ];
}

function evaluateTarget(spec, candidates) {
  const measured = [];
  const lookup = new Map();
  for (const candidate of candidates) {
    const { counts } = directionalMasks(candidate);
    candidate.counts = counts;
    const key = candidate.neighborhoodKey.join(",");
    if (!lookup.has(key)) lookup.set(key, new Map());
    lookup.get(key).set(candidate.phaseIndex, counts.target);
  }
  const contract = spec.measurementContract;
  const target = candidates[0].target;
  const targetFloor = target === "NEITHER_HORIZONTAL_AVAILABLE" ? contract.neitherHorizontalMinimumWitnesses : contract.perVerticalTargetMinimumWitnesses;
  const phaseCount = Math.max(...candidates.map((candidate) => candidate.phaseIndex)) + 1;
  const passing = [];
  for (const candidate of candidates) {
    const neighbors = lookup.get(candidate.neighborhoodKey.join(","));
    const indices = [candidate.phaseIndex - 1, candidate.phaseIndex, candidate.phaseIndex + 1].filter((index) => 0 <= index && index < phaseCount);
    const neighborhoodMinimum = Math.min(...indices.map((index) => neighbors.get(index)));
    const counts = candidate.counts;
    const oneSided = counts.target + counts["non-target-one-sided"];
    const purityOk = oneSided > 0 && counts["non-target-one-sided"] * 100 <= 5 * oneSided;
    const passed = counts.target >= targetFloor
      && counts["current-interior"] >= contract.minimumCurrentInterior
      && counts["bilinear-support"] >= contract.minimumBilinearSupport
      && neighborhoodMinimum >= contract.minimumNeighborhoodTargetWitnesses
      && purityOk;
    candidate.neighborhoodMinimum = neighborhoodMinimum;
    candidate.passed = passed;
    measured.push(rowPayload(candidate, counts, neighborhoodMinimum, passed));
    if (passed) passing.push(candidate);
  }
  if (passing.length === 0) return { measured, selected: null, masks: null };
  const scaleIndex = target === "NEITHER_HORIZONTAL_AVAILABLE" ? 0 : 1;
  passing.sort((a, b) => {
    const keysA = [-a.neighborhoodMinimum, a.counts["non-target-one-sided"], fixed(a.scale[scaleIndex])];
    const keysB = [-b.neighborhoodMinimum, b.counts["non-target-one-sided"], fixed(b.scale[scaleIndex])];
    for (let index = 0; index < keysA.length; index += 1) {
      if (keysA[index] !== keysB[index]) return keysA[index] - keysB[index];
    }
    return a.id.localeCompare(b.id);
  });
  const selected = passing[0];
  const replay = directionalMasks(selected, true);
  if (JSON.stringify(replay.counts) !== JSON.stringify(selected.counts)) throw new Error("D12.14-C1 selected mask replay mismatch");
  return { measured, selected, masks: replay.masks };
}

function reportCandidate(candidate) {
  return {
    candidateId: candidate.id,
    target: candidate.target,
    ordinal: candidate.ordinal,
    resolution: candidate.resolution,
    currentRect: candidate.currentRect,
    previousRect: candidate.previousRect,
    currentCenter: candidate.currentCenter,
    previousCenter: candidate.previousCenter,
    scale: candidate.scale,
    phaseIndex: candidate.phaseIndex,
    neighborhoodMinimumTargetWitnesses: candidate.neighborhoodMinimum,
    counts: candidate.counts,
  };
}

function parseArgs() {
  const result = {};
  for (let index = 2; index < process.argv.length; index += 2) result[process.argv[index].slice(2)] = process.argv[index + 1];
  if (!result.spec || !result.output) throw new Error("--spec and --output are required");
  return result;
}

function main() {
  const args = parseArgs();
  if (shaFile(args.spec) !== SPEC_SHA256 || fs.existsSync(args.output)) throw new Error("D12.14-C1 spec identity or output freshness failure");
  const spec = JSON.parse(fs.readFileSync(args.spec, "utf8"));
  fs.mkdirSync(args.output, { recursive: true });
  const allRows = [];
  const selectedReports = [];
  const selectedHashes = {};
  for (const target of TARGETS) {
    const candidates = target === "NEITHER_HORIZONTAL_AVAILABLE" ? neitherCandidates(spec) : verticalCandidates(spec, target);
    const { measured, selected, masks } = evaluateTarget(spec, candidates);
    allRows.push(...measured);
    const targetHashes = {};
    if (selected && masks) {
      const selectedDir = path.join(args.output, "selected", target);
      fs.mkdirSync(selectedDir, { recursive: true });
      for (const name of MASK_NAMES) {
        const maskPath = path.join(selectedDir, `${name}.u8`);
        fs.writeFileSync(maskPath, Buffer.from(masks[name]));
        targetHashes[name] = { sha256: shaFile(maskPath), bytes: fs.statSync(maskPath).size };
      }
      selectedReports.push(reportCandidate(selected));
    } else {
      selectedReports.push({ target, candidateId: null });
    }
    selectedHashes[target] = targetHashes;
  }
  const candidatePath = path.join(args.output, "candidates.bin");
  fs.writeFileSync(candidatePath, Buffer.from(JSON.stringify(allRows)));
  const body = {
    schemaVersion: "bfs.blenderMaterialOwnerDirectionalFixtureCalibrationOracleReport.v0.1",
    experimentId: spec.experimentId,
    specSha256: SPEC_SHA256,
    language: "node",
    pid: process.pid,
    runtime: { node: process.version, executable: process.execPath, executableSha256: shaFile(process.execPath) },
    candidateCount: allRows.length,
    candidateTable: { uri: candidatePath, sha256: shaFile(candidatePath), bytes: fs.statSync(candidatePath).size },
    selected: selectedReports,
    selectedMasks: selectedHashes,
    operationCounts: { blenderProcesses: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, modelCalls: 0, networkCalls: 0 },
  };
  const report = { ...body, reportHash: canonicalHash(body) };
  fs.writeFileSync(path.join(args.output, "report.json"), `${JSON.stringify(sortValue(report), null, 2)}\n`);
  console.log(`BFS_B52_D1214C1_NODE_OK candidates=${allRows.length} selected=${selectedReports.map((row) => row.candidateId).join(",")}`);
}

main();
