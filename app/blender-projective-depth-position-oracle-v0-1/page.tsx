import type { Metadata } from 'next';
import Link from 'next/link';
import result from '../../experiments/blender-material-owner-rigid-directional-position-oracle-development-v0-1/results.json';
import audit from '../../experiments/blender-material-owner-rigid-directional-position-oracle-development-v0-1/audit.posthoc.json';

const canonical = 'https://lovejzzz.github.io/BlenderFilmStudio/blender-projective-depth-position-oracle-v0-1/';

export const metadata: Metadata = {
  title: 'D12.14-P1 Projective Depth & Position Oracle｜Blender Film Studio',
  description: 'H1 事后诊断定位 linear-Z 插值错误；两次新 Blender 5.2 renders 验证 Position pass 能把 Vector oracle 绑定到真实 first-hit sample。',
  alternates: { canonical },
  openGraph: {
    title: 'D12.14-P1 · Position Oracle Supported',
    description: '1/Z restores 16,065 posthoc witnesses; fresh Position passes reduce Vector oracle error to 3.28e−5 px.',
    url: canonical,
    images: [],
  },
  twitter: {
    card: 'summary',
    title: 'D12.14-P1 · Projective Instrument Repair',
    description: 'Two different failures, two different repairs: inverse depth and actual-hit Position.',
    images: [],
  },
};

const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';
const official = 'https://github.com/blender/blender/blob/fbe6228777e7d9afefcd61a413844e790ae75db7/';
const measurements = result.measurements;

function scientific(value: number, digits = 3) {
  return value.toExponential(digits).replace('e-', 'e−').replace('e+', 'e+');
}

