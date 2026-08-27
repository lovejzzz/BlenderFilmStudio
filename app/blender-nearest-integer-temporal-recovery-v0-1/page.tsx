import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'B52-D11.1 有界整数运动恢复｜Blender Film Studio',
  description: '81 个唯一进程、32 次真实 Blender 5.2 render：双实现有界 nearest-integer quantizer 修复 D11 的向零截断反例，71/71 attacks 与独立重放审计通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-nearest-integer-temporal-recovery-v0-1/' },
};

const commit = '07cca8aeff7b8d38ec37408efa419863d0940aeb';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const raw = `https://raw.githubusercontent.com/lovejzzz/BlenderFilmStudio/${commit}/experiments/blender-nearest-integer-temporal-recovery-holdout-v0-1/diagnostics`;

const rows = [
  ['OBJECT OCCLUSION', '20,763 / 928', '397', '7.629e−6 px', 'LAYER'],
  ['CAMERA BOUNDS', '18,042 / 3,649', '661', '7.629e−6 px', 'BOUNDS'],
  ['SAME-ID DEPTH', '20,831 / 860', '359', '7.629e−6 px', 'DEPTH'],
  ['STATIC CONTROL', '21,691 / 0', '0', '0 px', 'ALL VALID'],
];

const gallery = [
  ['QUANTIZED_OCCLUSION_OBJECT_XY_199X109', 'OBJECT OCCLUSION'],
  ['QUANTIZED_CAMERA_BOUNDS_199X109', 'CAMERA BOUNDS'],
  ['QUANTIZED_SAME_ID_DEPTH_DISCLOSURE_199X109', 'SAME-ID DEPTH'],
  ['QUANTIZED_TEXTURED_STATIC_CONTROL_199X109', 'STATIC CONTROL'],
];

const views = [
  ['rawMotionMagnitude', 'RAW MOTION'],
  ['quantizationError', 'QUANTIZATION ERROR'],
  ['truncationRecovery', 'RECOVERED PIXELS'],
  ['historyValidity', 'HISTORY VALIDITY'],
  ['resolved', 'RESOLVED'],
];

