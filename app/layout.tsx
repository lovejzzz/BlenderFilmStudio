import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL('https://lovejzzz.github.io/BlenderFilmStudio/'),
  title: 'Blender Film Studio｜AI → Blender 电影工作流技术基线',
  description: '截至 2026-08-25，对 AI 驱动 Blender 电影生产链逐环节进行可行性、成熟度、证据与缺口调查。',
  openGraph: {
    title: 'Blender Film Studio｜AI → 3D → Cinema',
    description: '15 个技术环节的可行性、成熟度、证据与缺口调查。研究截点：2026-08-25。',
    type: 'website',
    locale: 'zh_CN',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/',
    images: [{ url: 'https://lovejzzz.github.io/BlenderFilmStudio/og.png', width: 1672, height: 941, alt: 'Blender Film Studio research dossier' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Blender Film Studio｜AI → 3D → Cinema',
    description: 'AI 驱动 Blender 电影工作流技术基线研究。',
    images: ['https://lovejzzz.github.io/BlenderFilmStudio/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body>
    </html>
  );
}
