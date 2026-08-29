import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import audit from '../../experiments/cinematic-render-repro-cost-v0-5/audit.json';
import receipt from '../../experiments/cinematic-render-repro-cost-v0-5/receipt.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/cinematic-render-repro-cost-v0-1/';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'B61-E1 三镜头 Cycles 像素复现与成本｜Blender Film Studio',
  description: '6 个真实 Blender 5.2 渲染进程、18 帧 1080p Cycles EXR、9/9 A/B 解码像素一致、16/16 gates 与 10/10 attacks 通过；同时明确不主张电影感。',
  alternates: { canonical },
  openGraph: {
    title: 'B61-E1 · Pixels Reproduced. Cinema Not Yet Claimed.',
    description: '18 real Cycles renders · 9/9 decoded A/B pixel pairs · measured wall, memory and bytes.',
    url: canonical,
    images: [],
  },
};

const shots = [
  { id: 'WIDE', hashes: ['192237bde2f6', '514aac2ab1c3', 'b842bb5ce630'], files: ['wide-0001.png', 'wide-0072.png', 'wide-0144.png'] },
  { id: 'MEDIUM', hashes: ['9d6ca4303b22', '577413dddfc9', 'd364595bbfe9'], files: ['medium-0001.png', 'medium-0072.png', 'medium-0144.png'] },
  { id: 'CLOSE', hashes: ['bb213fb84a74', 'f69a02d03416', '4809d28b335b'], files: ['close-0001.png', 'close-0072.png', 'close-0144.png'] },
] as const;
const frames = ['0001', '0072', '0144'] as const;

const failures = [
  ['v0.1 · OBSERVABILITY', 'EXR 写完后没有可靠失败码与原始日志', 'C1 · Python exit code + raw logs + stage ledger'],
  ['v0.2 · DECODER', 'Blender multilayer image 的 bpy pixels 为空', 'D1–D3 / C2 · bundled OpenImageIO + canonical hash'],
  ['v0.3 · PNG CONTEXT', '生产 scene 的输出格式被 multilayer enum 锁定', 'D4 / C3 · isolated review scene'],
  ['v0.4 · BUFFER OWNERSHIP', 'headless Render Result 没有 image data', 'D5 / C4 · OIIO array → generated float image'],
] as const;

