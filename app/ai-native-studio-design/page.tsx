import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'AI Native Film Studio 设计文档｜BlenderFilmStudio',
  description: '基于 Blender 官方开源内核的新一代 AI 原生电影软件：产品定义、架构、既有证据、许可证边界、源码介入策略与可证伪路线。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-design/' },
  openGraph: {
    title: 'AI Native Film Studio · Design Doc v0.1',
    description: '从“AI 操作 Blender”升级为“Blender 内核上的 AI 原生电影软件”。',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/ai-native-studio-design/',
  },
  twitter: { card: 'summary_large_image', title: 'AI Native Film Studio · Design Doc v0.1', description: '产品、架构、证据、GPL 边界与源码可行性 Gate。' },
};

const evidence = [
  {
    id: 'E01', title: '电影意图可以编译', state: 'SUPPORTED', tone: 'pass',
    result: 'SceneSpec、ActorSpec 与不可变 BuildPlan 已形成机器合同；B01/B02 canonical structure 可复现，B43 的 Codex structured intent 与冻结 oracle canonical exact。',
    product: '把 SceneSpec / BuildPlan 内嵌为产品持久 API，而不是继续生成任意 Python。',
  },
  {
    id: 'E02', title: '多镜头共享状态可守住', state: 'SUPPORTED', tone: 'pass',
    result: 'B60 在真实 Blender 5.2 中完成 wide / medium / close 各两次独立编译；六次共享人物、表演、场景、灯光和非摄影机状态一致。',
    product: 'Character、Performance、Look 与 Shot 必须是独立层，摄影机变化不能污染共享状态。',
  },
  {
    id: 'E03', title: '像素与生产通道可审计', state: 'SUPPORTED · BOUNDED', tone: 'pass',
    result: 'B45–B47 将结构推进到 float pixels、连续序列与 multilayer EXR；B61 的 9/9 关键帧 A/B 解码 Combined exact，但 EXR 容器字节不同。',
    product: '以 decoded pixel / pass semantics 定义身份，不以文件容器 hash 冒充画面一致。',
  },
  {
    id: 'E04', title: '成本必须实测', state: 'MEASURED', tone: 'measure',
    result: 'B48 选择 128 spp raw 作为冻结质量门下的最低支持点；B61 的 1080p / 64 spp CPU 样本均值 6.084 秒/帧、峰值 RSS 约 4.5 GB。',
    product: '每次 Preview / Final 请求在批准前显示预计时间、内存、磁盘和失效范围。',
  },
  {
    id: 'E05', title: '恢复与失败需要产品化', state: 'SUPPORTED · NARROW', tone: 'pass',
    result: 'B53–B58 建立准入、原生 PID、JIT 磁盘门、job manifest、stage receipt、失败保留与独立再审计；差一字节时 Blender 零启动。',
    product: 'Job Ledger 和 Evidence Explorer 是核心界面，不是藏在日志目录里的开发工具。',
  },
  {
    id: 'E06', title: '技术通过不等于电影通过', state: 'SCIENTIFIC REJECTION RETAINED', tone: 'reject',
    result: 'B62 已完成 12 秒 / 288 帧 / 三镜头 animatic 与 Cycles 校准；最新 camera holdout 18/18 技术门通过，仍因 frame 288 构图越过冻结阈值而拒绝。',
    product: '机器验收与导演审片并列；系统不得自动放宽阈值来制造成功。',
  },
];

const principles = [
  ['01', '电影对象优先', '项目、场次、镜头、人物、表演和连续性优先于 Object 与 Operator。'],
  ['02', 'AI 提案，不直接执行', '模型提交 typed patch、影响范围和风险；编译器决定是否可执行。'],
  ['03', '每个改变都有差异', '执行前显示 SceneSpec diff、失效依赖、预估成本与审批范围。'],
  ['04', '失败是一等状态', '失败 root 永久保留；correction 必须绑定旧证据，不能覆盖历史。'],
  ['05', '默认简单，能力可达', '普通用户使用电影工作台；Expert Mode 保留完整 Blender 编辑器。'],
  ['06', '薄分叉', '只有被实验证明无法从 Python 或进程边界可靠实现的能力才修改核心。'],
];

