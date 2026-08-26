import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const publicUrl = 'https://lovejzzz.github.io/BlenderFilmStudio/compiler-v0-1/';
const previewUrl = 'https://lovejzzz.github.io/BlenderFilmStudio/compiler-v0-1/B01-frame-0001.png';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'Blender 编译器 v0.1 实验｜Blender Film Studio',
  description: 'SceneSpec 经不可变 BuildPlan 编译进原生 Blender 5.2.0 LTS：B01/B02 双净构建、结构哈希、篡改拒绝与真实预览证据。',
  alternates: { canonical: publicUrl },
  openGraph: {
    title: 'Blender 编译器 v0.1 实验',
    description: '两次净构建结构一致；.blend 二进制并不相同。',
    url: publicUrl,
    images: [{ url: previewUrl, width: 960, height: 540, alt: 'B01 材质静物编译预览' }],
  },
  twitter: { card: 'summary_large_image', title: 'Blender 编译器 v0.1', description: '从可拒绝合同进入可复现场景。', images: [previewUrl] },
};

const results = [
  {
    id: 'B01', title: '材质静物', shot: 'SHOT_101', plan: '316114f1…3eaf', structure: 'c699fc27…7f0b',
    verdict: 'PASS', detail: '皮革、金属、玻璃、肤色卡、双灯与 58mm 摄影机。',
  },
  {
    id: 'B02', title: '室内 Dolly', shot: 'SHOT_102', plan: 'a9022bf6…6687', structure: '025c6fa5…856d',
    verdict: 'PASS', detail: '144 帧、24fps、摄影机线性关键帧、室内集合、道具与窗光。',
  },
];

const findings = [
  ['F01', '合同确实缺少运动', '原 B02 只有“Dolly”标题，没有摄影机动画。v0.1 现加入受限 transformKeys，并验证帧范围与严格顺序。'],
  ['F02', 'EEVEE 标识已变化', '原合同写 BLENDER_EEVEE_NEXT；Blender 5.2.0 实际接受 BLENDER_EEVEE。实验已修正 schema，而不是在运行时猜测。'],
  ['F03', 'EXR 是两阶段设置', 'Blender 5.2 需先把 media_type 设为 MULTI_LAYER_IMAGE，才允许 OPEN_EXR_MULTILAYER；旧式单字段赋值会失败。'],
  ['F04', 'Action 旧 API 已删除', 'Blender 5.2 不再提供 action.fcurves；编译器改用 Action Slot → Channelbag → F-Curves，并在 manifest 中记录插值。'],
  ['F05', '.blend 字节不稳定', '相同计划的两个 .blend SHA-256 不同，但规范化结构、关键帧、资产与渲染设置的结构哈希相同。'],
  ['F06', 'ACES 2 配置已锁定', 'cg-config-v4.0.0 / ACES 2.0 已按文件与 SHA-256 固定；物理审片显示校准仍是独立的未完成项。'],
];

const references = [
  ['Blender 5.2 API', 'Data-block creation and removal', 'https://docs.blender.org/api/5.2/info_quickstart.html'],
  ['Blender 5.2 API', 'BlendDataLibraries.load', 'https://docs.blender.org/api/5.2/bpy.types.BlendDataLibraries.html'],
  ['Blender 5.2 API', 'ActionChannelbag F-Curves', 'https://docs.blender.org/api/5.2/bpy.types.ActionChannelbag.html'],
  ['Blender 5.2 API', 'Animation quickstart', 'https://docs.blender.org/api/5.2/info_quickstart.html#animation'],
  ['Blender 5.2 API', 'ImageFormatSettings', 'https://docs.blender.org/api/5.2/bpy.types.ImageFormatSettings.html'],
  ['Blender 5.2 API', 'Save current file', 'https://docs.blender.org/api/5.2/bpy.ops.wm.html#bpy.ops.wm.save_as_mainfile'],
];

const gallery = [
  ['B01-frame-0001.png', 'B01 · FRAME 0001', '材质静物：编译器导入的资产集合、双灯与摄影机。'],
  ['B02-frame-0001.png', 'B02 · FRAME 0001', 'Dolly 起点：左侧近景遮挡保留了镜头空间关系。'],
  ['B02-frame-0072.png', 'B02 · FRAME 0072', '中间帧：从 Blender 5.2 的线性 F-Curve 求值，而不是页面插值。'],
  ['B02-frame-0144.png', 'B02 · FRAME 0144', 'Dolly 终点：同一资产与灯光下的确定性摄影机推进。'],
];

