import type { Metadata } from 'next';
import Link from 'next/link';
import spec from '../../specs/budgeted-native-child-pid-receipt-correction.v0.1.json';
import preflight from '../../experiments/budgeted-native-child-pid-receipt-preflight-v0-1/preflight.json';
import audit from '../../experiments/budgeted-native-child-pid-receipt-v0-1/audit.json';
import result from '../../experiments/budgeted-native-child-pid-receipt-v0-1/results.json';
import receipt from '../../experiments/budgeted-native-child-pid-receipt-v0-1/receipt.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/budgeted-native-child-pid-receipt-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

export const metadata: Metadata = {
  title: 'B55-E1 Native Child PID Receipt Correction｜Blender Film Studio',
  description: '用三处最小 supervisor 变化把原生 Blender PID 写入 budget receipt；四类自报 PID 探针、四次 B01/B02 fresh compile、22/22 gates 与 41/41 attacks 全部通过。',
  alternates: { canonical },
  openGraph: {
    title: 'B55-E1 · The Missing PID Is Now a Receipt',
    description: '3 exact source replacements · 4 corroborating probes · 4 native Blender compiles · 22/22 gates.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'B55-E1 · Native Blender PID Receipt Supported',
    description: 'A minimal, falsifiable correction with no rendered pixels.',
    images: [],
  },
};

type Probe = {
  id: string;
  exact: boolean;
  report: {
    outcome: string;
    version: string;
    breach: { reason: string } | null;
    child: { pid: number | null; exitCode: number | null; spawnError: string | null };
    termination: { requested: boolean; awaited: boolean };
  };
  observation: { pid: number; ppid: number } | null;
};

type RunAudit = {
  runId: string;
  benchmark: string;
  nativeChildPid: number;
  nativePidReceiptSchemaExact: boolean;
  receiptBudgetFileHashBindingExact: boolean;
  verifierExact: boolean;
  blendBindingExact: boolean;
  structureSha256: string;
};

const probes = preflight.pidProbes.cases as Probe[];
const runAudits = audit.runAudits as RunAudit[];
const gateLabels: Record<string, string> = {
  SPEC_PARENT_RUNTIME_AND_TOOL_IDENTITIES: 'Frozen identities',
  B54_SINGLE_PID_GAP_BOUND_EXACT: 'B54 single gap',
  SUPERVISOR_CHANGE_MINIMAL_AND_SCHEMA_V0_2: 'Minimal v0.2 change',
  ZERO_BLENDER_PID_PROBE_PREFLIGHT_ACCEPTED_AND_PUSHED: 'Zero-Blender preflight',
  PID_PROBE_PASS_FAIL_BREACH_AND_SPAWN_ERROR_EXACT: 'Four PID probes',
  RELATIVE_PATH_FORMAL_ADMISSION_ACCEPTED: 'Relative admission',
  ATTEMPT_ADMISSION_AND_RECEIPT_SELF_HASH_EXACT: 'Attempt ledger exact',
  FORMAL_ROOT_MATERIALIZED_ONLY_AFTER_ADMISSION: 'Authorization ordering',
  SCENESPEC_SUITE_22_OF_22: 'SceneSpec 22/22',
  BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: 'BuildPlan pair bytes',
  B01_B02_PLAN_HASHES_FROZEN: 'Plan hashes frozen',
  FOUR_FRESH_RESTRICTED_COMPILES_PASS: '4 fresh compiles',
  FOUR_NATIVE_PID_RECEIPT_SCHEMAS_EXACT: '4 native PID receipts',
  FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: '4 × 19 checks',
  B01_B02_PAIR_STRUCTURE_BYTES_EXACT: 'Structure pair bytes',
  B01_B02_STRUCTURE_HASHES_FROZEN: 'Structure hashes frozen',
  FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: '.blend bindings',
  NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: 'Output roster exact',
  DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT: 'Process counts exact',
  MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: 'Forbidden work zero',
  INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_32: '41 attacks rejected',
  VERDICT_MAPPING_OUTCOME_NEUTRAL: 'Outcome-neutral verdict',
};

