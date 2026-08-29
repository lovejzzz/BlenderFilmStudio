import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import audit from '../../experiments/b62-phase0-v0-4/audit.json';
import receipt from '../../experiments/b62-phase0-v0-4/receipt.json';
import blenderAudit from '../../experiments/b62-phase0-v0-4/reports/blender-audit.json';
import wide from '../../experiments/b62-phase0-v0-4/calibration/WIDE_APPROACH-0048.pixel.json';
import medium from '../../experiments/b62-phase0-v0-4/calibration/MEDIUM_CONTACT-0144.pixel.json';
import close from '../../experiments/b62-phase0-v0-4/calibration/CLOSE_REFLECTION-0240.pixel.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/b62-phase0-terminal-proof-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B62 Phase 0 终端实验｜Blender Film Studio',
  description: '真实 Blender 5.2 完成三镜头资产、288 帧 animatic、三张 1080p Cycles 校准帧与独立重开审计；工程门通过，镜头质量仍未通过。',
  alternates: { canonical },
  openGraph: {
    title: 'B62 · Pipeline admitted. Shot quality not admitted.',
    description: '6 Blender starts · 291 renders · 18/18 gates · 16/16 negative controls.',
    url: canonical,
    images: [],
  },
};

const shots = [
  {
    id: 'WIDE_APPROACH',
    frame: 48,
    file: 'WIDE_APPROACH-0048.png',
    report: wide,
    reading: '主体、观测台与冷色环境关系清楚；可进入下一轮。',
    verdict: 'READABLE',
  },
  {
    id: 'MEDIUM_CONTACT',
    frame: 144,
    file: 'MEDIUM_CONTACT-0144.png',
    report: medium,
    reading: '右手接触与核心转暖可读；动作仍只是技术级 blocking。',
    verdict: 'READABLE',
  },
  {
    id: 'CLOSE_REFLECTION',
    frame: 240,
    file: 'CLOSE_REFLECTION-0240.png',
    report: close,
    reading: '前景遮挡占比过高，反射信息与角色表意不足；必须重构图。',
    verdict: 'QUALITY FAIL',
  },
] as const;

const failures = [
  ['v0.1', 'EXR media type 顺序错误', '保留失败 root；D1/D2 证明动态 setter 行为'],
  ['v0.2', '运行时 color look 不存在', 'D3/D4 枚举真实 Blender 5.2 配置表面'],
  ['v0.3', '独立审计把 append descriptor 误判为外链', 'D6 证明 locality；D7 修正时序并复审 23/23'],
  ['v0.4', '完整重跑通过', '使用 fresh roots，重复 291 次 render，不追认旧输出'],
] as const;

