import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B05 手指级抓握｜GraspSpec v0.1｜Blender Film Studio',
  description: 'Blender 5.2 手指链、IK 限位、接触 patches、反例与人类门禁的可执行研究设计。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/grasp-v0-1/' },
};

const layers = [
  ['L4 · DIRECT', '关节与自由度', 'PoseBone IK limits、locks、stiffness、stretch policy', '可深度介入'],
  ['L4 · DIRECT', 'IK 与动作曲线', '受限 IK target、chain length、F-Curve 与最终 pose matrix', '可深度介入'],
  ['L3 · MEASURED', '多点几何接触', '求值三角形、patch 距离、穿透与相对漂移', '可构建'],
  ['L2 · PROXY', '抓握稳定性', '接触法线 + 摩擦假设 + 任务方向；不是实测受力', '条件研究'],
  ['L1 · WEAK', '皮肤与软组织', '盒状/刚性代理不能证明指腹压缩、褶皱或肌腱', '尚未解决'],
  ['L0 · HUMAN', '动作与电影表达', '意图、重量、节奏、构图和表演必须盲审', '不能自动替代'],
];

const negatives = [
  'IK 手指却只使用普通 Limit Rotation', '关节越界 10°', '两个接触法线近乎平行', '指尖穿入道具 8 mm',
  'HOLD 只剩一个有效接触', 'IK stretch 改变指骨长度', '接触被镜头遮挡', '掌心父级成立但指尖 patches 漂移',
];

const spikeFrames = [
  ['0036', 'OPEN', 'independent IK targets'],
  ['0048', 'CLOSED', '1.000011 mm proxy gap'],
  ['0078', 'TRANSPORT', 'relative drift 0 m'],
  ['0108', 'HOLD END', 'transport 0.300000006 m'],
  ['0120', 'RELEASE', 'targets reopen'],
];

