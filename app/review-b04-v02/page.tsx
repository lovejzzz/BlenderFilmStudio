import type { Metadata } from 'next';
import ReviewForm from '../review-b04/ReviewForm';

export const metadata: Metadata = {
  title: 'CLIP_D83K｜匿名交互审查',
  description: 'Blender Film Studio B04 修正接触候选的盲化人类审查。',
  robots: { index: false, follow: false },
};

export default function ReviewB04V02Page() {
  const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';
  return <main className="review-page"><header className="review-topbar"><span className="brand-mark">BFS</span><b>Independent visual review</b><code>Protocol 0.2 · CLIP_D83K</code></header><ReviewForm videoSrc={`${basePath}/contact-review/CLIP_D83K.mp4`} clipId="CLIP_D83K" protocolVersion="0.2.0" evidenceHref="/contact-v0-1" /><footer><span>NO METRICS SHOWN BEFORE SUBMISSION</span><p>Visual interaction pilot · No remote data collection</p></footer></main>;
}
