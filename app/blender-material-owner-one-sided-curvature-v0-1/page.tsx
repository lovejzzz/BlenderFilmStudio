import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-one-sided-curvature-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-12-d1/sweep-one-sided-recovery.png';

export const metadata: Metadata = {
  title: 'D12.12 One-sided Curvature Candidate｜Blender Film Studio',
  description: 'D12.11 真实 Blender 5.2 数组上的 post-hoc 推导：factor 1 恢复 sweep 136/146 与 parallax 144/152，但 sweep 总覆盖率仍未通过 97% 门。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.12 · One-sided Curvature Candidate',
    description: '136/146 sweep opportunities recovered · 64/64 semantic attacks rejected · fresh Blender holdout still required.',
    url: canonical,
    images: [{ url: socialImage, width: 628, height: 412, alt: 'Sweep one-sided curvature recovery classification' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'D12.12 · One-sided Curvature Candidate',
    description: 'Most one-sided opportunities recovered; the 97% sweep gate still fails.',
    images: [socialImage],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

const factorRows = [
  { factor: '1', sweep: '93.15%', parallax: '94.74%', recovered: '136 / 144', result: 'PASS', state: 'selected' },
  { factor: '2', sweep: '78.08%', parallax: '86.18%', recovered: '114 / 131', result: 'PASS', state: 'pass' },
  { factor: '4', sweep: '65.07%', parallax: '68.42%', recovered: '95 / 104', result: 'PASS', state: 'pass' },
  { factor: '8', sweep: '56.16%', parallax: '42.11%', recovered: '82 / 64', result: 'FAIL', state: 'fail' },
  { factor: '16', sweep: '50.68%', parallax: '15.13%', recovered: '74 / 23', result: 'FAIL', state: 'fail' },
  { factor: '32', sweep: '47.95%', parallax: '5.92%', recovered: '70 / 9', result: 'FAIL', state: 'fail' },
  { factor: '64', sweep: '44.52%', parallax: '4.61%', recovered: '65 / 7', result: 'FAIL', state: 'fail' },
] as const;

const evidencePanels = [
  {
    src: 'sweep-one-sided-recovery.png',
    width: 628,
    height: 412,
    label: 'ROTATED SWEEP · FACTOR 1',
    title: '146 个机会，恢复 136 个',
    copy: '绿色为 D12.11 已接受；黄色为 factor 1 新恢复；洋红为仍受 risk gate 拒绝；红色是 10 个存在单侧机会但仍未接受的反例。',
  },
  {
    src: 'parallax-one-sided-recovery.png',
    width: 668,
    height: 436,
    label: 'CAMERA PARALLAX · FACTOR 1',
    title: '152 个机会，恢复 144 个',
    copy: '同一分类规则下，parallax coverage 从 97.735% 升到 98.672%；8 个 localized opportunities 仍被风险阈值拒绝。',
  },
] as const;

export default function OneSidedCurvaturePage() {
  return <main className="contact-page d1212-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.12 one-sided curvature 导航">
        <Link href="/blender-material-index-owner-integration-v0-1">D12.11</Link>
        <Link href="/blender-material-owner-one-sided-curvature-holdout-v0-1">H1 Result</Link>
        <a href="#verdict">结论</a>
        <a href="#rule">规则</a>
        <a href="#evidence">像素图</a>
        <a href="#factors">因子族</a>
        <a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Curvature D12.12-D1</span>
    </header>

    <section className="contact-hero d1212-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.12-D1 · POST-HOC DERIVATION · REAL-RENDER PARENT</p>
        <h1>恢复了 136 个，<br/><span>仍然不能宣布通过。</span></h1>
        <p>上一轮的 symmetric 4×4 curvature stencil 在物体边缘过于保守。我们冻结七个 inflation factors，用独立 Python / Node consumers 只读重算 D12.11 的真实 Blender 5.2 数组；factor 1 恢复了大多数单侧机会，但 sweep 总覆盖仍低于 97%。</p>
      </div>
      <aside className="contact-gate d1212-gate">
        <b>BOUNDED VERDICT</b>
        <strong>DERIVED<br/>NOT<br/>HELD OUT</strong>
        <code>factor · 1 selected</code>
        <code>sweep · 0.95875 &lt; 0.97000</code>
        <small>fresh Blender H1 required</small>
      </aside>
      <div className="contact-stats">
        <article><strong>136 / 146</strong><span>sweep recovered</span><small>93.15% localized acceptance</small></article>
        <article><strong>144 / 152</strong><span>parallax recovered</span><small>94.74% localized acceptance</small></article>
        <article><strong>0</strong><span>measured risk underbounds</span><small>selected-factor RGB samples</small></article>
        <article><strong>64 / 64</strong><span>semantic attacks rejected</span><small>independent auditor</small></article>
      </div>
    </section>

    <section className="section d1212-verdict" id="verdict">
      <div className="section-index">00 / RESULT WITHOUT SUCCESS THEATER</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> LOCAL BOTTLENECK REMOVED · GLOBAL GATE RETAINED</p><h2>owner retention 过线。<br/><span>cell coverage 仍失败。</span></h2></div>
        <p>这次结果同时包含一个成功与一个反例。sweep foreground-owner retention 达到 0.95026，越过 0.95；但所有 radius-2 cells 的 accepted ratio 只有 0.95875，仍低于预先冻结的 0.97。剩余问题已经从 support availability 转移到 risk rejection。</p>
      </div>
      <div className="d1212-verdict-grid">
        <article className="before"><span>D12.11 SWEEP</span><strong>0.94558</strong><code>cell coverage</code><p>146 support rejects + 416 risk rejects。</p></article>
        <i>→</i>
        <article className="candidate"><span>FACTOR 1</span><strong>+136</strong><code>one-sided accepted</code><p>完整 symmetric-stencil 路径逐字节不变。</p></article>
        <i>→</i>
        <article className="bounded"><span>D12.12-D1 SWEEP</span><strong>0.95875</strong><code>gate · ≥ 0.97000</code><p>局部机制成立，但全局 promotion 继续暂停。</p></article>
      </div>
    </section>

    <section className="section d1212-rule" id="rule">
      <div className="section-index">01 / FROZEN RULE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> SAME OWNER · SAME ALPHA · ONE OUTER TAP</p><h2>有双侧，就保持旧算法。<br/><span>只剩一侧，才启用候选。</span></h2></div>
        <p>每个 bilinear row / column 单独检查外侧 second difference。双侧都存在时使用 D12.11 maximum；仅一侧存在时乘 frozen factor；两侧都不存在必须拒绝。Material Index、Q30/Q24、inclusive threshold 与 exact RGBA fallback 全部保持不变。</p>
      </div>
      <div className="d1212-rule-grid">
        <article><span>FULL STENCIL</span><strong>max(L, R)</strong><code>BYTE EXACT TO D12.11</code><p>不是重写原算法；完整 support 的像素没有任何数值漂移。</p></article>
        <article className="active"><span>ONE SIDE</span><strong>1 × Δ²</strong><code>SELECTED CANDIDATE</code><p>只在 owner 与 alpha 有效的单侧 second difference 上启用。</p></article>
        <article><span>NO SIDE</span><strong>REJECT</strong><code>NO IMPUTATION</code><p>不猜测缺失曲率，不通过放宽 owner 或阈值增加 coverage。</p></article>
      </div>
      <div className="d1212-contract-strip"><span>Material Index exact</span><span>Q30 / Q24 frozen</span><span>threshold 131072 inclusive</span><span>fallback byte exact</span><span>static Δ accepted = 0</span></div>
    </section>

    <section className="section d1212-evidence" id="evidence">
      <div className="section-index">02 / SOURCE-BOUND PIXEL MAPS</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> NEAREST-NEIGHBOR · TWO PRIMARY FIXTURES</p><h2>黄色是恢复。<br/><span>洋红是还欠下的风险问题。</span></h2></div>
        <p>图像由已提交的 baseline accepted、radius-2、localized opportunity、factor-1 accepted 与 Q30 risk arrays 只读导出。颜色不属于 Blender display transform，也不参与实验 verdict。</p>
      </div>
      <div className="d1212-gallery">
        {evidencePanels.map((panel) => <figure key={panel.src}>
          <Image src={`${basePath}/evidence/b52-d12-12-d1/${panel.src}`} width={panel.width} height={panel.height} alt={panel.title} unoptimized />
          <figcaption><span>{panel.label}</span><strong>{panel.title}</strong><p>{panel.copy}</p></figcaption>
        </figure>)}
      </div>
      <div className="d1212-legend" aria-label="代理图分类颜色">
        <span className="baseline">D12.11 accepted</span><span className="recovered">new accepted</span><span className="risk">remaining risk</span><span className="counter">opportunity rejected</span>
      </div>
      <div className="i1-proxy-note"><b>CLASSIFICATION</b><code>SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE</code><span>manifest · 37a8f49aa598…356c</span></div>
    </section>

    <section className="section d1212-factors" id="factors">
      <div className="section-index">03 / MECHANICAL SELECTION OVER SEVEN FACTORS</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> SMALLEST ALL-GATE PASS</p><h2>不是挑最好看的数字。<br/><span>选择规则先于结果冻结。</span></h2></div>
        <p>因子越大，估计风险越保守，accepted set 必须单调缩小。1、2、4 通过全部 derivation gates；8 首先在 parallax 的 ≥50% opportunity-acceptance gate 失败。机械规则选择最小通过者，因此结果是 factor 1。</p>
      </div>
      <div className="d1212-factor-table" role="table" aria-label="One-sided curvature inflation factor sweep">
        <div className="head" role="row"><b>FACTOR</b><b>SWEEP OPPORTUNITY</b><b>PARALLAX OPPORTUNITY</b><b>RECOVERED S / P</b><b>RESULT</b></div>
        {factorRows.map((row) => <div className={`row ${row.state}`} role="row" key={row.factor}><strong>{row.factor}</strong><code>{row.sweep}</code><code>{row.parallax}</code><code>{row.recovered}</code><b>{row.result}</b></div>)}
      </div>
      <div className="d1212-quality-grid">
        <article><span>GLOBAL RGB MAX</span><strong>3.0309e−5</strong><code>gate · ≤ 3.0518e−5</code></article>
        <article><span>GLOBAL RGB RMSE</span><strong>1.0527e−5</strong><code>gate · ≤ 3.0518e−5</code></article>
        <article><span>FALSE INVALID</span><strong>0</strong><code>all selected cells</code></article>
        <article><span>MATERIAL ALIASES</span><strong>0</strong><code>registered class</code></article>
      </div>
    </section>

    <section className="section d1212-boundary" id="boundary">
      <div className="section-index">04 / AUDIT + CLAIM BOUNDARY + H1</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> POST-HOC FACT ≠ GENERAL BOUND</p><h2>这里证明的是候选。<br/><span>下一轮才测试泛化。</span></h2></div>
        <p>factor 1 的零 underbound 是这组已有数组上的经验事实，不是对任意 rendered function 的数学上界。D1 没有启动 Blender、没有新 render、没有模型或网络；它继承的父证据是 16 次真实 Blender 5.2 Cycles renders。</p>
      </div>
      <div className="d1212-audit-grid">
        <article><span>ANALYZER</span><strong>13 / 13</strong><p>cross-language、repeat、full-stencil、quality、fallback 与 coverage gates。</p></article>
        <article><span>INDEPENDENT BASELINE</span><strong>21 / 21</strong><p>auditor 不 import consumers 或 runner，独立重算语义。</p></article>
        <article><span>CONCRETE ATTACKS</span><strong>64 / 64</strong><p>parent、adapter、mask、risk、fallback、result chain 与 repeat mutations 全拒绝。</p></article>
        <article className="next"><span>NEXT · D12.12-H1</span><strong>FRESH</strong><p>预登记 unseen Blender 5.2 fixtures：left/right、top/bottom 与 neither-side negative control。</p></article>
      </div>
      <div className="d1212-nonclaim"><b>NOT CLAIMED</b><p>production readiness、任意场景误差界、感知重要性、变形几何、透明、运动模糊、景深、降噪安全或电影质量。D12.12-H1 之前不得将 candidate 写入生产 compiler。</p></div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-owner-one-sided-curvature-derivation.v0.1.json`}><span>PREREGISTRATION</span><b>frozen factors + gates ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-derivation-v0-1/results.json`}><span>FORMAL RESULT</span><b>13 / 13 · factor 1 ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-derivation-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>21 / 21 · 64 / 64 ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-derivation-v0-1/receipt.json`}><span>EXECUTION RECEIPT</span><b>process + hash chain ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-12-d1-one-sided-curvature-derivation-result.md`}><span>RESEARCH NOTE</span><b>facts · limits · next ↗</b></a>
        <a href={`${repo}public/evidence/b52-d12-12-d1/manifest.json`}><span>VISUAL MANIFEST</span><b>source-bound hashes ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.12 One-sided Curvature Candidate</b></div><p>post-hoc candidate derived · H1 later rejected</p><Link href="/blender-material-owner-one-sided-curvature-holdout-v0-1">查看 D12.12-H1 新鲜留出结果 →</Link></footer>
  </main>;
}