const models = [
  ['ProjectSpec', '全局合同', '帧率、色彩、交付、预算与安全政策'],
  ['CharacterBible', '身份合同', '资产版本、比例、rig、材质、造型与允许变体'],
  ['SceneSpec', '世界意图', '资产、关系、表演、灯光、时间与输出'],
  ['ShotSpec', '摄影意图', '构图、焦段、轨迹、焦点、可见性与剪辑关系'],
  ['PerformanceSpec', '表演分层', '身体、面部、视线、呼吸、接触与 override'],
  ['BuildPlan', '不可变执行计划', '解析后的稳定顺序、精确参数、依赖和资源预测'],
  ['JobManifest', '耐久状态机', '阶段、预算、恢复点、尝试与晋级状态'],
  ['Receipt', '事实记录', '输入身份、进程、产物、测量、失败和自哈希'],
];

const sourceLevels = [
  ['L1', '发行版与工作区', '独立名称、图标、bundle id、配置目录、Film Workspace 与 Expert Mode。', 'Python / configuration first'],
  ['L2', '原生 Film Editor', 'Shot graph、proposal diff、job ledger、evidence viewer；通过 RNA 暴露持久状态。', 'C/C++ editor only when proven'],
  ['L3', '稳定执行 hooks', '无 UI 上下文操作、事务、取消、结构快照、渲染事件与恢复。', 'minimal core patch surface'],
  ['L4', '核心算法变化', '仅处理上游没有且独立模块无法实现的求值或渲染能力。', 'exception · explicit merge cost'],
];

const workflow = [
  ['01', '提出', '剧本、参考、资产或自然语言修改'],
  ['02', '解释', 'AI 生成意图、缺口与备选方案'],
  ['03', '比较', 'SceneSpec patch、影响范围、风险与成本'],
  ['04', '批准', '用户锁定 revision 与审批范围'],
  ['05', '编译', 'BuildPlan、语义验证、资源和安全准入'],
  ['06', '执行', '受限 Blender 进程、preview / EXR / passes'],
  ['07', '审查', '机器门、人审、差异、失败与恢复'],
];

const gates = [
  ['F0.1', '源码构建', '固定官方 Blender stable/LTS commit，在当前 Apple Silicon Mac 形成可重复 binary 与构建收据。', 'PASS'],
  ['F0.2', '独立身份', '新名称、bundle id、图标、启动画面和配置目录；不把 Blender 商标作为产品名。', 'PASS'],
  ['F0.3', '电影工作台', '最小 Project / Scene / Shot / Character 界面可用，且能进入 Expert Mode。', 'PASS'],
  ['F0.4', '合同内嵌', 'BuildPlan canonical exact；B01/B02 隔离构建与 semantic/provenance 独立审计通过。', 'PASS'],
  ['F0.5', '渲染与收据', '无鼠标完成 EEVEE preview、Cycles EXR、像素/成本/失败收据。', 'PASS'],
  ['F0.6', '上游合并演练', 'v5.2.1：0 冲突路径、0 人工小时、909 行 patch；F0.1–F0.5 回归通过。', 'PASS'],
  ['F0.7', '安装与往返', 'unsigned DMG 可验证；隔离安装/卸载、双向 `.blend` 往返和配置边界通过。', 'PASS'],
];

const risks = [
  ['R1', '分叉债务', '高', '固定 LTS、薄 patch、merge drill、优先把通用修复贡献上游。'],
  ['R2', 'GPL / 商标边界', '高', '引擎侧默认公开；独立品牌；商业发布前做专业许可证审查。'],
  ['R3', 'UI 只是换皮', '高', '以电影对象、typed action 和任务状态机验收，而不是隐藏按钮数量。'],
  ['R4', 'AI 越权', '高', '模型无 unrestricted bpy/shell；schema、semantic gate、approval 和隔离强制执行。'],
  ['R5', '资产与表演瓶颈', '高', '第一版锁定人工整理资产；明确不承诺任意真人近景。'],
  ['R6', '跨硬件差异', '中', '拆分同机 exact、跨后端 semantic、跨平台 perceptual 三层合同。'],
  ['R7', '成本和磁盘失控', '中', 'JIT capacity、quota、内容寻址缓存、保留政策和执行前预测。'],
  ['R8', '研究无限扩张', '中', '每阶段必须以可观看垂直切片或明确证伪结束。'],
];

