import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const mediaBase = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio/eevee-process-history-isolation-v0-1' : '/eevee-process-history-isolation-v0-1';
export const metadata: Metadata = {
  title: 'B20 Eevee 进程历史隔离｜Blender Film Studio',
  description: '真实 Blender 39 个唯一 PID、468 帧：每帧新进程仍只有 26/36 哨兵配对 exact，进程隔离不是充分修复；18/18 攻击通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/eevee-process-history-isolation-v0-1/' },
};

const attacks = [
  ['N01','B20 spec','B20_SPEC_SHA'],['N02','ReviewRenderSpec','REVIEW_SPEC_SHA'],['N03','Blender binary','BLENDER_SHA'],['N04','OCIO config','OCIO_SHA'],
  ['N05','source .blend','SCENE_SHA'],['N06','renderer','RENDERER_SHA'],['N07','configurator','CONFIGURATOR_SHA'],['N08','render samples','RENDER_SAMPLES'],
  ['N09','fixed dither','FIXED_DITHER'],['N10','Fast GI','FAST_GI'],['N11','reprojection','TAA_REPROJECTION'],['N12','history order','FRAME_SCHEDULE'],
  ['N13','fresh scope','FRAME_COUNT'],['N14','process alias','PROCESS_ALIAS'],['N15','missing sentinel','MISSING_SENTINEL'],['N16','mutated sentinel','IMAGE_SHA'],
  ['N17','comparison binding','COMPARISON_MANIFEST_BINDING'],['N18','comparator','COMPARATOR_SHA'],
];
const freshFrames = [
  ['001','1','3/3','0'],['002','5','1/3','10'],['003','20','3/3','0'],['004','35','1/3','16'],
  ['005','38','3/3','0'],['006','47','1/3','6'],['007','83','3/3','0'],['008','93','3/3','0'],
  ['009','103','1/3','14'],['010','110','1/3','10'],['011','114','3/3','0'],['012','144','3/3','0'],
];

