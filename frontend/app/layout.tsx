import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/layout/Sidebar';

export const metadata: Metadata = {
  title: 'CodeReview AI — Intelligent Pull Request Analysis',
  description:
    'AI-powered code review platform powered by Google Gemini. Automated pull request analysis for bugs, security, and performance.',
  keywords: ['code review', 'AI', 'pull request', 'gemini', 'github'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#09090B] text-white antialiased">
        {/*
          Root layout: sidebar sticky on left, content scrolls on right.
          Using plain CSS grid so the sidebar and main column widths are
          explicit and never squeeze each other.
        */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'auto 1fr',
            minHeight: '100vh',
          }}
        >
          <Sidebar />
          {/* Main column — full width, natural block scroll */}
          <main style={{ minWidth: 0, width: '100%' }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
