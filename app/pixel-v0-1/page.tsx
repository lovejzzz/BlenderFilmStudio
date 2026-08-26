import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const publicUrl = 'https://lovejzzz.github.io/BlenderFilmStudio/pixel-v0-1/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'PixelSpec v0.1｜4K EXR 实测｜Blender Film Studio',
  description: 'Blender 5.2、Cycles CPU、4K/512spp、ACES 2：四个代表帧双渲染、multipart EXR 逐像素比较与 mastering 元数据实测。',
  alternates: { canonical: publicUrl },
  openGraph: {
    title: 'PixelSpec v0.1：像素精确，文件字节不同',
    description: '8 次 4K 渲染；32 个逻辑通道、8 个 EXR parts；同机逐像素零误差。',
    url: publicUrl,
  },
  twitter: { card: 'summary_large_image', title: 'BFS PixelSpec v0.1', description: '4K EXR reproducibility, measured.' },
};

const samples = [
  { id: 'B01 · 0001', title: '材质静物', seconds: '357.75 / 369.53 s', size: '61.0 MB', sha: 'DIFFERENT', pixel: 'EXACT', image: 'B01-frame-0001.png' },
  { id: 'B02 · 0001', title: 'Dolly 起点', seconds: '327.82 / 309.52 s', size: '176.1 MB', sha: 'DIFFERENT', pixel: 'EXACT', image: 'B02-frame-0001.png' },
  { id: 'B02 · 0072', title: '线性插值中点', seconds: '326.15 / 317.08 s', size: '156.0 MB', sha: 'DIFFERENT', pixel: 'EXACT', image: 'B02-frame-0072.png' },
  { id: 'B02 · 0144', title: 'Dolly 终点', seconds: '301.55 / 311.76 s', size: '166.7 MB', sha: 'DIFFERENT', pixel: 'EXACT', image: 'B02-frame-0144.png' },
];

const parts = [
  ['01', 'Combined', 'R · G · B · A'],
  ['02', 'Depth', 'Z'],
  ['03', 'Normal', 'X · Y · Z'],
  ['04', 'Vector', 'X · Y · Z · W'],
  ['05–07', 'CryptoObject', '00 · 01 · 02 / RGBA'],
  ['08', 'Noisy Image', 'R · G · B · A'],
];

const references = [
  ['OpenImageIO 3.1.13', 'Image comparison and statistics', 'https://openimageio.readthedocs.io/en/v3.0.13.0/imagebufalgo.html#image-comparison-and-statistics'],
  ['OpenImageIO 3.1.13', 'Metadata conventions', 'https://openimageio.readthedocs.io/en/v3.1.13.0/stdmetadata.html'],
  ['OpenEXR', 'Standard attributes', 'https://openexr.com/en/latest/StandardAttributes.html'],
  ['OpenColorIO Config ACES', 'v4.0.0 · ACES 2.0', 'https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/releases/tag/v4.0.0'],
  ['Blender 5.2 API', 'RenderSettings', 'https://docs.blender.org/api/5.2/bpy.types.RenderSettings.html'],
];

