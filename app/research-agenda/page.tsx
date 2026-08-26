import type { Metadata } from 'next';
import Link from 'next/link';

type Priority = 'P0' | 'P1' | 'P2';
type GapType = 'definition' | 'engineering' | 'experiment' | 'governance';

export const metadata: Metadata = {
  title: '研究缺口与实验路线｜Blender Film Studio',
  description: '把 AI → SceneSpec → Blender 的未知问题转化为可证伪实验、通过门槛与可复现研究数据。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/research-agenda/' },
  openGraph: {
    title: 'Blender Film Studio 研究缺口与实验路线',
    description: '10 个关键缺口、6 个基准镜头、4 层验收信号和 4 阶段证伪路线。',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/research-agenda/',
  },
  twitter: { card: 'summary_large_image', title: '研究缺口与实验路线', description: '从技术可行性，走向可证伪的端到端证据。' },
};

const gapMeta: Record<GapType, { label: string; color: string }> = {
  definition: { label: '定义缺口', color: 'violet' },
  engineering: { label: '工程缺口', color: 'cyan' },
  experiment: { label: '证据缺口', color: 'orange' },
  governance: { label: '治理缺口', color: 'rose' },
};

const gaps: {
  id: string; title: string; type: GapType; priority: Priority; question: string; known: string; missing: string; artifact: string; gate: string;
}[] = [
  {
    id: 'G01', title: '“影院级”目标规格', type: 'definition', priority: 'P0',
    question: '我们究竟要交付给什么显示设备、色彩管线和母版容器？',
    known: 'OutputSpec 已锁 4K、24fps、HALF multipart EXR 与 ACES 2 OCIO 文件哈希；mastering 已验证标准属性写回不改变像素。',
    missing: '物理审片显示校准、影院输出路径、动态范围/噪声阈值与“电影感”盲评协议仍未完成。',
    artifact: 'OutputSpec v0.1 + Review Environment',
    gate: '同一 EXR 在两个受控显示路径中得到可解释、一致的输出。',
  },
  {
    id: 'G02', title: 'SceneSpec 正式合同', type: 'engineering', priority: 'P0',
    question: '导演意图如何成为可验证、可版本化、可迁移的数据？',
    known: 'v0.1–v0.5 已依次覆盖基础镜头、角色、接触、抓握与哈希锁定轨迹；B08 已贯通 immutable BuildPlan 与 Blender 5.2 编译。',
    missing: '导演节奏、对白、镜头意图、模拟依赖、资产变体、批量镜头关系与版本迁移仍未形成完整正式语义。',
    artifact: 'SceneSpec v0.1–v0.5 + Migration Contract',
    gate: '所有非法输入在启动 Blender 前被定位到字段，旧版本能明确迁移或拒绝。',
  },
  {
    id: 'G03', title: '确定性与可复现边界', type: 'experiment', priority: 'P0',
    question: '相同输入在同机、跨机和补丁升级后，究竟能复现到什么程度？',
    known: 'B01/B02 结构与选定 Cycles 像素复现通过；B06 证伪 Bullet；B07/B08 锁定轨迹零误差；B14 完成 144 帧；B15 证伪 Eevee exact；B16 又证伪“输出 dither 是充分原因”。',
    missing: 'Eevee 微差的采样/求值来源、预注册感知容差、跨 GPU、驱动、OS、补丁版本、角色求值、渲染噪声与模拟缓存边界仍未知。',
    artifact: 'Reproducibility Matrix + Tolerance Policy',
    gate: '结构哈希严格一致；像素差异在按设备分层定义的阈值内。',
  },
  {
    id: 'G04', title: '代表性基准镜头组', type: 'experiment', priority: 'P0',
    question: '一个六秒室内镜头能否代表整条电影制作链？',
    known: 'B01–B05 已覆盖编译、像素、角色、接触与抓握；B06–B08 覆盖物理证伪、轨迹冻结和正式编译；B09 已打开源物理盲评门；B14 首次把 B02 receipt 跑成完整 144 帧视频。',
    missing: 'B04/B05/B09 真实盲审仍不足；近景皮肤、毛发、布料、体积、大场景、崩溃恢复和跨镜头连续性仍无实证。',
    artifact: 'BFS Benchmark v0.1 · 6 Shots',
    gate: '六类镜头均能一键构建、失败、恢复、出具结构/像素/成本报告。',
  },
  {
    id: 'G05', title: '自动验收与人类校准', type: 'experiment', priority: 'P0',
    question: '系统如何知道镜头是真的通过，而不是“有一张图输出”？',
    known: '结构、穿插、间距、遮挡、关键帧、EXR 与像素差异已有机器门；B04/B05/B09 均有哈希锁定匿名素材、响应 Schema 与本地聚合器。',
    missing: '没有单一指标能衡量电影感、表演或构图；三个真实人类门均未收齐，机器阈值也尚未用导演/艺术家盲评校准。',
    artifact: 'Validator v0.1 + Human Review Protocol',
    gate: '在已标注故障集上达到预定召回率，并报告机器与人工分歧。',
  },
  {
    id: 'G06', title: '数字演员与表演协议', type: 'engineering', priority: 'P1',
    question: '如何把身份、动作、面部、视线、呼吸和接触分成可编辑层？',
    known: 'ActorSpec v0.1 已通过规范/资产/求值测试；B03 场景相对眼神与脚底接触通过；B04 证明父级切换与 real-prop socket，并把持续穿入修正为可复现的 2 mm 刚性间距。',
    missing: '英雄角色的皮肤、毛发、口腔、微表演、多角色反应、手指抓握、受力与重量感仍没有端到端可靠解。',
    artifact: 'Executed ActorSpec v0.1 + B03/B04 Scene Integration',
    gate: '同一角色完成近景对白、全身行走和拿取道具，身份不漂移且每层可单独修改。',
  },
  {
    id: 'G07', title: '资产来源、许可与内容凭证', type: 'governance', priority: 'P1',
    question: '每个模型、纹理、动作和参考图是否可追溯、可商用、可替换？',
    known: 'USD AssetInfo 可记录标识与版本；C2PA 2.4 提供媒体来源与历史的技术框架。',
    missing: '生成资产的训练/来源声明、作者、许可、地域限制、人物肖像同意和派生关系尚未形成统一清单。',
    artifact: 'Asset Manifest + Provenance Policy',
    gate: '任何成片像素都能回溯到镜头、场景、资产版本、许可与生成/编辑记录。',
  },
  {
    id: 'G08', title: '代理执行安全', type: 'governance', priority: 'P0',
    question: 'Codex / MCP 可以修改什么，如何防止任意代码、越权读写和供应链污染？',
    known: 'B10–B12 覆盖路径、资产求值结构与软资源预算；B13 用 receipt 绑定 plan、工具源、Blender/Node binary、profile、OCIO、manifest、规范结构与 .blend，10+2 攻击通过。',
    missing: 'receipt 尚未签名或远程证明；解析器漏洞、子进程总内存、GPU/网络/系统调用、OS 隔离、包供应链、签名审批、dry-run、回滚和完整 MCP 授权仍未实现。',
    artifact: 'Restricted Tool Gateway + Threat Model',
    gate: '攻击样例不能越出工作目录、联网、读取秘密或绕过批准修改制作资产。',
  },
  {
    id: 'G09', title: '恢复、编辑与生产编排', type: 'engineering', priority: 'P1',
    question: '镜头在崩溃、改剪、换资产和部分失败后如何继续，而不是整段重来？',
    known: '依赖图、内容寻址、缓存、后台渲染和 OpenTimelineIO 可连接镜头版本与剪辑时间线。',
    missing: '任务状态机、幂等步骤、缓存失效规则、重试预算、取消、人工接管和剪辑回写尚未联成系统。',
    artifact: 'Shot State Machine + Recovery Drill',
    gate: '随机终止任一步骤后可恢复；改剪只使必要帧和依赖失效。',
  },
  {
    id: 'G10', title: '对照实验与真实经济性', type: 'experiment', priority: 'P0',
    question: '与人工 Blender、视频生成和传统混合流程相比，何时真的更便宜？',
    known: '已经建立完整成本栈；简单 4K/512spp CPU 基准平均 327.65 秒/帧。B14 的 960×540 Eevee 代理实测 27.39 秒/144 帧，但明确不是同质量对照。',
    missing: '仍缺相同 brief 的三路对照，以及 Token、人工、功耗、GPU、重试和资产摊销的完整实测。',
    artifact: 'Three-arm Cost Study + Raw Telemetry',
    gate: '预注册假设后公开原始记录；不以生成秒数代替最终采用秒。',
  },
];

