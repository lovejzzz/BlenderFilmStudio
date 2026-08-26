import type { Metadata } from 'next';
import B06ReviewForm from './B06ReviewForm';

export const metadata: Metadata = { title: 'CLIP_P84R｜源物理匿名审查', description: 'Blender Film Studio 对一条哈希锁定源刚体轨迹的盲化人类审查。', robots: { index: false, follow: false } };

export default function ReviewB06Page() {
  const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';
  return <main className="review-page"><header className="review-topbar"><span className="brand-mark">BFS</span><b>Independent visual review</b><code>Protocol 0.4 · CLIP_P84R</code></header><B06ReviewForm videoSrc={`${basePath}/physics-review/CLIP_P84R.mp4`} /><footer><span>NO METRICS SHOWN BEFORE SUBMISSION</span><p>Single source-trajectory plausibility pilot · No remote data collection</p></footer></main>;
}
