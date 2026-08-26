import { createHash, randomBytes } from 'node:crypto';
import { link, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { relative, resolve, sep } from 'node:path';
import { repositoryRoot } from './lib/scene-spec.mjs';
import { sha256Canonical, sha256File } from './lib/receipt-format.mjs';

const root = resolve(repositoryRoot, 'experiments/blind-temporal-review-v0-1');
const evidenceRoot = resolve(root, 'evidence');
const workRoot = resolve(root, 'work');
const carrierRoot = resolve(workRoot, 'carriers');
const decodedRoot = resolve(workRoot, 'decoded');
const sessionRoot = resolve(workRoot, 'observer-sessions');
const sealedRoot = resolve(workRoot, 'sealed');
const specPath = resolve(repositoryRoot, 'specs/blind-temporal-review-spec.v0.1.json');
const b25ResultPath = resolve(repositoryRoot, 'experiments/temporal-residual-holdout-v0-1/results.json');
const b25Root = resolve(repositoryRoot, 'experiments/temporal-residual-holdout-v0-1');
const verifier = resolve(repositoryRoot, 'blender/verify_b26_lossless_carrier.py');
const runner = fileURLToPath(import.meta.url);
const blender = resolve(process.env.BLENDER_BIN || '/Applications/Blender.app/Contents/MacOS/Blender');
const ffmpeg = resolve(process.env.FFMPEG_BIN || '/opt/homebrew/bin/ffmpeg');
const ffprobe = resolve(process.env.FFPROBE_BIN || '/opt/homebrew/bin/ffprobe');
const serialize = value => `${JSON.stringify(value, null, 2)}\n`;
const repoUri = path => relative(repositoryRoot, path).split(sep).join('/');

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; });
    child.stderr.on('data', chunk => { output += chunk; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolvePromise({ processId: child.pid, output }) : reject(new Error(`${command} failed (${code})\n${output}`)));
  });
}

function digest(value) { return createHash('sha256').update(value).digest('hex'); }

