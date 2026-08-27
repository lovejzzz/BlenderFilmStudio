import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'B52-D12 透视亚像素重建｜Blender Film Studio',
  description: '65 个唯一进程、32 次真实 Blender 5.2 render：运动场景数值通过，但跨语言报告身份与静态绝对零门失败；C2 独立审计确认 NOT_SUPPORTED。',
  alternates: { canonical: 'https://lovejzzz.github.io/BlenderFilmStudio/blender-projective-subpixel-reconstruction-v0-1/' },
};

const commit = '40a8b78';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const raw = `https://raw.githubusercontent.com/lovejzzz/BlenderFilmStudio/${commit}/experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/diagnostics`;

const rows = [
  ['OBJECT DOLLY + XY', '5,841', '2.217e−5', '5.045e−5', '85.94 dB', '44.6×'],
  ['OBJECT YAW + PITCH', '5,841', '3.976e−5', '4.585e−5', '86.77 dB', '49.9×'],
  ['CAMERA DOLLY + YAW', '5,841', '4.077e−5', '3.926e−5', '88.12 dB', '60.4×'],
  ['STATIC CONTROL', '5,841', '1.526e−5', '2.656e−8', '151.52 dB', 'ZERO GATE FAIL'],
];

const gallery = [
  ['PROJECTIVE_OBJECT_DOLLY_TRANSLATE_107X67', 'OBJECT DOLLY + TRANSLATE'],
  ['PROJECTIVE_OBJECT_YAW_PITCH_107X67', 'OBJECT YAW + PITCH'],
  ['PROJECTIVE_CAMERA_DOLLY_YAW_107X67', 'CAMERA DOLLY + YAW'],
  ['PROJECTIVE_STATIC_CONTROL_107X67', 'STATIC CONTROL'],
];

const views = [
  ['current', 'CURRENT BEAUTY'],
  ['correct-bilinear', 'BILINEAR RECON'],
  ['absolute-error', 'ABS ERROR'],
  ['nearest-error', 'NEAREST ERROR'],
  ['wrong-sign-error', 'WRONG-SIGN ERROR'],
  ['depth-validity', 'DEPTH VALIDITY'],
];

