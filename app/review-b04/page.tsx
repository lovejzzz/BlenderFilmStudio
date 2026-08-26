import type { Metadata } from 'next';
import ReviewForm from './ReviewForm';

const basePath = process.env.GITHUB_PAGES === 'true' ? '/BlenderFilmStudio' : '';

export const metadata: Metadata = {
  title: 'CLIP_A17F｜匿名交互审查',
  description: '不显示机器指标的独立视觉交互审查材料。',
  robots: { index: false, follow: false },
};

export default function ReviewB04Page() {
  return <main className="review-page"><header className="review-topbar"><span className="brand-mark">BFS</span><b>Independent visual review</b><code>Protocol 0.1 · CLIP_A17F</code></header><ReviewForm videoSrc={`${basePath}/contact-review/CLIP_A17F.mp4`} clipId="CLIP_A17F" protocolVersion="0.1.0" evidenceHref="/contact-v0-1" /><footer><span>NO METRICS SHOWN BEFORE SUBMISSION</span><p>Visual interaction pilot · No remote data collection</p></footer></main>;
}
