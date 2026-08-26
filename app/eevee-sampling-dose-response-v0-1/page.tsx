import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const mediaBase = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio/eevee-sampling-dose-response-v0-1' : '/eevee-sampling-dose-response-v0-1';
export const metadata: Metadata = {
  title: 'B18 Eevee 采样剂量响应｜Blender Film Studio',
  description: '真实 Blender 1/2/4/8/16/32 samples 剂量实验得到 F,T,F,F,F,F：不存在简单单调确定性阈值；13/13 攻击通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/eevee-sampling-dose-response-v0-1/' },
};

const cells = [
  ['S01', '1', '143/144', '30 codes', false],
  ['S02', '2', '144/144', '0 codes', true],
  ['S04', '4', '140/144', '7 codes', false],
  ['S08', '8', '137/144', '4 codes', false],
  ['S16', '16', '137/144', '2 codes', false],
  ['S32', '32', '133/144', '1 code', false],
] as const;
const attacks = [
  ['N01','dose spec','DOSE_SPEC_SHA'],['N02','base review spec','BASE_REVIEW_SPEC_SHA'],['N03','derived review spec','DERIVED_REVIEW_SPEC_SHA'],
  ['N04','renderer','RENDERER_SHA'],['N05','comparator','COMPARATOR_SHA'],['N06','configurator','CONFIGURATOR_SHA'],['N07','fixed dither','FIXED_DITHER'],
  ['N08','observed samples','RENDER_SAMPLES'],['N09','run alias','ALIAS_RUNS'],['N10','missing frame','MISSING_FRAME'],['N11','extra frame','EXTRA_FRAME'],
  ['N12','frame bytes','FRAME_SHA'],['N13','comparison binding','COMPARISON_SEQUENCE_BINDING'],
];
const witnesses = [
  ['S01','1 sample','143/144 exact'],['S02','2 samples','144/144 exact'],['S08','8 samples','137/144 exact'],['S32','32 samples','133/144 exact'],
];

