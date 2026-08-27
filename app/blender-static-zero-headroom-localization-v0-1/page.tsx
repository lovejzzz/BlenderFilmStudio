import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-static-zero-headroom-localization-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-3/occluding-planes-beauty.png';

export const metadata: Metadata = {
  title: 'B52-D12.4 零余量像素定位｜Blender Film Studio',
  description: '不重渲染、不改 D12.3：从冻结数组中定位唯一撞线像素，并逐项重放双线性采样与 float32 舍入。',
  alternates: { canonical },
  openGraph: { title: 'B52-D12.4 零余量像素定位', description: '唯一像素、3px 轮廓距离、2^-17 Vector 残差；半径 3 仍只是待验证假设。', url: canonical, images: [{ url: socialImage }] },
  twitter: { card: 'summary_large_image', title: 'B52-D12.4 零余量像素定位', description: '唯一像素、3px 轮廓距离、2^-17 Vector 残差。', images: [socialImage] },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

const arithmetic = [
  ['RAW VECTOR', '−7.62939453125e−6 px', '−2⁻¹⁷ · horizontal'],
  ['LOCAL Δ BLUE', '−0.2496735155582428', 'left tap − center'],
  ['WEIGHTED Δ', '−1.9048577541980194e−6', 'contrast × 2⁻¹⁷'],
  ['FINAL F32', '−1.9073486328125e−6', 'exactly 1 / 524288'],
] as const;

export default function BlenderStaticZeroHeadroomLocalizationPage() {
  return <main className="contact-page b51-page b52-page d11-page d111-page d12p-page d122-page d123-page d124-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.4 导航"><Link href="/blender-static-nonplanar-multiowner-v0-1">D12.3</Link><a href="#pixel">像素</a><a href="#arithmetic">算术</a><Link href="/blender-static-radius-intervention-v0-1">D12.5 干预</Link><Link href="/journal">日志</Link></nav>
      <span className="edition contact-edition">Localization D12.4</span>
    </header>

    <section className="contact-hero d124-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D12.4 · POST-HOC DEVELOPMENT DIAGNOSTIC</p><h1>不是一片噪声。<br/><span>是唯一一个像素。</span></h1><p>正式 D12.3 数组保持不变。独立 localizer 与 audit 把零余量追到遮挡前景的蓝通道，并逐字节重放它如何抵达冻结门槛。</p></div>
      <aside className="contact-gate d124-gate"><b>DIAGNOSTIC VERDICT</b><strong>PIXEL<br/>LOCALIZED</strong><code>D12.3 unchanged</code><code>radius 3 · unvalidated</code><small>post-hoc ≠ holdout</small></aside>
      <div className="contact-stats"><article><strong>1</strong><span>唯一并列最大值</span><small>x 56 · y 38 · blue</small></article><article><strong>3 px</strong><span>轮廓距离</span><small>radius-2 后第一圈</small></article><article><strong>30 / 30</strong><span>审计与攻击</span><small>15 base + 15 mutations</small></article><article><strong>0</strong><span>新增 Blender render</span><small>locked arrays only</small></article></div>
    </section>

    <section className="section d124-pixel" id="pixel">
      <div className="section-index">00 / UNIQUE GLOBAL MAXIMUM</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> OWNER · COORDINATE · CHANNEL</p><h2>前景遮挡体内部，<br/><span>第一圈有资格的像素。</span></h2></div><p>坐标 `(56, 38)` 属于 `FRONT_OCCLUDER`，Object Index 10454。半径 2 的同主体检查通过；它离最近主体断裂恰好 3px，因此成为冻结规则下最靠近高反差轮廓的 eligible ring。</p></div>
      <div className="d124-stage"><figure><Image src={`${basePath}/evidence/b52-d12-3/occluding-planes-beauty.png`} width={714} height={438} unoptimized alt="D12.3 遮挡平面 Blender Beauty display proxy"/><figcaption>正式 EXR 的 ACES display proxy · 决策仍来自 scene-linear float32</figcaption></figure><figure><Image src={`${basePath}/evidence/b52-d12-3/occluding-planes-domains.png`} width={714} height={438} unoptimized alt="D12.3 遮挡平面的 owner interior 与 boundary 诊断图"/><span className="d124-cross" aria-label="极值像素示意">+</span><figcaption><i/> interior <em/> rejected boundary · cross 为示意定位</figcaption></figure></div>
      <div className="d124-identity"><article><span>FIXTURE</span><strong>STATIC_OCCLUDING_PLANES_119X73</strong></article><article><span>OWNER</span><strong>FRONT_OCCLUDER · 10454</strong></article><article><span>VECTOR BITS</span><strong>b7000000 · 00000000</strong></article><article><span>SIGNED ERROR</span><strong>−1.9073486328125e−6</strong></article></div>
    </section>

    <section className="section d124-arithmetic" id="arithmetic">
      <div className="section-index">01 / REPLAYED FLOAT32 ARITHMETIC</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> ONE QUANTUM × LOCAL CONTRAST</p><h2>误差不是猜出来的。<br/><span>每一步都能重算。</span></h2></div><p>前一帧采样坐标是 `(55.99999237060547, 38)`。左侧 tap 权重恰为 `2^-17`；中心蓝值 0.6667997241 与左 tap 0.4171262085 的差，解释了几乎全部误差，最后一次 float32 cast 补上约 −2.49e−9。</p></div>
      <div className="d124-equation">{arithmetic.map((item, index) => <article key={item[0]}><span>{String(index + 1).padStart(2, '0')} · {item[0]}</span><strong>{item[1]}</strong><small>{item[2]}</small></article>)}</div>
      <div className="d124-tail"><div><span>distance 3</span><strong>100%</strong><i style={{width:'100%'}}/><small>1.9073486328125e−6 · full gate</small></div><div><span>distance ≥ 4 · occluding</span><strong>15.625%</strong><i style={{width:'15.625%'}}/><small>2.980232238769531e−7</small></div><div><span>distance ≥ 4 · all fixtures</span><strong>25%</strong><i style={{width:'25%'}}/><small>4.76837158203125e−7</small></div></div>
      <div className="contact-nonclaim"><b>MEASURED ≠ INTERNAL CAUSE</b><p>这里建立的是图像空间算术定位。Depth Laplacian 只是一种代理；它不能证明几何曲率、Blender Vector 实现或某个未公开量化步骤是内部成因。</p></div>
    </section>

    <section className="section d124-next" id="next">
      <div className="section-index">02 / FRESH INTERVENTION REQUIRED</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> DERIVE HERE · TEST ELSEWHERE</p><h2>半径 3 是候选修正。<br/><span>还不是生产结论。</span></h2></div><p>在复用数组上把 erosion 从 2 提到 3，会移除撞线尾部，并把三场景最大值降到门槛的 25%。这是同数据上的事后推导。下一项 D12.5 必须在看到新输出前冻结半径 3，以半径 2 为控制，并防止靠“遮掉更多像素”购买成功。</p></div>
      <div className="d12p-failures d124-contract"><article className="control"><span>CONTROL</span><strong>RADIUS 2</strong><b>unchanged threshold</b><p>保留原规则，测量 fresh 几何上的尾部。</p></article><article className="candidate"><span>INTERVENTION</span><strong>RADIUS 3</strong><b>fresh holdout only</b><p>预注册后才渲染；不得用 D12.3 当验证集。</p></article><article className="coverage"><span>ANTI-GAMING</span><strong>COVERAGE</strong><b>retention gate required</b><p>同步报告 eligible pixels，避免空 mask 伪装通过。</p></article></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-static-zero-headroom-localization-v0-1/results.json`}><span>MACHINE RESULT</span><b>16 / 16 checks ↗</b></a><a href={`${repo}experiments/blender-static-zero-headroom-localization-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>15 + 15 PASS ↗</b></a><a href={`${repo}specs/blender-static-zero-headroom-localization.v0.1.json`}><span>FROZEN SPEC</span><b>decision role locked ↗</b></a><a href={`${repo}research/2026-08-27-b52-d12-4-zero-headroom-localization-result.md`}><span>RESULT NOTE</span><b>limits + next test ↗</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.4 Zero-headroom Localization</b></div><p>one pixel localized · D12.3 unchanged · radius 3 unvalidated</p><Link href="/journal">继续看实验日志 →</Link></footer>
  </main>;
}
