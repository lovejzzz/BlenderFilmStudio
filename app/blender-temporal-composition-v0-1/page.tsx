import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'B52-D11 真实 Blender 时序组合反例｜Blender Film Studio',
  description: '65 个唯一进程证明真实 Blender pass、双累积器与 Raw EXR bridge 可以逐段复现，但向零截断会把近整数运动变成一像素错误。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-temporal-composition-v0-1/' },
};

const commit = 'ae3a894cc20477949221760f4831ca5797623706';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const evidence = `https://raw.githubusercontent.com/lovejzzz/BlenderFilmStudio/${commit}/experiments/blender-real-textured-temporal-end-to-end-holdout-v0-1/diagnostics`;

const rows = [
  ['OBJECT OCCLUSION', '1,120', '211 / 211', '87 / 87', '21,668'],
  ['CAMERA BOUNDS', '21,645', '449 / 449', '318 / 318', '19,530'],
  ['SAME-ID DEPTH', '1,120', '86 / 86', '129 / 129', '21,643'],
  ['STATIC CONTROL', '21,645', '0 / 0', '0 / 0', '22,261'],
];

const gallery = [
  ['REAL_OCCLUSION_DISOCCLUSION_OBJECT_XY_197X113', 'OBJECT OCCLUSION'],
  ['REAL_CAMERA_BOUNDS_197X113', 'CAMERA BOUNDS'],
  ['REAL_SAME_ID_DEPTH_DISCLOSURE_197X113', 'SAME-ID DEPTH'],
];

const views = [
  ['currentCombined', 'CURRENT'],
  ['truncatedMotionError', 'TRUNCATION ERROR'],
  ['validityReason', 'VALIDITY REASON'],
  ['resolved', 'RESOLVED'],
];

