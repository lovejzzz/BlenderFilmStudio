import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: '成本模型｜Blender Film Studio',
  description: '研究 Codex CLI + Blender 工作流的真实成本：订阅、API、渲染、硬件、资产、人工与返工。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/cost-model/' },
  openGraph: {
    title: 'AI → Blender 电影工作流成本模型',
    description: '不使用视频生成模型，能省掉什么成本，又会把成本转移到哪里？',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/cost-model/',
  },
  twitter: { card: 'summary_large_image', title: 'AI → Blender 成本模型', description: '订阅优先、本地渲染、按需 API 的生产经济学。' },
};

const operatingModes = [
  {
    id: '01', label: '最低现金支出', title: '订阅优先 · 本地有人监督', fit: '个人研究 / 原型 / 单机制作',
    stack: ['ChatGPT 登录 Codex CLI', 'codex exec 编排本地任务', '现有工作站运行 Blender', '用套餐额度，超限后等待或加购'],
    verdict: '在已有硬件、免费/自有资产、用量未超套餐的前提下，新增现金支出可以接近一个订阅。',
    caveat: '订阅不是无限 Token，也不应被当作无人值守生产服务的保证。',
  },
  {
    id: '02', label: '可计量自动化', title: '混合 API · 本地渲染', fit: '小型团队 / 批处理 / 夜间任务',
    stack: ['API key 运行可编程任务', 'Luna 做检查与批量改写', 'Terra 做场景与工具工作', 'Sol 只处理高难推理与调试'],
    verdict: 'AI 成本从固定订阅变成可审计的 Token 变量；Blender 仍承担最终像素，不产生视频按秒费用。',
    caveat: '上下文膨胀、无效重试和错误模型路由，会让 Token 成本快速失控。',
  },
  {
    id: '03', label: '规模化制作', title: '工作室 · 渲染与资产主导', fit: '并行镜头 / 渲染节点 / 持续交付',
    stack: ['API 或受信任自动化身份', '资产注册表与 SceneSpec', '本地集群或云渲染', '集中存储、版本和 QA'],
    verdict: 'AI 编排往往不再是最大项；人物资产、动画清理、渲染小时、存储和验收开始主导总成本。',
    caveat: '低 API 账单并不等于低制片成本，尤其在英雄角色和复杂表演镜头中。',
  },
];

const apiPricing = [
  { model: 'GPT-5.6 Luna', role: '批量检查、格式转换、简单脚本', input: '$0.20', cached: '$0.02', output: '$1.20', example: '$3.20' },
  { model: 'GPT-5.6 Terra', role: '日常场景构建、工具调用、修复', input: '$2.00', cached: '$0.20', output: '$12.00', example: '$32.00' },
  { model: 'GPT-5.6 Sol', role: '复杂架构、困难调试、关键审计', input: '$4.00', cached: '$0.40', output: '$20.00', example: '$60.00' },
];

const costStack = [
  ['AI 编排', '订阅固定费，或 API 输入 / 缓存 / 输出 Token', '可低至订阅内'],
  ['渲染算力', 'GPU 功率 × 渲染小时 × 电价；或云 GPU 小时费', '随画质和帧数增长'],
  ['硬件折旧', '设备购置价 ÷ 可用生产小时 × 本项目占用小时', '已有硬件也不是经济学上的零'],
  ['存储与传输', 'EXR 序列、缓存、纹理、备份、代理与云出站', '长片与高分辨率显著'],
  ['资产与许可', '模型、扫描、动作、HDRI、字体、音乐及整理', '复用率决定摊销效果'],
  ['人工', '导演、TD、建模、绑定、动画、灯光、合成与 QA', '通常是完整成本大头'],
  ['失败与返工', '失败镜头、无效渲染、上游修改和重复验收', '最容易被漏算'],
];

const savings = [
  ['取消视频模型按秒费', '最终像素由 Blender 渲染；不存在每次生成/重试都按视频秒数支付的模型费用。'],
  ['资产跨镜头摊销', '同一角色、场景、材质和灯光模板可持续复用，镜头越多，单镜头资产成本越低。'],
  ['局部重建', '修改焦段或灯位时，只重建受影响依赖，不必整段重新“抽卡”。'],
  ['结果可复现', '相同 SceneSpec、资产版本和渲染配置可重复得到同一结构，减少随机重试。'],
];

