import type { CSSProperties } from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import result from '../../experiments/blender-material-owner-quality-coupling-derivation-v0-1/results.json';
import audit from '../../experiments/blender-material-owner-quality-coupling-derivation-v0-1/audit.json';
import execution from '../../experiments/blender-material-owner-quality-coupling-derivation-v0-1/execution.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-quality-coupling-derivation-v0-1/';
const socialImage = 'https://lovejzzz.github.io/BlenderFilmStudio/evidence/b52-d12-12-h1/quality-threshold-counterexample.png';

export const metadata: Metadata = {
  title: 'D12.13-D1 Global Threshold Rejected｜Blender Film Studio',
  description: '26-process post-hoc derivation：五档 Q30 threshold 全部满足质量门，但全部破坏 primary coverage 与 Material-owner retention，因此不导出候选。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.13-D1 · Quality Safe, Coverage Rejected',
    description: '19/19 analyzer · 19/19 audit baseline · 88/88 attacks · zero threshold candidates derived.',
    url: canonical,
    images: [{ url: socialImage, width: 555, height: 351, alt: 'The H1 quality-threshold counterexample that motivated D12.13-D1' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'D12.13-D1 · No Global Threshold Candidate',
    description: 'Quality became safe. Coverage collapsed. The evidence chain passed.',
    images: [socialImage],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const primaryFixtures = new Set(['LEFT_OUTER_MISSING_EXPANSION_173X107', 'RIGHT_OUTER_MISSING_EXPANSION_181X109', 'TOP_OUTER_MISSING_EXPANSION_169X113', 'BOTTOM_OUTER_MISSING_EXPANSION_177X115']);
const label = (fixtureId: string) => fixtureId.split('_')[0];
const scientific = (value: number) => value.toExponential(3).replace('e-', 'e−');
const candidates = result.candidates.map(row => ({
  threshold: row.thresholdQ30.toLocaleString('en-US'),
  quality: scientific(row.quality.maximum),
  qualityRatio: `${(row.quality.maximum / 0.000030517578125 * 100).toFixed(1)}%`,
  coverage: row.minimumPrimaryCellCoverage * 100,
  owner: row.minimumPrimaryOwnerRetention * 100,
}));
const widest = result.candidates[0];
const fixtures = widest.cells.filter(row => row.repeat === 1 && primaryFixtures.has(row.fixtureId)).map(row => ({
  id: label(row.fixtureId),
  coverage: `${((row.acceptedToRadius2 ?? 0) * 100).toFixed(1)}%`,
  accepted: `${row.accepted.toLocaleString('en-US')} / ${row.radius2.toLocaleString('en-US')}`,
}));
const lowestOwner = widest.cells.filter(row => primaryFixtures.has(row.fixtureId)).flatMap(row =>
  Object.entries(row.perOwner).filter(([, owner]) => owner.retention !== null).map(([id, owner]) => ({ id, ...owner })),
).sort((left, right) => (left.retention ?? 1) - (right.retention ?? 1))[0];

export default function QualityCouplingDerivationPage() {
  return <main className="contact-page d1212-page d1213-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.13-D1 derivation 导航">
        <Link href="/blender-material-owner-one-sided-curvature-holdout-v0-1">D12.12-H1</Link>
        <a href="#verdict">判决</a><a href="#frontier">阈值前沿</a><a href="#coverage">Fixture</a><a href="#integrity">审计</a><a href="#next">下一步</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Derivation D12.13-D1</span>
    </header>

    <section className="contact-hero d1212-hero d1213-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.13-D1 · POST-HOC DERIVATION · ZERO NEW RENDERS</p>
        <h1>质量安全了。<br/><span>覆盖率崩了。</span></h1>
        <p>把 risk threshold 从 131,072 Q30 收紧到精确 quality gate 或更低，确实消除了 H1 的 accepted RGB 超标；但最宽松的一档已经丢掉超过三分之一 primary cells。五档候选全部被同一组预登记 coverage gates 拒绝。</p>
      </div>
      <aside className="contact-gate d1212-gate d1213-gate">
        <b>DERIVATION VERDICT</b>
        <strong>NO<br/>CANDIDATE</strong>
        <code>evidence receipt · VALID</code>
        <code>quality gates · 5 / 5</code>
        <small>promotion forbidden</small>
      </aside>
      <div className="contact-stats">
        <article><strong>{execution.uniquePids}</strong><span>unique processes</span><small>12 Python · 12 Node · analyzer · audit</small></article>
        <article><strong>{result.hardChecksPassed}/{result.hardChecksTotal}</strong><span>analyzer hard gates</span><small>identity · replay · fallback · process</small></article>
        <article><strong>{audit.attacksPassed}/{audit.attacksTotal}</strong><span>semantic attacks</span><small>9 required mutation families</small></article>
        <article><strong>0</strong><span>threshold candidates</span><small>all fail coverage + owner retention</small></article>
      </div>
    </section>

    <section className="section d1213-verdict" id="verdict">
      <div className="section-index">01 / MECHANISM VERDICT</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> ONE KNOB CANNOT CLOSE TWO CONTRACTS</p><h2>收紧一个数，<br/><span>不能修好这个机制。</span></h2></div>
        <p>Q30 risk 仍正确上界实际误差；失败发生在 tightness。全局 threshold 足够低时 quality 必然安全，却把大量本可用 cell 一并拒绝。我们拒绝的是“只调 threshold”，不是 risk upper bound。</p>
      </div>
      <div className="d1213-equation">
        <article className="safe"><span>QUALITY CONTRACT</span><strong>PASS</strong><code>max 7.510e−6 &lt; 3.052e−5</code><p>最大阈值已经把 observed maximum 压到 gate 的 24.6%。</p></article>
        <i>AND</i>
        <article className="failed"><span>COVERAGE CONTRACT</span><strong>FAIL</strong><code>64.7% &lt; 97.0%</code><p>BOTTOM fixture 成为最坏 cell-level counterexample。</p></article>
        <i>⇒</i>
        <article className="stopped"><span>PROMOTION</span><strong>STOP</strong><code>selectedThresholdQ30 · null</code><p>没有 candidate 可进入 fresh Blender holdout。</p></article>
      </div>
    </section>

    <section className="section d1213-frontier" id="frontier">
      <div className="section-index">02 / FROZEN THRESHOLD FRONTIER</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> FIVE CANDIDATES · DESCENDING MECHANICAL SELECTION</p><h2>每一档更安全。<br/><span>每一档也更不可用。</span></h2></div>
        <p>绿色条表示最低 primary cell coverage，红色刻度是 97% gate；紫色条表示最低 Material-owner retention，目标为 95%。两类 coverage 都没有接近门线。</p>
      </div>
      <div className="d1213-frontier-table">
        <div className="head"><b>THRESHOLD Q30</b><b>RGB MAX</b><b>QUALITY / GATE</b><b>MIN CELL COVERAGE · TARGET 97%</b><b>MIN OWNER RETENTION · TARGET 95%</b><b>VERDICT</b></div>
        {candidates.map(row => <div className="row" key={row.threshold}>
          <strong>{row.threshold}</strong><code>{row.quality}</code><code>{row.qualityRatio}</code>
          <div className="meter" style={{ '--value': `${row.coverage}%` } as CSSProperties}><i/><span>{row.coverage.toFixed(1)}%</span></div>
          <div className="meter owner" style={{ '--value': `${row.owner}%` } as CSSProperties}><i/><span>{row.owner.toFixed(1)}%</span></div>
          <b>REJECT</b>
        </div>)}
      </div>
      <p className="d1213-table-note">All quality maximum / RMSE, risk-underbound, invalid-history, Material-alias and static gates passed. Every candidate failed both primary coverage gates.</p>
    </section>

    <section className="section d1213-coverage" id="coverage">
      <div className="section-index">03 / WIDEST SAFE THRESHOLD · 32768 Q30</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> FOUR PRIMARY FIXTURES · REPEAT 1</p><h2>不是一个坏场景。<br/><span>四个都远离 97%。</span></h2></div>
        <p>LEFT/RIGHT 相对较高，但仍至少丢失 15.8%；TOP/BOTTOM 更差。最低 owner 是 {lowestOwner.id}：{lowestOwner.accepted.toLocaleString('en-US')}/{lowestOwner.radius2.toLocaleString('en-US')}，仅保留 {((lowestOwner.retention ?? 0) * 100).toFixed(1)}%。</p>
      </div>
      <div className="d1213-fixture-grid">
        {fixtures.map(row => <article key={row.id}><span>{row.id}</span><strong>{row.coverage}</strong><code>{row.accepted}</code><div><i style={{ width: row.coverage }}/><b>97% gate</b></div></article>)}
      </div>
      <div className="d1213-controls">
        <article><span>NEITHER NEGATIVE CONTROL</span><strong>0 / 791</strong><p>五档全部 accepted=0；不计入 primary coverage promotion。</p></article>
        <article><span>STATIC CONTROL</span><strong>14,591 / 14,591</strong><p>五档全部 byte-stable；静态域没有被错误牺牲。</p></article>
      </div>
    </section>

    <section className="section d1213-integrity" id="integrity">
      <div className="section-index">04 / EVIDENCE INTEGRITY + FAILED ATTEMPT DISCLOSURE</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> VALID SCIENCE REQUIRES VALID FAILURE HANDLING</p><h2>第一次没有过审。<br/><span>所以没有被算作结果。</span></h2></div>
        <p>Attempt 0 的 19/19 baseline 通过，但 mutation audit 只有 87/88。工具误取 STATIC witness，导致一个攻击没有产生变异。我们保留整次 attempt，只修作用域，再从空 root 重跑。</p>
      </div>
      <div className="d1213-audit-chain">
        <article className="failed"><span>ATTEMPT 0</span><strong>87 / 88</strong><code>no evidence receipt</code><p>科学 metrics 已产生，但 evidence chain 拒绝发布。</p></article>
        <i>→</i>
        <article><span>SCOPED REPAIR</span><strong>1 LINE</strong><code>non-static LEFT/R1 witness</code><p>Threshold、gate、input、metric、verdict 均未改变。</p></article>
        <i>→</i>
        <article className="accepted"><span>FORMAL RERUN</span><strong>88 / 88</strong><code>receipt · 984ed192…3f2</code><p>两次 run 的科学 metrics/cells 完全一致。</p></article>
      </div>
    </section>

    <section className="section d1212-boundary d1213-next" id="next">
      <div className="section-index">05 / NEXT FALSIFIABLE QUESTIONS</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> DO NOT TUNE AGAIN</p><h2>下一步拆成两条线。<br/><span>先修实验域，再研究 tighter bound。</span></h2></div>
        <p>TOP/BOTTOM/NEITHER 缺 witness 是 fixture geometry 问题；risk 对 realized error 过松是机制问题。两者必须独立预登记，不能用一组 post-hoc arrays 同时“修好”。</p>
      </div>
      <div className="d1213-next-grid">
        <article><span>TRACK A · FIXTURE CALIBRATION</span><strong>先证明 stress domain 存在</strong><p>Zero-render analytic oracle 在任何 Cycles render 之前锁定 top/bottom/neither witnesses。</p></article>
        <article><span>TRACK B · RISK TIGHTNESS</span><strong>分解 bound 的保守来源</strong><p>按 full-stencil / one-sided support 与 Material owner 报告 risk-to-error envelope。</p></article>
        <article className="blocked"><span>PROMOTION RULE</span><strong>新的 unseen holdout</strong><p>只有同时通过 quality、97% cell、95% owner gates 才能进入 compiler。</p></article>
      </div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-owner-quality-coupling-derivation.v0.1.json`}><span>PREREGISTRATION</span><b>frozen thresholds + gates ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-quality-coupling-derivation-v0-1/results.json`}><span>FORMAL RESULT</span><b>19 / 19 · no candidate ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-quality-coupling-derivation-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>19 / 19 · 88 / 88 ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-quality-coupling-derivation-v0-1/receipt.json`}><span>EVIDENCE RECEIPT</span><b>valid · candidate false ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-quality-coupling-derivation-v0-1-attempt0-audit-tool-bug/failure-summary.json`}><span>FAILED ATTEMPT</span><b>scope bug disclosure ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-13-d1-quality-coupled-threshold-derivation-result.md`}><span>RESEARCH NOTE</span><b>result + next questions ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.13-D1 Quality Coupling Derivation</b></div><p>evidence valid · global threshold rejected · mechanism research continues</p><Link href="/blender-material-owner-one-sided-curvature-holdout-v0-1">返回 D12.12-H1 →</Link></footer>
  </main>;
}