export default function EeveeSamplingDoseResponsePage() {
  return <main className="contact-page dose-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B18 导航"><Link href="/journal">实验日志</Link><Link href="/eevee-sampling-factorial-v0-1">B17</Link><a href="#vector">结果向量</a><a href="#quality">画质</a><a href="#next">下一实验</a></nav><span className="edition contact-edition">Sampling Dose 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B18 · SIX-LEVEL DOSE RESPONSE</p><h1>不是一条阈值线。<br /><span>结果是 F T F F F F。</span></h1><p>固定 dither=0，1/2/4/8/16/32 samples 各做两次完整 144 帧净运行。样本 1 没有复现 B17 的 exact；样本 2 恰好 exact；更高采样全部非 exact。</p></div><aside className="contact-gate"><b>PRE-REGISTERED DECISION</b><strong>NON-MONOTONIC<br />OR UNSTABLE</strong><code>vector · F T F F F F</code><code>12 runs · 1,728 frames</code><small>13 / 13 ATTACKS PASS</small></aside><div className="contact-stats"><article><strong>6</strong><span>采样级别</span><small>powers of two</small></article><article><strong>12</strong><span>净运行</span><small>two per level</small></article><article><strong>1,728</strong><span>真实帧</span><small>all receipt-bound</small></article><article><strong>13/13</strong><span>负向攻击</span><small>stable reasons</small></article></div></section>

    <section className="section contact-verdict" id="vector"><div className="section-index">00 / Exactness vector</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> ZERO TOLERANCE · WITHIN-LEVEL A/B</p><h2>一次 exact，<br /><span>不能叫做确定性。</span></h2></div><p>如果存在简单单调边界，exact 应该形成连续前缀、non-exact 形成连续后缀。实际 1 sample 先失败、2 samples 通过、4–32 再失败，因此按冻结规则不能选中间的幸运 cell 当答案。</p></div><div className="dose-strip">{cells.map(([id,samples,frames,error,exact]) => <article className={exact ? 'dose-exact' : 'dose-nonexact'} key={id}><span>{id}</span><strong>{samples}</strong><b>samples</b><code>{frames}</code><small>{error} max</small></article>)}</div><div className="diagnostic-verdict"><b>DECISION</b><code>NON_MONOTONIC_OR_UNSTABLE</code><p>B17 对采样数的因果支持仍是有效的批内结果；B18 提供了反例，证明不能扩大成“1 sample 总是确定”或“2 samples 已解决”。</p></div></section>

    <section className="section contact-evidence"><div className="section-index light">01 / 新测量模式</div><div className="contact-heading"><div><p className="eyebrow"><span /> MAX ERROR · APPROXIMATE 8-BIT CODES</p><h2>采样越多，最大漂移越小。<br /><span>但 exact 并不单调。</span></h2></div><p>非 exact cells 的最大误差约为 30、7、4、2、1 个 8-bit code。这个阶梯与随机贡献被更多样本平均相容，但它不是 Eevee 内部随机数、竞态或累积算法的源码级证明。</p></div><div className="dose-error-ladder">{[['1','30',90],['2','0',0],['4','7',21],['8','4',12],['16','2',6],['32','1',3]].map(([sample,codes,width]) => <article key={sample}><span>{sample} spp</span><div><i style={{width: `${width}%`}} /></div><b>{codes} code{codes === '1' ? '' : 's'}</b></article>)}</div><div className="contact-nonclaim"><b>INFERENCE · NOT FACT</b><p>帧 9、83、91、103、104、144 在多个采样级别重复出现差异，部分坐标接近。它提示局部随机采样/求值贡献，但还没有证明根因，也没有排除调度因素。</p></div></section>

    <section className="section contact-limits" id="quality"><div className="section-index">02 / 画质剂量</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> SAME FRAME 72 · DITHER 0</p><h2>质量随采样改善。<br /><span>复现状态却会跳变。</span></h2></div><p>四张真实 Blender witness 显示噪声随采样数下降。2-sample 这次 exact 并不因此成为生产设置；32-sample 视觉更平滑，但严格像素复现仍失败。</p></div><div className="factorial-gallery dose-gallery">{witnesses.map(([id,title,note]) => <figure key={id}><Image src={`${mediaBase}/${id}-frame-0072.png`} alt={`B02 第72帧，Eevee ${title}、dither 0`} width={960} height={540} sizes="(max-width: 700px) 100vw, 50vw" /><figcaption><span>{id} · FRAME 0072</span><b>{title}</b><small>{note}</small></figcaption></figure>)}</div></section>

    <section className="section contact-diagnostic"><div className="section-index">03 / 对抗验证</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> THIRTEEN STABLE REASONS</p><h2>派生合同也必须，<br /><span>逐字节证明只改一项。</span></h2></div><p>除了工具、帧和比较绑定，B18 还攻击基础 ReviewRenderSpec 与六份派生 spec 的身份，防止“采样剂量”暗中带入其他配置差异。</p></div><ol className="contact-negative-list">{attacks.map(([id,item,result]) => <li key={id}><span>{id}</span><b>{item}</b><small>{result}</small></li>)}</ol></section>

    <section className="section contact-limits" id="next"><div className="section-index">04 / 下一可证伪边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> REPLICATION DEPTH · NOT MORE CHERRY-PICKING</p><h2>下一步增加重复次数，<br /><span>不是继续挑幸运 setting。</span></h2></div><p>B19 应在 samples 1 与 2 上预注册多次完整序列，固定全配对或参考配对图、置信区间与停止规则，估计 complete-shot exact 的出现频率；同时从真实 Blender 5.2 RNA 枚举可控 seed/求值参数。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/eevee-sampling-dose-response-v0-1/results.json`}><span>RESULT</span><b>vector · 13 attacks ↗</b></a><a href={`${repo}experiments/eevee-sampling-dose-response-v0-1/evidence/S01.sequence.comparison.json`}><span>S01 COUNTEREXAMPLE</span><b>frame 89 · 30 codes ↗</b></a><a href={`${repo}research/2026-08-26-b18-eevee-sampling-dose-response-result.md`}><span>RESULT NOTE</span><b>measured pattern ↗</b></a><a href={`${repo}research/2026-08-26-b18-eevee-sampling-dose-response-protocol.md`}><span>PROTOCOL</span><b>frozen decisions ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B18 Eevee Sampling Dose Response</b></div><p>Simple threshold falsified · replication depth next</p><Link href="/research-agenda">继续研究 →</Link></footer>
  </main>;
}
