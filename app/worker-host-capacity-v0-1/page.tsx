import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'B40 Worker Host 容量准入｜Blender Film Studio',
  description: '四项容量 blocker、五次公开工具失败、14/14 攻击与 JSON replay 稳定审计；当前 Colima host 不允许进入真实 Blender worker。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/worker-host-capacity-v0-1/' },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const failures = [
  ['B40', 'flags: parser', 'INVALID'],
  ['C1', 'object alias', 'AUDIT FAIL'],
  ['C2', 'failure projection', '0 / 14'],
  ['C3', 'identity source', 'NO RESULT'],
  ['C4', 'field outside hash', 'AUDIT FAIL'],
  ['C5', 'full replay', 'PASS'],
] as const;
const blockers = [
  ['HOST DISK', '19.67 GB', '120 GiB admission'],
  ['VM MEMORY', '6.20 GB', '10 GiB required'],
  ['VM CPU', '4', '5 required'],
  ['DOCKER FREE', '4.64 GB', '8 GiB required'],
] as const;

export default function WorkerHostCapacityPage() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B40 容量准入导航"><Link href="/journal">实验日志</Link><Link href="/linux-worker-preflight-v0-1">B39 架构</Link><a href="#failures">失败链</a><a href="#capacity">容量</a><a href="#next">B41</a></nav><span className="edition contact-edition">Host Admission B40</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> READ-ONLY CAPACITY ADMISSION · NO RUNTIME</p><h1>模拟器已经存在。<br/><span>运行资格还不存在。</span></h1><p>qemu-x86_64、零 swap、零竞争容器通过；宿主磁盘、VM memory、VM CPU 与 Docker build storage 四道门同时阻断。五次工具失败被逐次保留，第六次才得到可序列化、可独立重放的正式判决。</p></div><aside className="contact-gate"><b>FORMAL VERDICT</b><strong>HOST<br/>BLOCKED</strong><code>4 exact blockers</code><code>14 / 14 attacks</code><small>REPLAY + AUDIT PASS</small></aside><div className="contact-stats"><article><strong>4</strong><span>容量 blocker</span><small>exact ordered reasons</small></article><article><strong>5 → 1</strong><span>拒绝 → 接受</span><small>failures retained</small></article><article><strong>14 / 14</strong><span>攻击原因</span><small>JSON replay stable</small></article><article><strong>0</strong><span>runtime operations</span><small>no Blender · no container</small></article></div></section>

    <section className="section contact-diagnostic" id="failures"><div className="section-index">00 / THE TOOL WAS PART OF THE EXPERIMENT</div><div className="contact-heading"><div><p className="eyebrow"><span/> FAILURE CHAIN</p><h2>不是修到绿灯就结束。<br/><span>每个错误都改变证据合同。</span></h2></div><p>parser 忽略冒号、内存对象别名、wrapper 丢失具体 failure code、错误的 identity source、结果字段逃逸 self-hash——它们都可能制造“runner PASS”。只有持久化文件被独立重放后，C5 才被接受。</p></div><ol className="contact-negative-list">{failures.map(([id,defect,result])=><li key={id}><span>{id}</span><b>{defect}</b><small>{result}</small></li>)}</ol></section>

    <section className="section contact-verdict" id="capacity"><div className="section-index">01 / FOUR BLOCKERS</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> CEILING IS NOT A RESERVATION</p><h2>容器写了 8 GiB limit，<br/><span>不代表 VM 真有 8 GiB。</span></h2></div><p>B38 的 memory/CPU 是 ceiling。B40 另加 2 GiB 与 1 CPU infrastructure reserve，并为受信 image build 冻结 8 GiB Docker-free floor。这些是 BFS 运维准入政策，不冒充 Blender 官方最低配置。</p></div><div className="contact-stats">{blockers.map(([id,observed,required])=><article key={id}><strong>{id}</strong><span>{observed}</span><small>{required}</small></article>)}</div></section>

    <section className="section contact-contract"><div className="section-index">02 / PASSING GATES</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> ARCHITECTURE PATH EXISTS</p><h2>QEMU 已注册。<br/><span>兼容性依然 unknown。</span></h2></div><p>VM 记录 `qemu-x86_64` enabled、interpreter `/usr/bin/qemu-x86_64`、flags `POCF`；swap 为 0，running containers 为 0。这里只证明 emulator registration 和干净竞争状态，不证明 Blender、Eevee、EGL 或性能。</p></div><div className="contact-boundary"><b>ACCEPTED</b><span>swap · 0</span><span>running containers · 0</span><span>qemu · POCF</span><strong>NOT A COMPATIBILITY CLAIM</strong></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">03 / PERSISTENCE IS A GATE</div><div className="contact-heading"><div><p className="eyebrow"><span/> MEMORY → JSON → AUDIT</p><h2>同一个对象，<br/><span>落盘后可能不是同一份证据。</span></h2></div><p>C1 暴露了 structuredClone 会保留 alias、JSON 不会；C4 暴露了结果字段可能逃出 self-hash。C5 要求 base analysis、decision、hash、14 个 ordered failure vectors 在 JSON round-trip 与独立进程中完全相同。</p></div><div className="contact-flow"><article><span>01</span><b>OBSERVE</b><p>read-only probes</p></article><i>→</i><article><span>02</span><b>VALUE COPY</b><p>no cross-tree alias</p></article><i>→</i><article><span>03</span><b>SELF HASH</b><p>all decision fields</p></article><i>→</i><article><span>04</span><b>REPLAY</b><p>14/14 exact audit</p></article></div></section>

    <section className="section contact-limits" id="next"><div className="section-index">04 / EXTERNAL CHANGE REQUIRED</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> NEXT · CLEAN ADMISSION → B41</p><h2>先恢复容量。<br/><span>然后才有资格运行 Blender。</span></h2></div><p>至少需要：宿主清理约 102 GiB 以上；Colima 提升到 ≥10 GiB memory、≥5 CPU；Docker build storage ≥8 GiB free。Colima 变更需要 restart，可能影响其他 workload，因此 B40 没有自动执行。外部状态改变后还要新跑 clean admission，再单独预注册 B41。</p></div><div className="contact-artifacts"><a href={`${repo}research/2026-08-26-b40-c5-worker-host-capacity-result.md`}><span>ACCEPTED RESULT NOTE</span><b>four blockers · next conditions ↗</b></a><a href={`${repo}experiments/worker-host-capacity-admission-v0-6/results.json`}><span>MACHINE RESULT</span><b>self-hash · 14 attacks ↗</b></a><a href={`${repo}experiments/worker-host-capacity-admission-v0-6/audit.json`}><span>INDEPENDENT AUDIT</span><b>replay stable · PASS ↗</b></a><a href={`${repo}research/2026-08-26-b40-c1-aliasing-audit-failure.md`}><span>FAILURE EXAMPLE</span><b>memory alias ≠ JSON ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B40 Worker Host Capacity</b></div><p>four blockers · 14/14 · replay stable · runtime operations 0</p><Link href="/linux-worker-preflight-v0-1">回看 B39 架构预检 →</Link></footer>
  </main>;
}
