import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B06 接触驱动物理｜Rigid-body support｜Blender Film Studio',
  description: 'Blender 5.2 中取消 Child Of 后的刚体夹持、反例与 10 次跨进程轨迹重复性审计。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/physics-v0-1/' },
};

const frames = [
  ['0048', 'DYNAMIC HANDOFF', 'prop kinematic → false'],
  ['0078', 'CONTACT LIFT', 'friction + opposing colliders'],
  ['0108', 'HOLD END', 'vertical transport 0.300012082 m'],
  ['0112', 'RELEASE', 'no parent · no Child Of'],
];

const negatives = [
  ['N01', 'zero friction', 'TRANSPORT FAIL'], ['N02', 'one collider only', 'TRANSPORT FAIL'],
  ['N03', 'insufficient closure', 'TRANSPORT FAIL'], ['N04', 'prop remains kinematic', 'STATE FAIL'],
  ['N05', 'forbidden parent shortcut', 'STRUCTURE FAIL'], ['N06', '3 m collider teleport', 'INPUT STEP FAIL'],
  ['N07', '5 mm collision margin', 'CONFIG FAIL'], ['N08', '30 solver substeps', 'BUDGET FAIL'],
];

export default function PhysicsV01Page() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B06 导航"><Link href="/grasp-v0-2">B05 抓握</Link><Link href="/research-agenda">研究路线</Link><a href="#evidence">正例</a><a href="#repro">重复性</a></nav><span className="edition contact-edition">Physics 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B06 · BULLET RIGID-BODY EXECUTED</p><h1>道具真的被碰撞带起。<br /><span>轨迹却不够可重复。</span></h1><p>我们移除了 parent、Child Of 与 transform keyframe，让 0.25 kg 道具只靠两侧动画碰撞体和显式摩擦抵抗重力。单次接触搬运成立，8 个反例全部被拒绝；但 10 次净运行的释放轨迹最大分叉 106.825 mm，因此正式 B06 必须判失败。</p></div><aside className="contact-gate"><b>CURRENT STATUS</b><strong>CONTACT LIFT PASS<br />REPRO FAIL</strong><code>11 / 11 positive gates</code><code>8 / 8 negatives rejected</code><small>formal B06 false</small></aside><div className="contact-stats"><article><strong>0.300 m</strong><span>接触驱动抬升</span><small>no transform shortcut</small></article><article><strong>0.899 mm</strong><span>HOLD 最大漂移</span><small>rotation 0.309°</small></article><article><strong>10 × 45</strong><span>净运行 / 成对比较</span><small>1 structure hash</small></article><article><strong>106.825 mm</strong><span>释放轨迹分叉</span><small>threshold 1 mm · FAIL</small></article></div></section>

    <section className="section contact-verdict"><div className="section-index">00 / 结论边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> CONTACT-DRIVEN ≠ DETERMINISTIC</p><h2>物理支撑可行。<br /><span>跨进程确定性不成立。</span></h2></div><p>相同结构、相同数值参数、相同 Blender 版本并不保证 Bullet 在释放阶段给出同一条轨迹。HOLD 的最坏差异只有 0.370 mm，但到 frame 132 扩大到 106.825 mm。</p></div><div className="contact-boundary"><b>PROVEN</b><span>dynamic prop</span><span>opposing collision</span><span>frictional lift</span><span>gravity release</span><span>negative rejection</span><strong>REPRO FAIL</strong></div></section>

    <section className="section contact-evidence" id="evidence"><div className="section-index light">01 / 单次正例</div><div className="contact-heading"><div><p className="eyebrow"><span /> ACTIVE PROP · PASSIVE ANIMATED COLLIDERS</p><h2>不再跟随掌骨，<br /><span>而是让 Bullet 决定道具。</span></h2></div><p>蓝色道具在 frame 49 解除 kinematic；红黄碰撞体保持独立动画。HOLD 期间没有 prop transform 动画、父级、约束或 driver。</p></div><div className="contact-gallery">{frames.map(([frame,title,note],index) => <figure className={index === 1 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/physics-v0-1/B06-frame-${frame}.png`} alt={`B06 rigid-body ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div></section>

    <section className="section contact-diagnostic" id="repro"><div className="section-index">02 / 重复性审计</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> TEN RUNS · FORTY-FIVE PAIRS</p><h2>一次 A/B 相同，<br /><span>不能证明物理确定性。</span></h2></div><p>部分两次运行曾逐坐标完全一致，另一些运行却在释放后明显分叉。于是审计升级为 10 个 factory-startup 进程，对 45 个轨迹对逐帧比较。</p></div><div className="contact-checks"><article><span>STRUCTURE</span><h3>1 hash</h3><p>10 次声明结构完全一致</p><b>PASS</b></article><article><span>HOLD</span><h3>0.370 mm</h3><p>frames 49–108 最坏位置差</p><b>PASS &lt; 1 mm</b></article><article><span>RELEASE</span><h3>106.825 mm</h3><p>frame 132 最坏位置差</p><b>FAIL &gt; 1 mm</b></article><article><span>FORMAL</span><h3>FALSE</h3><p>不能选择性引用一次好结果</p><b>STOP GATE</b></article></div><div className="diagnostic-verdict"><b>ROOT CAUSE CLASS</b><code>POST-RELEASE BULLET TRAJECTORY BRANCHING</code><p>移除落地碰撞后仍存在分叉。结构确定性与求解轨迹确定性必须分开记录。</p></div></section>

    <section className="section contact-limits"><div className="section-index">03 / 反例与下一步</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FALSE SUCCESS MUST STOP EARLY</p><h2>输出看似合理，<br /><span>输入也可能根本不合法。</span></h2></div><p>尤其是 N06：碰撞体一帧瞬移 3 m 又返回，Bullet 仍可能生成“看起来通过”的道具轨迹。因此增加每帧位移配置门槛，而不是只盯结果。</p></div><ol className="contact-negative-list">{negatives.map(([id,item,result]) => <li key={id}><span>{id}</span><b>{item}</b><small>{result}</small></li>)}</ol><div className="contact-flow"><article><span>01</span><b>PHYSICS SOLVE</b><p>允许不确定性并完整记录</p></article><i>→</i><article><span>02</span><b>INSPECT + SELECT</b><p>几何、轨迹、镜头、人类门禁</p></article><i>→</i><article><span>03</span><b>BAKE + HASH</b><p>锁定选中的生产轨迹</p></article></div><div className="contact-artifacts"><a href={`${repo}experiments/physics-v0-1/results.json`}><span>RESULT</span><b>正式失败判定 ↗</b></a><a href={`${repo}experiments/physics-v0-1/B06.reproducibility-audit.json`}><span>10-RUN AUDIT</span><b>45 个轨迹对 ↗</b></a><a href={`${repo}research/2026-08-26-b06-physics-result.md`}><span>RESULT NOTE</span><b>完整证据边界 ↗</b></a><a href="https://docs.blender.org/manual/en/5.2/physics/rigid_body/introduction.html"><span>BLENDER 5.2</span><b>Rigid Body manual ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B06 Physics Support</b></div><p>Contact lift feasible · cross-process release trajectory not reproducible</p><Link href="/grasp-v0-2">返回 B05 →</Link></footer>
  </main>;
}
