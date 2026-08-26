import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = { title: '真实 Blender 实验日志｜Blender Film Studio', description: '持续记录 BlenderFilmStudio 在真实 Blender 5.2 上的假设、命令、观察、失败与下一步。', alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/journal/' } };
const entries = [
  ['J-001','最小编译器','B01 / B02 两次净构建结构一致，.blend 字节不一致','STRUCTURE PASS · BYTE IDENTITY FALSIFIED'],
  ['J-002','角色与抓握','真实 rig、Shape Keys、接触采样和双指 IK 已进入编译器','AUTOMATION PASS · HUMAN QUALITY OPEN'],
  ['J-003','物理与回放','源刚体精确复现失败；132 帧固定轨迹回放零误差','SOURCE FALSIFIED · REPLAY PASS'],
  ['J-004','资产安全','路径首轮 6 个逃逸；隐藏 Blender 求值行为首轮被编译','B10 8/8 · B11 9/9'],
  ['J-005','资源预算','真实 Blender 超时/日志与本地输出/RSS 反例全部被分类','B12 FORMAL TRUE · 6/6'],
  ['J-006','编译收据','四次真实净构建、19 项验证、三次实现假设被证伪','B13 FORMAL TRUE · 10+2'],
  ['J-007','完整审片样片','真实 Blender 跑完 144 帧；恒真 OCIO 检查被发现后全量重跑','B14 AUTOMATION TRUE · HUMAN PENDING'],
  ['J-008','代理像素复现','同源 A/B 仅 127/144 帧解码 exact；114 像素差异','B15 FORMAL EXACT FALSIFIED'],
  ['J-009','Dither 因果隔离','只把 dither 1→0，仍有 14 帧、69 像素微差','B16 DITHER NOT SUFFICIENT'],
  ['J-010','Eevee 采样因果','1/32 samples × dither 0/1，共 8 次净运行与 1,152 帧','B17 SAMPLING CAUSAL SUPPORT · 12/12'],
  ['J-011','采样剂量响应','1/2/4/8/16/32 samples 共 12 次净运行，exact 向量 F,T,F,F,F,F','B18 NON-MONOTONIC · 13/13'],
  ['J-012','Eevee 控制清单','真实 RNA 显示 Fast GI 与 TAA reprojection 开启；两次无效候选被拒绝','EXPLORATORY · NOT CAUSAL'],
  ['J-013','GI × Reprojection','四个 on/off cells 全部非 exact；同时关闭仍 131/144','B19 NO SUFFICIENT INTERVENTION · 14/14'],
  ['J-014','进程历史隔离','39 个唯一 PID、468 帧；每帧新进程仍只有 26/36 哨兵配对 exact','B20 PROCESS ISOLATION NOT SUFFICIENT · 18/18'],
  ['J-015','Float 输出接口','后台 Render Result.pixels 为空；同一结果可保存 PNG8 与 float EXR32','EXPLORATORY · DIRECT MEMORY CLAIM REJECTED'],
  ['J-016','双输出定位','EXR32 与 PNG8 均 21/36 exact，且 36 个 pair 标签逐一相同','B21 PRE-PNG VARIATION SUPPORT · 21/21'],
  ['J-017','线程数对照冻结','T01 × T08、12 哨兵、三重复；明确 CPU threads 可能不控制 Eevee GPU','B22 PRE-REGISTERED · 72 PROCESSES'],
  ['J-018','线程数对照与下一边界','T01 19/36、T08 22/36；1 thread 不足，转向进程初始化 × repeated render','B22 THREAD COUNT NOT SUFFICIENT · 19/19'],
  ['J-019','重复 render 协议冻结','PERSIST 同 PID 三次 render × FRESH 单次；72 进程、144 EXR、三道 gate','B23 PRE-REGISTERED · NOT EXECUTED'],
  ['J-020','重复 render 结果与研究转向','同 PID 同帧仍只有 59/108 exact；严格 provenance 与感知生产门分离','B23 PER-RENDER VARIATION · 20/20'],
  ['J-021','生产容差与 holdout 冻结','288 EXR + 36 PNG derivation；24 个未见帧、72 新进程验证','B24 PRE-REGISTERED · NO THRESHOLD REVISION'],
  ['J-022','生产容差 holdout 结果','EXR 与 PNG 均 72/72；strict exact 70/72，转向 temporal playback','B24 ENVELOPE SUPPORT · 22/22'],
  ['J-023','连续序列时间残差','三次完整 144 帧；temporal 429/429，static 430/432，frame 38 超门 1 像素','B25 STATIC-ONLY FAIL · 19/19'],
  ['J-024','匿名时间稳定性审片包','三条 lossless carrier 均 144/144 RGB exact；18 个平衡 session，当前 0 response','B26 PACKAGE READY · HUMAN PENDING'],
  ['J-025','frame 38 历史隔离','HISTORY 2/12、DIRECT 3/12 超门；p≈1；24 个输出只出现两个 exact 模式','B27 NO HISTORY ASSOCIATION · 23/23'],
  ['J-026','同 PID 重复 frame 38','12/12 PID 内出现两个冻结模式；144 render，42/132 相邻调用切换','B28 WITHIN-PID SWITCH · 23/23'],
  ['J-027','Pass 域探索定位','单 PID pilot：Combined/Crypto 同步一次；Depth/Normal/Position exact；Vector first-call transient','B29 DERIVATION ONLY'],
  ['J-028','Pass 域正式反证','103 coupled R、38 coupled A、3 Crypto-only 解耦；closest-sample passes 144/144 exact','B29 DECOUPLED PATTERN · 25/25'],
  ['J-029','固定 jitter 探索','NATURAL 单 PID 双模式；CENTER 与 ±QUARTER 各 12/12 exact，但都改变全幅采样','B30 DERIVATION ONLY'],
  ['J-030','固定 jitter 正式干预','CENTER 12/12 PID、144/144 exact；NATURAL 10/12 PID 切换；全幅采样代价保留','B30 STRICT STABILITY · 25/25'],
  ['J-031','采样质量代价探索','三个 frame 的 CENTER/NATURAL edge-reference RMSE 为 2.19–2.26×；双 1024 proxy 自身误差极小','B31 DERIVATION ONLY'],
  ['J-032','采样质量正式 holdout','四个未见 frame 全部 ≥1.5；最小 2.1693×；reference reliability 4/4','B31 EDGE COST SUPPORT · 23/23'],
  ['J-033','四点确定性积分','Q4 A/B exact；edge error 降至 CENTER 的 0.555×，仍为 NATURAL 的 1.238×','B32 DERIVATION · 4.093× COST'],
  ['J-034','八点分层积分','Q8 A/B exact；三个 derivation frame 的 Q8/NATURAL 为 0.926–0.948×','B32.1 PROMOTE TO HOLDOUT'],
  ['J-035','正式 holdout 无效尝试','frame 22 cutoff tie 使 quantile+≥ 选出 25,921 而非 25,920 pixels','B32 V0.1 INVALID · NO QUALITY DECISION'],
  ['J-036','Exact-top-k 正式 holdout','28 个新 PID、112 EXR；Q4 mean 1.2706×，Q8 mean 0.9510×，29/29 attacks','B32 V0.2 COST CURVE SUPPORT'],
  ['J-037','Q4/Q8 连续帧派生','28 PID、224 EXR；motion Q4/N 1.823×，Q8/N 0.948×，Q8/Q4 0.520×','B33 DERIVATION · THRESHOLD FREEZE'],
  ['J-038','Q8 连续帧正式 holdout','新 frame 74–81；Q8 motion mean 0.9497×、max 1.0397×，12/12 attacks','B33 TEMPORAL PROXY SUPPORT'],
];

export default function JournalPage() {
  return <main className="contact-page">
    <header className="topbar"><Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link><nav aria-label="实验日志导航"><Link href="/research-agenda">研究路线</Link><Link href="/resource-budget-v0-1">B12</Link><a href="#entries">日志</a><a href="#rules">规则</a></nav><span className="edition contact-edition">Real Blender Journal</span></header>
    <section className="contact-hero"><div className="contact-grid" aria-hidden="true" /><div className="contact-hero-copy"><p className="eyebrow"><span /> CONTINUOUS REAL-BLENDER LAB RECORD</p><h1>理论先写成假设。<br /><span>让真实 Blender 决定结论。</span></h1><p>实验对象是本机 Blender 5.2.0 LTS build `fbe6228777e7`，运行在 Apple M4 Max / 48 GiB。日志区分回填证据与现场实验；没有 manifest、哈希、几何测量或反例，就不写“已经解决”。</p></div><aside className="contact-gate"><b>LAB POLICY</b><strong>EVIDENCE<br />BEFORE CLAIM</strong><code>real .blend inputs</code><code>real Blender child processes</code><small>negative results stay published</small></aside><div className="contact-stats"><article><strong>5.2 LTS</strong><span>真实 Blender</span><small>fbe6228777e7</small></article><article><strong>38</strong><span>日志条目</span><small>retrospective + live</small></article><article><strong>48 GiB</strong><span>实验主机内存</span><small>Apple M4 Max</small></article><article><strong>ACES 2</strong><span>固定 OCIO</span><small>SHA verified</small></article></div></section>
    <section className="section contact-diagnostic" id="entries"><div className="section-index">00 / 记录</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> HYPOTHESIS · RUN · OBSERVATION</p><h2>保留失败，<br /><span>不重写历史。</span></h2></div><p>每条结论都能回到仓库中的 JSON、manifest、`.blend` 或协议。B06 的失败没有被隐藏，而是直接改变了 B07/B08 的架构：由“每次重算”转为“审核后固定回放”。</p></div><ol className="contact-negative-list">{entries.map(([id,item,observed,result]) => <li key={id}><span>{id}</span><b>{item}</b><code>{observed}</code><small>{result}</small></li>)}</ol></section>
    <section className="section contact-contract" id="rules"><div className="section-index">01 / 日志合同</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> SEVEN REQUIRED FIELDS</p><h2>每次实验必须留下，<br /><span>下一位研究者能复跑的东西。</span></h2></div><p>假设、预注册门槛、真实运行时身份、正反观察、被证伪的假设、机器可读证据路径、下一边界，缺一项就仍是工作笔记而不是晋级结论。</p></div><div className="contact-boundary"><b>REQUIRED</b><span>hypothesis</span><span>frozen gate</span><span>runtime identity</span><span>negative evidence</span><strong>NEXT OPEN BOUNDARY</strong></div></section>
    <section className="section contact-limits"><div className="section-index">02 / 最新结果</div><div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> B33 · CONSECUTIVE-FRAME Q8 HOLDOUT</p><h2>静态曲线之后。<br /><span>连续时间代理也过门。</span></h2></div><p>frame 74–81 使用 28 个新 PID / 224 EXR。Q8 motion mean 0.9497× NATURAL、max 1.0397×；Q8/Q4 全局最坏 0.7386，距离 0.75 门仅 0.0114。12/12 attacks 通过，但可见闪烁与电影感仍等待独立人类。</p></div><div className="contact-artifacts"><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/RESEARCH_CHARTER.md"><span>CHARTER</span><b>目标实验精神 ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/lab-journal.md"><span>FULL JOURNAL</span><b>完整文字记录 ↗</b></a><Link href="/quadrature-temporal-holdout-v0-1"><span>B33 RESULT</span><b>temporal proxy + margins →</b></Link><Link href="/research-agenda"><span>AGENDA</span><b>human boundary →</b></Link></div></section>
    <footer><div><span className="brand-mark">BFS</span><b>Real Blender Lab Journal</b></div><p>Blender 5.2 LTS · evidence is append-only in spirit</p><Link href="/">返回研究首页 →</Link></footer>
  </main>;
}