function observerHtml({ sessionId, specSha, visibleCarriers }) {
  const data = JSON.stringify({ sessionId, specSha, visibleCarriers });
  return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BFS B26 ${sessionId} · blinded temporal review</title>
<style>
:root{color-scheme:dark;--bg:#0c1010;--panel:#151a19;--ink:#edf0e8;--muted:#8c9893;--acid:#cfff5c;--orange:#ff765b}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:40px 24px 90px}header{border-bottom:1px solid #39423f;padding-bottom:28px}h1{font-size:clamp(38px,7vw,82px);line-height:.93;letter-spacing:-.06em;margin:22px 0}h1 span{color:var(--acid)}code,.mono{font-family:ui-monospace,monospace;color:var(--muted)}.warning{border:1px solid var(--orange);padding:18px;color:#ffc2b4}.clips{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#39423f;border:1px solid #39423f;margin-top:34px}.clip{background:var(--panel);padding:18px}.clip video{width:100%;display:block;background:#000;pointer-events:none}.clip h2{display:flex;justify-content:space-between;font-size:18px}.clip button,.lock{width:100%;border:0;background:var(--acid);padding:13px;font-weight:750;cursor:pointer}.clip button:disabled{background:#4e554d;color:#8d938c}.fields{display:grid;gap:10px;margin-top:16px}.fields label,.env label{display:grid;gap:6px;color:var(--muted);font-size:12px}select,input,textarea{width:100%;background:#0d1110;color:var(--ink);border:1px solid #46504c;padding:10px}section{margin-top:58px}section>h2{font-size:28px}.pairs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.pair{border:1px solid #46504c;padding:15px}.env{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.lock{margin-top:28px;font-size:16px}.status{margin-top:16px;color:var(--acid);font-family:ui-monospace,monospace}@media(max-width:800px){.clips,.pairs,.env{grid-template-columns:1fr}}
</style></head><body><main><header><div class="mono">BFS · B26 · ${sessionId}</div><h1>只判断<span>时间稳定性。</span></h1><p>这是匿名 primary review。每个片段必须完整播放两次；不得暂停、拖动或逐帧查看。不要打开开发者工具或研究仓库。完成并锁定 primary response 后，才可进入任何诊断回看。</p><div class="warning">你看不到 A/B/C 映射。此页面不会显示解盲信息；项目参与者的 session 只能标记为 interface pilot。</div></header>
<section><h2>01 · Primary clips</h2><div class="clips">${visibleCarriers.map((item, index) => `<article class="clip"><h2><span>${item.label}</span><small id="plays-${index}">0 / 2 plays</small></h2><video id="video-${index}" preload="metadata" playsinline src="${item.file}"></video><button type="button" id="play-${index}">完整播放</button><div class="fields"><label>Temporal instability<select id="rating-${index}" disabled><option value="">请选择</option><option>NONE</option><option>BARELY_VISIBLE</option><option>MILD</option><option>OBVIOUS</option><option>SEVERE</option></select></label><label>Confidence<select id="confidence-${index}" disabled><option value="">请选择</option><option>LOW</option><option>MEDIUM</option><option>HIGH</option></select></label><label>可选：时间 / 位置<textarea id="note-${index}" rows="2" disabled></textarea></label></div></article>`).join('')}</div></section>
<section><h2>02 · Pairwise judgement</h2><p>基于刚才的完整播放判断；primary response 锁定前不提供 seek/pause/loop。</p><div class="pairs">${[['CLIP-01','CLIP-02'],['CLIP-01','CLIP-03'],['CLIP-02','CLIP-03']].map((pair,index)=>`<label class="pair"><b>${pair[0]} × ${pair[1]}</b><select id="pair-${index}"><option value="">请选择</option><option>LEFT_MORE_STABLE</option><option>INDISTINGUISHABLE</option><option>RIGHT_MORE_STABLE</option></select><textarea id="pair-note-${index}" rows="2" placeholder="可选：时间 / 位置"></textarea></label>`).join('')}</div></section>
<section><h2>03 · Viewing record</h2><div class="env">${[
    ['observerId','匿名 observer ID'],['expertise','影像质量经验 / expertise'],['development','是否直接参与 BFS 开发（YES/NO）'],['acuity','正常或矫正视力筛查状态'],['colour','色觉筛查状态'],['display','显示器厂商与型号'],['resolution','原生分辨率'],['refresh','刷新率'],['scaling','缩放与亮度设置'],['player','浏览器名称与版本'],['os','操作系统'],['distance','观看距离'],['ambient','环境光描述'],
  ].map(([id,label])=>`<label>${label}<input id="${id}" required></label>`).join('')}</div><button type="button" class="lock" id="lock">锁定并下载 response JSON</button><div class="status" id="status">UNLOCKED · HUMAN RESULT PENDING</div></section>
<script>
const DATA=${data};const plays=[0,0,0];let active=-1,locked=false;const startedAt=new Date().toISOString();
for(let i=0;i<3;i++){const video=document.getElementById('video-'+i),button=document.getElementById('play-'+i);button.addEventListener('click',async()=>{if(locked||active!==-1||plays[i]>=2)return;active=i;button.disabled=true;video.currentTime=0;await video.play()});video.addEventListener('ended',()=>{plays[i]++;active=-1;document.getElementById('plays-'+i).textContent=plays[i]+' / 2 plays';if(plays[i]>=2){for(const id of ['rating-','confidence-','note-'])document.getElementById(id+i).disabled=false}else button.disabled=false})}
const value=id=>document.getElementById(id).value.trim();
document.getElementById('lock').addEventListener('click',async()=>{if(locked)return;if(plays.some(v=>v!==2)){alert('每个片段必须完整播放两次');return}const clipResponses=DATA.visibleCarriers.map((c,i)=>({label:c.label,carrierSha256:c.sha256,rating:value('rating-'+i),confidence:value('confidence-'+i),note:value('note-'+i)}));const pairResponses=[0,1,2].map(i=>({pair:i,choice:value('pair-'+i),note:value('pair-note-'+i)}));const viewing={observerId:value('observerId'),expertise:value('expertise'),directDevelopmentInvolvement:value('development'),acuityScreening:value('acuity'),colourVisionScreening:value('colour'),display:value('display'),nativeResolution:value('resolution'),refreshRate:value('refresh'),scalingAndBrightness:value('scaling'),player:value('player'),operatingSystem:value('os'),viewingDistance:value('distance'),ambientLighting:value('ambient'),userAgent:navigator.userAgent};if(clipResponses.some(r=>!r.rating||!r.confidence)||pairResponses.some(r=>!r.choice)||Object.values(viewing).some(v=>!v)){alert('请完成全部必填项');return}const body={documentType:'BFS_B26_BLINDED_RESPONSE',version:'0.1.0',sessionId:DATA.sessionId,b26SpecSha256:DATA.specSha,startedAt,lockedAt:new Date().toISOString(),primaryPlayback:{rate:1,playsPerClip:2,seeking:false,pausing:false,looping:false},clipResponses,pairResponses,viewing,carrierBindings:DATA.visibleCarriers.map(c=>({label:c.label,sha256:c.sha256}))};const canonical=JSON.stringify(body);const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical)))).map(b=>b.toString(16).padStart(2,'0')).join('');const response={...body,responseHash:hash};locked=true;document.querySelectorAll('button,select,input,textarea').forEach(el=>el.disabled=true);document.getElementById('status').textContent='LOCKED · '+hash;const blob=new Blob([JSON.stringify(response,null,2)+'\\n'],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=DATA.sessionId+'.response.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)});
</script></main></body></html>`;
}

async function validatePackage({
  spec, manifest, sealed, expectedSpecSha, expectedB25Sha, expectedManifestShas,
  expectedFfmpegSha, expectedFfprobeSha, expectedVerifierSha, expectedRunnerSha,
  expectedFirstSourceSha, expectedAlphaOpaque = true, expectedCodec = 'vp9', expectedDecodedFrames = 144,
  expectedExactFrames = 144, expectedCarrierCount = 3, expectedPermutationRepeats = 3,
  expectedOverallCommitment = sealed.overallCommitment, expectedSealedExposure = false,
  expectedFirstSessionId = 'OBS-01', expectedControlsHidden = true, expectedViewingField = 'observerId',
  expectedFormalResponseCount = 0, expectedResponseLockToken = 'responseHash', expectedEarlyUnblind = false,
  expectedHumanStatus = 'PENDING',
}) {
  if (await sha256File(specPath) !== expectedSpecSha) return 'B26_SPEC_SHA';
  if (await sha256File(b25ResultPath) !== expectedB25Sha) return 'B25_RESULT_SHA';
  for (const label of ['A','B','C']) if (await sha256File(resolve(b25Root, `evidence/${label}.manifest.json`)) !== expectedManifestShas[label]) return 'SOURCE_MANIFEST_SHA';
  if (await sha256File(ffmpeg) !== expectedFfmpegSha || await sha256File(ffprobe) !== expectedFfprobeSha) return 'FFMPEG_IDENTITY';
  if (await sha256File(verifier) !== expectedVerifierSha || await sha256File(runner) !== expectedRunnerSha) return 'TOOL_IDENTITY';
  const sourceA = JSON.parse(await readFile(resolve(b25Root, 'evidence/A.manifest.json'), 'utf8'));
  if (sourceA.frames[0].sha256 !== expectedFirstSourceSha || await sha256File(resolve(b25Root, 'work/A', sourceA.frames[0].name)) !== sourceA.frames[0].sha256) return 'SOURCE_FRAME_SHA';
  if (manifest.carriers.some(item => item.roundtrip.allSourceAlphaOpaque !== expectedAlphaOpaque)) return 'SOURCE_ALPHA';
  if (manifest.carriers.some(item => item.metadata.codecName !== expectedCodec || item.metadata.profile !== 'Profile 1' || item.metadata.pixelFormat !== 'gbrp' || item.metadata.width !== 960 || item.metadata.height !== 540 || item.metadata.frameRate !== '24/1' || item.metadata.durationSeconds !== 6)) return 'CARRIER_METADATA';
  if (manifest.carriers.some(item => item.roundtrip.frameCount !== expectedDecodedFrames)) return 'CARRIER_FRAME_COUNT';
  if (manifest.carriers.some(item => item.roundtrip.exactRgbFrames !== expectedExactFrames || item.roundtrip.maximumAbsoluteRgbError !== 0 || item.roundtrip.totalChangedRgbPixels !== 0)) return 'CARRIER_RGB_ROUNDTRIP';
  if (manifest.carriers.length !== expectedCarrierCount || new Set(manifest.carriers.map(item => item.sha256)).size !== 3) return 'CARRIER_SET';
  const counts = Object.fromEntries(spec.blinding.sixOrderPermutations.map(value => [value, sealed.sessions.filter(item => item.permutation === value).length]));
  if (Object.values(counts).some(count => count !== expectedPermutationRepeats) || sealed.sessions.length !== 18) return 'SCHEDULE_BALANCE';
  const sealedBody = { version: sealed.version, sessions: sealed.sessions };
  if (sha256Canonical(sealedBody) !== expectedOverallCommitment || manifest.mappingCommitment !== sealed.overallCommitment) return 'MAPPING_COMMITMENT';
  let exposed = false;
  for (const session of manifest.sessions) {
    const names = await readdir(resolve(sessionRoot, session.sessionId));
    const html = await readFile(resolve(sessionRoot, session.sessionId, 'index.html'), 'utf8');
    if (names.some(name => /mapping|sealed/i.test(name)) || /"underlying"|underlyingLabel|sourceLabel|permutation/i.test(html)) exposed = true;
  }
  if (exposed !== expectedSealedExposure) return 'SEALED_MAPPING_EXPOSURE';
  if (manifest.sessions[0].sessionId !== expectedFirstSessionId) return 'PRIMARY_ORDER_BINDING';
  const firstHtml = await readFile(resolve(sessionRoot, manifest.sessions[0].sessionId, 'index.html'), 'utf8');
  const controlsHidden = !/<video[^>]+controls/i.test(firstHtml) && /plays\[i\]>=2/.test(firstHtml);
  if (controlsHidden !== expectedControlsHidden) return 'PRIMARY_CONTROLS';
  if (!firstHtml.includes(`id="${expectedViewingField}"`)) return 'VIEWING_FIELD';
  if (manifest.humanReview.formalResponseCount !== expectedFormalResponseCount) return 'DEVELOPER_PILOT_COUNTED';
  if (!firstHtml.includes(expectedResponseLockToken) || !firstHtml.includes('lockedAt')) return 'RESPONSE_LOCK';
  const earlyUnblind = /unblind|underlyingLabel|sourceLabel/i.test(firstHtml);
  if (earlyUnblind !== expectedEarlyUnblind) return 'EARLY_UNBLIND';
  if (manifest.humanReview.status !== expectedHumanStatus || manifest.humanReview.formalResponseCount < 15 && expectedHumanStatus !== 'PENDING') return 'HUMAN_GATE';
  return 'OK';
}

await rm(evidenceRoot, { recursive: true, force: true });
await rm(workRoot, { recursive: true, force: true });
await mkdir(evidenceRoot, { recursive: true }); await mkdir(carrierRoot, { recursive: true }); await mkdir(decodedRoot, { recursive: true }); await mkdir(sessionRoot, { recursive: true }); await mkdir(sealedRoot, { recursive: true });
const spec = JSON.parse(await readFile(specPath, 'utf8'));
const specSha = await sha256File(specPath);
if (specSha !== 'e54d72f5f844d1dbc1b95bc6778dc3249762d82e0a936dca44e7ecb231b572d6') throw new Error('B26 spec changed after pre-registration');
const b25 = JSON.parse(await readFile(b25ResultPath, 'utf8'));
if (await sha256File(b25ResultPath) !== spec.evidenceBasis.b25ResultSha256 || b25.decision !== spec.evidenceBasis.b25Decision || b25.humanReview.status !== 'PENDING') throw new Error('B25 evidence basis mismatch');
if (await sha256File(ffmpeg) !== spec.playbackCarrier.ffmpegSha256 || await sha256File(ffprobe) !== spec.playbackCarrier.ffprobeSha256) throw new Error('FFmpeg identity mismatch');
const sourceManifestShas = { A: spec.sourceIdentity.A_manifest_sha256, B: spec.sourceIdentity.B_manifest_sha256, C: spec.sourceIdentity.C_manifest_sha256 };
for (const label of ['A','B','C']) if (await sha256File(resolve(b25Root, `evidence/${label}.manifest.json`)) !== sourceManifestShas[label]) throw new Error(`${label} manifest mismatch`);
const tools = { verifierSha256: await sha256File(verifier), runnerSha256: await sha256File(runner), ffmpegSha256: await sha256File(ffmpeg), ffprobeSha256: await sha256File(ffprobe), blenderSha256: await sha256File(blender) };

const carriers = [];
for (const label of ['A','B','C']) {
  const sourceDir = resolve(b25Root, 'work', label), sourceManifestPath = resolve(b25Root, `evidence/${label}.manifest.json`);
  const carrierPath = resolve(carrierRoot, `${label}.lossless.webm`), decodedDir = resolve(decodedRoot, label), roundtripPath = resolve(evidenceRoot, `${label}.roundtrip.json`);
  await mkdir(decodedDir, { recursive: true });
  await run(ffmpeg, ['-hide_banner','-loglevel','error','-framerate','24','-start_number','1','-i',resolve(sourceDir,'frame-%04d.png'),'-an','-c:v','libvpx-vp9','-lossless','1','-pix_fmt','gbrp','-row-mt','0','-threads','1','-tile-columns','0',carrierPath]);
  await run(ffmpeg, ['-hide_banner','-loglevel','error','-i',carrierPath,'-fps_mode','passthrough',resolve(decodedDir,'frame-%04d.png')]);
  await run(blender, ['--factory-startup','--background','--python-exit-code','1','--python',verifier,'--','--source-dir',sourceDir,'--decoded-dir',decodedDir,'--source-manifest',sourceManifestPath,'--output',roundtripPath]);
  const probed = await run(ffprobe, ['-v','error','-show_entries','format=size,duration,format_name:stream=codec_name,profile,pix_fmt,width,height,r_frame_rate','-of','json',carrierPath]);
  const probe = JSON.parse(probed.output), stream = probe.streams[0], format = probe.format, roundtrip = JSON.parse(await readFile(roundtripPath,'utf8'));
  const carrier = { sourceLabel: label, localUri: repoUri(carrierPath), sha256: await sha256File(carrierPath), bytes: Number(format.size), metadata: { codecName: stream.codec_name, profile: stream.profile, pixelFormat: stream.pix_fmt, width: stream.width, height: stream.height, frameRate: stream.r_frame_rate, durationSeconds: Number(format.duration), container: format.format_name }, roundtrip, roundtripReportUri: repoUri(roundtripPath), roundtripReportSha256: await sha256File(roundtripPath) };
  if (roundtrip.exactRgbFrames !== 144 || !roundtrip.allSourceAlphaOpaque || roundtrip.maximumAbsoluteRgbError !== 0 || roundtrip.totalChangedRgbPixels !== 0) throw new Error(`${label} carrier failed exact roundtrip`);
  carriers.push(carrier); process.stdout.write(`BFS_B26_CARRIER_OK ${label} bytes=${carrier.bytes} sha=${carrier.sha256}\n`);
}

const permutations = spec.blinding.sixOrderPermutations;
const sealedSessions = [], publicSessions = [];
for (let index = 0; index < 18; index += 1) {
  const sessionId = `OBS-${String(index + 1).padStart(2,'0')}`, permutation = permutations[index % permutations.length], salt = randomBytes(32).toString('hex');
  const mapping = permutation.split('').map((sourceLabel, position) => ({ visibleLabel: `CLIP-${String(position + 1).padStart(2,'0')}`, sourceLabel }));
  const commitment = sha256Canonical({ sessionId, salt, mapping });
  sealedSessions.push({ sessionId, salt, permutation, mapping, commitment });
  const dir = resolve(sessionRoot, sessionId); await mkdir(dir, { recursive: true });
  const visibleCarriers = [];
  for (const item of mapping) {
    const source = carriers.find(carrier => carrier.sourceLabel === item.sourceLabel), file = `${item.visibleLabel}.webm`;
    await link(resolve(carrierRoot, `${item.sourceLabel}.lossless.webm`), resolve(dir, file));
    visibleCarriers.push({ label: item.visibleLabel, file, sha256: source.sha256, bytes: source.bytes });
  }
  const html = observerHtml({ sessionId, specSha, visibleCarriers }); await writeFile(resolve(dir,'index.html'), html);
  publicSessions.push({ sessionId, mappingCommitment: commitment, observerPackageUri: repoUri(dir), observerHtmlSha256: digest(html), visibleCarrierBindings: visibleCarriers });
}
const sealedBody = { version: '0.1.0', sessions: sealedSessions }, sealed = { ...sealedBody, overallCommitment: sha256Canonical(sealedBody) };
const sealedPath = resolve(sealedRoot, 'mapping.sealed.json'); await writeFile(sealedPath, serialize(sealed));
const commitmentArtifact = { documentType: 'BFS_B26_MAPPING_COMMITMENT', version: '0.1.0', b26SpecSha256: specSha, overallCommitment: sealed.overallCommitment, sessions: publicSessions.map(({ sessionId, mappingCommitment }) => ({ sessionId, mappingCommitment })), mappingStatus: 'SEALED_UNTIL_RESPONSES_LOCKED' };
const commitmentPath = resolve(evidenceRoot, 'mapping.commitment.json'); await writeFile(commitmentPath, serialize(commitmentArtifact));
const manifest = { documentType: 'BFS_B26_BLIND_REVIEW_PACKAGE', version: '0.1.0', createdAtUtc: new Date().toISOString(), packageStatus: 'CARRIER_AND_INTERFACE_READY', b26SpecSha256: specSha, b25ResultSha256: await sha256File(b25ResultPath), tools, carriers, mappingCommitment: sealed.overallCommitment, mappingStatus: 'SEALED_LOCAL_NOT_PUBLISHED', sessions: publicSessions, humanReview: { status: 'PENDING', formalResponseCount: 0, pilotResponseCount: 0, claim: 'No human response has been collected or inferred.' }, explicitNonClaims: spec.explicitNonClaims };
const manifestPath = resolve(evidenceRoot, 'package.manifest.json'); await writeFile(manifestPath, serialize(manifest));

const expectedManifestShas = { A: spec.sourceIdentity.A_manifest_sha256, B: spec.sourceIdentity.B_manifest_sha256, C: spec.sourceIdentity.C_manifest_sha256 };
const sourceA = JSON.parse(await readFile(resolve(b25Root,'evidence/A.manifest.json'),'utf8'));
const defaults = { spec, manifest, sealed, expectedSpecSha: specSha, expectedB25Sha: spec.evidenceBasis.b25ResultSha256, expectedManifestShas, expectedFfmpegSha: spec.playbackCarrier.ffmpegSha256, expectedFfprobeSha: spec.playbackCarrier.ffprobeSha256, expectedVerifierSha: tools.verifierSha256, expectedRunnerSha: tools.runnerSha256, expectedFirstSourceSha: sourceA.frames[0].sha256 };
const attacks=[]; const attack=(id,expectedReason,observedReason)=>attacks.push({id,expectedReason,observedReason,pass:expectedReason===observedReason});
attack('N_B26_SPEC_SHA','B26_SPEC_SHA',await validatePackage({...defaults,expectedSpecSha:'0'.repeat(64)}));
attack('N_B25_RESULT_SHA','B25_RESULT_SHA',await validatePackage({...defaults,expectedB25Sha:'0'.repeat(64)}));
attack('N_SOURCE_MANIFEST','SOURCE_MANIFEST_SHA',await validatePackage({...defaults,expectedManifestShas:{...expectedManifestShas,A:'0'.repeat(64)}}));
attack('N_FFMPEG_IDENTITY','FFMPEG_IDENTITY',await validatePackage({...defaults,expectedFfmpegSha:'0'.repeat(64)}));
attack('N_TOOL_IDENTITY','TOOL_IDENTITY',await validatePackage({...defaults,expectedVerifierSha:'0'.repeat(64)}));
attack('N_SOURCE_FRAME','SOURCE_FRAME_SHA',await validatePackage({...defaults,expectedFirstSourceSha:'0'.repeat(64)}));
attack('N_SOURCE_ALPHA','SOURCE_ALPHA',await validatePackage({...defaults,expectedAlphaOpaque:false}));
attack('N_CARRIER_METADATA','CARRIER_METADATA',await validatePackage({...defaults,expectedCodec:'h264'}));
attack('N_CARRIER_FRAME_COUNT','CARRIER_FRAME_COUNT',await validatePackage({...defaults,expectedDecodedFrames:143}));
attack('N_RGB_ROUNDTRIP','CARRIER_RGB_ROUNDTRIP',await validatePackage({...defaults,expectedExactFrames:143}));
attack('N_CARRIER_SET','CARRIER_SET',await validatePackage({...defaults,expectedCarrierCount:2}));
attack('N_SCHEDULE_BALANCE','SCHEDULE_BALANCE',await validatePackage({...defaults,expectedPermutationRepeats:2}));
attack('N_MAPPING_COMMITMENT','MAPPING_COMMITMENT',await validatePackage({...defaults,expectedOverallCommitment:'0'.repeat(64)}));
attack('N_SEALED_EXPOSURE','SEALED_MAPPING_EXPOSURE',await validatePackage({...defaults,expectedSealedExposure:true}));
attack('N_PRIMARY_ORDER','PRIMARY_ORDER_BINDING',await validatePackage({...defaults,expectedFirstSessionId:'OBS-99'}));
attack('N_PRIMARY_CONTROLS','PRIMARY_CONTROLS',await validatePackage({...defaults,expectedControlsHidden:false}));
attack('N_VIEWING_FIELD','VIEWING_FIELD',await validatePackage({...defaults,expectedViewingField:'missing-required-field'}));
attack('N_DEVELOPER_COUNT','DEVELOPER_PILOT_COUNTED',await validatePackage({...defaults,expectedFormalResponseCount:1}));
attack('N_RESPONSE_LOCK','RESPONSE_LOCK',await validatePackage({...defaults,expectedResponseLockToken:'missing-lock-token'}));
attack('N_EARLY_UNBLIND','EARLY_UNBLIND',await validatePackage({...defaults,expectedEarlyUnblind:true}));
const validPackage = attacks.length === 20 && attacks.every(item=>item.pass) && await validatePackage(defaults) === 'OK';
const result = { documentType:'BFS_B26_BLIND_TEMPORAL_REVIEW_PACKAGE_RESULT',version:'0.1.0',executedAtUtc:new Date().toISOString(),packageStatus:validPackage?'CARRIER_AND_INTERFACE_READY':'INVALID_PACKAGE',validPackage,humanReview:{status:'PENDING',formalResponseCount:0,pilotResponseCount:0,decision:null},identities:{b26SpecSha256:specSha,b25ResultSha256:await sha256File(b25ResultPath),...tools},carrierSummary:{count:carriers.length,totalBytes:carriers.reduce((sum,item)=>sum+item.bytes,0),all144FrameRgbExact:carriers.every(item=>item.roundtrip.exactRgbFrames===144),allSourceAlphaOpaque:carriers.every(item=>item.roundtrip.allSourceAlphaOpaque),maximumAbsoluteRgbError:Math.max(...carriers.map(item=>item.roundtrip.maximumAbsoluteRgbError)),totalChangedRgbPixels:carriers.reduce((sum,item)=>sum+item.roundtrip.totalChangedRgbPixels,0)},schedule:{formalTarget:18,permutations:6,repetitionsPerPermutation:3,overallCommitment:sealed.overallCommitment,mappingStatus:'SEALED_LOCAL_NOT_PUBLISHED'},attacks,artifacts:{packageManifest:repoUri(manifestPath),mappingCommitment:repoUri(commitmentPath),roundtripReports:Object.fromEntries(carriers.map(item=>[item.sourceLabel,item.roundtripReportUri])),localObserverSessions:repoUri(sessionRoot)},nonClaims:spec.explicitNonClaims };
await writeFile(resolve(root,'results.json'),serialize(result));
process.stdout.write(`BFS_B26_PACKAGE ${result.packageStatus} carriers=${carriers.length} rgbExact=${result.carrierSummary.all144FrameRgbExact} attacks=${attacks.filter(item=>item.pass).length}/20 human=${result.humanReview.status}\n`);
if(!validPackage) process.exitCode=1;
