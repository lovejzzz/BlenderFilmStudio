import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'B52-D10.1 Blender Multipart Pass Adapter｜Blender Film Studio',
  description: '真实 Blender 5.2 multipart EXR 到七个 canonical temporal arrays：19 个独立进程、37/37 attacks、独立 audit PASS；同时保留 D10 verifier-contract 失败。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-pass-adapter-v0-1/' },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const evidence = 'https://raw.githubusercontent.com/lovejzzz/BlenderFilmStudio/5ad1800/experiments/blender-multipart-temporal-adapter-f32-holdout-v0-1/diagnostics';

const fixtures = [
  {
    slug: 'f32_object_xy_181x103',
    name: 'OBJECT XY',
    motion: 'XY (−11,+7) · ZW (−18,+11)',
    error: '3.815e−6 / 8.530e−6 px',
    wrong: 'nearest wrong 8.062 px',
  },
  {
    slug: 'f32_camera_xy_181x103',
    name: 'CAMERA XY',
    motion: 'XY (+9,−6) · ZW (+20,−12)',
    error: '3.076e−5 / 3.146e−5 px',
    wrong: 'nearest wrong ≥ 12.530 px',
  },
  {
    slug: 'f32_static_depth_owner_181x103',
    name: 'STATIC / DEPTH / OWNER',
    motion: 'nonzero floor retained',
    error: 'max 3.052e−5 px',
    wrong: 'Depth 60/60 · Owner 60/60',
  },
];

const views = [
  ['current-combined', 'COMBINED', '当前帧 Combined beauty pass'],
  ['current-depth', 'DEPTH', '当前帧 camera-space Depth 诊断图'],
  ['current-ownership', 'OWNERSHIP', '当前帧 Object Index 归属诊断图'],
  ['current-previous-motion-magnitude', 'MOTION |XY|', 'current-to-previous motion magnitude 诊断图'],
];