const sources = [
  ['Blender Foundation', 'Blender License：允许使用、修改、分发和销售；分发修改版需遵守 GPL', 'https://www.blender.org/about/license/'],
  ['Blender Foundation', 'Trademark Policy：fork 应使用独立名称与品牌', 'https://www.blender.org/about/trademark-policy/'],
  ['Blender', '官方源代码仓库：完整 3D pipeline 与 GPL-3.0 整体许可说明', 'https://projects.blender.org/blender/blender/src/branch/main'],
  ['Blender Developer Docs', 'Building Blender：CMake、跨平台构建与测试', 'https://developer.blender.org/docs/handbook/building_blender/'],
  ['Blender Developer Docs', 'Build Options：full、headless 与 bpy build targets', 'https://developer.blender.org/docs/handbook/building_blender/options/'],
  ['Blender Developer Docs', 'RNA：连接数据、UI、动画、override 与 Python API 的反射系统', 'https://developer.blender.org/docs/features/core/rna/'],
  ['Blender Developer Docs', 'Code Layout：editors、DNA/RNA、Python、nodes 与 render 等源码边界', 'https://developer.blender.org/docs/features/code_layout/'],
  ['Blender Developer Docs', 'Release Cycle：约四个月一版、每年一个两年 LTS', 'https://developer.blender.org/docs/handbook/release_process/release_cycle/'],
  ['Bforartists', '完整 Blender fork：UI 重构、`.blend` 兼容与上游维护样本', 'https://github.com/Bforartists/Bforartists'],
  ['GNU Project', 'GPL FAQ：插件、组合程序与进程/管道/socket 边界说明', 'https://www.gnu.org/licenses/gpl-faq.html.en'],
];