const benchmarkShots = [
  ['B01', '材质静物', '皮革、金属、玻璃、肤色卡与高光', '色彩 / 材质 / 噪声'],
  ['B02', '室内移动镜头', '6 秒 dolly、窗光、景深、运动模糊', '摄影 / 灯光 / 时序'],
  ['B03', '演员近景', '对白、眼神、牙齿、皮肤与头发边缘', '身份 / 面部 / 细节'],
  ['B04', '全身接触', '行走、坐下、拿杯、双手交换道具', '脚滑 / 穿插 / 重心'],
  ['B05', '次级运动', '服装、长发、快速转身与碰撞', '物理 / 缓存 / 恢复'],
  ['B06', '大型环境', '实例、体积、反射、远近景和镜头重构', '规模 / VRAM / 局部重建'],
];

const signalLayers = [
  ['01', '合同与结构', 'Schema 通过率、稳定 ID、依赖闭包、资产/许可完整性、结构哈希。'],
  ['02', '物理与技术', '穿插、接触距离、脚滑、曝光、超色域、噪声、缺帧、EXR 通道。'],
  ['03', '像素与感知', 'FLIP/HDR-FLIP、时序闪烁、身份特征、参考构图差异；只作辅助证据。'],
  ['04', '人类与经济', '导演盲评、首次接受率、人工分钟、Token、渲染小时、每个最终采用秒成本。'],
];

