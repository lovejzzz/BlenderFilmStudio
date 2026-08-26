import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'B39 Linux Worker 架构预检｜Blender Film Studio',
  description: '公开保留 B39 原始索引计数失败与 B39-C1 结构化纠错：ARM64 原生官方 artifact 缺失，x64 仅为模拟实验候选，runtime 因磁盘 gate 阻断。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/linux-worker-preflight-v0-1/' },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const probes = [
  ['HOST', 'macOS arm64', 'uname · exact'],
  ['VM', 'Colima aarch64', 'Apple Virtualization'],
  ['ENGINE', 'Docker aarch64', '29.5.2'],
  ['ARTIFACT', 'Linux x64 only', 'official 5.2.0 index'],
] as const;
const attacks = [
  ['PARSER', 'raw=1 恢复', 'REJECT'],
  ['ARTIFACT', 'ARM64 href 伪造', 'REJECT'],
  ['IDENTITY', 'size / SHA 篡改', 'REJECT'],
  ['PLATFORM', 'amd64 冒充 native', 'REJECT'],
  ['RUNTIME', 'below-reserve 强行放行', 'REJECT'],
] as const;

export default function LinuxWorkerPreflightPage() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B39 架构预检导航"><Link href="/journal">实验日志</Link><Link href="/worker-launch-contract-v0-1">B38 合同</Link><a href="#failure">失败</a><a href="#routes">路线</a><a href="#next">B40</a></nav><span className="edition contact-edition">Worker Preflight B39</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true"/><div className="contact-hero-copy"><p className="eyebrow"><span/> FAILURE RETAINED · CORRECTION PREREGISTERED</p><h1>官方 Linux 只有 x64。<br/><span>这台 Worker 是 ARM64。</span></h1><p>B39 先因错误的 HTML 原始计数假设被拒绝；B39-C1 只修正为 raw=2、exact href=1，并保留其余 gate。原生官方 ARM64 路线不成立，x64 只能进入后续模拟实验，而且当前磁盘禁止 runtime。</p></div><aside className="contact-gate"><b>FORMAL VERDICT</b><strong>CORRECTION<br/>SUPPORT</strong><code>B39 · REJECTED</code><code>B39-C1 · 15/15</code><small>RUNTIME STILL BLOCKED</small></aside><div className="contact-stats"><article><strong>2 → 1</strong><span>raw → exact href</span><small>structure-aware correction</small></article><article><strong>0</strong><span>官方 Linux ARM64</span><small>index · href · checksum</small></article><article><strong>15 / 15</strong><span>纠错攻击</span><small>independent audit PASS</small></article><article><strong>BLOCKED</strong><span>真实 runtime</span><small>DISK_RESERVE</small></article></div></section>

    <section className="section contact-diagnostic" id="failure"><div className="section-index">00 / REJECTED FIRST RUN</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> B39 · X64_INDEX_IDENTITY</p><h2>协议也可以错。<br/><span>错了就保留。</span></h2></div><p>首轮冻结“文件名在 raw HTML 中只出现一次”。真实响应是两次：一次 href target、一次 visible text。byte count 与官方 SHA 同时匹配，但组合 gate 仍按协议失败；accepted attacks 没有生成，独立 audit 也正确 FAIL。</p></div><div className="contact-flow"><article><span>01</span><b>PREREG</b><p>raw count = 1</p></article><i>→</i><article><span>02</span><b>OBSERVE</b><p>raw count = 2</p></article><i>→</i><article><span>03</span><b>REJECT</b><p>no route promotion</p></article><i>→</i><article><span>04</span><b>RETAIN</b><p>result + audit immutable</p></article></div></section>

    <section className="section contact-contract"><div className="section-index">01 / ONE-ASSUMPTION CORRECTION</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> B39-C1 · STRUCTURE AWARE</p><h2>只改一个错误。<br/><span>其余边界全部不动。</span></h2></div><p>纠错 spec 用 SHA 绑定失败结果，只把 raw=1 改为 raw=2 + exact quoted href=1。官方 filename、384,441,228 bytes、SHA-256、host identity、security metadata、disk gate、route class 与 zero-runtime 约束全部继承。</p></div><div className="contact-boundary"><b>CORRECTED</b><span>raw filename · 2</span><span>exact href · 1</span><span>checksum · 1</span><strong>15 / 15 ATTACKS</strong></div></section>

    <section className="section contact-verdict" id="routes"><div className="section-index">02 / HOST → ROUTE DECISION</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> ARCHITECTURE IS A GATE</p><h2>“能够模拟”不等于<br/><span>“原生、兼容、生产”。</span></h2></div><p>Blender Foundation 的冻结 5.2.0 release listing 提供 Linux x64 archive，没有 Linux ARM64 archive；本机 Colima 和现有 base images 都是 ARM64。Docker 支持 amd64 emulation 只产生一个待实验候选。</p></div><div className="contact-stats">{probes.map(([id,value,note])=><article key={id}><strong>{id}</strong><span>{value}</span><small>{note}</small></article>)}</div><div className="contact-flow"><article><span>A</span><b>linux/arm64</b><p>REJECTED · no official artifact</p></article><i>×</i><article><span>B</span><b>linux/amd64</b><p>IDENTIFIED · best effort</p></article><i>→</i><article><span>GATE</span><b>DISK</b><p>runtime blocked</p></article><i>→</i><article><span>B40</span><b>PENDING</b><p>separate preregistration</p></article></div></section>

    <section className="section contact-diagnostic"><div className="section-index light">03 / ADVERSARIAL REPLAY</div><div className="contact-heading"><div><p className="eyebrow"><span/> FRESH SELF-HASH PER MUTATION</p><h2>纠错不是放宽。<br/><span>新的假证据仍然进不来。</span></h2></div><p>每个 mutation 都重新生成 evidence self-hash，避免只靠 stale hash 拒绝。独立 audit 重新读取 spec、重算 base analysis，再逐项复现 15 个结果。</p></div><ol className="contact-negative-list">{attacks.map(([domain,mutation,result])=><li key={domain}><span>{domain}</span><b>{mutation}</b><small>{result}</small></li>)}</ol></section>

    <section className="section contact-limits" id="next"><div className="section-index">04 / NEXT · B40 REAL BACKEND</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> NOT YET EXECUTED</p><h2>下一次才下载、构建、运行。<br/><span>而且先要恢复 120 GiB 安全线。</span></h2></div><p>B40 必须另行预注册：digest-pinned linux/amd64 image、官方 archive byte verification、真实 Blender 5.2.0、x64 emulation、EGL/Eevee 或明确失败、B38 argv/env/mount、资源 breach、timeout recovery 与最小 compile/render receipt。B39-C1 对这些全部保持 unknown。</p></div><div className="contact-artifacts"><a href={`${repo}research/2026-08-26-b39-linux-worker-architecture-preflight-result.md`}><span>REJECTED B39</span><b>raw count assumption failed ↗</b></a><a href={`${repo}specs/linux-worker-architecture-preflight.v0.2.json`}><span>CORRECTION SPEC</span><b>one changed assumption ↗</b></a><a href={`${repo}experiments/linux-worker-architecture-preflight-v0-2/results.json`}><span>RESULT</span><b>routes · disk · 15 attacks ↗</b></a><a href={`${repo}experiments/linux-worker-architecture-preflight-v0-2/audit.json`}><span>INDEPENDENT AUDIT</span><b>exact replay · PASS ↗</b></a></div></section>

    <section className="section contact-contract"><div className="section-index">05 / PRIMARY SOURCES</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span/> OFFICIAL SOURCES ONLY</p><h2>Artifact identity 来自发布者。<br/><span>Emulation 风险来自 runtime 文档。</span></h2></div><p>索引与 checksum 在实验时重新获取，但没有下载 384 MB archive。Docker 对 Apple Silicon 上 Intel image 的说明被用作风险分类，不作为兼容性证明。</p></div><div className="contact-artifacts"><a href="https://download.blender.org/release/Blender5.2/"><span>BLENDER INDEX</span><b>5.2 official artifacts ↗</b></a><a href="https://download.blender.org/release/Blender5.2/blender-5.2.0.sha256"><span>BLENDER SHA-256</span><b>publisher manifest ↗</b></a><a href="https://www.blender.org/releases/5-2/"><span>BLENDER 5.2 LTS</span><b>release · supported to 2028 ↗</b></a><a href="https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/known-issues/"><span>DOCKER</span><b>Apple Silicon emulation limits ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B39 Linux Worker Preflight</b></div><p>failure retained · correction preregistered · runtime operations 0</p><Link href="/worker-launch-contract-v0-1">回看 B38 启动合同 →</Link></footer>
  </main>;
}
