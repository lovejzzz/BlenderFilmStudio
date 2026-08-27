#!/usr/bin/env node
/** Owner-aware scalar Node consumer for B52-D12.3. */

import crypto from 'node:crypto';
import fs from 'node:fs';
import process from 'node:process';

const SPEC_SHA256 = 'f1ffe5b4fe0912936b1e03677dd0985f11c34e6b5df4ddf70854533c4ad0b590';
const INPUTS = { previousRgba: ['previous.rgba32', 4], currentRgba: ['current.rgba32', 4], previousOwner: ['previous-owner.f32', 1], currentOwner: ['current-owner.f32', 1], vector: ['vector.xy32', 2] };
function parseArgs() { const out = {}; for (let i = 2; i < process.argv.length; i += 2) out[process.argv[i].replace(/^--/, '')] = process.argv[i + 1]; for (const key of ['spec','fixture','repeat','input-dir','adapter-report','output-dir','report']) if (!(key in out)) throw new Error(`missing --${key}`); out.repeat = Number(out.repeat); return out; }
const shaBytes = value => crypto.createHash('sha256').update(value).digest('hex');
const shaFile = path => shaBytes(fs.readFileSync(path));
function stable(value) { if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`; if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}`; return JSON.stringify(value); }
const canonicalHash = value => shaBytes(Buffer.from(stable(value)));
function readF32(path) { const buffer = fs.readFileSync(path), values = new Float32Array(buffer.length / 4); for (let i = 0; i < values.length; i++) values[i] = buffer.readFloatLE(i * 4); return {buffer, values}; }
function encodeF32(values) { const buffer = Buffer.alloc(values.length * 4); for (let i = 0; i < values.length; i++) buffer.writeFloatLE(values[i], i * 4); return buffer; }
const pixelBase = (width, x, y, channels) => (y * width + x) * channels;

function main() {
  const args = parseArgs(), specBuffer = fs.readFileSync(args.spec);
  if (shaBytes(specBuffer) !== SPEC_SHA256) throw new Error('D12.3 spec identity mismatch');
  const spec = JSON.parse(specBuffer);
  if (process.version !== spec.runtime.node.version || shaFile(process.execPath) !== spec.runtime.node.sha256) throw new Error('D12.3 Node identity mismatch');
  const fixture = spec.fixtures.find(row => row.id === args.fixture);
  if (!fixture || fs.existsSync(args['output-dir']) || fs.existsSync(args.report)) throw new Error('D12.3 fixture invalid or output exists');
  const adapter = JSON.parse(fs.readFileSync(args['adapter-report'], 'utf8'));
  const adapterBody = Object.fromEntries(Object.entries(adapter).filter(([key]) => key !== 'reportHash'));
  if (adapter.reportHash !== canonicalHash(adapterBody) || adapter.fixtureId !== args.fixture || adapter.repeat !== args.repeat) throw new Error('D12.3 adapter identity mismatch');
  const [width, height] = fixture.resolution, arrays = {};
  for (const [name, [filename]] of Object.entries(INPUTS)) { const loaded = readF32(`${args['input-dir']}/${filename}`); if (shaBytes(loaded.buffer) !== adapter.arrays[name].sha256) throw new Error(`D12.3 adapter array mismatch: ${name}`); arrays[name] = loaded.values; }
  const previous = arrays.previousRgba, current = arrays.currentRgba, reconstructed = new Float32Array(current), valid = new Uint8Array(width * height), boundary = new Uint8Array(width * height);
  const ownerIds = new Set(fixture.owners.map(owner => Math.fround(owner.passIndex))), radius = 2;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const pixel = y * width + x, owner = arrays.currentOwner[pixel], base = pixel * 4;
    if (!ownerIds.has(owner) || current[base + 3] <= Math.fround(0.999)) continue;
    const vectorX = arrays.vector[pixel * 2], vectorY = arrays.vector[pixel * 2 + 1], qx = x + vectorX, qy = y - vectorY;
    const x0 = Math.floor(qx), y0 = Math.floor(qy), x1 = x0 + 1, y1 = y0 + 1;
    let neighborhoodOk = x >= radius && y >= radius && x < width - radius && y < height - radius;
    if (neighborhoodOk) outer: for (let ty = y - radius; ty <= y + radius; ty++) for (let tx = x - radius; tx <= x + radius; tx++) {
      const tap = ty * width + tx;
      if (arrays.currentOwner[tap] !== owner || current[tap * 4 + 3] <= Math.fround(0.999)) { neighborhoodOk = false; break outer; }
    }
    let tapsOk = x0 >= 0 && y0 >= 0 && x1 < width && y1 < height;
    if (tapsOk) tapsOk = [[y0,x0],[y0,x1],[y1,x0],[y1,x1]].every(([ty,tx]) => { const tap = ty * width + tx; return arrays.previousOwner[tap] === owner && previous[tap * 4 + 3] > Math.fround(0.999); });
    if (!neighborhoodOk || !tapsOk) { boundary[pixel] = 1; continue; }
    const fx = qx - x0, fy = qy - y0, w0 = (1-fx)*(1-fy), w1 = fx*(1-fy), w2 = (1-fx)*fy, w3 = fx*fy;
    for (let channel = 0; channel < 4; channel++) {
      const v0 = previous[pixelBase(width,x0,y0,4)+channel], v1 = previous[pixelBase(width,x1,y0,4)+channel], v2 = previous[pixelBase(width,x0,y1,4)+channel], v3 = previous[pixelBase(width,x1,y1,4)+channel];
      reconstructed[base + channel] = Math.fround((((v0*w0)+(v1*w1))+(v2*w2))+(v3*w3));
    }
    valid[pixel] = 1;
  }
  fs.mkdirSync(args['output-dir'], {recursive:true});
  const records = {};
  for (const [name, filename, payload, shape, dtype] of [
    ['reconstructed','reconstructed.rgba32',encodeF32(reconstructed),[height,width,4],'little-endian-float32'],
    ['valid','valid.u8',Buffer.from(valid),[height,width],'uint8'], ['boundary','boundary.u8',Buffer.from(boundary),[height,width],'uint8']]) {
    const target = `${args['output-dir']}/${filename}`; fs.writeFileSync(target,payload); records[name] = {uri:target,sha256:shaBytes(payload),bytes:payload.length,shape,dtype};
  }
  const report = {schemaVersion:'bfs.blenderStaticNonplanarMultiownerConsumerReport.v0.1',experimentId:spec.experimentId,producer:'node',fixtureId:args.fixture,repeat:args.repeat,pid:process.pid,runtime:{node:process.version,nodeExecutableSha256:shaFile(process.execPath)},adapter:{uri:args['adapter-report'],sha256:shaFile(args['adapter-report']),reportHash:adapter.reportHash},contract:spec.ownerAwareConsumer,arrays:records,integrity:'external dual typed-envelope sidecars',operationCounts:{consumerProcesses:1,pixelsVisited:width*height,modelCalls:0,networkCalls:0}};
  fs.mkdirSync(args.report.slice(0,args.report.lastIndexOf('/')),{recursive:true}); fs.writeFileSync(args.report,`${JSON.stringify(report,null,2)}\n`);
  process.stdout.write(`BFS_B52_D123_CONSUMER_NODE_OK fixture=${args.fixture} repeat=${args.repeat} valid=${valid.reduce((a,b)=>a+b,0)} boundary=${boundary.reduce((a,b)=>a+b,0)}\n`);
}
main();