const phases = [
  ['PHASE 0', '冻结定义', '第 1–2 周', 'OutputSpec、SceneSpec、失败分类、实验预注册', '没有可测试合同，不开始自动生成。'],
  ['PHASE 1', '证明确定性', '第 3–6 周', 'B01 + B02、编译器、清单、Validator、成本遥测', '两次净构建一致，局部修改不污染无关依赖。'],
  ['PHASE 2', '挑战人物', '第 7–12 周', 'B03 + B04、ActorSpec、捕捉/重定向、接触层', '近景与全身均可编辑，不靠神经视频掩盖失败。'],
  ['PHASE 3', '挑战规模', '第 13–18 周', 'B05 + B06、模拟缓存、恢复、三路成本对照', '故障可恢复，成本结论有原始数据支持。'],
];

const references = [
  ['Digital Cinema Initiatives', 'Digital Cinema System Specification 1.5.0', 'https://www.dcimovies.com/dci-specification/'],
  ['Academy', 'ACES 2 Output Transforms', 'https://docs.acescentral.com/system-components/output-transforms/'],
  ['OpenEXR', 'Technical Introduction', 'https://openexr.com/en/latest/TechnicalIntroduction.html'],
  ['JSON Schema', 'Draft 2020-12', 'https://json-schema.org/draft/2020-12'],
  ['OpenUSD', 'Introduction and composition model', 'https://openusd.org/release/intro.html'],
  ['VFX Reference Platform', 'CY2026 compatibility baseline', 'https://vfxplatform.com/'],
  ['Blender', 'Open Data Benchmark', 'https://opendata.blender.org/about/'],
  ['Blender 5.2 Manual', 'Command-line rendering', 'https://docs.blender.org/manual/en/5.2/advanced/command_line/render.html'],
  ['NVIDIA Research', 'FLIP image-difference evaluator', 'https://research.nvidia.com/sites/default/files/node/3260/FLIP_Paper.pdf'],
  ['C2PA', 'Content Credentials Specification 2.4', 'https://spec.c2pa.org/specifications/'],
  ['OpenTimelineIO', 'Timeline structure 0.17', 'https://opentimelineio.readthedocs.io/en/v0.17.0/tutorials/otio-timeline-structure.html'],
  ['Blender Foundation', 'Official MCP server and security warning', 'https://www.blender.org/lab/mcp-server/'],
];

