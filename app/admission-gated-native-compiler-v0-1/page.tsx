import type { Metadata } from 'next';
import Link from 'next/link';
import spec from '../../specs/admission-gated-native-compiler-integration.v0.1.json';
import preflight from '../../experiments/admission-gated-native-compiler-preflight-v0-1/preflight.json';
import audit from '../../experiments/admission-gated-native-compiler-v0-1/audit.json';
import result from '../../experiments/admission-gated-native-compiler-v0-1/results.json';
import receipt from '../../experiments/admission-gated-native-compiler-v0-1/receipt.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/admission-gated-native-compiler-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

export const metadata: Metadata = {
  title: 'B54-E1 Admission-gated Native Blender Compiler｜Blender Film Studio',
  description: '四次 Blender 5.2 fresh compile、四份 19-check receipt、B01/B02 结构哈希全部复现；实验仍因 native PID 未被 budget report 绑定而以 17/18 gates 拒绝。',
  alternates: { canonical },
  openGraph: {
    title: 'B54-E1 · The Compiler Passed. The Experiment Rejected.',
    description: '4/4 native compiles · 4×19 receipt checks · 33/33 attacks · one missing OS PID binding.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'B54-E1 · 17 Gates Pass, 1 Evidence Gate Fails',
    description: 'A falsifiable SceneSpec → BuildPlan → Blender 5.2 integration result.',
    images: [],
  },
};

type RunAudit = {
  runId: string;
  benchmark: string;
  rosterExact: boolean;
  framesEmpty: boolean;
  verifierExact: boolean;
  blendBindingExact: boolean;
  structureSha256: string;
  blendSha256: string;
  nativeChildPid: number | null;
};

const runAudits = audit.runAudits as RunAudit[];
const failedGates = Object.entries(audit.gates).filter(([, passed]) => !passed).map(([gate]) => gate);
const gateLabels: Record<string, string> = {
  SPEC_PARENT_RUNTIME_AND_TOOL_IDENTITIES: 'Frozen identities',
  ZERO_BLENDER_PREFLIGHT_ACCEPTED_AND_PUSHED: 'Preflight accepted + pushed',
  RELATIVE_PATH_FORMAL_ADMISSION_ACCEPTED: 'Relative admission',
  ATTEMPT_ADMISSION_AND_RECEIPT_SELF_HASH_EXACT: 'Attempt ledger exact',
  FORMAL_ROOT_MATERIALIZED_ONLY_AFTER_ADMISSION: 'Authorization ordering',
  SCENESPEC_SUITE_22_OF_22: 'SceneSpec 22/22',
  BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: 'BuildPlan pair bytes',
  B01_B02_PLAN_HASHES_FROZEN: 'Plan hashes frozen',
  FOUR_FRESH_RESTRICTED_COMPILES_PASS: '4 fresh compiles',
  FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: '4 × 19 checks',
  B01_B02_PAIR_STRUCTURE_BYTES_EXACT: 'Structure pair bytes',
  B01_B02_STRUCTURE_HASHES_FROZEN: 'Structure hashes frozen',
  FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: '.blend bindings',
  NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: 'Output roster exact',
  DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT: 'Native PID binding',
  MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: 'Forbidden work zero',
  INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_24: '33 attacks rejected',
  VERDICT_MAPPING_OUTCOME_NEUTRAL: 'Outcome-neutral verdict',
};

const sequence = [
  ['01', 'ATTEMPT', 'durable before admission', '0 Blender authorized'],
  ['02', 'ADMISSION', 'relative evidence accepted', 'fresh output identity'],
  ['03', 'RECEIPT', 'authorization durable', 'formal root still absent'],
  ['04', 'COMPILE × 4', 'B01-A/B · B02-A/B', 'native Blender 5.2'],
  ['05', 'INDEPENDENT AUDIT', '4 verifier · 4 .blend audit', '33 attacks'],
] as const;