export default function ProjectiveDepthPositionOraclePage() {
  return <main className="contact-page d1212-page d1214p1-page">
    <header className="topbar">
      <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
      <nav aria-label="D12.14-P1 projective oracle 导航">
        <Link href="/blender-material-owner-rigid-directional-render-holdout-v0-1">D12.14-H1</Link>
        <a href="#split">双重根因</a><a href="#source">源码</a><a href="#probe">P1 实测</a><a href="#identity">身份</a><a href="#boundary">边界</a>
        <Link href="/blender-projective-depth-formal-invalidation-v0-1">D12.14-H2</Link>
        <Link href="/journal">日志</Link>
      </nav>
      <span className="edition contact-edition">Development P1 · Supported</span>
    </header>

    <section className="contact-hero d1214p1-hero">
      <div className="contact-grid" aria-hidden="true" />
      <div className="contact-hero-copy">
        <p className="eyebrow"><span /> B52-D12.14-P1 · TWO FRESH POSITION RENDERS · DEVELOPMENT ONLY</p>
        <h1>不是运动算错了。<br/><span>是我们问错了采样点。</span></h1>
        <p>H1 把真实 subpixel first hit 与整数像素中心比较，同时在线性 Z 空间插值透视深度。P1 用 Blender Position pass 绑定实际命中点；postfailure replay 则把深度搬到 inverse-depth 空间。两条错误来自不同层，不能用同一个阈值掩盖。</p>
      </div>
      <aside className="contact-gate d1214p1-gate">
        <b>DEVELOPMENT VERDICT</b>
        <strong>SUPPORTED</strong>
        <code>{result.gatesPassed} / {result.gatesTotal} gates</code>
        <code>scientific verdict · null</code>
        <small>{result.experimentId}</small>
      </aside>
      <div className="contact-stats">
        <article><strong>16,065</strong><span>NEITHER recovered</span><small>posthoc inverse-depth replay</small></article>
        <article><strong>{scientific(measurements.positionOracleVectorAbsoluteErrorPixels.maximum, 2)}</strong><span>Position oracle max</span><small>pixels · under 1/16384</small></article>
        <article><strong>{measurements.foregroundPositionPixels.toLocaleString('en-US')}</strong><span>actual hit positions</span><small>finite · owner exact</small></article>
        <article><strong>6 / 6</strong><span>decoded passes exact</span><small>two fresh EXR repeats</small></article>
      </div>
    </section>

    <section className="section d1214p1-split" id="split">
      <div className="section-index">00 / TWO FAILURES · TWO REPAIRS</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> DO NOT TURN GEOMETRY INTO A TOLERANCE</p><h2>一个错在深度空间。<br/><span>一个错在采样位置。</span></h2></div>
        <p>NEITHER 的 270 并不是 raster-domain 消失；16,541 个 same-owner supports 在 risk 计算之前被 linear-Z gate 淘汰。Vector gate 则把 Cycles 的实际 first hit 当成 integer center。</p>
      </div>
      <div className="d1214p1-repair-grid">
        <article className="before"><span>DEPTH · H1</span><strong>Z<sub>q</sub> = bilinear(Z)</strong><code>median error · 3.820e−1</code><p>透视平面上的 Z 不是 screen-space affine。直接插值产生最高 0.465 的系统误差。</p></article>
        <i>→</i>
        <article className="after"><span>DEPTH · NEXT CANDIDATE</span><strong>1 / bilinear(1/Z)</strong><code>16,819 / 16,819 pass old gate</code><p>Reciprocal depth 在 projective plane 上是 affine；radius-2 NEITHER 精确恢复到 16,065。</p></article>
        <article className="before"><span>VECTOR · H1</span><strong>project(pixel center)</strong><code>max error · 5.7716e−4 px</code><p>整数中心不是 Cycles data pass 使用的实际 first-hit point。</p></article>
        <i>→</i>
        <article className="after"><span>VECTOR · P1</span><strong>project(Position.xyz)</strong><code>max error · 3.2810e−5 px</code><p>同一 world-space hit 经 current/previous transforms 投影，重新通过原 1/16384 gate。</p></article>
      </div>
    </section>

    <section className="section d1214p1-source" id="source">
      <div className="section-index">01 / BLENDER 5.2 EXACT-BUILD SOURCE</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> BUILD fbe6228777e7 · SOURCE-BOUND INFERENCE</p><h2>Position 与 Vector，<br/><span>来自同一个 sd→P。</span></h2></div>
        <p>这不是从画面外观猜测。精确 build commit 的 Cycles 路径把 Depth 写为 camera-space Z、Position 写为 <code>sd→P</code>，motion vector 也从同一 ShaderData 出发，经 previous object 与 raster transforms 后求差。</p>
      </div>
      <div className="d1214p1-source-chain">
        <article><span>FIRST HIT</span><strong>ShaderData.sd→P</strong><p>同一个 surface intersection，保留真实 subpixel sample。</p></article><i>→</i>
        <article><span>DATA PASSES</span><strong>Depth + Position</strong><p>Depth 是 camera Z；Position 是 world-space XYZ。</p></article><i>→</i>
        <article><span>MOTION PATH</span><strong>object pre transform</strong><p>current hit 映回 previous rigid object state。</p></article><i>→</i>
        <article><span>RASTER</span><strong>previous − current</strong><p>两个 projected endpoints 形成 Vector.XY。</p></article>
      </div>
      <div className="contact-artifacts d1214p1-source-links">
        <a href={`${official}intern/cycles/kernel/film/data_passes.h`}><span>OFFICIAL SOURCE</span><b>data_passes.h ↗</b></a>
        <a href={`${official}intern/cycles/kernel/geom/primitive.h`}><span>OFFICIAL SOURCE</span><b>primitive.h ↗</b></a>
        <a href={`${official}intern/cycles/scene/camera.cpp`}><span>OFFICIAL SOURCE</span><b>camera.cpp ↗</b></a>
      </div>
    </section>

    <section className="section d1214p1-probe" id="probe">
      <div className="section-index">02 / TWO FRESH BLENDER 5.2 RENDERS</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> POSITION IS A CONTROL · NEVER A RECONSTRUCTION INPUT</p><h2>27,383 个命中点，<br/><span>把样本错位测了出来。</span></h2></div>
        <p>P1 在 H1 development-only 88° fixture 上做两个新的 factory-empty current-frame renders，只增加 Position pass。该 fixture 永久排除于 H2 formal measurement。</p>
      </div>
      <div className="d1214p1-metric-grid">
        <article><span>INTEGER-CENTER ORACLE · MAX</span><strong>{scientific(measurements.pixelCenterVectorAbsoluteErrorPixels.maximum, 4)}</strong><code>pixels · FAIL</code><div className="meter bad"><i /></div></article>
        <article><span>POSITION ORACLE · P99</span><strong>{scientific(measurements.positionOracleVectorAbsoluteErrorPixels.p99, 4)}</strong><code>pixels · PASS</code><div className="meter good"><i /></div></article>
        <article><span>POSITION ORACLE · MAX</span><strong>{scientific(measurements.positionOracleVectorAbsoluteErrorPixels.maximum, 4)}</strong><code>limit · 6.1035e−5</code><div className="meter good max"><i /></div></article>
        <article><span>POSITION → DEPTH · MAX</span><strong>{measurements.currentDepthFromPositionAbsoluteError.maximum}</strong><code>exact on 27,383 pixels</code><div className="meter exact"><i /></div></article>
      </div>
      <div className="d1214p1-offset">
        <div><span>ACTUAL CURRENT RASTER OFFSET</span><strong>≈ 5.3e−4 px</strong><p>X: {scientific(measurements.currentRasterOffsetFromIntegerPixelX.minimum, 3)}–{scientific(measurements.currentRasterOffsetFromIntegerPixelX.maximum, 3)} · Y: {scientific(measurements.currentRasterOffsetFromIntegerPixelY.minimum, 3)}–{scientific(measurements.currentRasterOffsetFromIntegerPixelY.maximum, 3)}</p></div>
        <div className="pixel-field" aria-hidden="true"><i className="center"/><i className="hit"/><span>integer center</span><b>Position hit</b></div>
      </div>
    </section>

    <section className="section d1214p1-identity" id="identity">
      <div className="section-index">03 / DECODED IDENTITY ≠ CONTAINER IDENTITY</div>
      <div className="contact-heading dark-heading">
        <div><p className="eyebrow dark"><span /> SAME PASS DATA · DIFFERENT FILE BYTES</p><h2>六层像素完全一致。<br/><span>容器仍然不应该相等。</span></h2></div>
        <p>Repeat identity 必须绑定 decoded roster、channels、shape、dtype 与 pixel bytes。EXR header 的运行时 provenance 单独列出，不得混入算法可重复性。</p>
      </div>
      <div className="d1214p1-identity-grid">
        {['Combined', 'Depth', 'Position', 'Vector', 'Object Index', 'Material Index'].map(name => <article key={name}><span>{name}</span><strong>EXACT</strong><i /></article>)}
      </div>
      <div className="d1214p1-metadata">
        <article className="pass"><span>DECODED ARRAYS</span><strong>BYTE EXACT</strong><code>R1 = R2 · every pass</code></article>
        <article className="warn"><span>EXR CONTAINERS</span><strong>DIFFERENT</strong><code>{result.repeatIdentity.differenceNames.join(' · ')}</code></article>
        <article><span>POSTHOC CHECK</span><strong>{audit.checksPassed} / {audit.checksTotal}</strong><code>not a preregistered P1 gate</code></article>
      </div>
    </section>

    <section className="section d1214p1-boundary" id="boundary">
      <div className="section-index">04 / H2 ENTRY CONTRACT & OBSERVED OUTCOME</div>
      <div className="contact-heading">
        <div><p className="eyebrow"><span /> P1 CLOSED AN INSTRUMENT GAP · H2 DID NOT REACH MEASUREMENT</p><h2>H2 没有测到 inverse depth。<br/><span>它停在正式调用入口。</span></h2></div>
        <p>H2 corrected preflight把schema handoff、operation replay、decoded digest与failure path变成可执行合同，但正式runner在启动任何Blender child前遇到relative/absolute path admission缺口。0 render，scientific verdict仍为null。</p>
      </div>
      <div className="d1214p1-h2-outcome"><span>OBSERVED H2 OUTCOME</span><strong>15 / 15 PREFLIGHT → 0 FORMAL CHILDREN → NULL VERDICT</strong><p>冻结runner失败后没有absolute-path workaround或同ID重跑。<Link href="/blender-projective-depth-formal-invalidation-v0-1">查看完整失效链与下一版admission contract →</Link></p></div>
      <div className="d1214p1-next-grid">
        <article><span>ALGORITHM</span><strong>inverse-depth gate</strong><p>正式 candidate 使用 reciprocal interpolation；linear Z 保留为 negative control。</p></article>
        <article><span>CONTROL ORACLE</span><strong>Position only</strong><p>Position 只验证 Vector/Depth source semantics，禁止影响 reconstruction decision。</p></article>
        <article><span>FRESHNESS</span><strong>new fixture + passes</strong><p>新 camera、raster、tokens、signals、seed 与 output；P1/H1 EXR 禁止输入。</p></article>
        <article><span>TOTALITY</span><strong>executable failure chain</strong><p>Analyzer 与 audit replay source/runner counts；任何 child failure 仍有 receipt。</p></article>
      </div>
      <div className="contact-artifacts">
        <a href={`${repo}specs/blender-material-owner-rigid-directional-position-oracle-development.v0.1.json`}><span>P1 PREREGISTRATION</span><b>development contract ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-rigid-directional-position-oracle-development-v0-1/results.json`}><span>MACHINE RESULT</span><b>{result.gatesPassed} / {result.gatesTotal} supported ↗</b></a>
        <a href={`${repo}experiments/blender-material-owner-rigid-directional-position-oracle-development-v0-1/audit.posthoc.json`}><span>POSTHOC CHECK</span><b>{audit.auditHash.slice(0, 16)}… ↗</b></a>
        <a href={`${repo}research/2026-08-28-b52-d12-14-position-oracle-development-result.md`}><span>RESULT NOTE</span><b>measurements + limits ↗</b></a>
      </div>
    </section>

    <footer><div><span className="brand-mark">BFS</span><b>B52-D12.14-P1 Projective Instrument Repair</b></div><p>2 fresh renders · 14/14 development gates · scientific verdict null</p><Link href="/blender-projective-depth-formal-invalidation-v0-1">继续 H2 invalidation →</Link></footer>
  </main>;
}
