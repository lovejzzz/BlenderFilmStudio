import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const publicUrl = 'https://lovejzzz.github.io/BlenderFilmStudio/actor-v0-1/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'ActorSpec v0.1｜角色系统实测｜Blender Film Studio',
  description: 'Blender 5.2 角色资产、Action Slot、Shape Keys、眼神约束、脚底 socket、Driver 安全与语义身份复现实测。',
  alternates: { canonical: publicUrl },
  openGraph: {
    title: 'ActorSpec v0.1：角色不是 Prompt，是可审计状态',
    description: '16 个规范用例、13 项资产审计、4 项逐帧求值；并记录一次“角度正确、眼球不可见”的反例。',
    url: publicUrl,
    images: [{ url: `${publicUrl}B03-frame-0096.png`, width: 960, height: 540, alt: 'B03 ActorSpec technical mannequin gaze evaluation' }],
  },
  twitter: { card: 'summary_large_image', title: 'BFS ActorSpec v0.1', description: 'Auditable Blender 5.2 character state, measured.' },
};

const frames = [
  { frame: '0036', title: 'Jaw channel', note: 'JAW_OPEN = 0.35', image: 'B03-frame-0036.png' },
  { frame: '0050', title: 'Blink keys', note: 'BLINK_L/R = 1.0', image: 'B03-frame-0050.png' },
  { frame: '0096', title: 'Gaze retarget', note: 'MAX ERROR = 0.0°', image: 'B03-frame-0096.png' },
];

const contract = [
  ['01', 'IDENTITY', 'asset SHA · rest pose · topology · Shape Keys'],
  ['02', 'RIG', 'semantic bones · rotation mode · modifiers'],
  ['03', 'PERFORMANCE', 'Action Slot · facial curves · gaze keys'],
  ['04', 'CONTACT', 'named sockets · windows · tolerances'],
  ['05', 'SECURITY', 'path roots · no network · no full Python'],
];

const references = [
  ['Blender 5.2', 'Animation & Rigging release notes', 'https://developer.blender.org/docs/release_notes/5.2/animation_rigging/'],
  ['Blender API 5.2', 'PoseBone', 'https://docs.blender.org/api/5.2/bpy.types.PoseBone.html'],
  ['Blender API 5.2', 'ShapeKey', 'https://docs.blender.org/api/5.2/bpy.types.ShapeKey.html'],
  ['Blender API 5.2', 'ActionSlot', 'https://docs.blender.org/api/5.2/bpy.types.ActionSlot.html'],
  ['Blender API 5.2', 'Driver', 'https://docs.blender.org/api/5.2/bpy.types.Driver.html'],
  ['Blender Manual 5.2', 'Drivers and security', 'https://docs.blender.org/manual/en/5.2/animation/drivers/introduction.html'],
];

