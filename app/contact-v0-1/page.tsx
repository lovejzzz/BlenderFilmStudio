import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';

const publicUrl = 'https://lovejzzz.github.io/BlenderFilmStudio/contact-v0-1/';
const imageBasePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';
const repo = 'https://github.com/lovejzzz/BlenderFilmStudio/blob/main/';

export const metadata: Metadata = {
  title: 'B04 接触基准｜SceneSpec v0.3｜Blender Film Studio',
  description: 'Blender 5.2 手—道具拿取实测：中心握点被证伪、socket 坐标系修正、2 mm 表面间距、镜头可见性与盲审。',
  alternates: { canonical: publicUrl },
  openGraph: {
    title: 'B04：从穿透 18.45 mm，到稳定 2 mm 间距',
    description: '几何自动化已修正；镜头可见性已建门禁。可信抓取仍待独立人类审查。',
    url: publicUrl,
    images: [{ url: 'https://lovejzzz.github.io/BlenderFilmStudio/contact-v0-3/D83K-frame-0078.png', width: 960, height: 540, alt: 'B04 corrected technical prop pickup at hold frame 78' }],
  },
};

const frames = [
  ['0036', 'APPROACH', '0 overlap pairs'],
  ['0048', 'ACQUIRE', 'Child Of 0 → 1'],
  ['0078', 'HOLD', 'relative drift ≈ 0'],
  ['0108', 'HOLD END', 'transport 0.4806 m'],
  ['0120', 'RELEASE', 'prop remains; hand retreats'],
];

const correctedFrames = [
  ['0036', 'APPROACH', 'independent prop and hand'],
  ['0048', 'ACQUIRE', '2 mm contact shell'],
  ['0078', 'HOLD', '0 overlap · visible pair'],
  ['0108', 'HOLD END', 'rigid transport complete'],
  ['0120', 'RELEASE', 'constraint released'],
];

const checks = [
  ['C01–C03', '合同与接近', '约束绑定、影响值状态、最后 12 帧距离单调下降'],
  ['C04–C06', '接触与漂移', '最大位置误差 1.6e−7 m；旋转 0°；相对漂移 3.18e−7 m'],
  ['C07–C08', '搬运与切换', '搬运 0.4806 m；拿起/释放跳变约 1.3e−7 m'],
  ['C09–C10', '求值几何', 'APPROACH/RETREAT 零重叠；端点间隙 0.1448 / 0.6051 m'],
];

const negatives = [
  '缺失道具对象', '缺失角色 socket', '缺 CREATE_CONSTRAINT 权限', '影响值始终为零',
  '释放位姿跳变 1 m', '接近阶段网格重叠', '静态假 target marker', '请求原始而非求值几何',
];

