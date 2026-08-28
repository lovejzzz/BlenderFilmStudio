#!/usr/bin/env node
/** Independent scalar Node 3D oracle for B52-D12.14-C2. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const SPEC_SHA256 = "e123b80fdba40c7e7e396e1aad149573e1e123c57198a21fa8af944320d7e4c3";
const TARGETS = ["TOP_MISSING_BOTTOM_AVAILABLE", "BOTTOM_MISSING_TOP_AVAILABLE", "NEITHER_HORIZONTAL_AVAILABLE"];
const TARGET_CODE = new Map(TARGETS.map((target, index) => [target, index + 1]));
const MASK_NAMES = [
  "current-foreground", "current-radius2", "previous-foreground", "bilinear-support",
  "direction-left", "direction-right", "direction-top", "direction-bottom",
  "neither-horizontal", "full-stencil", "target", "non-target-one-sided",
];

function shaFile(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value !== null && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortValue(value[key])]));
  return value;
}

function canonicalHash(value) {
  return crypto.createHash("sha256").update(Buffer.from(JSON.stringify(sortValue(value)))).digest("hex");
}

function fixed(value) {
  return value >= 0 ? Math.floor(value * 1_000_000 + 0.5) : -Math.floor(-value * 1_000_000 + 0.5);
}

function rotationXYZ(values) {
  const [x, y, z] = values;
  const cx = Math.cos(x); const sx = Math.sin(x);
  const cy = Math.cos(y); const sy = Math.sin(y);
  const cz = Math.cos(z); const sz = Math.sin(z);
  return [
    [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
    [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx + cz * sx],
    [-sy, cy * sx, cy * cx],
  ];
}

const add = (a, b) => a.map((value, index) => value + b[index]);
const subtract = (a, b) => a.map((value, index) => value - b[index]);
const scale = (a, amount) => a.map((value) => value * amount);
const dot = (a, b) => a.reduce((sum, value, index) => sum + value * b[index], 0);
const matVec = (matrix, vector) => matrix.map((row) => row.reduce((sum, value, index) => sum + value * vector[index], 0));
const matTVec = (matrix, vector) => [0, 1, 2].map((column) => matrix.reduce((sum, row, index) => sum + row[column] * vector[index], 0));

function transform(location, rotation) {
  return [location.map(Number), rotationXYZ(rotation.map(Number))];
}

function cameraRay(spec, width, height, pixelX, pixelY) {
  const camera = spec.sceneContract.camera;
  const sensorWidth = Number(camera.sensorWidthMm);
  const sensorHeight = sensorWidth * height / width;
  const lens = Number(camera.lensMm);
  const u = (pixelX + 0.5) / width;
  const vBottom = 1 - (pixelY + 0.5) / height;
  return [(u - 0.5) * sensorWidth / lens, (vBottom - 0.5) * sensorHeight / lens, -1];
}

function preparedOwner(id, size, location, rotation) {
  const [ownerLocation, ownerRotation] = transform(location, rotation);
  return { id, size: size.map(Number), location: ownerLocation, rotation: ownerRotation, normal: matVec(ownerRotation, [0, 0, 1]) };
}

function intersectPrepared(cameraLocation, direction, owner) {
  const denominator = dot(direction, owner.normal);
  if (denominator === 0) return null;
  const distance = dot(subtract(owner.location, cameraLocation), owner.normal) / denominator;
  if (distance <= 0) return null;
  const worldPoint = add(cameraLocation, scale(direction, distance));
  const localPoint = matTVec(owner.rotation, subtract(worldPoint, owner.location));
  if (Math.abs(localPoint[0]) > owner.size[0] / 2 || Math.abs(localPoint[1]) > owner.size[1] / 2) return null;
  const depth = cameraLocation[2] - worldPoint[2];
  return depth > 0 ? [depth, localPoint] : null;
}

function rasterFrame(spec, candidate, frame, keepLocal) {
  const [width, height] = candidate.resolution;
  const cameraLocation = spec.sceneContract.camera.location.map(Number);
  const foregroundSpec = spec.sceneContract.foreground;
  const foreground = preparedOwner(
    "foreground", foregroundSpec.sizeWorld,
    frame === 0 ? candidate.previousLocation : candidate.currentLocation,
    frame === 0 ? candidate.previousRotation : candidate.currentRotation,
  );
  const backgroundSpec = spec.sceneContract.background;
  const background = preparedOwner("background", backgroundSpec.sizeWorld, backgroundSpec.locationByFrame[String(frame)], backgroundSpec.rotationEulerByFrame[String(frame)]);
  const mask = new Uint8Array(width * height);
  const localPoints = keepLocal ? new Array(width * height).fill(null) : null;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = y * width + x;
      const direction = cameraRay(spec, width, height, x, y);
      const hits = [];
      for (const owner of [foreground, background]) {
        const hit = intersectPrepared(cameraLocation, direction, owner);
        if (hit) hits.push([hit[0], owner.id, hit[1]]);
      }
      hits.sort((a, b) => a[0] - b[0]);
      const surface = hits.length ? hits[0] : null;
      if (surface && surface[1] === "foreground") {
        mask[index] = 1;
        if (localPoints) localPoints[index] = surface[2];
      }
    }
  }
  return [mask, localPoints];
}

function cacheKey(resolution, location, rotation) {
  return JSON.stringify([resolution, location, rotation]);
}

function foregroundRasters(spec, candidate, caches) {
  const currentKey = cacheKey(candidate.resolution, candidate.currentLocation, candidate.currentRotation);
  const previousKey = cacheKey(candidate.resolution, candidate.previousLocation, candidate.previousRotation);
  if (!caches.current.has(currentKey)) caches.current.set(currentKey, rasterFrame(spec, candidate, 1, true));
  if (!caches.previous.has(previousKey)) caches.previous.set(previousKey, rasterFrame(spec, candidate, 0, false)[0]);
  const [current, currentLocal] = caches.current.get(currentKey);
  return [current, caches.previous.get(previousKey), currentLocal];
}

function project(spec, candidate, worldPoint) {
  const [width, height] = candidate.resolution;
  const camera = spec.sceneContract.camera;
  const relative = subtract(worldPoint, camera.location.map(Number));
  const depth = -relative[2];
  if (depth <= 0) return null;
  const sensorWidth = Number(camera.sensorWidthMm);
  const sensorHeight = sensorWidth * height / width;
  const lens = Number(camera.lensMm);
  return [(0.5 + lens * relative[0] / (depth * sensorWidth)) * width - 0.5, (0.5 - lens * relative[1] / (depth * sensorHeight)) * height - 0.5];
}

function directionalMasks(spec, candidate, caches, keepMasks = false) {
  const [width, height] = candidate.resolution;
  const [current, previous, currentLocal] = foregroundRasters(spec, candidate, caches);
  const masks = keepMasks ? Object.fromEntries(MASK_NAMES.map((name) => [name, new Uint8Array(width * height)])) : null;
  const counts = Object.fromEntries(MASK_NAMES.map((name) => [name, 0]));
  counts["current-foreground"] = current.reduce((sum, value) => sum + value, 0);
  counts["previous-foreground"] = previous.reduce((sum, value) => sum + value, 0);
  if (masks) {
    masks["current-foreground"].set(current);
    masks["previous-foreground"].set(previous);
  }
  const mark = (name, index, value) => {
    if (value) {
      counts[name] += 1;
      if (masks) masks[name][index] = 1;
    }
  };
  const previousTransform = transform(candidate.previousLocation, candidate.previousRotation);
  for (let y = 2; y < height - 2; y += 1) {
    for (let x = 2; x < width - 2; x += 1) {
      const index = y * width + x;
      let interior = true;
      for (let dy = -2; dy <= 2 && interior; dy += 1) {
        for (let dx = -2; dx <= 2; dx += 1) {
          if (!current[(y + dy) * width + x + dx]) { interior = false; break; }
        }
      }
      if (!interior) continue;
      mark("current-radius2", index, true);
      const localPoint = currentLocal[index];
      if (!localPoint) throw new Error("D12.14-C2 missing current local point");
      const previousWorld = add(previousTransform[0], matVec(previousTransform[1], localPoint));
      const coordinate = project(spec, candidate, previousWorld);
      if (!coordinate) continue;
      const x0 = Math.floor(coordinate[0]); const y0 = Math.floor(coordinate[1]);
      const valid = (px, py) => 0 <= px && px < width && 0 <= py && py < height && Boolean(previous[py * width + px]);
      const bilinear = valid(x0, y0) && valid(x0 + 1, y0) && valid(x0, y0 + 1) && valid(x0 + 1, y0 + 1);
      mark("bilinear-support", index, bilinear);
      if (!bilinear) continue;
      const left0 = valid(x0 - 1, y0); const right0 = valid(x0 + 2, y0);
      const left1 = valid(x0 - 1, y0 + 1); const right1 = valid(x0 + 2, y0 + 1);
      const left = left0 && left1; const right = right0 && right1;
      const top = valid(x0, y0 - 1) && valid(x0 + 1, y0 - 1);
      const bottom = valid(x0, y0 + 2) && valid(x0 + 1, y0 + 2);
      const values = {
        "direction-left": !left && right && top && bottom,
        "direction-right": left && !right && top && bottom,
        "direction-top": left && right && !top && bottom,
        "direction-bottom": left && right && top && !bottom,
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

function candidateId(target, ordinal) {
  const prefix = new Map([[TARGETS[0], "TOP"], [TARGETS[1], "BOTTOM"], [TARGETS[2], "NEITHER"]]).get(target);
  return `${prefix}-${String(ordinal).padStart(6, "0")}`;
}

function verticalCandidates(spec, target) {
  const grid = spec.searchSpace.vertical;
  const rows = []; let ordinal = 0;
  for (const currentX of grid.currentX) {
    for (const currentY of grid.currentYByTarget[target]) {
      for (const currentZ of grid.currentZ) {
        for (const previousX of grid.previousX) {
          for (const [deltaIndex, deltaY] of grid.previousYDeltaFromCurrent.entries()) {
            for (const previousZ of grid.previousZ) {
              rows.push({
                id: candidateId(target, ordinal), ordinal, target, resolution: grid.resolutionByTarget[target],
                currentLocation: [currentX, currentY, currentZ], currentRotation: [0, 0, 0],
                previousLocation: [previousX, currentY + deltaY, previousZ], previousRotation: [0, 0, 0],
                deltaY, robustnessIndex: deltaIndex,
                robustnessKey: [fixed(currentX), fixed(currentY), fixed(currentZ), fixed(previousX), fixed(previousZ)],
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

function neitherCandidates(spec) {
  const target = "NEITHER_HORIZONTAL_AVAILABLE";
  const grid = spec.searchSpace.neither;
  const rows = []; let ordinal = 0;
  const currentLocation = grid.currentLocation.map(Number);
  const currentRotation = grid.currentRotationEulerDegrees.map((value) => Number(value) * Math.PI / 180);
  for (const previousX of grid.previousX) {
    for (const previousY of grid.previousY) {
      for (const [zIndex, previousZ] of grid.previousZ.entries()) {
        for (const angle of grid.previousRotationYDegrees) {
          for (const rotationX of grid.previousRotationXDegrees) {
            for (const rotationZ of grid.previousRotationZDegrees) {
              rows.push({
                id: candidateId(target, ordinal), ordinal, target, resolution: grid.resolution,
                currentLocation, currentRotation, previousLocation: [previousX, previousY, previousZ],
                previousRotation: [rotationX * Math.PI / 180, angle * Math.PI / 180, rotationZ * Math.PI / 180],
                previousRotationDegrees: [rotationX, angle, rotationZ], angleDegrees: angle,
                robustnessIndex: zIndex,
                robustnessKey: [fixed(previousX), fixed(previousY), fixed(angle), fixed(rotationX), fixed(rotationZ)],
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
  const rotationDegrees = candidate.previousRotationDegrees ?? candidate.previousRotation.map((value) => value * 180 / Math.PI);
  return [
    TARGET_CODE.get(candidate.target), candidate.ordinal, ...candidate.resolution,
    ...candidate.currentLocation.map(fixed), ...candidate.currentRotation.map((value) => fixed(value * 180 / Math.PI)),
    ...candidate.previousLocation.map(fixed), ...rotationDegrees.map(fixed),
    counts["current-foreground"], counts["current-radius2"], counts["previous-foreground"], counts["bilinear-support"],
    counts["direction-left"], counts["direction-right"], counts["direction-top"], counts["direction-bottom"],
    counts["neither-horizontal"], counts["full-stencil"], counts.target, counts["non-target-one-sided"],
    neighborhoodMinimum, Number(passed),
  ];
}

function evaluateTarget(spec, candidates, caches) {
  const lookup = new Map();
  for (const candidate of candidates) {
    candidate.counts = directionalMasks(spec, candidate, caches).counts;
    const key = candidate.robustnessKey.join(",");
    if (!lookup.has(key)) lookup.set(key, new Map());
    lookup.get(key).set(candidate.robustnessIndex, candidate.counts.target);
  }
  const target = candidates[0].target;
  const contract = spec.measurementContract;
  const targetFloor = target === TARGETS[2] ? contract.neitherTargetMinimumWitnesses : contract.verticalTargetMinimumWitnesses;
  const neighborhoodFloor = target === TARGETS[2] ? contract.neitherNeighborhoodMinimumWitnesses : contract.verticalNeighborhoodMinimumWitnesses;
  const axisCount = Math.max(...candidates.map((row) => row.robustnessIndex)) + 1;
  const rows = []; const passing = [];
  for (const candidate of candidates) {
    const neighbors = lookup.get(candidate.robustnessKey.join(","));
    const indices = [candidate.robustnessIndex - 1, candidate.robustnessIndex, candidate.robustnessIndex + 1].filter((index) => 0 <= index && index < axisCount);
    const neighborhoodMinimum = Math.min(...indices.map((index) => neighbors.get(index)));
    const counts = candidate.counts;
    const passed = counts.target >= targetFloor
      && neighborhoodMinimum >= neighborhoodFloor
      && counts["current-radius2"] >= contract.minimumCurrentForegroundRadius2
      && counts["bilinear-support"] >= contract.minimumBilinearSupport
      && counts["non-target-one-sided"] <= contract.maximumNonTargetOneSidedWitnesses;
    candidate.neighborhoodMinimum = neighborhoodMinimum;
    candidate.passed = passed;
    rows.push(rowPayload(candidate, counts, neighborhoodMinimum, passed));
    if (passed) passing.push(candidate);
  }
  if (!passing.length) return { rows, selected: null, masks: null };
  passing.sort((a, b) => {
    const keysA = a.target === TARGETS[2]
      ? [-a.neighborhoodMinimum, -a.counts.target, fixed(Math.abs(90 - a.angleDegrees)), fixed(Math.abs(a.previousLocation[0]))]
      : [-a.neighborhoodMinimum, -a.counts.target, fixed(Math.abs(a.deltaY))];
    const keysB = b.target === TARGETS[2]
      ? [-b.neighborhoodMinimum, -b.counts.target, fixed(Math.abs(90 - b.angleDegrees)), fixed(Math.abs(b.previousLocation[0]))]
      : [-b.neighborhoodMinimum, -b.counts.target, fixed(Math.abs(b.deltaY))];
    for (let index = 0; index < keysA.length; index += 1) if (keysA[index] !== keysB[index]) return keysA[index] - keysB[index];
    return a.id.localeCompare(b.id);
  });
  const selected = passing[0];
  const replay = directionalMasks(spec, selected, caches, true);
  if (JSON.stringify(replay.counts) !== JSON.stringify(selected.counts)) throw new Error("D12.14-C2 selected replay mismatch");
  return { rows, selected, masks: replay.masks };
}

function reportCandidate(candidate) {
  return {
    candidateId: candidate.id, target: candidate.target, ordinal: candidate.ordinal, resolution: candidate.resolution,
    currentLocation: candidate.currentLocation, currentRotationEuler: candidate.currentRotation,
    previousLocation: candidate.previousLocation, previousRotationEuler: candidate.previousRotation,
    neighborhoodMinimumTargetWitnesses: candidate.neighborhoodMinimum, counts: candidate.counts,
  };
}

function parseArgs() {
  const args = {};
  for (let index = 2; index < process.argv.length; index += 2) args[process.argv[index].slice(2)] = process.argv[index + 1];
  if (!args.spec || !args.output) throw new Error("--spec and --output required");
  return args;
}

function main() {
  const args = parseArgs();
  if (shaFile(args.spec) !== SPEC_SHA256 || fs.existsSync(args.output)) throw new Error("D12.14-C2 spec identity or output freshness failure");
  const spec = JSON.parse(fs.readFileSync(args.spec, "utf8"));
  fs.mkdirSync(args.output, { recursive: true });
  const caches = { current: new Map(), previous: new Map() };
  const allRows = []; const selectedReports = []; const selectedHashes = {};
  for (const target of TARGETS) {
    const candidates = target === TARGETS[2] ? neitherCandidates(spec) : verticalCandidates(spec, target);
    const { rows, selected, masks } = evaluateTarget(spec, candidates, caches);
    allRows.push(...rows);
    const hashes = {};
    if (selected && masks) {
      const selectedDir = path.join(args.output, "selected", target);
      fs.mkdirSync(selectedDir, { recursive: true });
      for (const name of MASK_NAMES) {
        const maskPath = path.join(selectedDir, `${name}.u8`);
        fs.writeFileSync(maskPath, Buffer.from(masks[name]));
        hashes[name] = { sha256: shaFile(maskPath), bytes: fs.statSync(maskPath).size };
      }
      selectedReports.push(reportCandidate(selected));
    } else selectedReports.push({ target, candidateId: null });
    selectedHashes[target] = hashes;
  }
  const candidatePath = path.join(args.output, "candidates.bin");
  fs.writeFileSync(candidatePath, Buffer.from(JSON.stringify(allRows)));
  const body = {
    schemaVersion: "bfs.blenderMaterialOwnerRigidDirectionalCalibrationOracleReport.v0.1",
    experimentId: spec.experimentId, specSha256: SPEC_SHA256, language: "node", pid: process.pid,
    runtime: { node: process.version, executable: process.execPath, executableSha256: shaFile(process.execPath) },
    candidateCount: allRows.length,
    candidateTable: { uri: candidatePath, sha256: shaFile(candidatePath), bytes: fs.statSync(candidatePath).size },
    selected: selectedReports, selectedMasks: selectedHashes,
    operationCounts: { blenderProcesses: 0, blenderRenderCalls: 0, cyclesRayRenders: 0, modelCalls: 0, networkCalls: 0 },
  };
  const report = { ...body, reportHash: canonicalHash(body) };
  fs.writeFileSync(path.join(args.output, "report.json"), `${JSON.stringify(sortValue(report), null, 2)}\n`);
  console.log(`BFS_B52_D1214C2_NODE_OK candidates=${allRows.length} selected=${selectedReports.map((row) => row.candidateId ?? "NONE").join(",")}`);
}

main();