const corrections = [
  ['01', 'CAPTURE', 'child.pid immediately after spawn()'],
  ['02', 'VERSION', 'BFS_BUDGETED_PROCESS_RESULT 0.1 → 0.2'],
  ['03', 'PERSIST', 'child: { pid, exitCode, signal, spawnError }'],
] as const;

function short(value: string) {
  return `${value.slice(0, 12)}…`;
}

export default function BudgetedNativeChildPidReceiptPage() {
  return <main className="contact-page b55-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B55-E1 native PID receipt 导航">
        <Link href="/admission-gated-native-compiler-v0-1">B54 缺口</Link>
        <a href="#causal">修正</a><a href="#probes">探针</a><a href="#native-runs">编译</a><a href="#gates">门</a><a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">B55-E1 · Supported</span>
    </header>

    <section className="contact-hero b55-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> MINIMAL PRODUCTION CHANGE · CHILD-AUTHORED CORROBORATION · REAL BLENDER 5.2</p>
        <h1>PID不是猜出来的。<br/><span>现在它进入receipt了。</span></h1>
        <p>B54的编译链全部通过，却因为budget report没有保存native Blender PID而以17/18拒绝。B55只改变同一个supervisor的三处语义，再用子进程自写PID/PPID和四次真实Blender净构建检验：缺口闭合，结构没有回退。</p>
      </div>
      <aside className="contact-gate b55-gate">
        <b>FORMAL VERDICT</b>
        <strong>SUPPORTED</strong>
        <code>{audit.gatePassed} / {audit.gateTotal} frozen gates</code>
        <code>{audit.semanticAttacksPassed} / {audit.semanticAttackCount} attacks rejected</code>
        <small>{result.experimentId} · same ID closed</small>
      </aside>
      <div className="contact-stats">
        <article><strong>3</strong><span>exact replacements</span><small>one production file</small></article>
        <article><strong>4/4</strong><span>PID probes</span><small>pass · fail · breach · spawn error</small></article>
        <article><strong>4/4</strong><span>native compiles</span><small>PID-bearing budget reports</small></article>
        <article><strong>0</strong><span>render calls</span><small>0 network · model · Docker</small></article>
      </div>
    </section>

    <section className="section b55-causal-section" id="causal">
      <div className="section-index">00 / ONE OBSERVED GAP → ONE BOUNDED CORRECTION</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> DO NOT REWRITE B54</p><h2>历史仍然拒绝。<br/><span>新证据单独成立。</span></h2></div>
        <p>B55没有往B54旧report里补字段。它把B54的single false gate作为parent evidence，冻结before bytes，再在新ID里验证after bytes、行为探针和全部B01/B02回归。</p>
      </div>
      <div className="b55-causal">
        <article className="rejected"><span>B54-E1</span><strong>17 / 18</strong><code>native PID = absent</code><p>compiler semantics passed<br/>evidence claim rejected</p></article>
        <i aria-hidden="true">→</i>
        <article className="change"><span>INTERVENTION</span><strong>3 / 3</strong><code>single replacements exact</code><p>capture · version · persist</p></article>
        <i aria-hidden="true">→</i>
        <article><span>ZERO-BLENDER PROBES</span><strong>4 / 4</strong><code>PID / PPID corroborated</code><p>spawn error PID = null</p></article>
        <i aria-hidden="true">→</i>
        <article className="supported"><span>B55-E1</span><strong>22 / 22</strong><code>native PID = receipt</code><p>41 / 41 attacks rejected</p></article>
      </div>
      <div className="b55-diff">
        <article><span>BEFORE · v0.1</span><strong>{preflight.supervisorMinimality.beforeSha256}</strong><code>child: exitCode · signal · spawnError</code></article>
        <div>
          {corrections.map(([id, title, line]) => <p key={id}><span>{id}</span><b>{title}</b><code>{line}</code></p>)}
        </div>
        <article><span>AFTER · v0.2</span><strong>{preflight.supervisorMinimality.afterSha256}</strong><code>child: pid · exitCode · signal · spawnError</code></article>
      </div>
    </section>

    <section className="section b55-probe-section" id="probes">
      <div className="section-index">01 / CHILD-AUTHORED CORROBORATION</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> A POSITIVE INTEGER IS NOT ENOUGH</p><h2>让子进程自己写下PID。<br/><span>再与supervisor receipt对照。</span></h2></div>
        <p>三种真正spawn成功的Node child先写自己的PID与PPID：report PID必须逐个相等，PPID必须等于preflight进程。第四种不存在的executable不得伪造PID，只能记录null和spawn error。</p>
      </div>
      <div className="b55-probes">
        {probes.map((probe, index) => <article className={probe.observation ? 'spawned' : 'no-spawn'} key={probe.id}>
          <span>{String(index + 1).padStart(2, '0')} · {probe.id}</span>
          <strong>{probe.report.outcome}</strong>
          <dl>
            <div><dt>REPORT PID</dt><dd>{probe.report.child.pid ?? 'NULL'}</dd></div>
            <div><dt>CHILD SAYS</dt><dd>{probe.observation?.pid ?? 'NO CHILD'}</dd></div>
            <div><dt>PPID</dt><dd>{probe.observation?.ppid ?? '—'}</dd></div>
            <div><dt>EXIT / BREACH</dt><dd>{probe.report.breach?.reason ?? probe.report.child.exitCode}</dd></div>
          </dl>
          <code>v{probe.report.version} · {probe.exact ? 'EXACT' : 'FAIL'}</code>
        </article>)}
      </div>
      <div className="b55-probe-note"><span>PREFLIGHT PROCESS</span><strong>PID {preflight.pidProbes.preflightPid}</strong><p>3 child PPIDs exact · 1 spawn failure has no PID · Blender processes 0</p></div>
    </section>

    <section className="section b55-runs" id="native-runs">
      <div className="section-index">02 / FOUR FRESH NATIVE BLENDER COMPILES</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PID RECEIPT WITHOUT STRUCTURE REGRESSION</p><h2>换了证据schema。<br/><span>没有换掉场景语义。</span></h2></div>
        <p>每个benchmark仍先做两次immutable BuildPlan canonical比较，再运行A/B fresh compile。Current CompileReceipt verifier保持不变：每份19 checks；receipt用file SHA绑定完整PID-bearing budget report。</p>
      </div>
      <div className="b54-run-table b55-run-table" role="table" aria-label="B55-E1 four native PID-bearing Blender runs">
        <div className="head" role="row"><b>RUN</b><b>WRAPPER PID</b><b>BLENDER PID</b><b>REPORT</b><b>19 CHECKS</b><b>STRUCTURE</b></div>
        {runAudits.map(run => {
          const binding = result.runBindings.find(row => row.runId === run.runId);
          return <div className="row" role="row" key={run.runId}>
            <strong>{run.runId}<small>{run.benchmark} fresh output</small></strong>
            <code>{binding?.budget.restrictedWrapperPid}</code>
            <b className="pid">{run.nativeChildPid}</b>
            <b className="pass">{run.nativePidReceiptSchemaExact && run.receiptBudgetFileHashBindingExact ? 'v0.2 BOUND' : 'FAIL'}</b>
            <b className="pass">{run.verifierExact ? 'PASS' : 'FAIL'}</b>
            <code>{short(run.structureSha256)}</code>
          </div>;
        })}
      </div>
      <div className="b55-identities">
        {result.planIdentities.map(plan => <article key={plan.benchmark}><span>{plan.benchmark} BUILDPLAN</span><strong>{plan.firstPlanHash}</strong><code>dual canonical bytes exact</code></article>)}
        {spec.inputs.benchmarks.map(benchmark => <article key={benchmark.id}><span>{benchmark.id} STRUCTURE</span><strong>{benchmark.expectedStructureHash}</strong><code>A/B canonical bytes exact</code></article>)}
      </div>
    </section>

    <section className="section b55-gate-section" id="gates">
      <div className="section-index">03 / ALL 22 FROZEN GATES</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> OUTCOME-NEUTRAL MAPPING</p><h2>二十二项全绿。<br/><span>才允许写下SUPPORTED。</span></h2></div>
        <p>41种one-field attacks覆盖missing、null、string、fractional、non-positive、parent PID、wrong version与receipt hash不跟随等PID篡改，并保留B54所有compiler regression门。</p>
      </div>
      <div className="b54-gates b55-gates">
        {Object.entries(audit.gates).map(([gate, passed], index) => <article className={passed ? 'pass' : 'fail'} key={gate}>
          <span>{String(index + 1).padStart(2, '0')}</span><i aria-hidden="true"/><strong>{passed ? 'PASS' : 'FAIL'}</strong><code>{gateLabels[gate] ?? gate}</code>
        </article>)}
      </div>
      <div className="b55-equation"><span>FORMAL RESULT</span><strong>22 PASS + 0 FAIL</strong><i>→</i><b>SUPPORTED</b><code>{audit.semanticAttacksPassed} / {audit.semanticAttackCount} semantic attacks rejected</code></div>
    </section>

    <section className="section b55-boundary" id="boundary">
      <div className="section-index">04 / WHAT THE PID DOES — AND DOES NOT — PROVE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> LOCAL SPAWN RECEIPT ≠ REMOTE ATTESTATION</p><h2>证据变强了。<br/><span>边界也必须写在同一页。</span></h2></div>
        <p>Frozen supervisor确实保存了Node spawn返回的PID，controlled child self-report使常量、parent PID和事后猜数可被反证。但supervisor仍属于本地信任基，PID退出后也可能被OS复用。</p>
      </div>
      <div className="b55-boundary-grid">
        <article className="claim"><span>SUPPORTED CLAIM</span><strong>spawn PID persisted</strong><p>四份native budget receipts、四份CompileReceipts与independent audit共同绑定。</p></article>
        <article><span>CORROBORATION</span><strong>child-authored PID / PPID</strong><p>PASS、child failure与budget kill三条不同outcome路径均exact。</p></article>
        <article className="limit"><span>NON-CLAIM</span><strong>cryptographic identity</strong><p>不是remote attestation；不能抵御恶意改写的supervisor或证明PID永不复用。</p></article>
        <article className="next"><span>NEXT TECHNICAL GAP</span><strong>production entry promotion</strong><p>Admission + v0.2 PID receipt尚未成为公开preferred compiler entry，需要独立release contract。</p></article>
      </div>
      <div className="b55-nonclaims">
        {spec.nonClaims.map((claim, index) => <p key={claim}><span>{String(index + 1).padStart(2, '0')}</span>{claim}</p>)}
      </div>
      <div className="contact-artifacts b55-artifacts">
        <a href={`${repo}specs/budgeted-native-child-pid-receipt-correction.v0.1.json`}><span>FROZEN SPEC</span><b>{short(preflight.specSha256)} ↗</b></a>
        <a href={`${repo}scripts/lib/budgeted-process.mjs`}><span>SUPERVISOR v0.2</span><b>{short(preflight.supervisorMinimality.afterSha256)} ↗</b></a>
        <a href={`${repo}experiments/budgeted-native-child-pid-receipt-v0-1/results.json`}><span>RESULTS</span><b>{short(result.resultHash)} ↗</b></a>
        <a href={`${repo}experiments/budgeted-native-child-pid-receipt-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>{short(audit.auditHash)} ↗</b></a>
        <a href={`${repo}experiments/budgeted-native-child-pid-receipt-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>{short(receipt.receiptHash)} ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B55-E1 Native Child PID Receipt</b></div><p>3 replacements · 4 probes · 4 compiles · 22/22 gates · 41/41 attacks · 0 renders</p><Link href="/admission-gated-native-compiler-v0-1">查看B54原始缺口 →</Link></footer>
  </main>;
}
