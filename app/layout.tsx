import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] });
const geistMono = Geist_Mono({ variable: '--font-geist-mono', subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL('https://lovejzzz.github.io/BlenderFilmStudio/'),
  title: 'BlenderFilmStudio｜AI 原生电影软件研究',
  description: '最新方向：以 Blender 官方开源内核构建独立品牌、GPL 合规、可审计的 AI 原生电影制作软件，并用真实 Blender 实验验证。',
  openGraph: {
    title: 'BlenderFilmStudio｜AI Native Film Studio',
    description: '从 AI 操作 Blender，升级为 Blender 内核上的 AI 原生电影软件。设计、证据、许可证与源码可行性研究。',
    type: 'website',
    locale: 'zh_CN',
    url: 'https://lovejzzz.github.io/BlenderFilmStudio/',
    images: [{ url: 'https://lovejzzz.github.io/BlenderFilmStudio/og.png', width: 1672, height: 941, alt: 'Blender Film Studio research dossier' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'BlenderFilmStudio｜AI Native Film Studio',
    description: 'Blender 开源内核上的 AI 原生电影软件研究。',
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
