import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-one-sided-curvature-holdout-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-12-h1/quality-threshold-counterexample.png';

export const metadata: Metadata = {
  title: 'D12.12-H1 Holdout Rejected｜Blender Film Studio',
  description: '24 次新 Blender 5.2 renders 与 110-process evidence chain：audit 通过，但 factor-1 holdout 因质量门、竖向 witness、neither control 与 raw EXR identity 被拒绝。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.12-H1 · Evidence Valid, Candidate Rejected',
    description: '110 processes · audit 21/21 + 93/93 · accepted RGB maximum and fixture stress contracts falsified.',
    url: canonical,
    images: [{ url: socialImage, width: 555, height: 351, alt: 'Quality-threshold counterexample from the D12.12-H1 Blender holdout' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'D12.12-H1 · Holdout Rejected',
    description: 'The evidence chain passed. The factor-1 candidate did not.',
    images: [socialImage],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

const directionalRows = [
  { fixture: 'LEFT', witnesses: '89', accepted: '89', rate: '100%', coverage: '1.000', state: 'pass' },
  { fixture: 'RIGHT', witnesses: '91', accepted: '91', rate: '100%', coverage: '1.000', state: 'pass' },
  { fixture: 'TOP', witnesses: '0', accepted: '0', rate: '—', coverage: '1.000', state: 'fail' },
  { fixture: 'BOTTOM', witnesses: '0', accepted: '0', rate: '—', coverage: '1.000', state: 'fail' },
  { fixture: 'NEITHER', witnesses: '0', accepted: '0', rate: '—', coverage: '0.016', state: 'fail' },
  { fixture: 'STATIC', witnesses: '14,591', accepted: '14,591', rate: '100%', coverage: '1.000', state: 'control' },
] as const;

const hardChecks = [
  { label: 'SOURCE REPEAT', result: 'FAIL', detail: 'pixel arrays exact · raw EXR metadata differs' },
  { label: 'RGB MAXIMUM', result: 'FAIL', detail: '6.6936e−5 > 3.0518e−5' },
  { label: 'NEITHER CONTROL', result: 'FAIL', detail: '0 required witnesses generated' },
  { label: 'OTHER HARD GATES', result: '20 / 20', detail: 'identity · replay · risk · fallback · static' },
] as const;

export default function OneSidedCurvatureHoldoutPage() {
  return <main className="contact-page d1212-page d1212h1-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.12-H1 holdout 导航">
        <Link href="/blender-material-owner-one-sided-curvature-v0-1">D12.12-D1</Link>
        <a href="#verdict">判决</a><a href="#quality">质量反例</a><a href="#directions">方向矩阵</a><a href="#determinism">确定性</a><a href="#evidence">证据</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Holdout D12.12-H1</span>
    </header>

    <section className="contact-hero d1212-hero d1212h1-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.12-H1 · FRESH BLENDER 5.2 HOLDOUT · 24 RENDERS</p>
        <h1>证据链通过。<br/><span>候选没有通过。</span></h1>
        <p>Factor 1 在上一轮真实数组上看起来足够好，所以我们冻结新场景、方向门、质量门与失败叙事，再让 Blender 5.2 重新渲染。110 个进程和独立审计全部有效；新数据同时否定了质量保证与两组 fixture stress contract。</p>
      </div>
      <aside className="contact-gate d1212-gate d1212h1-gate">
        <b>CONFIRMATORY VERDICT</b>
        <strong>HOLDOUT<br/>REJECTED</strong>
        <code>evidence receipt · VALID</code>
        <code>audit · 21/21 + 93/93</code>
        <small>candidate promotion forbidden</small>
      </aside>
      <div className="contact-stats">
        <article><strong>24</strong><span>new Cycles CPU renders</span><small>6 fixtures × 2 frames × 2 repeats</small></article>
        <article><strong>110</strong><span>unique child processes</span><small>all exit zero</small></article>
        <article><strong>20 / 23</strong><span>hard checks passed</span><small>three preregistered failures</small></article>
        <article><strong>93 / 93</strong><span>semantic attacks rejected</span><small>independent auditor</small></article>
      </div>
    </section>

    <section className="section d1212-verdict d1212h1-verdict" id="verdict">
      <div className="section-index">00 / FAILURE WITHOUT FAILURE THEATER</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> AUDIT ACCEPTED ≠ HYPOTHESIS ACCEPTED</p><h2>实验是有效的。<br/><span>失败也是有效结果。</span></h2></div>
        <p>Audit 检查的是证据有没有被替换、进程是否真实、两种语言是否一致、结果是否忠实映射 raw arrays。它没有替 candidate 改分。三道 hard gates 失败后，唯一允许的 confirmatory verdict 就是 rejected。</p>
      </div>
      <div className="d1212h1-hard-grid">
        {hardChecks.map((check) => <article key={check.label} className={check.result === 'FAIL' ? 'failed' : 'passed'}>
          <span>{check.label}</span><strong>{check.result}</strong><p>{check.detail}</p>
        </article>)}
      </div>
    </section>

    <section className="section d1212-rule d1212h1-quality" id="quality">
      <div className="section-index">01 / QUALITY-POLICY COUNTEREXAMPLE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> RISK BOUND HELD · ACCEPTANCE POLICY DID NOT</p><h2>上界没有低估。<br/><span>阈值却比质量门宽四倍。</span></h2></div>
        <p>最坏 accepted pixel 的实际误差为 6.6936e−5；risk 给出更保守的 1.1687e−4，所以 underbound 仍为 0。但 acceptance threshold 是 1.2207e−4，而质量门只有 3.0518e−5。规则允许一个自己也无法称为合格的像素进入。</p>
      </div>
      <div className="d1212h1-equation">
        <article><span>QUALITY GATE</span><strong>32,768</strong><code>Q30 · 3.0518e−5</code></article>
        <i>× 4</i>
        <article className="threshold"><span>ACCEPT THRESHOLD</span><strong>131,072</strong><code>Q30 · 1.2207e−4</code></article>
        <i>→</i>
        <article className="counter"><span>WORST ACCEPTED</span><strong>6.6936e−5</strong><code>39 exceeding samples / repeat</code></article>
      </div>
      <figure className="d1212h1-map">
        <Image src={`${basePath}/evidence/b52-d12-12-h1/quality-threshold-counterexample.png`} width={555} height={351} alt="Neither fixture map with risk rejects, right-missing boundaries, accepts, and quality violations" unoptimized />
        <figcaption><span>NEITHER FIXTURE · R1</span><strong>红色是 accepted quality violations</strong><p>洋红为 778 个 risk rejects；黄色为实际生成的 right-missing 边界；绿色为 13 个 accepts；红色标出其中至少一个 RGB channel 越过质量门的像素。</p></figcaption>
      </figure>
    </section>

    <section className="section d1212-factors d1212h1-directions" id="directions">
      <div className="section-index">02 / DIRECTIONAL FIXTURE FALSIFICATION</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> COVERAGE CANNOT SUBSTITUTE FOR STRESS</p><h2>左右形成了边界。<br/><span>上下只形成 full stencil。</span></h2></div>
        <p>TOP 与 BOTTOM 的 coverage 都是 1.0，但它们的 radius-2 cells 全部也属于 full-stencil；候选 one-sided branch 从未被测试。NEITHER fixture 则生成 297 个 right-missing cells，却没有生成一个 neither-horizontal cell。</p>
      </div>
      <div className="d1212h1-direction-table" role="table" aria-label="D12.12-H1 directional fixture results">
        <div className="head" role="row"><b>FIXTURE</b><b>WITNESSES</b><b>ACCEPTED</b><b>DIRECTION RATE</b><b>COVERAGE</b></div>
        {directionalRows.map((row) => <div className={`row ${row.state}`} role="row" key={row.fixture}><strong>{row.fixture}</strong><code>{row.witnesses}</code><code>{row.accepted}</code><code>{row.rate}</code><b>{row.coverage}</b></div>)}
      </div>
      <figure className="d1212h1-map matrix">
        <Image src={`${basePath}/evidence/b52-d12-12-h1/directional-witness-matrix.png`} width={1098} height={702} alt="Two-by-two matrix for left, right, top, and bottom directional holdout fixtures" unoptimized />
        <figcaption><span>2×2 · LEFT / RIGHT / TOP / BOTTOM</span><strong>只有上排出现绿色 directional witness 线</strong><p>青色是 full-stencil radius-2 domain；绿色是被接受的预期方向 witness。下排 TOP/BOTTOM 没有绿色，不是“太少”，而是严格为 0。</p></figcaption>
      </figure>
    </section>

    <section className="section d1212-evidence d1212h1-determinism" id="determinism">
      <div className="section-index">03 / TWO LAYERS OF DETERMINISM</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PIXELS EXACT · CONTAINER NOT EXACT</p><h2>数据可以复现。<br/><span>文件仍然可以不同。</span></h2></div>
        <p>Repeat 1/2 的 Combined、Depth、Vector、Object Index 与 Material Index canonical arrays 全部 byte exact。Raw multipart EXR SHA 不同，因为 Blender 写入了动态 metadata。这次 raw-byte gate 仍按预登记失败；未来需要显式分层。</p>
      </div>
      <div className="d1212h1-layer-grid">
        <article className="pass"><span>PIXEL PAYLOAD</span><strong>EXACT</strong><code>10 / 10 arrays · both repeats</code><p>所有被消费的 float32 pass payloads 相同。</p></article>
        <article className="fail"><span>EXR CONTAINER</span><strong>DIFF</strong><code>Date · Scene · RenderTime</code><p>文件尺寸相同；动态 header metadata 改变 raw SHA。</p></article>
        <article><span>NEXT CONTRACT</span><strong>2 LAYERS</strong><code>payload + normalized container</code><p>不能在本次结果之后事后改 gate；只允许下一轮重新预登记。</p></article>
      </div>
    </section>

    <section className="section d1212-boundary d1212h1-evidence" id="evidence">
      <div className="section-index">04 / EVIDENCE CHAIN + NEXT RESEARCH</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> NO PROMOTION · FOUR SEPARATE NEXT QUESTIONS</p><h2>先修研究设计。<br/><span>不能直接修成一个“通过”。</span></h2></div>
        <p>质量阈值、竖向 fixture、neither geometry 与 EXR container contract 是四个不同问题。下一轮应分别做 post-hoc derivation 与 calibration，再用新的 unseen confirmatory fixtures；本次 24 renders 不能重复充当 holdout。</p>
      </div>
      <div className="d1212-audit-grid">
        <article><span>ANALYZER</span><strong>3×</strong><p>Python、Node 与独立 replay 对 19 个 arrays 完全一致。</p></article>
        <article><span>AUDIT BASELINE</span><strong>21 / 21</strong><p>证据、自哈希、process roster、raw counts 与 verdict mapping。</p></article>
        <article><span>ATTACKS</span><strong>93 / 93</strong><p>真实 parent/tool/EXR/adapter/decision/envelope/receipt mutations。</p></article>
        <article className="next"><span>PROMOTION</span><strong>STOP</strong><p>不得进入 nonplanar、lit 或 production compiler holdout。</p></article>
      </div>
      <div className="d1212-nonclaim"><b>NOT CLAIMED</b><p>factor 1 对任意信号的质量保证、竖向或 neither-side 泛化、raw EXR strict determinism、production readiness、电影质量或主观感知等价性。</p></div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-owner-one-sided-curvature-holdout.v0.1.json`}><span>PREREGISTRATION</span><b>fixtures + failure map ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-holdout-v0-1/results.json`}><span>FORMAL RESULT</span><b>20 / 23 · rejected ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-holdout-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>21 / 21 · 93 / 93 ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-holdout-v0-1/execution.json`}><span>EXECUTION</span><b>110 unique processes ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-one-sided-curvature-holdout-v0-1/receipt.json`}><span>RECEIPT</span><b>valid evidence chain ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-12-h1-one-sided-curvature-holdout-result.md`}><span>RESEARCH NOTE</span><b>counterexamples + next ↗</b></a>
      </div>
      <div className="i1-proxy-note"><b>VISUAL CLASSIFICATION</b><code>SOURCE_BOUND_VISUALIZATION_NOT_DECISIONAL_EVIDENCE</code><span>manifest · f24511e8f2bd…36fc</span></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.12-H1 Confirmatory Holdout</b></div><p>evidence valid · candidate rejected · promotion stopped</p><Link href="/blender-material-owner-one-sided-curvature-v0-1">返回 D12.12 derivation →</Link></footer>
  </main>;
}
