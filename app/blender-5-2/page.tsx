import type { Metadata } from 'next';
import Link from 'next/link';

type Maturity = 'stable' | 'conditional' | 'experimental';
type Priority = 'P0' | 'P1' | 'P2';

export const metadata: Metadata = {
  title: 'Blender 5.2 技术介入地图｜Blender Film Studio',
  description: '逐技术域审计 Blender 5.2 LTS：哪些能力可读、可控、可程序化、可编译，以及哪些环节适合建立自动闭环。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-5-2/' },
  openGraph: {
    title: 'Blender 5.2 技术介入地图',
    description: '从数据模型、Python API、Geometry Nodes 到 Cycles 与交付验证，分析 AI 电影系统可以深度介入的层面。',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-5-2/',
  },
  twitter: { card: 'summary_large_image', title: 'Blender 5.2 技术介入地图', description: '18 个技术域，5 级介入深度，6 个首批工程包。' },
};

const maturityMeta: Record<Maturity, { label: string; note: string }> = {
  stable: { label: '生产稳定', note: '可进入版本锁定的常规制作' },
  conditional: { label: '条件可用', note: '需预设、人工验收或限制输入' },
  experimental: { label: '实验性', note: '接口或行为仍可能变化' },
};

const interventionLevels = [
  ['L0', '观察', '读取场景、依赖、性能与错误；不改变文件。'],
  ['L1', '参数化', '控制已有对象、节点、约束与渲染参数。'],
  ['L2', '程序化', '用节点组、资产模板和规则构造内容。'],
  ['L3', '编译', '把 SceneSpec 确定性转换为可交付场景。'],
  ['L4', '闭环', '渲染、检测、定位并只重算受影响部分。'],
];