export default function BlenderPassAdapterPage() {
  return <main className="contact-page b51-page b52-page d91-page d101-page">
    <header className="topbar">
      <a className="brand" href="../"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></a>
      <nav aria-label="D10.1 导航"><a href="../temporal-accumulation-v0-1/">D9.1 累积</a><a href="#failure">D10 失败</a><a href="#oracle">Typed oracle</a><a href="#adapter">Adapter</a><a href="#evidence">诊断图</a><a href="../blender-temporal-composition-v0-1/">D11 反例</a><a href="../journal/">日志</a></nav>
      <span className="edition contact-edition">Pass Adapter D10.1</span>
    </header>

    <section className="contact-hero b51-hero b52-hero d101-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D10.1 · REAL BLENDER MULTIPART ADAPTER</p><h1>不是猜 Vector。<br/><span>让真实 pass 对齐解析真值。</span></h1><p>三个 fresh 181×103 fixtures、十二次真实 Blender 5.2 Cycles 源渲染、六次独立 adapter 和一次分析。Combined、Depth、Vector、Object Index 被转换成 D9.1 所需的七个 canonical arrays；结构、重复、数值、攻击与独立重放全部过门。</p></div>
      <aside className="contact-gate b51-gate b52-gate d101-gate"><b>SCIENTIFIC VERDICT</b><strong>SUPPORTED<br/>NARROWLY</strong><code>37 / 37 attacks</code><code>audit PASS</code><small>opaque · orthographic · integer motion</small></aside>
      <div className="contact-stats"><article><strong>19 / 19</strong><span>formal child processes</span><small>all PID unique</small></article><article><strong>12</strong><span>Cycles source renders</span><small>two clean repeats</small></article><article><strong>42 / 42</strong><span>canonical arrays</span><small>independent replay exact</small></article><article><strong>60 / 60</strong><span>depth + ownership rows</span><small>both domains exact</small></article></div>
    </section>

    <section className="section d101-failure" id="failure">
      <div className="section-index">00 / RETAINED NEGATIVE RESULT</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> D10 · PAYLOAD PASSED, CONTRACT FAILED</p><h2>失败没有被覆盖。<br/><span>它定义了正确的数据类型。</span></h2></div><p>D10 的 Vector、Depth、ownership 与重复性全部通过冻结门，但结构 oracle 把十进制 JSON double 直接与 Blender RNA float32 readback 比较，例如 17.3 对 17.299999237060547。它因此保持 NOT_SUPPORTED、audit FAIL、attacks 0/34；没有补 epsilon，也没有重跑。</p></div>
      <div className="d101-failure-chain"><article className="payload"><span>D10 PAYLOAD</span><strong>ALL GATES</strong><b>vector · depth · owner · repeat</b></article><i>+</i><article className="fault"><span>STRUCTURE ORACLE</span><strong>double ≠ f32</strong><b>representation mismatch</b></article><i>→</i><article className="stopped"><span>FROZEN VERDICT</span><strong>NOT SUPPORTED</strong><b>SCENE_STRUCTURE</b></article></div>
      <div className="contact-nonclaim"><b>NEGATIVE RESULT IS IMMUTABLE</b><p>D10.1 是全新 resolution、ortho scale、几何、对象名、ID 与轨迹上的独立实验。它修复的是下一实验的 verifier contract，不能追溯性地把 D10 改成通过。</p></div>
    </section>

    <section className="section d101-oracle" id="oracle">
      <div className="section-index">01 / TYPED STRUCTURAL ORACLE</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> EXACTNESS WITHOUT A GLOBAL EPSILON</p><h2>类型知道哪里是 float。<br/><span>其余结构仍逐项 exact。</span></h2></div><p>只有 spec 明确声明的 Blender RNA float path 经过 IEEE-754 binary32 pack/unpack；名称、枚举、整数、拓扑、pass index、Action roster 与操作次数保持严格相等。这样既接受 Blender 的真实存储，也不把错误藏进一个全局容差。</p></div>
      <div className="d101-oracle-rail"><article><span>JSON DOUBLE</span><code>18.1</code><small>raw comparison must reject</small></article><i>→</i><article className="typed"><span>RNA FLOAT32</span><code>18.100000381469727</code><small>binary32 round-trip exact</small></article><i>≠</i><article><span>ADJACENT ULP</span><code>18.10000228881836</code><small>one-ULP attack rejected</small></article></div>
      <div className="d101-exact-grid"><article><span>DECLARED RNA FLOATS</span><strong>f32 exact</strong><p>only enumerated paths canonicalize</p></article><article><span>NAMES / ENUMS</span><strong>string exact</strong><p>no normalization fallback</p></article><article><span>INTEGER / TOPOLOGY</span><strong>value exact</strong><p>pass index mutation rejected</p></article><article><span>GLOBAL EPSILON</span><strong>forbidden</strong><p>no blanket tolerance</p></article></div>
    </section>

    <section className="section d101-adapter" id="adapter">
      <div className="section-index">02 / PRODUCTION-PASS MAPPING</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> MULTIPART EXR → SEVEN CANONICAL ARRAYS</p><h2>真实 Blender 数据进入<br/><span>可审计的时序接口。</span></h2></div><p>Blender Vector 的 `XY` 对齐 previous−current，`ZW` 对齐 current−next；由于图像 row 向下，D9.1 current→previous lookup 使用 `motion=(-Vector.X,-Vector.Y)`。Depth 与 Object Index 不做视觉猜测，分别对齐解析 camera-space 距离和固定 3×3 ownership probes。</p></div>
      <div className="d101-pipeline"><article><span>01</span><strong>MULTIPART EXR</strong><b>Combined · Depth · Vector · Object Index</b></article><i>→</i><article><span>02</span><strong>D10.1 ADAPTER</strong><b>typed roster · raster orientation</b></article><i>→</i><article><span>03</span><strong>7 ARRAYS</strong><b>RGBA ×2 · depth ×2 · motion · owner ×2</b></article><i>→</i><article><span>04</span><strong>D9.1 READY</strong><b>current→previous canonical contract</b></article></div>
      <div className="d101-metric-table"><div className="head"><b>FIXTURE</b><b>FROZEN MOTION</b><b>CORRECT MAXIMA</b><b>SEPARATION / DATA</b></div>{fixtures.map((fixture)=><div className="row" key={fixture.slug}><span><b>{fixture.name}</b><small>181 × 103</small></span><code>{fixture.motion}</code><code>{fixture.error}</code><code>{fixture.wrong}</code></div>)}</div>
      <div className="b51-localization-grid"><article className="exact"><span>STRUCTURE</span><strong>12 / 12</strong><b>typed scene + Action exact</b><p>raw-double attacks rejected</p></article><article className="exact"><span>SOURCE REPEAT</span><strong>12 / 12</strong><b>all required passes exact</b><p>fresh Blender processes</p></article><article className="exact"><span>ADAPTER REPLAY</span><strong>6 / 6</strong><b>42 arrays exact</b><p>independent reconstruction</p></article><article className="exact"><span>INTEGRITY</span><strong>37 / 37</strong><b>mutation attacks pass</b><p>audit has zero failures</p></article></div>
    </section>

    <section className="section d101-evidence" id="evidence">
      <div className="section-index">03 / FIXED DIAGNOSTICS</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> COMBINED · DEPTH · OWNER · MOTION</p><h2>每一种语义，<br/><span>都留下独立定位图。</span></h2></div><p>下面十二张图固定来自正式 commit `5ad1800`。图像只用于定位；判定来自原始 EXR、canonical float32 arrays、解析投影和独立 replay，浏览器显示不参与数值门。</p></div>
      <div className="d101-gallery">{fixtures.map((fixture)=><article key={fixture.slug}><header><b>{fixture.name}</b><span>181 × 103 · FORMAL</span></header><div>{views.map(([suffix,label,alt])=><figure key={suffix}><img src={`${evidence}/${fixture.slug}--${suffix}.png`} width="181" height="103" alt={`${fixture.name}：${alt}`}/><figcaption>{label}</figcaption></figure>)}</div></article>)}</div>
      <div className="contact-nonclaim"><b>DIAGNOSTIC PNG ≠ NUMERIC EVIDENCE</b><p>颜色映射、缩放和量化只帮助人类定位。正式结论要求 EXR channel roster、解析 endpoint、原始 float32 数组、重复 hash 和独立审计同时成立。</p></div>
    </section>

    <section className="section contact-limits b51-next" id="boundary">
      <div className="section-index">04 / DOWNSTREAM COMPOSITION RESULT</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> B52-D11 · REAL TEXTURED END-TO-END HOLDOUT</p><h2>接口本身成立。<br/><span>未修改组合仍被反例拒绝。</span></h2></div><p>D11 已用全新真实场景把 textured multipart、D10.1 adapter、Python/Node accumulator、Raw EXR 与 Blender compositor 串成一条链。所有接口与重放门通过，但 near-integer Vector 经 toward-zero 转换后稳定偏移一像素；正式结论保持 NOT_SUPPORTED。</p></div>
      <div className="b51-next-flow"><article><span>01</span><b>REAL TEXTURED RENDER</b><p>fresh scene · occlusion cases</p></article><i>→</i><article><span>02</span><b>D10.1 ADAPTER</b><p>production pass extraction</p></article><i>→</i><article><span>03</span><b>D9.1 ACCUMULATOR</b><p>analytic validity + controls</p></article><i>→</i><article><span>04</span><b>D8 RAW EXR</b><p>end-to-end decoded exactness</p></article></div>
      <div className="contact-nonclaim"><b>D10.1 SUPPORT REMAINS NARROW</b><p>D11 没有推翻 pass adapter 的 typed float32 extraction；它拒绝的是 adapter 与 integer accumulator 的未修改组合。唯一允许的恢复是在全新 D11.1 中显式插入 nearest-integer quantizer，而不是改写 D11。</p></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-multipart-temporal-adapter-f32-holdout-v0-1/results.json`}><span>D10.1 MACHINE RESULT</span><b>SUPPORTED · 37 / 37 ↗</b></a><a href={`${repo}experiments/blender-multipart-temporal-adapter-f32-holdout-v0-1/audit.json`}><span>D10.1 AUDIT</span><b>PASS · 42 / 42 arrays ↗</b></a><a href={`${repo}research/2026-08-27-b52-d10-blender-multipart-temporal-adapter-holdout-invalid-result.md`}><span>D10 NEGATIVE RESULT</span><b>NOT SUPPORTED · retained ↗</b></a><a href={`${repo}specs/blender-multipart-temporal-adapter-f32-holdout.v0.1.json`}><span>FROZEN SPEC</span><b>typed oracle · fresh fixtures ↗</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D10.1 Pass Adapter Research</b></div><p>D10 failure retained · D10.1 narrow support · D11 composition rejected</p><a href="../blender-temporal-composition-v0-1/">继续看 D11 反例 →</a></footer>
  </main>;
}