export default function ResearchAgendaPage() {
  const p0Count = gaps.filter(gap => gap.priority === 'P0').length;

  return (
    <main className="agenda-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="研究路线导航"><Link href="/">技术基线</Link><Link href="/blender-5-2">Blender 5.2</Link><Link href="/cost-model">成本</Link><a href="#gaps">缺口</a><Link className="route-tab spec-route" href="/spec-v0-1">规格 v0.1</Link><Link className="route-tab compiler-route" href="/compiler-v0-1">编译实验</Link><Link className="route-tab" href="/pixel-v0-1">像素实验</Link><Link className="route-tab actor-route" href="/actor-v0-1">角色实验</Link><Link className="route-tab contact-route" href="/contact-v0-1">接触实验</Link><Link className="route-tab" href="/grasp-v0-1">手指抓握</Link></nav>
        <span className="edition agenda-edition">Agenda 01</span>
      </header>

      <section className="agenda-hero" id="top">
        <div className="agenda-grid" aria-hidden="true" />
        <div className="agenda-hero-copy"><p className="eyebrow"><span /> FALSIFIABLE ROADMAP · 2026.08.25</p><h1>我们知道它<span>可能成立。</span><br />下一步要证明它<span>何时失败。</span></h1><p>现有研究回答了“哪些技术存在”。尚未回答的是：在固定输入、固定验收和真实成本下，整条链能否重复交付。这里把未知问题转成合同、基准、指标与失败门槛。</p></div>
        <div className="agenda-compass" aria-hidden="true"><span>KNOWN</span><i /><b>?</b><small>PROOF</small></div>
        <div className="agenda-stats"><article><strong>{gaps.length}</strong><span>关键缺口</span><small>{p0Count} 个 P0</small></article><article><strong>6</strong><span>基准镜头</span><small>覆盖静物到规模场景</small></article><article><strong>4</strong><span>证据层</span><small>结构 → 人类与经济</small></article><article><strong>18w</strong><span>首轮协议</span><small>四阶段，可提前证伪</small></article></div>
      </section>

      <section className="section agenda-verdict">
        <div className="section-index">00 / 当前判断</div>
        <div className="agenda-verdict-grid"><div><p className="eyebrow dark"><span /> THE MISSING CENTER</p><h2>缺的不是更多功能，<br />而是<span>可执行证据。</span></h2></div><div><b>当前能说</b><p>Blender 的场景控制、路径追踪、EXR 和自动化足以成为确定性后端。</p><b>当前不能说</b><p>整条 AI 工作流已经比视频生成更便宜、更快，或能自动交付电影级人物表演。</p></div></div>
        <div className="proof-chain"><article><span>01</span><b>定义目标</b><small>没有目标就没有“影院级”</small></article><i>→</i><article><span>02</span><b>冻结输入</b><small>合同、资产与版本</small></article><i>→</i><article><span>03</span><b>运行对照</b><small>相同 brief 与验收</small></article><i>→</i><article><span>04</span><b>允许失败</b><small>预注册通过 / 停止门槛</small></article><i>→</i><article><span>05</span><b>公开证据</b><small>数据、日志、成本与差异</small></article></div>
      </section>

      <section className="section agenda-gaps" id="gaps">
        <div className="section-index light">01 / 研究缺口矩阵</div>
        <div className="agenda-heading"><div><p className="eyebrow"><span /> TEN GAPS</p><h2>每个未知问题，<br />都必须有<span>工程物与门槛。</span></h2></div><p>优先级不是按“看起来最酷”排序，而是按它是否会让后续结论无效。P0 未完成前，不应宣称端到端生产成立。</p></div>
        <div className="gap-legend">{(Object.keys(gapMeta) as GapType[]).map(type => <span className={gapMeta[type].color} key={type}><i />{gapMeta[type].label}</span>)}<b>P0 = 会阻断结论</b></div>
        <div className="gap-table" role="table" aria-label="研究缺口概览"><div className="gap-table-head" role="row"><span>缺口</span><span>类型</span><span>优先级</span><span>必须交付</span></div>{gaps.map(gap => <a href={`#${gap.id}`} className="gap-table-row" role="row" key={gap.id}><span><i>{gap.id}</i>{gap.title}</span><span className={gapMeta[gap.type].color}>{gapMeta[gap.type].label}</span><b className={gap.priority.toLowerCase()}>{gap.priority}</b><small>{gap.artifact}</small></a>)}</div>
        <div className="gap-cards">{gaps.map(gap => <article id={gap.id} key={gap.id}><aside><span>{gap.id}</span><small className={gapMeta[gap.type].color}>{gapMeta[gap.type].label}</small><b>{gap.priority}</b></aside><div><header><h3>{gap.title}</h3><p>{gap.question}</p></header><div className="gap-evidence"><div><span>已经知道</span><p>{gap.known}</p></div><div><span>仍然缺失</span><p>{gap.missing}</p></div></div><div className="gap-gate"><span>工程物</span><b>{gap.artifact}</b><span>通过门槛</span><p>{gap.gate}</p></div></div></article>)}</div>
      </section>

      <section className="section agenda-benchmark" id="benchmark">
        <div className="section-index">02 / BFS Benchmark v0.1</div>
        <div className="agenda-heading dark-heading"><div><p className="eyebrow dark"><span /> SIX GOLDEN SHOTS</p><h2>一个镜头证明闭环，<br />六个镜头挑战边界。</h2></div><p>每个基准镜头都必须包含固定 SceneSpec、资产包、golden manifest、预期故障、审片参考和成本记录；不能只保存最终视频。</p></div>
        <div className="benchmark-grid">{benchmarkShots.map(([id, title, content, stress]) => <article key={id}><span>{id}</span><small>{stress}</small><h3>{title}</h3><p>{content}</p><div aria-hidden="true"><i /><i /><i /></div></article>)}</div>
        <div className="benchmark-package"><span>每个基准包</span><div>{['scene.spec.json', 'assets.lock', 'golden.manifest', 'expected-failures', 'review-reference', 'telemetry.jsonl', 'render.exr', 'report.html'].map(item => <code key={item}>{item}</code>)}</div></div>
      </section>

      <section className="section agenda-signals">
        <div className="section-index light">03 / 验收信号</div>
        <div className="agenda-heading"><div><p className="eyebrow"><span /> FOUR EVIDENCE LAYERS</p><h2>“有输出”不是通过，<br />“像电影”也不是指标。</h2></div><p>自动指标负责发现已编码的错误，人类负责审美与叙事。两者必须同时保存，而且要记录分歧，不能让任一方伪装成绝对真值。</p></div>
        <div className="signal-layers">{signalLayers.map(([id, title, detail]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
        <div className="metric-warning"><b>重要边界</b><p>FLIP、SSIM、身份相似度或 VMAF 都不能单独证明“电影感”。它们只能检测相对于参考的特定差异；构图、表演、节奏和审美仍需要盲评与导演验收。</p></div>
      </section>

      <section className="section agenda-protocol" id="protocol">
        <div className="section-index">04 / 首轮实验协议</div>
        <div className="agenda-heading dark-heading"><div><p className="eyebrow dark"><span /> 18-WEEK FALSIFICATION PLAN</p><h2>越早失败，<br />研究越有价值。</h2></div><p>每阶段都有停止门槛。前一阶段不能通过，就修正假设，不用更多内容复杂度掩盖底层问题。</p></div>
        <div className="protocol-timeline">{phases.map(([phase, title, time, work, gate]) => <article key={phase}><header><span>{phase}</span><small>{time}</small></header><h3>{title}</h3><p>{work}</p><div><b>停止 / 通过门槛</b><span>{gate}</span></div></article>)}</div>
        <div className="first-action"><span>NEXT CONCRETE ACTION</span><div><h3>冻结生产容差，再用 holdout 证伪。</h3><p>B23 已证明同一 PID、同一帧连续 render 也会发生严格 float variation。下一步不再从这批数据挑 exact 开关：保持结构与 provenance 哈希严格一致，使用独立 derivation / holdout 划分预注册数值、显示域与感知门槛。</p></div></div>
      </section>

      <section className="section agenda-decisions">
        <div className="section-index light">05 / 现在做什么</div>
        <div className="decision-columns"><article className="now"><span>BUILD NOW</span><h2>立即建设</h2><ul><li>三条真实人类盲评门</li><li>恶意 .blend 隔离实验</li><li>资源与超时预算</li><li>审查者分歧记录</li><li>Token / 渲染 / 人工遥测</li><li>受限工具审批与回滚</li></ul></article><article><span>RESEARCH IN PARALLEL</span><h2>并行研究</h2><ul><li>跨 GPU 容差</li><li>物理显示校准</li><li>资产来源与 C2PA 映射</li><li>角色许可与肖像同意</li><li>ACES 2 审片路径</li><li>模拟缓存与恢复</li></ul></article><article className="later"><span>DEFER</span><h2>暂缓承诺</h2><ul><li>全自动英雄角色</li><li>端到端电影微表演</li><li>任意生成网格自动可动画</li><li>实验物理作为唯一主干</li><li>无人监督的任意代码执行</li><li>“一键长片”产品叙事</li></ul></article></div>
      </section>

      <section className="section agenda-method" id="sources">
        <div className="section-index">06 / 方法与证据</div>
        <div className="agenda-heading dark-heading"><div><p className="eyebrow dark"><span /> RESEARCH STANDARD</p><h2>标准定义边界，<br />实验决定结论。</h2></div><p>标准只能告诉我们数据该如何表达、显示或交换，不能证明本系统已经工作。所有“可生产”结论必须回到固定实验、原始记录与明确停止门槛。</p></div>
        <div className="method-rules"><article><b>预注册</b><p>运行前写明假设、输入、阈值、排除项和停止条件。</p></article><article><b>对照</b><p>相同 brief、资产与验收，对比人工、BFS 和视频生成三路。</p></article><article><b>可复现</b><p>保存环境、版本、种子、设备、清单、日志和完整生成物。</p></article><article><b>负结果</b><p>失败镜头、人工分歧与不经济区间同样进入公开记录。</p></article></div>
        <ol className="references agenda-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>Falsifiable Research Agenda</b></div><p>Research tab · Snapshot: 2026-08-26 · Negative results are evidence</p><Link href="/eevee-repeated-render-boundary-v0-1">查看最新同进程实验 →</Link></footer>
    </main>
  );
}