export default function ActorV01Page() {
  return (
    <main className="actor-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="角色实验导航"><Link href="/">技术基线</Link><Link href="/compiler-v0-1">编译实验</Link><Link href="/pixel-v0-1">像素实验</Link><Link href="/research-agenda">研究路线</Link><Link className="contact-route" href="/contact-v0-1">接触实验</Link><a href="#evidence">证据</a><a href="#limits">边界</a></nav>
        <span className="edition actor-edition">Actor 0.1</span>
      </header>

      <section className="actor-hero">
        <div className="actor-axis" aria-hidden="true"><i /><i /><i /></div>
        <div className="actor-hero-copy"><p className="eyebrow"><span /> BLENDER 5.2 · EXECUTED · B03</p><h1>角色不是 Prompt。<br /><span>是可审计的状态。</span></h1><p>冻结身份、骨架、拓扑、Shape Keys、动作、眼神、接触窗口与安全边界；再让 Blender 求值，测量实际结果，而不是只检查配置是否存在。</p></div>
        <aside className="actor-lock"><b>IDENTITY LOCK</b><code>a923c92b979f…b1e7</code><dl><div><dt>REST POSE</dt><dd>LOCKED</dd></div><div><dt>TOPOLOGY</dt><dd>4 / 4</dd></div><div><dt>DRIVERS</dt><dd>SAFE ONLY</dd></div><div><dt>HUMAN REVIEW</dt><dd>REQUIRED</dd></div></dl></aside>
        <div className="actor-stats"><article><strong>16/16</strong><span>规范用例</span><small>valid + invalid fixtures</small></article><article><strong>13/13</strong><span>资产审计</span><small>inside Blender 5.2</small></article><article><strong>4/4</strong><span>求值检查</span><small>pose · face · gaze · slip</small></article><article><strong>0.0°</strong><span>最大眼神误差</span><small>threshold 2°</small></article></div>
      </section>

      <section className="section actor-verdict">
        <div className="section-index">00 / 有限结论</div>
        <div className="actor-heading dark-heading"><div><p className="eyebrow dark"><span /> DATA-DRIVEN SUBSTRATE EXISTS</p><h2>控制底座成立。<br />“真实演员”<span>尚未成立。</span></h2></div><p>Blender 5.2 已能承载可寻址、可分层、可拒绝、可逐帧测量的角色数据。但技术假人的成功不证明皮肤、毛发、肌肉、口型、情绪、微表演或手指接触已经解决。</p></div>
        <div className="actor-boundary"><b>本阶段只证明</b><span>身份锁</span><span>动作求值</span><span>表情通道</span><span>眼神方向</span><span>socket 滑移</span><span>Driver 拒绝</span></div>
      </section>

      <section className="section actor-evidence" id="evidence">
        <div className="section-index light">01 / 可见求值</div>
        <div className="actor-heading"><div><p className="eyebrow"><span /> THREE REPRESENTATIVE FRAMES</p><h2>不是资产清单。<br />是依赖图求值后的画面。</h2></div><p>B03 将 Action Slot、Shape Key F-Curves 与 Damped Track 目标写入一个全新 Blender 进程，并在关键帧求值。画面是技术可观察性证据，不是角色美术质量演示。</p></div>
        <div className="actor-gallery">{frames.map(item => <figure key={item.frame}><Image src={`${imageBasePath}/actor-v0-1/${item.image}`} alt={`B03 frame ${item.frame}: ${item.title}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 33vw" /><figcaption><span>FRAME {item.frame}</span><h3>{item.title}</h3><code>{item.note}</code></figcaption></figure>)}</div>
        <p className="actor-image-note">技术假人故意保持低复杂度，使眼神方向和变形通道可以被直接观察；它不代表项目对最终人物造型的目标。</p>
      </section>

      <section className="section actor-contract">
        <div className="section-index">02 / ActorSpec v0.1</div>
        <div className="actor-heading dark-heading"><div><p className="eyebrow dark"><span /> BOUNDED CHARACTER CONTRACT</p><h2>把“角色一致”拆成<br /><span>五组机器合同。</span></h2></div><p>精确二进制 SHA 用于冻结被选中的资产；规范化语义哈希用于判断重生成的骨架、拓扑、Shape Key 和动作是否等价。两者回答不同问题，不能混成一个“文件相同”。</p></div>
        <div className="actor-contract-grid">{contract.map(([id, title, copy]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{copy}</p></article>)}</div>
        <div className="actor-layers"><b>PERFORMANCE ORDER</b><span>BODY</span><i>→</i><span>BREATH</span><i>→</i><span>GAZE</span><i>→</i><span>FACIAL</span><i>→</i><span>CONTACT</span></div>
      </section>

      <section className="section actor-failure">
        <div className="section-index light">03 / 被证伪的实现</div>
        <div className="actor-heading"><div><p className="eyebrow"><span /> ZERO ERROR, WRONG RESULT</p><h2>角度误差 0°，<br />眼球却在<span>头后面。</span></h2></div><p>第一次实现把骨骼负 Y 轴对准目标，但眼球几何位于正 Y 方向。约束数学上完全满足，视觉结果却错误。改为正 Y 跟踪后，误差仍为 0°，眼球才真正可见。</p></div>
        <div className="axis-case"><article><span>FAILED</span><b>TRACK −Y</b><p>target error = 0.0°<br />visible geometry = wrong side</p></article><i>→</i><article className="fixed"><span>CORRECTED</span><b>TRACK +Y</b><p>target error = 0.0°<br />visible geometry = target side</p></article><aside><b>研究结论</b><p>单一约束误差不足以验收角色；合同必须固定骨轴/几何约定，或增加几何可观察性与视觉审查。</p></aside></div>
      </section>

      <section className="section actor-identity">
        <div className="section-index">04 / 两种“相同”</div>
        <div className="actor-heading dark-heading"><div><p className="eyebrow dark"><span /> BINARY ≠ SEMANTIC IDENTITY</p><h2>两次生成，`.blend` SHA 不同；<br /><span>角色语义身份相同。</span></h2></div><p>相同 Blender、相同生成器、相同输出路径连续运行两次。资产文件字节不同，但 rest pose、四个拓扑、Shape Key set、动作库与聚合身份哈希全部一致。</p></div>
        <div className="identity-compare"><article><span>RUN A · BINARY SHA</span><code>a1a626484ee1…57fa2</code></article><strong>≠</strong><article><span>RUN B · BINARY SHA</span><code>c72713bc9f57…cc2a9</code></article><aside><span>SEMANTIC IDENTITY</span><code>a923c92b979f…b1e7</code><b>EQUAL</b></aside></div>
      </section>

      <section className="section actor-security">
        <div className="section-index light">05 / 运行时安全</div>
        <div className="actor-heading"><div><p className="eyebrow"><span /> SCHEMA CANNOT SEE INSIDE .BLEND</p><h2>文档合法，<br />导入资产仍可能危险。</h2></div><p>负向样本在合法 ActorSpec 指向的资产副本里加入非 simple Driver 表达式。JSON 仍通过，但 Blender 运行时审计在 A11 明确拒绝；篡改 rest pose 哈希则在 A05 拒绝。</p></div>
        <div className="security-gates"><article><span>01</span><b>JSON Schema</b><small>shape · enums · ranges</small></article><i>→</i><article><span>02</span><b>Semantic validator</b><small>references · frames · paths</small></article><i>→</i><article><span>03</span><b>Blender asset audit</b><small>Drivers · constraints · hashes</small></article><i>→</i><article><span>04</span><b>Evaluated metrics</b><small>pose · face · gaze · slip</small></article></div>
      </section>

      <section className="section actor-integration">
        <div className="section-index">06 / SceneSpec v0.2 集成</div>
        <div className="actor-heading dark-heading"><div><p className="eyebrow dark"><span /> ACTOR → SCENE → BUILDPLAN → BLENDER</p><h2>B03 已进入场景合同。<br /><span>目标相对误差可测。</span></h2></div><p>SceneSpec v0.1 保持冻结；v0.2 新增 ActorSpec 哈希引用、场景 target sockets 与角色专用权限。相同 BuildPlan 两次净编译得到同一结构哈希，再从最终 `.blend` 测量角色—目标关系。</p></div>
        <div className="integration-stats"><article><strong>2 / 2</strong><span>净构建结构一致</span><small>96041c22…d5ff</small></article><article><strong>9 / 9</strong><span>表情值零误差</span><small>compiled Shape Keys</small></article><article><strong>0.0°</strong><span>场景相对眼神</span><small>2 targets × 2 eyes</small></article><article><strong>4.4e−8 m</strong><span>最大脚底位置误差</span><small>144 samples · rotation 0°</small></article></div>
        <div className="integration-plan"><span>BUILDPLAN</span><code>56417f40ffa6…c22cd</code><b>5 / 5 EVALUATION PASS</b><b>4 / 4 NEGATIVES REJECTED</b></div>
        <div className="integration-flow"><article><span>01</span><b>SceneSpec v0.2</b><small>actors + targets + permissions</small></article><i>→</i><article><span>02</span><b>Immutable BuildPlan</b><small>asset/action/spec hashes</small></article><i>→</i><article><span>03</span><b>Blender compile</b><small>Action + Shape Keys + gaze</small></article><i>→</i><article><span>04</span><b>Scene evaluator</b><small>gaze + position + rotation + slip</small></article></div>
      </section>

      <section className="section actor-limits" id="limits">
        <div className="section-index">07 / 明确边界与下一步</div>
        <div className="actor-heading dark-heading"><div><p className="eyebrow dark"><span /> B04 AUTOMATION EXECUTED</p><h2>手已经拿起物体。<br /><span>但还不像真实抓取。</span></h2></div><p>B04 已加入可见手掌、真实道具、父级切换与求值几何，10/10 机器检查和 8/8 反例通过；人类审查仍未完成，盒状手掌也不能证明手指与重量感。</p></div>
        <div className="actor-limit-grid"><article><span>NOT PROVEN</span><h3>近景人物真实感</h3><p>皮肤、眼睛、牙齿、舌头、头发、肌肉、口型、情绪与微表演。</p></article><article><span>NOT PROVEN</span><h3>接触可信度</h3><p>手指抓握、碰撞压力、掌心贴合、软组织、布料响应与重量感。</p></article><article className="next"><span>EXECUTED · HUMAN PENDING</span><h3><Link href="/contact-v0-1">B04 · Prop pickup</Link></h3><p>查看 SceneSpec v0.3、双净构建、逐帧 BVH、失败修正与全部反例。</p></article></div>
        <div className="actor-artifacts"><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/specs/actor-spec.v0.1.schema.json" target="_blank" rel="noreferrer"><span>CONTRACT</span><b>ActorSpec schema ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/tree/main/experiments/actor-v0-1" target="_blank" rel="noreferrer"><span>EXECUTED EVIDENCE</span><b>audit · evaluation · negatives ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/2026-08-26-actor-spec-v0.1-experiment.md" target="_blank" rel="noreferrer"><span>RESEARCH NOTE</span><b>methods · nonclaims ↗</b></a></div>
        <ol className="references actor-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>ActorSpec v0.1</b></div><p>Blender 5.2.0 LTS · technical character substrate</p><Link href="/research-agenda">进入 SceneSpec 集成缺口 →</Link></footer>
    </main>
  );
}