const domains: {
  id: string; group: string; title: string; maturity: Maturity; depth: string; deterministic: '高' | '中' | '低'; priority: Priority;
  signal: string; intervene: string; deliverable: string; boundary: string; sources: { label: string; href: string }[];
}[] = [
  {
    id: 'B01', group: 'CORE', title: '数据块、依赖图与场景状态', maturity: 'stable', depth: 'L4', deterministic: '高', priority: 'P0',
    signal: '5.2 扩大了全局 ID 与文件路径遍历能力；库覆盖和打包数据继续构成可追踪场景结构。',
    intervene: '把对象、集合、材质、动作、图像与外部依赖映射为稳定 ID；做场景 diff、依赖扫描、命名/单位/版本验证。',
    deliverable: 'Scene Manifest + Dependency Graph + Deterministic Hash',
    boundary: '依赖图负责求值，不理解镜头的叙事意图；.blend 也不应被当作唯一的业务数据合同。',
    sources: [{ label: 'Python API 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/python_api/' }],
  },
  {
    id: 'B02', group: 'AUTO', title: 'Python API 与后台自动化', maturity: 'stable', depth: 'L4', deterministic: '高', priority: 'P0',
    signal: '后台模式新增 gpu.init()；Geometry Nodes modifier 输入/输出成为正式 RNA 属性；图像缓冲接口扩展。',
    intervene: '建立幂等构建器、任务队列、事务日志、批量渲染和结构化错误报告；优先直接操作数据，少依赖 UI 上下文。',
    deliverable: 'Blender Compiler + Headless Worker + Operation Log',
    boundary: 'bpy.ops 仍可能依赖上下文；版本升级会改变 RNA 路径，必须做 API 合约测试并锁定 5.2 LTS。',
    sources: [{ label: 'Python API', href: 'https://docs.blender.org/api/5.2/' }, { label: '5.2 变更', href: 'https://docs.blender.org/api/5.2/change_log.html' }],
  },
  {
    id: 'B03', group: 'AGENT', title: 'MCP、插件与人机控制面', maturity: 'conditional', depth: 'L2', deterministic: '中', priority: 'P1',
    signal: 'Blender 官方 MCP 能让模型读取场景并生成/执行操作，但官方明确警告其没有安全护栏。',
    intervene: '把自然语言限制为“提出变更集”；经 SceneSpec schema、权限白名单、dry-run 与人工批准后才执行。',
    deliverable: 'Restricted Tool Gateway + Approval UI + Sandbox Policy',
    boundary: '不能让模型在含敏感数据的制作机上任意执行生成代码；MCP 是接口，不是正确性或安全性的证明。',
    sources: [{ label: '官方 MCP', href: 'https://www.blender.org/lab/mcp-server/' }],
  },
  {
    id: 'B04', group: 'ASSET', title: '远程资产库与资产治理', maturity: 'conditional', depth: 'L3', deterministic: '高', priority: 'P0',
    signal: '5.2 首次支持通过 HTTP 浏览、按需下载远程资产；清单 v1 含哈希、许可、作者、版本和目录。',
    intervene: '建立角色/场景/材质圣经，固定资产 ID、真实尺度、许可、LOD、预览和 preferred import method。',
    deliverable: 'Studio Asset Registry + Static Remote Library + Validation Gate',
    boundary: '5.2 的远程库偏静态公开分发，复杂多文件资产支持有限；搜索系统不会自动统一美术风格与拓扑质量。',
    sources: [{ label: 'Assets 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/assets/' }, { label: 'Remote Library v1', href: 'https://developer.blender.org/docs/features/asset_system/remote_asset_libraries/' }],
  },
  {
    id: 'B05', group: 'IO', title: 'USD、Alembic、glTF 与交换层', maturity: 'stable', depth: 'L3', deterministic: '高', priority: 'P0',
    signal: 'USD 增加色彩空间标记与导出 flush 控制；Alembic 可导入动画可见性和相机 F-Curves；glTF 扩展压缩、点云与材质。',
    intervene: '以 USD 组织镜头层、资产引用和非破坏性 override；用 Alembic 做几何缓存，用 glTF 做轻量预览交付。',
    deliverable: 'Shot Package Contract + USD Layer Policy + I/O Round-trip Tests',
    boundary: '任何交换格式都不是完整 .blend 的无损镜像；modifier、复杂 shader、rig 语义与约束可能降级或丢失。',
    sources: [{ label: 'Pipeline & I/O 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/pipeline_io/' }],
  },
  {
    id: 'B06', group: 'MODEL', title: '建模、UV、雕刻与纹理绘制', maturity: 'conditional', depth: 'L2', deterministic: '中', priority: 'P2',
    signal: 'LoopTools 的 Circle/Space/Flatten 进入核心；UV 选择与展开增强；voxel remesh 更好保留颜色属性。',
    intervene: '自动执行规范化、检查非流形/重叠 UV/面密度、静态道具减面和烘焙；把人工修形设置为明确关卡。',
    deliverable: 'Asset Ingest Linter + Repair Presets + Hero-asset Review Gate',
    boundary: '通用 AI 网格的语义部件、四边面边流、英雄角色变形拓扑和材质分解仍不能靠规则一次解决。',
    sources: [{ label: 'Modeling & UV', href: 'https://developer.blender.org/docs/release_notes/5.2/modeling/' }, { label: 'Sculpt/Paint', href: 'https://developer.blender.org/docs/release_notes/5.2/sculpt/' }],
  },
  {
    id: 'B07', group: 'PROC', title: 'Geometry Nodes 程序化系统', maturity: 'stable', depth: 'L3', deterministic: '高', priority: 'P0',
    signal: 'Geometry Bundle 可跨对象携带数据；Lists 成为核心数据类型；Collections、Empty、Sound 与 Mesh Bevel 扩大系统表达力。',
    intervene: '把布景、散布、道路、植被、破损、镜头代理和变体封装为有输入合同、版本和测试场景的节点资产。',
    deliverable: 'Procedural Asset SDK + Typed Node Groups + Bake Registry',
    boundary: '节点图依然需要被设计和测试；5.2 Lists 的核心节点数量有限，新 RNA 路径也会破坏旧自动化。',
    sources: [{ label: 'Geometry Nodes 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/' }, { label: '兼容性', href: 'https://developer.blender.org/docs/release_notes/compatibility/' }],
  },
  {
    id: 'B08', group: 'LOOK', title: '材质、灯光与色彩管理', maturity: 'stable', depth: 'L3', deterministic: '高', priority: 'P0',
    signal: '新增多家摄影机厂商与宽色域输入色彩空间；Principled BSDF Thin Wall、Time Node 与 light/shadow linking 操作增强。',
    intervene: '建立灯光 rig、材质模板、相机输入变换、曝光策略和 look version；所有决定保存为显式参数，不烘焙进参考图。',
    deliverable: 'Look Template Library + OCIO Policy + Light-linking Rules',
    boundary: '从单张 LDR 参考图无法唯一分离真实材质、HDR 光照和摄影处理；艺术取舍仍需摄影/灯光指导。',
    sources: [{ label: 'Rendering 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/rendering/' }],
  },
  {
    id: 'B09', group: 'CAM', title: '摄影机、镜头、轨迹与跟踪', maturity: 'stable', depth: 'L3', deterministic: '高', priority: 'P1',
    signal: '精确摄影机参数、约束和跟踪求解本已成熟；5.2 继续改善高分辨率素材、遮罩与动画相机数据交换。',
    intervene: '定义镜头模板、传感器/焦段/光圈/快门合同、可解释轨迹原语、构图安全区和实拍跟踪质量门槛。',
    deliverable: 'Camera Grammar + Lens Profiles + Tracking QA Report',
    boundary: '数值可完全控制，不代表系统能从“孤独感”唯一推导出最有叙事意义的机位与运动。',
    sources: [{ label: 'Camera Solver', href: 'https://docs.blender.org/manual/en/5.2/animation/constraints/motion_tracking/camera_solver.html' }, { label: 'Pipeline & I/O', href: 'https://developer.blender.org/docs/release_notes/5.2/pipeline_io/' }],
  },
  {
    id: 'B10', group: 'ANIM', title: '动画、绑定、动作与约束', maturity: 'conditional', depth: 'L3', deterministic: '中', priority: 'P1',
    signal: '5.2 加强约束复制、骨骼批量命名、Dope Sheet/F-Curve 操作、pose 旋转模式转换和播放循环控制。',
    intervene: '统一骨架语义、动作资产、retarget mapping、接触事件、root motion、F-Curve 清理和镜头级 corrective pass。',
    deliverable: 'Rig Contract + Motion Retargeter + Contact Event Track',
    boundary: 'Blender 能准确执行已定义动作，但不会自动产生演员级意图、重量、眼神和细微非对称表演。',
    sources: [{ label: 'Animation & Rigging 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/animation_rigging/' }, { label: 'Rigify', href: 'https://docs.blender.org/manual/en/latest/addons/rigify/index.html' }],
  },
  {
    id: 'B11', group: 'PREVIS', title: 'Grease Pencil、分镜与视觉规划', maturity: 'stable', depth: 'L2', deterministic: '高', priority: 'P1',
    signal: 'Delaunay 精确填充成为默认；新增曲线类型、渲染时 dots/squares、在线笔刷和更完整的 Python stroke/fill API。',
    intervene: '把镜头草图、角色走位、焦点和注释转为可解析层；从结构化分镜生成摄影机与 blocking 初稿。',
    deliverable: 'Storyboard Schema + Shot Annotation Importer + Previs Export',
    boundary: '分镜的线条与层级不能唯一确定三维深度、真实资产、表演节奏和最终构图。',
    sources: [{ label: 'Grease Pencil 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/grease_pencil/' }],
  },
  {
    id: 'B12', group: 'SIM', title: '刚体、布料、毛发、流体与次级运动', maturity: 'experimental', depth: 'L2', deterministic: '中', priority: 'P1',
    signal: '5.2 推出基于 Geometry Nodes/XPBD 的实验性布料与毛发，支持可组合 collider、force、custom effector 与 tearing。',
    intervene: '用镜头级预设、碰撞代理、缓存依赖、参数搜索和自动穿透/能量异常检测做受控实验；保留成熟求解器回退。',
    deliverable: 'Simulation Preset Lab + Cache DAG + Failure Detector',
    boundary: '官方明确标为实验性，设计仍可能变化；不能把它作为当前英雄角色服装/毛发的唯一生产路径。',
    sources: [{ label: 'Physics 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/physics/' }],
  },
  {
    id: 'B13', group: 'PREVIEW', title: 'EEVEE 与实时视口', maturity: 'stable', depth: 'L3', deterministic: '高', priority: 'P1',
    signal: '实例密集场景 CPU 瓶颈最高约 2×；屏幕空间光追重构、GI/AO 修正、光线可见性与更大 shadow pool。',
    intervene: '把 EEVEE 设为导演实时预览和回归快照，自动比对构图、遮挡、动画、灯光代理与性能预算。',
    deliverable: 'Realtime Review Mode + Visual Regression Set + Frame Budget',
    boundary: '屏幕空间效果不等于完整路径追踪；5.2 修正能量守恒后旧场景可能更暗，必须做版本前后 look diff。',
    sources: [{ label: 'EEVEE 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/eevee/' }],
  },
  {
    id: 'B14', group: 'FINAL', title: 'Cycles 影院级路径追踪', maturity: 'stable', depth: 'L4', deterministic: '高', priority: 'P0',
    signal: '5.2 引入 texture cache/on-demand mip mapping，降低大型高分辨率纹理场景的内存压力；着色与几何性能继续增强。',
    intervene: '锁定设备、采样、去噪、光路、运动模糊、持久数据与纹理预算；按镜头输出渲染统计和可复现配置。',
    deliverable: 'Render Profile + Farm Worker + Cost/Noise Telemetry',
    boundary: '高采样只会更精确地渲染输入；不能修复错误资产、僵硬表演、穿插或失败的美术方向。',
    sources: [{ label: 'Cycles Texture Cache', href: 'https://code.blender.org/2026/05/cycles-texture-cache/' }, { label: 'Cycles Manual', href: 'https://docs.blender.org/manual/en/5.2/render/cycles/' }],
  },
  {
    id: 'B15', group: 'COMP', title: 'Compositor、AOV 与镜头合成', maturity: 'stable', depth: 'L4', deterministic: '高', priority: 'P0',
    signal: '交互合成显著更响应并支持播放；新增 6 类 socket 与大量节点，输出控制、相机/对象数据和稳定处理能力扩展。',
    intervene: '生成标准 node tree、AOV/Light Group/Cryptomatte 路由、景深/辉光/合成模板和逐层有效性检查。',
    deliverable: 'Comp Template + Pass Contract + Layer Integrity Tests',
    boundary: '合成能重组与修正已有信息，不能凭空恢复不存在的几何、正确遮挡或可信表演。',
    sources: [{ label: 'Compositor 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/compositor/' }, { label: 'Cryptomatte', href: 'https://docs.blender.org/manual/en/5.2/compositing/types/mask/cryptomatte.html' }],
  },
  {
    id: 'B16', group: 'EDIT', title: 'VSE、声音与镜头装配', maturity: 'conditional', depth: 'L3', deterministic: '高', priority: 'P1',
    signal: 'VSE 新增 Compositor effect、复杂图可用 GPU；scene strip 可选 view layer；Python 可读取 strip connections。',
    intervene: '从镜头清单建立 animatic、版本替换、handles、字幕、代理、view layer 选择和色彩/音频交付检查。',
    deliverable: 'Edit Decision Compiler + Shot Version Relinker + Review Export',
    boundary: 'VSE 适合预演和轻量装配；复杂声音、协作剪辑、调色与长片 conform 仍宜交给专门 DCC。',
    sources: [{ label: 'Video Sequencer 5.2', href: 'https://developer.blender.org/docs/release_notes/5.2/sequencer/' }],
  },
  {
    id: 'B17', group: 'DELIVERY', title: 'EXR、色彩与最终交付', maturity: 'stable', depth: 'L4', deterministic: '高', priority: 'P0',
    signal: 'FP16 OpenEXR 写入更快；可禁用渲染输出保存；全景/立体元数据和更广输入色彩空间增强。',
    intervene: '规定 scene-linear EXR、多层/单层策略、数据 pass、校验和、帧完整性、命名、manifest 与代理编码。',
    deliverable: 'Delivery Spec + Frame Verifier + Master Manifest',
    boundary: '“高比特”只是容器能力；没有统一 OCIO、合法信号范围和下游解释，颜色仍会不一致。',
    sources: [{ label: 'Pipeline & I/O', href: 'https://developer.blender.org/docs/release_notes/5.2/pipeline_io/' }, { label: 'Rendering', href: 'https://developer.blender.org/docs/release_notes/5.2/rendering/' }],
  },
  {
    id: 'B18', group: 'QA', title: '验证、恢复、兼容性与回归测试', maturity: 'conditional', depth: 'L4', deterministic: '高', priority: 'P0',
    signal: '5.2 是 LTS 且修复 560 项既有问题；同时 Geometry Nodes RNA 路径等存在明确破坏性变更。LTS 不是“没有 bug”。',
    intervene: '为 golden shots 做结构、像素、性能与 API 回归；保存前检查未保存图像；自动归档日志、依赖和构建指纹。',
    deliverable: 'Golden Shot Suite + Compatibility Matrix + Recovery Protocol',
    boundary: '自动检查只能覆盖编码过的规则；审美、叙事、表演与未见过的故障仍需人类 review。',
    sources: [{ label: '560 Bug Fixes', href: 'https://developer.blender.org/docs/release_notes/5.2/bugfixes/' }, { label: 'Compatibility', href: 'https://developer.blender.org/docs/release_notes/compatibility/' }],
  },
];