export default function PixelV01Page() {
  return (
    <main className="pixel-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="像素实验导航"><Link href="/">技术基线</Link><Link href="/compiler-v0-1">编译实验</Link><Link href="/cost-model">成本</Link><Link href="/research-agenda">研究路线</Link><Link className="actor-route" href="/actor-v0-1">角色实验</Link><a href="#results">结果</a><a href="#mastering">Mastering</a></nav>
        <span className="edition pixel-edition">Pixel 0.1</span>
      </header>

      <section className="pixel-hero">
        <div className="pixel-raster" aria-hidden="true" />
        <div className="pixel-hero-copy"><p className="eyebrow"><span /> 4K · 512 SPP · ACES 2 · EXECUTED</p><h1>文件不同。<br /><span>像素完全相同。</span></h1><p>四个代表帧各渲染两次。8 个 multipart 子图全部逐像素零误差；原生 EXR 缺失的交付元数据，再由可验证 mastering 步骤补齐。</p></div>
        <div className="pixel-proof"><b>PIXEL CONTRACT</b><code>MAX ABS ERROR&nbsp;&nbsp;0.0</code><code>FAIL PIXELS&nbsp;&nbsp;&nbsp;&nbsp;0</code><code>NaN / Inf&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;0 / 0</code><code>FILE SHA A = B&nbsp;&nbsp;FALSE</code><span>4 / 4 REPRESENTATIVE FRAMES PASS</span></div>
        <div className="pixel-stats"><article><strong>8</strong><span>4K 终稿渲染</span><small>4 帧 × 2 次</small></article><article><strong>8</strong><span>EXR parts / 帧</span><small>32 个逻辑通道</small></article><article><strong>5:28</strong><span>平均每帧</span><small>CPU · 固定 8 线程</small></article><article><strong>1.0 GB</strong><span>实验原始文件</span><small>不进入 Git</small></article></div>
      </section>

      <section className="section pixel-verdict">
        <div className="section-index">00 / 有限结论</div>
        <div className="pixel-heading dark-heading"><div><p className="eyebrow dark"><span /> PROVEN ON ONE DEVICE CLASS</p><h2>受限相机动画，<br />可以<span>精确复现。</span></h2></div><p>在同一台 darwin-arm64 机器、Blender 5.2.0 LTS、Cycles CPU、固定 8 线程与 seed、512 samples、同一 ACES 2 OCIO 配置下，B01 与 B02 的起点、中点、终点均逐像素一致。</p></div>
        <div className="pixel-boundary"><b>不能外推</b><span>不同 GPU</span><span>不同驱动</span><span>不同 OS</span><span>角色表演</span><span>布料 / 毛发 / 流体</span><span>影院审美</span></div>
      </section>

      <section className="section pixel-results" id="results">
        <div className="section-index light">01 / 双渲染证据</div>
        <div className="pixel-heading"><div><p className="eyebrow"><span /> CONTENT ≠ CONTAINER</p><h2>SHA 不同，<br />不是噪声漂移。</h2></div><p>每一对 EXR 的文件 SHA-256 都不同，主要因为 Cycles 写入的时间统计不同；解码后分别比较每个 part，平均误差、RMS 与最大绝对误差全部为 0。</p></div>
        <div className="pixel-sample-grid">{samples.map(sample => <article key={sample.id}><Image src={`${imageBasePath}/compiler-v0-1/${sample.image}`} alt={`${sample.id} ${sample.title} 的编译场景预览`} width={960} height={540} sizes="(max-width: 760px) 100vw, 50vw" /><header><span>{sample.id}</span><b>{sample.pixel}</b></header><h3>{sample.title}</h3><dl><div><dt>RUN A / B</dt><dd>{sample.seconds}</dd></div><div><dt>ONE EXR</dt><dd>{sample.size}</dd></div><div><dt>FILE SHA</dt><dd className="pixel-warn">{sample.sha}</dd></div><div><dt>PIXELS</dt><dd>{sample.pixel}</dd></div></dl></article>)}</div>
        <p className="pixel-image-note">图像为同一编译场景的网页预览；数值结论来自未压缩到网页的 3840×2160 HALF multipart EXR 原始文件与 OIIO 报告。</p>
      </section>

      <section className="section pixel-parts">
        <div className="section-index">02 / EXR 结构</div>
        <div className="pixel-heading dark-heading"><div><p className="eyebrow dark"><span /> OPENEXR MULTIPART</p><h2>不只看 Combined，<br />后期数据也要一致。</h2></div><p>Blender 5.2 将本实验输出组织为 8 个 parts。验收覆盖可见画面、深度、法线、运动向量和 Cryptomatte；任何一个 part 漂移，都不能算通过。</p></div>
        <div className="pixel-part-grid">{parts.map(([id, title, channels]) => <article key={id}><span>{id}</span><h3>{title}</h3><code>{channels}</code></article>)}</div>
        <div className="pixel-checkline"><span>3840 × 2160</span><span>HALF</span><span>ZIP LOSSLESS</span><span>0 NaN</span><span>0 Infinity</span><span>ALL PASSES PRESENT</span></div>
      </section>

      <section className="section pixel-mastering" id="mastering">
        <div className="section-index light">03 / Mastering 闭环</div>
        <div className="pixel-heading"><div><p className="eyebrow"><span /> NATIVE GAP → VERIFIED TRANSFORM</p><h2>Blender 缺的元数据，<br />补写但<span>不改像素。</span></h2></div><p>原生 EXR 未包含 OutputSpec 要求的五项交付属性。master_exr 使用 Blender 自带 OpenImageIO 复制 multipart 数据并写入标准属性，再把输出与源文件逐 part 比较。</p></div>
        <div className="master-flow"><article><span>01</span><b>Native EXR</b><small>passes ✓ · metadata ×</small></article><i>→</i><article><span>02</span><b>OIIO mastering</b><small>copy parts + attributes</small></article><i>→</i><article><span>03</span><b>Master EXR</b><small>passes ✓ · metadata ✓</small></article><i>→</i><article><span>04</span><b>Pixel compare</b><small>max error 0.0</small></article></div>
        <div className="metadata-grid"><article><span>chromaticities</span><b>ACEScg / AP1 · D60</b></article><article><span>framesPerSecond</span><b>24 / 1</b></article><article><span>timeCode</span><b>SMPTE packed</b></article><article><span>owner</span><b>Copyright alias</b></article><article><span>comments</span><b>ImageDescription alias</b></article></div>
        <div className="master-verdict"><b>4 / 4 MASTERING PASS</b><p>属性齐全 · Pass 保留 · 有限值 · 写回前后逐像素零误差</p></div>
      </section>

      <section className="section pixel-cost">
        <div className="section-index">04 / 成本实测</div>
        <div className="pixel-heading dark-heading"><div><p className="eyebrow dark"><span /> SOFTWARE FREE ≠ COMPUTE FREE</p><h2>最小现金成本低，<br />渲染吞吐并不免费。</h2></div><p>8 次正式渲染累计 2,621 秒，平均 327.65 秒/帧。按 24 fps 串行换算，这台机器完成一秒同复杂度画面约需 2.18 小时；一帧平均约 140 MB。</p></div>
        <div className="pixel-cost-grid"><article><strong>43:41</strong><span>正式渲染总时长</span><small>8 frames · 不含 smoke</small></article><article><strong>2.18 h</strong><span>每秒成片机器时间</span><small>简单 benchmark 下限</small></article><article><strong>3.36 GB</strong><span>每秒原生 EXR</span><small>约 140 MB × 24</small></article></div>
        <Link className="pixel-cost-link" href="/cost-model">查看更新后的完整成本模型 →</Link>
      </section>

      <section className="section pixel-sources">
        <div className="section-index light">05 / 可重跑证据</div>
        <div className="pixel-heading"><div><p className="eyebrow"><span /> REPORTS, NOT 1 GB BINARIES</p><h2>原始 EXR 留在本地，<br />报告进入版本控制。</h2></div><p>Git 保存 PixelSpec、渲染器、mastering 工具、每个 frame 的通道/统计/差异报告与汇总；巨大的 EXR 运行产物被明确忽略，避免把仓库变成无法审计的二进制仓库。</p></div>
        <div className="pixel-artifacts"><a href="https://github.com/lovejzzz/BlenderFilmStudio/tree/main/experiments/pixel-v0-1" target="_blank" rel="noreferrer"><span>PIXEL EXPERIMENT</span><b>results · inspections ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/tree/main/experiments/mastering-v0-1" target="_blank" rel="noreferrer"><span>MASTERING</span><b>conformance · comparisons ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/specs/pixel-spec.v0.1.json" target="_blank" rel="noreferrer"><span>CONTRACT</span><b>PixelSpec v0.1 ↗</b></a></div>
        <ol className="references pixel-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
        <div className="pixel-next"><span>NEXT EVIDENCE LAYER</span><div><h3>B03 · ActorSpec v0.1</h3><p>角色合同、资产审计、负向 Driver 测试与逐帧求值已经执行。<Link href="/actor-v0-1">查看角色身份、眼神轴反例与 SceneSpec 集成缺口 →</Link></p></div></div>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>PixelSpec v0.1</b></div><p>Blender 5.2.0 LTS · 4K EXR · same-machine proof</p><Link href="/actor-v0-1">进入角色实验 →</Link></footer>
    </main>
  );
}
