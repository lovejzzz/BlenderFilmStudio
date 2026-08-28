import type { Metadata } from 'next';
import Link from 'next/link';
import spec from '../../specs/production-disk-jit-readmission.v0.1.json';
import release from '../../specs/production-compiler-entry.v0.2.json';
import preflight from '../../experiments/production-disk-jit-readmission-preflight-v0-1/preflight.json';
import result from '../../experiments/production-disk-jit-readmission-v0-1/results.json';
import audit from '../../experiments/production-disk-jit-readmission-v0-1/audit.json';
import receipt from '../../experiments/production-disk-jit-readmission-v0-1/receipt.json';
import lowDisk from '../../experiments/production-disk-jit-readmission-v0-1/low-disk/native-compile-disk-admission.json';
import boundedResult from '../../experiments/b57-formal-rehearsal-c2-v0-1/results.json';
import boundedAudit from '../../experiments/b57-formal-rehearsal-c2-v0-1/audit.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/production-disk-jit-readmission-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

export const metadata: Metadata = {
  title: 'B57-E1 Production Disk JIT Readmission｜Blender Film Studio',
  description: '在原生 Blender 启动前重新观察磁盘并把决定强绑定进 production receipt；26/26 gates、56/56 attacks 与四次真实净编译通过。',
  alternates: { canonical },
  openGraph: {
    title: 'B57-E1 · Check Disk at the Last Responsible Moment',
    description: '100 GiB reserve · one-byte-below rejection · 4 native compiles · 26/26 gates · 56/56 attacks.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'B57-E1 · Production Disk JIT Readmission Supported',
    description: 'A durably receipted disk decision immediately before native Blender spawn.',
    images: [],
  },
};

const escaped = boundedAudit.attacks.filter(attack => !attack.rejected);
const gateLabels: Record<string, string> = {
  B56_SUPPORTED_PARENT_BOUND_EXACT: 'B56 parent exact',
  V0_1_RELEASE_AND_BEFORE_IDENTITIES_EXACT: 'v0.1 evidence preserved',
  V0_2_RELEASE_AND_B57_TOOL_FREEZE_EXACT: 'v0.2 + tools frozen',
  PACKAGE_ALIASES_UNCHANGED_EXACT: 'Aliases unchanged',
  JIT_POLICY_EQUALS_PREFLIGHT_POLICY_EXACT: 'Disk policy unchanged',
  JIT_TEST_CEILING_CAN_ONLY_LOWER_REAL_OBSERVATION: 'Ceiling only lowers',
  OFFICIAL_PREFLIGHT_ZERO_BLENDER_ACCEPTED_AND_PUSHED: 'Pushed zero-Blender preflight',
  SCENESPEC_SUITE_22_OF_22: 'SceneSpec 22/22',
  B01_B02_BUILDPLAN_PAIR_BYTES_EXACT: 'BuildPlan pairs exact',
  STALE_CAPACITY_CASE_REJECTED_BEFORE_RESTRICTED_SPAWN: 'Stale capacity rejects pre-spawn',
  STALE_CAPACITY_REJECTION_EVIDENCE_DURABLE_AND_SELF_HASH_EXACT: 'Rejection durable + exact',
  FOUR_PREFERRED_PRODUCTION_ALIAS_COMPILES_PASS: '4 preferred compiles',
  FOUR_JIT_DISK_ADMISSIONS_ACCEPTED_BEFORE_WRAPPER_SPAWN: '4 JIT admissions precede spawn',
  FOUR_PRODUCTION_RECEIPTS_BIND_JIT_DISK_EVIDENCE: '4 receipts bind disk evidence',
  FOUR_PREFERRED_PRODUCTION_VERIFIERS_PASS: '4 preferred verifiers',
  FOUR_CURRENT_COMPILE_RECEIPTS_VERIFY_19_CHECKS: '4 × current 19 checks',
  FOUR_NATIVE_PID_RECEIPTS_EXACT: '4 native PID receipts',
  B01_B02_PLAN_HASHES_FROZEN: 'Plan hashes frozen',
  B01_B02_STRUCTURE_PAIR_BYTES_EXACT: 'Structure pairs exact',
  B01_B02_STRUCTURE_HASHES_FROZEN: 'Structure hashes frozen',
  FOUR_BLEND_EMBEDDED_BINDINGS_EXACT: '4 `.blend` bindings',
  NO_UNBOUND_OR_BACKUP_OUTPUT_FILES: 'Output rosters exact',
  DIRECT_PROCESS_AND_OPERATION_COUNTS_EXACT: 'Operation counts exact',
  MODEL_NETWORK_DOCKER_AND_RENDER_ZERO: 'Forbidden work zero',
  INDEPENDENT_AUDIT_AND_SEMANTIC_ATTACKS_MINIMUM_56: '56 attacks rejected',
  VERDICT_MAPPING_OUTCOME_NEUTRAL: 'Outcome-neutral verdict',
};