const packages = [
  ['01', 'SceneSpec + Blender Compiler', '受限合同、幂等构建、场景 diff、操作日志', 'B01 · B02 · B03'],
  ['02', 'Asset Registry', '远程清单、稳定 ID、许可、版本、依赖与导入策略', 'B04 · B05'],
  ['03', 'Procedural Factory', '类型化节点组、输入合同、测试场景、bake 版本', 'B06 · B07'],
  ['04', 'Cinematography System', '镜头语法、摄影机、灯光、材质与实时预览模板', 'B08 · B09 · B13'],
  ['05', 'Render Delivery', 'Cycles profile、AOV、Compositor、EXR 与成本遥测', 'B14 · B15 · B17'],
  ['06', 'Validator + Regression Lab', '结构、像素、性能、缓存与兼容性闭环', 'B12 · B16 · B18'],
];

const exclusions = [
  ['任意代码直达 .blend', '模型只能提交受限变更，不允许绕过 schema、权限、dry-run 与日志。'],
  ['把 LTS 当作零风险', 'LTS 提供维护窗口，不保证所有 GPU、节点、缓存和旧文件路径无回归。'],
  ['实验物理成为主干', '节点布料/毛发先进入隔离实验室；生产保留传统求解器或人工缓存回退。'],
  ['交换格式等于语义真值', 'USD/Alembic/glTF 各有职责；必须用 round-trip 测试证明具体字段可保真。'],
];

