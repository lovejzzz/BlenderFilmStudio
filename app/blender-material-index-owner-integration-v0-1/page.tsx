import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-material-index-owner-integration-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-11-i1/accepted-intervention-delta.png';

export const metadata: Metadata = {
  title: 'D12.11 Material Index Owner Integration｜Blender Film Studio',
  description: '16 次真实 Blender 5.2 Cycles 配对干预：Material Index 将已登记的错误 owner aliases 从 15 降到 0，且未产生新 false accepts；覆盖率仍未通过。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.11 · Material Index Owner Integration',
    description: '15→0 registered aliases · 16 real renders · 56/56 concrete semantic attacks · coverage remains unsupported.',
    url: canonical,
    images: [{ url: socialImage, width: 716, height: 452, alt: 'Material Index owner intervention accepted-pixel delta' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'D12.11 · Material Index Owner Integration',
    description: '15→0 aliases · no new false accepts · bounded by coverage',
    images: [socialImage],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

const evidencePanels = [
  {
    src: 'object-index-shared.png',
    width: 716,
    height: 452,
    label: 'NEGATIVE CONTROL · OBJECT INDEX 14555 / 14555',
    title: '共享编号，看不见 owner',
    copy: 'critical fixture 的前景与背景故意保持相同 Object Index。这个通道逐字节稳定，却无法表达 analytic ownership。',
  },
  {
    src: 'material-index-separated.png',
    width: 716,
    height: 452,
    label: 'INTERVENTION · MATERIAL INDEX 21301 / 21302',
    title: '只改变身份通道',
    copy: 'compiler 为两个 owners 分配不同的整数 token。Combined、Depth、Vector 与 Object Index 均保持与 H1 byte exact。',
  },
  {
    src: 'accepted-intervention-delta.png',
    width: 716,
    height: 452,
    label: 'PAIRED RESULT · H1 ACCEPTED → MATERIAL ACCEPTED',
    title: '15 个已登记 alias 全部消失',
    copy: '绿色是干预后仍接受的样本，黄色是被安全移除的样本。分类图仅解释绑定数组，不参与 verdict。',
  },
  {
    src: 'remaining-coverage-boundary.png',
    width: 628,
    height: 412,
    label: 'OPEN BOUNDARY · SUPPORT + RISK REJECTION',
    title: '身份修好了，覆盖率没有',
    copy: 'rotated sweep 仍有 146 个 support rejects 与 416 个 risk rejects；下一干预必须单独处理 stencil coverage。',
  },
] as const;

const fixtureRows = [
  { fixture: 'TRANSLATING_OCCLUDER', h1: '13,420', material: '13,420', delta: '0', newAccept: '0' },
  { fixture: 'PARALLAX_MULTI_OWNER', h1: '12,108', material: '12,108', delta: '0', newAccept: '0' },
  { fixture: 'SAME_INDEX_DEPTH_CROSSING', h1: '13,717', material: '13,003', delta: '−714', newAccept: '0' },
  { fixture: 'ROTATED_SWEEP_HIGH_FREQUENCY', h1: '9,765', material: '9,765', delta: '0', newAccept: '0' },
] as const;

export default function MaterialIndexOwnerIntegrationPage() {
  return <main className="contact-page i1-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.11 Material Index owner integration 导航">
        <Link href="/blender-owner-token-pass-v0-1">D12.10</Link>
        <Link href="/blender-material-owner-one-sided-curvature-v0-1">D12.12 Result</Link>
        <a href="#verdict">结论</a>
        <a href="#evidence">像素证据</a>
        <a href="#matrix">配对矩阵</a>
        <a href="#audit">攻击审计</a>
        <a href="#boundary">未解边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Owner Integration D12.11</span>
    </header>

    <section className="contact-hero i1-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.11-I1-A1 · REAL BLENDER 5.2 PAIRED INTERVENTION</p>
        <h1>错误身份接受，<br/><span>从 15 降到 0。</span></h1>
        <p>我们没有换场景、相机、光照、运动、深度、Vector、颜色或风险算法，只把 ownership 从共享 Object Index 换成 compiler-assigned Material Index。16 次真实 Cycles render 复现了同一个因果方向。</p>
      </div>
      <aside className="contact-gate i1-gate">
        <b>BOUNDED VERDICT</b>
        <strong>OWNER<br/>FIX<br/>ACCEPTED</strong>
        <code>registered aliases · 15 → 0</code>
        <code>new false accepts · 0</code>
        <small>coverage not supported</small>
      </aside>
      <div className="contact-stats">
        <article><strong>16</strong><span>real Cycles renders</span><small>4 fixtures × 2 frames × 2 repeats</small></article>
        <article><strong>74 / 74</strong><span>unique child processes</span><small>all exit zero</small></article>
        <article><strong>15 → 0</strong><span>registered aliases</span><small>both clean repeats</small></article>
        <article><strong>56 / 56</strong><span>concrete attacks rejected</span><small>independent semantic audit</small></article>
      </div>
    </section>

    <section className="section i1-verdict" id="verdict">
      <div className="section-index">00 / ONE-VARIABLE CAUSAL CHAIN</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> SAME PIXELS · NEW OWNER IDENTITY</p><h2>Object Index 是负对照。<br/><span>Material Index 是干预变量。</span></h2></div>
        <p>critical fixture 中两个 analytic owners 继续共享 Object Index 14555；新编译器只给它们分配 Material Index 21301 与 21302。成对数组证明其余四个数据通道没有漂移。</p>
      </div>
      <div className="i1-chain">
        <article className="negative"><span>NEGATIVE CONTROL</span><strong>14555 / 14555</strong><code>OBJECT INDEX · SHARED</code><p>17 个 bilinear aliases 中，H1 接受 15 个。</p></article>
        <i>→</i>
        <article className="intervention"><span>SINGLE INTERVENTION</span><strong>21301 / 21302</strong><code>MATERIAL INDEX · DISTINCT</code><p>compiler-assigned、shot-local、整数 exact identity。</p></article>
        <i>→</i>
        <article className="result"><span>REGISTERED ENDPOINT</span><strong>15 → 0</strong><code>NEW ACCEPTED · 0</code><p>错误身份样本被拒绝，没有用新 false accept 换结果。</p></article>
      </div>
      <div className="i1-byte-strip">
        <span>COMBINED</span><b>BYTE EXACT</b><span>DEPTH</span><b>BYTE EXACT</b><span>VECTOR</span><b>BYTE EXACT</b><span>OBJECT INDEX</span><b>BYTE EXACT</b>
      </div>
    </section>

    <section className="section i1-evidence" id="evidence">
      <div className="section-index">01 / SOURCE-BOUND VISUALIZATION</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> NEAREST-NEIGHBOR · NO NEW MEASUREMENT</p><h2>先看身份为什么错。<br/><span>再看干预移除了什么。</span></h2></div>
        <p>四张图由正式 float32/u8 arrays 只读导出。颜色是分类映射，不是 Blender display transform；最近邻放大保留源样本，但不增加任何证据。</p>
      </div>
      <div className="i1-gallery">
        {evidencePanels.map((panel) => <figure key={panel.src}>
          <Image src={`${basePath}/evidence/b52-d12-11-i1/${panel.src}`} width={panel.width} height={panel.height} alt={panel.title} unoptimized />
          <figcaption><span>{panel.label}</span><strong>{panel.title}</strong><p>{panel.copy}</p></figcaption>
        </figure>)}
      </div>
      <div className="i1-proxy-note"><b>CLASSIFICATION</b><code>SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE</code><span>manifest · 9333159908c8…fae9</span></div>
    </section>

    <section className="section i1-matrix" id="matrix">
      <div className="section-index">02 / PAIRED H1 MATRIX</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> FOUR FIXTURES · TWO CLEAN REPEATS</p><h2>只有 critical cell 改变。<br/><span>其他 fixture 接受数不动。</span></h2></div>
        <p>下表每个数字在 R1/R2 相同。critical cell 的 714 个移除样本中包含预登记的 15 个错误 owner aliases；全八个 fixture/repeat cells 均没有 H1 之外的新 accepted coordinate。</p>
      </div>
      <div className="i1-table" role="table" aria-label="Material Index 配对干预矩阵">
        <div className="head" role="row"><b>FIXTURE</b><b>H1 ACCEPTED</b><b>MATERIAL</b><b>Δ</b><b>NEW ACCEPT</b></div>
        {fixtureRows.map((row) => <div className="row" role="row" key={row.fixture}><strong>{row.fixture}<small>R1 = R2</small></strong><code>{row.h1}</code><code>{row.material}</code><b className={row.delta === '0' ? '' : 'changed'}>{row.delta}</b><code>{row.newAccept}</code></div>)}
      </div>
      <div className="i1-critical-grid">
        <article><span>CRITICAL ACCEPTED</span><strong>13,717 → 13,003</strong><p>714 个 samples 转为安全拒绝。</p></article>
        <article><span>INVALID_OWNER</span><strong>0 → 4,187</strong><p>ownership gate 现在先于错误的 depth coincidence。</p></article>
        <article><span>INVALID_DEPTH</span><strong>4,169 → 0</strong><p>同一批历史不再伪装成同 owner depth mismatch。</p></article>
        <article><span>FALSE INVALID ACCEPT</span><strong>0</strong><p>全部 analytic invalid-history controls 保持拒绝。</p></article>
      </div>
    </section>

    <section className="section i1-audit" id="audit">
      <div className="section-index">03 / FAILURE RETAINED · ATTACK GAP CLOSED</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> HASH SENSITIVITY ≠ SEMANTIC ATTACK</p><h2>正式结果先被暂停。<br/><span>直到真实 mutation 全部拒绝。</span></h2></div>
        <p>原 analyzer 把 `mutationNonce` 变化记成 56 个 attacks。我们保留 18/19 formal result，但不承认那条攻击声明；随后以独立工具对真实 payload 执行 56 个具体 mutation，并验证 formal Git tree 前后不变。</p>
      </div>
      <div className="i1-audit-chain">
        <article className="formal"><span>FORMAL MATRIX</span><strong>18 / 19</strong><code>raw audit · 9 / 9</code><p>像素结论成立；coverage 失败。</p></article>
        <i>→</i>
        <article className="hold"><span>PROMOTION HOLD</span><strong>NONCE ONLY</strong><code>semantic coverage · unproven</code><p>主动发现并记录审计设计缺陷。</p></article>
        <i>→</i>
        <article className="accepted"><span>INDEPENDENT A1</span><strong>56 / 56</strong><code>baseline · 19 / 19</code><p>channel、token、alias、fallback、Q30 与 Vector attacks 全拒绝。</p></article>
      </div>
      <div className="i1-attack-roster">
        <span>8 parent bytes</span><span>4 source reports</span><span>8 adapter bytes</span><span>2 channel swaps</span><span>4 token contract</span><span>4 Object controls</span><span>2 alias injects</span><span>8 new accepts</span><span>4 fallback bytes</span><span>4 coverage edits</span><span>4 chain artifacts</span><span>2 Q30 + 2 Vector</span>
      </div>
    </section>

    <section className="section i1-boundary" id="boundary">
      <div className="section-index">04 / CLAIM BOUNDARY + NEXT EXPERIMENT</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> IDENTITY FIXED · COVERAGE STILL BOUNDED</p><h2>这不是“重建已解决”。<br/><span>下一变量是单侧 stencil。</span></h2></div>
        <p>Material Index 只证明这组 paired matrix 内的 owner identity input 可用。rotated sweep 的 cell ratio 仍为 0.94558、foreground retention 为 0.94151，未过冻结的 0.97 / 0.95 门；不能通过改 denominator 或放宽 Q30 宣称成功。</p>
      </div>
      <div className="i1-boundary-grid">
        <article><span>SWEEP CELL RATIO</span><strong>0.94558</strong><code>gate · ≥ 0.97000</code><p>身份干预没有改变 coverage failure。</p></article>
        <article><span>FOREGROUND RETENTION</span><strong>0.94151</strong><code>gate · ≥ 0.95000</code><p>全局 coverage 仍不支持 promotion。</p></article>
        <article className="next"><span>NEXT · SWEEP</span><strong>146</strong><code>one-sided support opportunities</code><p>下一轮可证伪干预的第一组边界。</p></article>
        <article className="next"><span>NEXT · PARALLAX</span><strong>152</strong><code>one-sided support opportunities</code><p>必须独立于 owner identity 做控制实验。</p></article>
      </div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-index-owner-integration.v0.1.json`}><span>PREREGISTRATION</span><b>paired intervention ↗</b></a>
        <a href={`${repo}experiments/blender-material-index-owner-integration-v0-1/results.json`}><span>FORMAL RESULT</span><b>18 / 19 · 15→0 ↗</b></a>
        <a href={`${repo}experiments/blender-material-index-owner-integration-v0-1/audit.json`}><span>RAW AUDIT</span><b>9 / 9 checks ↗</b></a>
        <a href={`${repo}specs/blender-material-index-owner-integration-adversarial-audit.v0.1.json`}><span>ATTACK SPEC</span><b>56 concrete mutations ↗</b></a>
        <a href={`${repo}experiments/blender-material-index-owner-integration-adversarial-audit-v0-1/results.json`}><span>ADVERSARIAL RESULT</span><b>19 / 19 · 56 / 56 ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-11-i1-formal-result-and-attack-gap.md`}><span>RETAINED GAP</span><b>nonce-only audit ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-11-i1-adversarial-audit-result.md`}><span>RESEARCH NOTE</span><b>claims · limits · next ↗</b></a>
        <a href={`${repo}public/evidence/b52-d12-11-i1/manifest.json`}><span>VISUAL MANIFEST</span><b>source-bound hashes ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.11 Material Index Owner Integration</b></div><p>owner identity accepted · coverage not supported</p><Link href="/blender-material-owner-one-sided-curvature-v0-1">继续：D12.12 单侧曲率候选 →</Link></footer>
  </main>;
}
