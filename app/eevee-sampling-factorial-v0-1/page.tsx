import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const mediaBase = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio/eevee-sampling-factorial-v0-1' : '/eevee-sampling-factorial-v0-1';
export const metadata: Metadata = {
  title: 'B17 Eevee 采样因果实验｜Blender Film Studio',
  description: '真实 Blender 2×2 因子实验：1 sample 在两种 dither 下均为 144/144 像素 exact，32 samples 两组均非 exact；12/12 攻击通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/eevee-sampling-factorial-v0-1/' },
};

const attacks = [
  ['N01', 'factorial spec bytes', 'FACTORIAL_SPEC_SHA'],
  ['N02', 'ReviewRenderSpec bytes', 'REVIEW_SPEC_SHA'],
  ['N03', 'renderer bytes', 'RENDERER_SHA'],
  ['N04', 'comparator bytes', 'COMPARATOR_SHA'],
  ['N05', 'configurator bytes', 'CONFIGURATOR_SHA'],
  ['N06', 'dither factor level', 'DITHER_LEVEL'],
  ['N07', 'observed render samples', 'RENDER_SAMPLES'],
  ['N08', 'A/B directory alias', 'ALIAS_RUNS'],
  ['N09', 'missing frame', 'MISSING_FRAME'],
  ['N10', 'extra frame', 'EXTRA_FRAME'],
  ['N11', 'mutated frame bytes', 'FRAME_SHA'],
  ['N12', 'comparison sequence binding', 'COMPARISON_SEQUENCE_BINDING'],
];

