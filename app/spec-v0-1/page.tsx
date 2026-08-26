import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'SceneSpec v0.1 可执行合同｜Blender Film Studio',
  description: '首个可执行的 AI → Blender 镜头合同：JSON Schema、语义规则、安全边界、22 个测试样例与研究母版。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/spec-v0-1/' },
  openGraph: {
    title: 'SceneSpec v0.1 可执行合同',
    description: '让非法镜头数据在 Blender 启动前被拒绝。',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/spec-v0-1/',
  },
  twitter: { card: 'summary_large_image', title: 'SceneSpec v0.1', description: '10 个合同块、22 个测试样例、四层验证与零任意代码。' },
};

const rootBlocks = [
  ['01', 'shot', '镜头 ID、帧区间、24fps、米制单位、随机种子和激活摄影机', '冻结时空基准'],
  ['02', 'assets', '资产 ID、类型、受限 URI、版本、SHA-256、许可、变换和可见性', '建立可追溯世界'],
  ['03', 'actors', '角色 ID、CHARACTER 资产引用、rig profile 与身份锁', '不把角色当普通物体'],
  ['04', 'cameras', '焦段、传感器、光圈、焦距、快门角、显式变换和受限关键帧', '摄影参数可重现'],
  ['05', 'lights', '灯型、scene-linear 颜色、能量、尺寸和变换', '灯光不是参考图烘焙'],
  ['06', 'world', '环境颜色与强度', '最小世界状态'],
  ['07', 'events', '接触、视线、对白与 cue 的帧和主体', '交互成为一等数据'],
  ['08', 'render', '预览/终稿引擎、4K、采样、EXR、AOV 和输出目录', '绑定研究母版'],
  ['09', 'security', '禁网、禁任意 Python、资产根目录和操作白名单', '模型不能直达系统'],
  ['10', 'provenance', 'brief、创建者、UTC 时间、来源、许可和哈希', '结论可追溯'],
];

const validationLayers = [
  ['L1', 'JSON Schema', '类型、必填字段、枚举、范围、格式、未知字段与固定版本。', '机器可解释的结构拒绝'],
  ['L2', '语义规则', '帧区间、全局唯一 ID、摄影机引用、角色资产类型、事件范围与主体存在性。', '跨字段一致性'],
  ['L3', '安全规则', '拒绝绝对路径、URL、路径穿越、未授权资产根和 renders/ 之外的输出。', '执行前权限边界'],
  ['L4', 'BuildPlan 与 Blender 复验', '解析资产、验证真实 SHA-256、冻结 BuildPlan，并在 Blender 5.2 内再次验证计划和资产。', '双净构建已通过'],
];

const validFixtures = ['V01 基准镜头', 'V02 标题变体', 'V03 焦段变体', 'V04 新增道具', 'V05 新增补光', 'V06 合法角色', 'V07 合法接触', 'V08 偏移帧区间', 'V09 世界变体', 'V10 关闭降噪', 'V11 摄影机 Dolly'];
const invalidFixtures = ['I01 未知根字段', 'I02 错误版本', 'I03 倒置帧区间', 'I04 重复 ID', 'I05 不存在的摄影机', 'I06 路径穿越', 'I07 开启网络', 'I08 缺失许可', 'I09 越界事件', 'I10 角色引用道具', 'I11 摄影机关键帧越界'];

const unresolved = [
  ['U01', 'OCIO 配置与哈希', 'ACEScg 已选为研究编码，但 Phase 1 前必须选择真实 ACES 2 配置文件并锁定 SHA-256。'],
  ['U02', '跨 GPU 像素容差', '结构必须严格一致；不同设备、驱动、去噪路径的像素阈值需要实测，不能先写死。'],
  ['U03', '完整动画数据模型', 'v0.1 已支持摄影机受限 transformKeys，但仍不定义动作片段、retarget、约束图与 performance layer。'],
  ['U04', 'USD 映射', 'SceneSpec 是意图合同，USD 是场景组合层；哪些字段进入 USD schema、哪些留在 manifest 尚待验证。'],
  ['U05', '像素验收合同', '结构编译已通过；仍需冻结 OCIO、EXR 通道与元数据检查、NaN/Inf 扫描和像素差异阈值。'],
  ['U06', '合法许可词表', 'v0.1 要求非空许可，但尚未限制为可批准的 SPDX/项目内部许可清单。'],
];