export default function BlenderTemporalCompositionPage() {
  return <main className="contact-page b51-page b52-page d11-page">
    <header className="topbar">
      <a className="brand" href="../"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></a>
      <nav aria-label="D11 导航"><a href="../blender-pass-adapter-v0-1/">D10.1 Adapter</a><a href="#failure">反例</a><a href="#matrix">矩阵</a><a href="#evidence">诊断图</a><a href="#next">D11.1</a><a href="../journal/">日志</a></nav>
      <span className="edition contact-edition">Temporal Composition D11</span>
    </header>

    <section className="contact-hero b52-hero d11-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D11 · REAL TEXTURED END-TO-END</p><h1>每一段都对。<br/><span>组合却错一像素。</span></h1><p>真实 Blender 5.2 textured multipart EXR 进入 pass adapter、Python/Node 时序累积器、Raw float32 EXR 和 Blender compositor。所有接口与重放门通过，但近整数 Vector 被向零截断，整条未修改 workflow 因此不获支持。</p></div>
      <aside className="contact-gate d11-gate"><b>SCIENTIFIC VERDICT</b><strong>NOT<br/>SUPPORTED</strong><code>MOTION_INTEGERIZATION</code><code>audit PASS</code><small>negative result retained</small></aside>
      <div className="contact-stats"><article><strong>65 / 65</strong><span>formal child PIDs</span><small>all unique</small></article><article><strong>32</strong><span>Blender renders</span><small>16 Cycles + 16 compositor</small></article><article><strong>56 / 56</strong><span>registered attacks</span><small>all executed</small></article><article><strong>1,492</strong><span>owner-interior misses</span><small>two clean repeats</small></article></div>
    </section>

    <section className="section d11-failure" id="failure">
      <div className="section-index">00 / COMPOSITION COUNTEREXAMPLE</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> SUBPIXEL TOLERANCE ≠ INTEGER SAFETY</p><h2>误差只有十万分之一像素。<br/><span>整数坐标却会错一整格。</span></h2></div><p>Vector 的最大 endpoint error 只有 1.079e−5 px，远低于 D10.1 门槛。但 `int()` / `Math.trunc()` 面对略低于整数的 float32 会向零跨过整数边界。D11 在看结果前明确冻结了这个风险，所以最近整数对照不能用于修复正式结论。</p></div>
      <div className="d11-numberline"><article><span>RAW BLENDER F32</span><code>12.999996185302734</code><small>inside endpoint tolerance</small></article><i>→</i><article className="bad"><span>TRUNCATE TOWARD ZERO</span><code>12</code><small>formal inherited path</small></article><i>≠</i><article className="good"><span>ANALYTIC INTEGER</span><code>13</code><small>one full pixel apart</small></article></div>
      <div className="contact-nonclaim"><b>AUDIT PASS ≠ WORKFLOW PASS</b><p>独立 audit 的 PASS 只说明负面结论可重放、证据完整。正式 verdict 仍是 NOT_SUPPORTED；D8、D9.1、D10.1 的窄合同各自保留，但不能据此宣称未修改组合可用。</p></div>
    </section>

    <section className="section d11-matrix" id="matrix">
      <div className="section-index">01 / FROZEN MATRIX</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FOUR FIXTURES · TWO CLEAN REPEATS</p><h2>反例不是边缘偶发。<br/><span>三类运动都稳定复现。</span></h2></div><p>表中 mismatch 只统计 preregistered moving-owner interior，不把背景或边缘混入。静态控制完全通过，说明问题来自运动整数化而非通用 EXR、ownership、depth 或 compositor 破坏。</p></div>
      <div className="d11-table"><div className="head"><b>FIXTURE</b><b>OWNER INTERIOR</b><b>MISMATCH R1 / R2</b><b>ROUND Δ SCALARS</b><b>VALID PIXELS</b></div>{rows.map(row=><div className="row" key={row[0]}>{row.map((value,index)=>index===0?<strong key={value}>{value}</strong>:<code key={index}>{value}</code>)}</div>)}</div>
      <div className="d11-chain"><article><span>01</span><b>REAL MULTIPART</b><small>repeat exact</small></article><i>→</i><article><span>02</span><b>RAW ADAPTER</b><small>7 arrays exact</small></article><i>→</i><article className="failed"><span>03</span><b>TRUNCATION</b><small>first failed gate</small></article><i>→</i><article><span>04</span><b>RAW EXR BRIDGE</b><small>decoded exact</small></article></div>
    </section>

    <section className="section d11-evidence" id="evidence">
      <div className="section-index">02 / FIXED DIAGNOSTICS</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> CURRENT · ERROR · REASON · RESOLVED</p><h2>一像素错误的位置，<br/><span>可以被直接定位。</span></h2></div><p>十二张图固定来自正式提交 `{commit.slice(0,7)}`。PNG 只用于定位，正式判定来自 float32 arrays、解析 owner-interior mask、双实现逐字节对照与独立重放。</p></div>
      <div className="d11-gallery">{gallery.map(([slug,label])=><article key={slug}><header><b>{label}</b><span>197 × 113 · FORMAL</span></header><div>{views.map(([view,caption])=><figure key={view}><img src={`${evidence}/${slug}/${view}.png`} width="197" height="113" alt={`${label} ${caption}`}/><figcaption>{caption}</figcaption></figure>)}</div></article>)}</div>
    </section>

    <section className="section contact-limits b51-next" id="next">
      <div className="section-index">03 / ONLY PERMITTED RECOVERY</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> B52-D11.1 · FRESH QUANTIZER HOLDOUT</p><h2>不改 D11。<br/><span>新实验显式加入 quantizer。</span></h2></div><p>D11 的失败路径保持冻结。D11.1 已在 raw adapter 和 integer accumulator 之间插入声明过的 bounded nearest-integer quantizer，并用全新 resolution、几何、IDs 与轨迹通过 clean holdout；它不追认未修改路径。</p></div>
      <div className="b51-next-flow"><article><span>01</span><b>RAW VECTOR F32</b><p>D10.1 extraction</p></article><i>→</i><article><span>02</span><b>NEAREST INTEGER</b><p>new explicit contract</p></article><i>→</i><article><span>03</span><b>D9.1 ACCUMULATOR</b><p>unchanged integer lookup</p></article><i>→</i><article><span>04</span><b>FRESH HOLDOUT</b><p>new fixtures · attacks</p></article></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-real-textured-temporal-end-to-end-holdout-v0-1/results.json`}><span>D11 MACHINE RESULT</span><b>NOT SUPPORTED · 56 / 56 ↗</b></a><a href={`${repo}experiments/blender-real-textured-temporal-end-to-end-holdout-v0-1/audit.json`}><span>D11 AUDIT</span><b>PASS · negative reproduced ↗</b></a><a href={`${repo}research/2026-08-27-b52-d11-blender-real-textured-temporal-end-to-end-result.md`}><span>RESULT NOTE</span><b>1,492 owner-interior misses ↗</b></a><a href="../blender-nearest-integer-temporal-recovery-v0-1/"><span>D11.1 RECOVERY</span><b>SUPPORTED · bounded domain →</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D11 Temporal Composition Research</b></div><p>interfaces exact · composition rejected · D11.1 bounded recovery supported</p><a href="../blender-nearest-integer-temporal-recovery-v0-1/">查看 D11.1 恢复实验 →</a></footer>
  </main>;
}