const shifted = [
  ['算力转移', '从视频模型服务器转到本地 GPU / 渲染农场；成本变成小时、电力和折旧。'],
  ['内容转移', '视频模型隐式猜出的细节，变成显式资产、材质、绑定、动画和灯光制作。'],
  ['质量责任转移', '高质量渲染不会自动修复错误拓扑、僵硬表演或穿插；QA 与技术美术仍存在。'],
  ['前期投资转移', '先建立资产圣经、模板和编译器，后续镜头才会真正获得低边际成本。'],
];

const levers = [
  ['01', '模型路由', 'Luna 默认、Terra 升级、Sol 例外；记录每项任务的模型、Token 和接受率。'],
  ['02', '上下文预算', '只加载当前镜头需要的文件、工具和依赖；稳定前缀利用缓存，避免全库塞入提示。'],
  ['03', '预览 / 终稿分层', 'EEVEE 做构图、遮挡与动作验收；Cycles 只渲染已经通过的镜头。'],
  ['04', '渲染预算', '先小分辨率、低采样、局部区域测试；锁定噪声阈值后再输出 EXR 终稿。'],
  ['05', '资产复用', '固定 ID、版本、LOD、许可和导入策略；衡量每个资产被多少镜头复用。'],
  ['06', '失败可定位', '每次构建保存 SceneSpec、依赖哈希、日志和渲染统计，避免用整段重来掩盖错误。'],
];

const references = [
  ['OpenAI', 'Codex 套餐、额度与定价', 'https://learn.chatgpt.com/docs/pricing'],
  ['OpenAI', 'Codex CLI：本地工作与 codex exec', 'https://learn.chatgpt.com/docs/codex/cli'],
  ['OpenAI', 'Codex 认证：ChatGPT 登录与 API key', 'https://learn.chatgpt.com/docs/auth'],
  ['OpenAI', 'API 模型定价', 'https://developers.openai.com/api/docs/pricing'],
  ['OpenAI', 'GPT-5.6 Sol API 价格', 'https://developers.openai.com/api/docs/models/gpt-5.6-sol'],
  ['OpenAI', 'Sora 2 API 历史按秒价格', 'https://developers.openai.com/api/docs/models/sora-2'],
  ['Blender Foundation', 'Blender 许可与商业使用', 'https://www.blender.org/about/license/'],
  ['Blender Manual 5.2', 'Cycles 渲染设置与设备选择', 'https://docs.blender.org/manual/en/5.2/render/cycles/render_settings/index.html'],
  ['Blender Manual 5.2', 'CUDA / OptiX / Metal 支持与显存边界', 'https://docs.blender.org/manual/en/5.2/render/cycles/gpu_rendering.html'],
  ['Blender Open Data', 'RTX 5090 当前公开 benchmark 分布', 'https://opendata.blender.org/devices/NVIDIA%20GeForce%20RTX%205090/'],
  ['NVIDIA', 'GeForce RTX 5090：32 GB 与官方系统要求', 'https://marketplace.nvidia.com/en-us/consumer/graphics-cards/nvidia-geforce-rtx-5090/'],
  ['NVIDIA', 'RTX PRO 6000 Blackwell：96 GB ECC 与 600 W', 'https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000-family/'],
  ['AMD', 'Ryzen 9 9950X：16C/32T、256 GB 内存上限与 Linux 支持', 'https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x.html'],
];

