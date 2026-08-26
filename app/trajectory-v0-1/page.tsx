import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B07 不可变轨迹｜TrajectorySpec v0.1｜Blender Film Studio',
  description: '把一次选定的 Blender 物理解算导出为哈希锁定逐帧轨迹，并在关闭物理后精确重放。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/trajectory-v0-1/' },
};

const frames = [['0048','HANDOFF','source transform baked'],['0078','PLAYBACK','physics disabled'],['0108','HOLD END','declared frame sample']];
const negatives = ['wrong file hash','missing frame sample','duplicate frame','non-normalized quaternion','source evaluation hash drift','rigid body reintroduced','transform key mutation','undeclared target object'];

export default function TrajectoryV01Page() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B07 导航"><Link href="/physics-v0-1">B06 物理</Link><Link href="/grasp-v0-2">B05 抓握</Link><a href="#artifact">合同</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">Trajectory 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B07 · IMMUTABLE PLAYBACK EXECUTED</p><h1>解算可以分叉。<br /><span>交付轨迹必须锁定。</span></h1><p>B06 证明 Bullet 的释放轨迹跨进程并不可靠。B07 选择一条明确标为“未获人类批准”的技术候选，把 132 帧位置和四元数导出为哈希锁定数据，再在关闭物理的 Blender 5.2 场景中精确重放。</p></div><aside className="contact-gate"><b>CURRENT STATUS</b><strong>REPLAY PASS<br />SOURCE UNAPPROVED</strong><code>0 m position error</code><code>0° rotation error</code><small>formal B07 false</small></aside><div className="contact-stats"><article><strong>132</strong><span>连续逐帧样本</span><small>24 fps · world space</small></article><article><strong>2 / 2</strong><span>结构哈希一致</span><small>0d41d623…ae1b15</small></article><article><strong>8 / 8</strong><span>反例被拒绝</span><small>input + runtime</small></article><article><strong>0</strong><span>重放误差</span><small>position + rotation</small></article></div></section>

    <section className="section contact-verdict"><div className="section-index">00 / 系统边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> SOLVE ≠ SELECT ≠ PLAYBACK</p><h2>确定的是重放，<br /><span>不是原始物理。</span></h2></div><p>TrajectorySpec 把一个候选结果变成可审计输入。它保留来源哈希和未批准状态，因此下游不能把“可重复”偷换成“物理正确”。</p></div><div className="contact-boundary"><b>PROVEN</b><span>data-only artifact</span><span>source hash</span><span>continuous frames</span><span>exact replay</span><span>negative rejection</span><strong>SOURCE HUMAN PENDING</strong></div></section>

    <section className="section contact-evidence"><div className="section-index light">01 / 重放画面</div><div className="contact-heading"><div><p className="eyebrow"><span /> PHYSICS DISABLED · KEYS PINNED</p><h2>同一条轨迹，<br /><span>不再让求解器重新决定。</span></h2></div><p>这些画面来自 replay 场景：道具没有 rigid body、父级、约束或 driver。每个 frame 都由 TrajectorySpec 的 world transform 直接定义。</p></div><div className="contact-gallery">{frames.map(([frame,title,note],index) => <figure className={index === 1 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/trajectory-v0-1/B07-frame-${frame}.png`} alt={`B07 baked trajectory ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div></section>

    <section className="section contact-contract" id="artifact"><div className="section-index">02 / TrajectorySpec v0.1</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> DATA, NOT EXECUTABLE CODE</p><h2>把轨迹当资产，<br /><span>像模型和贴图一样版本化。</span></h2></div><p>合同包含目标对象、frame range、fps、空间、132 个 transform、源评估 SHA、源结构 SHA、误差门槛和选择状态。网络与可执行代码均禁止。</p></div><div className="contact-flow"><article><span>01</span><b>SOLVE CANDIDATE</b><p>Bullet · may branch</p></article><i>→</i><article><span>02</span><b>SELECT + HASH</b><p>TrajectorySpec · provenance</p></article><i>→</i><article><span>03</span><b>REPLAY</b><p>physics off · exact keys</p></article></div><div className="contact-plan"><span>TRAJECTORY SHA-256</span><code>c4efaf29535c…e3caf146</code><b>STRUCTURE 0d41d623…ae1b15</b><b>SELECTION NOT HUMAN APPROVED</b></div></section>

    <section className="section contact-diagnostic"><div className="section-index">03 / 反例</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> HASH OR STOP</p><h2>任何来源或关键帧漂移，<br /><span>都必须让重放失败。</span></h2></div><p>输入级错误在 build 前停止；运行态重新加刚体或篡改 frame 60 关键帧，由逐帧 evaluator 停止。</p></div><ol className="contact-negative-list">{negatives.map((item,index) => <li key={item}><span>N{String(index+1).padStart(2,'0')}</span><b>{item}</b><small>REJECTED</small></li>)}</ol></section>

    <section className="section contact-limits" id="boundary"><div className="section-index">04 / 下一步</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> DO NOT LAUNDER THE SOURCE</p><h2>可重复播放，<br /><span>不是批准这条物理轨迹。</span></h2></div><p>不可变 BuildPlan 集成已经由 B08 完成；正式 B07 现在只剩源 solve 的镜头证据与真实人类评审。当前未批准状态已被证明会穿过正式编译链。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/trajectory-v0-1/results.json`}><span>RESULT</span><b>双构建与反例 ↗</b></a><a href={`${repo}specs/benchmarks/B07.trajectory.json`}><span>TRAJECTORY</span><b>132 帧不可变数据 ↗</b></a><Link href="/trajectory-v0-2"><span>B08</span><b>正式编译集成 →</b></Link><a href={`${repo}specs/trajectory-spec.v0.1.schema.json`}><span>SCHEMA</span><b>TrajectorySpec v0.1 ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B07 Immutable Trajectory</b></div><p>Exact replay pass · BuildPlan integration passed in B08 · source approval pending</p><Link href="/trajectory-v0-2">继续 B08 →</Link></footer>
  </main>;
}
