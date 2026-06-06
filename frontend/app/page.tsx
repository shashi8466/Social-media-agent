'use client';
import { useEffect, useState } from 'react';
import StatCard from '@/components/StatCard';
import RecentPosts from '@/components/RecentPosts';
import { useSettings } from '@/app/providers/SettingsProvider';
import { API_BASE_URL } from '@/lib/api';

const API = API_BASE_URL;

export default function Dashboard() {
  const { settings } = useSettings();
  const [stats, setStats] = useState<any>(null);
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Split app name for display
  const words = settings.app_name.split(' ');
  const firstWord = words[0] || 'GigaTech';
  const restWords = words.slice(1).join(' ') || 'Social Agent';

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/stats`).then(r => r.json()),
      fetch(`${API}/api/posts?limit=5`).then(r => r.json()),
    ]).then(([s, p]) => {
      setStats(s.data);
      setPosts(p.data || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          {settings.logo_url ? (
            <img src={settings.logo_url} alt="Logo" style={{ width: '48px', height: '48px', borderRadius: '12px', objectFit: 'contain' }} />
          ) : (
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              background: 'var(--gradient-1)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: '24px'
            }}>🤖</div>
          )}
          <div>
            <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700 }}>
              <span className="gradient-text">{firstWord}</span> {restWords}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Multi-agent AI content workflow</p>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <StatCard
          label="Total Posts"
          value={loading ? '—' : stats?.total ?? 0}
          icon="📊" gradient="var(--gradient-1)"
          description="All generated posts"
        />
        <StatCard label="LinkedIn"  value={loading ? '—' : stats?.by_platform?.linkedin  ?? 0} icon="💼" gradient="linear-gradient(135deg, #0077B5, #00A0DC)" description="LinkedIn posts" />
        <StatCard label="Instagram" value={loading ? '—' : stats?.by_platform?.instagram ?? 0} icon="📸" gradient="linear-gradient(135deg, #E1306C, #FFDC80)" description="Instagram captions" />
        <StatCard label="Facebook"  value={loading ? '—' : stats?.by_platform?.facebook  ?? 0} icon="👥" gradient="linear-gradient(135deg, #1877F2, #42A5F5)" description="Facebook posts" />
        <StatCard label="X / Twitter" value={loading ? '—' : stats?.by_platform?.twitter ?? 0} icon="🐦" gradient="linear-gradient(135deg, #1DA1F2, #0D8ECF)" description="X threads" />
        <StatCard label="YouTube"   value={loading ? '—' : stats?.by_platform?.youtube   ?? 0} icon="▶️" gradient="linear-gradient(135deg, #FF0000, #FF6B6B)" description="YouTube posts" />
        <StatCard label="TikTok"    value={loading ? '—' : stats?.by_platform?.tiktok    ?? 0} icon="🎵" gradient="linear-gradient(135deg, #010101, #444)" description="TikTok captions" />
        <StatCard label="Pinterest" value={loading ? '—' : stats?.by_platform?.pinterest ?? 0} icon="📌" gradient="linear-gradient(135deg, #E60023, #ff6b6b)" description="Pinterest pins" />
        <StatCard label="Threads"   value={loading ? '—' : stats?.by_platform?.threads   ?? 0} icon="🧵" gradient="linear-gradient(135deg, #101010, #333)" description="Threads posts" />
      </div>

      {/* Agent Pipeline Visual */}
      <div className="card" style={{ marginBottom: '32px' }}>
        <h2 style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 600, marginBottom: '20px' }}>
          🔄 Agent Pipeline
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { icon: '🌐', name: 'Web Research', desc: 'URL Crawling' },
            { icon: '🔍', name: 'Research Agent', desc: 'News & Context' },
            { icon: '✍️', name: 'Content Agent', desc: 'GPT-4o · 8 Platforms' },
            { icon: '#️⃣', name: 'Hashtag Agent', desc: 'Optimization' },
            { icon: '🎨', name: 'Image Agent', desc: 'Segmind · 5+ Images' },
            { icon: '💾', name: 'Database Agent', desc: 'SQLite' },
          ].map((agent, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                borderRadius: '12px', padding: '12px 16px', textAlign: 'center', minWidth: '110px'
              }}>
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>{agent.icon}</div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{agent.name}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{agent.desc}</div>
              </div>
              {i < 5 && <div style={{ color: 'var(--accent-primary)', fontSize: '20px' }}>→</div>}
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <h2 style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 600, marginBottom: '20px' }}>
          🕐 Recent Posts
        </h2>
        <RecentPosts posts={posts} loading={loading} />
      </div>
    </div>
  );
}