export default function B62Phase0TerminalProofPage() {
  const gatePasses = audit.gates.filter(gate => gate.pass).length;
  const attackPasses = audit.attacks.filter(attack => attack.pass).length;
  const blenderCheckPasses = Object.values(blenderAudit.checks).filter(Boolean).length;
  const projectionHours = audit.costs.mechanicalProjectionSecondsFor288Frames / 3600;

  return <main className="contact-page b62-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B62 导航"><a href="#film">Animatic</a><a href="#frames">Cycles 帧</a><a href="#audit">审计</a><a href="#cost">成本</a><a href="#boundary">边界</a><Link href="/journal">Journal</Link></nav>
      <span className="edition contact-edition">B62 · PHASE 0</span>
    </header>

    <section className="contact-hero b62-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> REAL BLENDER 5.2 · FRESH ROOTS · FORMAL RECEIPT</p>
        <h1>流水线通过了。<br/><span>镜头还没通过。</span></h1>
        <p>结构化意图已经生成真实资产库、动作库、主场景、12 秒三镜头 animatic 与三张 1080p Cycles 校准帧；独立 Blender 重开审计也通过。但 CLOSE 镜头构图明显失效，因此这不是“电影完成”的声明。</p>
      </div>
      <aside className="contact-gate b62-gate">
        <b>FORMAL MACHINE VERDICT</b><strong>PHASE 0<br/>ADMITTED</strong>
        <code>{gatePasses} / {audit.gates.length} frozen gates</code>
        <code>{attackPasses} / {audit.attacks.length} mutations rejected</code>
        <small>receipt {receipt.receiptHash.slice(0, 16)}…</small>
      </aside>
      <div className="contact-stats">
        <article><strong>12 s</strong><span>三镜头 Animatic</span><small>288 frames · 24 fps</small></article>
        <article><strong>291</strong><span>真实 Render Calls</span><small>288 Eevee + 3 Cycles</small></article>
        <article><strong>23/23</strong><span>独立 Blender 审计</span><small>reopen · locality · causality</small></article>
        <article><strong>0</strong><span>视频模型调用</span><small>model / network / Docker</small></article>
      </div>
    </section>

    <section className="section b62-film" id="film">
      <div className="section-index">00 / ACTUAL 288-FRAME OUTPUT</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> WIDE → MEDIUM → CLOSE · COLD → CONTACT → WARM HOLD</p><h2>不是 prompt 预览。<br/><span>这是 Blender 输出的完整时线。</span></h2></div><p>视频由 288 张 640×360 Eevee 帧经本机 ffmpeg 编码；同一 master scene 在三段 marker 上切换相机。它证明时间线与状态连续性，不证明最终画质。</p></div>
      <div className="b62-player"><video controls preload="metadata" playsInline aria-label="B62 Phase 0 真实 Blender 三镜头 animatic"><source src={`${basePath}/evidence/b62/B62_PHASE0_ANIMATIC.mp4`} type="video/mp4" /></video><div><span>DELIVERY PROXY</span><strong>288 / 288</strong><p>frame roster exact</p><code>SHA-256 7e8a2060e5d310f2…</code></div></div>
    </section>

    <section className="section b62-frames" id="frames">
      <div className="section-index">01 / THREE REAL CYCLES CALIBRATION FRAMES</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> 1920×1080 · 64 SPP · MULTILAYER EXR · ACES</p><h2>机器看数据完整。<br/><span>人必须看镜头是否成立。</span></h2></div><p>三张 PNG 由对应 scene-linear EXR 的 Combined float pixels 解码生成。所有像素 finite、非空且具动态范围；下面的“可读 / 失败”是额外人工观察，不改写本轮预注册的 machine verdict。</p></div>
      <div className="b62-shot-grid">{shots.map(shot => <article className={shot.verdict === 'QUALITY FAIL' ? 'quality-fail' : ''} key={shot.id}><figure><Image src={`${basePath}/evidence/b62/${shot.file}`} width={1920} height={1080} unoptimized alt={`${shot.id} frame ${shot.frame}, real Blender 5.2 Cycles calibration render`} /><figcaption><span>{shot.id} · FRAME {shot.frame}</span><b>{shot.verdict}</b></figcaption></figure><p>{shot.reading}</p><code>pixels {shot.report.decodedCombined.sha256.slice(0, 16)}…</code></article>)}</div>
      <p className="b62-warning"><b>QUALITATIVE COUNTEREVIDENCE</b><span>CLOSE_REFLECTION 大面积前景遮挡，不能作为电影级 close-up 接受。</span><strong>下一轮先改镜头，不烧 288 帧 Cycles。</strong></p>
    </section>

    <section className="section b62-audit" id="audit">
      <div className="section-index">02 / STRUCTURE, LOCALITY AND CAUSALITY</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> INDEPENDENT READ-ONLY REOPEN</p><h2>场景不是黑盒视频。<br/><span>每个对象仍然可检查。</span></h2></div><p>第六个 Blender 进程只读重开 master、三份资产库与 motion library。它检查 timeline、camera、rig、materials、drivers、contact、cold→warm 状态与资产 locality；不是相信 generator 自报。</p></div>
      <div className="b62-audit-grid">
        <article><span>BLENDER REOPEN CHECKS</span><strong>{blenderCheckPasses} / {Object.keys(blenderAudit.checks).length}</strong><p>全部 true；zero render</p></article>
        <article><span>APPENDED LOCAL IDS</span><strong>54 / 84 / 16</strong><p>三份资产的 tracked IDs 全部 library=null</p></article>
        <article><span>FORMAL GATES</span><strong>{gatePasses} / {audit.gates.length}</strong><p>输入、身份、镜头、状态、输出、成本</p></article>
        <article><span>NEGATIVE CONTROLS</span><strong>{attackPasses} / {audit.attacks.length}</strong><p>16 类篡改全部被拒绝</p></article>
      </div>
      <ol className="b62-failure-list">{failures.map(([version, failure, correction]) => <li key={version}><span>{version}</span><strong>{failure}</strong><p>{correction}</p></li>)}</ol>
    </section>

    <section className="section b62-cost" id="cost">
      <div className="section-index">03 / OBSERVED LOCAL COST</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> SUBSCRIPTION-DRIVEN CONTROL · FREE BLENDER · LOCAL COMPUTE</p><h2>生成调用为零。<br/><span>算力成本仍然真实存在。</span></h2></div><p>本轮没有模型、网络或 Docker 调用。成本主要来自本机 Cycles：三张 still 共 {audit.costs.calibrationRenderSeconds.toFixed(2)} 秒。全 288 帧数字只是逐帧机械外推，不是实测序列预算。</p></div>
      <div className="b62-cost-grid">
        <article><span>ANIMATIC RENDER</span><strong>{audit.costs.animaticRenderSeconds.toFixed(2)} s</strong><small>288 Eevee frames</small></article>
        <article><span>CYCLES CALIBRATION</span><strong>{audit.costs.calibrationMeanSecondsPerFrame.toFixed(2)} s/f</strong><small>3 × 1080p · 64 spp</small></article>
        <article><span>PEAK PROCESS RSS</span><strong>{(audit.costs.peakResidentSetSizeBytes / 1e9).toFixed(2)} GB</strong><small>measured maximum</small></article>
        <article className="projection"><span>288-FRAME PROJECTION</span><strong>{projectionHours.toFixed(2)} h</strong><small>mechanical only · not measured</small></article>
      </div>
    </section>

    <section className="section b62-boundary" id="boundary">
      <div className="section-index">04 / CLAIM BOUNDARY</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> ENGINEERING PASS ≠ CINEMATIC PASS</p><h2>先否决坏镜头。<br/><span>再支付最终渲染成本。</span></h2></div><p>Phase 0 关闭的是“可否生成、保存、复开、审计、渲染和核算”的门。下一门将对构图、遮挡、主体占比、焦点、曝光与运动可读性做预注册 camera-quality 检验；通过前不运行完整 288 帧 Cycles。</p></div>
      <div className="b62-boundary-grid">
        <article className="supported"><span>SUPPORTED</span><strong>资产到三镜头时线</strong><p>真实 .blend、rig、动作、camera、light state 与 animatic 已闭环。</p></article>
        <article><span>NOT CLAIMED</span><strong>电影级镜头质量</strong><p>CLOSE 构图反例已公开；没有人类审片通过。</p></article>
        <article><span>NOT CLAIMED</span><strong>照片级数字演员</strong><p>皮肤、毛发、服装、表情和微表演仍未进入本轮。</p></article>
        <article className="next"><span>NEXT GATE</span><strong>Camera Quality</strong><p>先在三个关键帧与低成本 animatic 上拒绝坏镜头，再决定 full Cycles。</p></article>
      </div>
      <div className="contact-artifacts b62-artifacts">
        <a href={`${repo}research/2026-08-29-b62-phase0-asset-animatic-calibration-result.md`}><span>RESULT NOTE</span><b>measures · failures · boundary ↗</b></a>
        <a href={`${repo}experiments/b62-phase0-v0-4/audit.json`}><span>INDEPENDENT AUDIT</span><b>{gatePasses}/{audit.gates.length} · {attackPasses}/{audit.attacks.length} ↗</b></a>
        <a href={`${repo}experiments/b62-phase0-v0-4/reports/blender-audit.json`}><span>BLENDER REOPEN</span><b>{blenderCheckPasses}/{Object.keys(blenderAudit.checks).length} checks ↗</b></a>
        <a href={`${repo}experiments/b62-phase0-v0-4/receipt.json`}><span>FORMAL RECEIPT</span><b>{receipt.receiptHash.slice(0, 16)}… ↗</b></a>
      </div>
    </section>
    <footer><div><span className="brand-mark">BFS</span><b>B62 Phase 0 Terminal Experiment</b></div><p>pipeline admitted · shot quality not admitted</p><Link href="/journal">查看完整实验日志 →</Link></footer>
  </main>;
}
