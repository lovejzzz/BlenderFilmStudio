import Link from 'next/link';

type Status = 'ready' | 'partial' | 'research' | 'blocked';

const statusMeta: Record<Status, { label: string; score: string }> = {
  ready: { label: '可生产', score: 'TRL 8–9' },
  partial: { label: '人工监督', score: 'TRL 5–7' },
  research: { label: '研究阶段', score: 'TRL 3–5' },
  blocked: { label: '尚不可靠', score: 'TRL 1–3' },
};

const pipeline = [
  { id: '01', title: '导演意图', state: 'partial', note: '剧本拆解、镜头表、参考图' },
  { id: '02', title: '场景编译', state: 'partial', note: '结构化场景图与验证' },
  { id: '03', title: '数字资产', state: 'research', note: '人物、场景、材质、绑定' },
  { id: '04', title: '表演与摄影', state: 'partial', note: '动作、面部、镜头、灯光' },
  { id: '05', title: '物理与渲染', state: 'ready', note: 'Cycles、EXR、AOV、色彩' },
  { id: '06', title: '神经精修', state: 'research', note: '受控重绘与时序一致性' },
] satisfies { id: string; title: string; state: Status; note: string }[];

const overview = [
  { value: '15', label: '技术环节', detail: '从剧本到母版' },
  { value: '4', label: '成熟度等级', detail: '避免二元判断' },
  { value: '2026.08.25', label: '研究截点', detail: '结论将持续更新' },
];

