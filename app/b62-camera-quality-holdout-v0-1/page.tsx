import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import audit from '../../experiments/b62-camera-quality-holdout-render-v0-5/audit.json';
import independent from '../../experiments/b62-camera-quality-holdout-render-v0-5/independent.json';
import receipt from '../../experiments/b62-camera-quality-holdout-render-v0-5/receipt.json';
import render from '../../experiments/b62-camera-quality-holdout-render-v0-5/render.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/b62-camera-quality-holdout-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B62 Camera Quality 留出实验｜Blender Film Studio',
  description: '真实 Blender 5.2 完成 12 次 Cycles 配对留出渲染：静态相机修正显著改善遮挡，但在冻结的 frame 288 门槛上被科学拒绝。',
  alternates: { canonical },
  openGraph: {
    title: 'B62 · Correction worked. Holdout still rejected.',
    description: '3 fresh Blender processes · 12 Cycles renders · 18/18 technical checks · scientific rejection retained.',
    url: canonical,
    images: [],
  },
};

const frames = [193, 204, 228, 252, 276, 288] as const;
const readings: Record<number, { short: string; human: string }> = {
  193: { short: 'READABLE', human: '上身、visor、抬手动作与环境灯同时可读，仍有负空间。' },
  204: { short: 'READABLE', human: '角色轮廓与环境分离稳定；比原镜头有实质改善。' },
  228: { short: 'READABLE', human: 'profile 与胸肩层级清楚；构图开始收紧但仍平衡。' },
  252: { short: 'TIGHTENING', human: '角色仍可识别，头盔与肩部比例开始压迫画面。' },
  276: { short: 'TOO TIGHT', human: '语义 anchor 尚在，但环境与身体信息明显减少。' },
  288: { short: 'HOLDOUT FAIL', human: '头盔与肩部挤满画面，缺少呼吸空间；拒绝推广。' },
};

