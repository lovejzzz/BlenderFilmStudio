import type { Metadata } from 'next';
import Link from 'next/link';
import failure from '../../experiments/blender-material-owner-rigid-directional-render-holdout-v0-1/failure.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-material-owner-rigid-directional-render-holdout-v0-1/';

export const metadata: Metadata = {
  title: 'D12.14-H1 Frozen Tool Failure｜Blender Film Studio',
  description: '12 次真实 Blender 5.2 renders 完成后，冻结 analyzer 因 schema 展开缺口中止。H1 没有科学 verdict；partial evidence 与不可重跑边界完整公开。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.14-H1 · No Scientific Verdict',
    description: '54 children completed · frozen analyzer failed · same-ID rerun forbidden.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'D12.14-H1 · Frozen Tool Failure',
    description: 'A failed instrument is not a failed hypothesis. The partial evidence remains public.',
    images: [],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const processes = failure.completedProcessCounts;
const forensic = failure.postFailureForensics;
const topBottom = forensic.topAndBottom;
const neither = forensic.neither;

const cells = [
  { label: 'TOP', witnesses: topBottom.eligiblePerRepeat, eligible: topBottom.eligiblePerRepeat, accepted: topBottom.acceptedPerRepeat, quality: '2.402e−5', status: 'TARGET PASSED' },
  { label: 'BOTTOM', witnesses: topBottom.eligiblePerRepeat, eligible: topBottom.eligiblePerRepeat, accepted: topBottom.acceptedPerRepeat, quality: '1.910e−5', status: 'TARGET PASSED' },
  { label: 'NEITHER', witnesses: neither.witnessesPerRepeat, eligible: 0, accepted: neither.acceptedPerRepeat, quality: 'n/a', status: '270 < 1,024' },
];

export default function RigidDirectionalHoldoutFailurePage() {
  return <main className="contact-page d1212-page d1214h1-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.14-H1 failure 导航">
        <Link href="/blender-material-owner-rigid-directional-calibration-v0-1">D12.14-C2</Link>
        <a href="#status">状态</a><a href="#failure">故障</a><a href="#evidence">证据</a><a href="#forensics">取证</a><a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Formal H1 · Invalidated</span>
    </header>

    <section className="contact-hero d1214h1-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.14-H1 · FRESH RENDER HOLDOUT · FROZEN TOOL FAILURE</p>
        <h1>实验没有结论。<br/><span>这本身就是结论边界。</span></h1>
        <p>12 次真实 Blender 5.2 渲染已经完成，但冻结 analyzer 在读取 background mesh schema 时中止。我们保留全部 partial evidence，不修工具后重跑，不把 instrument failure 冒充成 hypothesis failure。</p>
      </div>
      <aside className="contact-gate d1214h1-gate">
        <b>SCIENTIFIC VERDICT</b>
        <strong>NULL</strong>
        <code>tool chain · invalidated</code>
        <code>same ID · rerun forbidden</code>
        <small>{failure.experimentId}</small>
      </aside>
      <div className="contact-stats">
        <article><strong>{processes.sourceCyclesRayRenders}</strong><span>fresh Cycles renders</span><small>3 fixtures × 2 frames × 2 repeats</small></article>
        <article><strong>{processes.successfulChildrenBeforeAnalyzer}</strong><span>successful children</span><small>source → adapter → consumers → envelopes</small></article>
        <article><strong>{processes.analyzerProcessesFailed}</strong><span>frozen analyzer failed</span><small>KeyError · background subdivisions</small></article>
        <article><strong>{processes.auditProcesses}</strong><span>audit processes</span><small>not started · no receipt</small></article>
      </div>
    </section>

    <section className="section d1214h1-status" id="status">
      <div className="section-index">00 / STATE MACHINE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> A GREEN PREFLIGHT IS ADMISSION · NOT A RESULT</p><h2>顺序没有被破坏。<br/><span>失败也不能被绕过。</span></h2></div>
        <p>Spec 先提交，八工具后冻结，official preflight 14/14，再创建唯一 formal root。错误发生后，没有第二次 runner，没有补造 result，也没有让 audit 对不存在的结果签字。</p>
      </div>
      <div className="d1214h1-state-chain">
        <article className="done"><span>01 · PREREG</span><strong>FROZEN</strong><code>spec · 7ff239d9…</code><p>raster、tokens、gates、56-process matrix 均先冻结。</p></article>
        <i>→</i>
        <article className="done"><span>02 · PREFLIGHT</span><strong>14 / 14</strong><code>zero renders</code><p>Scene、RNA、pass registration 与 disk gate 全通过。</p></article>
        <i>→</i>
        <article className="warn"><span>03 · FORMAL</span><strong>54 OK</strong><code>12 renders completed</code><p>Analyzer 是第 55 个 child，也是第一个失败点。</p></article>
        <i>→</i>
        <article className="failed"><span>04 · DECISION</span><strong>NO VERDICT</strong><code>audit · not started</code><p>工具链不完整，科学映射不成立。</p></article>
      </div>
    </section>

    <section className="section d1214h1-failure" id="failure">
      <div className="section-index">01 / FROZEN INSTRUMENT FAILURE</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> ONE MISSING NORMALIZATION FIELD</p><h2>不是 Blender 崩了。<br/><span>是 analyzer 没读懂自己的 schema。</span></h2></div>
        <p>Source、preflight 与 auditor 都会把全局 background subdivisions 展开进 owner。Analyzer 的 <code>effective_fixture</code> 只展开 size 与 transforms，却在 mesh gate 中读取缺失的 <code>owner[&quot;subdivisions&quot;]</code>。</p>
      </div>
      <div className="d1214h1-failure-grid">
        <article><span>EXPECTED</span><strong>normalized owner</strong><pre>{`background: {\n  sizeWorld,\n  subdivisions,\n  transformByFrame\n}`}</pre></article>
        <article className="fault"><span>OBSERVED</span><strong>field omitted</strong><pre>{`columns, rows = owner[\n  "subdivisions"\n]\n// KeyError`}</pre></article>
        <article><span>WHY PREFLIGHT MISSED IT</span><strong>producer-only smoke</strong><p>Preflight 验证 source report 与自己的 checker，没有让冻结 analyzer 消费 probe-shaped report。下一实验必须测试跨阶段 schema handoff。</p></article>
      </div>
      <div className="d1214h1-trace"><b>FAILED CHILD</b><code>analyzer · PID {failure.error.failedPid} · exit {failure.error.runnerExitCode}</code><span>{failure.error.exception}</span></div>
    </section>

    <section className="section d1214h1-evidence" id="evidence">
      <div className="section-index">02 / WHAT ACTUALLY COMPLETED</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PARTIAL EVIDENCE · PRESERVED, NOT PROMOTED</p><h2>失败点之前，<br/><span>每一层都留在证据树里。</span></h2></div>
        <p>Formal root 包含 12 个 multipart EXR、全部 source/adapter/consumer reports、canonical arrays 与 24 对 envelopes。Failure record 单独声明哪些数据存在、哪些决策链永远没有发生。</p>
      </div>
      <div className="d1214h1-process-grid">
        <article><span>BLENDER SOURCE</span><strong>{processes.sourceBlenderProcesses} / 12</strong><p>Cycles CPU · factory empty · fresh EXR</p></article>
        <article><span>ADAPTER</span><strong>{processes.adapterProcesses} / 6</strong><p>multipart roster → canonical arrays</p></article>
        <article><span>CONSUMERS</span><strong>{processes.pythonConsumerProcesses + processes.nodeConsumerProcesses} / 12</strong><p>Python + Node every array exact</p></article>
        <article><span>ENVELOPES</span><strong>{processes.typedEnvelopePythonProcesses + processes.typedEnvelopeNodeProcesses} / 24</strong><p>control + decision subtrees</p></article>
        <article className="failed"><span>ANALYZER</span><strong>0 / 1</strong><p>attempted once · frozen failure</p></article>
        <article className="blocked"><span>AUDIT + RECEIPT</span><strong>0 / 2</strong><p>correctly never created</p></article>
      </div>
    </section>

    <section className="section d1214h1-forensics" id="forensics">
      <div className="section-index">03 / POST-FAILURE FORENSICS · NON-DECISIONAL</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> READ-ONLY CLUES FOR THE NEXT PREREGISTRATION</p><h2>TOP 与 BOTTOM 很强。<br/><span>NEITHER 仍然不够。</span></h2></div>
        <p>这些计数来自已完成的 formal pass arrays，但读取发生在 analyzer 失败之后。它们只能指导新 ID；不能补造 H1 verdict。</p>
      </div>
      <div className="d1214h1-forensic-table" role="table" aria-label="Post-failure directional forensic counts">
        <div className="head" role="row"><b>CLASS</b><b>WITNESSES</b><b>ELIGIBLE</b><b>ACCEPTED</b><b>QUALITY MAX</b><b>STATUS</b></div>
        {cells.map(row => <div className={`row ${row.label.toLowerCase()}`} role="row" key={row.label}>
          <strong>{row.label}</strong><span>{row.witnesses.toLocaleString('en-US')}</span><span>{row.eligible.toLocaleString('en-US')}</span><span>{row.accepted.toLocaleString('en-US')}</span><code>{row.quality}</code><b>{row.status}</b>
        </div>)}
      </div>
      <div className="d1214h1-identity-split">
        <article className="pass"><span>DECODED SOURCE PASSES</span><strong>BYTE EXACT</strong><p>Repeat adapters 与 consumers 完全一致；Python/Node every array、24 envelope pairs 也一致。</p></article>
        <article className="fail"><span>EXR CONTAINER FILES</span><strong>NOT BYTE EXACT</strong><p>像素相同，但 Combined metadata 的 <code>Date</code>、<code>RenderTime</code>、<code>Scene</code> 不同。</p></article>
      </div>
    </section>

    <section className="section d1214h1-boundary" id="boundary">
      <div className="section-index">04 / NON-CLAIMS & NEXT EXPERIMENT</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> DO NOT REPAIR THE PAST</p><h2>H1 到此封闭。<br/><span>修复必须拥有新的 ID。</span></h2></div>
        <p>H1 不能支持、拒绝或修复 Material-owner mechanism，也不能改变 D12.13-D1 对 compiler promotion 的阻止。下一实验要把 failure mode 写进 spec，而不是悄悄修改旧工具。</p>
      </div>
      <div className="d1214h1-next-grid">
        <article><span>SCHEMA HANDOFF</span><strong>analyzer-on-probe smoke</strong><p>让真实 probe report 穿过 analyzer 的 normalization boundary。</p></article>
        <article><span>SOURCE IDENTITY</span><strong>canonical decoded digest</strong><p>像素/pass identity 与 EXR container metadata 分层判定。</p></article>
        <article><span>NEITHER DOMAIN</span><strong>≥ 1,024 witnesses</strong><p>以已披露 270 为 pilot input；不能降低旧 minimum。</p></article>
        <article><span>FAILURE TOTALITY</span><strong>runner finally receipt</strong><p>任何 child 失败也要留下 process roster 与 immutable failure chain。</p></article>
      </div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-owner-rigid-directional-render-holdout.v0.1.json`}><span>PREREGISTRATION</span><b>frozen H1 contract ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-rigid-directional-render-holdout-v0-1/failure.json`}><span>FAILURE RECORD</span><b>{failure.failureHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-14-h1-rendered-holdout-frozen-tool-failure.md`}><span>RESEARCH NOTE</span><b>cause + forensics + boundary ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.14-H1 Frozen Tool Failure</b></div><p>12 renders · 54 successful children · scientific verdict null</p><Link href="/blender-material-owner-rigid-directional-calibration-v0-1">返回 D12.14-C2 →</Link></footer>
  </main>;
}
