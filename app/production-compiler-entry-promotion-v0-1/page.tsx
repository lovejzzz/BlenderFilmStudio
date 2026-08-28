import type { Metadata } from 'next';
import Link from 'next/link';
import promotionSpec from '../../specs/production-compiler-entry-promotion.v0.1.json';
import release from '../../specs/production-compiler-entry.v0.1.json';
import preflight from '../../experiments/production-compiler-entry-promotion-preflight-v0-1/preflight.json';
import result from '../../experiments/production-compiler-entry-promotion-v0-1/results.json';
import audit from '../../experiments/production-compiler-entry-promotion-v0-1/audit.json';
import receipt from '../../experiments/production-compiler-entry-promotion-v0-1/receipt.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/production-compiler-entry-promotion-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

export const metadata: Metadata = {
  title: 'B56-E1 Production Compiler Entry Promotion｜Blender Film Studio',
  description: '把 SceneSpec → BuildPlan → Blender 5.2 净构建提升为受准入约束的正式生产入口；4 次真实编译、27/27 gates 与 64/64 attacks 通过。',
  alternates: { canonical },
  openGraph: {
    title: 'B56-E1 · A Production Entry, Not Another Script',
    description: '3 preferred aliases · 4 native Blender compiles · 27/27 gates · 64/64 attacks.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'B56-E1 · Production Compiler Entry Supported',
    description: 'An admission-gated, receipted Blender 5.2 production entry with no rendered pixels.',
    images: [],
  },
};

type NegativeProbe = {
  id: string;
  exact: boolean;
  reason: string;
  child?: { exitCode: number | null; pid: number | null; signal: string | null };
};

const negativeProbes = preflight.observations.negative.rows as NegativeProbe[];
const aliases = Object.entries(release.packageAliases);
const gateLabels: Record<string, string> = {
  B01_B02_PAIR_STRUCTURE_BYTES_EXACT: 'Structure pair bytes',
  B01_B02_PLAN_HASHES_FROZEN: 'Plan hashes frozen',
  B01_B02_STRUCTURE_HASHES_FROZEN: 'Structure hashes frozen',
  B55_SUPPORTED_PARENT_BOUND_EXACT: 'B55 parent exact',
  BUILDPLAN_PAIR_CANONICAL_BYTES_EXACT: 'BuildPlan pair bytes',
  DIRECT_PROCESS_AND_SEMANTIC_OPERATION_COUNTS_EXACT: 'Process counts exact',
  FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: '.blend bindings',
  FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: '4 × 19 current checks',
  FOUR_NATIVE_PID_RECEIPT_SCHEMAS_EXACT: '4 native PID receipts',
  FOUR_OUTPUT_ROOTS_MATERIALIZED_ONLY_AFTER_DURABLE_RECEIPT: 'Output after receipt',
  FOUR_PREFERRED_PRODUCTION_ALIAS_COMPILES_PASS: '4 preferred compiles',
  FOUR_PREFERRED_PRODUCTION_VERIFIERS_PASS: '4 preferred verifiers',
  FOUR_PREFLIGHT_SCENE_OUTPUT_AND_TOOL_BINDINGS_EXACT: '4 preflight bindings',
  FOUR_PRODUCTION_ATTEMPTS_PRECEDE_ADMISSION: 'Attempts precede admission',
  FOUR_PRODUCTION_RECEIPTS_BIND_COMPLETE_CHAIN: 'Complete chain receipts',
  INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_48: '64 attacks rejected',
  META_ATTEMPT_ADMISSION_AND_RECEIPT_SELF_HASH_EXACT: 'Meta ledgers exact',
  MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: 'Forbidden work zero',
  NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: 'Output roster exact',
  PACKAGE_DELTA_EXACTLY_THREE_ALIASES: 'Only three aliases',
  PREFLIGHT_NEGATIVE_PROBES_FAIL_CLOSED: '9 negative probes',
  RELEASE_MANIFEST_AND_SEVEN_NEW_TOOLS_FROZEN: 'Release + tools frozen',
  SCENESPEC_SUITE_22_OF_22: 'SceneSpec 22/22',
  SPEC_PARENT_RUNTIME_AND_FROZEN_IDENTITIES_EXACT: 'Frozen identities',
  UNCHANGED_PRODUCTION_DEPENDENCIES_EXACT: 'Dependencies unchanged',
  VERDICT_MAPPING_OUTCOME_NEUTRAL: 'Outcome-neutral verdict',
  ZERO_BLENDER_PRODUCTION_PREFLIGHTS_ACCEPTED_AND_PUSHED: 'Zero-Blender preflights',
};

