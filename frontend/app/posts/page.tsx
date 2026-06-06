'use client';
import { useEffect, useState } from 'react';
import PackageCard from '@/components/PackageCard';

const API = 'http://localhost:8000';

export default function PostsPage() {
  const [packages, setPackages] = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);
  const [filter, setFilter]     = useState('all');

  const fetchPackages = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/packages`);
      const data = await res.json();
      setPackages(data.data || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchPackages(); }, []);

  const deletePackage = async (id: number) => {
    if (!confirm('Delete this entire content package?')) return;
    await fetch(`${API}/api/packages/${id}`, { method: 'DELETE' });
    fetchPackages();
  };

  const filtered = packages.filter(pkg => {
    if (filter === 'all') return true;
    if (filter === 'social') return pkg.package_type === 'social';
    if (filter === 'video')  return pkg.package_type === 'video' || pkg.has_video;
    if (filter === 'flyer')  return pkg.package_type === 'flyer';
    return (pkg.platforms || []).includes(filter);
  });

  const FILTERS = [
    { id: 'all', label: '🌐 All' },
    { id: 'social', label: '📱 Social' },
    { id: 'video', label: '🎬 Video' },
    { id: 'flyer', label: '🪧 Flyer' },
    { id: 'linkedin', label: '💼 LinkedIn' },
    { id: 'instagram', label: '📸 Instagram' },
    { id: 'facebook', label: '👥 Facebook' },
    { id: 'twitter', label: '🐦 X' },
    { id: 'youtube', label: '▶️ YouTube' },
    { id: 'tiktok', label: '🎵 TikTok' },
    { id: 'pinterest', label: '📌 Pinterest' },
    { id: 'threads', label: '🧵 Threads' },
  ];

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontFamily: 'Space Grotesk', fontSize: '28px', fontWeight: 700, marginBottom: '8px' }}>
            📚 <span className="gradient-text">Content Library</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '15px' }}>
            {packages.length} complete package{packages.length !== 1 ? 's' : ''} · ready to publish
          </p>
        </div>
        <button onClick={fetchPackages} className="btn-secondary" style={{ fontSize: '13px', padding: '8px 16px' }}>
          🔄 Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '24px' }}>
        {FILTERS.map(f => (
          <button key={f.id} onClick={() => setFilter(f.id)}
            style={{
              padding: '7px 14px', borderRadius: '20px', border: '1px solid',
              borderColor: filter === f.id ? 'var(--accent-primary)' : 'var(--border)',
              background: filter === f.id ? 'rgba(0,212,255,0.12)' : 'transparent',
              color: filter === f.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontWeight: 500, fontSize: '12px', cursor: 'pointer', transition: 'all 0.2s',
            }}>
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'grid', gap: '16px' }}>
          {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: '140px' }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📭</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '16px' }}>
            {packages.length === 0 ? 'No content packages yet. Generate some content!' : 'No packages match this filter.'}
          </p>
          <a href="/generate" style={{ display: 'inline-block', marginTop: '16px' }}>
            <button className="btn-primary">Generate Content</button>
          </a>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {filtered.map(pkg => (
            <PackageCard key={pkg.id} pkg={pkg} onDelete={() => deletePackage(pkg.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