export default function CostModelPage() {
  return (
    <main className="cost-page">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="返回技术基线"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="成本研究导航"><Link href="/">技术基线</Link><Link href="/blender-5-2">Blender 5.2</Link><a href="#economics">成本栈</a><a href="#hardware">硬件采购门</a><Link className="route-tab agenda-route" href="/research-agenda">研究路线</Link><Link className="route-tab spec-route" href="/spec-v0-1">规格 v0.1</Link><Link className="route-tab compiler-route" href="/compiler-v0-1">编译实验</Link><Link className="route-tab" href="/pixel-v0-1">像素实验</Link><Link className="route-tab actor-route" href="/actor-v0-1">角色实验</Link><Link className="route-tab contact-route" href="/contact-v0-1">接触实验</Link><Link className="route-tab" href="/grasp-v0-1">手指抓握</Link></nav>
        <span className="edition cost-edition">Cost 01</span>
      </header>

      <section className="cost-hero" id="top">
        <div className="cost-hero-copy">
          <p className="eyebrow"><span /> PRODUCTION ECONOMICS · 2026.08.25</p>
          <h1>成本不是“零”，<br />而是从<span>按秒生成</span><br />转向<span>可复用生产。</span></h1>
          <p>Codex 负责把意图变成可检查的场景数据与自动化操作；Blender 免费、确定性地渲染像素。最小现金成本可以非常低，但完整制作成本还包括算力、资产、人工和失败返工。</p>
        </div>
        <div className="cost-hero-stats">
          <article><strong>$0</strong><span>Blender 许可</span><small>商业使用无需软件许可费</small></article>
          <article><strong>$20</strong><span>订阅起点</span><small>Plus 月费快照；受用量限制</small></article>
          <article><strong>0</strong><span>视频模型</span><small>不产生按生成秒数计费</small></article>
          <article><strong>2</strong><span>Codex 路径</span><small>ChatGPT 登录 / API key</small></article>
        </div>
      </section>

      <section className="section cost-verdict" id="equation">
        <div className="section-index">00 / 核心判断</div>
        <div className="cost-verdict-grid">
          <div><p className="eyebrow dark"><span /> VERDICT</p><h2>方向成立，<br />但必须区分<span>边际现金成本</span><br />与<span>完整生产成本。</span></h2></div>
          <div className="cost-equation" aria-label="总拥有成本公式"><b>TCO / 每条可接受镜头</b><p>AI 编排 + 渲染算力 + 硬件折旧 + 电力 + 存储 + 资产许可 + 人工 + 失败返工</p></div>
        </div>
        <div className="cost-lenses">
          <article><span>A / CASH MARGIN</span><h3>边际现金成本可以接近订阅费</h3><p>成立条件：已有合适工作站、本地渲染、自有或免费资产、暂不计人工，并且 Codex 用量保持在套餐额度内。</p></article>
          <article><span>B / FULLY LOADED</span><h3>完整生产成本绝不会只有订阅</h3><p>当我们把设备占用、资产制作、动画清理、渲染时间、存储和导演验收计入后，人工和资产往往远高于模型账单。</p></article>
        </div>
      </section>

      <section className="section cost-shift">
        <div className="section-index light">01 / 成本重构</div>
        <div className="cost-section-heading"><div><p className="eyebrow"><span /> AVOIDED ≠ ELIMINATED</p><h2>我们真正省掉的，<br />是随机像素的<span>重复购买。</span></h2></div><p>没有视频模型，不等于没有计算或内容成本。它把费用从不可控的“每次整段重生成”，迁移到可积累的资产和可审计的渲染。</p></div>
        <div className="cost-shift-grid">
          <div className="shift-column saved"><header><span>−</span><h3>被省掉 / 被摊薄</h3></header>{savings.map(([title, detail]) => <article key={title}><b>{title}</b><p>{detail}</p></article>)}</div>
          <div className="shift-arrow" aria-hidden="true"><span>→</span><small>价值迁移</small></div>
          <div className="shift-column moved"><header><span>+</span><h3>被转移 / 仍需支付</h3></header>{shifted.map(([title, detail]) => <article key={title}><b>{title}</b><p>{detail}</p></article>)}</div>
        </div>
        <div className="accepted-second"><span>唯一正确的分母</span><strong>每个最终采用秒成本 = 全部制作成本 ÷ 最终通过验收的成片秒数</strong><p>不是“生成一秒多少钱”。失败率、返工次数和资产复用率，比单次模型价格更能决定经济性。</p></div>
      </section>

      <section className="section cost-operations" id="modes">
        <div className="section-index">02 / 运行模式</div>
        <div className="cost-section-heading dark-heading"><div><p className="eyebrow dark"><span /> OPERATING MODES</p><h2>先从订阅开始，<br />自动化再切到 API。</h2></div><p>Codex CLI 支持 ChatGPT 登录和 API key。个人本地探索可以优先使用订阅额度；官方对可编程共享自动化和 CI/CD 更推荐 API key。</p></div>
        <div className="operating-grid">{operatingModes.map(mode => <article key={mode.id}>
          <header><span>{mode.id}</span><small>{mode.label}</small></header><h3>{mode.title}</h3><b>{mode.fit}</b>
          <ul>{mode.stack.map(item => <li key={item}>{item}</li>)}</ul>
          <div className="mode-verdict"><span>经济判断</span><p>{mode.verdict}</p></div>
          <div className="mode-caveat"><span>边界</span><p>{mode.caveat}</p></div>
        </article>)}</div>
        <div className="auth-line"><div><span>SUBSCRIPTION</span><b>ChatGPT 登录</b><small>套餐内额度 · 本地交互 · 可用 codex exec</small></div><i>或</i><div><span>METERED</span><b>API key</b><small>按 Token 计费 · 无人值守 · 可审计扩展</small></div><p>两者都只负责编排和产出场景操作；最终帧仍由 Blender 渲染。</p></div>
      </section>

      <section className="section cost-api">
        <div className="section-index light">03 / AI 编排成本</div>
        <div className="cost-section-heading"><div><p className="eyebrow"><span /> MODEL ROUTER</p><h2>不要让最贵模型，<br />处理所有任务。</h2></div><p>API 价格按每百万 Token 计。下面是 2026-08-25 官方公开价格快照；长上下文、Batch 等条件可能改变实际价格。</p></div>
        <div className="pricing-table" role="table" aria-label="OpenAI API 价格快照">
          <div className="pricing-head" role="row"><span>模型 / 建议职责</span><span>输入</span><span>缓存输入</span><span>输出</span><span>示例任务</span></div>
          {apiPricing.map(row => <div className="pricing-row" role="row" key={row.model}><div><b>{row.model}</b><small>{row.role}</small></div><span>{row.input}</span><span>{row.cached}</span><span>{row.output}</span><strong>{row.example}</strong></div>)}
        </div>
        <div className="pricing-note"><b>示例任务假设</b><p>每月 10M 输入 + 1M 输出、无缓存命中。它不是“一部电影”的价格，只用于展示相同工作负载在不同模型上的数量级差异。</p><span>API 成本 = 输入 MTok × 输入价 + 缓存 MTok × 缓存价 + 输出 MTok × 输出价</span></div>
        <div className="video-comparison"><div><span>LEGACY REFERENCE</span><h3>60 秒 × $0.10–$0.70 / 秒 = $6–$42 / 每次尝试</h3></div><p>这是官方 Sora 2 / Pro 在本研究截点公开的历史按秒价格区间，仅用于说明视频 API 的计费结构；产品已标记为 legacy 并计划停用。Blender 路线取消的是这项“每次视频尝试”的模型费用，不是渲染与制作本身。</p></div>
      </section>

      <section className="section cost-economics" id="economics">
        <div className="section-index">04 / 完整成本栈</div>
        <div className="cost-section-heading dark-heading"><div><p className="eyebrow dark"><span /> TRUE COST STACK</p><h2>七层都记录，<br />才叫科研数据。</h2></div><p>每个镜头保存可复算的成本清单，而不是凭感受宣称“几乎免费”。这也能告诉我们优化模型、渲染，还是资产与人工更有效。</p></div>
        <div className="stack-table" role="table" aria-label="完整制作成本栈"><div className="stack-head" role="row"><span>成本层</span><span>计算方式 / 证据</span><span>典型行为</span></div>{costStack.map(([name, formula, behavior], index) => <div className="stack-row" role="row" key={name}><span><i>{String(index + 1).padStart(2, '0')}</i><b>{name}</b></span><p>{formula}</p><small>{behavior}</small></div>)}</div>
        <div className="render-formulas">
          <article><span>RENDER ENERGY</span><b>GPU kW × 渲染小时 × 电价 / kWh</b><p>把设备待机、CPU 与多卡功耗按测量值补入；不要只用显卡标称功率。</p></article>
          <article><span>HARDWARE AMORTIZATION</span><b>设备净成本 ÷ 预计有效生产小时 × 占用小时</b><p>已有工作站的现金支出为零，但机会成本和折旧不为零。</p></article>
          <article><span>REWORK MULTIPLIER</span><b>基础成本 ×（1 ÷ 首次接受率）</b><p>首次接受率 50% 时，平均生产工作量约为基础值的 2 倍。</p></article>
        </div>
      </section>

      <section className="section cost-measured">
        <div className="section-index light">05 / 真实渲染基线</div>
        <div className="cost-section-heading"><div><p className="eyebrow"><span /> MEASURED · NOT ESTIMATED</p><h2>免费的是许可，<br />不是<span>机器时间。</span></h2></div><p>PixelSpec v0.1 在同一台 darwin-arm64 工作站上完成 8 次 Blender 5.2 Cycles CPU 终稿渲染：3840×2160、512 samples、固定 8 线程、ACES 2、multipart HALF EXR。</p></div>
        <div className="measured-bench"><article><strong>2,621 s</strong><span>8 次正式渲染</span><small>43 分 41 秒</small></article><article><strong>327.65 s</strong><span>平均每帧</span><small>5 分 28 秒</small></article><article><strong>2.18 h</strong><span>每秒成片</span><small>24 帧串行换算</small></article><article><strong>140 MB</strong><span>平均每帧 EXR</span><small>约 3.36 GB / 成片秒</small></article></div>
        <div className="measured-warning"><b>这是下限，不是电影报价</b><p>B01/B02 是简单基准场景；英雄角色、毛发、体积、复杂间接光、更多 AOV 与更高采样都会改变吞吐。另一方面，GPU、分帧并行、降噪策略和分层验收可以显著降低时间。</p><Link href="/pixel-v0-1">查看原始像素与 EXR 证据 →</Link></div>
        <div className="b49-cost-update"><header><span>NEW · B49-R FORMAL HOLDOUT</span><b>当前 qemu CPU worker 的分辨率成本接近像素线性</b></header><div><article><strong>0.985980</strong><span>TABLETOP exponent</span></article><article><strong>0.996206</strong><span>INTERIOR exponent</span></article><article><strong>28–60 min</strong><span>2K / frame · projected</span></article><article><strong>1.76–4.26 h</strong><span>4K / frame · projected</span></article></div><p>后两项来自预注册 `[0.95,1.05]` 指数带，标记为模型外推而非实测。它们不是 GPU、云端或美元价格；它们说明当前 emulated CPU backend 只能做证据 worker，不是生产渲染方案。</p><Link href="/resolution-holdout-v0-1">查看两场景实测、外推区间与非主张 →</Link></div>
        <div className="b49-cost-update b51-cost-update"><header><span>NEW · B51 H1 + D5 + D6 NATIVE BACKEND</span><b>Metal 热态便宜；split production 并没有变便宜</b></header><div><article><strong>0.53–0.75 s</strong><span>H1 Metal / frame</span></article><article><strong>128 spp</strong><span>exact CPU data floor</span></article><article><strong>128 spp</strong><span>semantic CPU data floor</span></article><article><strong>H2 STOP</strong><span>cost hypothesis closed</span></article></div><p>H1 拒绝统一 CPU–Metal image contract；D5 的 32 次真实 CPU render 证明 exact data 不降档；D6 又按规范解码 32 份 EXR，证明冻结 production-semantic profile 仍不降档。继续 split 会支付完整 CPU data + Metal beauty + merge，不再具有已证明的成本优势。下一步转向单一 native CPU production path 的 adaptive sampling / quality–cost 优化。</p><Link href="/native-backend-v0-1#semantic">查看 D6 解码门、16/16 attacks 与路线终止证据 →</Link></div>
        <div className="b49-cost-update b51-cost-update"><header><span>NEW · B52-D1 ADAPTIVE CONTROL FALSIFICATION</span><b>production baseline 原来已经在 adaptive 0.01/min0</b></header><div><article><strong>30 / 30</strong><span>native CPU renders</span></article><article><strong>7 / 7</strong><span>0.01 parent exact</span></article><article><strong>14.67% / 9.62%</strong><span>best descriptive saving</span></article><article><strong>INVALID</strong><span>fixed parent control</span></article></div><p>D5 renderer 没有覆盖源 `.blend` 的 adaptive 属性；真正 fixed 128 因而不能复现 D5 parent。B52-D1 不能晋级任何 profile，但已经把成本基线修正为显式 adaptive 0.01/min0/max128。下一实验必须用 fresh seed 相对这个真实 production baseline 测更宽松 threshold。</p><Link href="/adaptive-cpu-v0-1">查看控制反例、Sample Count 与完整失败链 →</Link></div>
      </section>

      <section className="section cost-hardware" id="hardware">
        <div className="section-index">06 / 硬件采购门 · 2026.08.27</div>
        <div className="cost-section-heading dark-heading"><div><p className="eyebrow dark"><span /> BUY A NEW EVIDENCE DOMAIN · NOT A FASTER DUPLICATE</p><h2>当前机器够研究。<br />下一台必须<span>增加对照维度。</span></h2></div><p>本机实测为 M4 Max、16 CPU cores、40 GPU cores、48 GB unified memory；当前内盘仅约 100 GiB 可用。D5 与 D6 已分别把 exact 和 production-semantic CPU data floor 固定在 128 spp，H2 split cost 路线停止。最先逼近的资源仍是证据存储，不是计算。</p></div>
        <div className="hardware-gates"><article className="now"><span>BUY FIRST · STORAGE</span><strong>4–8 TB</strong><b>Thunderbolt / NVMe evidence volume</b><p>触发：在保留失败 EXR 与 100 GiB 安全余量时，本机无法准入下一实验。当前已经接近该门。</p></article><article className="candidate"><span>RESEARCH EXPANSION</span><strong>RTX 5090</strong><b>Linux · CUDA / OptiX · 32 GB</b><p>触发：开始跨 GPU/OS holdout、队列持续占用本机，或需要独立无人值守节点。它增加 NVIDIA 证据域，不只是缩短等待。</p></article><article><span>DO NOT BUY YET</span><strong>96 GB</strong><b>RTX PRO 6000 · ECC</b><p>仅当真实生产场景在 32 GB 上 OOM、必须依赖 ECC，或角色/毛发/体积工作集经测量需要 32 GB 以上时晋级。</p></article></div>
        <div className="hardware-blueprint"><header><span>RECOMMENDED COMPLEMENTARY NODE</span><b>不是第二台 Mac，也不是双 GPU 堆料</b></header><div><article><span>GPU</span><strong>RTX 5090 · 32 GB</strong><small>OptiX/CUDA counterfactual</small></article><article><span>CPU / RAM</span><strong>16C/32T · 128 GB</strong><small>Ryzen 9 9950X class</small></article><article><span>STORAGE</span><strong>4 TB + 4–8 TB</strong><small>workspace + evidence/cache</small></article><article><span>HOST</span><strong>Linux · 1200 W</strong><small>pinned driver · remote worker</small></article></div><p>NVIDIA 对 RTX 5090 标注 32 GB GDDR7，安装指南要求至少 1000 W；长期满载研究节点建议留电源与散热余量。Blender 5.2 在 Linux 支持 OptiX，并要求 NVIDIA driver ≥575。显示器不是必要投入：节点可以由当前 Mac 通过受限 worker/SSH 调度。</p></div>
        <div className="hardware-decision"><b>CURRENT DECISION</b><p><strong>存储：现在有理由购买。</strong> RTX 5090 节点仍有跨 OS / CUDA / OptiX 科研价值，但不是继续 native CPU 优化的前置条件；如果预算允许，它是新增对照域，而不是修复已关闭的 H2。当前 split path 要支付完整 128-spp CPU data + Metal，并无成本优势。RTX PRO 6000：没有实测触发证据，暂不购买。</p></div>
      </section>

      <section className="section cost-scenarios">
        <div className="section-index light">07 / 条件与情景</div>
        <div className="cost-section-heading"><div><p className="eyebrow"><span /> WHEN IS IT “ALMOST SUBSCRIPTION ONLY”?</p><h2>只有六个条件<br />同时成立。</h2></div><p>这不是否定最初设想，而是把它变成可以验证的假设。只要任一条件变化，就切换相应成本模型。</p></div>
        <div className="condition-grid">
          <article><span>01</span><b>已有可用 GPU 工作站</b><p>不发生新增硬件现金支出。</p></article><article><span>02</span><b>全部本地渲染</b><p>不使用云 GPU 和大额出站流量。</p></article><article><span>03</span><b>资产已拥有或免费</b><p>没有临时购买、扫描和外包建模。</p></article><article><span>04</span><b>人工暂不计价</b><p>研究者时间被视为研发投入而非镜头成本。</p></article><article><span>05</span><b>Codex 未超过额度</b><p>不加购 credits，也不切换到 API 计费。</p></article><article><span>06</span><b>不接可选生成 API</b><p>不额外调用图像、3D、动作、声音或视频模型。</p></article>
        </div>
        <div className="scenario-verdict"><b>因此最准确的表述是：</b><p>“在已有硬件与资产、个人本地制作且不计人工的研究阶段，Codex 订阅 + Blender 可以把新增现金成本压到接近订阅与电力；进入生产后，应按完整成本栈核算。”</p></div>
      </section>

      <section className="section cost-levers">
        <div className="section-index">08 / 降本路线</div>
        <div className="cost-section-heading dark-heading"><div><p className="eyebrow dark"><span /> OPTIMIZATION ORDER</p><h2>先减少失败，<br />再减少单价。</h2></div><p>把每个优化动作与测量指标绑定。低价模型如果导致更多返工，可能反而提高“每个最终采用秒”的成本。</p></div>
        <div className="lever-grid">{levers.map(([id, title, detail]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p></article>)}</div>
        <div className="instrumentation"><span>每个镜头最少记录</span><div>{['Codex 模式与模型', '输入 / 缓存 / 输出 Token', '构建与渲染小时', '功耗与设备', '资产复用次数', '失败原因与重试', '人工分钟', '最终采用秒'].map(item => <b key={item}>{item}</b>)}</div></div>
      </section>

      <section className="section cost-method" id="sources">
        <div className="section-index light">09 / 方法与证据</div>
        <div className="cost-section-heading"><div><p className="eyebrow"><span /> EVIDENCE POLICY</p><h2>价格会变，<br />公式应该稳定。</h2></div><p>本页所有价格以 2026-08-25 为截点，优先引用官方资料。具体订阅额度会随任务、模型、上下文、推理强度和工具调用变化；发布前应再次核价。</p></div>
        <div className="method-cautions"><article><b>事实</b><p>Blender 许可为零、Codex 的两种认证路径、公开套餐/API 价格，以及 PixelSpec 的 CPU 时间与 EXR 体积。</p></article><article><b>工程判断</b><p>推荐的模型路由、资产摊销方式、成本栈与降本顺序。</p></article><article><b>待实验</b><p>真实镜头的 Token、渲染能耗、GPU 吞吐、首次接受率与资产复用收益。</p></article></div>
        <ol className="references cost-references">{references.map(([author, title, href], index) => <li key={href}><span>{String(index + 1).padStart(2, '0')}</span><div><small>{author}</small><a href={href} target="_blank" rel="noreferrer">{title} ↗</a></div></li>)}</ol>
        <div className="license-note"><b>许可提醒</b><p>Blender 本身可免费用于商业作品，作品版权归创作者；但如果未来分发依赖 <code>bpy</code> 的 Blender 插件，应单独审查 GPL 合规。免费使用与可任意闭源分发插件不是同一件事。</p></div>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>Production Cost Model</b></div><p>Research tab · Updated: 2026-08-27 · Prices are time-sensitive</p><Link href="/blender-5-2">Blender 5.2 技术地图 →</Link></footer>
    </main>
  );
}