export default function AdmissionGatedNativeCompilerPage() {
  return <main className="contact-page b54-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B54-E1 native compiler integration 导航">
        <Link href="/formal-runner-admission-totality-v0-1">B53 准入</Link>
        <Link href="/budgeted-native-child-pid-receipt-v0-1">B55 PID 修正</Link>
        <a href="#sequence">时序</a><a href="#reproduction">复现</a><a href="#gates">门</a><a href="#pid-gap">PID 缺口</a><a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">B54-E1 · Rejected</span>
    </header>

    <section className="contact-hero b54-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> REAL BLENDER 5.2 · FOUR FRESH BUILDS · OUTCOME-NEUTRAL AUDIT</p>
        <h1>编译器通过了。<br/><span>实验仍然拒绝。</span></h1>
        <p>SceneSpec、immutable BuildPlan、四次native Blender compile、CompileReceipt与结构哈希全部复现。但科研合同要求native Blender PID进入budget evidence；current supervisor只记录command、args、exit与metrics。我们保留这一个false gate，不把“知道启动过Blender”冒充“完成OS PID attestation”。</p>
      </div>
      <aside className="contact-gate b54-gate">
        <b>FORMAL VERDICT</b>
        <strong>REJECTED</strong>
        <code>{audit.gatePassed} / {audit.gateTotal} frozen gates</code>
        <code>{audit.semanticAttacksPassed} / {audit.semanticAttackCount} attacks rejected</code>
        <small>{result.experimentId} · same ID closed</small>
      </aside>
      <div className="contact-stats">
        <article><strong>4/4</strong><span>native compiles</span><small>fresh outputs · budget PASS</small></article>
        <article><strong>4×19</strong><span>receipt checks</span><small>current verifier · PASS OK</small></article>
        <article><strong>2/2</strong><span>structure identities</span><small>B01 / B02 pair-byte exact</small></article>
        <article><strong>0</strong><span>render calls</span><small>0 network · model · Docker</small></article>
      </div>
    </section>

    <section className="section b54-sequence" id="sequence">
      <div className="section-index">00 / AUTHORIZATION BEFORE COMPUTE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> B53 INSTRUMENT → REAL COMPILER ENTRY</p><h2>先留下授权证据。<br/><span>再允许Blender启动。</span></h2></div>
        <p>Formal runner没有改变production compiler。它只在入口外增加single-use ledger：attempt、accepted admission和receipt必须先写入另一个root；formal root直到sequence 4才可物化。</p>
      </div>
      <div className="b54-sequence-map">
        {sequence.map(([id, title, line, note], index) => <div className="b54-sequence-node" key={id}>
          <article><span>{id}</span><strong>{title}</strong><code>{line}</code><p>{note}</p></article>
          {index < sequence.length - 1 ? <i aria-hidden="true">→</i> : null}
        </div>)}
      </div>
      <div className="b54-preflight-strip">
        <article><span>ZERO-BLENDER PREFLIGHT</span><strong>{preflight.checkPassed}/{preflight.checkTotal}</strong><p>tracked · pushed · runtime · hashes · relative path · disk</p></article>
        <article><span>FORMAL MATERIALIZATION</span><strong>sequence 4</strong><p>attempt receipt durable before formal root</p></article>
        <article><span>ADMISSION REPLAY</span><strong>{audit.admissionReplay.relativeAdmissionAccepted ? 'EXACT' : 'FAIL'}</strong><p>independent path and Git evidence readback</p></article>
      </div>
    </section>

    <section className="section b54-reproduction" id="reproduction">
      <div className="section-index">01 / WHAT ACTUALLY REPRODUCED</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> SEMANTIC IDENTITY, NOT .BLEND CONTAINER BYTES</p><h2>两次净构建。<br/><span>同一份场景结构。</span></h2></div>
        <p>每个benchmark先生成两次BuildPlan并比较canonical wrapper bytes，再执行A/B两次fresh native compile。Acceptance比较canonical structure stream；`.blend` file hash被记录，但不要求相等。</p>
      </div>
      <div className="b54-run-table" role="table" aria-label="B54-E1 four native compiler runs">
        <div className="head" role="row"><b>RUN</b><b>PLAN</b><b>STRUCTURE</b><b>19 CHECKS</b><b>.BLEND</b><b>PID</b></div>
        {runAudits.map(run => <div className="row" role="row" key={run.runId}>
          <strong>{run.runId}<small>{run.rosterExact && run.framesEmpty ? 'fresh roster exact' : 'roster fail'}</small></strong>
          <code>{result.runBindings.find(binding => binding.runId === run.runId)?.planHash.slice(0, 12)}…</code>
          <code>{run.structureSha256.slice(0, 12)}…</code>
          <b className="pass">{run.verifierExact ? 'PASS' : 'FAIL'}</b>
          <code>{run.blendBindingExact ? 'BOUND' : 'FAIL'}</code>
          <b className="missing">{run.nativeChildPid ?? 'NULL'}</b>
        </div>)}
      </div>
      <div className="b54-identities">
        {result.planIdentities.map(plan => <article key={plan.benchmark}><span>{plan.benchmark} BUILDPLAN</span><strong>{plan.firstPlanHash}</strong><code>pair canonical SHA · {plan.firstCanonicalSha256}</code></article>)}
        {spec.inputs.benchmarks.map(benchmark => <article key={benchmark.id}><span>{benchmark.id} STRUCTURE</span><strong>{benchmark.expectedStructureHash}</strong><code>A/B canonical bytes exact</code></article>)}
      </div>
    </section>

    <section className="section b54-gate-section" id="gates">
      <div className="section-index">02 / ALL 18 FROZEN GATES</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> ONE FALSE MEANS REJECTED</p><h2>十七项绿色。<br/><span>不能投票盖过一项红色。</span></h2></div>
        <p>Verdict mapping在审计里同时验证all-true与any-false两条路径。它不知道我们“希望”得到什么；它只消费18个observed booleans。</p>
      </div>
      <div className="b54-gates">
        {Object.entries(audit.gates).map(([gate, passed], index) => <article className={passed ? 'pass' : 'fail'} key={gate}>
          <span>{String(index + 1).padStart(2, '0')}</span><i aria-hidden="true" /><strong>{passed ? 'PASS' : 'FAIL'}</strong><code>{gateLabels[gate] ?? gate}</code>
        </article>)}
      </div>
      <div className="b54-verdict-equation"><span>VERDICT</span><strong>17 PASS + 1 FAIL</strong><i>→</i><b>REJECTED</b><code>{failedGates[0]}</code></div>
    </section>

    <section className="section b54-pid" id="pid-gap">
      <div className="section-index">03 / THE SINGLE OBSERVED GAP</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> SEMANTIC INVOCATION ≠ OS PROCESS ATTESTATION</p><h2>我们知道Blender运行了。<br/><span>但receipt没有它的PID。</span></h2></div>
        <p>Budget supervisor内部拿得到child PID，却只把exitCode、signal和spawnError写进report。其余证据足以验证结果和资源，但不足以满足冻结的native PID binding强要求。</p>
      </div>
      <div className="b54-pid-machine">
        <article className="source"><span>NODE SUPERVISOR</span><strong>spawn()</strong><code>child.pid exists in memory</code></article><i>→</i>
        <article className="report"><span>BUDGET REPORT</span><ul><li className="yes">command ✓</li><li className="yes">args ✓</li><li className="yes">exit + metrics ✓</li><li className="no">native PID ✕</li></ul></article><i>→</i>
        <article className="decision"><span>FROZEN GATE</span><strong>FALSE</strong><code>do not infer · do not fabricate</code></article>
      </div>
      <div className="b54-process-grid">
        <article><span>RUNNER DIRECT CHILDREN</span><strong>4</strong><p>PIDs、args、exit、elapsed与stdout/stderr hashes exact。</p></article>
        <article><span>AUDITOR DIRECT CHILDREN</span><strong>8</strong><p>4 verifier + 4 `.blend` audits；roster exact。</p></article>
        <article><span>SEMANTIC INVOCATIONS</span><strong>20</strong><p>4 compile + 4 receipt probes + 4 verifier + 4 verifier probes + 4 blend audits。</p></article>
        <article className="gap"><span>NATIVE PID BINDINGS</span><strong>0/4</strong><p>B55已在新ID里修正这一字段；B54 evidence保持不变。</p></article>
      </div>
    </section>

    <section className="section b54-boundary" id="boundary">
      <div className="section-index">04 / RESULT AND NEXT INTERVENTION</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> REJECTED DOES NOT MEAN NOTHING WORKED</p><h2>保留成功的链。<br/><span>只修正失败的证据字段。</span></h2></div>
        <p>B54-E1同一ID已经封闭。Observed follow-up B55-E1只修改budget supervisor，把spawn返回的native PID写入v0.2 report，并以child-authored PID/PPID与全部B01/B02回归门独立验证。</p>
      </div>
      <div className="b54-boundary-grid">
        <article className="preserve"><span>PRESERVED OBSERVATION</span><strong>compiler semantics</strong><p>SceneSpec、BuildPlan、四次compile、receipt、structure与blend bindings全部通过。</p></article>
        <article className="reject"><span>REJECTED CLAIM</span><strong>complete PID evidence</strong><p>Current budget report不能证明native Blender OS PID。</p></article>
        <article><span>NON-CLAIM</span><strong>cinematic pixels</strong><p>没有render frame；本实验不评价影像真实感或电影感。</p></article>
        <article className="next"><span>OBSERVED FOLLOW-UP</span><strong>22/22 supported</strong><p>三处exact replacement · 四类PID probes · 四次fresh regression。<br/><Link href="/budgeted-native-child-pid-receipt-v0-1">查看B55完整证据 →</Link></p></article>
      </div>
      <div className="b54-nonclaims">
        {spec.nonClaims.map((claim, index) => <p key={claim}><span>{String(index + 1).padStart(2, '0')}</span>{claim}</p>)}
      </div>
      <div className="contact-artifacts b54-artifacts">
        <a href={`${repo}specs/admission-gated-native-compiler-integration.v0.1.json`}><span>FROZEN SPEC</span><b>{preflight.specSha256.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/admission-gated-native-compiler-v0-1/results.json`}><span>RESULTS</span><b>{result.resultHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/admission-gated-native-compiler-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>{audit.auditHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/admission-gated-native-compiler-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>{receipt.receiptHash.slice(0, 16)}… ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B54-E1 Native Compiler Integration</b></div><p>4/4 compiles · 17/18 gates · 33/33 attacks · 0 renders</p><Link href="/budgeted-native-child-pid-receipt-v0-1">继续到B55 PID修正 →</Link></footer>
  </main>;
}
