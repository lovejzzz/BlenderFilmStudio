#!/usr/bin/env node
// Independent JavaScript/Float32Array reference worker for B52-D7.
import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';

const SPEC_SHA256 = 'f102a969cb59d92b0103c6807f20ca5436978504aafadd14a9b0353709ea0df5';
const argv = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, all) => index % 2 === 0 ? [...pairs, [value, all[index + 1]]] : pairs, []));
const specPath = argv['--spec'], fixtureId = argv['--fixture'], outputPath = argv['--output'], reportPath = argv['--report'];
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
const stable = value => Array.isArray(value) ? `[${value.map(stable).join(',')}]` : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stable(value[key])}`).join(',')}}` : JSON.stringify(value);
if (sha(fs.readFileSync(specPath)) !== SPEC_SHA256) throw new Error('spec mismatch');
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const fixture = spec.fixtures.find(item => item.id === fixtureId);
if (!fixture) throw new Error('fixture mismatch');
if (sha(fs.readFileSync(process.execPath)) !== spec.runtime.nodeReference.sha256) throw new Error('Node runtime mismatch');
if (fs.existsSync(outputPath) || fs.existsSync(reportPath)) throw new Error('refusing to overwrite reference output');
const [width, height] = fixture.resolution;
const source = new Float32Array(width * height * 4), field = new Float32Array(width * height * 2);
for (let y=0; y<height; y++) for (let x=0; x<width; x++) {
  const si=(y*width+x)*4;
  const values = fixture.sourcePattern === 'LOW_FREQUENCY_ALPHA_RAMP'
    ? [(x%64)/64,(y%64)/64,((x+3*y)%64)/64,((x+2*y)%17)/16]
    : [(x^y)&1,((5*x+11*y)%16)/16,((13*x+7*y)%32)/32,((3*x+5*y)%9)/8];
  source.set(values.map(Math.fround),si);
  let dx,dy;
  if (fixtureId==='LF_63X47_CLIP_Q1') [dx,dy]=[1/4,3/4];
  else if (fixtureId==='LF_63X47_EXTEND_MIX') [dx,dy]=[-3/2,1/8];
  else if (fixtureId==='LF_63X47_REPEAT_FIELD') [dx,dy]=[x<31?3/8:-5/8,y%2===0?1/4:-3/4];
  else if (fixtureId==='HF_127X73_CLIP_MIX') [dx,dy]=[-3/4,3/2];
  else if (fixtureId==='HF_127X73_EXTEND_MIX') [dx,dy]=[17/8,-3/8];
  else if (fixtureId==='HF_127X73_REPEAT_FIELD') [dx,dy]=[[1/8,5/8,-7/8,3/8][x%4],[-1/8,7/8][y%2]];
  else throw new Error('unknown fixture');
  field.set([Math.fround(dx),Math.fround(dy)],(y*width+x)*2);
}
const resolve=(value,size,mode)=>mode==='Clip'?(value>=0&&value<size?value:null):mode==='Extend'?Math.min(Math.max(value,0),size-1):((value%size)+size)%size;
const tap=(x,y)=>{const sx=resolve(x,width,fixture.extensionX),sy=resolve(y,height,fixture.extensionY);if(sx===null||sy===null)return[0,0,0,0];const i=(sy*width+sx)*4;return[source[i],source[i+1],source[i+2],source[i+3]];};
const output=new Float32Array(width*height*4);
for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  const di=(y*width+x)*2,u=x-field[di],v=y+field[di+1],x0=Math.floor(u),y0=Math.floor(v),fx=u-x0,fy=v-y0;
  const weights=[(1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy],taps=[tap(x0,y0),tap(x0+1,y0),tap(x0,y0+1),tap(x0+1,y0+1)];
  const oi=(y*width+x)*4;for(let c=0;c<4;c++)output[oi+c]=Math.fround(taps[0][c]*weights[0]+taps[1][c]*weights[1]+taps[2][c]*weights[2]+taps[3][c]*weights[3]);
}
const encode=array=>{const buffer=Buffer.alloc(array.length*4);const view=new DataView(buffer.buffer,buffer.byteOffset,buffer.byteLength);for(let i=0;i<array.length;i++)view.setFloat32(i*4,array[i],true);return buffer;};
const outputBytes=encode(output),sourceBytes=encode(source),fieldBytes=encode(field);
fs.mkdirSync(path.dirname(outputPath),{recursive:true});fs.writeFileSync(outputPath,outputBytes);
const body={schemaVersion:'bfs.subpixelBilinearNodeReferenceReport.v0.1',experimentId:spec.experimentId,fixtureId,pid:process.pid,runtime:{executable:process.execPath,sha256:spec.runtime.nodeReference.sha256},arrays:{sourceFloat32Sha256:sha(sourceBytes),displacementFloat32Sha256:sha(fieldBytes)},output:{uri:outputPath,sha256:sha(outputBytes),bytes:outputBytes.length},operationCounts:{pythonReferenceProcesses:0,nodeReferenceProcesses:1,blenderProcesses:0,renderCalls:0}};
const report={...body,reportHash:sha(Buffer.from(stable(body)))};fs.writeFileSync(reportPath,`${JSON.stringify(report,null,2)}\n`);
console.log(`BFS_B52_D7_NODE_REFERENCE_OK fixture=${fixtureId} sha=${report.output.sha256}`);
