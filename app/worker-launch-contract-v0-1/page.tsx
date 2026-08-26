import type { Metadata } from 'next';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const contractRows = [
  ['ENVIRONMENT','11 exact keys','parent canary absent','ALLOWLIST ONLY'],
  ['ARGV','disable-autoexec · offline','python exit code 1','NO SHELL'],
  ['MOUNTS','/inputs · read-only','/outputs · writable','2 EXACT'],
  ['CANDIDATE','digest · pull never','non-root · bounded','NOT EXECUTED'],
];
const receipts = [
  ['SUCCEEDED','exit 0 · identities complete','PROMOTABLE'],
  ['FAILED','exit 7','QUARANTINE'],
  ['TIMED_OUT','SIGTERM → 5 s → SIGKILL policy','QUARANTINE'],
  ['CANCELLED','explicit cancellation','QUARANTINE'],
];
const attackGroups = [
  ['A01–A03','environment','inherit · missing · path escape'],
  ['A04–A10','process argv','shell · identity · autoexec · offline · Python fail'],
  ['A11–A15','image + mounts','digest · pull · RO/RW · Docker socket'],
  ['A16–A22','runtime policy','network · privilege · caps · user · rootfs · limits'],
  ['A23–A25','promotion','disk admission · timeout · self-hash'],
];

export const metadata: Metadata = {
  title: 'B38 Worker 启动合同｜Blender Film Studio',
  description: '三个 canonical request→plan 对、11-key 环境 allowlist、25/25 攻击与 fail-closed receipt；纯合同支持，不声称 container containment。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/worker-launch-contract-v0-1/' },
};