const sample = `{
  "specVersion": "0.1.0",
  "shot": {
    "id": "SHOT_001",
    "frameStart": 1,
    "frameEnd": 144,
    "frameRate": { "numerator": 24, "denominator": 1 },
    "unitScaleMeters": 1,
    "seed": 240825,
    "activeCamera": "CAM_MAIN"
  },
  "render": {
    "outputProfile": "BFS_RESEARCH_MASTER_0_1",
    "previewEngine": "BLENDER_EEVEE",
    "finalEngine": "CYCLES",
    "fileFormat": "OPEN_EXR_MULTILAYER",
    "compression": "ZIP_LOSSLESS"
  },
  "security": {
    "networkAccess": false,
    "arbitraryPython": false
  }
}`;

const references = [
  ['JSON Schema', 'Draft 2020-12 Core and Validation', 'https://json-schema.org/draft/2020-12'],
  ['OpenUSD', 'Scene description and composition', 'https://openusd.org/release/intro.html'],
  ['OpenEXR', 'Technical Introduction', 'https://openexr.com/en/latest/TechnicalIntroduction.html'],
  ['OpenEXR', 'Standard attributes', 'https://openexr.com/en/latest/StandardAttributes.html'],
  ['Blender 5.2', 'Output properties and multi-layer EXR', 'https://docs.blender.org/manual/en/5.2/render/output/properties/output.html'],
  ['Blender 5.2', 'Color management system configuration', 'https://docs.blender.org/manual/en/5.2/render/color_management/system_configuration.html'],
  ['Academy', 'ACES 2 Output Transforms', 'https://docs.acescentral.com/system-components/output-transforms/'],
  ['DCI', 'Digital Cinema System Specification 1.5.0', 'https://www.dcimovies.com/dci-specification/'],
];