export default function CinematicRenderReproCostPage() {
  const processes = receipt.processes;
  const gatePasses = audit.gates.filter(gate => gate.pass).length;

  return <main className="contact-page b61-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="B61-E1 导航"><a href="#frames">真实帧</a><a href="#identity">复现</a><a href="#cost">成本</a><a href="#failures">失败史</a><a href="#boundary">边界</a><Link href="/journal">日志</Link></nav>
      <span className="edition contact-edition">B61-E1 · PASS</span>
    </header>

    <section className="contact-hero b61-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> REAL BLENDER 5.2 · CYCLES · 1080P MULTILAYER EXR</p>
        <h1>像素复现了。<br/><span>电影感还没有。</span></h1>
        <p>三个镜头、三个关键帧、A/B 两次独立进程。九组解码后的 Combined RGBA 全部一致，正式成本也已测得。但测试资产仍是低多边形几何：技术确定性不能冒充角色真实感、表演或电影美术。</p>
      </div>
      <aside className="contact-gate b61-gate">
        <b>FORMAL VERDICT</b><strong>SUPPORTED</strong>
        <code>{gatePasses} / {audit.gates.length} frozen gates</code>
        <code>{audit.attacks.filter(attack => attack.pass).length} / {audit.attacks.length} attacks rejected</code>
        <small>receipt {receipt.receiptHash.slice(0, 16)}…</small>
      </aside>
      <div className="contact-stats">
        <article><strong>18</strong><span>真实 Cycles 帧</span><small>1920×1080 · 64 spp</small></article>
        <article><strong>9/9</strong><span>A/B 像素一致</span><small>decoded Combined RGBA</small></article>
        <article><strong>6.084 s</strong><span>平均 render / frame</span><small>本机 CPU 实测</small></article>
        <article><strong>4.54 GB</strong><span>最高 process RSS</span><small>六个 render processes</small></article>
      </div>
    </section>

    <section className="section b61-frames" id="frames">
      <div className="section-index">00 / NINE REAL REVIEW FRAMES</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> A-RUN DISPLAY PROXIES · ACES · ORIGINAL 1920×1080</p><h2>三种景别。<br/><span>三个运动时刻。</span></h2></div><p>这些 PNG 来自同一次 EXR 解码数组，只供可视检查。正式判决发生在 scene-linear float32-LE Combined 像素上。方向、颜色、景别和运动可读；低多边形外观也被原样保留。</p></div>
      <div className="b61-gallery">
        {shots.map(shot => <article key={shot.id}><header><strong>{shot.id}</strong><span>A-RUN · REVIEW ONLY</span></header><div>{shot.files.map((file, index) => <figure key={file}><Image src={`${basePath}/evidence/b61/${file}`} width={1920} height={1080} unoptimized alt={`${shot.id} frame ${frames[index]} real Blender 5.2 Cycles render`} /><figcaption><span>FRAME {frames[index]}</span><code>{shot.hashes[index]}…</code></figcaption></figure>)}</div></article>)}
      </div>
      <p className="b61-visual-warning"><b>人工检查结论</b><span>无空帧、翻转或明显数据损坏；WIDE → MEDIUM → CLOSE 和三帧运动状态可辨。</span><strong>不支持真人身份或电影级美术判断</strong></p>
    </section>

    <section className="section b61-identity" id="identity">
      <div className="section-index">01 / IDENTITY SURFACE</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> SEMANTIC PIXELS ≠ CONTAINER BYTES</p><h2>画面相同。<br/><span>EXR 文件并不相同。</span></h2></div><p>九组 A/B 的解码像素 digest 全部 exact，PNG SHA 也全部 exact；九组 EXR container SHA 则全部不同。B61 因此拒绝用文件哈希替代像素语义，并由独立 Blender 进程重开 18 个 EXR 再验证一次。</p></div>
      <div className="b61-identity-grid">
        <article className="pass"><span>DECODED COMBINED</span><strong>9 / 9</strong><b>A/B EXACT</b><small>float32-LE RGBA digest</small></article>
        <article className="pass"><span>REVIEW PNG</span><strong>9 / 9</strong><b>A/B EXACT</b><small>display proxy container SHA</small></article>
        <article className="expected"><span>MULTILAYER EXR</span><strong>0 / 9</strong><b>CONTAINER EXACT</b><small>expected non-identity surface</small></article>
        <article><span>INDEPENDENT REOPEN</span><strong>18 / 18</strong><b>REPORT MATCH</b><small>seventh Blender · zero renders</small></article>
      </div>
      <div className="b61-process-table"><div className="head"><b>PROCESS</b><b>WALL</b><b>MAX RSS</b><b>POST-READ WARN</b></div>{processes.map(process => <div className="row" key={process.id}><strong>{process.id}</strong><code>{process.elapsedSeconds.toFixed(3)} s</code><code>{(process.timing.maximumResidentSetSizeBytes / 1e9).toFixed(3)} GB</code><b>{process.phaseGate.postReadWarningCount}</b></div>)}</div>
    </section>

    <section className="section b61-cost" id="cost">
      <div className="section-index">02 / OBSERVED COST</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> MEASURED STILL FRAMES · LABELED EXTRAPOLATION</p><h2>十八帧花了两分钟。<br/><span>一分钟成片不是两分钟。</span></h2></div><p>六个进程 wall 合计 121.366 秒；机械外推到 24 fps 的一分钟成片约 2.433 小时。这个数字只来自九个 still-frame 状态，不包含全序列的时间连续性、启动摊销变化、模拟、合成、资产制作或返工。</p></div>
      <div className="b61-cost-grid">
        <article><span>RENDER OPERATOR</span><strong>109.506 s</strong><small>18 calls · mean 6.084 s</small></article>
        <article><span>PROCESS WALL</span><strong>121.366 s</strong><small>6 fresh render starts</small></article>
        <article><span>FINISHED SECOND</span><strong>146.008 s</strong><small>24 fps mechanical projection</small></article>
        <article className="projection"><span>FINISHED MINUTE</span><strong>2.433 h</strong><small>projection · not a rendered sequence</small></article>
      </div>
      <div className="b61-byte-rail"><article><span>18 MULTILAYER EXR</span><strong>91.62 MB</strong></article><i>+</i><article><span>18 REVIEW PNG</span><strong>4.86 MB</strong></article><i>=</i><article><span>FORMAL PIXEL ASSETS</span><strong>96.49 MB</strong></article></div>
    </section>

    <section className="section b61-failures" id="failures">
      <div className="section-index">03 / FOUR FAILURES RETAINED</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> PASS ON THE FIFTH FORMAL VERSION</p><h2>成功没有覆盖失败。<br/><span>失败塑造了正确的路径。</span></h2></div><p>每次失败都在第一个尚未证明的接口停止，其 root、raw logs、stage ledger 和 correction preregistration 均留存。v0.5 没有删除攻击、放宽参数或换掉原判决门。</p></div>
      <ol className="b61-failure-list">{failures.map(([id, observed, intervention]) => <li key={id}><span>{id}</span><strong>{observed}</strong><p>{intervention}</p></li>)}</ol>
    </section>

    <section className="section b61-boundary" id="boundary">
      <div className="section-index">04 / CLAIM BOUNDARY AND NEXT GATE</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> TECHNICAL REPRODUCIBILITY ≠ CINEMATIC PROOF</p><h2>关闭一扇技术门。<br/><span>打开真正的电影门。</span></h2></div><p>下一阶段不再用低多边形测试场景回答审美问题。终局目标是 10–20 秒、至少三个连续镜头、同一英雄角色与环境，从干净输出 root 单命令编译，并在受控中断后从已验证 receipt 恢复，最终交付 EXR 与成片视频。</p></div>
      <div className="b61-boundary-grid">
        <article className="supported"><span>SUPPORTED</span><strong>同机像素复现</strong><p>same host · same Blender build · frozen CPU/Cycles/OCIO/seed · nine sampled pairs</p></article>
        <article><span>NOT YET TESTED</span><strong>全序列连续性</strong><p>144 frames、simulation、motion continuity 与完整镜头成本仍未进入本门。</p></article>
        <article><span>NOT CLAIMED</span><strong>真人与电影感</strong><p>皮肤、毛发、服装、微表演、摄影与美术必须由真实英雄资产和匿名审片评估。</p></article>
        <article className="next"><span>NEXT TERMINAL PROOF</span><strong>10–20 秒 / 3+ 镜头</strong><p>single command · controlled interruption · verified resume · EXR + delivery video</p></article>
      </div>
      <div className="contact-artifacts b61-artifacts">
        <a href={`${repo}research/2026-08-29-b61-e1-cinematic-render-repro-cost-protocol.md`}><span>FROZEN PROTOCOL</span><b>3 shots × 3 frames × A/B ↗</b></a>
        <a href={`${repo}research/2026-08-29-b61-e1-cinematic-render-repro-cost-result.md`}><span>RESULT NOTE</span><b>claims · failures · limits ↗</b></a>
        <a href={`${repo}experiments/cinematic-render-repro-cost-v0-5/audit.json`}><span>INDEPENDENT AUDIT</span><b>{audit.auditHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}experiments/cinematic-render-repro-cost-v0-5/receipt.json`}><span>FORMAL RECEIPT</span><b>{receipt.receiptHash.slice(0, 16)}… ↗</b></a>
      </div>
    </section>
    <footer><div><span className="brand-mark">BFS</span><b>B61-E1 Render Reproducibility</b></div><p>18 real renders · 9/9 pixel pairs · cinema not claimed</p><Link href="/journal">查看完整实验日志 →</Link></footer>
  </main>;
}