export default function WorkerLaunchContractPage() {
  return <main className="contact-page security-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B38 导航"><Link href="/journal">实验日志</Link><Link href="/worker-containment-v0-1">B37 隔离</Link><Link href="/autoexec-boundary-v0-1">Autoexec</Link><a href="#plan">计划</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">Launcher B38</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> PURE CONTRACT · NO CHILD PROCESS</p><h1>启动计划已经冻结。<br/><span>内核边界还没有。</span></h1><p>三个 WorkerRequest 在 key order 改变后仍得到相同 request hash 与 launch-plan hash。环境、argv、mount、资源与失败 promotion 都能 fail-closed；但 B38 没有运行 Blender 或 container。</p></div><aside className="contact-gate"><b>FORMAL VERDICT</b><strong>LOGIC<br/>SUPPORT</strong><code>3 / 3 canonical pairs</code><code>25 / 25 attacks rejected</code><small>NO BACKEND CLAIM</small></aside><div className="contact-stats"><article><strong>3 / 3</strong><span>Canonical plans</span><small>deep-reordered requests</small></article><article><strong>11</strong><span>环境 keys</span><small>parent canary absent</small></article><article><strong>25 / 25</strong><span>分析攻击</span><small>independent audit pass</small></article><article><strong>BLOCKED</strong><span>真实磁盘 admission</span><small>100 GiB reserve held</small></article></div></section>

    <section className="section contact-verdict" id="plan"><div className="section-index">00 / REQUEST → IMMUTABLE PLAN</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> BACKEND-AGNOSTIC COMPILER</p><h2>先冻结启动语义。<br/><span>再让 backend 接受攻击。</span></h2></div><p>B36 与 B37 已证明 autoexec、capability policy 和 environment policy 是不同的门。B38 把这些门写进 self-hashed plan，避免未来 Linux/macOS 实验靠改变参数获得通过。</p></div><div className="contact-flow"><article><span>01</span><b>REQUEST</b><p>data only · strict keys</p></article><i>→</i><article><span>02</span><b>COMPILER</b><p>canonical · no inheritance</p></article><i>→</i><article><span>03</span><b>PLAN</b><p>self hash · exact policy</p></article><i>→</i><article><span>04</span><b>BACKEND</b><p>B39 architecture gate</p></article></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">01 / FOUR INDEPENDENT GATES</div><div className="contact-heading"><div><p className="eyebrow"><span/> ENV ≠ ARGV ≠ MOUNTS ≠ KERNEL</p><h2>一组参数不是 sandbox。<br/><span>但缺一项就应当拒绝启动。</span></h2></div><p>候选 container policy 只是一份未来必须 enforce 的数据合同。digest-only image、network none 和 cgroup limits 尚未在 B38 runtime 中执行，页面不会把它们画成已经生效。</p></div><ol className="contact-negative-list">{contractRows.map(([domain,primary,secondary,status])=><li key={domain}><span>{domain}</span><b>{primary}</b><code>{secondary}</code><small>{status}</small></li>)}</ol></section>

    <section className="section contact-contract"><div className="section-index">02 / DISK ADMISSION IS PART OF CORRECTNESS</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> REAL HOST OBSERVATION</p><h2>空间不足不是警告。<br/><span>是启动前的拒绝结果。</span></h2></div><p>正式运行观察到 available 24.23 GB；扣除默认 projected 21.47 GB 后只余 2.76 GB，远低于 107.37 GB reserve。B38 因此记录 `BLOCKED`，没有 override，也没有创建 container。</p></div><div className="contact-boundary"><b>HOST ADMISSION</b><span>24,230,027,264 B available</span><span>21,474,836,480 B projected</span><span>2,755,190,784 B after</span><strong>BLOCKED · DISK_RESERVE</strong></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">03 / TERMINAL RECEIPTS</div><div className="contact-heading"><div><p className="eyebrow"><span/> PROMOTION IS A STATE MACHINE</p><h2>退出不等于完成。<br/><span>只有完整成功可以晋级。</span></h2></div><p>四种 synthetic receipt 都绑定同一 plan 并通过 self-hash。timeout 只冻结未来 backend 的 SIGTERM/grace/SIGKILL 记录要求；B38 没有真的发送 signal。</p></div><ol className="contact-negative-list">{receipts.map(([status,observed,decision])=><li key={status}><span>{status}</span><b>{observed}</b><small>{decision}</small></li>)}</ol></section>

    <section className="section contact-contract"><div className="section-index">04 / ADVERSARIAL ANALYZER</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> 25 FROZEN MUTATIONS</p><h2>每道门都被改坏一次。<br/><span>每次都必须留下拒绝原因。</span></h2></div><p>攻击在 baseline 通过后才运行，覆盖环境继承、危险 argv、Docker socket、root/privileged、缺资源上限、伪造 admission 与 timeout promotion。独立 audit 重算后的 attack JSON 与记录值 exact 相同。</p></div><ol className="contact-negative-list">{attackGroups.map(([id,domain,cases])=><li key={id}><span>{id}</span><b>{domain}</b><code>{cases}</code><small>ALL REJECTED</small></li>)}</ol></section>

    <section className="section contact-limits" id="boundary"><div className="section-index">05 / CONTRACT ≠ CONTAINMENT</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> B39 PREFLIGHT → B40 REAL BACKEND</p><h2>先过架构门。<br/><span>恢复磁盘后才运行 backend。</span></h2></div><p>B39-C1 已确认本机与 Colima 是 ARM64，而官方 Blender 5.2 Linux artifact 是 x64；因此后续只能把 amd64 emulation 当实验候选。digest-pinned image、只读输入、禁网、non-root、cap drop、cgroup breach、真实 Blender canary 与 timeout recovery 全部留给 B40。</p></div><div className="contact-artifacts"><a href={`${repo}specs/worker-launch-contract.v0.1.json`}><span>FROZEN SPEC</span><b>11 env · 25 attacks · non-claims ↗</b></a><a href={`${repo}experiments/worker-launch-contract-v0-1/results.json`}><span>RESULT</span><b>3/3 canonical · host blocked ↗</b></a><a href={`${repo}experiments/worker-launch-contract-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>25/25 exact replay · PASS ↗</b></a><a href={`${repo}research/2026-08-26-b38-worker-launch-contract-result.md`}><span>RESULT NOTE</span><b>measured facts · B39 boundary ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B38 Worker Launch Contract</b></div><p>logic support only · no child process · no backend claim</p><Link href="/linux-worker-preflight-v0-1">继续 B39 架构预检 →</Link></footer>
  </main>;
}