export default function EeveeSamplingFactorialPage() {
  return <main className="contact-page factorial-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B17 导航"><Link href="/journal">实验日志</Link><Link href="/dither-isolation-v0-1">B16</Link><a href="#matrix">因子矩阵</a><a href="#quality">画质边界</a><a href="#next">下一实验</a></nav><span className="edition contact-edition">Sampling Factorial 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B17 · PRE-REGISTERED 2×2 FACTORIAL</p><h1>采样降到 1。<br /><span>精确复现回来了。</span></h1><p>8 个独立 Blender 5.2 进程按冻结顺序输出 1,152 帧。1/32 samples × dither 0/1 四个 cell 各做 A/B；门槛始终是 144/144、max error 0、failed pixels 0。</p></div><aside className="contact-gate"><b>PRE-REGISTERED DECISION</b><strong>SAMPLING<br />CAUSAL SUPPORT</strong><code>S01 · 288 / 288 exact frames</code><code>S32 · 258 / 288 exact frames</code><small>12 / 12 ATTACKS PASS</small></aside><div className="contact-stats"><article><strong>2×2</strong><span>完整因子</span><small>samples × dither</small></article><article><strong>8</strong><span>净 Blender 运行</span><small>two per cell</small></article><article><strong>1,152</strong><span>真实渲染帧</span><small>all receipt-bound</small></article><article><strong>12/12</strong><span>负向攻击</span><small>stable reasons</small></article></div></section>

    <section className="section contact-verdict" id="matrix"><div className="section-index">00 / 因子矩阵</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> WITHIN-CELL A/B · ZERO TOLERANCE</p><h2>不是一次幸运运行。<br /><span>四个 cell 全部重做。</span></h2></div><p>两组 sample=1 在 dither 0 与 1 下都严格 exact；两组 sample=32 都重复了非 exact 现象。失败像素很少仍然算失败，不追认感知容差。</p></div><div className="factorial-matrix"><article className="factorial-exact"><span>S01-D0</span><strong>144/144</strong><b>samples 1 · dither 0</b><small>0 failed · max 0</small></article><article className="factorial-exact"><span>S01-D1</span><strong>144/144</strong><b>samples 1 · dither 1</b><small>0 failed · max 0</small></article><article className="factorial-nonexact"><span>S32-D0</span><strong>132/144</strong><b>samples 32 · dither 0</b><small>88 failed pixels</small></article><article className="factorial-nonexact"><span>S32-D1</span><strong>126/144</strong><b>samples 32 · dither 1</b><small>113 failed pixels</small></article></div><div className="diagnostic-verdict"><b>DECISION</b><code>SAMPLING_CAUSAL_SUPPORT</code><p>在冻结场景、渲染器、Blender、OCIO 与比较方法下，改变采样数改变了 exact/non-exact 状态。它支持“多采样路径参与了漂移”，但没有证明具体是累积顺序、线程调度还是另一段内部求值逻辑。</p></div></section>

    <section className="section contact-evidence" id="quality"><div className="section-index light">01 / 视觉代价</div><div className="contact-heading"><div><p className="eyebrow"><span /> DIAGNOSTIC SETTING ≠ PRODUCTION SETTING</p><h2>精确，不代表精致。<br /><span>1 sample 明显更糟。</span></h2></div><p>同一第 72 帧、同为 dither 0：单采样呈现强烈噪点，32 采样明显平滑。B17 找到的是定位故障的干预，不是可交付的画质方案。</p></div><div className="factorial-gallery"><figure><Image src={`${mediaBase}/S01-D0-frame-0072.png`} alt="B02 第72帧，Eevee 1 sample、dither 0，画面存在明显噪点" width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>S01-D0 · FRAME 0072</span><b>严格复现 · 明显噪声</b><small>diagnostic only</small></figcaption></figure><figure><Image src={`${mediaBase}/S32-D0-frame-0072.png`} alt="B02 第72帧，Eevee 32 samples、dither 0，画面更平滑" width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>S32-D0 · FRAME 0072</span><b>更平滑 · 但非严格复现</b><small>132/144 exact</small></figcaption></figure></div><div className="contact-nonclaim"><b>NON-CLAIM</b><p>这两张图不是 A/B 差异可视化，而是采样质量对照。B17 没有把 sample=1 推荐为审片设置，也没有把像素 exact 等同于电影感、时间稳定性或母版质量。</p></div></section>

    <section className="section contact-diagnostic"><div className="section-index">02 / 对抗验证</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> TWELVE WAYS TO BREAK THE CLAIM</p><h2>工具、条件、帧与比较，<br /><span>都必须绑定正确。</span></h2></div><p>攻击全部作用于错误预期或 disposable 副本。特别验证比较报告确实对应 A/B 两条 sequence hash，而不是碰巧读取另一组目录。</p></div><ol className="contact-negative-list">{attacks.map(([id,item,result]) => <li key={id}><span>{id}</span><b>{item}</b><small>{result}</small></li>)}</ol></section>

    <section className="section contact-limits" id="next"><div className="section-index">03 / 下一可证伪边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> DOSE RESPONSE · COMPLETED IN B18</p><h2>因果支持之后，<br /><span>反例限制了外推。</span></h2></div><p>B18 已测试 samples 1/2/4/8/16/32，得到 F,T,F,F,F,F：sample=1 不再 exact，sample=2 恰好 exact。简单阈值被证伪，下一步需要更多重复而不是挑选幸运 cell。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/eevee-sampling-factorial-v0-1/results.json`}><span>RESULT</span><b>4 cells · 12 attacks ↗</b></a><a href={`${repo}experiments/eevee-sampling-factorial-v0-1/evidence/S01-D0.sequence.comparison.json`}><span>EXACT CELL</span><b>144 OIIO pairs ↗</b></a><a href={`${repo}research/2026-08-26-b17-eevee-sampling-factorial-result.md`}><span>RESULT NOTE</span><b>causal boundary ↗</b></a><Link href="/eevee-sampling-dose-response-v0-1"><span>B18</span><b>dose-response counterexample →</b></Link></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B17 Eevee Sampling Factorial</b></div><p>Causal support · visual quality still open</p><Link href="/research-agenda">进入下一实验 →</Link></footer>
  </main>;
}