function short(value: string) {
  return `${value.slice(0, 12)}…`;
}

function bytes(value: string | number) {
  return Number(value).toLocaleString('en-US');
}

export default function ProductionDiskJitReadmissionPage() {
  return <main className="contact-page b55-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B57-E1 production disk readmission 导航">
        <Link href="/production-compiler-entry-promotion-v0-1">B56 入口</Link>
        <a href="#window">时间窗</a><a href="#negative">负例</a><a href="#correction">纠错</a><a href="#runs">编译</a><a href="#gates">门</a><a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">B57-E1 · Supported</span>
    </header>

    <section className="contact-hero b55-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> LAST-RESPONSIBLE-MOMENT CHECK · DURABLE DISK RECEIPT · REAL BLENDER 5.2</p>
        <h1>预检通过之后，<br/><span>磁盘还会变化。</span></h1>
        <p>B56 已把编译器变成正式入口，但磁盘检查发生在预检；如果调用被搁置，旧容量仍可能授权新的 Blender。B57 把同一条 100 GiB 安全线移到 native spawn 前最后一刻，并把真实观察、有效观察、策略与决定写进不可抵赖的 production receipt。</p>
      </div>
      <aside className="contact-gate b55-gate">
        <b>FORMAL VERDICT</b>
        <strong>SUPPORTED</strong>
        <code>{audit.gatePassed} / {audit.gateTotal} frozen gates</code>
        <code>{audit.attackSummary.rejected} / {audit.attackSummary.total} attacks rejected</code>
        <small>{result.experimentId} · official ID closed</small>
      </aside>
      <div className="contact-stats">
        <article><strong>1 byte</strong><span>negative margin</span><small>zero restricted/native spawn</small></article>
        <article><strong>4/4</strong><span>native compiles</span><small>B01 / B02 · A/B fresh</small></article>
        <article><strong>26/26</strong><span>formal gates</span><small>independent replay</small></article>
        <article><strong>0</strong><span>render calls</span><small>0 model · network · Docker</small></article>
      </div>
    </section>

    <section className="section b55-causal-section" id="window">
      <div className="section-index">00 / CLOSE THE CHECK–USE WINDOW</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PREFLIGHT IS NECESSARY — NOT FRESH FOREVER</p><h2>计划落盘以后。<br/><span>进程启动以前。</span></h2></div>
        <p>干预只增加 sequence-5。SceneSpec、immutable BuildPlan、restricted compiler 与 Blender 场景语义不变；test ceiling 只能降低真实观察，所以它可以制造拒绝，不能伪造通过。</p>
      </div>
      <div className="b55-causal">
        <article><span>EARLIER · PREFLIGHT</span><strong>ACCEPTED</strong><code>{bytes(preflight.disk.availableBytes)} bytes</code><p>冻结工具、输入、输出与当时磁盘状态。</p></article>
        <i aria-hidden="true">→</i>
        <article className="change"><span>DURABLE · BUILDPLAN</span><strong>IMMUTABLE</strong><code>canonical plan persisted first</code><p>自然语言不能在检查后改变编译内容。</p></article>
        <i aria-hidden="true">→</i>
        <article className="change"><span>SEQUENCE 5 · STATFS</span><strong>RE-OBSERVE</strong><code>reserve + projected write</code><p>对 repository root 就地重新观察并 fsync 决定。</p></article>
        <i aria-hidden="true">→</i>
        <article className="supported"><span>ONLY IF ACCEPTED</span><strong>SPAWN</strong><code>restricted wrapper → native Blender</code><p>production receipt 反向绑定真实 disk record。</p></article>
      </div>
      <div className="b55-identities">
        <article><span>MINIMUM RESERVE</span><strong>{bytes(release.diskAdmission.minimumReserveBytes)} bytes</strong><code>100 GiB · no release override</code></article>
        <article><span>PROJECTED WRITE</span><strong>{bytes(release.diskAdmission.projectedWriteBytes)} bytes</strong><code>0.5 GiB · subtracted before accept</code></article>
        <article><span>OFFICIAL PREFLIGHT AFTER WRITE</span><strong>{bytes(preflight.disk.freeAfterProjectedBytes)} bytes</strong><code>status {preflight.disk.status}</code></article>
        <article><span>RECEIPT CONTRACT</span><strong>bfs.productionCompileReceipt.v0.2</strong><code>disk file + self-hash + semantic projection</code></article>
      </div>
    </section>

    <section className="section b55-probe-section" id="negative">
      <div className="section-index">01 / ONE BYTE BELOW MEANS ZERO BLENDER</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> ACCEPTED PREFLIGHT · STALE CAPACITY · FAIL CLOSED</p><h2>不是“差不多够”。<br/><span>差一字节也不启动。</span></h2></div>
        <p>正式负例先持有合法、已推送的 production preflight，再把 JIT effective available 降到冻结阈值下 1 byte。输出只允许留下授权、BuildPlan、拒绝记录与 invalidation。</p>
      </div>
      <div className="b55-probes">
        <article><span>REAL OBSERVATION</span><strong>{bytes(lowDisk.filesystemAvailableBytesObserved)}</strong><dl><div><dt>TARGET</dt><dd>repository root</dd></div><div><dt>CEILING</dt><dd>LOWER ONLY</dd></div></dl><code>statfs immediately before spawn</code></article>
        <article><span>EFFECTIVE AVAILABLE</span><strong>{bytes(lowDisk.effectiveAvailableBytes)}</strong><dl><div><dt>TEST</dt><dd>APPLIED</dd></div><div><dt>SEQUENCE</dt><dd>{lowDisk.sequence}</dd></div></dl><code>{short(lowDisk.diskAdmissionHash)}</code></article>
        <article className="no-spawn"><span>AFTER PROJECTED WRITE</span><strong>{bytes(lowDisk.disk.freeAfterProjectedBytes)}</strong><dl><div><dt>RESERVE</dt><dd>{bytes(lowDisk.disk.reserveBytes)}</dd></div><div><dt>MARGIN</dt><dd>−1 byte</dd></div></dl><code>{lowDisk.reason}</code></article>
        <article className="no-spawn"><span>PROCESS CONSEQUENCE</span><strong>0 + 0</strong><dl><div><dt>WRAPPER</dt><dd>{lowDisk.restrictedCompilerProcessesStarted}</dd></div><div><dt>BLENDER</dt><dd>{lowDisk.nativeBlenderProcessesStarted}</dd></div></dl><code>durable rejection · no retry in same root</code></article>
      </div>
    </section>

    <section className="section b55-boundary" id="correction">
      <div className="section-index">02 / THE FAILED REHEARSAL STAYS VISIBLE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> C2 FOUND A REAL VERIFIER GAP</p><h2>文件哈希正确。<br/><span>receipt 仍能撒谎。</span></h2></div>
        <p>C2 的四次 Blender 编译与真实 disk files 都正确，但 verifier 没有把 receipt 内的 `diskAdmissionHash` 再与实际 disk record 比较。攻击者可修改 receipt 投影并重封装自身哈希；四个 DISK_HASH attacks 因此逃逸。</p>
      </div>
      <div className="b55-boundary-grid">
        <article className="limit"><span>C2 REHEARSAL</span><strong>{Object.values(boundedResult.gates).filter(Boolean).length} / {Object.keys(boundedResult.gates).length}</strong><p>{boundedResult.scientificVerdict}</p></article>
        <article><span>ATTACKS</span><strong>{boundedAudit.attackSummary.rejected} / {boundedAudit.attackSummary.total}</strong><p>{escaped.map(attack => attack.id).join(' · ')}</p></article>
        <article className="next"><span>MINIMAL CORRECTION</span><strong>external bind</strong><p>receipt disk hash、sequence、status、bytes、ceiling 与 policy 必须逐字段等于实际 disk record。</p></article>
        <article className="claim"><span>OFFICIAL</span><strong>{audit.attackSummary.rejected} / {audit.attackSummary.total}</strong><p>四个 DISK_HASH 反例与其余重封装攻击全部拒绝。</p></article>
      </div>
    </section>

    <section className="section b55-runs" id="runs">
      <div className="section-index">03 / FOUR RECEIPT-BOUND NATIVE COMPILES</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> JIT ACCEPTED BEFORE EACH WRAPPER</p><h2>四次重新观察。<br/><span>四份真实 `.blend`。</span></h2></div>
        <p>每个 fresh run 都独立写 sequence-5 disk admission，随后才出现 wrapper PID 与 native Blender PID。Preferred verifier 为 11/11，内部 current CompileReceipt 仍为 19/19；B01/B02 A/B 结构保持精确。</p>
      </div>
      <div className="b54-run-table b55-run-table" role="table" aria-label="B57-E1 four disk-readmitted production Blender runs">
        <div className="head" role="row"><b>RUN</b><b>WRAPPER PID</b><b>BLENDER PID</b><b>PROD VERIFY</b><b>CURRENT</b><b>DISK / STRUCTURE</b></div>
        {audit.runInspections.map(run => <div className="row" role="row" key={run.runId}>
          <strong>{run.runId}<small>{run.benchmarkId} fresh output</small></strong>
          <code>{run.wrapperPid}</code><b className="pid">{run.nativePid}</b>
          <b className="pass">11 / 11</b><b className="pass">19 / 19</b>
          <code>{short(run.diskAdmissionHash)}<br/>{short(run.structureHash)}</code>
        </div>)}
      </div>
      <div className="b55-identities">
        {preflight.plans.map(plan => <article key={`${plan.id}-plan`}><span>{plan.id} BUILDPLAN</span><strong>{plan.planHash}</strong><code>A/B canonical bytes exact</code></article>)}
        {[audit.runInspections[0], audit.runInspections[2]].map(run => <article key={`${run.benchmarkId}-structure`}><span>{run.benchmarkId} STRUCTURE</span><strong>{run.structureHash}</strong><code>A/B `.blend` semantic structure exact</code></article>)}
      </div>
    </section>

    <section className="section b55-gate-section" id="gates">
      <div className="section-index">04 / ALL 26 FROZEN GATES</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> NO POST-HOC POLICY WEAKENING</p><h2>二十六项全绿。<br/><span>五十六种攻击全拒。</span></h2></div>
        <p>门覆盖 parent identity、release freeze、one-byte fail-closed、四次 JIT ordering、production receipt 交叉绑定、native PID、BuildPlan、结构、roster、零禁用工作与独立 verdict mapping。</p>
      </div>
      <div className="b54-gates b55-gates">
        {Object.entries(audit.gates).map(([gate, passed], index) => <article className={passed ? 'pass' : 'fail'} key={gate}>
          <span>{String(index + 1).padStart(2, '0')}</span><i aria-hidden="true"/><strong>{passed ? 'PASS' : 'FAIL'}</strong><code>{gateLabels[gate] ?? gate}</code>
        </article>)}
      </div>
      <div className="b55-equation"><span>FORMAL RESULT</span><strong>26 PASS + 0 FAIL</strong><i>→</i><b>SUPPORTED</b><code>{audit.attackSummary.rejected} / {audit.attackSummary.total} semantic attacks rejected · independent auditor imported no execution modules</code></div>
    </section>

    <section className="section b55-boundary" id="boundary">
      <div className="section-index">05 / A NARROWER WINDOW — NOT RESERVED SPACE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> PRODUCTION SAFETY ≠ CRASH RECOVERY ≠ CINEMATIC QUALITY</p><h2>磁盘旧证据已经关死。<br/><span>流水线恢复仍未解决。</span></h2></div>
        <p>B57 证明检查在正确位置发生并被 receipt 绑定。它不锁定 filesystem blocks，也不排除观察后到写入间的外部并发写入；更没有证明 Codex 崩溃后可幂等续跑，或最终像素达到电影质量。</p>
      </div>
      <div className="b55-boundary-grid">
        <article className="claim"><span>SUPPORTED CLAIM</span><strong>JIT readmission</strong><p>旧 preflight 容量不能直接授权新 native process。</p></article>
        <article><span>DURABLE EVIDENCE</span><strong>disk → receipt</strong><p>实际记录与 receipt 投影逐字段、逐哈希交叉绑定。</p></article>
        <article className="limit"><span>NON-CLAIM</span><strong>reserved blocks</strong><p>没有预留 filesystem blocks，也没有远程签名或 attestation。</p></article>
        <article className="next"><span>NEXT GOAL GATE</span><strong>restart-safe job</strong><p>durable job manifest、阶段 checkpoint、幂等恢复与受控进程中断。</p></article>
      </div>
      <div className="b55-nonclaims">
        {spec.nonClaims.map((claim, index) => <p key={claim}><span>{String(index + 1).padStart(2, '0')}</span>{claim}</p>)}
      </div>
      <div className="contact-artifacts b55-artifacts">
        <a href={`${repo}specs/production-disk-jit-readmission.v0.1.json`}><span>PREREGISTERED SPEC</span><b>{short(result.specSha256)} ↗</b></a>
        <a href={`${repo}experiments/production-disk-jit-readmission-preflight-v0-1/preflight.json`}><span>OFFICIAL PREFLIGHT</span><b>{short(preflight.preflightHash)} ↗</b></a>
        <a href={`${repo}experiments/production-disk-jit-readmission-v0-1/results.json`}><span>RESULTS</span><b>{short(result.resultHash)} ↗</b></a>
        <a href={`${repo}experiments/production-disk-jit-readmission-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>{short(audit.auditHash)} ↗</b></a>
        <a href={`${repo}experiments/production-disk-jit-readmission-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>{short(receipt.receiptHash)} ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B57-E1 Production Disk JIT Readmission</b></div><p>1-byte rejection · 4 compiles · 26/26 gates · 56/56 attacks · 0 renders</p><Link href="/production-compiler-entry-promotion-v0-1">查看 B56 生产入口 →</Link></footer>
  </main>;
}