export default function BlenderNearestIntegerTemporalRecoveryPage() {
  return <main className="contact-page b51-page b52-page d11-page d111-page">
    <header className="topbar">
      <a className="brand" href="../"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></a>
      <nav aria-label="D11.1 导航"><a href="../blender-temporal-composition-v0-1/">D11 反例</a><a href="#contract">量化合同</a><a href="#matrix">实测矩阵</a><a href="#evidence">诊断图</a><a href="#audit">审计</a><a href="../journal/">日志</a></nav>
      <span className="edition contact-edition">Temporal Recovery D11.1</span>
    </header>

    <section className="contact-hero b52-hero d111-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D11.1 · BOUNDED INTEGER-MOTION RECOVERY</p><h1>不是随便四舍五入。<br/><span>只接纳可证明的近整数。</span></h1><p>D11 的负面结果保持不变。新合同在 raw Vector 与原累积器之间加入 whole-array nearest-integer quantizer；四个全新 textured fixtures、Python/Node 双实现和真实 Blender Raw EXR bridge 共同通过。</p></div>
      <aside className="contact-gate d111-gate"><b>SCIENTIFIC VERDICT</b><strong>SUPPORTED<br/>BOUNDED</strong><code>radius ≤ 1 / 1024 px</code><code>C2 audit PASS</code><small>not arbitrary float motion</small></aside>
      <div className="contact-stats"><article><strong>81 / 81</strong><span>formal child PIDs</span><small>all unique</small></article><article><strong>32</strong><span>Blender renders</span><small>16 Cycles + 16 bridge</small></article><article><strong>71 / 71</strong><span>registered attacks</span><small>all rejected</small></article><article><strong>0</strong><span>bridge scalar changes</span><small>16 / 16 decoded exact</small></article></div>
    </section>

    <section className="section d111-contract" id="contract">
      <div className="section-index">00 / EXPLICIT DOMAIN CONTRACT</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> ACCEPT OR REJECT THE COMPLETE ARRAY</p><h2>量化器不是模糊补丁。<br/><span>它有不可越过的定义域。</span></h2></div><p>每个输入先按 half-away-from-zero 求最近整数候选；只有全部 finite float32 分量都距离候选不超过冻结半径，整个数组才会输出。任一分量越界、半整数、NaN 或 infinity，完整数组拒绝且无 payload。</p></div>
      <div className="d111-formula"><article><span>CANDIDATE</span><code>n(v) = v ≥ 0 ? floor(v + 0.5)<br/>: ceil(v − 0.5)</code><small>language-independent</small></article><i>+</i><article className="accept"><span>DOMAIN</span><code>finite(v) ∧ |v − n(v)| ≤ 1/1024</code><small>inclusive · per component</small></article><i>→</i><article><span>OUTPUT</span><code>exact integral float32<br/>zero → +0.0 bytes</code><small>whole-array atomic</small></article></div>
      <div className="d111-boundary"><article><b>允许</b><span>nearest integer</span><span>idempotence</span><span>positive zero</span><span>Python = Node bytes</span></article><article><b>禁止</b><span>clamping</span><span>partial output</span><span>fixture lookup</span><span>radius widening</span></article></div>
    </section>

    <section className="section d111-matrix" id="matrix">
      <div className="section-index">01 / FRESH REAL-BLENDER HOLDOUT</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FOUR FIXTURES · TWO SOURCE REPEATS</p><h2>三类错误被恢复。<br/><span>三类历史仍被拒绝。</span></h2></div><p>“恢复像素”是如果继续沿用 D11 向零截断就会选择相邻整数的坐标。量化之后，运动 owner interior 与解析整数真值一致；layer、bounds 与 same-ID depth rejection 仍按原语义生效。</p></div>
      <div className="d11-table d111-table"><div className="head"><b>FIXTURE</b><b>VALID / INVALID</b><b>RECOVERED / REPEAT</b><b>MAX Q ERROR</b><b>REJECTION</b></div>{rows.map(row=><div className="row" key={row[0]}>{row.map((value,index)=>index===0?<strong key={value}>{value}</strong>:<code key={index}>{value}</code>)}</div>)}</div>
      <div className="d111-process"><article><span>01</span><strong>16</strong><b>CYCLES SOURCES</b><small>real textured multipart</small></article><i>→</i><article><span>02</span><strong>8 + 8</strong><b>PY / NODE Q</b><small>byte-identical motion</small></article><i>→</i><article><span>03</span><strong>8 + 8</strong><b>ACCUMULATORS</b><small>truncation now identity</small></article><i>→</i><article><span>04</span><strong>16</strong><b>BLENDER BRIDGES</b><small>zero changed scalars</small></article></div>
    </section>

    <section className="section d111-evidence" id="evidence">
      <div className="section-index">02 / FORMAL DIAGNOSTIC IMAGES</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> MOTION · ERROR · RECOVERY · VALIDITY · RESOLVED</p><h2>恢复发生在哪里，<br/><span>拒绝又发生在哪里。</span></h2></div><p>二十张 PNG 固定来自正式证据提交 `{commit.slice(0,7)}`，只承担空间定位。判定本身来自 raw float32/u8 arrays、解析 probe、双实现 bytes 和独立 replay；图像不能代替数值门。</p></div>
      <div className="d11-gallery d111-gallery">{gallery.map(([slug,label])=><article key={slug}><header><b>{label}</b><span>199 × 109 · FORMAL</span></header><div>{views.map(([view,caption])=><figure key={view}><img src={`${raw}/${slug}/${view}.png`} width="199" height="109" alt={`${label} ${caption}`}/><figcaption>{caption}</figcaption></figure>)}</div></article>)}</div>
    </section>

    <section className="section d111-audit" id="audit">
      <div className="section-index">03 / CORRECTION-PROVENANCE CHAIN</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> FAILED AUDITS STAY VISIBLE</p><h2>正式结果没有重跑。<br/><span>审计工具修了两次。</span></h2></div><p>原 audit 在完成重放后因 NumPy `bool_` 无法 JSON 序列化而崩溃；C1 加入 native bool cast，却被自身错误的 65 字符 receipt hash guard 拒绝；预注册的 C2 只修正该 literal 与 provenance，最终独立通过。</p></div>
      <div className="d111-corrections"><article className="fail"><span>ORIGINAL</span><strong>NO JSON</strong><b>NumPy bool_ serialization</b><small>formal files unchanged</small></article><article className="fail"><span>C1</span><strong>REJECTED</strong><b>65-character hash literal</b><small>stopped before replay</small></article><article className="pass"><span>C2</span><strong>PASS</strong><b>8 / 8 cells replayed</b><small>14 gates · 71 attacks</small></article></div>
      <div className="contact-nonclaim"><b>SUPPORTED ≠ GENERAL TEMPORAL RECONSTRUCTION</b><p>本实验没有验证 perspective、subpixel、deformation、transparency、volumes、hair、motion blur、depth of field、Cryptomatte coverage 或多人可见质量。下一步必须另建 perspective/subpixel reconstruction contract；不能扩大 rounding radius。</p></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-nearest-integer-temporal-recovery-holdout-v0-1/results.json`}><span>MACHINE RESULT</span><b>SUPPORTED · 71 / 71 ↗</b></a><a href={`${repo}experiments/blender-nearest-integer-temporal-recovery-holdout-v0-1/audit.json`}><span>C2 AUDIT</span><b>PASS · 8 / 8 replay ↗</b></a><a href={`${repo}research/2026-08-27-b52-d11-1-nearest-integer-temporal-recovery-holdout-result.md`}><span>RESULT NOTE</span><b>claims · corrections · limits ↗</b></a><a href={`${repo}specs/blender-nearest-integer-temporal-recovery-holdout.v0.1.json`}><span>FROZEN SPEC</span><b>radius · attacks · gates ↗</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D11.1 Temporal Recovery Research</b></div><p>bounded integer motion supported · perspective/subpixel open</p><a href="../journal/">继续看实验日志 →</a></footer>
  </main>;
}