const stages: {
  id: string;
  group: string;
  title: string;
  status: Status;
  claim: string;
  can: string[];
  cannot: string[];
  route: string;
  sources: { label: string; href: string }[];
}[] = [
  {
    id: 'S01', group: 'PRE', title: '剧本拆解与镜头规划', status: 'partial',
    claim: '语言模型能生成可用初稿，但不能替代导演对节奏、潜台词和表演的判断。',
    can: ['把剧本拆成场次、角色、道具、动作和镜头候选', '输出镜头表、连续性约束、资产清单和结构化 JSON', '基于固定摄影规则检查轴线、景别覆盖和缺失信息'],
    cannot: ['稳定判断某种调度是否真正有戏剧张力', '在长片尺度自动维持隐含叙事、表演弧线与文化语境', '保证一次规划即可直接拍摄，无需导演修订'],
    route: '把 AI 定位为副导演与场记：提案、整理、检查；最终镜头意图由人锁定。',
    sources: [{ label: 'P3D-Bench 2026', href: 'https://arxiv.org/abs/2606.11152' }],
  },
  {
    id: 'S02', group: 'SYS', title: '场景描述与“电影编译器”', status: 'partial',
    claim: '从结构化 SceneSpec 到 Blender 是确定的；从任意自然语言直接得到正确 SceneSpec 仍不稳定。',
    can: ['用 Blender Python API 创建对象、约束、灯光、摄影机与关键帧', '用 OpenUSD 表达层、引用、变体和非破坏性覆盖', '用验证器检查单位、命名、依赖、碰撞和镜头输出'],
    cannot: ['安全地执行任意模型生成脚本而不做隔离和权限控制', '仅凭语言推断所有空间尺寸、资产语义和技术参数', '保证复杂程序第一次运行就可执行、几何正确且结构合理'],
    route: 'LLM 不直接写最终 .blend；先写受限 SceneSpec，再由确定性编译器生成场景。',
    sources: [
      { label: 'Blender Python API 5.2', href: 'https://docs.blender.org/api/current/' },
      { label: 'Blender 官方 MCP', href: 'https://www.blender.org/lab/mcp-server/' },
      { label: 'OpenUSD', href: 'https://www.pixar.com/openusd' },
    ],
  },
  {
    id: 'S03', group: 'AST', title: '资产库检索与场景组装', status: 'partial',
    claim: '“从经过整理的资产库选择并摆放”远比“现场生成所有资产”成熟。',
    can: ['按标签、尺寸、风格和许可检索已有模型', '以 USD/链接库复用同一人物、场景与道具版本', '自动进行粗略布局、实例化和镜头内可见性优化'],
    cannot: ['从杂乱资产库自动找到完全符合美术设计的资产', '自动统一来自不同作者的尺度、拓扑、材质和美术风格', '在没有资产治理的情况下维持跨镜头版本一致性'],
    route: '优先建立“电影资产圣经”：固定 ID、版本、真实尺寸、材质规范和许可来源。',
    sources: [{ label: 'OpenUSD FAQ', href: 'https://openusd.org/release/usdfaq.html' }],
  },
  {
    id: 'S04', group: 'AST', title: '通用物体：图像 / 文本到 3D', status: 'partial',
    claim: '单物体已能快速得到高观感 PBR GLB；隐藏面、零件语义和可变形拓扑仍需整理。',
    can: ['TRELLIS.2 从单图生成高分辨率几何与 PBR 材质', '生成概念验证、远景道具、静态布景和背景资产', '导出 GLB 后在 Blender 中重新布光与渲染'],
    cannot: ['从单张照片知道不可见背面的真实结构', '稳定生成工程正确的独立零件、枢轴、内部结构和四边面流', '保证每个结果无需修洞、减面、重拓扑或重做 UV'],
    route: '把生成结果当高质量毛坯；重要近景资产采用多视图、扫描或人工建模。',
    sources: [
      { label: 'Microsoft TRELLIS.2', href: 'https://github.com/microsoft/TRELLIS.2' },
      { label: '生产级 3D 资产综述', href: 'https://arxiv.org/abs/2604.23629' },
    ],
  },
  {
    id: 'S05', group: 'CHR', title: '数字人物与身份一致性', status: 'research',
    claim: '“像这个人”可以做到，“全身、全角度、近景、可表演的同一个数字演员”尚未端到端解决。',
    can: ['从照片恢复参数化身体、基础头部几何或可驱动 Gaussian Avatar', '用固定角色资产天然保证三维形体和服装的跨镜头一致', '以模板拓扑方法生成可对应的头部资产'],
    cannot: ['从少量照片可靠恢复毛发、口腔、皮肤微结构、服装背面和遮挡区域', '把高相似度、标准拓扑、面部绑定、毛发与服装一次性统一生成', '保证极近景表演达到真人演员和高端扫描资产水平'],
    route: '第一阶段锁定少量人工整理的英雄角色；AI 负责变体与驱动，不负责从零交付。',
    sources: [
      { label: 'DECA', href: 'https://github.com/YadiraF/DECA' },
      { label: 'LHM 可动画人物', href: 'https://openaccess.thecvf.com/content/ICCV2025/papers/Qiu_LHM_Large_Animatable_Human_Reconstruction_Model_for_Single_Image_to_ICCV_2025_paper.pdf' },
      { label: 'TOPOS 2026', href: 'https://arxiv.org/abs/2605.14594' },
    ],
  },
  {
    id: 'S06', group: 'AST', title: '拓扑、UV 与 PBR 材质', status: 'research',
    claim: '静态物体的 PBR 外观进步很快；角色变形所需的边流与材质分解仍是生产断点。',
    can: ['生成 albedo、roughness、metallic 等 PBR 通道', '对静态模型执行减面、重网格、UV 展开和纹理烘焙', '用固定模板保证特定人头的拓扑对应'],
    cannot: ['为任意生成角色自动产生适合特写变形的四边面边流', '从单图可靠分离真实材质与原照片中烘焙的光影', '自动处理所有纹理接缝、透明材质、皮肤层和 UDIM 质量'],
    route: '静态道具允许自动化；英雄角色必须通过模板拓扑或人工 retopo 关卡。',
    sources: [
      { label: 'TRELLIS.2 PBR', href: 'https://github.com/microsoft/TRELLIS.2' },
      { label: '单图材质/灯光歧义', href: 'https://link.springer.com/article/10.1007/s11263-026-02833-z' },
    ],
  },
  {
    id: 'S07', group: 'CHR', title: '骨骼、蒙皮与面部绑定', status: 'partial',
    claim: '标准人形和干净网格的自动绑定可用；任意 AI 网格与电影级面部绑定仍需要技术美术。',
    can: ['Rigify 从匹配好的 meta-rig 生成完整控制系统', '对标准人形执行自动骨骼定位、蒙皮与动作重定向', '研究系统已能处理部分混乱的 AI 生成人形网格'],
    cannot: ['保证肩、手、面部和极端姿势无体积损失或穿插', '自动为任意拓扑创建稳定 FACS、牙齿、舌头与口腔系统', '免除权重绘制、修形目标和镜头级 corrective shapes'],
    route: '角色入库前通过“animation-ready”验收；不把 rigging 留到镜头生成时解决。',
    sources: [
      { label: 'Blender Rigify 5.2', href: 'https://docs.blender.org/manual/en/latest/addons/rigify/index.html' },
      { label: 'HumanRig', href: 'https://openaccess.thecvf.com/content/CVPR2025/papers/Chu_HumanRig_Learning_Automatic_Rigging_for_Humanoid_Character_in_a_Large_CVPR_2025_paper.pdf' },
      { label: 'OmniFaceRig', href: 'https://arxiv.org/abs/2606.08043' },
    ],
  },
  {
    id: 'S08', group: 'PERF', title: '身体动作捕捉与重定向', status: 'partial',
    claim: '普通全身动作已能从视频恢复；被遮挡、快速旋转、手物接触和脚底稳定仍需清理。',
    can: ['从单目视频估计世界坐标中的人体运动与相机关系', '输出 SMPL/SMPL-X 参数并重定向到 Blender 角色', '用多机位或专业动捕显著提高可用性'],
    cannot: ['从任意单机位准确恢复深度、遮挡肢体、手指和衣物运动', '自动消除所有 foot sliding、关节抖动和身体穿插', '只靠文字产生具有演员个性、节奏和细微重量感的表演'],
    route: 'AI 视频先做排练参考；重要镜头使用真人表演捕捉，再进行约束和动画清理。',
    sources: [
      { label: 'DuoMo CVPR 2026', href: 'https://github.com/facebookresearch/DuoMo' },
      { label: '运动生成综述 2026', href: 'https://doi.org/10.1016/j.inffus.2026.104435' },
    ],
  },
  {
    id: 'S09', group: 'PERF', title: '面部、口型、眼神与情绪', status: 'research',
    claim: '口型同步不是电影表演；眼神、停顿、呼吸与细微不对称仍缺少可靠自动解。',
    can: ['从音频生成口型、眨眼、基础表情和头部运动', '从人脸视频捕获表情系数并驱动已有面部 rig', '对固定说话头像获得较稳定的同步效果'],
    cannot: ['从声音唯一推断演员真实的内心表演和视线目标', '在沉默、反应镜头和多人互动中维持自然微表演', '自动处理牙齿、舌头、唇部接触、泪液和皮肤褶皱的全部细节'],
    route: '对白口型可自动打底；眼神、眉眼、呼吸和关键表演 beat 必须允许导演逐层修改。',
    sources: [
      { label: 'ARTalk', href: 'https://github.com/xg-chu/ARTalk' },
      { label: 'SyncAnimation', href: 'https://arxiv.org/abs/2501.14646' },
    ],
  },
  {
    id: 'S10', group: 'PERF', title: '调度、接触与道具交互', status: 'research',
    claim: '粗略走位容易，可信地拿、坐、拥抱、搏斗和交换道具仍是核心难题。',
    can: ['在已知导航空间内规划路径并避开静态障碍', '用 IK、约束、碰撞体和接触关键帧修正动作', '对预定义交互模板稳定复用动作'],
    cannot: ['从一句描述自动求解复杂双手、多人和可变形物体接触', '保证接触时机、受力、抓握区域和角色意图同时正确', '避免所有穿模、漂浮、脚滑和不合理重心'],
    route: '把“接触事件”升级为 SceneSpec 的一等数据，而不是让动作模型隐式猜测。',
    sources: [
      { label: 'Contact-aware Motion', href: 'https://arxiv.org/abs/2403.15709' },
      { label: '人类动作研究缺口', href: 'https://doi.org/10.1016/j.inffus.2026.104435' },
    ],
  },
  {
    id: 'S11', group: 'CAM', title: '摄影机、镜头与轨迹', status: 'ready',
    claim: '明确的相机参数和轨迹可以精确重现；“自动成为好摄影师”仍需导演监督。',
    can: ['精确控制焦段、传感器、光圈、景深、快门和变形宽银幕散景', '从实拍素材解算摄影机运动与镜头畸变', '用约束、曲线和关键帧复现可重复轨迹'],
    cannot: ['从抽象情绪描述唯一决定最有叙事意义的机位', '自动保证复杂调度下构图、遮挡、轴线和节奏一直优秀', '从缺少纹理、强运动模糊的素材稳定恢复真实相机'],
    route: '先让 AI 提供三种可解释镜头方案，导演选定后再锁定数值轨迹。',
    sources: [
      { label: 'Blender Camera Solver', href: 'https://docs.blender.org/manual/en/latest/animation/constraints/motion_tracking/camera_solver.html' },
      { label: 'Blender 摄影机', href: 'https://docs.blender.org/manual/en/latest/render/cameras.html' },
    ],
  },
  {
    id: 'S12', group: 'LOOK', title: '灯光、材质与参考图反推', status: 'partial',
    claim: '在三维场景中布光已经成熟；从一张照片唯一反推出真实灯光和材质在数学上有歧义。',
    can: ['用 HDRI、面光源、灯光组和 PBR 材质建立可重复 look', '从参考图估计主光方向、色温、环境亮度和近似材质', '分别调整光线、材质与曝光并输出灯光分层'],
    cannot: ['从单张 LDR 图像恢复唯一正确的 HDR 环境与表面反射属性', '自动识别艺术上“应该”保留的非物理光线和负补光', '在不同镜头中无需人工即可保持精细 look continuity'],
    route: 'AI 估计只用于起点；最终灯光是显式可编辑 rig，并保存为场景级 look template。',
    sources: [
      { label: 'Materialist 2026', href: 'https://link.springer.com/article/10.1007/s11263-026-02833-z' },
      { label: 'Cycles PBR', href: 'https://www.blender.org/features/rendering/' },
    ],
  },
  {
    id: 'S13', group: 'SIM', title: '刚体、布料、毛发、流体与次级运动', status: 'partial',
    claim: '求解器可用，自动决定正确碰撞体、缓存顺序和物理参数仍不可靠。',
    can: ['对已经正确设置的场景计算刚体、布料、毛发与流体效果', '缓存并重复渲染相同模拟结果', '通过节点与约束把模拟纳入自动化流程'],
    cannot: ['从文字自动估计所有真实材料参数和碰撞近似', '保证复杂角色服装、长发与快速动作一次通过', '在镜头变化后自动判断哪些模拟必须重新烘焙'],
    route: '使用经过测试的模拟预设和依赖图；自动检查穿透、能量爆炸和缓存版本。',
    sources: [
      { label: 'Blender 5.2 Physics', href: 'https://developer.blender.org/docs/release_notes/5.2/physics/' },
      { label: 'Rigid Body Manual', href: 'https://docs.blender.org/manual/en/latest/physics/rigid_body/introduction.html' },
    ],
  },
  {
    id: 'S14', group: 'REN', title: '影院级渲染、色彩与分层合成', status: 'ready',
    claim: '这是整个设想中最成熟的一段：只要输入资产和场景正确，Blender 可以稳定输出高质量母版素材。',
    can: ['Cycles 进行物理路径追踪、全局照明、体积、毛发、运动模糊和景深', '输出 16/32-bit OpenEXR、多层 AOV、Cryptomatte、深度、法线和运动矢量', '用 OCIO/AgX 管理场景线性色彩并进行镜头级合成与调色'],
    cannot: ['用更高采样自动修复错误模型、僵硬表演或差的美术设计', '消除所有渲染时间、显存、噪点和复杂焦散成本', '保证没有统一 OCIO 配置的下游软件看到相同颜色'],
    route: '锁定 Blender 5.2 LTS、EXR 分层规范、色彩配置和确定性渲染清单。',
    sources: [
      { label: 'Blender 5.2 LTS', href: 'https://www.blender.org/releases/5-2/' },
      { label: 'Cycles', href: 'https://docs.blender.org/manual/en/latest/render/cycles/index.html' },
      { label: 'Cryptomatte', href: 'https://docs.blender.org/manual/en/5.2/compositing/types/mask/cryptomatte.html' },
    ],
  },
  {
    id: 'S15', group: 'POST', title: '神经写实化与跨镜头一致性', status: 'research',
    claim: '3D 可提供深度、法线、遮罩和运动真值；生成式精修仍可能重新引入身份漂移和闪烁。',
    can: ['以 Blender 输出的深度、法线、角色 ID 和运动矢量约束重绘', '补充皮肤、毛发、复杂纹理与难以建模的高频细节', '用 3D 角色和镜头作为跨镜头共同结构锚点'],
    cannot: ['保证每一帧严格服从几何、材质、光线和人物身份', '在长镜头和快速运动中完全消除纹理爬动与细节幻觉', '把生成式结果重新无损映射回可编辑的三维资产'],
    route: '神经层必须可关闭、可对比、可按 Cryptomatte 分区，并保留纯 CG 母版作为真值。',
    sources: [
      { label: 'DepthSync ICCV 2025', href: 'https://openaccess.thecvf.com/content/ICCV2025/papers/Dong_DepthSync_Diffusion_Guidance-Based_Depth_Synchronization_for_Scale-_and_Geometry-Consistent_Video_ICCV_2025_paper.pdf' },
      { label: '3D Gaussian Splatting Survey', href: 'https://doi.org/10.1145/3807511' },
    ],
  },
];

