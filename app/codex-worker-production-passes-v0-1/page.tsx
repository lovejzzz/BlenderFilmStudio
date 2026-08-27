import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'B47 Blender 多层 EXR 生产通道｜Blender Film Studio',
  description: '四个真实 Blender 5.2 Linux/amd64 worker 生成八个 multipart EXR；Combined、Depth、Normal、Vector 与 Cryptomatte 共 28/28 跨构建通道对精确一致。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/codex-worker-production-passes-v0-1/' },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const passes = [
  ['01','COMBINED','RGBA','scene-linear beauty','finite · 36,864 values'],
  ['02','DEPTH','Z','camera-space distance','far sentinel = 1e10'],
  ['03','NORMAL','XYZ','surface orientation','finite · range [−1, 1]'],
  ['04','VECTOR','XYZW','screen-space motion','non-zero on moving shot'],
  ['05','CRYPTO 00','RGBA','object IDs + coverage','MurmurHash3_32'],
  ['06','CRYPTO 01','RGBA','object IDs + coverage','manifest-bound'],
  ['07','CRYPTO 02','RGBA','object IDs + coverage','depth 6 payload'],
] as const;
const runs = [
  ['TABLETOP-A1','21 · 22','10,679 ms','MOVING','14 / 14'],
  ['TABLETOP-A2','21 · 22','10,713 ms','MOVING','14 / 14'],
  ['INTERIOR-A1','09 · 10','11,012 ms','STATIC','14 / 14'],
  ['INTERIOR-A2','09 · 10','10,706 ms','STATIC','14 / 14'],
] as const;
const tabletopObjects = ['STAGE','LEATHER_BLOCK','METAL_SPHERE','GLASS_CYLINDER','SKIN_TONE_CARD','KEY_LARGE','RIM_COOL','object'];
const interiorObjects = ['FLOOR','BACK_WALL','SIDE_WALL','CENTER_PLINTH','DISPLAY_CUBE','DISPLAY_SPHERE','DISPLAY_CYLINDER','LEFT_FILL','RIGHT_EDGE','CEILING_PANEL','PRACTICAL_A','PRACTICAL_B','CAMERA_GUIDE','HERO_PROP','object'];

