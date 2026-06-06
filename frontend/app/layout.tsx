import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import { SettingsProvider } from '@/app/providers/SettingsProvider';

export const metadata: Metadata = {
  title: 'GigaTech Social Agent | AI Content Dashboard',
  description: 'Multi-agent AI workflow for automated social media content generation — LinkedIn, Instagram, X, and Reels',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SettingsProvider>
          <div style={{ display: 'flex', minHeight: '100vh' }}>
            <Sidebar />
            <main style={{ flex: 1, padding: '32px', overflow: 'auto' }}>
              {children}
            </main>
          </div>
        </SettingsProvider>
      </body>
    </html>
  );
}