const references = [
  ['Blender Foundation', 'Blender 5.2 LTS 发布页', 'https://www.blender.org/releases/5-2/'],
  ['Blender Developers', 'Blender 5.2 完整发布说明', 'https://www.blender.org/download/releases/5-2/'],
  ['Blender Developers', 'Python API 5.2', 'https://developer.blender.org/docs/release_notes/5.2/python_api/'],
  ['Blender Developers', 'Geometry Nodes 5.2', 'https://developer.blender.org/docs/release_notes/5.2/geometry_nodes/'],
  ['Blender Developers', 'Physics 5.2', 'https://developer.blender.org/docs/release_notes/5.2/physics/'],
  ['Blender Developers', 'Assets / Remote Libraries', 'https://developer.blender.org/docs/release_notes/5.2/assets/'],
  ['Blender Developers', 'Pipeline & I/O 5.2', 'https://developer.blender.org/docs/release_notes/5.2/pipeline_io/'],
  ['Blender Developers', 'Rendering 5.2', 'https://developer.blender.org/docs/release_notes/5.2/rendering/'],
  ['Blender Developers', 'EEVEE & Viewport 5.2', 'https://developer.blender.org/docs/release_notes/5.2/eevee/'],
  ['Blender Developers', 'Compositor 5.2', 'https://developer.blender.org/docs/release_notes/5.2/compositor/'],
  ['Blender Developers', 'Video Sequencer 5.2', 'https://developer.blender.org/docs/release_notes/5.2/sequencer/'],
  ['Blender Developers', '兼容性与破坏性变更', 'https://developer.blender.org/docs/release_notes/compatibility/'],
  ['Blender Foundation', '官方 Blender MCP Server', 'https://www.blender.org/lab/mcp-server/'],
];

