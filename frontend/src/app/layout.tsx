import type { Metadata } from 'next';
import './globals.css';
import { QueryProvider } from '@/components/providers/query-provider';
import { Navbar } from '@/components/layout/navbar';

export const metadata: Metadata = {
  title: 'AI PDF Chatter — Context-Aware Reading Companion',
  description: 'AI-native PDF reading workspace with multi-layered context & RAG intelligence.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased">
        <QueryProvider>
          <Navbar />
          <main className="flex-1 flex flex-col">{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}