export default function SpecV01Page() {
  return (
    <main className="spec-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="规格导航"><Link href="/">技术基线</Link><Link href="/blender-5-2">Blender 5.2</Link><Link href="/cost-model">成本</Link><Link href="/research-agenda">研究路线</Link><Link className="compiler-route" href="/compiler-v0-1">编译实验</Link><Link href="/pixel-v0-1">像素实验</Link><Link className="actor-route" href="/actor-v0-1">角色实验</Link><Link className="contact-route" href="/contact-v0-1">接触实验</Link><Link href="/grasp-v0-1">手指抓握</Link><a href="#tests">测试</a></nav>
        <span className="edition spec-edition">Spec 0.1</span>
      </header>

      <section className="spec-hero" id="top">
        <div className="spec-grid" aria-hidden="true" />
        <div className="spec-hero-copy"><p className="eyebrow"><span /> EXECUTABLE CONTRACT · EXPERIMENTAL</p><h1>让非法镜头数据，<br />在 <span>Blender 启动前</span><br />被拒绝。</h1><p>SceneSpec v0.1 不是自然语言提示词，也不是 .blend 文件。它是 AI 与确定性编译器之间受限、可版本化、可测试的合同。</p></div>
        <div className="spec-terminal" aria-label="规格验证摘要"><header><i /><i /><i /><span>validate:spec</span></header><code>PASS V01_BASE_B02</code><code>PASS V11_CAMERA_DOLLY</code><code>PASS I06_PATH_TRAVERSAL</code><code>PASS I11_CAMERA_KEY_OUTSIDE_SHOT</code><b>22 / 22 FIXTURES PASSED</b></div>
        <div className="spec-stats"><article><strong>10</strong><span>根合同块</span><small>shot → provenance</small></article><article><strong>22</strong><span>正反样例</span><small>11 接受 / 11 拒绝</small></article><article><strong>4</strong><span>已执行验证层</span><small>含 BuildPlan + Blender</small></article><article><strong>0</strong><span>任意代码权限</span><small>禁网 · 禁任意 Python</small></article></div>
      </section>

      <section className="section spec-verdict">
        <div className="section-index">00 / 当前状态</div>
        <div className="spec-verdict-grid"><div><p className="eyebrow dark"><span /> FIRST EXECUTABLE ARTIFACT</p><h2>研究从“可行”，<br />进入<span>可拒绝。</span></h2></div><div><b>已经证明</b><p>合同能够机械区分 22 个预设的合法与非法镜头变体，并已通过 B01/B02 原生 Blender 编译实验。</p><b>尚未证明</b><p>合同可以完整表达电影表演，或能跨 GPU 得到已校准的像素一致性。</p></div></div>
        <div className="spec-status-line"><span>STATUS</span><b>EXPERIMENTAL · v0.1.0</b><p>允许破坏性变更；只有通过 fixtures、编译实验和迁移测试后，才进入 v0.2。</p></div>
      </section>

      <section className="section spec-contract" id="contract">
        <div className="section-index light">01 / 合同架构</div>
        <div className="spec-heading"><div><p className="eyebrow"><span /> RESTRICTED PIPE</p><h2>模型只能提交数据，<br />不能提交<span>执行权。</span></h2></div><p>JSON Schema 先验证局部结构，语义层再检查跨字段引用与安全路径。只有完全通过，才允许生成不可变 BuildPlan；Blender 永远不直接消费模型文本。</p></div>
        <div className="spec-flow"><article><span>01</span><b>Director Intent</b><small>自然语言 · 分镜 · 参考</small></article><i>→</i><article className="agent"><span>02</span><b>Codex Proposal</b><small>只提出 SceneSpec</small></article><i>→</i><article className="gate"><span>03</span><b>Validation Gates</b><small>Schema · 语义 · 安全</small></article><i>→</i><article><span>04</span><b>BuildPlan</b><small>不可变 · 可 diff</small></article><i>→</i><article><span>05</span><b>Blender Compiler</b><small>bpy data API · 已执行</small></article></div>
        <div className="root-blocks">{rootBlocks.map(([id, name, content, purpose]) => <article key={name}><span>{id}</span><h3>{name}</h3><p>{content}</p><small>{purpose}</small></article>)}</div>
      </section>

      <section className="section spec-anatomy">
        <div className="section-index">02 / 数据剖面</div>
        <div className="spec-heading dark-heading"><div><p className="eyebrow dark"><span /> HUMAN-READABLE, MACHINE-STRICT</p><h2>读起来像制作单，<br />执行时像 API 合同。</h2></div><p>示例省略了资产、摄影机和灯光的完整字段；真实文档不允许省略，也不允许出现 schema 之外的未知字段。</p></div>
        <div className="spec-code"><div><header><span>scene.spec.json</span><small>excerpt · v0.1.0</small></header><pre><code>{sample}</code></pre></div><aside><article><span>STRICT</span><b>additionalProperties: false</b><p>模型不能偷偷增加编译器不理解的指令。</p></article><article><span>PINNED</span><b>specVersion: 0.1.0</b><p>版本不匹配时明确迁移或拒绝，不静默猜测。</p></article><article><span>REFERENTIAL</span><b>stable global IDs</b><p>摄影机、角色和事件主体必须真实存在且类型正确。</p></article></aside></div>
      </section>

      <section className="section spec-validation">
        <div className="section-index light">03 / 验证层</div>
        <div className="spec-heading"><div><p className="eyebrow"><span /> DEFENSE IN DEPTH</p><h2>Schema 必要，<br />但远远不够。</h2></div><p>JSON Schema 无法自然表达 frameEnd 必须晚于 frameStart、actor 必须引用 CHARACTER 等所有关系，因此明确增加独立语义层。</p></div>
        <div className="validation-layers">{validationLayers.map(([id, title, content, result]) => <article key={id}><span>{id}</span><small>ACTIVE</small><h3>{title}</h3><p>{content}</p><b>{result}</b></article>)}</div>
        <div className="security-invariants"><span>不可协商的 v0.1 安全常量</span><div><b>networkAccess = false</b><b>arbitraryPython = false</b><b>assets/ 或 library/</b><b>outputs 只在 renders/</b><b>操作必须在白名单</b></div></div>
      </section>

      <section className="section spec-tests" id="tests">
        <div className="section-index">04 / Fixtures</div>
        <div className="spec-heading dark-heading"><div><p className="eyebrow dark"><span /> 22 CONTRACT TESTS</p><h2>正例证明表达力，<br />反例证明边界。</h2></div><p>每个测试从相同 B02 基准文档派生，只改变目标字段。验证器必须同时匹配预期 valid/invalid 状态和关键错误代码。</p></div>
        <div className="fixture-board"><div className="valid"><header><span>ACCEPT</span><b>11 / 11</b></header>{validFixtures.map(item => <p key={item}><i>✓</i>{item}</p>)}</div><div className="invalid"><header><span>REJECT</span><b>11 / 11</b></header>{invalidFixtures.map(item => <p key={item}><i>×</i>{item}</p>)}</div></div>
        <div className="test-command"><span>可重复运行</span><code>npm run validate:spec</code><p>验证器也可以接收一个或多个外部 SceneSpec 文件，输出 VALID / INVALID、错误代码、字段路径和原因。</p></div>
      </section>

      <section className="section output-spec">
        <div className="section-index light">05 / OutputSpec v0.1</div>
        <div className="spec-heading"><div><p className="eyebrow"><span /> RESEARCH MASTER</p><h2>先冻结研究母版，<br />不冒充院线交付。</h2></div><p>OpenEXR 支持高动态范围、多通道和标准元数据；ACES 2 提供到具体显示设备的输出变换。但正确容器和色彩空间仍不能自动保证电影感。</p></div>
        <div className="output-profile"><article><span>PICTURE</span><b>3840 × 2160</b><small>24 fps · 180° shutter · square pixels</small></article><article><span>ENCODING</span><b>scene-linear ACEScg</b><small>具体 OCIO config + hash 待 Phase 1 锁定</small></article><article><span>MASTER</span><b>Multi-layer OpenEXR</b><small>HALF · ZIP lossless · premultiplied alpha</small></article><article><span>PASSES</span><b>6 required</b><small>Combined · Alpha · Depth · Normal · Vector · Cryptomatte</small></article></div>
        <div className="nonclaims"><b>明确不声称</b><p>这不是 DCP，不证明 DCI 合规，不把 ACEScg 当成显示正确性的充分条件，也不把 16-bit float 当成电影感的充分条件。</p></div>
      </section>

      <section className="section spec-open">
        <div className="section-index">06 / 未冻结问题</div>
        <div className="spec-heading dark-heading"><div><p className="eyebrow dark"><span /> OPEN DECISIONS</p><h2>v0.1 有意保持小，<br />不假装解决全部电影语义。</h2></div><p>这些问题不阻止第一轮 B01/B02 编译实验，却会阻止角色、跨机渲染或正式交付。每项必须用实验升级，而不是凭设计文档升级。</p></div>
        <div className="unresolved-grid">{unresolved.map(([id, title, detail]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
        <div className="next-compiler"><span>COMPLETED MILESTONES</span><div><h3>SceneSpec → BuildPlan → Blender → 4K EXR</h3><p>B01/B02 双净构建已经通过；固定 ACES 2 后的 4 个代表帧也完成双渲染与逐像素比较。<Link href="/pixel-v0-1">查看 PixelSpec、mastering 与成本实测 →</Link></p></div></div>
      </section>

      <section className="section spec-sources" id="sources">
        <div className="section-index light">07 / 规格文件与证据</div>
        <div className="spec-heading"><div><p className="eyebrow"><span /> AUDITABLE ARTIFACTS</p><h2>网页解释合同，<br />仓库里的文件执行合同。</h2></div><p>所有规格和 fixtures 都以文本进入版本控制；页面只是人类可读说明，不能成为实现的唯一事实来源。</p></div>
        <div className="artifact-links"><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/specs/scene-spec.v0.1.schema.json" target="_blank" rel="noreferrer"><span>JSON SCHEMA</span><b>scene-spec.v0.1.schema.json ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/specs/output-spec.v0.1.json" target="_blank" rel="noreferrer"><span>OUTPUT PROFILE</span><b>output-spec.v0.1.json ↗</b></a><a href="https://github.com/lovejzzz/BlenderFilmStudio/blob/main/specs/fixtures/scene-spec-fixtures.v0.1.json" target="_blank" rel="noreferrer"><span>TEST SUITE</span><b>22 fixtures ↗</b></a></div>
        <ol className="references spec-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>SceneSpec v0.1</b></div><p>Executable artifact · Experimental · 22/22 fixtures passing</p><Link href="/pixel-v0-1">进入像素实验 →</Link></footer>
    </main>
  );
}
