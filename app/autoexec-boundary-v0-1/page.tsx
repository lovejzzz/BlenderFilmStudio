import type { Metadata } from 'next';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const cells = [
  ['ENABLE_A','87507','MARKER · YES','autoexec_fail · false'],
  ['ENABLE_B','87509','MARKER · YES','autoexec_fail · false'],
  ['DISABLE_A','87511','MARKER · NO','autoexec_fail · true'],
  ['DISABLE_B','87513','MARKER · NO','autoexec_fail · true'],
  ['DEFAULT_A','87514','MARKER · NO','autoexec_fail · true'],
  ['DEFAULT_B','87517','MARKER · NO','autoexec_fail · true'],
];

export const metadata: Metadata = {
  title: 'B36 Blender Autoexec 边界｜Blender Film Studio',
  description: '六个真实 Blender 5.2 进程验证 registered Text 的 enable/disable 边界；首次 analyzer 错误被保留，7/7 攻击与独立复核通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/autoexec-boundary-v0-1/' },
};

export default function AutoexecBoundaryPage() {
  return <main className="contact-page security-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B36 导航"><Link href="/journal">实验日志</Link><Link href="/security-v0-1">路径安全</Link><Link href="/asset-security-v0-1">资产净化</Link><a href="#result">结果</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">Security B36</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> REAL BLENDER · REGISTERED TEXT</p><h1>一个 flag 挡住了自动脚本。<br/><span>没有挡住解析器。</span></h1><p>同一份受控 `.blend` 在 ENABLE 时先于 trusted probe 写出 marker；在 `--disable-autoexec` 与 factory default 时没有执行 registered Text，但显式指定的审计脚本仍能运行。它是必要的 fail-closed control，不是 sandbox。</p></div><aside className="contact-gate"><b>FORMAL VERDICT</b><strong>BOUNDARY<br/>SUPPORT</strong><code>registered Text only</code><code>OS containment · OPEN</code><small>first invalid run retained</small></aside><div className="contact-stats"><article><strong>6</strong><span>真实 Blender PID</span><small>all unique</small></article><article><strong>2 / 2</strong><span>ENABLE marker</span><small>executed before probe</small></article><article><strong>4 / 4</strong><span>blocked marker</span><small>disable + default</small></article><article><strong>7 / 7</strong><span>分析攻击</span><small>independent audit pass</small></article></div></section>

    <section className="section contact-verdict" id="result"><div className="section-index">00 / 受控因果边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> SAME BLEND · ONE CLI VARIABLE</p><h2>允许自动执行，<br/><span>Python side effect 发生。</span></h2></div><p>canary 只读取一个固定非秘密 token，并且只写 ignored B36 work 内的 JSON。没有外网、真实 secret、子进程或工作区外写入。ENABLE 与 DISABLE 使用相同 source、factory startup 和 trusted probe。</p></div><div className="contact-flow"><article><span>01</span><b>REGISTERED TEXT</b><p>`Text.use_module = true`</p></article><i>→</i><article><span>02</span><b>ENABLE</b><p>marker 2 / 2</p></article><i>⇄</i><article><span>03</span><b>DISABLE</b><p>marker 0 / 2</p></article><i>→</i><article><span>04</span><b>TRUSTED PROBE</b><p>6 / 6 still runs</p></article></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">01 / 六个新进程，不复用首次无效输出</div><div className="contact-heading"><div><p className="eyebrow"><span/> PROCESS EVIDENCE</p><h2>默认关闭与显式关闭一致。<br/><span>但必须显式写进 worker。</span></h2></div><p>factory startup 的两次默认 cell 也没有 marker；四个 blocked cells 的 `bpy.app.autoexec_fail` 都为 true。生产 worker 仍应显式传 `--disable-autoexec`，不能依赖某位用户机器上的偏好状态。</p></div><ol className="contact-negative-list">{cells.map(([id,pid,marker,state])=><li key={id}><span>{id}</span><b>PID {pid}</b><code>{marker}</code><small>{state}</small></li>)}</ol></section>

    <section className="section contact-contract"><div className="section-index">02 / 失败没有被结果覆盖</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> ATTEMPT 1 · INVALID</p><h2>行为模式对了，<br/><span>身份比较仍然让运行判废。</span></h2></div><p>首次 analyzer 把 API 返回的 `5.2.0 LTS` 错写成 `5.2.0`，所以在七个 attacks 前停止。该六进程 artifact 原样提交；修复只改回 spec 已冻结的完整字符串，然后从新目录重跑全部 cell。</p></div><div className="contact-boundary"><b>RETAINED</b><span>6 first-run PIDs</span><span>all side effects</span><span>zero attacks executed</span><strong>NO RETROACTIVE PASS</strong></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">03 / 反例必须能让 analyzer 失败</div><div className="contact-heading"><div><p className="eyebrow"><span/> SEVEN FROZEN ATTACKS</p><h2>不是看见 2 / 2 就结束。<br/><span>还要证明判定器会拒绝伪证据。</span></h2></div><p>DISABLE 假 marker 直接得到 `AUTOEXEC_DISABLE_INSUFFICIENT`；其他攻击分别破坏默认阻断、ENABLE 执行、token、PID 唯一性与 source identity。独立 audit 重新读取 ignored source 并复算同一组门。</p></div><ol className="contact-negative-list">{['DISABLE marker injection','FACTORY_DEFAULT marker injection','missing ENABLE marker','wrong non-secret token','marker / probe PID mismatch','duplicate Blender PID','source .blend SHA mutation'].map((item,index)=><li key={item}><span>A{String(index+1).padStart(2,'0')}</span><b>{item}</b><small>REJECTED</small></li>)}</ol></section>

    <section className="section contact-limits" id="boundary"><div className="section-index">04 / AUTOEXEC CONTROL ≠ SANDBOX</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> THE PARSER STILL RUNS</p><h2>脚本没自动执行，<br/><span>文件仍然被 Blender 解析。</span></h2></div><p>B36 不隔离解析器漏洞、内存、文件、网络、子进程、GPU、系统调用、真实 secrets、Freestyle、add-ons 或 MCP 权限。下一实验必须是实际 OS worker containment；如果本机没有可审计 kernel boundary，就应转向 disposable VM，而不是把 B12 watchdog 写成 sandbox。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/autoexec-boundary-v0-1/attempt-1-invalid.json`}><span>INVALID ATTEMPT</span><b>first-run evidence retained ↗</b></a><a href={`${repo}experiments/autoexec-boundary-v0-1/results.json`}><span>FORMAL RESULT</span><b>6 PID · 7/7 attacks ↗</b></a><a href={`${repo}experiments/autoexec-boundary-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>source exact · PASS ↗</b></a><a href={`${repo}research/2026-08-26-b36-autoexec-boundary-result.md`}><span>RESULT NOTE</span><b>facts · non-claims · next ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B36 Autoexec Boundary</b></div><p>registered Text blocked · parser sandbox still open</p><Link href="/worker-containment-v0-1">继续 B37 worker capability canary →</Link></footer>
  </main>;
}