export default function ContactV01Page() {
  return (
    <main className="contact-page">
      <header className="topbar">
        <Link className="brand" href="/"><span className="brand-mark">BFS</span><span>Blender Film Studio</span></Link>
        <nav aria-label="接触实验导航"><Link href="/">技术基线</Link><Link href="/actor-v0-1">角色实验</Link><Link href="/research-agenda">研究路线</Link><a href="#evidence">画面</a><a href="#limits">边界</a></nav>
        <span className="edition contact-edition">Contact 0.1</span>
      </header>

      <section className="contact-hero">
        <div className="contact-grid" aria-hidden="true" />
        <div className="contact-hero-copy"><p className="eyebrow"><span /> BLENDER 5.2 · EXECUTED · B04</p><h1>几何修正成立。<br /><span>可信抓取仍待盲审。</span></h1><p>中心握点先被 18.45 mm 穿入证伪；校正 socket 坐标系后，60 帧 HOLD 保持约 2 mm 表面间距。机器几何已经过关，但动作、重量感和电影表达仍不能由这些数字代替。</p></div>
        <aside className="contact-gate"><b>CURRENT GATE</b><strong>GEOMETRY PASS<br />HUMAN PENDING</strong><code>HOLD overlap 0 / 60</code><code>surface gap 1.999974 mm</code><small>0 valid blind reviews</small></aside>
        <div className="contact-stats"><article><strong>2 / 2</strong><span>修正场景净构建一致</span><small>03596141…f5c88</small></article><article><strong>10 / 10</strong><span>合同与时序检查</span><small>8 / 8 negatives rejected</small></article><article><strong>2.00 mm</strong><span>HOLD 最小表面间距</span><small>0 overlap · 0 inside depth</small></article><article><strong>PASS</strong><span>审查机位可见性</span><small>human gate still pending</small></article></div>
      </section>

      <section className="section contact-verdict">
        <div className="section-index">00 / 有限结论</div>
        <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> WHAT THE EXPERIMENT PROVES</p><h2>Blender 可以编译<br /><span>可编辑的交互状态。</span></h2></div><p>它证明 Child Of 父级切换、Action、资产 socket 和依赖图几何可以被同一份不可变 BuildPlan 驱动并测量。它不证明手指抓握、受力、软组织、重量感或电影表演已经自动解决。</p></div>
        <div className="contact-boundary"><b>AUTOMATION PASS</b><span>asset-bound target</span><span>parent switch</span><span>2 mm rigid shell</span><span>camera visibility</span><span>identity lock</span><strong>HUMAN PENDING</strong></div>
      </section>

      <section className="section contact-evidence" id="evidence">
        <div className="section-index light">01 / 被证伪的中心握点基线</div>
        <div className="contact-heading"><div><p className="eyebrow"><span /> FROZEN BASELINE · NOT THE CORRECTION</p><h2>时序看起来成立，<br />几何却<span>穿入 18.45 mm。</span></h2></div><p>这些图与 v0.1 的 10/10 检查保持冻结。更强的显式三角形诊断后来证明 HOLD 60/60 帧相交，因此不能再把它当作接触质量通过的画面。</p></div>
        <div className="contact-gallery">{frames.map(([frame, title, note], index) => <figure className={index === 2 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/contact-v0-1/B04-frame-${frame}.png`} alt={`B04 ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div>
      </section>

      <section className="section contact-contract">
        <div className="section-index">02 / SceneSpec v0.3</div>
        <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> STATIC MARKERS ARE NOT CONTACT</p><h2>v0.3 新增三件事：<br /><span>绑定、切换、求值。</span></h2></div><p>道具 GRIP socket 必须绑定到真实资产对象；父级切换只能用受限 CHILD_OF 指令；碰撞检查必须读取依赖图求值后的网格。v0.1 与 v0.2 的含义保持冻结。</p></div>
        <div className="contact-flow"><article><span>01</span><b>ASSET_OBJECT SOCKET</b><p>assetRef + objectRef + local transform</p></article><i>→</i><article><span>02</span><b>CHILD_OF TRACK</b><p>target actor/socket + inverse + influence keys</p></article><i>→</i><article><span>03</span><b>EVALUATED_WORLD</b><p>Depsgraph mesh → BVH overlap / proximity</p></article></div>
        <div className="contact-plan"><span>BUILDPLAN SHA-256</span><code>bb9e4ff1484d…45b08</code><b>SCENE v0.3</b><b>BLENDER 5.2.0 LTS</b></div>
      </section>

      <section className="section contact-metrics">
        <div className="section-index light">03 / 自动验收</div>
        <div className="contact-heading"><div><p className="eyebrow"><span /> TEN CHECKS · EVALUATED STATE</p><h2>不是“约束存在”。<br />是<span>最终状态满足阈值。</span></h2></div><p>每帧从 Blender dependency graph 读取手掌、道具、约束与变形网格。BVH overlap 只代表相交三角形对，不代表穿透深度或压力。</p></div>
        <div className="contact-checks">{checks.map(([id, title, detail]) => <article key={id}><span>{id}</span><h3>{title}</h3><p>{detail}</p><b>PASS</b></article>)}</div>
        <div className="contact-nonclaim"><b>V0.1 MEASUREMENT LIMIT</b><p>HOLD 最大重叠为 11 个 source-polygon face pairs；这里仅记录，不解释为“11 mm”或任何穿透体积。端点间隙是 vertex-to-surface 采样，不是精确 signed distance。</p></div>
      </section>

      <section className="section contact-diagnostic">
        <div className="section-index">03B / 更强诊断的负结果</div>
        <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> V0.1 PASS ≠ CONTACT QUALITY PASS</p><h2>socket 几乎零误差，<br /><span>手仍穿入道具 18.45 mm。</span></h2></div><p>v0.2 显式三角化求值网格，计算非相交表面的精确无符号距离，并用闭合网格 ray parity + 最近表面距离报告 inside-vertex 深度代理。HOLD 的 60/60 帧均发生表面相交。</p></div>
        <div className="diagnostic-result"><article><span>APPROACH</span><strong>0 / 36</strong><b>重叠帧</b><small>minimum separation 94.78 mm</small></article><article className="fail"><span>ACQUIRE</span><strong>68.33 mm</strong><b>最大深度代理</b><small>9 / 12 overlap frames</small></article><article className="fail"><span>HOLD</span><strong>18.45 mm</strong><b>最大深度代理</b><small>60 / 60 overlap frames</small></article><article><span>RETREAT</span><strong>0 / 24</strong><b>重叠帧</b><small>minimum separation 605.08 mm</small></article></div>
        <div className="diagnostic-verdict"><b>CLASSIFICATION</b><code>V01_AUTOMATIC_PASS_INSUFFICIENT_FOR_CONTACT_QUALITY</code><p>这是对验证器能力的证伪，不是把原实验结果改成“没运行”。v0.1 的 10 项合同与时序检查确实通过；v0.2 证明它们不足以支持“接触质量通过”。</p></div>
      </section>

      <section className="section contact-evidence">
        <div className="section-index light">03C / socket-frame 修正</div>
        <div className="contact-heading"><div><p className="eyebrow"><span /> COORDINATE CONTRACT CORRECTED</p><h2>不是继续调距离。<br />先让<span>语义坐标系对齐可见网格。</span></h2></div><p>第一次表面偏移仍失败，因为偏移沿着倾斜的骨骼轴，而盒状手掌的轴已经烘焙在角色空间。第二次先用逆静止旋转校正 PALM_R，再应用冻结的 2 mm 接触壳；双净构建和逐帧几何报告均复现。</p></div>
        <div className="diagnostic-result"><article><span>FAILED SURFACE OFFSET</span><strong>18.45 mm</strong><b>最大深度代理</b><small>wrong socket frame · 60/60 overlap</small></article><article><span>SOCKET FRAME</span><strong>0°</strong><b>HOLD 旋转误差</b><small>ActorSpec hash locked</small></article><article><span>CORRECTED HOLD</span><strong>0 / 60</strong><b>重叠帧</b><small>inside depth 0 m</small></article><article><span>CONTACT SHELL</span><strong>2.00 mm</strong><b>最小精确间距</b><small>measured 1.999974 mm</small></article></div>
        <div className="contact-gallery">{correctedFrames.map(([frame, title, note], index) => <figure className={index === 2 ? 'wide' : ''} key={frame}><Image src={`${imageBasePath}/contact-v0-3/D83K-frame-${frame}.png`} alt={`B04 corrected ${title} frame ${frame}`} width={960} height={540} sizes="(max-width: 800px) 100vw, 50vw" /><figcaption><span>FRAME {frame}</span><h3>{title}</h3><code>{note}</code></figcaption></figure>)}</div>
        <div className="diagnostic-verdict"><b>CAMERA IS ALSO A GATE</b><code>CLIP_C42N REJECTED → CLIP_D83K VISIBLE</code><p>原修正机位把 HOLD 中段的手完全挡在头后：手的最低/中位直接可见比例均为 0%。独立背面技术机位达到手 25% / 66.7%、道具 75% / 83.3%，因此只允许后者进入盲审。可见性通过仍不等于构图或动作通过。</p></div>
      </section>

      <section className="section contact-failure">
        <div className="section-index">04 / 先失败，再修正</div>
        <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> FIRST RUN · 7 / 10</p><h2>父级切换没跳。<br /><span>几何与朝向却错了。</span></h2></div><p>第一轮拿起/释放跳变只有约 10⁻⁷ m，但握持旋转误差 90°，初始间隙只有 4.4 mm，接近与退开阶段发生重叠。由此修正动作距离、释放时机和道具朝向，再重新生成 Action 与哈希。</p></div>
        <div className="contact-before-after"><article><span>FAILED RUN</span><strong>7 / 10</strong><p>rotation 90°<br />clearance 0.0044 m<br />clear-phase overlap</p></article><i>→</i><article className="fixed"><span>CORRECTED RUN</span><strong>10 / 10</strong><p>rotation 0°<br />clearance 0.1448 m<br />clear-phase overlap 0</p></article><aside><b>没有被修好的问题</b><p>技术盒状手掌仍不具备手指闭合、抓握区域、接触压力、软组织或重量感。机器通过不能覆盖这个视觉事实。</p></aside></div>
      </section>

      <section className="section contact-negatives">
        <div className="section-index light">05 / 预注册反例</div>
        <div className="contact-heading"><div><p className="eyebrow"><span /> 8 / 8 REJECTED</p><h2>系统必须知道<br /><span>哪些“成功”是伪造的。</span></h2></div><p>反例分别在 Schema、BuildPlan、Blender 编译和最终求值四层失败。尤其是静态假 marker：它看起来有 target，却与真实道具脱离，HOLD 位置误差达到 1.647 m。</p></div>
        <ol className="contact-negative-list">{negatives.map((item, index) => <li key={item}><span>N{String(index + 1).padStart(2, '0')}</span><b>{item}</b><small>REJECTED</small></li>)}</ol>
      </section>

      <section className="section contact-limits" id="limits">
        <div className="section-index">06 / 当前停止门槛</div>
        <div className="contact-heading dark-heading"><div><p className="eyebrow dark"><span /> EXPERIMENT COMPLETE = FALSE</p><h2>刚性几何完成。<br /><span>可信表演尚未完成。</span></h2></div><p>修正版已经满足合同、双构建、表面距离和镜头可见性门禁。预注册仍要求至少三名独立评审通过；而且即使盲审通过，也只说明这个技术代理的交互可接受，不代表手指、受力或电影级表演已经解决。</p></div>
        <div className="contact-gates"><article><span>DONE</span><b>合同 / 哈希 / 双构建</b></article><article><span>CORRECTED</span><b>HOLD 0/60 重叠 · 2 mm 间距</b></article><article className="pending"><span>PENDING · 0 / 3</span><b>CLIP_D83K 盲化人类审查</b></article><article className="blocked"><span>NOT PROVEN</span><b>可信手指抓握与重量感</b></article></div>
        <div className="contact-review-action"><div><span>INDEPENDENT REVIEW · NO METRICS</span><b>如果你尚未看过本页数据，可以参加 CLIP_D83K 盲审。</b><p>独立页面只显示 6 秒视频和固定问题，答案下载为本地 JSON，不会上传个人信息。旧 CLIP_A17F 与被遮挡的 C42N 不会混入本轮。</p></div><Link href="/review-b04-v02">打开 v0.2 盲审页面 →</Link></div>
        <div className="contact-artifacts"><a href={`${repo}research/2026-08-26-b04-socket-frame-correction-result.md`}><span>CORRECTION RESULT</span><b>坐标系修正与边界 ↗</b></a><a href={`${repo}research/2026-08-26-b04-contact-visibility-result.md`}><span>VISIBILITY RESULT</span><b>原机位失败与新机位通过 ↗</b></a><a href={`${repo}experiments/contact-v0-3/results.json`}><span>V0.3 EVIDENCE</span><b>哈希、逐帧几何与门禁 ↗</b></a><a href={`${repo}research/2026-08-26-b04-human-review-protocol-v0.2.md`}><span>BLIND REVIEW</span><b>冻结的人类审查协议 ↗</b></a></div>
      </section>

      <footer><div><span className="brand-mark">BFS</span><b>B04 Contact Benchmark</b></div><p>SceneSpec v0.3 · Blender 5.2.0 LTS · Evidence, not a demo reel</p><Link href="/research-agenda">继续研究路线 →</Link></footer>
    </main>
  );
}