export default function CompilerV01Page() {
  return (
    <main className="compiler-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="编译实验导航"><Link href="/">技术基线</Link><Link href="/blender-5-2">Blender 5.2</Link><Link href="/research-agenda">研究路线</Link><Link href="/spec-v0-1">规格 v0.1</Link><Link href="/pixel-v0-1">像素实验</Link><Link className="actor-route" href="/actor-v0-1">角色实验</Link><Link className="contact-route" href="/contact-v0-1">接触实验</Link><Link href="/grasp-v0-1">手指抓握</Link><a href="#results">结果</a></nav>
        <span className="edition compiler-edition">Compiler 0.1</span>
      </header>

      <section className="compiler-hero">
        <div className="compiler-grid" aria-hidden="true" />
        <div className="compiler-hero-copy"><p className="eyebrow"><span /> NATIVE BLENDER 5.2.0 LTS · EXECUTED</p><h1>从<span>可拒绝合同</span><br />进入<span>可复现场景。</span></h1><p>这不是架构图。B01 与 B02 已经由同一条 SceneSpec → BuildPlan → Blender 编译链各执行两次，并留下场景 manifest、结构哈希、篡改测试和真实预览。</p></div>
        <div className="compiler-proof"><header><span>experiment:compiler</span><b>ALL STRUCTURAL CHECKS PASSED</b></header><code>B01 · c699fc27…7f0b</code><code>B02 · 025c6fa5…856d</code><code>TAMPERED PLAN · REJECTED × 2</code><small>.blend bytes differ · structure matches</small></div>
        <div className="compiler-stats"><article><strong>2</strong><span>基准镜头</span><small>B01 + B02</small></article><article><strong>4</strong><span>净构建</span><small>每镜头两次</small></article><article><strong>2/2</strong><span>结构一致</span><small>SHA-256 manifest</small></article><article><strong>4</strong><span>真实预览</span><small>Blender EEVEE</small></article></div>
      </section>

      <section className="section compiler-verdict">
        <div className="section-index">00 / 实验结论</div>
        <div className="compiler-verdict-grid"><div><p className="eyebrow dark"><span /> PROVEN, WITH LIMITS</p><h2>最小“电影编译器”<br />已经<span>运行。</span></h2></div><div><b>可以确认</b><p>同一受限计划能在 Blender 5.2 中复建相同的资产拓扑、对象参数、摄影机关键帧与渲染设置。</p><b>后续证据</b><p>同机 4K EXR 像素实验已通过；跨设备一致性、物理显示校准、人物表演与电影审美仍未证明。</p></div></div>
        <div className="compiler-acceptance"><span>ACCEPTANCE UNIT</span><b>canonical scene structure</b><p>不是 `.blend` 文件字节，也不是一张看起来相似的截图。</p></div>
      </section>

      <section className="section compiler-system">
        <div className="section-index light">01 / 已执行系统</div>
        <div className="compiler-heading"><div><p className="eyebrow"><span /> DOUBLE VERIFICATION</p><h2>每一层都只接受<br /><span>比自己更窄的数据。</span></h2></div><p>Node 端验证 SceneSpec、路径、许可与资产哈希；BuildPlan 自带内容哈希；Blender 端再次验证计划与资产，然后才调用固定的 data API。</p></div>
        <div className="compiler-flow"><article><span>01</span><b>SceneSpec</b><small>22 fixtures</small></article><i>→</i><article><span>02</span><b>BuildPlan</b><small>canonical + hashed</small></article><i>→</i><article><span>03</span><b>Blender 5.2</b><small>data API + allowlist</small></article><i>→</i><article><span>04</span><b>Manifest</b><small>normalized structure</small></article><i>→</i><article><span>05</span><b>Compare</b><small>accept / reject</small></article></div>
        <div className="compiler-security"><b>模型没有得到的权限</b><span>任意 Python</span><span>网络</span><span>绝对路径</span><span>未锁定资产</span><span>绕过 BuildPlan</span></div>
      </section>

      <section className="section compiler-results" id="results">
        <div className="section-index">02 / 双净构建</div>
        <div className="compiler-heading dark-heading"><div><p className="eyebrow dark"><span /> B01 + B02</p><h2>两个不同问题，<br />同一编译合同。</h2></div><p>B01 压力测试材质与高光场景的结构；B02 压力测试 144 帧摄影机求值。两者都从空场景开始，不复用上一次构建状态。</p></div>
        <div className="compiler-result-grid">{results.map(result => <article key={result.id}><header><span>{result.id}</span><b>{result.verdict}</b></header><h3>{result.title}</h3><p>{result.detail}</p><dl><div><dt>SHOT</dt><dd>{result.shot}</dd></div><div><dt>PLAN</dt><dd>{result.plan}</dd></div><div><dt>STRUCTURE</dt><dd>{result.structure}</dd></div><div><dt>CLEAN A = B</dt><dd>TRUE</dd></div><div><dt>.BLEND A = B</dt><dd className="warning">FALSE</dd></div></dl></article>)}</div>
        <div className="binary-finding"><span>关键发现</span><div><h3>结构确定，不等于容器字节确定。</h3><p>Blender 保存的二进制包含不适合作为镜头验收依据的内部状态。我们保留两个不同的文件哈希作为反证，并把可解释的结构 manifest 设为主验收物。</p></div></div>
      </section>

      <section className="section compiler-evidence" id="evidence">
        <div className="section-index light">03 / 真实预览</div>
        <div className="compiler-heading"><div><p className="eyebrow"><span /> COMPILED PIXELS · NOT MASTER</p><h2>这些图来自编译场景，<br />不是 AI 视频模型。</h2></div><p>960×540、Blender EEVEE、32 samples，仅用于检查资产、灯光、构图和摄影机运动是否被编译。它们不是 4K EXR，也不参与电影感结论。</p></div>
        <div className="compiler-gallery">{gallery.map(([file, label, description], index) => <figure key={file} className={index === 0 ? 'wide' : ''}><Image src={`${imageBasePath}/compiler-v0-1/${file}`} width={960} height={540} sizes={index === 0 ? '(max-width: 760px) 100vw, 66vw' : '(max-width: 760px) 100vw, 33vw'} alt={description} /><figcaption><b>{label}</b><p>{description}</p></figcaption></figure>)}</div>
      </section>

      <section className="section compiler-findings">
        <div className="section-index">04 / Blender 5.2 实证修正</div>
        <div className="compiler-heading dark-heading"><div><p className="eyebrow dark"><span /> API REALITY</p><h2>文档里的架构，<br />必须服从运行时事实。</h2></div><p>六项修正都来自 Blender 5.2.0 LTS 的真实执行。它们说明版本锁定不是形式工作，而是编译系统正确性的组成部分。</p></div>
        <div className="compiler-findings-grid">{findings.map(([id, title, detail]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
      </section>

      <section className="section compiler-next">
        <div className="section-index light">05 / 后续证据层 · 已执行</div>
        <div className="compiler-heading"><div><p className="eyebrow"><span /> PIXEL CONTRACT · PASS</p><h2>结构之后，<br />像素也接受了<span>审判。</span></h2></div><p>固定 ACES 2 配置后，B01 与 B02 四个代表帧各执行两次 4K/512spp Cycles CPU 渲染。所有 multipart EXR 解码后逐像素零误差。</p></div>
        <div className="pixel-gates"><article><span>G01 · PASS</span><b>Pin OCIO</b><p>配置、版本、SHA-256 与 display/view 已锁定。</p></article><article><span>G02 · PASS</span><b>Render EXR</b><p>4 帧 × 2 次真实 4K Multi-layer EXR。</p></article><article><span>G03 · PASS*</span><b>Inspect</b><p>Pass 与有限值通过；原生元数据由 mastering 补齐。</p></article><article><span>G04 · PASS</span><b>Compare</b><p>8 个 parts 全部 max error = 0。</p></article></div>
        <div className="compiler-nonclaim"><b>进入 PixelSpec</b><p><Link href="/pixel-v0-1">查看 8 次 4K 渲染、EXR 通道、逐像素差异、mastering 与成本实测 →</Link></p></div>
      </section>

      <section className="section compiler-sources">
        <div className="section-index">06 / 可审计材料</div>
        <div className="compiler-heading dark-heading"><div><p className="eyebrow dark"><span /> REPOSITORY IS THE RECORD</p><h2>结论对应文件，<br />文件对应可重跑实验。</h2></div><p>BuildPlan、两次 manifest、实验汇总、基准 SceneSpec、资产生成器和 Blender 编译器都进入版本控制；页面不替代原始证据。</p></div>
        <div className="compiler-artifacts"><a href="https://github.com/lovejzzz/BlenderFilmStudio/tree/main/experiments/compiler-v0-1" target="_blank" rel="noreferrer"><span>EXPERIMENT</span><b>plans · manifests · results ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/blender/compile_scene.py" target="_blank" rel="noreferrer"><span>BLENDER</span><b>restricted compiler ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/tree/main/specs/benchmarks" target="_blank" rel="noreferrer"><span>BENCHMARKS</span><b>B01 · B02 SceneSpec ↗</b></a></div>
        <ol className="references compiler-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>Compiler Experiment v0.1</b></div><p>Native Blender 5.2.0 LTS · B01/B02 structural proof</p><Link href="/pixel-v0-1">进入像素实验 →</Link></footer>
    </main>
  );
}