const sequenceNotes: Record<string, string> = {
  '1_ATTEMPT_FSYNCED': '先留下尝试，不让失败消失',
  '2_ADMISSION_FSYNCED': '准入决定独立持久化',
  '3_ATTEMPT_RECEIPT_FSYNCED': 'receipt 绑定 attempt + admission',
  '4_OUTPUT_FORMAL_START_FSYNCED': '到此才允许创建输出根',
  '5_IMMUTABLE_BUILD_PLAN': '自然语言不直接进入 Blender',
  '6_RESTRICTED_NATIVE_COMPILE': '受预算约束启动原生 Blender',
  '7_PRODUCTION_RECEIPT': '完整链路进入可验证收据',
};

function short(value: string) {
  return `${value.slice(0, 12)}…`;
}

export default function ProductionCompilerEntryPromotionPage() {
  return <main className="contact-page b55-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B56-E1 production compiler entry 导航">
        <Link href="/budgeted-native-child-pid-receipt-v0-1">B55 基础</Link>
        <a href="#entry">入口</a><a href="#preflight">准入</a><a href="#native-runs">编译</a><a href="#gates">门</a><a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">B56-E1 · Supported</span>
    </header>

    <section className="contact-hero b55-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> PREFERRED ENTRY · DURABLE AUTHORIZATION · REAL BLENDER 5.2</p>
        <h1>不是又一条脚本。<br/><span>是一个生产入口。</span></h1>
        <p>B56没有改动 SceneSpec、BuildPlan 或 Blender 编译语义。它把已经验证的低层组件包进唯一推荐入口：先检查工具、场景、输出与磁盘，再按可审计顺序留下 attempt、admission 和 receipt，最后才允许原生 Blender 创建 `.blend`。</p>
      </div>
      <aside className="contact-gate b55-gate">
        <b>FORMAL VERDICT</b>
        <strong>SUPPORTED</strong>
        <code>{Object.values(audit.gates).filter(Boolean).length} / {Object.keys(audit.gates).length} frozen gates</code>
        <code>{audit.attackSummary.rejected} / {audit.attackSummary.total} attacks rejected</code>
        <small>{result.experimentId} · evidence remains append-only</small>
      </aside>
      <div className="contact-stats">
        <article><strong>3</strong><span>preferred aliases</span><small>preflight · compile · verify</small></article>
        <article><strong>4/4</strong><span>native compiles</span><small>B01 / B02 · A/B fresh</small></article>
        <article><strong>27/27</strong><span>formal gates</span><small>independent audit</small></article>
        <article><strong>0</strong><span>render calls</span><small>0 network · model · Docker</small></article>
      </div>
    </section>

    <section className="section b55-causal-section" id="entry">
      <div className="section-index">00 / ONE PREFERRED RELEASE SURFACE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> RELEASE CONTRACT BEFORE CONVENIENCE</p><h2>用户看到三个命令。<br/><span>机器执行七步授权。</span></h2></div>
        <p>package.json 只增加三个命名入口；release manifest 冻结其背后的 29 个文件身份。低层 restricted compiler 仍保留作受控调试面，但不再是推荐生产调用。</p>
      </div>
      <div className="b55-causal b56-entry-flow">
        {aliases.map(([name, command], index) => <div key={name} style={{display:'contents'}}>
          {index > 0 && <i aria-hidden="true">→</i>}
          <article className={index === aliases.length - 1 ? 'supported' : index === 1 ? 'change' : ''}>
            <span>{String(index + 1).padStart(2, '0')} · NPM ALIAS</span>
            <strong>{name}</strong>
            <code>{command}</code>
            <p>{index === 0 ? '零 Blender、fail-closed 准入' : index === 1 ? '真实 Blender 净构建与生产 receipt' : '独立重开并验证完整证据链'}</p>
          </article>
        </div>)}
      </div>
      <div className="b55-diff">
        <article><span>LOW-LEVEL CONTROL</span><strong>restricted compiler</strong><code>保留 · 不是 preferred release entry</code></article>
        <div>
          {release.authorizationSequence.map((step, index) => <p key={step}><span>{String(index + 1).padStart(2, '0')}</span><b>{step.split('_').slice(1).join(' ')}</b><code>{sequenceNotes[step]}</code></p>)}
        </div>
        <article><span>PRODUCTION SURFACE</span><strong>{release.releaseId}</strong><code>{release.status} · activation condition satisfied by B56-E1</code></article>
      </div>
    </section>

    <section className="section b55-probe-section" id="preflight">
      <div className="section-index">01 / ZERO-BLENDER ADMISSION</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> REJECT BEFORE NATIVE WORK</p><h2>四条合法路径通过。<br/><span>九种危险输入关死。</span></h2></div>
        <p>正式预检运行 0 个 Blender 进程。四个 B01/B02 输出在 absent 状态被接受并推送；绝对路径、越界路径、符号链接、已有输出、磁盘不足、脏工具、脏场景、未推送 release 与输出换位全部 fail-closed。</p>
      </div>
      <div className="b55-probes">
        {negativeProbes.slice(0, 4).map((probe, index) => <article className="no-spawn" key={probe.id}>
          <span>{String(index + 1).padStart(2, '0')} · {probe.id}</span><strong>REJECTED</strong>
          <dl><div><dt>REASON</dt><dd>{probe.reason}</dd></div><div><dt>EXIT</dt><dd>{probe.child?.exitCode ?? 1}</dd></div><div><dt>EXACT</dt><dd>{probe.exact ? 'YES' : 'NO'}</dd></div></dl>
          <code>no Blender process</code>
        </article>)}
      </div>
      <div className="b55-probe-note"><span>ALL NEGATIVE CASES</span><strong>{negativeProbes.length} / {negativeProbes.length}</strong><p>{negativeProbes.slice(4).map(probe => probe.id).join(' · ')}</p></div>
      <div className="b55-identities">
        <article><span>AVAILABLE AT PREFLIGHT</span><strong>{Number(preflight.observations.disk.availableBytes).toLocaleString()} bytes</strong><code>host observation</code></article>
        <article><span>AFTER PROJECTED WRITE</span><strong>{Number(preflight.observations.disk.freeAfterProjectedBytes).toLocaleString()} bytes</strong><code>&gt; 100 GiB frozen reserve</code></article>
      </div>
    </section>

    <section className="section b55-runs" id="native-runs">
      <div className="section-index">02 / FOUR PREFERRED-ENTRY NATIVE COMPILES</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> SAME SCENE SEMANTICS · STRONGER OPERATIONAL CHAIN</p><h2>入口换成生产级。<br/><span>结构身份没有漂移。</span></h2></div>
        <p>四次都由 `compile:production` 启动，并由 `verify:production-receipt` 重开验证。每份 production receipt 有 10 项链路检查，内部现行 CompileReceipt 仍保持 19 项；wrapper PID 与 native Blender PID 分别记录。</p>
      </div>
      <div className="b54-run-table b55-run-table" role="table" aria-label="B56-E1 four preferred production Blender runs">
        <div className="head" role="row"><b>RUN</b><b>WRAPPER PID</b><b>BLENDER PID</b><b>PROD VERIFY</b><b>CURRENT</b><b>STRUCTURE</b></div>
        {result.runs.map(run => <div className="row" role="row" key={run.runId}>
          <strong>{run.runId}<small>{run.benchmarkId} fresh output</small></strong>
          <code>{run.wrapperPid}</code><b className="pid">{run.nativePid}</b>
          <b className="pass">{run.verification.checks.length} / 10</b><b className="pass">19 / 19</b>
          <code>{short(run.structureHash)}</code>
        </div>)}
      </div>
      <div className="b55-identities">
        {result.pairIdentity.map(pair => <article key={`${pair.id}-plan`}><span>{pair.id} BUILDPLAN</span><strong>{pair.planHash}</strong><code>A/B canonical bytes exact</code></article>)}
        {result.pairIdentity.map(pair => <article key={`${pair.id}-structure`}><span>{pair.id} STRUCTURE</span><strong>{pair.structureHash}</strong><code>A/B `.blend` semantic structure exact</code></article>)}
      </div>
    </section>

    <section className="section b55-gate-section" id="gates">
      <div className="section-index">03 / ALL 27 FROZEN GATES</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> NO POST-HOC THRESHOLD EDITS</p><h2>二十七项全绿。<br/><span>六十四种攻击全拒。</span></h2></div>
        <p>门覆盖 parent evidence、release manifest、package 最小差异、准入排序、四份生产 receipt、PID、BuildPlan、结构哈希、输出 roster 与独立审计。结论由冻结映射导出。</p>
      </div>
      <div className="b54-gates b55-gates">
        {Object.entries(audit.gates).map(([gate, passed], index) => <article className={passed ? 'pass' : 'fail'} key={gate}>
          <span>{String(index + 1).padStart(2, '0')}</span><i aria-hidden="true"/><strong>{passed ? 'PASS' : 'FAIL'}</strong><code>{gateLabels[gate] ?? gate}</code>
        </article>)}
      </div>
      <div className="b55-equation"><span>FORMAL RESULT</span><strong>27 PASS + 0 FAIL</strong><i>→</i><b>SUPPORTED</b><code>{audit.attackSummary.rejected} / {audit.attackSummary.total} semantic attacks rejected · audit imported no execution modules</code></div>
    </section>

    <section className="section b55-boundary" id="boundary">
      <div className="section-index">04 / THE ENTRY IS PROMOTED — THE FILM IS NOT</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> OPERATIONAL CONFIDENCE ≠ CINEMATIC QUALITY</p><h2>编译入口已经晋级。<br/><span>电影质量没有被顺便宣称。</span></h2></div>
        <p>B56证明“指定 SceneSpec 能经受控入口生成结构一致、可追溯的 Blender 文件”。它没有证明角色表演、资产美术、光影审美或最终像素已经达到影院级，也没有签名或远程证明。</p>
      </div>
      <div className="b55-boundary-grid">
        <article className="claim"><span>SUPPORTED CLAIM</span><strong>preferred entry promoted</strong><p>三个公开 alias 与七步 durable authorization 已通过真实 Blender 回归。</p></article>
        <article><span>STRUCTURAL EVIDENCE</span><strong>2 plans · 2 structures</strong><p>B01/B02 各自 A/B exact；四份 `.blend` 的内嵌绑定均通过。</p></article>
        <article className="limit"><span>NON-CLAIM</span><strong>cinematic pixels</strong><p>本实验没有 render；也不主张 container bytes deterministic、signed 或 remotely attested。</p></article>
        <article className="next"><span>NEXT GATE · NOW CLOSED</span><strong><Link href="/production-disk-jit-readmission-v0-1">B57 supported</Link></strong><p>native spawn 前已就地重观察磁盘，并把 sequence-5 决定交叉绑定进 production receipt。</p></article>
      </div>
      <div className="b55-nonclaims">
        {promotionSpec.nonClaims.map((claim, index) => <p key={claim}><span>{String(index + 1).padStart(2, '0')}</span>{claim}</p>)}
      </div>
      <div className="contact-artifacts b55-artifacts">
        <a href={`${repo}specs/production-compiler-entry.v0.1.json`}><span>RELEASE MANIFEST</span><b>{short(preflight.observations.toolFreeze.hashes['specs/production-compiler-entry.v0.1.json'])} ↗</b></a>
        <a href={`${repo}experiments/production-compiler-entry-promotion-preflight-v0-1/preflight.json`}><span>PREFLIGHT</span><b>{short(preflight.preflightHash)} ↗</b></a>
        <a href={`${repo}experiments/production-compiler-entry-promotion-v0-1/results.json`}><span>RESULTS</span><b>{short(result.resultHash)} ↗</b></a>
        <a href={`${repo}experiments/production-compiler-entry-promotion-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>{short(audit.auditHash)} ↗</b></a>
        <a href={`${repo}experiments/production-compiler-entry-promotion-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>{short(receipt.receiptHash)} ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B56-E1 Production Compiler Entry</b></div><p>3 aliases · 4 compiles · 27/27 gates · 64/64 attacks · 0 renders</p><Link href="/budgeted-native-child-pid-receipt-v0-1">查看 B55 基础证据 →</Link></footer>
  </main>;
}
