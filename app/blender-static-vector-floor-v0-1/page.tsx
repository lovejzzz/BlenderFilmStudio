import type { Metadata } from 'next';
import Link from 'next/link';
import type { CSSProperties } from 'react';

export const metadata: Metadata = {
  title: 'B52-D12.2 静态 Vector 浮点底噪｜Blender Film Studio',
  description: '55 个唯一进程、12 次真实 Blender 5.2 render：静态绝对零被反驳，注册容差与三层跨语言证据合同通过 24/24 攻击。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-static-vector-floor-v0-1/' },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

const measurements = [
  ['STATIC WIDE', '83×53', '3,375', '7.629e−6 px', '8.941e−8', '3.735e−9'],
  ['STATIC TELE', '113×71', '6,615', '1.526e−5 px', '1.192e−7', '1.776e−8'],
  ['STATIC NORMAL', '127×79', '8,449', '2.289e−5 px', '1.788e−7', '2.066e−8'],
];

export default function BlenderStaticVectorFloorPage() {
  return <main className="contact-page b51-page b52-page d11-page d111-page d12p-page d122-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.2 导航"><Link href="/blender-projective-subpixel-reconstruction-v0-1">D12 反例</Link><a href="#verdict">结论</a><a href="#floor">浮点底噪</a><a href="#identity">三层证据</a><Link href="/journal">日志</Link></nav>
      <span className="edition contact-edition">Static Floor D12.2</span>
    </header>

    <section className="contact-hero d111-hero d122-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D12.2 · REAL BLENDER 5.2 HOLDOUT</p><h1>静止不是<span>绝对零。</span><br/>但它可以被<span>严格约束。</span></h1><p>三个全新静态透视场景、双语言消费者与独立判决器完成。工程容差通过；“静止 Vector 必须等于零”被六个真实单元一致反驳。</p></div>
      <aside className="contact-gate d111-gate d122-gate"><b>FORMAL VERDICT</b><strong>WITHIN<br/>TOLERANCE</strong><code>exact zero · falsified</code><code>24 / 24 attacks</code><small>three-layer evidence passed</small></aside>
      <div className="contact-stats"><article><strong>55 / 55</strong><span>formal child PIDs</span><small>all unique</small></article><article><strong>12</strong><span>Blender renders</span><small>Cycles · CPU · 1 spp</small></article><article><strong>6 / 6</strong><span>payload pairs exact</span><small>Python = Node bytes</small></article><article><strong>12 / 12</strong><span>document envelopes</span><small>dual encoders exact</small></article></div>
    </section>

    <section className="section d122-verdict" id="verdict">
      <div className="section-index">00 / TWO CLAIMS, TWO ANSWERS</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> TOLERANCE PASS · ZERO FAIL</p><h2>不把小误差说成零。<br/><span>也不把浮点底噪说成失败。</span></h2></div><p>前后帧 Beauty 数组完全相同，证明场景确实静止；但 Vector 仍留下可重复的非零残差。预注册把“工程容差”和“数学绝对零”分成两个命题，因此结果无需事后改门槛。</p></div>
      <div className="d12p-failures d122-dual"><article className="pass"><span>ENGINEERING BOUND</span><strong>PASS</strong><b>max Vector ≤ 1/4096 px</b><p>最坏单元仍保留约 10.67× 裕量。</p></article><article className="static"><span>EXACT-ZERO CLAIM</span><strong>FALSE</strong><b>6 / 6 cells nonzero</b><p>静止 Vector 与 bilinear 重建误差均非零。</p></article><article><span>STATIC SOURCE CONTROL</span><strong>EXACT</strong><b>previous RGB = current RGB</b><p>差异来自 Vector/采样数值路径，不是 Beauty 漂移。</p></article></div>
    </section>

    <section className="section d12p-matrix d122-floor" id="floor">
      <div className="section-index">01 / MEASURED FLOATING FLOOR</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> THREE FRESH OPTICAL CONFIGURATIONS</p><h2>残差随配置变化，<br/><span>重复却完全一致。</span></h2></div><p>每个场景跑两次。表内数值为两次一致的独立结果；观察到的 Vector 最大值形成 1×、2×、3× 2⁻¹⁷ px，但这只是测量模式，不是 Blender 内部实现结论。</p></div>
      <div className="d12p-table d122-table"><div className="head"><b>FIXTURE</b><b>RASTER</b><b>VALID PX</b><b>VECTOR MAX</b><b>RGB MAX</b><b>RGB RMSE</b></div>{measurements.map(row => <div className="row" key={row[0]}>{row.map((cell, index) => index === 0 ? <strong key={cell}>{cell}</strong> : <code key={cell}>{cell}</code>)}</div>)}</div>
      <div className="d122-scale" aria-label="静态 Vector 最大残差相对量级"><article><span>WIDE</span><i style={{'--level': '33.333%'} as CSSProperties}/><code>1 × 2⁻¹⁷</code></article><article><span>TELE</span><i style={{'--level': '66.667%'} as CSSProperties}/><code>2 × 2⁻¹⁷</code></article><article><span>NORMAL</span><i style={{'--level': '100%'} as CSSProperties}/><code>3 × 2⁻¹⁷</code></article></div>
    </section>

    <section className="section d122-identity" id="identity">
      <div className="section-index">02 / THREE-LAYER EVIDENCE</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> SEPARATE WHAT MUST NOT BE CONFLATED</p><h2>数组、文档、判决，<br/><span>分别验证。</span></h2></div><p>D12.1 已证明：即使底层 float32 数组完全相同，Python 与 JavaScript 的 reduction 也可能相差一个 ULP。D12.2 因此让 producer 不输出判决指标。</p></div>
      <div className="d111-process d122-layers"><article><span>01 · PAYLOAD</span><strong>6 / 6</strong><b>Python = Node bytes</b><small>RGBA reconstruction + valid mask</small></article><i>→</i><article><span>02 · DOCUMENT</span><strong>12 / 12</strong><b>dual typed envelopes</b><small>same report, same normalized bytes</small></article><i>→</i><article><span>03 · DECISION</span><strong>24 / 24</strong><b>independent analyzer attacks</b><small>metrics recomputed from payloads</small></article></div>
      <div className="contact-nonclaim"><b>BOUNDARY</b><p>本结果只覆盖冻结的 Blender 5.2 / Cycles / 不透明刚性平面静态场景。它没有覆盖非平面几何、多主体边界、透明、形变、遮挡显露，也不是感知或电影感结论。下一道门是非平面 + 多 owner 静态 holdout。</p></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-static-vector-floor-three-layer-evidence-holdout-v0-1/results.json`}><span>MACHINE RESULT</span><b>PASS · 24 / 24 ↗</b></a><a href={`${repo}experiments/blender-static-vector-floor-three-layer-evidence-holdout-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>55 unique processes ↗</b></a><a href={`${repo}research/2026-08-27-b52-d12-2-static-vector-floor-three-layer-evidence-result.md`}><span>RESULT NOTE</span><b>measurements · inference · limits ↗</b></a><a href={`${repo}specs/blender-static-vector-floor-three-layer-evidence-holdout.v0.1.json`}><span>FROZEN SPEC</span><b>thresholds · attacks · nonclaims ↗</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.2 Static Vector Floor</b></div><p>bounded residue supported · exact zero falsified · evidence layers separated</p><Link href="/journal">继续看实验日志 →</Link></footer>
  </main>;
}
