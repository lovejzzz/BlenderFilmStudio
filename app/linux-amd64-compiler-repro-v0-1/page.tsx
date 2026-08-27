import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'B42 Blender 5.2 Worker 编译复现｜Blender Film Studio',
  description: '真实 Blender 5.2 Linux/amd64 worker：B01/B02 四次净构建结构复现、篡改拒绝、失败保留与独立审计。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/linux-amd64-compiler-repro-v0-1/' },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const runs = [
  ['B01-A', '9,685 ms', 'c699fc27…b7f0b', 'PASS'],
  ['B01-B', '9,678 ms', 'c699fc27…b7f0b', 'PASS'],
  ['B02-A', '9,776 ms', '025c6fa5…fa856', 'PASS'],
  ['B02-B', '9,361 ms', '025c6fa5…fa856', 'PASS'],
] as const;

export default function LinuxAmd64CompilerReproPage() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B42 编译复现导航"><Link href="/journal">实验日志</Link><Link href="/worker-host-capacity-v0-1">Worker 容量</Link><a href="#result">复现结果</a><a href="#failure">失败链</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">Compiler Worker B42-C1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> REAL BLENDER 5.2 · LINUX/AMD64 · FIVE CONTAINERS</p><h1>第三道门，<br/><span>已经由真实 Blender 关闭。</span></h1><p>同一份 SceneSpec 独立生成 immutable BuildPlan，再交给受限 Blender worker 编译。B01 与 B02 各做两次空目录净构建，canonical scene structure 完全一致；第五次篡改计划被拒绝。</p></div><aside className="contact-gate"><b>FORMAL VERDICT</b><strong>COMPILE<br/>REPRO</strong><code>4 / 4 clean builds</code><code>1 / 1 tamper rejected</code><small>INDEPENDENT AUDIT PASS</small></aside><div className="contact-stats"><article><strong>5.2 LTS</strong><span>Linux/amd64 Blender</span><small>fbe6228777e7</small></article><article><strong>4 / 4</strong><span>净构建完成</span><small>9.36–9.78 s</small></article><article><strong>2 / 2</strong><span>结构哈希复现</span><small>B01 · B02</small></article><article><strong>0</strong><span>残留容器</span><small>network none</small></article></div></section>

    <section className="section contact-diagnostic" id="result"><div className="section-index">00 / SCENESPEC → BUILDPLAN → BLENDER</div><div className="contact-heading"><div><p className="eyebrow"><span/> SEMANTIC REPRODUCIBILITY</p><h2>我们复现的是场景语义，<br/><span>不是 `.blend` 文件字节。</span></h2></div><p>四个 worker 都重新读取经过哈希验证的 SceneSpec、资产、OCIO 与编译器。每个 manifest 绑定预期 planHash 和 structureHash；同一 benchmark 的 canonical structure 文件逐字节相等。</p></div><div className="contact-flow"><article><span>01</span><b>SCENESPEC</b><p>data · schema · asset IDs</p></article><i>→</i><article><span>02</span><b>BUILDPLAN</b><p>canonical · self hash</p></article><i>→</i><article><span>03</span><b>BLENDER 5.2</b><p>read-only · no network</p></article><i>→</i><article><span>04</span><b>STRUCTURE</b><p>manifest · canonical hash</p></article></div><ol className="contact-negative-list">{runs.map(([id,time,hash,status])=><li key={id}><span>{id}</span><b>{time}</b><code>{hash}</code><small>{status}</small></li>)}</ol></section>

    <section className="section contact-verdict" id="failure"><div className="section-index">01 / FAILURE RETAINED</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> B42 REJECTED → B42-C1 PASS</p><h2>第一次五个容器，<br/><span>一个 Blender 都没启动。</span></h2></div><p>只读 `/repo` 内缺少嵌套输出挂载点，OCI 全部 exit 125；分析器随后又因 null observation 崩溃。失败计划、日志与 failure.json 全部保留。C1 预注册后只加入空挂载点与 failure-total analysis，再完整重跑，未修改任何验收门。</p></div><div className="contact-boundary"><b>CORRECTION ONLY</b><span>mountpoint exists</span><span>null is a failed gate</span><span>new evidence directory</span><strong>NO RETROACTIVE PASS</strong></div></section>

    <section className="section contact-contract"><div className="section-index">02 / INTEGRITY ATTACK</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> ZEROED PLAN HASH</p><h2>内容没变，声明被篡改。<br/><span>编译器必须停止。</span></h2></div><p>第五个容器只把 B01 顶层 planHash 改成 64 个零。Blender 进程 exit 1，日志包含 `BuildPlan hash mismatch`，没有写出 scene、manifest 或 structure。这证明 immutable plan 不只是文档约定，而是执行门。</p></div><div className="diagnostic-verdict"><b>NEGATIVE CONTROL</b><code>EXIT 1 · DIAGNOSTIC MATCH · OUTPUT FILES 0</code><p>独立 audit 重新读取工具、计划与四组输出：tools MATCH、outputs MATCH、plans MATCH。</p></div></section>

    <section className="section contact-limits" id="boundary"><div className="section-index">03 / WHAT REMAINS OPEN</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> COMPILE GATE ≠ FILM QUALITY</p><h2>机器能稳定造场景。<br/><span>还不等于机器会拍电影。</span></h2></div><p>当前镜像已确认可做编译与 Cycles CPU；Eevee 在这台无 GPU worker 上仍停在 render start。下一阶段需要扩大 SceneSpec 覆盖、加入镜头级审片与资产质量门，并为 Eevee 选择 GPU worker 或单独构建软件 Vulkan 路线。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/linux-amd64-compiler-repro-c1-v0-1/results.json`}><span>MACHINE RESULT</span><b>4 builds · tamper control ↗</b></a><a href={`${repo}experiments/linux-amd64-compiler-repro-c1-v0-1/audit.json`}><span>INDEPENDENT AUDIT</span><b>tools · outputs · plans MATCH ↗</b></a><a href={`${repo}research/2026-08-26-b42-c1-linux-amd64-compiler-repro-result.md`}><span>RESULT NOTE</span><b>claims · non-claims ↗</b></a><a href={`${repo}research/2026-08-26-b42-nested-mountpoint-failure.md`}><span>FAILED B42</span><b>OCI 125 · analyzer defect ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B42-C1 Compiler Worker</b></div><p>four clean builds · two structure hashes · one rejected tamper</p><Link href="/journal">回到实验日志 →</Link></footer>
  </main>;
}