const references = [
  ['Blender Foundation', 'Blender 5.2 LTS（2026-07-14，支持至 2028-07）', 'https://www.blender.org/releases/5-2/'],
  ['Blender Foundation', 'Blender Python API 5.2', 'https://docs.blender.org/api/current/'],
  ['Pixar / AOUSD', 'OpenUSD：可组合、非破坏性的电影级场景图', 'https://www.pixar.com/openusd'],
  ['Microsoft Research', 'TRELLIS.2：高保真图像到 3D 与 PBR 资产', 'https://github.com/microsoft/TRELLIS.2'],
  ['Wu et al.', 'Toward Production-Ready 3D Asset Generation（2026）', 'https://arxiv.org/abs/2604.23629'],
  ['Wang et al.', 'DuoMo：单目视频世界空间人体运动恢复（CVPR 2026）', 'https://github.com/facebookresearch/DuoMo'],
  ['Chu et al.', 'HumanRig：AI 生成人形的自动绑定（CVPR 2025）', 'https://openaccess.thecvf.com/content/CVPR2025/papers/Chu_HumanRig_Learning_Automatic_Rigging_for_Humanoid_Character_in_a_Large_CVPR_2025_paper.pdf'],
  ['Chen & Wang', '3D Gaussian Splatting Survey（2026）', 'https://doi.org/10.1145/3807511'],
  ['Liu et al.', 'Materialist：单图逆渲染及其固有歧义（2026）', 'https://link.springer.com/article/10.1007/s11263-026-02833-z'],
  ['SimWorlds', '动态可编辑 4D Blender 场景的自动生成与验证（2026）', 'https://arxiv.org/abs/2607.01766'],
];

