import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import result from '../../experiments/blender-material-owner-rigid-directional-calibration-v0-1/results.json';
import audit from '../../experiments/blender-material-owner-rigid-directional-calibration-v0-1/audit.json';
import execution from '../../experiments/blender-material-owner-rigid-directional-calibration-v0-1/execution.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-rigid-directional-calibration-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-14-c2/rigid-directional-domain-matrix.png';

export const metadata: Metadata = {
  title: 'D12.14-C2 Rigid Directional Calibration｜Blender Film Studio',
  description: '两个独立 3D oracle 与三个真实 Blender 5.2 zero-render probes，从 500 个 world-space candidates 中导出 TOP、BOTTOM、NEITHER 三个同一刚体平面夹具。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.14-C2 · Rigid Directional Domains Derived',
    description: '500 candidates · 6 processes · 18/18 audit baseline · 64/64 attacks · zero renders.',
    url: canonical,
    images: [{ url: socialImage, width: 1797, height: 798, alt: 'Source-bound previous-owner and current directional-domain matrix for three rigid calibration candidates' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'D12.14-C2 · Rigid Fixture Geometry Derived',
    description: 'The missing stress domains now exist in world-space rigid geometry. Rendering remains the next gate.',
    images: [socialImage],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';
const targetMeta = {
  TOP_MISSING_BOTTOM_AVAILABLE: { short: 'TOP', statement: '上侧 outer taps 缺失', motion: '向下位移 + 透视扩张' },
  BOTTOM_MISSING_TOP_AVAILABLE: { short: 'BOTTOM', statement: '下侧 outer taps 缺失', motion: '深度推进 + 镜像边界' },
  NEITHER_HORIZONTAL_AVAILABLE: { short: 'NEITHER', statement: '水平两侧 outer taps 均缺失', motion: '88° edge-on → face-on' },
} as const;

const candidates = result.selected.map(row => ({
  ...row,
  ...targetMeta[row.target as keyof typeof targetMeta],
  current: `(${row.currentLocation.map(value => value.toFixed(1)).join(', ')})`,
  previous: `(${row.previousLocation.map(value => value.toFixed(1)).join(', ')})`,
  rotationY: `${(row.previousRotationEuler[1] * 180 / Math.PI).toFixed(1)}°`,
}));

export default function RigidDirectionalCalibrationPage() {
  return <main className="contact-page d1212-page d1214c2-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.14-C2 calibration 导航">
        <Link href="/blender-material-owner-quality-coupling-derivation-v0-1">D12.13-D1</Link>
        <a href="#verdict">结论</a><a href="#candidates">刚体候选</a><a href="#domains">方向域</a><a href="#blender">Blender</a><a href="#evidence">证据</a><a href="#next">下一门</a>
        <Link href="/blender-material-owner-rigid-directional-render-holdout-v0-1">D12.14-H1</Link>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Calibration D12.14-C2</span>
    </header>

    <section className="contact-hero d1212-hero d1214c2-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.14-C2 · WORLD-SPACE RIGID CALIBRATION · ZERO RENDERS</p>
        <h1>这次方向域，<br/><span>真的存在于 3D 世界里。</span></h1>
        <p>上一轮失败不是阈值不够聪明，而是 TOP、BOTTOM、NEITHER 场景没有真正进入要测试的几何域。我们先让两个独立 3D oracle 搜索同一尺寸刚体平面，再让真实 Blender 5.2 验证 mesh、transform 与投影。</p>
      </div>
      <aside className="contact-gate d1212-gate d1214c2-gate">
        <b>CALIBRATION VERDICT</b>
        <strong>RIGID<br/>DOMAINS</strong>
        <code>3 / 3 candidates · DERIVED</code>
        <code>receipt · VALID</code>
        <small>rendered holdout still required</small>
      </aside>
      <div className="contact-stats">
        <article><strong>500</strong><span>world-space candidates</span><small>360 vertical · 140 neither</small></article>
        <article><strong>{execution.processes.length}</strong><span>unique child processes</span><small>2 oracles · 3 Blender · audit</small></article>
        <article><strong>{audit.baselineChecksPassed}/{audit.baselineChecksTotal}</strong><span>audit baseline</span><small>identity · selection · rigidness</small></article>
        <article><strong>{audit.attacksPassed}/{audit.attacksTotal}</strong><span>semantic attacks</span><small>32 families × 2 mutations</small></article>
      </div>
    </section>

    <section className="section d1214c2-verdict" id="verdict">
      <div className="section-index">00 / SCIENTIFIC REPAIR</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> DO NOT PATCH A FAILED PREREGISTRATION</p><h2>先让旧设计失败。<br/><span>再开一项新实验。</span></h2></div>
        <p>D12.14-C1 把 Blender projection error 冻结为不可实现的 1e−9 pixel，还没有证明两帧矩形来自同一刚体。我们保留反例、不放宽原门，另行预登记 C2：固定一个 `[8,7]` mesh，只允许 location 与 Euler rotation 改变。</p>
      </div>
      <div className="d1214c2-repair-chain">
        <article className="failed"><span>C1 · PREFORMAL</span><strong>INVALID</strong><code>5.0e−6…5.8e−6 px &gt; 1e−9</code><p>Formal root 从未创建；失败 spec 与 prototype 全部保留。</p></article>
        <i>→</i>
        <article><span>C2 · NEW PREREG</span><strong>RIGID</strong><code>one mesh · scale [1,1,1]</code><p>搜索直接发生在 world-space transforms，不再独立缩放两张矩形。</p></article>
        <i>→</i>
        <article className="accepted"><span>FORMAL RESULT</span><strong>DERIVED</strong><code>8/8 runner · 18/18 audit</code><p>三种方向均产生纯 target domain，non-target 严格为 0。</p></article>
      </div>
    </section>

    <section className="section d1214c2-candidates" id="candidates">
      <div className="section-index">01 / MECHANICAL SELECTION</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> ONE MESH · TWO FRAMES · NO SCALE</p><h2>三种缺口，<br/><span>三条可复现的刚体轨迹。</span></h2></div>
        <p>选择规则先最大化相邻参数上的最坏 witness count，再最大化本 cell，最后最小化运动并按 candidate ID 决胜。没有 fixture-specific 手选，也没有颜色误差参与。</p>
      </div>
      <div className="d1214c2-candidate-grid">
        {candidates.map(row => <article key={row.candidateId} className={row.short.toLowerCase()}>
          <div><span>{row.short}</span><code>{row.candidateId}</code></div>
          <h3>{row.statement}</h3><p>{row.motion}</p>
          <dl>
            <div><dt>PREVIOUS LOC</dt><dd>{row.previous}</dd></div>
            <div><dt>CURRENT LOC</dt><dd>{row.current}</dd></div>
            <div><dt>PREVIOUS Y ROT</dt><dd>{row.rotationY}</dd></div>
            <div><dt>TARGET / ROBUST</dt><dd>{row.counts.target.toLocaleString('en-US')} / {row.neighborhoodMinimumTargetWitnesses.toLocaleString('en-US')}</dd></div>
          </dl>
          <footer><b>NON-TARGET</b><strong>{row.counts['non-target-one-sided']}</strong><span>scale · 1 / 1 / 1</span></footer>
        </article>)}
      </div>
    </section>

    <section className="section d1214c2-domains" id="domains">
      <div className="section-index">02 / SOURCE-BOUND DOMAIN MAP</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PREVIOUS OWNER RASTER → CURRENT CLASSIFICATION</p><h2>边界不再靠文字声称。<br/><span>它被写进逐像素 masks。</span></h2></div>
        <p>三列依次为 TOP、BOTTOM、NEITHER。上排洋红显示 previous-frame foreground raster；下排灰色是 full stencil，青色是 bilinear support，绿色是 target domain。NEITHER 的 previous owner 只有 262 pixels，却在 current frame 形成 15,113 个 neither witnesses。</p>
      </div>
      <figure className="d1214c2-domain-map">
        <Image src={`${basePath}/evidence/b52-d12-14-c2/rigid-directional-domain-matrix.png`} width={1797} height={798} alt="Three-column source-bound matrix showing previous foreground masks above and current rigid directional domains below" unoptimized />
        <figcaption>
          <div><span><i className="previous"/>previous foreground</span><span><i className="full"/>full stencil</span><span><i className="bilinear"/>bilinear support</span><span><i className="target"/>target domain</span></div>
          <p>最近邻 3× 放大，不插值、不创造新类别。分类为 <code>SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE</code>。</p>
        </figcaption>
      </figure>
    </section>

    <section className="section d1214c2-blender" id="blender">
      <div className="section-index">03 / REAL BLENDER 5.2 · ZERO RENDER PROBES</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> RNA REALIZABILITY · NOT A SCREENSHOT CLAIM</p><h2>同一个 mesh，<br/><span>在 Blender 里走完两帧。</span></h2></div>
        <p>每个 target 都由独立 factory-empty Blender process 构造 camera、background 和 foreground。Probe 顺序设置 frame 0/1 transforms，持续检查 mesh pointer、local-vertex hash 和 scale，没有调用 render。</p>
      </div>
      <div className="d1214c2-probe-grid">
        {result.probeSummary.map(row => <article key={row.target}>
          <span>{targetMeta[row.target as keyof typeof targetMeta].short}</span>
          <strong>{row.maximumProjectionAbsoluteErrorPixels.toExponential(3).replace('e-', 'e−')} px</strong>
          <code>limit · 3.052e−5 px</code>
          <div><b>mesh</b><i className={row.meshIdentityStable ? 'pass' : ''}/><b>scale</b><i className={row.scaleStable ? 'pass' : ''}/><b>RNA</b><em>{row.maximumRnaTransformAbsoluteError.toExponential(2)}</em></div>
        </article>)}
      </div>
      <div className="d1214c2-zero-strip">
        <article><strong>0</strong><span>Render Result</span></article><article><strong>0</strong><span>EXR files</span></article><article><strong>0</strong><span>Cycles renders</span></article><article><strong>0</strong><span>model / network</span></article>
      </div>
    </section>

    <section className="section d1214c2-evidence" id="evidence">
      <div className="section-index">04 / EVIDENCE CHAIN</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> GEOMETRY DERIVED · ALGORITHM STILL UNPROVEN</p><h2>证据闭环了。<br/><span>结论边界也必须闭环。</span></h2></div>
        <p>Python/Node 对 500-row candidate table 与 selected masks byte exact；第三方 audit 独立重放 selection，并对 32 个机制族执行两次 mutation。Receipt 有效，只证明“刚体方向夹具存在”。</p>
      </div>
      <div className="d1212-audit-grid d1214c2-audit-grid">
        <article><span>CANDIDATE TABLE</span><strong>BYTE EXACT</strong><p><code>{result.candidateTableSha256.slice(0, 16)}…</code></p></article>
        <article><span>RUNNER</span><strong>{result.evidenceChecksPassed} / {result.evidenceChecksTotal}</strong><p>parent · runtime · cross-language · probes</p></article>
        <article><span>AUDIT</span><strong>{audit.baselineChecksPassed} / {audit.baselineChecksTotal}</strong><p>independent selection + mask replay</p></article>
        <article><span>ATTACKS</span><strong>{audit.attacksPassed} / {audit.attacksTotal}</strong><p>32 named families · two variants each</p></article>
        <article><span>PROCESS</span><strong>{execution.processes.length} / {execution.processes.length}</strong><p>unique PID · exit zero</p></article>
        <article><span>RECEIPT</span><strong>VALID</strong><p><code>e2a6cc139972…d4c7</code></p></article>
      </div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-owner-rigid-directional-calibration.v0.1.json`}><span>PREREGISTRATION</span><b>world-space grid + gates ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-rigid-directional-calibration-v0-1/results.json`}><span>FORMAL RESULT</span><b>3 / 3 rigid candidates ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-rigid-directional-calibration-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>18 / 18 · 64 / 64 ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-rigid-directional-calibration-v0-1/execution.json`}><span>EXECUTION</span><b>6 unique processes ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-14-c1-directional-calibration-preregistered-gate-falsification.md`}><span>FAILED C1 DESIGN</span><b>preformal falsification ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-14-c2-rigid-directional-calibration-result.md`}><span>RESEARCH NOTE</span><b>result + non-claims ↗</b></a>
      </div>
    </section>

    <section className="section d1214c2-next" id="next">
      <div className="section-index">05 / NEXT GATE · FRESH BLENDER RENDER HOLDOUT</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> THE RENDER HOLDOUT RAN · THE INSTRUMENT FAILED</p><h2>12 次渲染完成了。<br/><span>但 H1 没有科学结论。</span></h2></div>
        <p>Fresh holdout 使用了新 raster、tokens、signals、EXR outputs 与两次 repeats；第 55 个 child 因冻结 analyzer 的 schema 缺口中止。失败证据已封存，相同 ID 不得重跑。</p>
      </div>
      <div className="d1214c2-next-grid">
        <article><span>COMPLETED</span><strong>12 fresh renders</strong><p>3 fixtures × 2 frames × 2 repeats 全部产生真实 Cycles passes。</p></article>
        <article><span>FAILED</span><strong>frozen analyzer</strong><p>Background subdivisions 未在 analyzer schema normalization 中展开。</p></article>
        <article><span>READ</span><strong>open H1 failure dossier</strong><p><Link href="/blender-material-owner-rigid-directional-render-holdout-v0-1">查看完整失败链与非决定性取证 →</Link></p></article>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.14-C2 Rigid Directional Calibration</b></div><p>rigid domains derived · H1 instrument failure preserved</p><Link href="/blender-material-owner-rigid-directional-render-holdout-v0-1">进入 D12.14-H1 →</Link></footer>
  </main>;
}
