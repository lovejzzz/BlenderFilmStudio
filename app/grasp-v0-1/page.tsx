import type { Metadata } from 'next';
import Link from 'next/link';

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

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

export default function GraspV01Page() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="B05 导航"><Link href="/contact-v0-1">B04 接触</Link><Link href="/research-agenda">研究路线</Link><a href="#contract">合同</a><a href="#gates">门禁</a></nav><span className="edition contact-edition">Grasp 0.1</span></header>

    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> B05 · CONTRACT VALIDATED · BLENDER NOT EXECUTED</p><h1>不再把手掌贴住，<br /><span>叫作“抓握”。</span></h1><p>B04 已把穿透修成稳定的 2 mm 刚性间距，也暴露了下一层缺口：没有手指链、多接触点、关节限位和闭合过程，就只能证明“附着”，不能证明“抓取”。</p></div><aside className="contact-gate"><b>CURRENT STATUS</b><strong>CONTRACT PASS<br />BENCHMARK NOT RUN</strong><code>valid fixture accepted</code><code>8 / 8 mutations rejected</code><small>no Blender grasp pass claim</small></aside><div className="contact-stats"><article><strong>8 / 8</strong><span>合同变异被拒绝</span><small>schema + semantic validator</small></article><article><strong>2+</strong><span>最少有效接触</span><small>opposing normals required</small></article><article><strong>0</strong><span>允许的 IK stretch</span><small>bone length must stay fixed</small></article><article><strong>3+</strong><span>独立盲审人数</span><small>automation is insufficient</small></article></div></section>

    <section className="section contact-verdict"><div className="section-index">00 / 结论边界</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> WHAT BLENDER CAN ACTUALLY PROVIDE</p><h2>Blender 提供求解与求值。<br /><span>稳定抓握必须由合同定义。</span></h2></div><p>我们可以编译关节、目标、动作和限制，也可以逐帧读取最终骨骼矩阵与求值网格；但“接触点是否足以支撑任务”“重量感是否可信”不是 Blender 自动给出的真值。</p></div><div className="contact-boundary"><b>DIRECT CONTROL</b><span>PoseBone IK limits</span><span>IK targets</span><span>evaluated mesh</span><span>contact patches</span><span>camera rays</span><strong>HUMAN REQUIRED</strong></div></section>

    <section className="section contact-evidence"><div className="section-index light">01 / 六层介入矩阵</div><div className="contact-heading"><div><p className="eyebrow"><span /> CONTROL ≠ EVIDENCE ≠ REALISM</p><h2>能写入 Blender，<br />不代表<span>能由 Blender 证明。</span></h2></div><p>每层都标明证据强度。尤其是抓握稳定性：法线和摩擦锥只能形成显式假设下的代理，不得冒充真实压力、摩擦或肌肉受力。</p></div><div className="contact-checks">{layers.map(([level,title,detail,status]) => <article key={title}><span>{level}</span><h3>{title}</h3><p>{detail}</p><b>{status}</b></article>)}</div></section>

    <section className="section contact-contract" id="contract"><div className="section-index">02 / GraspSpec v0.1</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> DECLARE BEFORE SOLVING</p><h2>先声明手指、patch 与阈值，<br /><span>再允许编译器求解。</span></h2></div><p>GraspSpec 把手指链、主旋转轴、角度范围、目标表面点、单位法线、接触间距、摩擦假设、阶段和停止门禁变成可验证数据。IK 链强制使用 PoseBone IK limits。</p></div><div className="contact-flow"><article><span>01</span><b>FINGER CHAINS</b><p>bones · DOF · IK limits · no stretch</p></article><i>→</i><article><span>02</span><b>CONTACT PATCHES</b><p>point · normal · separation · assumption</p></article><i>→</i><article><span>03</span><b>EVALUATED GATES</b><p>joint · penetration · drift · visibility</p></article></div><div className="contact-plan"><span>SCHEMA SHA-256</span><code>d89e4958bcf5…c6033c0</code><b>8 / 8 CONTRACT MUTATIONS</b><b>NO BLENDER BUILD YET</b></div></section>

    <section className="section contact-diagnostic" id="gates"><div className="section-index">03 / 可证伪门禁</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> EIGHT WAYS TO REJECT A FALSE GRASP</p><h2>成功样例不够。<br /><span>系统必须拒绝伪成功。</span></h2></div><p>下面八个反例在 B05 正式运行前冻结。它们覆盖约束语义、关节越界、错误法线、穿透、接触丢失、骨骼拉伸、镜头遮挡与掌心/指尖证据脱节。</p></div><ol className="contact-negative-list">{negatives.map((item,index) => <li key={item}><span>N{String(index+1).padStart(2,'0')}</span><b>{item}</b><small>PREREGISTERED</small></li>)}</ol></section>

    <section className="section contact-limits"><div className="section-index">04 / 下一次执行</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> NEXT EXECUTABLE BENCHMARK</p><h2>从两指技术夹爪开始，<br /><span>不直接跳到英雄角色。</span></h2></div><p>首个正例只用两个两关节手指夹持凸形道具：12 帧单调闭合、两处对向接触、零穿透、零拉伸、0.30 m 稳定搬运、可见性通过。先证明合同和测量有效，再增加五指、蒙皮和软组织。</p></div><div className="contact-gates"><article><span>DONE</span><b>Schema + semantic validator</b></article><article className="pending"><span>NEXT</span><b>技术夹爪资产 + BuildPlan 指令</b></article><article className="pending"><span>NEXT</span><b>运行时反例 + 双净构建</b></article><article className="blocked"><span>AFTER AUTOMATION</span><b>独立人类盲审</b></article></div><div className="contact-artifacts"><a href={`${repo}specs/grasp-spec.v0.1.schema.json`}><span>CONTRACT</span><b>GraspSpec v0.1 Schema ↗</b></a><a href={`${repo}experiments/grasp-v0-1/contract-self-test.json`}><span>CONTRACT TEST</span><b>8 个变异拒绝证据 ↗</b></a><a href="https://docs.blender.org/api/5.2/bpy.types.PoseBone.html"><span>BLENDER 5.2</span><b>PoseBone / IK limits ↗</b></a><a href="https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=919752"><span>PRIMARY REFERENCE</span><b>NIST 多指抓握综述 ↗</b></a></div></section>

    <footer><div><span className="brand-mark">BFS</span><b>B05 Articulated Grasp</b></div><p>GraspSpec v0.1 · Design evidence, not an executed result</p><Link href="/contact-v0-1">返回 B04 实验 →</Link></footer>
  </main>;
}
