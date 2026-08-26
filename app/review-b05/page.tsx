import type { Metadata } from 'next';
import B05ReviewForm from './B05ReviewForm';

export const metadata: Metadata = {
  title: 'CLIP_G52Q｜B05 匿名抓握审查',
  description: 'Blender Film Studio B05 编译抓握候选的盲化人类审查。',
  robots: { index: false, follow: false },
};

export default function ReviewB05Page() {
  const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';
  return <main className="review-page"><header className="review-topbar"><span className="brand-mark">BFS</span><b>Independent visual review</b><code>Protocol 0.3 · CLIP_G52Q</code></header><B05ReviewForm videoSrc={`${basePath}/grasp-review/CLIP_G52Q.mp4`} /><footer><span>NO METRICS SHOWN BEFORE SUBMISSION</span><p>Technical grasp-motion pilot · No remote data collection</p></footer></main>;
}