function MaturityBadge({ maturity }: { maturity: Maturity }) {
  return <span className={`b52-badge ${maturity}`}><i />{maturityMeta[maturity].label}</span>;
}

export default function Blender52Page() {
  const maturityCounts = domains.reduce((acc, domain) => ({ ...acc, [domain.maturity]: (acc[domain.maturity] ?? 0) + 1 }), {} as Record<Maturity, number>);

  return (
    <main className="b52-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="Blender 5.2 研究导航"><Link href="/">技术基线</Link><a href="#matrix-52">技术域</a><Link className="route-tab cost-route" href="/cost-model">成本</Link><Link className="route-tab agenda-route" href="/research-agenda">研究路线</Link><Link className="route-tab spec-route" href="/spec-v0-1">规格 v0.1</Link><Link className="route-tab compiler-route" href="/compiler-v0-1">编译实验</Link><Link className="route-tab" href="/pixel-v0-1">像素实验</Link><Link className="route-tab actor-route" href="/actor-v0-1">角色实验</Link></nav>
        <span className="edition active-edition">Blender 5.2</span>
      </header>

      <section className="b52-hero" id="top">
        <div className="b52-orbit" aria-hidden="true"><span /><i /><b>5.2</b></div>
        <div className="b52-hero-copy">
          <p className="eyebrow"><span /> LTS SYSTEM AUDIT · 2026.08.25</p>
          <h1>Blender 5.2<br /><span>技术介入地图</span></h1>
          <p>不是“新功能清单”，而是一份面向 AI 电影系统的控制面审计：逐层判断我们能读取什么、可靠控制什么、程序化什么，以及哪里能建立自动纠错闭环。</p>
        </div>
        <div className="b52-summary">
          <article><strong>18</strong><span>技术域</span><small>覆盖场景到交付</small></article>
          <article><strong>5</strong><span>介入层级</span><small>观察 → 闭环</small></article>
          <article><strong>6</strong><span>P0 工程包</span><small>首阶段建设重点</small></article>
          <article><strong>LTS</strong><span>生产基线</span><small>支持至 2028.07</small></article>
        </div>
      </section>

      <section className="section b52-verdict">
        <div className="section-index">00 / 结论</div>
        <div className="b52-verdict-grid">
          <div><p className="eyebrow dark"><span /> VERDICT</p><h2>可以深度介入。<br />最有价值的不是替人点击，<br />而是<span>建立一个电影操作系统。</span></h2></div>
          <div className="verdict-aside"><b>最强介入面</b><p>数据合同、资产治理、程序化场景、镜头模板、渲染交付、自动验收。</p><b>最弱介入面</b><p>演员级表演、审美判断、任意拓扑修复、一次成功的复杂接触与实验物理。</p></div>
        </div>
        <div className="b52-boundary-line"><span>核心原则</span><p>AI 负责提出意图与变更；Blender 编译器负责确定性执行；验证器负责用结构和像素证据决定是否接受。</p></div>
      </section>

      <section className="section b52-depth" id="depth">
        <div className="section-index">01 / 介入深度</div>
        <div className="b52-section-heading"><div><p className="eyebrow dark"><span /> CONTROL SURFACE</p><h2>“能调用 API”<br />不是深度介入。</h2></div><p>真正的深度介入，是从读取状态开始，逐步建立可预测的参数控制、可复用的程序化资产、确定性的场景编译，以及带证据的自动纠错。</p></div>
        <div className="depth-ladder">{interventionLevels.map(([level, title, description]) => <article key={level}><span>{level}</span><div><b>{title}</b><p>{description}</p></div></article>)}</div>
        <div className="depth-interpretation"><b>本项目的目标不是 L2。</b><p>市面上多数“AI for Blender”停留在生成脚本或自动调参。Blender Film Studio 应把 L3 的确定性编译与 L4 的自动验证作为护城河。</p></div>
      </section>

      <section className="section b52-map" id="matrix-52">
        <div className="section-index light">02 / 全技术域审计</div>
        <div className="b52-section-heading"><div><p className="eyebrow"><span /> 18 CONTROL DOMAINS</p><h2>每一层都问同一件事：<br />我们能交付什么？</h2></div><p>“生产稳定”描述 Blender 自身；“介入深度”描述我们能建立到哪一层；“确定性”描述相同输入能否复现相同结构。三者必须分开。</p></div>
        <div className="maturity-overview" aria-label="成熟度统计">{(['stable', 'conditional', 'experimental'] as Maturity[]).map(maturity => <article key={maturity} className={maturity}><strong>{maturityCounts[maturity] ?? 0}</strong><div><b>{maturityMeta[maturity].label}</b><span>{maturityMeta[maturity].note}</span></div></article>)}</div>
        <div className="domain-table" role="table" aria-label="Blender 5.2 技术介入总览">
          <div className="domain-table-head" role="row"><span>技术域</span><span>稳定性</span><span>深度</span><span>确定性</span><span>优先级</span></div>
          {domains.map(domain => <a href={`#${domain.id}`} className="domain-table-row" role="row" key={domain.id}><span><i>{domain.id}</i>{domain.title}</span><MaturityBadge maturity={domain.maturity} /><b>{domain.depth}</b><span>{domain.deterministic}</span><strong className={domain.priority.toLowerCase()}>{domain.priority}</strong></a>)}
        </div>
        <div className="domain-list">{domains.map(domain => <article className="domain-card" id={domain.id} key={domain.id}>
          <div className="domain-card-side"><span>{domain.id}</span><small>{domain.group}</small><b>{domain.depth}</b></div>
          <div className="domain-card-body">
            <header><div><h3>{domain.title}</h3><p>{domain.signal}</p></div><div className="domain-card-meta"><MaturityBadge maturity={domain.maturity} /><span>确定性 {domain.deterministic}</span><strong>{domain.priority}</strong></div></header>
            <div className="domain-analysis"><div className="intervene"><span>深度介入</span><p>{domain.intervene}</p></div><div className="boundary"><span>明确边界</span><p>{domain.boundary}</p></div></div>
            <div className="domain-delivery"><span>建议工程物</span><b>{domain.deliverable}</b></div>
            <div className="domain-sources"><span>官方证据</span>{domain.sources.map(source => <a href={source.href} target="_blank" rel="noreferrer" key={source.href}>{source.label} ↗</a>)}</div>
          </div>
        </article>)}</div>
      </section>

      <section className="section b52-architecture" id="roadmap">
        <div className="section-index light">03 / 系统架构</div>
        <div className="b52-section-heading"><div><p className="eyebrow"><span /> CLOSED LOOP</p><h2>所有深度介入，<br />最终汇入同一闭环。</h2></div><p>一个镜头不是被“生成”出来，而是经过声明、编译、求值、预览、渲染和验收。失败必须能回指到 SceneSpec、资产版本或某个构建步骤。</p></div>
        <div className="b52-flow" aria-label="Blender 5.2 闭环架构图">
          <article><span>01</span><b>Intent</b><small>剧本 · 分镜 · 参考</small></article><i>→</i><article className="contract"><span>02</span><b>SceneSpec</b><small>受限、可验证合同</small></article><i>→</i><article><span>03</span><b>Compiler</b><small>bpy · USD · Nodes</small></article><i>→</i><article><span>04</span><b>Shot Scene</b><small>资产 · 动画 · look</small></article><i>→</i><article><span>05</span><b>Render</b><small>EEVEE → Cycles → EXR</small></article>
        </div>
        <div className="b52-feedback"><span>VALIDATOR</span><b>结构检查</b><b>像素检查</b><b>性能检查</b><b>版本检查</b><p>拒绝 → 精确定位 → 修改上游 → 局部重建 ↺</p></div>
        <div className="package-heading"><p className="eyebrow"><span /> SIX P0 PACKAGES</p><h2>六个工程包，覆盖第一阶段。</h2></div>
        <div className="package-grid">{packages.map(([id, title, description, domainsCovered]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{description}</p><small>{domainsCovered}</small></article>)}</div>
      </section>

      <section className="section b52-risks">
        <div className="section-index">04 / 不介入清单</div>
        <div className="b52-section-heading"><div><p className="eyebrow dark"><span /> HARD BOUNDARIES</p><h2>主动说“不”，<br />也是架构的一部分。</h2></div><p>这些方向看起来最像“一键 AI”，却会让系统失去安全性、可复现性或生产回退路径。第一阶段明确排除。</p></div>
        <div className="exclusion-grid">{exclusions.map(([title, detail], index) => <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
      </section>

      <section className="section b52-plan">
        <div className="section-index light">05 / 推荐顺序</div>
        <div className="plan-heading"><p className="eyebrow"><span /> BUILD ORDER</p><h2>先让一个镜头完全可控，<br />再扩大内容复杂度。</h2></div>
        <div className="timeline">
          <article><span>PHASE 01</span><b>可观察</b><small>0–4 周</small><p>SceneSpec、场景清单、依赖图、日志、golden shot。</p></article>
          <article><span>PHASE 02</span><b>可编译</b><small>4–10 周</small><p>资产库、节点资产、摄影机/灯光模板、幂等构建。</p></article>
          <article><span>PHASE 03</span><b>可交付</b><small>10–16 周</small><p>EEVEE review、Cycles profiles、AOV、EXR、manifest。</p></article>
          <article><span>PHASE 04</span><b>可闭环</b><small>16 周后</small><p>像素/性能回归、局部重建、动画与物理实验。</p></article>
        </div>
        <div className="decision-gate"><span>首个里程碑</span><b>同一个 6 秒镜头，改变焦段、动作节拍或灯位后，只重建受影响部分，并输出可解释的差异报告。</b></div>
      </section>

      <section className="section b52-method" id="sources">
        <div className="section-index">06 / 方法与证据</div>
        <div className="method-52-grid"><div><p className="eyebrow dark"><span /> EVIDENCE POLICY</p><h2>只把官方声明的能力，<br />写成 Blender 5.2 的事实。</h2></div><div><p>本页研究范围是电影制作相关控制面，不是逐项复述整个用户手册。结论以 2026-08-25 为截点，优先使用 Blender Foundation、Blender Developer Documentation 与版本化 API/Manual。</p><p>“深度介入”与“生产成熟度”属于本项目基于接口、可确定性和制作价值作出的工程判断，已与官方事实分开表述。</p></div></div>
        <ol className="references b52-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>Blender 5.2 System Audit</b></div><p>Research tab · Snapshot: 2026-08-25 · LTS support: 2028-07</p><Link href="/">返回技术基线 →</Link></footer>
    </main>
  );
}
