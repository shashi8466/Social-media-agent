const PLATFORM_BADGES: Record<string, { emoji: string; class: string }> = {
  linkedin: { emoji: '💼', class: 'badge-linkedin' },
  instagram: { emoji: '📸', class: 'badge-instagram' },
  twitter: { emoji: '🐦', class: 'badge-twitter' },
  reels: { emoji: '🎬', class: 'badge-reels' },
};

export default function RecentPosts({ posts, loading }: { posts: any[]; loading: boolean }) {
  if (loading) {
    return <div style={{ display: 'grid', gap: '12px' }}>
      {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: '60px' }} />)}
    </div>;
  }

  if (!posts.length) {
    return (
      <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>📭</div>
        <p>No posts yet. <a href="/generate" style={{ color: 'var(--accent-primary)' }}>Generate your first content!</a></p>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: '12px' }}>
      {posts.map((post) => (
        <div key={post.id} style={{
          display: 'flex', alignItems: 'center', gap: '16px', padding: '14px 16px',
          background: 'var(--bg-secondary)', borderRadius: '12px',
          border: '1px solid var(--border)', transition: 'all 0.2s'
        }}>
          <span className={`platform-badge ${PLATFORM_BADGES[post.platform]?.class}`} style={{ flexShrink: 0 }}>
            {PLATFORM_BADGES[post.platform]?.emoji} {post.platform}
          </span>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <div style={{ fontWeight: 600, fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {post.topic}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
              {new Date(post.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
          {post.image_url && <span style={{ fontSize: '16px' }} title="Has image">🖼️</span>}
        </div>
      ))}
      <a href="/posts" style={{ textAlign: 'center', color: 'var(--accent-primary)', fontSize: '13px', display: 'block', marginTop: '4px' }}>
        View all posts →
      </a>
    </div>
  );
}
