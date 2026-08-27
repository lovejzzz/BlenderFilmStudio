import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import type { CSSProperties } from 'react';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-static-nonplanar-multiowner-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-3/curved-pair-beauty.png';

export const metadata: Metadata = {
  title: 'B52-D12.3 非平面与多主体静态 Holdout｜Blender Film Studio',
  description: '55 个唯一进程、12 次真实 Blender 5.2 Cycles render：三组非平面/多主体场景的 owner-interior 通过冻结容差，但遮挡场景精确撞线，鲁棒性仍未成立。',
  alternates: { canonical },
  openGraph: { title: 'B52-D12.3 非平面与多主体静态 Holdout', description: '真实 Blender 5.2：interior 通过，boundary 拒绝，最坏单元零余量。', url: canonical, images: [{ url: socialImage }] },
  twitter: { card: 'summary_large_image', title: 'B52-D12.3 非平面与多主体静态 Holdout', description: '真实 Blender 5.2：interior 通过，boundary 拒绝，最坏单元零余量。', images: [socialImage] },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';
const threshold = 1.9073486328125e-6;

const fixtures = [
  { id: 'CURVED PAIR', title: 'UV sphere + torus', owners: '2 owners', raster: '97×61', registered: '3,566', interior: '2,598', boundary: '968', vector: '1.526e−5 px', interiorMax: 7.748603820800781e-7, rmse: '4.067e−8', boundaryMax: 7.331371307373047e-6, image: 'curved-pair' },
  { id: 'OCCLUDING PLANES', title: 'tilted grid + cube', owners: '2 owners', raster: '119×73', registered: '8,676', interior: '7,265', boundary: '1,411', vector: '2.289e−5 px', interiorMax: 1.9073486328125e-6, rmse: '2.470e−8', boundaryMax: 5.245208740234375e-6, image: 'occluding-planes' },
  { id: 'THIN DEPTH STACK', title: 'sphere + rod + sphere', owners: '3 owners', raster: '131×83', registered: '3,266', interior: '2,437', boundary: '829', vector: '2.289e−5 px', interiorMax: 5.960464477539062e-7, rmse: '4.991e−8', boundaryMax: 9.894371032714844e-6, image: 'thin-depth-stack' },
] as const;

export default function BlenderStaticNonplanarMultiownerPage() {
  return <main className="contact-page b51-page b52-page d11-page d111-page d12p-page d122-page d123-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.3 导航"><Link href="/blender-static-vector-floor-v0-1">D12.2 底噪</Link><a href="#verdict">结论</a><a href="#fixtures">真实场景</a><a href="#headroom">零余量</a><Link href="/blender-static-zero-headroom-localization-v0-1">D12.4 定位</Link><Link href="/journal">日志</Link></nav>
      <span className="edition contact-edition">Multi-owner D12.3</span>
    </header>

    <section className="contact-hero d123-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D12.3 · REAL BLENDER 5.2 HOLDOUT</p><h1>主体内部<span>通过。</span><br/>遮挡边界<span>拒绝复用。</span></h1><p>球面、圆环、遮挡平面与薄深度堆栈进入同一 owner-aware 重建合同。冻结容差在三个全新场景中成立，但最坏单元精确撞线：这是通过，不是鲁棒。</p></div>
      <aside className="contact-gate d123-gate"><b>FORMAL VERDICT</b><strong>INTERIOR<br/>SUPPORTED</strong><code>boundary · fail closed</code><code>zero headroom · 1 cell</code><small>exact zero falsified</small></aside>
      <div className="contact-stats"><article><strong>55 / 55</strong><span>formal child PIDs</span><small>all unique</small></article><article><strong>12</strong><span>真实 Cycles renders</span><small>three fixtures × two frames × two repeats</small></article><article><strong>27 / 27</strong><span>registered attacks</span><small>all passed</small></article><article><strong>12 / 12</strong><span>typed envelopes</span><small>Python = Node</small></article></div>
    </section>

    <section className="section d123-verdict" id="verdict">
      <div className="section-index">00 / THREE DOMAINS, THREE CLAIMS</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> REGISTER · ERODE · REJECT</p><h2>不是把全画面平均掉。<br/><span>而是先决定哪些像素有资格。</span></h2></div><p>Object Index 确认主体身份；5×5 同 owner 邻域与四个双线性 tap 同时成立，像素才进入 interior。任何主体断裂、画面外采样或 alpha 不完整都进入 boundary，并保持当前帧，不读取历史。</p></div>
      <div className="d12p-failures d123-claims"><article className="pass"><span>OWNER INTERIOR</span><strong>PASS</strong><b>3 / 3 fresh fixtures</b><p>RGB max 与 RMSE 全部满足 D12.2 冻结门。</p></article><article className="boundary"><span>OWNER BOUNDARY</span><strong>REJECT</strong><b>history reuse denied</b><p>最大误差达到 interior gate 的 5.19×；不进入正式通过域。</p></article><article className="warning"><span>ROBUSTNESS</span><strong>OPEN</strong><b>0 numeric headroom</b><p>遮挡平面恰好等于上限，不能外推到未见几何。</p></article></div>
    </section>

    <section className="section d123-fixtures" id="fixtures">
      <div className="section-index">01 / REAL GEOMETRY · DISPLAY PROXIES</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> BEAUTY BESIDE DOMAIN MAP</p><h2>先看真实场景。<br/><span>再看算法允许复用的区域。</span></h2></div><p>左侧来自正式 multipart EXR 的 Combined pass，经固定 ACES 2 SDR view 导出；右侧只是导航图：绿色为注册 interior，橙色为被拒 boundary。正式判决仍由 scene-linear float32 数组产生。</p></div>
      <div className="d123-gallery">{fixtures.map(fixture => <article key={fixture.id}><header><div><span>{fixture.id}</span><b>{fixture.title}</b></div><code>{fixture.owners} · {fixture.raster}</code></header><div><figure><Image src={`${basePath}/evidence/b52-d12-3/${fixture.image}-beauty.png`} width={262} height={166} unoptimized alt={`${fixture.title} 真实 Blender Beauty display proxy`}/><figcaption>ACES DISPLAY PROXY</figcaption></figure><figure><Image src={`${basePath}/evidence/b52-d12-3/${fixture.image}-domains.png`} width={262} height={166} unoptimized alt={`${fixture.title} owner interior 与 boundary 诊断图`}/><figcaption><i/> INTERIOR <em/> BOUNDARY</figcaption></figure></div></article>)}</div>
      <div className="contact-nonclaim"><b>DISPLAY PROXY ≠ DECISION SURFACE</b><p>这些 PNG 只帮助人理解场景与 mask。它们在正式运行结束后生成，不参与阈值、指标、攻击或 verdict；映射与源 EXR 哈希记录在独立 manifest 中。</p></div>
    </section>

    <section className="section d123-matrix">
      <div className="section-index">02 / INTERIOR MEASUREMENTS</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> REPEATS EXACT · LANGUAGES EXACT</p><h2>三个拓扑都过门。<br/><span>数值裕量却完全不同。</span></h2></div><p>两次源渲染、Python/Node payload 与双编码 envelope 在每个场景中均逐字节一致。表内是两个 repeat 完全相同的正式测量。</p></div>
      <div className="d12p-table d123-table"><div className="head"><b>FIXTURE</b><b>REGISTERED</b><b>INTERIOR</b><b>BOUNDARY</b><b>VECTOR MAX</b><b>INTERIOR RGB MAX</b><b>RMSE</b></div>{fixtures.map(fixture => <div className="row" key={fixture.id}><strong>{fixture.id}</strong><code>{fixture.registered}</code><code>{fixture.interior}</code><code>{fixture.boundary}</code><code>{fixture.vector}</code><code>{fixture.interiorMax.toExponential(4)}</code><code>{fixture.rmse}</code></div>)}</div>
    </section>

    <section className="section d123-headroom" id="headroom">
      <div className="section-index">03 / PASS WITH ZERO HEADROOM</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> ≤ IS TRUE · ROBUST IS UNPROVEN</p><h2>门槛没有失败。<br/><span>但它已经没有退路。</span></h2></div><p>冻结上限是 1/524288。遮挡平面的 interior RGB max 与它逐位相等。我们保留通过结论，同时拒绝“已具备鲁棒裕量”这一更强主张，也不在看到结果后提高门槛。</p></div>
      <div className="d123-bars">{fixtures.map(fixture => { const ratio = fixture.interiorMax / threshold; return <article key={fixture.id} className={ratio === 1 ? 'hit' : ''}><header><span>{fixture.id}</span><code>{(ratio * 100).toFixed(3)}% OF GATE</code></header><div><i style={{ '--level': `${ratio * 100}%` } as CSSProperties}/><b>LIMIT</b></div><footer><strong>{fixture.interiorMax.toExponential(8)}</strong><small>boundary max · {(fixture.boundaryMax / threshold).toFixed(2)}× gate</small></footer></article>})}</div>
      <div className="d123-next"><span>D12.4 · MECHANISM LOCALIZED</span><strong>唯一像素，距离轮廓 3px。</strong><div>{['FRONT_OCCLUDER','x56 · y38 · B','Vector −2⁻¹⁷','exact gate'].map(item => <code key={item}>{item}</code>)}</div><p>锁定数组的独立重放已定位完整算术链；D12.3 结论不变，半径 3 仍需 fresh holdout。</p><Link href="/blender-static-zero-headroom-localization-v0-1">查看 D12.4 证据 →</Link></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-static-nonplanar-multiowner-holdout-v0-1/results.json`}><span>MACHINE RESULT</span><b>PASS · 27 / 27 attacks ↗</b></a><a href={`${repo}experiments/blender-static-nonplanar-multiowner-holdout-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>55 unique processes ↗</b></a><a href={`${repo}research/2026-08-27-b52-d12-3-static-nonplanar-multiowner-holdout-result.md`}><span>RESULT NOTE</span><b>zero-headroom interpretation ↗</b></a><a href={`${repo}public/evidence/b52-d12-3/manifest.json`}><span>PROXY MANIFEST</span><b>source-bound · non-decisional ↗</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.3 Nonplanar Multi-owner</b></div><p>interior supported · boundaries rejected · robustness still open</p><Link href="/journal">继续看实验日志 →</Link></footer>
  </main>;
}
