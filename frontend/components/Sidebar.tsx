'use client';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useSettings } from '@/app/providers/SettingsProvider';

const NAV_ITEMS = [
  { href: '/', icon: '🏠', label: 'Dashboard' },
  { href: '/generate', icon: '✨', label: 'Generate Posts' },
  { href: '/video', icon: '🎬', label: 'Video Studio' },
  { href: '/posts', icon: '📚', label: 'Post Library' },
  { href: '/providers', icon: '🔌', label: 'AI Providers' },
  { href: '/settings', icon: '⚙️', label: 'App Settings' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { settings, loading } = useSettings();
  
  // Split app name for aesthetic display: "GigaTech" and "Social Media Agent"
  const words = settings.app_name.split(' ');
  const firstWord = words[0] || 'GigaTech';
  const restWords = words.slice(1).join(' ') || 'Social Agent';

  return (
    <aside style={{
      width: '240px', minHeight: '100vh', background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border)', padding: '24px 16px',
      display: 'flex', flexDirection: 'column', gap: '8px', flexShrink: 0
    }}>
      {/* Logo */}
      <div style={{ padding: '8px 16px 24px', borderBottom: '1px solid var(--border)', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {settings.logo_url ? (
            <img src={settings.logo_url} alt="Logo" style={{ width: '36px', height: '36px', borderRadius: '10px', objectFit: 'contain' }} />
          ) : (
            <div style={{
              width: '36px', height: '36px', borderRadius: '10px',
              background: 'var(--gradient-1)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: '18px'
            }}>🤖</div>
          )}
          <div>
            <div style={{ fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: '14px' }} className="gradient-text">{firstWord}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '140px' }}>{restWords}</div>
          </div>
        </div>
      </div>

      {/* Nav Links */}
      {NAV_ITEMS.map(item => (
        <Link key={item.href} href={item.href}
          className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}>
          <span style={{ fontSize: '18px' }}>{item.icon}</span>
          <span>{item.label}</span>
        </Link>
      ))}

      {/* Footer */}
      <div style={{ marginTop: 'auto', padding: '16px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: '1.6' }}>
          {settings.footer_text && <div>{settings.footer_text}</div>}
          {!settings.footer_text && <div>{settings.company_name}</div>}
        </div>
      </div>
    </aside>
  );
}
