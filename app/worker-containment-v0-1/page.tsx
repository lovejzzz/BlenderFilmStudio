import type { Metadata } from 'next';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const rows = [
  ['UNSANDBOXED × 2','ALLOW','ALLOW','ALLOW','VISIBLE'],
  ['SBPL INHERITED × 2','BLOCK','BLOCK','BLOCK','VISIBLE'],
  ['SBPL SANITIZED × 2','BLOCK','BLOCK','BLOCK','ABSENT'],
];

export const metadata: Metadata = {
  title: 'B37 Worker 能力隔离｜Blender Film Studio',
  description: '六个真实 Blender 5.2 进程：deprecated SBPL 阻断 16/16 受控能力，但 inherited environment 仍泄露假 secret；9/9 攻击通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/worker-containment-v0-1/' },
};

export default function WorkerContainmentPage() {
  return <main className="contact-page security-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B37 导航"><Link href="/journal">实验日志</Link><Link href="/autoexec-boundary-v0-1">Autoexec</Link><Link href="/resource-budget-v0-1">Watchdog</Link><a href="#matrix">矩阵</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">Security B37</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> REAL BLENDER · OS CAPABILITY CANARY</p><h1>四类能力被挡住。<br/><span>一个假 secret 穿过去了。</span></h1><p>deprecated SBPL 在四个 Blender worker 中阻断 sibling 文件读写、loopback 与 child exec；但 parent 已放进环境的字符串仍然 2/2 可见。只有 launcher 主动清理，才降到 0/2。</p></div><aside className="contact-gate"><b>FORMAL VERDICT</b><strong>PARTIAL<br/>SUPPORT</strong><code>16 / 16 capabilities blocked</code><code>2 / 2 inherited env visible</code><small>NOT A PRODUCTION SANDBOX</small></aside><div className="contact-stats"><article><strong>6</strong><span>真实 Blender PID</span><small>all unique · exit 0</small></article><article><strong>16 / 16</strong><span>SBPL capability deny</span><small>PermissionError</small></article><article><strong>2 / 2</strong><span>环境继承反例</span><small>fake secret visible</small></article><article><strong>9 / 9</strong><span>分析攻击</span><small>independent audit pass</small></article></div></section>

    <section className="section contact-verdict" id="matrix"><div className="section-index">00 / 同一 canary，三种 launcher</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> CAPABILITY POLICY × ENVIRONMENT POLICY</p><h2>Kernel 能拒绝动作。<br/><span>不能撤回已经继承的数据。</span></h2></div><p>baseline 先证明全部 canary 原本可达；再只切换 SBPL 与 fake-secret sanitization。network 始终只连接一次性 `127.0.0.1` server，“outside” 仍位于 ignored run root 内。</p></div><div className="contact-flow"><article><span>01</span><b>PARENT</b><p>env · paths · nonce</p></article><i>→</i><article><span>02</span><b>LAUNCHER</b><p>sanitize before exec</p></article><i>→</i><article><span>03</span><b>SBPL</b><p>deny capabilities</p></article><i>→</i><article><span>04</span><b>BLENDER</b><p>trusted probe · report</p></article></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">01 / 冻结矩阵</div><div className="contact-heading"><div><p className="eyebrow"><span/> SIX UNIQUE PIDS</p><h2>文件、网络、子进程被挡。<br/><span>Worker 内写入仍保留。</span></h2></div><p>UNSANDBOXED 两次共有 12/12 capability success。四个 SBPL 进程中，sibling read/write、loopback、`/usr/bin/touch` 共 16/16 block；六个 worker report 都能写出。</p></div><ol className="contact-negative-list">{rows.map(([cell,files,network,child,secret])=><li key={cell}><span>{cell}</span><b>FILES · {files}</b><code>NET · {network} / CHILD · {child}</code><small>ENV · {secret}</small></li>)}</ol></section>

    <section className="section contact-contract"><div className="section-index">02 / 反例不是实现瑕疵</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> INHERITED ENVIRONMENT</p><h2>Sandbox policy 生效。<br/><span>假 secret 仍在进程里。</span></h2></div><p>SBPL_INHERITED 的两次都看到固定非秘密 canary；SBPL_SANITIZED 的两次都看不到。结论不是“SBPL 没用”，而是 capability isolation 与 environment allowlist 是两道独立的门。</p></div><div className="contact-boundary"><b>COUNTEREXAMPLE</b><span>SBPL inherited · 2/2 visible</span><span>SBPL sanitized · 0/2 visible</span><span>no real secret used</span><strong>SANITIZE BEFORE EXEC</strong></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">03 / 独立 receipt 与攻击</div><div className="contact-heading"><div><p className="eyebrow"><span/> SERVER-SIDE BINDING</p><h2>不能只信 Blender 自己说“网络失败”。<br/><span>Server 也必须没有 nonce。</span></h2></div><p>loopback server 只收到两个 UNSANDBOXED nonce，四个 sandboxed cells 均无 receipt。九个 frozen attacks 还注入 capability 假成功、secret 状态错、duplicate PID 与 sandbox receipt，全部被拒。</p></div><ol className="contact-negative-list">{['outside read fabricated success','outside write fabricated success','loopback fabricated success','child exec fabricated success','missing worker write','missing inherited-env counterexample','secret visible after sanitization','duplicate Blender PID','sandboxed nonce receipt'].map((item,index)=><li key={item}><span>A{String(index+1).padStart(2,'0')}</span><b>{item}</b><small>REJECTED</small></li>)}</ol></section>

    <section className="section contact-limits" id="boundary"><div className="section-index">04 / CURRENT HOST PROTOTYPE ≠ BACKEND</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> SANDBOX-EXEC IS DEPRECATED</p><h2>当前机器上能拦，<br/><span>不等于产品可以依赖。</span></h2></div><p>系统 man page 已标 deprecated，profile 还是 `allow default`，Blender 也没有 App Sandbox entitlement。没有验证 parser memory safety、GPU、DoS、全部 IPC/syscalls 或真实 secret。下一步应该选择 disposable VM/container，或构建并签名独立 App Sandbox worker host。</p></div><div className="contact-artifacts"><a href={`${repo}specs/worker-containment-spec.v0.1.json`}><span>FROZEN SPEC</span><b>matrix · gates · non-claims ↗</b></a><a href={`${repo}experiments/worker-containment-v0-1/results.json`}><span>RESULT</span><b>6 PID · 16/16 · counterexample ↗</b></a><a href={`${repo}experiments/worker-containment-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>9/9 attacks · PASS ↗</b></a><a href={`${repo}research/2026-08-26-b37-worker-containment-result.md`}><span>RESULT NOTE</span><b>measured limits · next backend ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B37 Worker Containment Canary</b></div><p>deprecated prototype support · inherited env counterexample</p><Link href="/research-agenda">继续选择 supported worker backend →</Link></footer>
  </main>;
}
