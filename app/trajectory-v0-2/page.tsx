import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B08 轨迹编译｜SceneSpec v0.5｜Blender Film Studio',
  description: '把 B07 不可变轨迹接入 SceneSpec、BuildPlan 与 Blender 5.2 正式数据编译器，并执行双净构建与八类反例。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/trajectory-v0-2/' },
};

const frames = [['0048','SOURCE PIN','same immutable sample'],['0078','BUILDPLAN','world transform embedded'],['0108','COMPILED','physics remains disabled']];
const negatives = ['trajectory SHA drift','source evaluation SHA drift','missing compiler authority','binding target mismatch','missing asset object','missing frame sample','compiled key mutation','rigid body injection'];

export default function TrajectoryV02Page() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B08 导航"><Link href="/trajectory-v0-1">B07 轨迹</Link><Link href="/physics-v0-1">B06 物理</Link><a href="#chain">编译链</a><a href="#boundary">边界</a></nav><span className="edition contact-edition">SceneSpec 0.5</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B08 · IMMUTABLE COMPILER INTEGRATION</p><h1>轨迹不再是旁路。<br /><span>它已进入正式编译链。</span></h1><p>B07 已证明固定轨迹能够精确重放；B08 进一步要求 SceneSpec 声明权限、BuildPlan 验证所有来源、Blender 编译器写入关键帧、运行态 evaluator 再逐帧核验。8 类错误均必须在注册层停止。</p></div><aside className="contact-gate"><b>CURRENT STATUS</b><strong>FORMAL B08<br />TRUE</strong><code>SceneSpec → BuildPlan → .blend</code><code>8 / 8 negatives rejected</code><small>source human approval still pending</small></aside><div className="contact-stats"><article><strong>0.5</strong><span>正式合同版本</span><small>data-only trajectory binding</small></article><article><strong>2 / 2</strong><span>结构哈希一致</span><small>46898404…3077d</small></article><article><strong>132</strong><span>逐帧精确核验</span><small>0 m · 0°</small></article><article><strong>8 / 8</strong><span>分层反例被拒绝</span><small>plan + compile + runtime</small></article></div></section>

    <section className="section contact-verdict" id="chain"><div className="section-index">00 / 正式链路</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> ONE RESTRICTED DATA PATH</p><h2>不是让 Codex 写任意脚本，<br /><span>而是提交可验证的数据。</span></h2></div><p>编译器只接受合同中授权的操作。轨迹、源评估、资产和输出边界都先变成不可变 BuildPlan，然后 Blender 才能执行预先实现的轨迹应用逻辑。</p></div><div className="contact-flow"><article><span>01</span><b>SCENESPEC v0.5</b><p>binding + authority</p></article><i>→</i><article><span>02</span><b>BUILDPLAN v0.5</b><p>hash + source verification</p></article><i>→</i><article><span>03</span><b>BLENDER 5.2</b><p>132 authored transforms</p></article></div><div className="contact-plan"><span>BUILDPLAN SHA-256</span><code>7a4bccb64013…2d544dd9</code><b>COMPILER 0.5.0</b><b>NETWORK FALSE · PYTHON INPUT FALSE</b></div></section>

    <section className="section contact-evidence"><div className="section-index light">01 / 共享轨迹证据</div><div className="contact-heading"><div><p className="eyebrow"><span /> SAME BYTES · FORMAL PATH</p><h2>画面不变，<br /><span>证据链变完整。</span></h2></div><p>下列帧来自 B07/B08 共同使用、SHA 锁定的 132 帧 TrajectorySpec。B08 的新证据不是“看起来相同”，而是正式编译后的每个 world transform 与这些样本逐值相同。</p></div><div className="contact-gallery">{frames.map(([frame,title,note],index) => <figure className={index === 1 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/trajectory-v0-1/B07-frame-${frame}.png`} alt={`Shared immutable trajectory ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div></section>

    <section className="section contact-contract"><div className="section-index">02 / 哈希与状态</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> VERIFY, EMBED, PRESERVE</p><h2>可重复性不能靠信任，<br /><span>必须靠逐层锁定。</span></h2></div><p>BuildPlan 同时锁定 PROP 资产、TrajectorySpec、B06 源评估与 132 个样本。编译场景继续携带“技术候选、未获人类批准”状态，任何下游都能看到这一边界。</p></div><div className="contact-boundary"><b>PINNED</b><span>PROP bytes</span><span>trajectory bytes</span><span>source evaluation</span><span>target object</span><span>selection status</span><strong>NO STATUS LAUNDERING</strong></div></section>

    <section className="section contact-diagnostic"><div className="section-index">03 / 反例矩阵</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FAIL AT THE RIGHT LAYER</p><h2>错误不只要失败，<br /><span>还要尽早失败。</span></h2></div><p>哈希、权限和合同错误由 BuildPlan 阻断；资产内部缺对象由 Blender 编译器阻断；保存后关键帧被改或刚体被重新引入，则由 runtime evaluator 以非零状态退出。</p></div><ol className="contact-negative-list">{negatives.map((item,index) => <li key={item}><span>N{String(index+1).padStart(2,'0')}</span><b>{item}</b><small>REJECTED</small></li>)}</ol></section>

    <section className="section contact-limits" id="boundary"><div className="section-index">04 / 科学边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> REPLAY PROOF ≠ PHYSICS APPROVAL</p><h2>B08 已完成，<br /><span>源物理仍未获批准。</span></h2></div><p>形式上的 B08 为真：编译集成、双净构建、逐帧评估与 8 个反例全部通过。但这不修复 B06 已证伪的 Bullet 跨进程释放分叉，也不替代真实人类对镜头可信度的判断。</p></div><div className="contact-artifacts"><a href={`${repo}experiments/trajectory-v0-2/results.json`}><span>RESULT</span><b>完整机器证据 ↗</b></a><a href={`${repo}experiments/trajectory-v0-2/B08.build-plan.json`}><span>BUILDPLAN</span><b>不可变执行计划 ↗</b></a><a href={`${repo}research/2026-08-26-b08-trajectory-compiler-result.md`}><span>RESULT NOTE</span><b>结论与非声明 ↗</b></a><a href={`${repo}specs/scene-spec.v0.5.schema.json`}><span>SCHEMA</span><b>SceneSpec v0.5 ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B08 Trajectory Compiler</b></div><p>Formal integration pass · exact replay · source human approval pending</p><Link href="/trajectory-v0-1">返回 B07 →</Link></footer>
  </main>;
}