export default function GraspV01Page() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B05 导航"><Link href="/contact-v0-1">B04 接触</Link><Link href="/research-agenda">研究路线</Link><a href="#contract">合同</a><a href="#gates">门禁</a></nav><span className="edition contact-edition">Grasp 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B05 · CONTRACT + IK SPIKE EXECUTED</p><h1>不再把手掌贴住，<br /><span>叫作“抓握”。</span></h1><p>B04 已把穿透修成稳定的 2 mm 刚性间距。B05 进一步实测两条两关节 IK 手指链：关节限位、无拉伸、单调闭合、双侧 1 mm 间距和 0.30 m 搬运均可逐帧复现；正式 BuildPlan 与接触驱动物理仍未完成。</p></div><aside className="contact-gate"><b>CURRENT STATUS</b><strong>IK SPIKE PASS<br />FORMAL B05 FALSE</strong><code>2 / 2 clean structures</code><code>10 / 10 spike gates</code><small>standalone builder · shared carrier</small></aside><div className="contact-stats"><article><strong>8 / 8</strong><span>合同变异被拒绝</span><small>schema + semantic validator</small></article><article><strong>0°</strong><span>最大关节越界</span><small>PoseBone IK limits</small></article><article><strong>1.00 mm</strong><span>HOLD 表面间距</span><small>relative drift 0 m</small></article><article><strong>0.30 m</strong><span>HOLD 搬运</span><small>common carrier · not dynamics</small></article></div></section>

    <section className="section contact-verdict"><div className="section-index">00 / 结论边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> WHAT BLENDER CAN ACTUALLY PROVIDE</p><h2>Blender 提供求解与求值。<br /><span>稳定抓握必须由合同定义。</span></h2></div><p>我们可以编译关节、目标、动作和限制，也可以逐帧读取最终骨骼矩阵与求值网格；但“接触点是否足以支撑任务”“重量感是否可信”不是 Blender 自动给出的真值。</p></div><div className="contact-boundary"><b>DIRECT CONTROL</b><span>PoseBone IK limits</span><span>IK targets</span><span>evaluated mesh</span><span>contact patches</span><span>camera rays</span><strong>HUMAN REQUIRED</strong></div></section>

    <section className="section contact-evidence"><div className="section-index light">01 / 六层介入矩阵</div><div className="contact-heading"><div><p className="eyebrow"><span /> CONTROL ≠ EVIDENCE ≠ REALISM</p><h2>能写入 Blender，<br />不代表<span>能由 Blender 证明。</span></h2></div><p>每层都标明证据强度。尤其是抓握稳定性：法线和摩擦锥只能形成显式假设下的代理，不得冒充真实压力、摩擦或肌肉受力。</p></div><div className="contact-checks">{layers.map(([level,title,detail,status]) => <article key={title}><span>{level}</span><h3>{title}</h3><p>{detail}</p><b>{status}</b></article>)}</div></section>

    <section className="section contact-contract" id="contract"><div className="section-index">02 / GraspSpec v0.1</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> DECLARE BEFORE SOLVING</p><h2>先声明手指、patch 与阈值，<br /><span>再允许编译器求解。</span></h2></div><p>GraspSpec 把手指链、主旋转轴、角度范围、目标表面点、单位法线、接触间距、摩擦假设、阶段和停止门禁变成可验证数据。IK 链强制使用 PoseBone IK limits。</p></div><div className="contact-flow"><article><span>01</span><b>FINGER CHAINS</b><p>bones · DOF · IK limits · no stretch</p></article><i>→</i><article><span>02</span><b>CONTACT PATCHES</b><p>point · normal · separation · assumption</p></article><i>→</i><article><span>03</span><b>EVALUATED GATES</b><p>joint · penetration · drift · visibility</p></article></div><div className="contact-plan"><span>SPIKE STRUCTURE SHA-256</span><code>86ae7ec3287c…d23385</code><b>2 / 2 CLEAN MANIFESTS</b><b>FORMAL BUILDPLAN PENDING</b></div></section>

    <section className="section contact-evidence"><div className="section-index light">02B / Blender 5.2 feasibility spike</div><div className="contact-heading"><div><p className="eyebrow"><span /> ACTUAL IK · ACTUAL POSE-BONE LIMITS</p><h2>两条手指链，<br /><span>双净构建逐帧一致。</span></h2></div><p>这些图是求值后骨骼 head/tail 的技术代理，不是蒙皮手指。两条两段链分别由 IK target 驱动；12 帧闭合距离单调下降，HOLD 的目标误差最多 9.034 μm，骨长比误差最多约 1.01×10⁻⁷。</p></div><div className="contact-gallery">{spikeFrames.map(([frame,title,note],index) => <figure className={index === 2 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/grasp-v0-1/B05-frame-${frame}.png`} alt={`B05 IK spike ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div><div className="diagnostic-verdict"><b>CLASSIFICATION</b><code>BLENDER_52_TWO_FINGER_IK_FEASIBILITY_PASS</code><p>这足以支持下一步实现 GraspSpec → BuildPlan 指令；不足以支持“稳定抓握已解决”。道具与夹爪共享 carrier，因此搬运不是由接触、摩擦或力学产生。</p></div></section>

    <section className="section contact-diagnostic" id="gates"><div className="section-index">03 / 可证伪门禁</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> EIGHT WAYS TO REJECT A FALSE GRASP</p><h2>成功样例不够。<br /><span>系统必须拒绝伪成功。</span></h2></div><p>下面八个反例在 B05 正式运行前冻结。它们覆盖约束语义、关节越界、错误法线、穿透、接触丢失、骨骼拉伸、镜头遮挡与掌心/指尖证据脱节。</p></div><ol className="contact-negative-list">{negatives.map((item,index) => <li key={item}><span>N{String(index+1).padStart(2,'0')}</span><b>{item}</b><small>PREREGISTERED</small></li>)}</ol></section>

    <section className="section contact-limits"><div className="section-index">04 / 下一次执行</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FROM SPIKE TO FORMAL COMPILER</p><h2>接口已经证明可用。<br /><span>现在把它变成不可变 BuildPlan。</span></h2></div><p>下一步不是继续美化 spike，而是增加手指链与 contact patch 的正式编译指令，让 prop 不再与手共享 carrier，再运行八个冻结的运行时反例、双净构建、几何可见性和人类盲审。</p></div><div className="contact-gates"><article><span>DONE</span><b>Schema + semantic validator</b></article><article><span>DONE · SPIKE</span><b>真实 IK + limits + 双净构建</b></article><article className="pending"><span>NEXT</span><b>GraspSpec → BuildPlan + runtime negatives</b></article><article className="blocked"><span>AFTER AUTOMATION</span><b>独立人类盲审</b></article></div><div className="contact-artifacts"><a href={`${repo}experiments/grasp-v0-1/results.json`}><span>SPIKE RESULT</span><b>双构建与逐帧指标 ↗</b></a><a href={`${repo}research/2026-08-26-b05-ik-feasibility-result.md`}><span>BOUNDARY</span><b>可行性结论与非声明 ↗</b></a><a href="https://docs.blender.org/api/5.2/bpy.types.PoseBone.html"><span>BLENDER 5.2</span><b>PoseBone / IK limits ↗</b></a><a href="https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=919752"><span>PRIMARY REFERENCE</span><b>NIST 多指抓握综述 ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B05 Articulated Grasp</b></div><p>GraspSpec v0.1 · IK feasibility executed · Formal benchmark pending</p><Link href="/contact-v0-1">返回 B04 实验 →</Link></footer>
  </main>;
}