export default function CodexWorkerProductionPassesPage(){return <main className="contact-page b47-page">
  <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B47 导航"><Link href="/journal">实验日志</Link><Link href="/codex-worker-sequence-v0-1">B46 序列</Link><a href="#stack">通道栈</a><a href="#evidence">证据</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">Production Passes B47</span></header>

  <section className="contact-hero b47-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> REAL .BLEND → 32-BIT MULTIPART EXR → CANONICAL PASS ARRAYS</p><h1>不是只有漂亮画面。<br/><span>后期需要的层，也能复现。</span></h1><p>四份字节不同、结构相同的 `.blend`，进入四个真实 Blender 5.2 Linux/amd64 worker。八个 multipart EXR 被独立重开并规范化；七类生产通道在两次净构建之间得到 28/28 精确配对。</p></div><aside className="contact-gate b47-gate"><b>FORMAL VERDICT</b><strong>PASS DATA<br/>EXACT</strong><code>28 / 28 cross-build pairs</code><code>8 multipart EXR · 56 observations</code><small>AUDIT MATCH · 18/18 ATTACKS</small></aside><div className="contact-stats"><article><strong>7</strong><span>每帧子图层</span><small>beauty + geometry + IDs</small></article><article><strong>32-bit</strong><span>浮点输出</span><small>ZIP multipart OpenEXR</small></article><article><strong>4 / 4</strong><span>隔离 worker</span><small>Linux/amd64 · Cycles CPU</small></article><article><strong>8 / 8</strong><span>容器字节不同</span><small>decoded data is claim unit</small></article></div></section>

  <section className="section b47-stack" id="stack"><div className="section-index">00 / PRODUCTION LAYER STACK</div><div className="contact-heading"><div><p className="eyebrow"><span/> ONE RENDER · SEVEN ADDRESSABLE SUBIMAGES</p><h2>Beauty 是结果。<br/><span>Depth、Normal、Vector、ID 是控制权。</span></h2></div><p>同一次 render result 直接保存为 `OPEN_EXR_MULTILAYER`。不从 PNG 推导深度，不另跑遮罩，不用生成式模型猜运动。每层都有固定名称、channel layout、float32 语义和独立哈希。</p></div><div className="b47-layer-stack">{passes.map(([n,name,channels,meaning,rule],i)=><article key={name} style={{'--layer':i} as React.CSSProperties}><span>{n}</span><b>{name}</b><code>{channels}</code><p>{meaning}</p><small>{rule}</small></article>)}</div></section>

  <section className="section b47-evidence" id="evidence"><div className="section-index">01 / FOUR CLEAN WORKERS</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> TWO SEMANTIC PAIRS · EIGHT REAL EXR FILES</p><h2>文件字节不相同。<br/><span>解码通道逐值相同。</span></h2></div><p>EXR header、压缩块或写出细节会改变容器 SHA-256，所以 B47 没有把 file-byte identity 冒充科学复现。判决对象是按固定 dtype、shape、channel order 规范化后的 little-endian float32 数组，以及 Cryptomatte 所需 metadata。</p></div><ol className="b47-run-table"><li className="head"><span>WORKER</span><b>FRAMES</b><code>WALL</code><small>TEMPORAL ROLE</small><i>PASS PAIRS</i></li>{runs.map(([id,frames,wall,role,pairs])=><li key={id}><span>{id}</span><b>{frames}</b><code>{wall}</code><small>{role}</small><i>{pairs}</i></li>)}</ol><div className="b47-identity"><article><span>CONTAINER FILE SHA-256</span><strong>0 / 8</strong><b>BYTE-IDENTICAL</b><p>八个 EXR 的文件哈希全部不同；不作为失败，也不被隐藏。</p></article><i>≠</i><article><span>CANONICAL FLOAT32 PASS SHA-256</span><strong>28 / 28</strong><b>CROSS-BUILD EXACT</b><p>每个语义场景、每一帧、每一层的 A1/A2 数组哈希一致。</p></article></div></section>

  <section className="section b47-temporal"><div className="section-index">02 / TEMPORAL CONTROLS</div><div className="contact-heading"><div><p className="eyebrow"><span/> CHANGE WHERE EXPECTED · HOLD WHERE EXPECTED</p><h2>运动镜头必须变化。<br/><span>静态对照必须不动。</span></h2></div><p>跨构建相同不是“所有帧都被错误冻结”。TABLETOP 的摄影机从 frame 21 推进到 22；INTERIOR 的 frame 9 和 10 则是严格静态负对照。</p></div><div className="b47-temporal-grid"><article><span>TABLETOP · MOVING CAMERA</span><strong>4 / 4</strong><b>核心通道发生变化</b><div><i>Combined</i><i>Depth</i><i>Normal</i><i>Vector</i></div><small>两份净构建呈现相同变化关系</small></article><article><span>INTERIOR · STATIC CONTROL</span><strong>7 / 7</strong><b>全部通道保持精确</b><div><i>Combined</i><i>Depth</i><i>Normal</i><i>Vector</i><i>Crypto × 3</i></div><small>零变化是测得的，不是由场景标签推断</small></article></div></section>

  <section className="section b47-crypto"><div className="section-index">03 / OBJECT-LEVEL ADDRESSABILITY</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> CRYPTOMATTE MANIFESTS · HASHED OBJECT IDs</p><h2>画面不再是一张扁平图。<br/><span>对象可以被后期精确寻址。</span></h2></div><p>两个场景的 Cryptomatte metadata 声明 `MurmurHash3_32` 和 `uint32_to_float32`，manifest 在 A/B worker 间 exact，并包含预注册要求的对象。B47 证明 ID 数据结构可复现，不证明任意合成软件的交互体验。</p></div><div className="b47-manifest"><article><header><span>SHOT_109</span><b>TABLETOP · 8 KEYS</b></header><div>{tabletopObjects.map(x=><code key={x}>{x}</code>)}</div></article><article><header><span>SHOT_110</span><b>INTERIOR · 15 KEYS</b></header><div>{interiorObjects.map(x=><code key={x}>{x}</code>)}</div></article></div></section>

  <section className="section b47-attacks"><div className="section-index">04 / FALSIFICATION SURFACE</div><div className="contact-heading"><div><p className="eyebrow"><span/> PRE-REGISTERED REJECTION REASONS</p><h2>不是只测 happy path。<br/><span>错误证据必须无法晋级。</span></h2></div><p>18 个攻击覆盖父实验身份、源 `.blend`、worker image、安全边界、采样、缺失子图、channel layout、NaN/Inf、Depth sentinel、Normal 范围、Vector 零值、Cryptomatte、pair hash、时间角色、额外 Docker 运行与 evidence self-hash。</p></div><div className="b47-attack-meter"><strong>18</strong><div><b>18 / 18 EXPECTED REJECTIONS</b><span/><code>independent audit = MATCH</code></div></div></section>

  <section className="section contact-limits" id="boundary"><div className="section-index">05 / WHAT THIS CLOSES</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> PRODUCTION REPRESENTATION CLOSED · CINEMA QUALITY OPEN</p><h2>现在有可合成的母版结构。<br/><span>还没有证明电影级生产点。</span></h2></div><p>B47 关闭的是 128×72、8 spp、Cycles CPU、两个短区间上的生产通道表示与跨构建复现。它不证明 2K/4K、去噪、运动模糊、景深、体积、毛发、皮肤、高频材质、人物表演、长镜头或 GPU 农场。B48 将固定同一镜头，逐级提高分辨率、采样与电影特性，测量质量收益、耗时、峰值内存、输出体积和可预测成本。</p></div><div className="b47-next"><span>NEXT FALSIFIABLE GATE</span><strong>B48</strong><div><b>QUALITY</b><i>↔</i><b>SAMPLES</b><i>↔</i><b>TIME</b><i>↔</i><b>COST</b></div><small>find the lowest defensible cinema-production point</small></div><div className="contact-artifacts"><a href={`${repo}experiments/codex-worker-production-pass-promotion-v0-1/results.json`}><span>MACHINE RESULT</span><b>evidence hash · 4 runs ↗</b></a><a href={`${repo}experiments/codex-worker-production-pass-promotion-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>8 EXR re-opens MATCH ↗</b></a><a href={`${repo}research/2026-08-26-b47-codex-worker-production-pass-promotion-result.md`}><span>RESULT NOTE</span><b>claims · non-claims ↗</b></a><a href={`${repo}research/2026-08-26-b47-codex-worker-production-pass-promotion-protocol.md`}><span>PREREGISTRATION</span><b>frozen before formal tools ↗</b></a></div></section>
  <footer><div><span className="brand-mark">BFS</span><b>B47 Production Passes</b></div><p>real `.blend` · multipart EXR · canonical pass arrays</p><Link href="/journal">回到实验日志 →</Link></footer>
</main>}
