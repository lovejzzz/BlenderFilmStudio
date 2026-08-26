import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = { title: '真实 Blender 实验日志｜Blender Film Studio', description: '持续记录 BlenderFilmStudio 在真实 Blender 5.2 上的假设、命令、观察、失败与下一步。', alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/journal/' } };
const entries = [
  ['J-001','最小编译器','B01 / B02 两次净构建结构一致，.blend 字节不一致','STRUCTURE PASS · BYTE IDENTITY FALSIFIED'],
  ['J-002','角色与抓握','真实 rig、Shape Keys、接触采样和双指 IK 已进入编译器','AUTOMATION PASS · HUMAN QUALITY OPEN'],
  ['J-003','物理与回放','源刚体精确复现失败；132 帧固定轨迹回放零误差','SOURCE FALSIFIED · REPLAY PASS'],
  ['J-004','资产安全','路径首轮 6 个逃逸；隐藏 Blender 求值行为首轮被编译','B10 8/8 · B11 9/9'],
  ['J-005','资源预算','真实 Blender 超时/日志与本地输出/RSS 反例全部被分类','B12 FORMAL TRUE · 6/6'],
  ['J-006','编译收据缺口','manifest 尚未绑定 plan、工具链、Blender binary 与输出','B13 PRE-REGISTERED'],
];

export default function JournalPage() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="实验日志导航"><Link href="/research-agenda">研究路线</Link><Link href="/resource-budget-v0-1">B12</Link><a href="#entries">日志</a><a href="#rules">规则</a></nav><span className="edition contact-edition">Real Blender Journal</span></header>
    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> CONTINUOUS REAL-BLENDER LAB RECORD</p><h1>理论先写成假设。<br /><span>让真实 Blender 决定结论。</span></h1><p>实验对象是本机 Blender 5.2.0 LTS build `fbe6228777e7`，运行在 Apple M4 Max / 48 GiB。日志区分回填证据与现场实验；没有 manifest、哈希、几何测量或反例，就不写“已经解决”。</p></div><aside className="contact-gate"><b>LAB POLICY</b><strong>EVIDENCE<br />BEFORE CLAIM</strong><code>real .blend inputs</code><code>real Blender child processes</code><small>negative results stay published</small></aside><div className="contact-stats"><article><strong>5.2 LTS</strong><span>真实 Blender</span><small>fbe6228777e7</small></article><article><strong>6</strong><span>日志条目</span><small>retrospective + live</small></article><article><strong>48 GiB</strong><span>实验主机内存</span><small>Apple M4 Max</small></article><article><strong>ACES 2</strong><span>固定 OCIO</span><small>SHA verified</small></article></div></section>
    <section className="section contact-diagnostic" id="entries"><div className="section-index">00 / 记录</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> HYPOTHESIS · RUN · OBSERVATION</p><h2>保留失败，<br /><span>不重写历史。</span></h2></div><p>每条结论都能回到仓库中的 JSON、manifest、`.blend` 或协议。B06 的失败没有被隐藏，而是直接改变了 B07/B08 的架构：由“每次重算”转为“审核后固定回放”。</p></div><ol className="contact-negative-list">{entries.map(([id,item,observed,result]) => <li key={id}><span>{id}</span><b>{item}</b><code>{observed}</code><small>{result}</small></li>)}</ol></section>
    <section className="section contact-contract" id="rules"><div className="section-index">01 / 日志合同</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> SEVEN REQUIRED FIELDS</p><h2>每次实验必须留下，<br /><span>下一位研究者能复跑的东西。</span></h2></div><p>假设、预注册门槛、真实运行时身份、正反观察、被证伪的假设、机器可读证据路径、下一边界，缺一项就仍是工作笔记而不是晋级结论。</p></div><div className="contact-boundary"><b>REQUIRED</b><span>hypothesis</span><span>frozen gate</span><span>runtime identity</span><span>negative evidence</span><strong>NEXT OPEN BOUNDARY</strong></div></section>
    <section className="section contact-limits"><div className="section-index">02 / 当前进行中</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> B13 · COMPILE RECEIPT</p><h2>结构哈希已经稳定。<br /><span>现在绑定是谁编译了它。</span></h2></div><p>现有 manifest 没有 planHash 与完整工具链身份。B13 已在实现前冻结：B01/B02 各跑两次，生成可独立验证的 receipt，并用 10 类重哈希篡改攻击它。</p></div><div className="contact-artifacts"><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/RESEARCH_CHARTER.md"><span>CHARTER</span><b>目标实验精神 ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/lab-journal.md"><span>FULL JOURNAL</span><b>完整文字记录 ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/2026-08-26-b13-compile-receipt-protocol.md"><span>B13 PROTOCOL</span><b>预注册攻击矩阵 ↗</b></a><Link href="/research-agenda"><span>AGENDA</span><b>未关闭缺口 →</b></Link></div></section>
    <footer><div><span className="brand-mark">BFS</span><b>Real Blender Lab Journal</b></div><p>Blender 5.2 LTS · evidence is append-only in spirit</p><Link href="/">返回研究首页 →</Link></footer>
  </main>;
}
