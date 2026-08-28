import type { Metadata } from 'next';
import Link from 'next/link';
import preflight from '../../experiments/blender-material-owner-projective-depth-holdout-preflight-v0-1/preflight.json';
import failure from '../../experiments/blender-material-owner-projective-depth-holdout-formal-invocation-failure-v0-1/failure.json';
import failureReceipt from '../../experiments/blender-material-owner-projective-depth-holdout-formal-invocation-failure-v0-1/receipt.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-projective-depth-formal-invalidation-v0-1/';

export const metadata: Metadata = {
  title: 'D12.14-H2 Formal Invocation Invalidated｜Blender Film Studio',
  description: '15/15 corrected preflight 通过，但冻结 runner 在启动任何 Blender child 前因相对/绝对路径 admission 缺口作废；0 render，scientific verdict 为 null。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.14-H2 · Preflight Passed, Formal Invalidated',
    description: '15/15 preflight · 0 formal children · 0 renders · null scientific verdict.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'D12.14-H2 · No Scientific Verdict',
    description: 'A green preflight did not cover the exact formal CLI path shape.',
    images: [],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const gates = preflight.evidenceChecks;

const admissionCases = [
  ['RELATIVE PATH', 'repo/path', '未覆盖', 'formal invocation 的实际输入形状'],
  ['ABSOLUTE PATH', '/repo/path', '内部假定', 'runner 的 relative_to 基准'],
  ['FRESH OUTPUT', 'absent → create', '未到达', 'formal root 保持不存在'],
  ['FAILURE RECEIPT', 'finally boundary', '未到达', '错误发生在 try/finally 之前'],
] as const;

export default function ProjectiveDepthFormalInvalidationPage() {
  return <main className="contact-page d1212-page d1214h2-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.14-H2 invalidation 导航">
        <Link href="/blender-projective-depth-position-oracle-v0-1">D12.14-P1</Link>
        <a href="#state">状态</a><a href="#preflight">Preflight</a><a href="#failure">失效点</a><a href="#boundary">边界</a><a href="#core">主线</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Formal H2 · Invalidated</span>
    </header>

    <section className="contact-hero d1214h2-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.14-H2 · CORRECTED PREFLIGHT · FORMAL ADMISSION FAILURE</p>
        <h1>15 道门全绿。<br/><span>实验仍然没有开始。</span></h1>
        <p>Corrected preflight 真正跑通了 nested Python/Node consumers 与完整 analyzer dry run；正式 runner 却在启动第一个 Blender child 前，把相对路径当成绝对路径处理。工具链失效不等于 hypothesis 被拒绝：H2 没有生成任何 measurement，也没有 scientific verdict。</p>
      </div>
      <aside className="contact-gate d1214h2-gate">
        <b>SCIENTIFIC VERDICT</b>
        <strong>NULL</strong>
        <code>{preflight.evidenceChecksPassed} / {preflight.evidenceChecksTotal} preflight gates</code>
        <code>same ID · rerun forbidden</code>
        <small>{failure.experimentId}</small>
      </aside>
      <div className="contact-stats">
        <article><strong>{preflight.operationCounts.childProcesses}</strong><span>preflight children</span><small>all exit zero · unique PIDs</small></article>
        <article><strong>{failure.operationCounts.childProcesses}</strong><span>formal children</span><small>admission failed first</small></article>
        <article><strong>{failure.operationCounts.blenderRenderCalls}</strong><span>formal renders</span><small>0 EXR · 0 Blender process</small></article>
        <article><strong>1</strong><span>frozen runner failure</span><small>{failure.execution.phase}</small></article>
      </div>
    </section>

    <section className="section d1214h2-state" id="state">
      <div className="section-index">00 / IMMUTABLE EXPERIMENT STATE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> ADMISSION IS PART OF THE INSTRUMENT</p><h2>没有重跑。<br/><span>没有换参数绕过去。</span></h2></div>
        <p>Spec、C1 consumer semantics、C2 tool correction、第二次 tool-freeze 与 corrected preflight 都先后提交并推送。Formal invocation 失败后，H2 立即封闭；absolute-path workaround 没有被当作“同一个实验”。</p>
      </div>
      <div className="d1214h2-chain">
        <article className="done"><span>01 · PREREG</span><strong>FROZEN</strong><code>fresh fixture · 4 renders planned</code><p>inverse depth、Position control、repeat identity 与 verdict mapping先冻结。</p></article><i>→</i>
        <article className="done"><span>02 · C2 TOOL FREEZE</span><strong>BOUND</strong><code>8 exact tool hashes</code><p>只修nested output parent，并增强full-shape preflight。</p></article><i>→</i>
        <article className="pass"><span>03 · PREFLIGHT</span><strong>{preflight.evidenceChecksPassed} / {preflight.evidenceChecksTotal}</strong><code>0 renders · 0 EXR</code><p>11个真实children；完整synthetic analyzer正确返回NOT_SUPPORTED。</p></article><i>→</i>
        <article className="failed"><span>04 · FORMAL</span><strong>INVALID</strong><code>exit {failure.execution.exitCode} · 0 children</code><p>relative/absolute path shape mismatch发生在failure-finally之前。</p></article>
      </div>
    </section>

    <section className="section d1214h2-preflight" id="preflight">
      <div className="section-index">01 / WHAT THE CORRECTED PREFLIGHT DID PROVE</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> GREEN, BUT DELIBERATELY PREFORMAL</p><h2>它不是假通过。<br/><span>它只是覆盖范围仍少了一层。</span></h2></div>
        <p>Corrected preflight确实复现了此前Node nested-parent故障、验证Python/Node every-array byte identity，并让完整analyzer在不足样本上只失败measurement gate。缺口是没有用formal runner自身执行exact CLI-shaped admission。</p>
      </div>
      <div className="d1214h2-gates">
        {gates.map((gate, index) => <article key={gate.name}><span>{String(index + 1).padStart(2, '0')}</span><strong>{gate.passed ? 'PASS' : 'FAIL'}</strong><code>{gate.name.replaceAll('_', ' ')}</code></article>)}
      </div>
      <div className="d1214h2-preflight-foot">
        <article><span>FACTORY PROBE</span><strong>{preflight.operationCounts.blenderProcesses}</strong><p>真实Blender 5.2 scene construction；render call为0。</p></article>
        <article><span>FULL-SHAPE ANALYZER</span><strong>11 / 12</strong><p>唯一false是故意不足的PROJECTIVE_DEPTH_MEASUREMENT。</p></article>
        <article><span>FREE BYTES OBSERVED</span><strong>{(preflight.disk.freeBytesObserved / 2 ** 30).toFixed(1)} GiB</strong><p>正式写入预算与100 GiB reserve gate均通过。</p></article>
      </div>
    </section>

    <section className="section d1214h2-failure" id="failure">
      <div className="section-index">02 / FROZEN ADMISSION DEFECT</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PATH VALUE ≠ PATH REPRESENTATION</p><h2>指向同一目录。<br/><span>Path 类型仍然不同。</span></h2></div>
        <p>CLI收到仓库内relative preflight root。Runner随后对它调用 <code>relative_to(absoluteRepoRoot)</code>；Python拒绝把relative Path表达为absolute root的子路径。错误位于output-root创建与runner try/finally之前。</p>
      </div>
      <div className="d1214h2-fault-code">
        <article><span>CALLER</span><strong>relative path</strong><pre>{`--preflight-root\nexperiments/...-preflight-v0-1`}</pre></article>
        <i>≠</i>
        <article className="fault"><span>RUNNER ASSUMPTION</span><strong>absolute child</strong><pre>{`cli.preflight_root.relative_to(\n  absolute_repository_root\n)`}</pre></article>
        <i>→</i>
        <article className="outcome"><span>OBSERVED</span><strong>{failure.error.type}</strong><pre>{`line 127 · ${failure.execution.phase}\nformal root · absent`}</pre></article>
      </div>
      <div className="d1214h2-trace"><b>FROZEN LOCATION</b><code>{failure.error.frozenLocation}</code><span>{failure.error.type} · exit {failure.execution.exitCode}</span></div>
    </section>

    <section className="section d1214h2-boundary" id="boundary">
      <div className="section-index">03 / NEXT FORMAL-RUN ADMISSION CONTRACT</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> TEST THE ACTUAL ENTRY SHAPE</p><h2>下一次不只测算法。<br/><span>还要测“如何开始实验”。</span></h2></div>
        <p>Future one-shot experiments必须在tool freeze前，让正式runner自己的admission层消费等价path shapes；preflight helper复制相同逻辑仍不够。这个新合同不追溯修复H2。</p>
      </div>
      <div className="d1214h2-admission-grid">
        {admissionCases.map(([name, shape, status, note]) => <article key={name}><span>{name}</span><strong>{shape}</strong><code>{status}</code><p>{note}</p></article>)}
      </div>
      <div className="d1214h2-rule"><span>NEW INVARIANT</span><strong>admission must be total before render authorization</strong><p>relative/absolute equivalence · containment · fresh root · pushed evidence lookup · failure receipt reachability</p></div>
    </section>

    <section className="section d1214h2-core" id="core">
      <div className="section-index">04 / RETURN TO THE PRIMARY COMPILER GOAL</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> H2 FAILURE DOES NOT ERASE B01 / B02</p><h2>算法实验封闭。<br/><span>核心编译器证据仍成立。</span></h2></div>
        <p>H2后重新运行SceneSpec suite、BuildPlan双编译、四份native receipts verifier，并重算macOS与Linux/amd64八份canonical structure字节流。主目标仍被直接证据支持。</p>
      </div>
      <div className="d1214h2-core-grid">
        <article><span>SCENESPEC</span><strong>22 / 22</strong><p>valid/invalid fixtures expected outcome exact</p></article>
        <article><span>NATIVE RECEIPTS</span><strong>4 / 4</strong><p>19 exact bindings each</p></article>
        <article><span>B01 STRUCTURE</span><strong>c699fc27…</strong><p>4/4 native + worker streams</p></article>
        <article><span>B02 STRUCTURE</span><strong>025c6fa5…</strong><p>4/4 native + worker streams</p></article>
      </div>
      <div className="contact-artifacts">
        <a href={`${repo}experiments/blender-material-owner-projective-depth-holdout-preflight-v0-1/preflight.json`}><span>CORRECTED PREFLIGHT</span><b>{preflight.preflightHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-projective-depth-holdout-formal-invocation-failure-v0-1/failure.json`}><span>FORMAL FAILURE</span><b>{failure.failureHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-projective-depth-holdout-formal-invocation-failure-v0-1/receipt.json`}><span>FAILURE RECEIPT</span><b>{failureReceipt.receiptHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}research/2026-08-28-post-h2-core-compiler-revalidation.md`}><span>CORE REVALIDATION</span><b>B01 / B02 current evidence ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.14-H2 Formal Invocation Invalidated</b></div><p>15/15 preflight · 0 formal renders · scientific verdict null</p><Link href="/compiler-v0-1">返回核心编译器 →</Link></footer>
  </main>;
}
