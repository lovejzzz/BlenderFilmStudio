import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B05 正式抓握编译｜SceneSpec v0.4｜Blender Film Studio',
  description: 'SceneSpec v0.4 → immutable BuildPlan v0.4.1 → Blender 5.2 的双手指 IK、接触、搬运、反例和可见性实测。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/grasp-v0-2/' },
};

const frames = [
  ['0036', 'OPEN', 'closure 前，IK influence = 0'],
  ['0048', 'ACQUIRE', '双接触 · 1.997984 mm'],
  ['0078', 'TRANSPORT', '可见网格与 pose 同步上升'],
  ['0108', 'HOLD END', '累计搬运 0.300000006 m'],
  ['0120', 'RELEASE', 'Child Of = 0 · position pop 0 m'],
];

const negatives = [
  ['N01', 'generic joint-limit source', 'BUILD_PLAN'], ['N02', 'invalid joint range', 'SEMANTIC'],
  ['N03', 'parallel contact normals', 'SEMANTIC'], ['N04', 'missing finger bone', 'BLENDER COMPILE'],
  ['N05', 'CREATE_GRASP 未授权', 'BUILD_PLAN'], ['N06', 'runtime stretch enabled', 'EVALUATOR'],
  ['N07', 'HOLD contact disabled', 'EVALUATOR'], ['N08', 'HOLD target drift', 'EVALUATOR'],
];

export default function GraspV02Page() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B05 v0.2 导航"><Link href="/grasp-v0-1">v0.1 Spike</Link><Link href="/contact-v0-1">B04 接触</Link><a href="#evidence">证据</a><a href="#negatives">反例</a></nav><span className="edition contact-edition">Grasp 0.2</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B05 · SCENESPEC v0.4 EXECUTED</p><h1>从声明的抓握，<br /><span>编译到可见的运动。</span></h1><p>这次不再是 standalone spike。哈希锁定的 GraspSpec 被嵌入不可变 BuildPlan，由 Blender 5.2 编译两条受限 IK 手指链、两个对向接触、拿起、0.30 m 搬运与释放；15 项机器门槛、8 个反例和相机可见性均已实测。</p></div><aside className="contact-gate"><b>CURRENT STATUS</b><strong>AUTOMATION PASS<br />HUMAN PENDING</strong><code>15 / 15 machine gates</code><code>8 / 8 negatives rejected</code><small>kinematic · not dynamics</small></aside><div className="contact-stats"><article><strong>2 / 2</strong><span>结构哈希一致</span><small>a21c1e89…4d315df</small></article><article><strong>1.998 mm</strong><span>HOLD 表面间距</span><small>2 active contacts</small></article><article><strong>45 nm</strong><span>网格 / pose 最大偏差</span><small>evaluated geometry</small></article><article><strong>0.30 m</strong><span>道具搬运</span><small>relative drift 18 nm</small></article></div></section>

    <section className="section contact-verdict"><div className="section-index">00 / 结论</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> WHAT IS NOW PROVEN</p><h2>正式编译链成立。<br /><span>物理抓握仍未成立。</span></h2></div><p>SceneSpec v0.4 可以引用并验证 GraspSpec，BuildPlan v0.4.1 可以冻结所有资产和合同哈希，Blender 可以重复构造求值一致的 kinematic grasp。但道具由 keyed Child Of 跟随掌骨，不是由摩擦和接触力支撑。</p></div><div className="contact-boundary"><b>PROVEN</b><span>hash-pinned input</span><span>restricted compile</span><span>evaluated IK</span><span>visible mesh alignment</span><span>camera visibility</span><strong>HUMAN PENDING</strong></div></section>

    <section className="section contact-evidence" id="evidence"><div className="section-index light">01 / 编译后画面证据</div><div className="contact-heading"><div><p className="eyebrow"><span /> AUTHORED CAMERA · EVALUATED GEOMETRY</p><h2>数值通过以后，<br /><span>还要看真正被渲染的网格。</span></h2></div><p>第一次数值成功曾被画面推翻：骨骼移动而手指网格留在原处。编译器 0.4.1 改为移动完整角色根节点，并新增 C15 逐帧比较求值网格中心与 pose bone 中点。</p></div><div className="contact-gallery">{frames.map(([frame,title,note],index) => <figure className={index === 2 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/grasp-v0-2/B05-compiled-frame-${frame}.png`} alt={`B05 compiled grasp ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div><div className="diagnostic-verdict"><b>ACTIVE-CAMERA VISIBILITY</b><code>FINGERS min 91.7% · PROP min 50%</code><p>这是三角形中心 + camera ray 的几何诊断，不是构图或观感评分。真实手部、皮肤、重量与电影表达仍必须由独立人类评审。</p></div></section>

    <section className="section contact-diagnostic" id="negatives"><div className="section-index">02 / 反证</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> EXPECTED FAILURE, OBSERVED FAILURE</p><h2>不是只展示成功。<br /><span>八种伪抓握全部被拒绝。</span></h2></div><p>合同错误在 schema/semantic 或 BuildPlan 层停止；缺骨骼在 Blender 编译层停止；stretch、接触丢失和 target 漂移由运行时求值器停止。</p></div><ol className="contact-negative-list">{negatives.map(([id,item,layer]) => <li key={id}><span>{id}</span><b>{item}</b><small>{layer} · REJECTED</small></li>)}</ol></section>

    <section className="section contact-limits"><div className="section-index">03 / 证据边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> TWO FAILURES WERE NECESSARY</p><h2>第一次手指够不到。<br />第二次<span>画面揭穿了数值。</span></h2></div><p>预注册首跑以 44.024683 mm 间距失败；延长技术手指后，pose 数值通过，但预览发现可见网格未随行。两份旧结果均保留，最终结论只引用编译器 0.4.1 的第三次运行。</p></div><div className="contact-gates"><article><span>FALSIFIED</span><b>0.12 m chain · unreachable target</b></article><article><span>AUDIT FAIL</span><b>pose moved · render mesh stayed</b></article><article><span>FINAL PASS</span><b>15 gates · 8 negatives · visibility</b></article><article className="blocked"><span>OPEN</span><b>3 authentic independent reviews</b></article></div><div className="contact-plan"><span>FINAL BUILDPLAN SHA-256</span><code>c245fe10b81c…92013425c</code><b>STRUCTURE a21c1e89…4d315df</b><b>.BLEND BYTES DIFFER</b></div><div className="contact-artifacts"><a href={`${repo}experiments/grasp-v0-2/results.json`}><span>FINAL RESULT</span><b>完整机器结果 ↗</b></a><a href={`${repo}research/2026-08-26-b05-compiled-grasp-result.md`}><span>RESULT NOTE</span><b>失败与修订链 ↗</b></a><a href={`${repo}research/2026-08-26-b05-compiler-benchmark-protocol.md`}><span>PROTOCOL</span><b>预注册阈值 ↗</b></a><a href={`${repo}specs/scene-spec.v0.4.schema.json`}><span>CONTRACT</span><b>SceneSpec v0.4 ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B05 Compiled Grasp</b></div><p>Automation + visibility pass · dynamics false · human review pending</p><Link href="/review-b05">进入匿名评审 →</Link></footer>
  </main>;
}