export default function B62CameraQualityHoldoutPage() {
  const checkPasses = audit.checks.filter(check => check.pass).length;
  const corrected = independent.geometry.filter(row => row.condition === 'CORRECTED');
  const original = independent.geometry.filter(row => row.condition === 'ORIGINAL');

  return <main className="contact-page b62-page b62q-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B62 camera quality 导航"><a href="#pairs">六组配对</a><a href="#gate">机器门</a><a href="#review">人工复核</a><a href="#cost">成本</a><a href="#next">下一实验</a><Link href="/journal">Journal</Link></nav>
      <span className="edition contact-edition">B62 · CAMERA Q1</span>
    </header>

    <section className="contact-hero b62-hero b62q-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> REAL BLENDER 5.2 · SIX SEALED HOLDOUTS · PAIRED CYCLES</p>
        <h1>修正生效了。<br/><span>镜头仍被拒绝。</span></h1>
        <p>有界相机变换把“整帧头盔表面”恢复成可读角色镜头，六组像素也全部不同。但同一静态修正无法跟随运动维持主体尺度：frame 288 的画面占比为 0.933787，超过预登记上限 0.90。</p>
      </div>
      <aside className="contact-gate b62-gate b62q-gate">
        <b>FORMAL OUTCOME</b><strong>TECHNICAL PASS<br/>SCIENTIFIC REJECTED</strong>
        <code>{checkPasses} / {audit.checks.length} checks</code>
        <code>frame 288 · 0.933787 &gt; 0.90</code>
        <small>receipt {receipt.receiptHash.slice(0, 16)}…</small>
      </aside>
      <div className="contact-stats">
        <article><strong>12</strong><span>Cycles Render Calls</span><small>6 frames × 2 conditions</small></article>
        <article><strong>6/6</strong><span>像素配对不同</span><small>timeline routing exact</small></article>
        <article><strong>5/6</strong><span>Corrected 几何通过</span><small>frame 288 rejected</small></article>
        <article><strong>0</strong><span>视频模型调用</span><small>model · network · Docker</small></article>
      </div>
    </section>

    <section className="section b62-frames b62q-pairs" id="pairs">
      <div className="section-index">00 / ORIGINAL LEFT · CORRECTED RIGHT</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> 960×540 · CYCLES CPU · 16 SPP · MULTILAYER EXR</p><h2>灾难性遮挡被修复。<br/><span>时间中的构图漂移没有。</span></h2></div><p>每一行来自同一 frame 的两次真实 Blender 渲染。左图是原相机，右图是唯一 D3 有界候选。所有 EXR Combined pixels 均 finite、具动态范围并由第三个 Blender 进程独立解码。</p></div>
      <div className="b62q-pair-list">{frames.map(frame => {
        const metric = corrected.find(row => row.frame === frame)!;
        return <article key={frame} className={metric.feasible ? '' : 'holdout-fail'}>
          <header><span>FRAME {frame}</span><b>{readings[frame].short}</b><code>clamped area {metric.characterProjection.clampedUnionAreaFraction.toFixed(6)}</code></header>
          <div className="b62q-images">
            <figure><Image src={`${basePath}/evidence/b62-d4/${String(frame).padStart(4, '0')}-original.png`} width={960} height={540} unoptimized alt={`Frame ${frame}, original Blender camera, extreme helmet occlusion`} /><figcaption>ORIGINAL · REJECTED</figcaption></figure>
            <figure><Image src={`${basePath}/evidence/b62-d4/${String(frame).padStart(4, '0')}-corrected.png`} width={960} height={540} unoptimized alt={`Frame ${frame}, corrected Blender camera holdout render`} /><figcaption>CORRECTED · {metric.feasible ? 'MECHANICAL PASS' : 'HOLDOUT FAIL'}</figcaption></figure>
          </div>
          <p>{readings[frame].human}</p>
        </article>;
      })}</div>
    </section>

    <section className="section b62-audit b62q-gate-section" id="gate">
      <div className="section-index">01 / FROZEN GEOMETRY GATE</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> DO NOT MOVE THE THRESHOLD AFTER SEEING THE DATA</p><h2>前五帧不是全片。<br/><span>最后一个反例足以拒绝。</span></h2></div><p>候选必须在六帧全部满足 visor + eye、helmet blocker、character blocker、on-screen vertices、clamped area 与可见 anchor 门。不能因为 5/6 看起来不错，就删除 frame 288 或把 0.90 改成 0.94。</p></div>
      <div className="b62q-trend" role="img" aria-label="Corrected camera clamped character area grows from 0.54 at frame 193 to 0.934 at frame 288 and crosses the 0.90 limit only at the last frame">
        <div className="b62q-threshold"><span>0.90 FROZEN MAXIMUM</span></div>
        {corrected.map(row => <article key={row.frame}><b>{row.frame}</b><div><i style={{ width: `${row.characterProjection.clampedUnionAreaFraction * 100}%` }} /></div><code>{row.characterProjection.clampedUnionAreaFraction.toFixed(6)}</code><span>{row.feasible ? 'PASS' : 'FAIL'}</span></article>)}
      </div>
      <div className="b62-audit-grid b62q-audit-grid">
        <article><span>FORMAL CHECKS</span><strong>{checkPasses}/{audit.checks.length}</strong><p>身份、进程、路由、像素与 verdict mapping 全通过</p></article>
        <article><span>ORIGINAL FAILED</span><strong>{original.filter(row => !row.feasible).length}/6</strong><p>六帧全部不可接受</p></article>
        <article><span>CORRECTED PASSED</span><strong>{corrected.filter(row => row.feasible).length}/6</strong><p>最后一帧保留为反例</p></article>
        <article><span>PAIR DIGESTS</span><strong>{render.pairs.filter(pair => pair.different).length}/6</strong><p>marker 与 scene camera 双路由确实生效</p></article>
      </div>
    </section>

    <section className="section b62-cost b62q-review" id="review">
      <div className="section-index">02 / NATIVE-RESOLUTION HUMAN ENGINEERING REVIEW</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> LABELS KNOWN · NOT A BLIND PREFERENCE STUDY</p><h2>方向是对的。<br/><span>路径还不够聪明。</span></h2></div><p>逐张打开全部 12 张 PNG 后，人工观察与机器门一致：静态变换显著改善原镜头，但 corrected shot 从 193 到 288 持续推紧。它是一个有效反例驱动的设计信号，不是审美晋级。</p></div>
      <div className="b62-boundary-grid b62q-review-grid">
        <article className="supported"><span>OBSERVED</span><strong>Occlusion fixed</strong><p>visor、eye、手臂、肩部和环境关系重新可读。</p></article>
        <article><span>OBSERVED</span><strong>Scale drifts</strong><p>角色占画面面积从 0.540941 增长到 0.933787。</p></article>
        <article><span>NOT CLAIMED</span><strong>Cinematic approval</strong><p>有标签工程复核不是 blind preference；16 spp 也不是 final master。</p></article>
        <article className="next"><span>DESIGN CONSEQUENCE</span><strong>Motion-aware path</strong><p>下一轮必须让相机路径随运动补偿主体尺度，而不是单一静态变换。</p></article>
      </div>
    </section>

    <section className="section b62-boundary b62q-cost" id="cost">
      <div className="section-index">03 / OBSERVED EXECUTION COST</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> LOCAL CPU CYCLES · NO VIDEO MODEL</p><h2>失败也有成本。<br/><span>但成本被留出门限制住了。</span></h2></div><p>D4 只支付 12 张低样本诊断图，没有运行 288 帧完整 Cycles。渲染进程总计 {render.elapsedSeconds.toFixed(2)} 秒；失败发生在构图门，而不是昂贵最终交付之后。</p></div>
      <div className="b62-cost-grid b62q-cost-grid">
        <article><span>BUILD</span><strong>0.53 s</strong><small>fresh derived .blend</small></article>
        <article><span>12 × CYCLES</span><strong>{render.elapsedSeconds.toFixed(2)} s</strong><small>960×540 · CPU · 16 spp</small></article>
        <article><span>INDEPENDENT REOPEN</span><strong>2.43 s</strong><small>geometry + EXR decode</small></article>
        <article className="projection"><span>PEAK RENDER RSS</span><strong>1.33 GB</strong><small>measured sampled maximum</small></article>
      </div>
    </section>

    <section className="section b62-audit b62q-next" id="next">
      <div className="section-index">04 / NEXT FALSIFIABLE QUESTION</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> STATIC TRANSFORM REJECTED · TEMPORAL CONTROL NEXT</p><h2>不放宽 0.90。<br/><span>让镜头学会跟随运动。</span></h2></div><p>下一实验将预登记一个有界 motion-aware camera path：以连续时间上的主体尺度与语义 anchor 为反馈，对 radial scale 或焦距做平滑补偿，并保留未参与拟合的验证帧。只有全帧机械门与新 Cycles 留出都通过，才允许推广。</p></div>
      <div className="contact-artifacts b62-artifacts">
        <a href={`${repo}research/2026-08-29-b62-d4-native-resolution-human-review.md`}><span>HUMAN REVIEW</span><b>all 12 native PNGs ↗</b></a>
        <a href={`${repo}experiments/b62-camera-quality-holdout-render-v0-5/audit.json`}><span>INDEPENDENT AUDIT</span><b>{checkPasses}/{audit.checks.length} technical checks ↗</b></a>
        <a href={`${repo}experiments/b62-camera-quality-holdout-render-v0-5/independent.json`}><span>GEOMETRY EVIDENCE</span><b>5/6 corrected · 6/6 original fail ↗</b></a>
        <a href={`${repo}experiments/b62-camera-quality-holdout-render-v0-5/receipt.json`}><span>FORMAL RECEIPT</span><b>{receipt.receiptHash.slice(0, 16)}… ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B62 Camera Quality Holdout</b></div><p>technical pass · scientific rejection retained</p><Link href="/b62-phase0-terminal-proof-v0-1">返回 Phase 0 →</Link></footer>
  </main>;
}