function StatusBadge({ status }: { status: Status }) {
  const meta = statusMeta[status];
  return <span className={`status-badge ${status}`}><i />{meta.label}<small>{meta.score}</small></span>;
}

export default function Home() {
  const counts = stages.reduce((acc, stage) => ({ ...acc, [stage.status]: (acc[stage.status] ?? 0) + 1 }), {} as Record<Status, number>);

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="返回顶部"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></a>
        <nav aria-label="研究导航">
          <a href="#pipeline">技术链</a><Link className="route-tab" href="/blender-5-2">Blender 5.2</Link><Link className="route-tab cost-route" href="/cost-model">成本</Link><Link className="route-tab" href="/native-backend-v0-1">Native 后端</Link><Link className="route-tab agenda-route" href="/research-agenda">研究路线</Link><Link className="route-tab" href="/journal">实验日志</Link><Link className="route-tab spec-route" href="/spec-v0-1">规格 v0.1</Link><Link className="route-tab compiler-route" href="/compiler-v0-1">编译实验</Link><Link className="route-tab" href="/pixel-v0-1">像素实验</Link><Link className="route-tab actor-route" href="/actor-v0-1">角色实验</Link><Link className="route-tab contact-route" href="/contact-v0-1">接触实验</Link><Link className="route-tab" href="/grasp-v0-1">抓握设计</Link><Link className="route-tab" href="/grasp-v0-2">抓握编译</Link><Link className="route-tab" href="/physics-v0-1">物理支撑</Link><Link className="route-tab" href="/trajectory-v0-1">轨迹烘焙</Link><Link className="route-tab" href="/trajectory-v0-2">轨迹编译</Link><Link className="route-tab" href="/security-v0-1">路径安全</Link><Link className="route-tab" href="/asset-security-v0-1">资产净化</Link><Link className="route-tab" href="/autoexec-boundary-v0-1">Autoexec 边界</Link><Link className="route-tab" href="/worker-containment-v0-1">Worker 隔离</Link><Link className="route-tab" href="/worker-launch-contract-v0-1">Worker 启动合同</Link><Link className="route-tab" href="/linux-worker-preflight-v0-1">Linux Worker 预检</Link><Link className="route-tab" href="/worker-host-capacity-v0-1">Worker 容量准入</Link><Link className="route-tab" href="/resource-budget-v0-1">资源预算</Link><Link className="route-tab" href="/compile-receipt-v0-1">编译收据</Link><Link className="route-tab" href="/review-dailies-v0-1">完整样片</Link><Link className="route-tab" href="/review-proxy-repro-v0-1">代理复现</Link><Link className="route-tab" href="/dither-isolation-v0-1">Dither 隔离</Link><Link className="route-tab" href="/eevee-sampling-factorial-v0-1">采样因果</Link><Link className="route-tab" href="/eevee-sampling-dose-response-v0-1">采样剂量</Link><Link className="route-tab" href="/eevee-gi-reprojection-factorial-v0-1">GI×Temporal</Link><Link className="route-tab" href="/eevee-process-history-isolation-v0-1">进程隔离</Link><Link className="route-tab" href="/dual-output-localization-v0-1">EXR×PNG</Link><Link className="route-tab" href="/eevee-thread-count-factorial-v0-1">线程 1×8</Link><Link className="route-tab" href="/eevee-repeated-render-boundary-v0-1">同 PID render</Link><Link className="route-tab" href="/production-tolerance-holdout-v0-1">生产容差</Link><Link className="route-tab" href="/temporal-residual-holdout-v0-1">连续时间门</Link><Link className="route-tab" href="/blind-temporal-review-v0-1">匿名审片</Link><Link className="route-tab" href="/frame-history-isolation-v0-1">frame 38 历史</Link>
          <Link className="route-tab" href="/linux-amd64-compiler-repro-v0-1">Worker 编译复现</Link>
          <Link className="route-tab" href="/codex-to-blender-worker-v0-1">Codex → Blender</Link>
          <Link className="route-tab" href="/codex-worker-pixels-v0-1">Worker 浮点像素</Link>
          <Link className="route-tab" href="/codex-worker-sequence-v0-1">Worker 连续序列</Link>
          <Link className="route-tab" href="/codex-worker-production-passes-v0-1">Worker 生产通道</Link>
          <Link className="route-tab" href="/quality-cost-holdout-v0-1">质量 × 成本</Link>
          <Link className="route-tab" href="/resolution-holdout-v0-1">分辨率 Holdout</Link>
          <Link className="route-tab" href="/motion-blur-holdout-v0-1">运动模糊 Holdout</Link>
          <Link className="route-tab" href="/depth-of-field-holdout-v0-1">景深 Holdout</Link>
          <Link className="route-tab" href="/focus-intent-review-v0-1">焦点意图盲评</Link>
          <Link className="route-tab" href="/repeated-frame-mode-switch-v0-1">同 PID 模式</Link>
          <Link className="route-tab" href="/pass-domain-localization-v0-1">Pass 域定位</Link>
          <Link className="route-tab" href="/fixed-jitter-intervention-v0-1">固定抖动干预</Link>
          <Link className="route-tab" href="/sampling-quality-holdout-v0-1">采样质量代价</Link>
          <Link className="route-tab" href="/quadrature-cost-holdout-v0-2">多抖动成本曲线</Link>
          <Link className="route-tab" href="/quadrature-temporal-holdout-v0-1">Q8 连续时间门</Link>
          <Link className="route-tab" href="/human-quadrature-review-v0-1">B34 公开失盲</Link>
          <Link className="route-tab" href="/delayed-disclosure-review-v0-2">B35 延迟披露</Link>
          <Link className="route-tab" href="/temporal-accumulation-v0-1">D9.1 时序累积</Link>
          <Link className="route-tab" href="/blender-pass-adapter-v0-1">D10.1 Pass Adapter</Link>
          <Link className="route-tab" href="/blender-temporal-composition-v0-1">D11 组合反例</Link>
          <Link className="route-tab" href="/blender-nearest-integer-temporal-recovery-v0-1">D11.1 整数恢复</Link>
          <Link className="route-tab" href="/blender-projective-subpixel-reconstruction-v0-1">D12 亚像素</Link>
          <Link className="route-tab" href="/blender-static-vector-floor-v0-1">D12.2 静态底噪</Link>
          <Link className="route-tab" href="/blender-static-nonplanar-multiowner-v0-1">D12.3 多主体</Link>
          <Link className="route-tab" href="/blender-static-zero-headroom-localization-v0-1">D12.4 像素定位</Link>
          <Link className="route-tab" href="/blender-static-radius-intervention-v0-1">D12.5 半径干预</Link>
          <Link className="route-tab" href="/blender-static-interior-risk-localization-v0-1">D12.6 局部风险</Link>
          <Link className="route-tab" href="/blender-motion-aware-curvature-risk-holdout-v0-1">D12.9 新鲜运动门</Link>
          <Link className="route-tab" href="/blender-owner-token-pass-v0-1">D12.10 Owner Token</Link>
          <Link className="route-tab" href="/blender-material-index-owner-integration-v0-1">D12.11 Material Owner</Link>
          <Link className="route-tab" href="/blender-material-owner-one-sided-curvature-v0-1">D12.12 单侧曲率</Link>
          <Link className="route-tab" href="/blender-material-owner-one-sided-curvature-holdout-v0-1">D12.12-H1 留出</Link>
          <Link className="route-tab" href="/blender-material-owner-quality-coupling-derivation-v0-1">D12.13 全局阈值</Link>
          <Link className="route-tab" href="/blender-material-owner-rigid-directional-calibration-v0-1">D12.14 刚体校准</Link>
          <Link className="route-tab" href="/blender-material-owner-rigid-directional-render-holdout-v0-1">D12.14-H1 工具失败</Link>
          <Link className="route-tab" href="/blender-projective-depth-position-oracle-v0-1">D12.14-P1 投影修复</Link>
          <Link className="route-tab" href="/blender-projective-depth-formal-invalidation-v0-1">D12.14-H2 正式调用失效</Link><Link className="route-tab" href="/formal-runner-admission-totality-v0-1">B53-E1 准入总路径</Link><Link className="route-tab" href="/admission-gated-native-compiler-v0-1">B54-E1 原生编译器准入</Link><Link className="route-tab" href="/budgeted-native-child-pid-receipt-v0-1">B55-E1 原生 PID Receipt</Link><Link className="route-tab" href="/production-compiler-entry-promotion-v0-1">B56-E1 生产编译入口</Link><Link className="route-tab" href="/production-disk-jit-readmission-v0-1">B57-E1 磁盘即时再准入</Link><Link className="route-tab" href="/cinematic-render-repro-cost-v0-1">B61-E1 Cycles 复现与成本</Link>
        </nav>
        <span className="edition">Baseline 01</span>
      </header>

      <section className="hero" id="top">
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-copy">
          <p className="eyebrow"><span /> RESEARCH DOSSIER · 研究基线 01</p>
          <h1>AI 能否把导演意图<br />编译成<span>影院级 Blender 镜头？</span></h1>
          <p className="dek">一份面向实际制作的技术可行性调查：逐环节区分“已经可生产”、“需要人工监督”、“仍属研究阶段”和“尚不可可靠实现”。</p>
          <div className="hero-actions"><a className="primary-button" href="#pipeline">查看技术链 <span>↓</span></a><a className="text-link" href="#method">阅读判定方法</a></div>
        </div>
        <aside className="hypothesis">
          <p className="card-kicker">核心假设</p>
          <blockquote>不让 AI 直接猜最终像素，而让它生成一个可编辑、可验证、可重复渲染的三维世界。</blockquote>
          <div className="signal"><span className="signal-dot" /><div><b>结论：部分成立</b><small>渲染端成熟，内容自动化仍有断点</small></div></div>
        </aside>
        <div className="hero-stats">{overview.map((item) => <div key={item.label} className="stat"><strong>{item.value}</strong><span>{item.label}</span><small>{item.detail}</small></div>)}</div>
      </section>

      <section className="section thesis" id="verdict">
        <div className="section-index">00 / 核心结论</div>
        <div className="thesis-main">
          <p className="eyebrow dark"><span /> VERDICT</p>
          <h2>可以做出非常好的视频，<br />但前提不是“一键生成”，<br />而是<span>受约束的混合制作。</span></h2>
        </div>
        <div className="thesis-notes">
          <article><b>Blender 已解决</b><p>确定世界的可编辑性、跨镜头结构一致性、物理渲染、高动态范围与分层后期。</p></article>
          <article><b>AI 正在解决</b><p>场景初稿、物体资产、动作捕捉、镜头提案、参考图分析与自动质检。</p></article>
          <article><b>仍未解决</b><p>任意数字演员、电影级微表演、复杂接触、单图真实世界恢复与全片艺术判断。</p></article>
        </div>
      </section>

      <section className="section pipeline-section" id="pipeline">
        <div className="section-index light">01 / 系统总览</div>
        <div className="section-heading">
          <div><p className="eyebrow"><span /> THE PIPELINE</p><h2>电影不是一次生成，<br />而是一条可验证的技术链</h2></div>
          <p>只要其中一个环节不稳定，影院级渲染也只会把错误渲染得更清楚。因此本报告以生产链，而不是模型排行榜为研究单位。</p>
        </div>
        <div className="legend inverse" aria-label="成熟度图例"><span><i className="ready" /> 可生产</span><span><i className="partial" /> 人工监督</span><span><i className="research" /> 研究阶段</span><span><i className="blocked" /> 尚不可靠</span></div>
        <div className="pipeline-map">
          {pipeline.map((item, index) => <article className={`pipeline-node ${item.state}`} key={item.id}><div className="node-top"><span>{item.id}</span><i /></div><h3>{item.title}</h3><p>{item.note}</p>{index < pipeline.length - 1 && <b className="connector" aria-hidden="true">→</b>}</article>)}
        </div>
        <div className="truth-diagram">
          <div className="truth-title"><span>三种“真实”</span><b>不要混为一谈</b></div>
          <div className="truth-card solved"><small>01</small><h3>结构真实</h3><p>位置、尺度、遮挡、镜头、碰撞</p><strong>3D 最擅长</strong></div>
          <div className="truth-card conditional"><small>02</small><h3>外观真实</h3><p>材质、皮肤、毛发、光影、高频细节</p><strong>取决于资产</strong></div>
          <div className="truth-card open"><small>03</small><h3>表演真实</h3><p>意图、眼神、重量、停顿、人物关系</p><strong>最大缺口</strong></div>
        </div>
      </section>

      <section className="section matrix-section" id="matrix">
        <div className="section-index">02 / 技术成熟度</div>
        <div className="matrix-heading">
          <div><p className="eyebrow dark"><span /> 15 TECHNICAL LINKS</p><h2>逐环节审计</h2></div>
          <div className="count-bars" aria-label="成熟度统计">
            {(['ready','partial','research','blocked'] as Status[]).map(status => <div className={`count ${status}`} key={status}><span style={{ width: `${Math.max(8, (counts[status] ?? 0) / stages.length * 100)}%` }} /><b>{counts[status] ?? 0}</b><small>{statusMeta[status].label}</small></div>)}
          </div>
        </div>

        <div className="stage-list">
          {stages.map((stage) => (
            <article className="stage-card" id={stage.id} key={stage.id}>
              <div className="stage-side"><span>{stage.id}</span><small>{stage.group}</small></div>
              <div className="stage-body">
                <div className="stage-title"><div><h3>{stage.title}</h3><p>{stage.claim}</p></div><StatusBadge status={stage.status} /></div>
                <div className="capability-grid">
                  <div className="can"><h4><i>✓</i> 今天已经可以</h4><ul>{stage.can.map(item => <li key={item}>{item}</li>)}</ul></div>
                  <div className="cannot"><h4><i>×</i> 今天仍不能可靠做到</h4><ul>{stage.cannot.map(item => <li key={item}>{item}</li>)}</ul></div>
                </div>
                <div className="research-route"><b>建议工程路线</b><p>{stage.route}</p></div>
                <div className="source-row"><span>证据</span>{stage.sources.map(source => <a href={source.href} target="_blank" rel="noreferrer" key={source.href}>{source.label} ↗</a>)}</div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section architecture-section" id="architecture">
        <div className="section-index light">03 / 推荐架构</div>
        <div className="architecture-heading"><p className="eyebrow"><span /> BUILD THE COMPILER</p><h2>不要让模型直接控制电影。<br />让它提交一个可以检查的世界。</h2></div>
        <div className="architecture-flow" aria-label="推荐系统架构流程图">
          <div className="flow-column inputs"><span>INPUT</span><b>剧本</b><b>角色圣经</b><b>分镜 / 动态预演</b><b>美术与摄影参考</b></div>
          <div className="flow-arrow">→</div>
          <div className="flow-column brain"><span>INTENT LAYER</span><h3>AI 导演助理</h3><p>拆解、提案、补全、检查矛盾</p><small>不直接执行任意代码</small></div>
          <div className="flow-arrow">→</div>
          <div className="flow-column spec"><span>CONTRACT</span><h3>SceneSpec</h3><p>角色 ID · 资产版本 · 空间关系 · 接触事件 · 相机 · 灯光 · 时间</p><small>JSON Schema + USD Layers</small></div>
          <div className="flow-arrow">→</div>
          <div className="flow-column blender"><span>DETERMINISTIC CORE</span><h3>Blender Compiler</h3><p>组装 · 绑定 · 约束 · 模拟 · 渲染</p><small>Python API · 受限操作集</small></div>
          <div className="flow-arrow">→</div>
          <div className="flow-column outputs"><span>OUTPUT</span><b>EXR 母版</b><b>AOV / Cryptomatte</b><b>预览 MP4</b><b>镜头报告</b></div>
        </div>
        <div className="feedback-loop"><span>视觉质检</span><i>构图</i><i>穿插</i><i>脚滑</i><i>视线</i><i>身份</i><i>曝光</i><b>发现问题 → 修改 SceneSpec → 只重算受影响环节 ↺</b></div>

        <div className="hybrid-stack">
          <div className="stack-copy"><p className="eyebrow"><span /> HIGHEST-CEILING ROUTE</p><h2>质量上限最高的不是纯 AI，也不是纯 CG。</h2><p>推荐把 Blender 作为“结构真值层”，把生成模型限制在“可选的外观精修层”。这能保留三维世界的一致性与可重渲染性，同时补足真人皮肤、毛发和复杂纹理。</p></div>
          <div className="stack-visual">
            <div><span>01</span><b>Blender 真值层</b><small>RGB · Depth · Normal · Motion · IDs</small></div>
            <i>↓</i>
            <div><span>02</span><b>受控神经精修</b><small>只在许可区域补充高频外观</small></div>
            <i>↓</i>
            <div><span>03</span><b>一致性验证</b><small>与纯 CG 基线逐帧比较</small></div>
          </div>
        </div>
      </section>

      <section className="section experiment-section" id="experiment">
        <div className="section-index">04 / 首个实验</div>
        <div className="experiment-grid">
          <div className="experiment-copy"><p className="eyebrow dark"><span /> MVP — SHOT 001</p><h2>先证明一个镜头，<br />不要先承诺一部电影。</h2><p>选择一个足够困难、又可以量化的封闭场景，验证“导演意图 → SceneSpec → Blender → EXR”的核心闭环。</p></div>
          <div className="shot-board">
            <div className="shot-frame" aria-label="镜头实验示意图">
              <div className="window-light" /><div className="subject"><span /></div><div className="table-prop" /><div className="camera-ray ray-one" /><div className="camera-ray ray-two" /><div className="camera-icon">CAM</div>
              <span className="frame-label">50 mm · T2.8 · 6 sec · DOLLY IN</span>
            </div>
            <div className="shot-notes"><span>单一角色</span><span>固定室内</span><span>一次道具接触</span><span>一次焦点转移</span><span>6 秒镜头</span></div>
          </div>
        </div>
        <div className="acceptance">
          <article><span>01</span><b>可重复</b><p>同一 SceneSpec 两次构建得到相同结构与镜头。</p></article>
          <article><span>02</span><b>可编辑</b><p>焦段、动作节拍、灯位和资产可以局部修改。</p></article>
          <article><span>03</span><b>可验证</b><p>自动检测穿插、脚滑、曝光和输出完整性。</p></article>
          <article><span>04</span><b>可交付</b><p>输出 EXR、多层 AOV、预览与机器可读报告。</p></article>
        </div>
      </section>

      <section className="section method-section" id="method">
        <div className="section-index light">05 / 研究方法</div>
        <div className="method-grid">
          <div><p className="eyebrow"><span /> EVIDENCE STANDARD</p><h2>科研态度意味着：<br />能展示 ≠ 能生产。</h2></div>
          <div className="method-levels">
            <article><StatusBadge status="ready" /><p>可重复、可编辑、有稳定接口与输出规范；失败可定位，能进入常规生产。</p></article>
            <article><StatusBadge status="partial" /><p>主要能力存在，但需要人工清理、限定输入、预设资产或镜头级修正。</p></article>
            <article><StatusBadge status="research" /><p>论文或代码已经证明方向，但泛化、许可、速度、质量或工具集成尚不足。</p></article>
            <article><StatusBadge status="blocked" /><p>只有零散 demo，或缺少一般化、可重复、可编辑的公开证据。</p></article>
          </div>
        </div>
        <div className="caveat"><b>本报告不声称穷尽所有工具。</b><p>判定对象是能力类别，而非单一产品。商业工具可能在特定数据与人工服务支持下达到更高完成度；若其方法、权重或失败率不可审计，则不据此上调通用技术成熟度。</p></div>
      </section>

      <section className="section evidence-section" id="evidence">
        <div className="section-index">06 / 主要证据</div>
        <div className="evidence-heading"><div><p className="eyebrow dark"><span /> PRIMARY SOURCES</p><h2>可追溯，而不是“听说可以”</h2></div><p>优先使用官方文档、官方代码仓库、同行评审论文与原始项目页面。每一项技术卡片内还保留更直接的证据链接。</p></div>
        <ol className="references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
      </section>

      <footer>
        <div><span className="brand-mark">BFS</span><b>Blender Film Studio</b></div>
        <p>Research Baseline 01 · Snapshot: 2026-08-25 · America/New_York</p>
        <a href="https://github.com/lovejzzz/BlenderFilmStudio" target="_blank" rel="noreferrer">GitHub Repository ↗</a>
      </footer>
    </main>
  );
}
