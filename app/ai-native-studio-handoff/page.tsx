import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: '新机器交接｜AI Native Film Studio',
  description: '让另一台机器上的 Codex 从同一个事实快照、源码基线与 F0 实验协议立即开始。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-handoff/' },
  openGraph: {
    title: 'AI Native Film Studio · New Machine Handoff',
    description: '一个仓库、一个事实快照、七道源码可行性门。',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-handoff/',
  },
};

const gates = [
  ['F0.1', '源码复现', '两次 clean build + 负控', 'PASS'],
  ['F0.2', '独立身份', '名称 / bundle / config 隔离', 'PASS'],
  ['F0.3', '电影工作台', 'Project / Scene / Shot / Character', 'PASS'],
  ['F0.4', '合同内嵌', 'canonical exact；OCIO build gate failed', 'FAIL / RETRY'],
  ['F0.5', '渲染收据', 'EEVEE / Cycles / resume / audit', 'LOCKED'],
  ['F0.6', '合并演练', '10 paths / 8 h / 5000 LOC ceiling', 'LOCKED'],
  ['F0.7', '安装往返', 'package / identity / .blend', 'LOCKED'],
];

const documents = [
  ['01', 'START_HERE.md', '人类与 Codex 的统一入口；30 分钟启动顺序、禁区与下一 checkpoint。', 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/START_HERE.md'],
  ['02', 'AGENTS.md', '自动生效的操作目标、证据纪律、磁盘政策与浏览器崩溃保护。', 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/AGENTS.md'],
  ['03', 'current-state.json', '机器可读的当前决策、版本、gate 状态、命令和禁止事项。', 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/handoff/ai-native-studio-current-state.v0.1.json'],
  ['04', 'F0 protocol', '完整预注册：竞争假设、固定输入、资源门、负控和停止规则。', 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/2026-08-29-ai-native-film-studio-f0-source-feasibility-protocol-v0.1.zh-CN.md'],
  ['05', 'F0 spec.json', '七道门的机器验收合同、证据清单和 fallback trigger。', 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/specs/ai-native-studio-f0.v0.1.json'],
  ['06', 'Design Doc v0.1', '产品、架构、GPL 边界、已有研究与长期路线。', 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/research/2026-08-29-ai-native-film-studio-design-v0.1.zh-CN.md'],
];

const inherited = [
  ['B01–B43', '意图与结构', 'SceneSpec、ActorSpec、BuildPlan 与 Codex structured intent 已形成确定性合同。'],
  ['B44–B48', '执行到像素', '真实 worker、连续帧、EXR production passes 与质量—成本门已验证。'],
  ['B53–B59', '安全与恢复', '准入、原生 PID、JIT disk、manifest、receipt 与 crash recovery 已形成资产。'],
  ['B60–B62', '电影边界', '多镜头共享状态成立；最新构图 holdout 技术通过但电影质量仍被拒绝。'],
];

export default function AiNativeStudioHandoffPage() {
  return (
    <main className="handoff-page">
      <header className="topbar handoff-topbar">
        <Link className="brand" href="/" aria-label="返回研究首页"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="交接导航"><a href="#start">开始</a><a href="#gates">F0 Gates</a><a href="#map">仓库地图</a><a href="#evidence">继承证据</a><Link href="/ai-native-studio-design">设计文档</Link></nav>
        <span className="edition handoff-edition">Cold Start · v0.1</span>
      </header>

      <section className="handoff-hero" id="top">
        <div className="handoff-grid" aria-hidden="true" />
        <div className="handoff-hero-copy">
          <p className="eyebrow"><span /> NEW MACHINE HANDOFF · 2026.08.29</p>
          <h1>换一台电脑，<br />不换一套<span>事实。</span></h1>
          <p>F0.1–F0.3 已在 M2 Max 主机通过。F0.4 attempt-01 又证明了内嵌 B01/B02 BuildPlan canonical exact 与四项负控，但首个隔离 B01 build 因 OCIO config name 为空而正式 FAIL。新的 Codex 只能从交叉绑定该失败的新 evidence root 继续。</p>
          <div className="handoff-hero-actions"><a href="#start">开始交接 ↓</a><Link href="/ai-native-studio-design">为什么做自己的软件</Link></div>
        </div>
        <aside className="handoff-state">
          <header><span>PROGRAM STATE</span><b>F0.4 ATTEMPT-01 FAIL</b></header>
          <div className="handoff-state-main"><small>ACTIVE CORRECTION</small><strong>F0.4</strong><h2>OCIO-BOUND<br />RETRY</h2></div>
          <dl><div><dt>ENGINE</dt><dd>Film Studio Engine F0</dd></div><div><dt>COMMIT</dt><dd>b47eae224b6d</dd></div><div><dt>HOST</dt><dd>macOS · M2 Max</dd></div><div><dt>RESULT</dt><dd>2 exact · build FAIL</dd></div></dl>
          <footer>FORK IS A HYPOTHESIS · NOT A CONCLUSION</footer>
        </aside>
        <div className="handoff-signal"><span>01</span><b>读取规则</b><i>→</i><span>02</span><b>只读预检</b><i>→</i><span>03</span><b>固定源码</b><i>→</i><span>04</span><b>保存证据</b></div>
      </section>

      <section className="handoff-start" id="start">
        <div className="section-index">00 / FIRST 30 MINUTES</div>
        <div className="handoff-heading"><div><p className="eyebrow dark"><span /> ONE SAFE ENTRY</p><h2>第一步不是编译。<br />先确认这台机器<span>有资格编译。</span></h2></div><p>预检只读取主机状态，不安装、不下载、不改配置。它同时检查平台、架构、内存、磁盘和构建工具；不满足条件就保留拒绝，而不是硬跑到磁盘再次爆满。</p></div>
        <div className="handoff-command"><header><span>READ-ONLY HOST ADMISSION</span><b>NO WRITES · NO CLONE · NO BLENDER</b></header><code><span>$</span> node scripts/preflight-f0-source-host.mjs</code><footer><b>PASS</b><span>≥160 GiB free · macOS arm64 · toolchain ready</span><i>then preview bootstrap</i></footer></div>
        <div className="handoff-steps">
          <article><span>01</span><h3>读入口</h3><code>START_HERE.md</code><p>确认目标与禁区，不从旧 B62 继续。</p></article>
          <article><span>02</span><h3>做预检</h3><code>preflight-f0-source-host.mjs</code><p>先获得 ACCEPTED 或 BLOCKED 事实。</p></article>
          <article><span>03</span><h3>预览 bootstrap</h3><code>--workspace /absolute/path</code><p>源码永远放在研究仓库之外。</p></article>
          <article><span>04</span><h3>建立 correction root</h3><code>F0.4-…-attempt-02</code><p>交叉绑定 attempt-01，冻结 OCIO 环境。</p></article>
        </div>
      </section>

      <section className="handoff-gates" id="gates">
        <div className="section-index light">01 / SOURCE FEASIBILITY</div>
        <div className="handoff-heading light"><div><p className="eyebrow"><span /> SEVEN GATES · ONE DECISION</p><h2>全部关闭，才有资格<br />建立<span>正式引擎仓库。</span></h2></div><p>这不是七项功能清单，而是七个能推翻 thin fork 的实验。失败本身可接受；隐藏失败、挪动阈值或无限扩大 patch 不可接受。</p></div>
        <div className="handoff-gate-list">{gates.map(([id,title,detail,status],index) => <article className={index === 3 ? 'active' : ''} key={id}><span>{id}</span><div><h3>{title}</h3><p>{detail}</p></div><b>{status}</b></article>)}</div>
        <div className="handoff-fork"><article><span>ALL PASS</span><h3>THIN FORK</h3><p>进入独立引擎产品原型；仍维持最小核心 patch。</p></article><i>OR</i><article><span>CEILING EXCEEDED</span><h3>EXTERNAL SHELL</h3><p>保留电影体验和 typed protocol，使用未修改 Blender。</p></article></div>
      </section>

      <section className="handoff-map" id="map">
        <div className="section-index">02 / REPOSITORY MAP</div>
        <div className="handoff-heading"><div><p className="eyebrow dark"><span /> SIX AUTHORITATIVE FILES</p><h2>给人看的解释，<br />和给机器读的<span>状态同样重要。</span></h2></div><p>入口、设计、实验协议与机器规范各司其职。状态变化时必须同步，而不是只在聊天记录里留下一个新方向。</p></div>
        <div className="handoff-docs">{documents.map(([id,title,detail,href]) => <a href={href} target="_blank" rel="noreferrer" key={id}><span>{id}</span><div><h3>{title}</h3><p>{detail}</p></div><b>OPEN ↗</b></a>)}</div>
        <div className="handoff-storage"><span>REPOSITORY BOUNDARY</span><div><code>BlenderFilmStudio</code><b>rules · protocols · evidence · site</b></div><i>≠</i><div><code>external F0 workspace</code><b>source · dependencies · builds</b></div></div>
      </section>

      <section className="handoff-evidence" id="evidence">
        <div className="section-index light">03 / INHERITED WORK</div>
        <div className="handoff-heading light"><div><p className="eyebrow"><span /> KEEP THE KNOWLEDGE · CHANGE THE GOAL</p><h2>旧流程没有作废。<br />它变成新软件的<span>测谎仪。</span></h2></div><p>B01–B62 不再驱动研究方向，却会验证新内核是否破坏我们已经赢得的确定性、安全性和像素证据。</p></div>
        <div className="handoff-inherited">{inherited.map(([range,title,detail]) => <article key={range}><span>{range}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
        <div className="handoff-warning"><b>DO NOT CLAIM</b><p>拥有源码不等于人物、表演、资产和电影判断已经自动化。B62 的构图拒绝必须保留在产品承诺里：技术门通过，仍可能不是一个好镜头。</p></div>
      </section>

      <section className="handoff-checkpoint">
        <span>NEXT PUSH MUST CONTAIN</span>
        <h2>一个被保留的 F0.4 失败。</h2>
        <p>2 canonical-exact BuildPlans · 4 / 4 negative controls · B01 OCIO mismatch · B02 not run · same-ID repair forbidden</p>
        <div><Link href="/journal">查看实验日志 →</Link><a href="https://github.com/lovejzzz/BlenderFilmStudio" target="_blank" rel="noreferrer">打开 GitHub 仓库 ↗</a></div>
      </section>

      <footer className="ain-footer"><div><span className="brand-mark">BFS</span><b>AI Native Film Studio · New Machine Handoff</b></div><p>One repository · One source identity · Seven falsifiable gates</p><Link href="/ai-native-studio-design">返回 Design Doc →</Link></footer>
    </main>
  );
}