export default function ProcessHistoryIsolationPage() {
  return <main className="contact-page factorial-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B20 导航"><Link href="/journal">实验日志</Link><Link href="/eevee-gi-reprojection-factorial-v0-1">B19</Link><a href="#modes">模式</a><a href="#frames">哨兵</a><a href="#evidence">画面</a><a href="#next">下一边界</a></nav><span className="edition contact-edition">Process History 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B20 · 39 REAL BLENDER PROCESSES</p><h1>每一帧都重启。<br /><span>漂移仍然存在。</span></h1><p>三条完整 HISTORY 序列，对照 36 次“一帧一进程”的 FRESH 渲染。39 个 PID 全部唯一，固定 32 samples、dither 0、Fast GI on、temporal on。</p></div><aside className="contact-gate"><b>PRE-REGISTERED DECISION</b><strong>ISOLATION NOT<br />SUFFICIENT</strong><code>history · 18 / 36</code><code>fresh · 26 / 36</code><small>18 / 18 ATTACKS PASS</small></aside><div className="contact-stats"><article><strong>39/39</strong><span>唯一 PID</span><small>no process alias</small></article><article><strong>468</strong><span>真实渲染帧</span><small>3×144 + 36</small></article><article><strong>12</strong><span>预注册哨兵</span><small>mechanical selection</small></article><article><strong>18/18</strong><span>负向攻击</span><small>stable reasons</small></article></div></section>

    <section className="section contact-verdict" id="modes"><div className="section-index">00 / 两种模式</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> THREE REPLICATES · ALL PAIRS · ZERO TOLERANCE</p><h2>新进程减少了差异，<br /><span>但没有通过门。</span></h2></div><p>每种模式的 A-B、A-C、B-C 都对 12 个哨兵逐像素比较。预注册要求 36/36 才通过；26/36 不能在结果出来后改写成“足够稳定”。</p></div><div className="factorial-matrix"><article className="factorial-nonexact"><span>HISTORY</span><strong>18/36</strong><b>3 × full 1–144</b><small>118 failed pixels</small></article><article className="factorial-nonexact"><span>FRESH</span><strong>26/36</strong><b>one frame · one PID</b><small>56 failed pixels</small></article><article className="factorial-nonexact"><span>CROSS MODE</span><strong>61/108</strong><b>all 3 × 3 pairs</b><small>320 failed pixels</small></article><article className="factorial-exact"><span>PROCESS GATE</span><strong>39/39</strong><b>distinct observed PIDs</b><small>468 frames complete</small></article></div><div className="diagnostic-verdict"><b>DECISION</b><code>PROCESS_ISOLATION_NOT_SUFFICIENT</code><p>FRESH 的计数更好只是描述性观察。三重复不能估计可靠失配率；实验只否定“每帧新进程足以保证 strict exact”。</p></div></section>

    <section className="section contact-evidence" id="frames"><div className="section-index light">01 / FRESH 帧级审计</div><div className="contact-heading"><div><p className="eyebrow"><span /> EACH FRAME · THREE FRESH PROCESSES</p><h2>七个帧全相同。<br /><span>五个帧仍然分裂。</span></h2></div><p>哨兵不是看完 B20 才挑：frame 1 是启动锚点，其余来自七个既有 32-sample/dither-zero 比较中至少四次失败的全部帧。</p></div><ol className="contact-negative-list">{freshFrames.map(([id,frame,exact,failed]) => <li key={id}><span>{id}</span><b>frame {frame}</b><code>{exact} pairs exact</code><small>{failed} failed pixels</small></li>)}</ol><div className="contact-nonclaim"><b>IMPORTANT</b><p>FRESH 的失败帧 5、35、47、103、110 都呈“两份相同、一份不同”。这说明重启并未固定所有采样结果；但它仍不等于源码级 GPU race 证明。</p></div></section>

    <section className="section contact-limits" id="evidence"><div className="section-index">02 / 真实画面 witness</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FRAME 110 · FRESH A VS FRESH C</p><h2>肉眼看不出五个像素。<br /><span>机器门仍能拒绝。</span></h2></div><p>两张图来自两个不同 Blender PID。OIIO 解码后有 5 个像素失败，最大通道误差约 1/255。单张 witness 不替代 36 个 primary comparisons。</p></div><div className="factorial-gallery"><figure><Image src={`${mediaBase}/F-A-frame-0110.png`} alt="B20 FRESH A 第110帧，独立 Blender 进程" width={960} height={540} sizes="(max-width: 700px) 100vw, 50vw" /><figcaption><span>F-A · FRAME 0110</span><b>fresh Blender PID 59734</b><small>matches F-B exactly</small></figcaption></figure><figure><Image src={`${mediaBase}/F-C-frame-0110.png`} alt="B20 FRESH C 第110帧，另一个独立 Blender 进程" width={960} height={540} sizes="(max-width: 700px) 100vw, 50vw" /><figcaption><span>F-C · FRAME 0110</span><b>fresh Blender PID 59835</b><small>5 pixels differ from F-A</small></figcaption></figure></div></section>

    <section className="section contact-diagnostic"><div className="section-index">03 / 对抗验证</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> EIGHTEEN STABLE REASONS</p><h2>进程边界也要，<br /><span>成为可审计证据。</span></h2></div><p>除了输入与工具身份，B20 明确攻击 PID 别名、完整历史帧序、单帧 scope、哨兵文件和 manifest 比较绑定。</p></div><ol className="contact-negative-list">{attacks.map(([id,item,result]) => <li key={id}><span>{id}</span><b>{item}</b><small>{result}</small></li>)}</ol></section>

    <section className="section contact-limits" id="next"><div className="section-index">04 / B21 后续证据</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> EXR32 NON-EXACT · PNG NOT THE ORIGIN</p><h2>Float 已经变化，<br /><span>下一步查求值并发。</span></h2></div><p>B21 从同一 Render Result 保存 EXR32 与 PNG8；两者均 21/36 exact，且 36 个 pair 标签逐一相同。输出量化不是起点，下一候选是 fixed threads 1×8。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/eevee-process-history-isolation-v0-1/results.json`}><span>RESULT</span><b>39 PIDs · 18 attacks ↗</b></a><a href={`${repo}research/2026-08-26-b20-eevee-process-history-isolation-result.md`}><span>RESULT NOTE</span><b>frame-level audit ↗</b></a><Link href="/dual-output-localization-v0-1"><span>B21</span><b>EXR / PNG localization →</b></Link><a href={`${repo}experiments/eevee-process-history-isolation-v0-1/evidence/process-ledger.json`}><span>PROCESS LEDGER</span><b>39 unique PIDs ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B20 Process History Isolation</b></div><p>Per-frame restart falsified as a sufficient fix</p><Link href="/research-agenda">进入 float-buffer 边界 →</Link></footer>
  </main>;
}
