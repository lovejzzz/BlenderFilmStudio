import type { Metadata } from 'next';
import Link from 'next/link';
import spec from '../../specs/formal-runner-admission-path-totality.v0.1.json';
import audit from '../../experiments/formal-runner-admission-path-totality-v0-1/audit.json';
import result from '../../experiments/formal-runner-admission-path-totality-v0-1/results.json';
import receipt from '../../experiments/formal-runner-admission-path-totality-v0-1/receipt.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/formal-runner-admission-totality-v0-1/';

export const metadata: Metadata = {
  title: 'B53-E1 Formal Runner Admission Totality｜Blender Film Studio',
  description: '17 个隔离 Git cases、14/14 gates、34/34 semantic attacks：relative、dot-segment 与 absolute path 归一为同一 evidence identity，拒绝路径在任何 formal work 前留下可审计 receipt。',
  alternates: { canonical },
  openGraph: {
    title: 'B53-E1 · Formal Admission Is Now Total',
    description: '17/17 cases · 14/14 gates · 34/34 attacks · 0 Blender · 0 renders.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'B53-E1 · 3 Path Shapes, 1 Evidence Identity',
    description: 'A falsifiable execution-infrastructure result for one-shot Blender experiments.',
    images: [],
  },
};

type CaseAudit = {
  caseId: string;
  observed: { outcome: string; reason: string | null };
  evidenceIdentity?: { identityHash: string } | null;
  outputIdentity?: { parentRepositoryRelative: string; repositoryRelative: string; fresh: boolean } | null;
  outputFingerprint: { kind: string };
  bindingExact: boolean;
  replayExact: boolean;
  outputUnchanged: boolean;
};

const caseAudits = audit.caseAudits as CaseAudit[];
const positives = caseAudits.filter(row => row.observed.outcome === 'ACCEPT');
const negatives = caseAudits.filter(row => row.observed.outcome === 'REJECT');
const identityHash = positives[0]?.evidenceIdentity?.identityHash ?? 'missing';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

const pathShapes = [
  { id: 'P01_RELATIVE', label: 'RELATIVE', input: 'fixture/evidence', output: 'formal-relative' },
  { id: 'P02_DOT_SEGMENTS', label: 'DOT SEGMENTS', input: 'fixture/./scratch/../evidence', output: 'formal-dot' },
  { id: 'P03_ABSOLUTE', label: 'ABSOLUTE', input: '/private/…/fixture/evidence', output: 'formal-absolute' },
] as const;

const failureChain = [
  ['B42', 'MOUNTPOINT', '0 worker launch', '嵌套可写mountpoint缺失；null observation也未被analyzer总处理。'],
  ['D12.14-H1', 'SCHEMA', '4 renders · invalid', 'Producer-only preflight没有消费analyzer真实输入形状。'],
  ['D12.14-H2', 'PATH SHAPE', '15/15 preflight · 0 formal', 'Relative CLI path在runner try/finally之前触发absolute基准错误。'],
  ['B53-E1', 'TOTAL ADMISSION', '17 cases · supported', '把路径、Git freshness与failure receipt变成独立可审计仪器。'],
] as const;

const gateLabels: Record<string, string> = {
  SPEC_AND_TOOL_IDENTITIES: 'Frozen identities',
  THREE_POSITIVES_ACCEPT: '3 positives accept',
  POSITIVE_EVIDENCE_CANONICAL_IDENTITY_EXACT: 'Evidence identity exact',
  POSITIVE_OUTPUT_PARENT_IDENTITY_EXACT: 'Output parent exact',
  FOURTEEN_NEGATIVES_REJECT_WITH_EXACT_REASON: '14 reasons exact',
  EVERY_CASE_WRITES_ONE_RECEIPT: 'Receipt totality',
  EVERY_REJECTION_WRITES_SELF_HASHED_FAILURE: 'Failure self-hash',
  NO_CASE_CREATES_DECLARED_FORMAL_OUTPUT: 'No output creation',
  NO_SYMLINK_OR_OUTSIDE_WRITE: 'No escape write',
  LOCAL_BARE_ORIGIN_ONLY: 'Local origin only',
  PROCESS_ROSTER_EXACT: 'Process roster exact',
  MODEL_NETWORK_BLENDER_RENDER_ZERO: 'Forbidden work zero',
  AUDIT_REPLAY_EXACT: 'Independent replay',
  SEMANTIC_ATTACKS_MINIMUM_32: '34 attacks rejected',
};

