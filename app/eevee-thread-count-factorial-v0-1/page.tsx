import type { Metadata } from 'next';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
export const metadata: Metadata = {
  title: 'B22 Eevee 线程数因果实验｜Blender Film Studio',
  description: '真实 Blender 72 进程 EXR32 实验：固定 1 线程与 8 线程都未恢复严格复现，19/19 攻击通过。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/eevee-thread-count-factorial-v0-1/' },
};

const pairs = [
  ['T01 · A/B', '5/12', '172', '0.005615234375'],
  ['T01 · A/C', '5/12', '146', '0.00537109375'],
  ['T01 · B/C', '9/12', '46', '0.005615234375'],
  ['T08 · A/B', '7/12', '116', '0.00634765625'],
  ['T08 · A/C', '7/12', '133', '0.005615234375'],
  ['T08 · B/C', '8/12', '97', '0.00634765625'],
];
const attacks = [
  'B22 spec','B21 result','control inventory','ReviewRenderSpec','Blender binary','OCIO config','source .blend','configurator','renderer','comparator','source threads','requested mode','requested count','render samples','fixed render controls','render count','EXR layout','missing / mutated EXR','comparison binding',
];

export default function ThreadCountFactorialPage() {
  return <main className="contact-page factorial-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B22 导航"><Link href="/journal">实验日志</Link><Link href="/dual-output-localization-v0-1">B21</Link><a href="#cells">线程 cell</a><a href="#pairs">配对</a><a href="#failure">失败假设</a><a href="#next">下一边界</a></nav><span className="edition contact-edition">Thread Factorial 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B22 · 72 FRESH BLENDER PROCESSES</p><h1>只用一个渲染线程。<br /><span>Float 漂移仍然存在。</span></h1><p>12 个预选哨兵、T01 与 T08 两个 cell、每组 A/B/C 三重复。每个观察都启动真实 Blender 5.2 新进程，render 一次，并保存一张 scene-linear ACEScg RGBA32 EXR。</p></div><aside className="contact-gate"><b>PRE-REGISTERED DECISION</b><strong>THREAD COUNT<br />NOT SUFFICIENT</strong><code>T01 · 19 / 36 exact</code><code>T08 · 22 / 36 exact</code><small>19 / 19 ATTACKS PASS</small></aside><div className="contact-stats"><article><strong>72/72</strong><span>唯一 PID</span><small>fresh process</small></article><article><strong>72</strong><span>render calls</span><small>one per observation</small></article><article><strong>72</strong><span>float EXR</span><small>RGBA32 · ZIP</small></article><article><strong>19/19</strong><span>负向攻击</span><small>stable reasons</small></article></div></section>

    <section className="section contact-verdict" id="cells"><div className="section-index">00 / 线程干预</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FIXED 1 × FIXED 8 · ZERO TOLERANCE</p><h2>CPU-facing 开关已改变。<br /><span>严格复现没有回来。</span></h2></div><p>每个 cell 有 36 个解码浮点配对；只有 36/36、最大误差 0、failed pixels 0 才算 exact。两组均失败，因此不能把 `scene.render.threads` 当作充分原因。</p></div><div className="factorial-matrix"><article className="factorial-nonexact"><span>T01 · FIXED/1</span><strong>19/36</strong><b>364 failed pixels</b><small>max 0.005615234375</small></article><article className="factorial-nonexact"><span>T08 · FIXED/8</span><strong>22/36</strong><b>346 failed pixels</b><small>max 0.00634765625</small></article><article className="factorial-exact"><span>PROCESS IDENTITY</span><strong>72/72</strong><b>all PIDs unique</b><small>interleaved frozen order</small></article><article className="factorial-exact"><span>CONTROL ATTACKS</span><strong>19/19</strong><b>expected reason reached</b><small>no post-hoc tolerance</small></article></div><div className="diagnostic-verdict"><b>DECISION</b><code>THREAD_COUNT_NOT_SUFFICIENT</code><p>19 与 22 只是描述性计数。本实验没有预注册概率或效应量比较，不能宣称“1 线程更差”或“8 线程更好”。</p></div></section>

    <section className="section contact-evidence" id="pairs"><div className="section-index light">01 / 六条独立配对</div><div className="contact-heading"><div><p className="eyebrow"><span /> A/B · A/C · B/C</p><h2>不是一个偶然坏 pair。<br /><span>两个 cell 全部分裂。</span></h2></div><p>每一行包含 12 个哨兵的精确比较。T01 与 T08 的三条 replicate pair 都出现非精确帧；最大差异仍在此前 B21 观察到的 float 量级。</p></div><ol className="contact-negative-list">{pairs.map(([id,exact,failed,max], index) => <li key={id}><span>{String(index + 1).padStart(2,'0')}</span><b>{id}</b><code>{exact} exact</code><small>{failed} px · max {max}</small></li>)}</ol></section>

    <section className="section contact-limits" id="failure"><div className="section-index">02 / 被真实机器否证的实现假设</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> CANDIDATE 780e470 · REJECTED</p><h2>源文件没有 dither 0。<br /><span>B21 只在内存里改过。</span></h2></div><p>第一候选在第一个 Blender 进程就停止：源 `.blend` 报告 dither 1.0。接受候选随后显式固定 dither 0、Fast GI on、reprojection on，并记录所有前后值；预注册规则没有修改。</p></div><div className="contact-nonclaim"><b>WHY IT MATTERS</b><p>实验状态必须由当前进程的可审计配置建立，不能从上一实验的结果反推源文件已改变。负结果因此被保留为新的工作流约束。</p></div></section>

    <section className="section contact-diagnostic"><div className="section-index">03 / 对抗验证</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> NINETEEN FROZEN REASONS</p><h2>线程值变了，<br /><span>证据链也必须没断。</span></h2></div><p>攻击覆盖上游结果、运行时与工具哈希，源/请求线程状态，固定采样控制，单 render 约束，EXR 布局、文件字节与 comparison-manifest 绑定。</p></div><ol className="contact-negative-list">{attacks.map((item,index) => <li key={item}><span>N{String(index + 1).padStart(2,'0')}</span><b>{item}</b><small>PASS</small></li>)}</ol></section>

    <section className="section contact-limits" id="next"><div className="section-index">04 / 下一可证伪边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> PROCESS INIT × RENDER INVOCATION</p><h2>线程开关不足。<br /><span>下一步分离初始化与每次 render。</span></h2></div><p>同一哨兵在一个已初始化 Blender 进程中重复 render，和每次新进程相比较。若进程内 exact、跨进程 non-exact，支持初始化边界；若进程内也漂移，则继续逼近每次 render / GPU 工作。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/eevee-thread-count-factorial-v0-1/results.json`}><span>RESULT</span><b>72 PIDs · 19 attacks ↗</b></a><a href={`${repo}experiments/eevee-thread-count-factorial-v0-1/evidence/process-ledger.json`}><span>LEDGER</span><b>render process identity ↗</b></a><a href={`${repo}research/2026-08-26-b22-eevee-thread-count-factorial-result.md`}><span>RESULT NOTE</span><b>failed candidate included ↗</b></a><a href={`${repo}research/2026-08-26-b22-eevee-thread-count-factorial-protocol.md`}><span>PROTOCOL</span><b>pre-execution freeze ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B22 Thread-count Factorial</b></div><p>One exposed thread does not restore strict EXR32 equality</p><Link href="/research-agenda">继续隔离 render 边界 →</Link></footer>
  </main>;
}