export default function AiNativeStudioDesignPage() {
  return (
    <main className="ain-page">
      <header className="topbar ain-topbar">
        <Link className="brand" href="/" aria-label="返回研究首页"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="AI Native Studio 设计导航"><Link href="/ai-native-studio-handoff">新机器交接</Link><a href="#decision">决策</a><a href="#evidence">已有证据</a><a href="#architecture">架构</a><a href="#experience">产品</a><a href="#source">源码</a><a href="#license">许可</a><a href="#gates">F0</a><Link href="/journal">实验日志</Link></nav>
        <span className="edition ain-edition">Direction · ADR-001</span>
      </header>

      <section className="ain-hero" id="top">
        <div className="ain-hero-grid" aria-hidden="true" />
        <div className="ain-hero-copy">
          <p className="eyebrow"><span /> DESIGN DOC v0.1 · 2026.08.29</p>
          <h1>不再教 AI<br />操作 Blender。<br /><span>让 Blender 成为<br />我们的电影内核。</span></h1>
          <p>一个独立品牌、GPL 合规、AI 原生的电影制作软件：用户表达镜头与表演意图，AI 提交可审查的结构化计划，确定性内核编译、渲染、恢复并留下证据。</p>
          <div className="ain-hero-actions"><a href="#decision">阅读设计决策 ↓</a><a href="#gates">查看源码可行性门</a></div>
        </div>
        <aside className="ain-decision-card">
          <header><span>ADR-001</span><b>ADOPTED DIRECTION</b></header>
          <strong>DIRECT BLENDER<br />THIN FORK</strong>
          <dl><div><dt>内核</dt><dd>Blender official source</dd></div><div><dt>参照</dt><dd>Bforartists UI fork</dd></div><div><dt>控制</dt><dd>typed intent + receipts</dd></div><div><dt>模型</dt><dd>Codex / local / API adapters</dd></div></dl>
          <footer>Direction adopted ≠ implementation proven</footer>
        </aside>
        <div className="ain-stats">
          <article><strong>483</strong><span>真实实验日志编号</span><small>负结果同样保留</small></article>
          <article><strong>B01–B62</strong><span>符合性证据范围</span><small>结构 → 像素 → 恢复 → 镜头</small></article>
          <article><strong>4</strong><span>产品平面</span><small>体验 · 意图 · 引擎 · 证据</small></article>
          <article><strong>7</strong><span>源码可行性门</span><small>全部通过才正式立项</small></article>
        </div>
      </section>

      <section className="section ain-decision" id="decision">
        <div className="section-index">00 / EXECUTIVE DECISION</div>
        <div className="ain-section-heading"><div><p className="eyebrow dark"><span /> THE NEW DIRECTION</p><h2>做自己的软件，<br />但<span>不重写成熟世界。</span></h2></div><p>我们继承 Blender 的数据、动画、节点、求值、渲染与文件能力，重写用户与系统之间的“意图层”。现有 workflow 不被废弃，而被提升为新产品的执行内核与符合性测试。</p></div>
        <div className="ain-decision-grid">
          <article className="selected"><span>01 · SELECTED</span><h3>Blender 官方源码<br />薄分叉</h3><p>最短上游链、最大源码控制；核心改动保持最小，先从工作区和协议内嵌开始。</p><b>默认基线</b></article>
          <article><span>02 · REFERENCE</span><h3>Bforartists<br />作为研究样本</h3><p>证明独立发行和 UI 重构可行；借鉴其设计与合并经验，不增加第二层上游。</p><b>选择性借鉴</b></article>
          <article><span>03 · FALLBACK</span><h3>外部 Studio Shell<br />驱动未修改引擎</h3><p>若源码合并或发行成本越门，退回清晰进程边界，牺牲部分原生体验换取维护性。</p><b>F0 失败时启用</b></article>
        </div>
        <div className="ain-not-chat"><b>AI-NATIVE ≠ CHAT PANEL</b><p>真正的 AI 原生意味着 typed schema、revision、diff、权限、预算、恢复、证据和人类批准都进入产品主路径。聊天只是输入方式之一。</p></div>
      </section>

      <section className="section ain-evidence" id="evidence">
        <div className="section-index light">01 / INHERITED EVIDENCE</div>
        <div className="ain-section-heading light"><div><p className="eyebrow"><span /> RESEARCH BECOMES PRODUCT</p><h2>不是重新开始。<br /><span>483 条日志成为测试资产。</span></h2></div><p>每一项“支持”都有范围；每一项“拒绝”都限制产品承诺。新软件第一天就继承真实 Blender 行为、失败路径和冻结阈值，而不是从演示开始。</p></div>
        <div className="ain-evidence-list">{evidence.map(item => <article className={item.tone} key={item.id}><aside><span>{item.id}</span><b>{item.state}</b></aside><div><h3>{item.title}</h3><p>{item.result}</p><footer><span>产品化结论</span><strong>{item.product}</strong></footer></div></article>)}</div>
        <div className="ain-boundary"><strong>当前最重要的边界</strong><p>B62 的技术执行链已经很强，但最新镜头留出实验仍被构图门拒绝。新方向不能把“拥有 Blender 源码”误写成“电影审美已经自动解决”。源码控制让我们更准确地表达和检查意图，不替代导演。</p><Link href="/b62-camera-quality-holdout-v0-1">查看 B62 Camera Q1 负结果 →</Link></div>
      </section>

      <section className="section ain-principles">
        <div className="section-index">02 / PRODUCT PRINCIPLES</div>
        <div className="ain-section-heading"><div><p className="eyebrow dark"><span /> RULES BEFORE FEATURES</p><h2>先决定软件<br /><span>永远不该变成什么。</span></h2></div><p>这些规则约束 UI、协议和底层代码。功能如果破坏它们，就算看起来更“智能”，也不能进入生产路径。</p></div>
        <div className="ain-principle-grid">{principles.map(([id,title,detail]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
        <div className="ain-nongoals"><span>NON-GOALS</span><ul><li>一句话自动生成完整长片</li><li>从零重写 3D / render engine</li><li>任意 AI Python / shell 执行</li><li>用像素指标替代电影判断</li><li>隐藏按钮后称为新产品</li><li>承诺任意真人近景已解决</li></ul></div>
      </section>

      <section className="section ain-architecture" id="architecture">
        <div className="section-index light">03 / SYSTEM ARCHITECTURE</div>
        <div className="ain-section-heading light"><div><p className="eyebrow"><span /> FOUR PLANES · HARD BOUNDARIES</p><h2>模型负责理解。<br />内核负责<span>证明与执行。</span></h2></div><p>AI 与 Blender 不共享无限权力。它们通过版本化协议合作，任务状态和事实证据独立于任何一次界面或进程的生命期。</p></div>
        <div className="ain-architecture-map" aria-label="AI Native Film Studio 四平面架构">
          <article className="experience"><span>A · EXPERIENCE</span><h3>Film Studio UI</h3><p>Project · Story · Shot · Character · Dailies</p><small>默认电影工作台 / Expert Mode</small></article>
          <i>↓</i>
          <article className="intent"><span>B · INTENT & CONTROL</span><h3>AI Control Plane</h3><p>Codex · Local model · API adapters</p><small>proposal · typed patch · diff · approval</small></article>
          <i>↓</i>
          <article className="engine"><span>C · DETERMINISTIC ENGINE</span><h3>GPL Blender Distribution</h3><p>validator · compiler · admission · executor · audit</p><small>Blender Core · Cycles · EEVEE · compositor</small></article>
          <i>↓</i>
          <article className="evidence"><span>D · EVIDENCE</span><h3>Immutable Production Graph</h3><p>spec · plan · assets · cache · EXR · receipts</p><small>resume from bytes, not UI memory</small></article>
        </div>
        <div className="ain-processes"><article><span>studio-ui</span><p>电影工作台与审批</p></article><article><span>model-adapter</span><p>独立模型连接器</p></article><article><span>job-supervisor</span><p>预算、进程与恢复</p></article><article><span>engine-host</span><p>受限 Blender 执行</p></article><article><span>auditor</span><p>独立只读重算</p></article></div>
      </section>

      <section className="section ain-experience" id="experience">
        <div className="section-index">04 / PRODUCT EXPERIENCE</div>
        <div className="ain-section-heading"><div><p className="eyebrow dark"><span /> A FILM DESK, NOT A DCC MAZE</p><h2>用户从镜头出发，<br />而不是从<span>Cube 出发。</span></h2></div><p>默认界面围绕“要拍什么、哪里不一致、下一步会花多少”组织。完整 Blender 工具仍然存在，但不再决定普通用户的工作路径。</p></div>
        <div className="ain-ui-frame" aria-label="AI Native Film Studio 概念界面">
          <header><span>PROJECT · REMAINDER</span><nav><b>PROPOSE</b><b>REVIEW</b><b>APPROVE</b><b>BUILD PREVIEW</b><b>RENDER FINAL</b></nav><i>REV 42 · CLEAN</i></header>
          <aside><b>STORY</b><span>SC 01 · The room</span><small>SH 010 · WIDE</small><small className="active">SH 020 · CLOSE</small><small>SH 030 · EXIT</small><b>CAST</b><span>Guardian</span><b>ASSETS</b><span>Room v07</span></aside>
          <div className="ain-viewport"><div><span>SHOT 020 · CAMERA PREVIEW</span><b>85 mm · f/2.8 · 24 fps</b></div><figure><i /><i /><i /><span>SAFE FRAME</span><strong>ACTOR</strong></figure></div>
          <section><b>INTENT INSPECTOR</b><dl><div><dt>Purpose</dt><dd>Reveal hesitation</dd></div><div><dt>Continuity</dt><dd>Lock actor + key light</dd></div><div><dt>Movement</dt><dd>0.6 m slow push</dd></div><div><dt>Focus</dt><dd>Eyes · 3.18 m</dd></div></dl><button>Review proposed patch</button></section>
          <footer><b>JOB LEDGER</b><span className="done">✓ plan</span><span className="done">✓ admission</span><span className="run">● preview 63%</span><span>○ machine review</span><span>○ human approval</span><i>+2.1 GiB · est. 00:18</i></footer>
        </div>
        <div className="ain-workflow">{workflow.map(([id,title,detail],index) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p>{index < workflow.length - 1 && <i>→</i>}</article>)}</div>
      </section>

      <section className="section ain-data">
        <div className="section-index light">05 / DATA MODEL</div>
        <div className="ain-section-heading light"><div><p className="eyebrow"><span /> THE PRODUCT IS ITS CONTRACTS</p><h2>界面可以变化。<br /><span>身份和语义不能漂移。</span></h2></div><p>持久对象定义产品真正能理解和恢复的内容。`.blend` 仍是重要派生产物，但不再承担全部业务语义和身份责任。</p></div>
        <div className="ain-model-grid">{models.map(([name,kind,detail]) => <article key={name}><span>{kind}</span><h3>{name}</h3><p>{detail}</p></article>)}</div>
        <div className="ain-identity-rules"><b>IDENTITY RULES</b><p>canonical typed data 定义合同身份</p><i>≠</i><p>.blend container bytes</p><i>·</i><p>decoded pixel digest</p><i>≠</i><p>EXR container hash</p><i>·</i><p>binary32 / binary64 必须显式声明</p></div>
      </section>

      <section className="section ain-source" id="source">
        <div className="section-index">06 / SOURCE INTERVENTION</div>
        <div className="ain-section-heading"><div><p className="eyebrow dark"><span /> CHANGE THE SMALLEST CORRECT LAYER</p><h2>拥有全部代码，<br />不代表要<span>修改全部代码。</span></h2></div><p>源码控制是安全阀，而不是改动 KPI。每深入一级，都需要一个无法在更浅层可靠解决的实验反例。</p></div>
        <div className="ain-source-levels">{sourceLevels.map(([id,title,detail,policy]) => <article key={id}><aside><span>{id}</span><small>{policy}</small></aside><div><h3>{title}</h3><p>{detail}</p></div></article>)}</div>
        <div className="ain-repo-map"><header><span>REPOSITORY STRATEGY</span><b>研究证据与多 GiB 引擎历史分离</b></header><div><code>BlenderFilmStudio / research + protocols + evidence</code><i>→</i><code>film-studio-engine / Blender thin fork · GPL</code><i>+</i><code>film-studio-control / adapters + services</code></div><footer>Public GitHub fork路线已通过本地full-history rehearsal；外部create/first push仍等待明确授权。</footer></div>
      </section>

      <section className="section ain-license" id="license">
        <div className="section-index light">07 / LICENSE & BUSINESS</div>
        <div className="ain-section-heading light"><div><p className="eyebrow"><span /> OPEN ENGINE · VIABLE BUSINESS</p><h2>可以商业化。<br />不能把衍生内核<span>偷偷闭源。</span></h2></div><p>这是工程设计边界，不是法律意见。发布前仍需针对实际链接、插件、RPC 和分发组合做专业审查。</p></div>
        <div className="ain-license-grid"><article><span>必须 GPL 兼容</span><h3>Engine side</h3><ul><li>修改后的 Blender binary</li><li>内嵌 Film UI / Editor</li><li>直接使用 bpy 的已发布脚本</li><li>相应构建源码与 notices</li></ul></article><article><span>可清晰分离</span><h3>Service side</h3><ul><li>Codex / 本地 / API 模型服务</li><li>账号、团队和托管队列</li><li>远程推理与商业支持</li><li>通过版本化协议通信</li></ul></article><article><span>归用户</span><h3>Creative output</h3><ul><li>.blend 与项目数据</li><li>EXR、图片和视频</li><li>剧本、资产与剪辑</li><li>不因 Blender GPL 自动 GPL</li></ul></article></div>
        <div className="ain-brand-rule"><b>品牌规则</b><p>产品使用独立名称与 Logo；可事实性说明 “Based on Blender”，不能把 Blender 名称或标志作为产品主品牌。最终名称尚未决定。</p></div>
        <div className="ain-business"><span>可持续收入</span><b>模型订阅</b><b>托管渲染</b><b>团队协作</b><b>资产治理</b><b>企业支持</b><b>认证发行版</b></div>
      </section>

      <section className="section ain-gates" id="gates">
        <div className="section-index">08 / F0 SOURCE FEASIBILITY</div>
        <div className="ain-section-heading"><div><p className="eyebrow dark"><span /> PROVE THE FORK BEFORE COMMITTING TO IT</p><h2>七道门关闭前，<br />它仍是<span>方向，不是能力。</span></h2></div><p>第一个工程里程碑不是漂亮界面，而是证明我们能构建、重品牌、内嵌合同、渲染、合并上游并交付安装包。</p></div>
        <div className="ain-gate-list">{gates.map(([id,title,detail,status]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p><b>{status}</b></article>)}</div>
        <div className="ain-stop-rule"><span>STOP / FALLBACK RULE</span><p>如果上游合并成本、签名发行或核心 patch surface 超过冻结门槛，架构退回“外部 Studio Shell + 未修改 Blender engine”。失败会改变设计，而不是被愿景忽略。</p></div>
      </section>

      <section className="section ain-roadmap">
        <div className="section-index light">09 / PHASED DELIVERY</div>
        <div className="ain-section-heading light"><div><p className="eyebrow"><span /> VERTICAL SLICE BEFORE PLATFORM</p><h2>每个阶段都必须<br /><span>产出证据或可观看结果。</span></h2></div><p>不以功能数量衡量进度。第一条用户价值链始终是：意图 → 三镜头 → preview → 审片 → EXR → 可恢复交付。</p></div>
        <div className="ain-roadmap-line"><article><span>A</span><h3>Source Feasibility</h3><p>关闭 F0，选择正式基线。</p><b>build / identity / merge / package</b></article><article><span>B</span><h3>AI-native Shell</h3><p>电影工作台与 typed proposal。</p><b>B01/B02 + B62 slice</b></article><article><span>C</span><h3>Production Control</h3><p>准入、预算、恢复和审计。</p><b>B53–B59 embedded</b></article><article><span>D</span><h3>Cinematic Slice</h3><p>三镜头、EXR、人审与交付。</p><b>one watchable proof</b></article><article><span>E</span><h3>Generalization</h3><p>全新角色、场景与风格留出。</p><b>only then expand</b></article></div>
      </section>

      <section className="section ain-risks">
        <div className="section-index">10 / RISK REGISTER</div>
        <div className="ain-section-heading"><div><p className="eyebrow dark"><span /> DESIGN FOR FAILURE</p><h2>最大风险不是做不出来，<br />而是做出一个<span>无法维护的 demo。</span></h2></div><p>风险在立项时进入设计，而不是上线前补写。每项缓解措施都必须最终变成测试、政策或发布门。</p></div>
        <div className="ain-risk-table"><header><span>ID</span><span>风险</span><span>级别</span><span>缓解</span></header>{risks.map(([id,risk,level,mitigation]) => <article key={id}><span>{id}</span><b>{risk}</b><strong>{level}</strong><p>{mitigation}</p></article>)}</div>
      </section>

      <section className="section ain-sources" id="sources">
        <div className="section-index light">11 / PRIMARY SOURCES</div>
        <div className="ain-section-heading light"><div><p className="eyebrow"><span /> RESEARCH BASIS</p><h2>许可证决定边界。<br /><span>真实实验决定主张。</span></h2></div><p>外部来源用于确认源码、构建、架构、商标和许可证；产品可靠性结论只来自本仓库冻结协议下的真实 Blender 实验。</p></div>
        <ol className="ain-source-list">{sources.map(([author,title,href],index) => <li key={href}><span>{String(index + 1).padStart(2,'0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
        <div className="ain-next"><span>NEXT AUTHORIZED RESEARCH</span><div><h3>PUBLIC FORK CREATION · EXPLICIT AUTHORIZATION</h3><p>Repository-readiness C2 attempt-03 已完成 exact local full-history rehearsal：162,917 commits、8/8负控、93/93独立audit，external writes为0。授权请求现在明示 owner `lovejzzz`、public `film-studio-engine` fork、只上传2个fork-owned LFS objects（2,701,144 bytes并接受可能计费），以及只对fresh无owner commit的generated main执行OID-bound `--force-with-lease`。Private standalone、release、签名、公证、DMG distribution与Phase B仍未授权。</p><Link href="/ai-native-studio-handoff">打开授权边界 →</Link></div></div>
      </section>

      <footer className="ain-footer"><div><span className="brand-mark">BFS</span><b>AI Native Film Studio · Design Doc v0.1</b></div><p>Direction adopted · Implementation gated · Snapshot 2026-08-29</p><Link href="/ai-native-studio-handoff">新机器从这里开始 →</Link></footer>
    </main>
  );
}