export default function BlenderProjectiveSubpixelReconstructionPage() {
  return <main className="contact-page b51-page b52-page d11-page d111-page d12p-page">
    <header className="topbar">
      <a className="brand" href="../"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></a>
      <nav aria-label="D12 导航"><a href="../blender-nearest-integer-temporal-recovery-v0-1/">D11.1</a><a href="#verdict">结论</a><a href="#matrix">运动测量</a><a href="#evidence">诊断图</a><a href="#audit">审计</a><a href="../blender-static-vector-floor-v0-1/">D12.2 静态底噪</a><a href="../journal/">日志</a></nav>
      <span className="edition contact-edition">Projective Subpixel D12</span>
    </header>

    <section className="contact-hero b52-hero d111-hero d12p-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy"><p className="eyebrow"><span /> B52-D12 · PROJECTIVE SUBPIXEL RECONSTRUCTION</p><h1>运动像素通过。<br/><span>完整合同没有通过。</span></h1><p>四个全新 107×67 透视场景、双语言消费者和真实 Blender 5.2 Raw EXR bridge 完成。三组运动结果非常强，但报告身份与静态绝对零门给出两个可复现反例。</p></div>
      <aside className="contact-gate d111-gate d12p-gate"><b>AUDITED VERDICT</b><strong>NOT<br/>SUPPORTED</strong><code>base: DUAL IDENTITY</code><code>C2 audit PASS</code><small>moving reconstruction still passes</small></aside>
      <div className="contact-stats"><article><strong>65 / 65</strong><span>formal child PIDs</span><small>all unique</small></article><article><strong>32</strong><span>Blender renders</span><small>16 Cycles + 16 bridge</small></article><article><strong>47 / 57</strong><span>registered attacks</span><small>negative result retained</small></article><article><strong>8 / 8</strong><span>dual arrays exact</span><small>Python = Node bytes</small></article></div>
    </section>

    <section className="section d12p-verdict" id="verdict">
      <div className="section-index">00 / WHY THE CONTRACT FAILED</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> TWO FAILURES · ONE CLEAN MATRIX</p><h2>不是把小误差说成成功。<br/><span>也不是把工具错误说成物理失败。</span></h2></div><p>C1 修复了目录创建并从零重跑完整矩阵。冻结 analyzer 依次检查身份、物理、数值和输出：最早在 Node report canonical hash 停下；更后面的 static exact gate 也独立失败。</p></div>
      <div className="d12p-failures"><article className="identity"><span>BASE FAILURE · IDENTITY</span><strong>8 / 8</strong><b>Node report self-hashes rejected</b><p>同一小数在 JavaScript canonical JSON 中写为十进制，在 Python 中写为指数形式。数组逐字节相同，但报告身份不成立。</p></article><article className="static"><span>INDEPENDENT FAILURE · STATIC</span><strong>1.49e−7</strong><b>maximum RGB residual</b><p>静态 Vector 仍有 1.526e−5 px 浮点残差。双线性重建不是绝对零，而冻结 gate 明确要求 0.0。</p></article><article><span>WHAT DID PASS</span><strong>3 / 3</strong><b>moving projective fixtures</b><p>endpoint、subpixel、transform depth、RGB quality、nearest/wrong-sign controls 与 bridge 全部通过。</p></article></div>
    </section>

    <section className="section d12p-matrix" id="matrix">
      <div className="section-index">01 / MEASURED REAL-BLENDER MATRIX</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FRESH 47 MM PERSPECTIVE HOLDOUT</p><h2>亚像素不是猜测。<br/><span>端点、采样与深度都被外部 oracle 检查。</span></h2></div><p>独立 pinhole/ray-plane oracle 不导入 bpy、mathutils 或被测重建器。运动 fixture 的正确双线性 RMSE 为 nearest 的 1/45–1/60，且错误符号控制更差。</p></div>
      <div className="d12p-table"><div className="head"><b>FIXTURE</b><b>VALID</b><b>ENDPOINT MAX PX</b><b>CORRECT RMSE</b><b>PSNR</b><b>VS NEAREST</b></div>{rows.map(row=><div className="row" key={row[0]}>{row.map((value,index)=>index===0?<strong key={value}>{value}</strong>:<code key={index}>{value}</code>)}</div>)}</div>
      <div className="d111-process d12p-process"><article><span>VECTOR ENDPOINT</span><strong>≤ 4.08e−5</strong><b>PX MAX · MOVING</b><small>frozen max: 1/1024 px</small></article><i>→</i><article><span>SAMPLE</span><strong>q = x+Vx</strong><b>y − Vy · TOP LEFT</b><small>clip bilinear · four taps</small></article><i>→</i><article><span>DEPTH</span><strong>96–100%</strong><b>DIRECT ID REJECTED</b><small>transform prediction required</small></article><i>→</i><article><span>BRIDGE</span><strong>16 / 16</strong><b>RAW EXR EXACT</b><small>decoded float32 unchanged</small></article></div>
    </section>

    <section className="section d12p-depth">
      <div className="section-index">02 / TRANSFORM-AWARE HISTORY</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> PREVIOUS DEPTH IS NOT CURRENT DEPTH</p><h2>同一个表面点，<br/><span>跨帧深度本来就会变化。</span></h2></div><p>当前 pixel-center ray 与当前刚性平面相交，反变换到 object local，再应用 previous object transform，并投影到 previous camera。只有这个预测深度能验证对应历史。</p></div>
      <div className="d111-formula d12p-formula"><article><span>CURRENT RAY</span><code>pixel center<br/>→ current plane</code><small>recover local surface point</small></article><i>→</i><article className="accept"><span>RIGID TRANSFORM</span><code>local point<br/>→ previous world</code><small>object + camera known</small></article><i>→</i><article><span>PREVIOUS TEST</span><code>bilinear Z ≈<br/>predicted previous Z</code><small>direct depth identity forbidden</small></article></div>
    </section>

    <section className="section d12p-evidence" id="evidence">
      <div className="section-index">03 / FORMAL DIAGNOSTIC IMAGES</div>
      <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> 24 PNG + 24 HASHED SIDECARS</p><h2>正确、最近邻与错误符号，<br/><span>放在同一个空间坐标系里看。</span></h2></div><p>这些图来自正式证据提交 `{commit}`，用于定位，不参与 verdict。每张图都绑定 current EXR、adapter report 与 Python reconstructor report；数值判定来自 raw float32/u8 arrays。</p></div>
      <div className="d11-gallery d111-gallery d12p-gallery">{gallery.map(([slug,label])=><article key={slug}><header><b>{label}</b><span>107 × 67 · FORMAL</span></header><div>{views.map(([view,caption])=><figure key={view}><img src={`${raw}/${slug}/${view}.png`} width="107" height="67" alt={`${label} ${caption}`}/><figcaption>{caption}</figcaption></figure>)}</div></article>)}</div>
    </section>

    <section className="section d12p-audit" id="audit">
      <div className="section-index">04 / FAILURE-PRESERVING AUDIT CHAIN</div>
      <div className="contact-heading"><div><p className="eyebrow"><span /> INVALID RUNS AND FAILED AUDITS STAY VISIBLE</p><h2>更正基础设施，<br/><span>不更正科学结果。</span></h2></div><p>原 D12 因 Node 父目录不存在而无效；C1 只修复目录并全量重跑。首次 audit 暴露相对路径与负结果 totality 缺陷；预注册 C2 只重放一次，最终确认原 negative verdict。</p></div>
      <div className="d111-corrections d12p-corrections"><article className="fail"><span>D12 ORIGINAL</span><strong>INVALID</strong><b>Node parent ENOENT</b><small>no scientific verdict</small></article><article className="fail"><span>C1 FIRST AUDIT</span><strong>FAIL</strong><b>relative URI + 57/57 assumption</b><small>negative result unchanged</small></article><article className="pass"><span>C2 AUDIT</span><strong>PASS</strong><b>10 / 10 checks</b><small>47/57 faithfully replayed</small></article></div>
      <div className="contact-nonclaim"><b>NOT_SUPPORTED ≠ PROJECTIVE RECONSTRUCTION IS USELESS</b><p>运动数值证据支持继续研究，但 D12 的完整合同按预注册规则失败。下一步必须拆成两个新的 fresh holdout：跨语言 RFC 8785/JCS 报告身份，以及基于 measured floating floor 的静态容差；不能回改本结果。</p></div>
      <div className="contact-artifacts"><a href={`${repo}experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/results.json`}><span>MACHINE RESULT</span><b>NOT SUPPORTED · 47 / 57 ↗</b></a><a href={`${repo}experiments/blender-projective-subpixel-reconstruction-holdout-c1-v0-1/audit.c2.json`}><span>C2 AUDIT</span><b>PASS · 10 / 10 ↗</b></a><a href={`${repo}research/2026-08-27-b52-d12-c1-formal-result-and-audit-failure.md`}><span>RESULT NOTE</span><b>measurements · failures · limits ↗</b></a><a href={`${repo}specs/blender-projective-subpixel-reconstruction-holdout.v0.1.json`}><span>FROZEN SPEC</span><b>oracle · gates · attacks ↗</b></a></div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12 Projective Subpixel Research</b></div><p>moving numerics pass · complete contract rejected · C2 audit pass</p><a href="../journal/">继续看实验日志 →</a></footer>
  </main>;
}