export default function FormalRunnerAdmissionTotalityPage() {
  return <main className="contact-page b53-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B53-E1 admission totality 导航">
        <Link href="/blender-projective-depth-formal-invalidation-v0-1">H2 失效</Link>
        <a href="#instrument">仪器</a><a href="#equivalence">等价性</a><a href="#rejects">拒绝矩阵</a><a href="#audit">审计</a><a href="#boundary">边界</a>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">B53-E1 · Supported</span>
    </header>

    <section className="contact-hero b53-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> EXECUTION INFRASTRUCTURE · SINGLE-USE FORMAL RUN · ZERO BLENDER</p>
        <h1>三种路径写法。<br/><span>同一个证据身份。</span></h1>
        <p>我们没有重跑H2，也没有用absolute path绕过旧故障。B53-E1把“实验如何获准开始”隔离成新的可证伪对象：路径必须归一、证据必须已推送、output必须fresh，而每一次拒绝都必须在formal work之前留下自哈希failure与receipt。</p>
      </div>
      <aside className="contact-gate b53-gate">
        <b>FORMAL VERDICT</b>
        <strong>SUPPORTED</strong>
        <code>{audit.gatePassed} / {audit.gateTotal} frozen gates</code>
        <code>{audit.semanticAttacksPassed} / {audit.semanticAttackCount} attacks rejected</code>
        <small>{result.experimentId} · same ID closed</small>
      </aside>
      <div className="contact-stats">
        <article><strong>{result.cases.length}</strong><span>isolated cases</span><small>3 accept · 14 reject</small></article>
        <article><strong>{audit.gatePassed}/{audit.gateTotal}</strong><span>formal gates</span><small>independent replay exact</small></article>
        <article><strong>{result.operationCounts.gitChildProcesses}</strong><span>Git children</span><small>{result.operationCounts.runnerGitChildProcesses} runner · {result.operationCounts.auditorGitChildProcesses} audit</small></article>
        <article><strong>0</strong><span>Blender / render</span><small>0 network · 0 model · 0 Docker</small></article>
      </div>
    </section>

    <section className="section b53-instrument" id="instrument">
      <div className="section-index">00 / WHY ADMISSION BECAME AN INSTRUMENT</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> FAILURE CHAIN → FROZEN INTERVENTION</p><h2>三个失败没有被抹掉。<br/><span>它们定义了第四个实验。</span></h2></div>
        <p>B42、H1与H2分别暴露mountpoint、consumer schema和formal CLI path边界。B53-E1不声称修复这些旧实验；它只验证一个新admission module能否在任何昂贵工作前，把这些基础条件变成total、可记录、可攻击的合同。</p>
      </div>
      <div className="b53-failure-chain">
        {failureChain.map(([id, fault, observation, note], index) => <div className="b53-chain-node" key={id}>
          <article className={id === 'B53-E1' ? 'supported' : 'preserved'}><span>{String(index + 1).padStart(2, '0')} · {id}</span><strong>{fault}</strong><code>{observation}</code><p>{note}</p></article>
          {index < failureChain.length - 1 ? <i aria-hidden="true">→</i> : null}
        </div>)}
      </div>
    </section>

    <section className="section b53-equivalence" id="equivalence">
      <div className="section-index">01 / POSITIVE PATH EQUIVALENCE</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> CALLER SPELLING IS NOT EVIDENCE IDENTITY</p><h2>输入表达可以不同。<br/><span>可信身份不能漂移。</span></h2></div>
        <p>每种输入都在独立clone里消费同一已推送evidence。Admission返回canonical repository-relative identity与fresh output target，但不创建target。Auditor重新实现全部逻辑，得到相同结果。</p>
      </div>
      <div className="b53-path-machine">
        <div className="b53-path-inputs">
          {pathShapes.map(shape => {
            const observed = caseAudits.find(row => row.caseId === shape.id);
            return <article key={shape.id}><span>{shape.label}</span><strong>{shape.input}</strong><code>{observed?.observed.outcome} · output {observed?.outputFingerprint.kind}</code></article>;
          })}
        </div>
        <div className="b53-resolver"><span>RESOLVE + REALPATH</span><i>↓</i><strong>TRACKED · CLEAN · PUSHED</strong><i>↓</i><span>SELF-HASH + TOOL BINDINGS</span></div>
        <div className="b53-identity"><span>CANONICAL EVIDENCE IDENTITY</span><strong>{identityHash}</strong><code>repository-relative · no caller spelling · no host prefix</code></div>
      </div>
      <div className="b53-positive-grid">
        {positives.map(row => <article key={row.caseId}><span>{row.caseId}</span><strong>{row.outputIdentity?.repositoryRelative}</strong><code>parent · {row.outputIdentity?.parentRepositoryRelative}</code><p>fresh {String(row.outputIdentity?.fresh)} · target {row.outputFingerprint.kind.toLowerCase()} · replay {row.replayExact ? 'exact' : 'mismatch'}</p></article>)}
      </div>
    </section>

    <section className="section b53-rejects" id="rejects">
      <div className="section-index">02 / NEGATIVE EARLIEST-REASON MATRIX</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> REJECT BEFORE FORMAL WORK</p><h2>不是只会成功。<br/><span>还要精确地失败。</span></h2></div>
        <p>14个negative cases各冻结一个earliest reason。任何后续错误都不能遮住更早的安全边界；每个case仍须产生attempt、failure和receipt，且scientific verdict保持null。</p>
      </div>
      <div className="b53-reject-table" role="table" aria-label="14 个 formal admission rejection cases">
        <div className="b53-reject-head" role="row"><span>CASE</span><span>BOUNDARY</span><span>OBSERVED REASON</span><span>RECEIPT</span></div>
        {negatives.map((row, index) => <div className="b53-reject-row" role="row" key={row.caseId}>
          <span>{String(index + 1).padStart(2, '0')}</span><strong>{row.caseId.replace(/^N\d+_/, '').replaceAll('_', ' ')}</strong><code>{row.observed.reason}</code><b>{row.bindingExact && row.outputUnchanged ? 'BOUND' : 'FAIL'}</b>
        </div>)}
      </div>
      <div className="b53-ledger">
        <article><span>01 · BEFORE ADMISSION</span><strong>attempt.json</strong><p>caller spelling、expected reason、origin ref与null verdict先落盘。</p></article><i>→</i>
        <article><span>02 · EXACT REJECTION</span><strong>failure.json</strong><p>self-hashed reason；formalWorkStarted=false。</p></article><i>→</i>
        <article><span>03 · FILE BINDING</span><strong>receipt.json</strong><p>绑定attempt与failure bytes；17/17 case totality。</p></article><i>⊘</i>
        <article className="zero"><span>04 · NEVER CREATED</span><strong>formal output</strong><p>所有before/after fingerprints exact。</p></article>
      </div>
    </section>

    <section className="section b53-audit" id="audit">
      <div className="section-index">03 / INDEPENDENT AUDIT</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> DO NOT IMPORT THE INSTRUMENT UNDER TEST</p><h2>Auditor重新写了一遍。<br/><span>然后攻击了34次。</span></h2></div>
        <p>独立auditor不import admission library或runner。它重开本地bare origin与17个clones，复算canonical hashes、Git ancestry、path containment、process roster，并对case records做34项单字段篡改。</p>
      </div>
      <div className="b53-gates">
        {Object.entries(audit.gates).map(([gate, passed], index) => <article key={gate}><span>{String(index + 1).padStart(2, '0')}</span><i aria-hidden="true" /><strong>{passed ? 'PASS' : 'FAIL'}</strong><code>{gateLabels[gate] ?? gate}</code></article>)}
      </div>
      <div className="b53-process-plot">
        <article><span>RUNNER</span><strong>{result.operationCounts.runnerGitChildProcesses}</strong><div><i style={{width: `${result.operationCounts.runnerGitChildProcesses / result.operationCounts.gitChildProcesses * 100}%`}} /></div><code>Git children · roster exact</code></article>
        <article><span>INDEPENDENT AUDITOR</span><strong>{result.operationCounts.auditorGitChildProcesses}</strong><div><i style={{width: `${result.operationCounts.auditorGitChildProcesses / result.operationCounts.gitChildProcesses * 100}%`}} /></div><code>Git children · parent PID bound</code></article>
        <article className="attacks"><span>SEMANTIC ATTACKS</span><strong>{audit.semanticAttacksPassed}/{audit.semanticAttackCount}</strong><div><i /></div><code>17 receipt · 14 failure · 3 admission</code></article>
        <article className="zero"><span>FORBIDDEN OPERATIONS</span><strong>0</strong><div><i /></div><code>Blender · render · network · model · Docker</code></article>
      </div>
    </section>

    <section className="section b53-boundary" id="boundary">
      <div className="section-index">04 / CLAIM AND PROMOTION BOUNDARY</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> SUPPORTED ≠ UNIVERSAL SAFETY</p><h2>一扇基础设施门被证明。<br/><span>不是整部电影被证明。</span></h2></div>
        <p>本结果只授权未来新实验预登记采用admission module。它不修复H2，不证明任意文件系统、远端Git或Blender正确性，也不自动改变production compiler orchestration。</p>
      </div>
      <div className="b53-boundary-grid">
        <article className="claim"><span>SUPPORTED CLAIM</span><strong>path + evidence admission totality</strong><p>在冻结的17-case local-Git fixture内，等价路径归一且拒绝路径均留下receipt。</p></article>
        <article><span>NON-CLAIM</span><strong>H2 hypothesis</strong><p>Projective-depth material-owner实验仍是null verdict，不因本结果被追溯修复。</p></article>
        <article><span>NON-CLAIM</span><strong>arbitrary hosts</strong><p>Local bare origin只模拟pushed ancestry，不是remote attestation或任意filesystem证明。</p></article>
        <article className="next"><span>OBSERVED INTEGRATION GATE</span><strong>B54-E1 · 17/18</strong><p>四次native compile与B01/B02结构哈希全部复现；current budget report缺native PID，因此formal verdict为REJECTED。</p><Link href="/admission-gated-native-compiler-v0-1">打开完整integration证据 →</Link></article>
      </div>
      <div className="b53-nonclaims">
        {spec.nonClaims.map((claim, index) => <p key={claim}><span>{String(index + 1).padStart(2, '0')}</span>{claim}</p>)}
      </div>
      <div className="contact-artifacts b53-artifacts">
        <a href={`${repo}specs/formal-runner-admission-path-totality.v0.1.json`}><span>FROZEN SPEC</span><b>{receipt.spec.sha256.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/formal-runner-admission-path-totality-v0-1/results.json`}><span>RESULTS</span><b>{result.resultHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/formal-runner-admission-path-totality-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>{audit.auditHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/formal-runner-admission-path-totality-v0-1/receipt.json`}><span>FORMAL RECEIPT</span><b>{receipt.receiptHash.slice(0, 16)}… ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B53-E1 Formal Runner Admission Totality</b></div><p>17 cases · 14/14 gates · 34/34 attacks · 0 Blender renders</p><Link href="/compiler-v0-1">返回核心编译器 →</Link></footer>
  </main>;
}
