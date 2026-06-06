'use client';
import { useState } from 'react';
import { downloadFile } from '@/lib/download';

const PLATFORM_META: Record<string, { color: string; icon: string }> = {
  linkedin:  { color: '#0077B5', icon: '💼' },
  instagram: { color: '#E1306C', icon: '📸' },
  facebook:  { color: '#1877F2', icon: '👥' },
  twitter:   { color: '#1DA1F2', icon: '🐦' },
  youtube:   { color: '#FF0000', icon: '▶️' },
  tiktok:    { color: '#010101', icon: '🎵' },
  pinterest: { color: '#E60023', icon: '📌' },
  threads:   { color: '#101010', icon: '🧵' },
};

interface ResultsPanelProps {
  results: any;
  generating: boolean;
  error: string | null;
}

export default function ResultsPanel({ results, generating, error }: ResultsPanelProps) {
  const [activeTab, setActiveTab] = useState<string>('');
  const [copied, setCopied]       = useState(false);
  const [imgTab, setImgTab]       = useState<string>('');

  if (results && !activeTab) {
    const platforms = Object.keys(results.content || {});
    if (platforms.length) setActiveTab(platforms[0]);
  }

  // Group images by ratio
  const images: any[] = results?.images || [];
  const ratios = Array.from(new Set(images.map((img: any) => img.ratio || '1:1')));
  if (images.length && !imgTab && ratios.length) setImgTab(ratios[0]);

  if (generating) return <GeneratingState />;
  if (error) return <ErrorState error={error} />;
  if (!results) return null;

  const platforms   = Object.keys(results.content || {});
  const activeContent = results.content?.[activeTab] || null;

  const copyContent = () => {
    if (!activeContent) return;
    navigator.clipboard.writeText(activeContent.content || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredImages = imgTab
    ? images.filter((img: any) => (img.ratio || '1:1') === imgTab)
    : images;

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Success Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(0,229,160,0.1), rgba(0,212,255,0.1))',
        border: '1px solid rgba(0,229,160,0.3)', borderRadius: '12px', padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <span style={{ fontSize: '24px' }}>✅</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: '16px', color: 'var(--accent-green)' }}>Pipeline Complete!</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            {platforms.length} platform{platforms.length !== 1 ? 's' : ''} · {images.length} image{images.length !== 1 ? 's' : ''}
            {results.website_context?.brand_name && ` · Brand: ${results.website_context.brand_name}`}
          </div>
        </div>
      </div>

      {/* Website Context Summary */}
      {results.website_context?.summary && (
        <div style={{
          background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.2)',
          borderRadius: '12px', padding: '14px 16px',
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase', marginBottom: '8px' }}>
            🌐 Website Analysis — {results.website_context.brand_name}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
            {results.website_context.summary}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' }}>
            {[
              results.website_context.industry && `📊 ${results.website_context.industry}`,
              results.website_context.tone_of_voice && `🎨 ${results.website_context.tone_of_voice}`,
              results.website_context.target_audience && `👥 ${results.website_context.target_audience}`,
            ].filter(Boolean).map((tag, i) => (
              <span key={i} style={{
                padding: '3px 10px', borderRadius: '10px', fontSize: '11px',
                background: 'rgba(0,212,255,0.1)', color: 'var(--accent-primary)',
                border: '1px solid rgba(0,212,255,0.2)',
              }}>{tag}</span>
            ))}
          </div>
        </div>
      )}

      {/* Platform Tabs */}
      {platforms.length > 0 && (
        <>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {platforms.map(p => {
              const meta = PLATFORM_META[p] || { color: 'var(--accent-primary)', icon: '📣' };
              return (
                <button key={p} onClick={() => setActiveTab(p)} style={{
                  padding: '8px 16px', borderRadius: '10px', border: '1px solid',
                  borderColor: activeTab === p ? meta.color : 'var(--border)',
                  background: activeTab === p ? `${meta.color}20` : 'transparent',
                  color: activeTab === p ? meta.color : 'var(--text-secondary)',
                  fontWeight: 600, fontSize: '13px', cursor: 'pointer', transition: 'all 0.2s',
                }}>
                  {meta.icon} {p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              );
            })}
          </div>

          {/* Active Platform Content */}
          {activeContent && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 700 }}>
                  {PLATFORM_META[activeTab]?.icon || '📣'} {activeTab.charAt(0).toUpperCase()}{activeTab.slice(1)} Post
                </h3>
                <button onClick={copyContent} className="btn-secondary" style={{ fontSize: '13px', padding: '8px 16px' }}>
                  {copied ? '✓ Copied!' : '📋 Copy'}
                </button>
              </div>

              <div style={{
                background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '20px',
                whiteSpace: 'pre-wrap', fontSize: '14px', lineHeight: '1.8',
                color: 'var(--text-primary)', border: '1px solid var(--border)', maxHeight: '320px', overflow: 'auto',
              }}>
                {activeContent.content}
              </div>

              {/* Extra fields: YouTube title/description/tags, TikTok content ideas */}
              {activeContent.video_title && (
                <ExtraField label="🎬 Video Title" value={activeContent.video_title} />
              )}
              {activeContent.video_description && (
                <ExtraField label="📄 Video Description" value={activeContent.video_description} multiline />
              )}
              {activeContent.video_tags?.length > 0 && (
                <div>
                  <div style={metaLabel}>🏷️ Video Tags</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {activeContent.video_tags.map((t: string, i: number) => (
                      <span key={i} style={tagStyle('rgba(255,0,0,0.1)', '#FF4444')}>{t}</span>
                    ))}
                  </div>
                </div>
              )}
              {activeContent.content_ideas?.length > 0 && (
                <div>
                  <div style={metaLabel}>💡 Content Ideas</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {activeContent.content_ideas.map((idea: string, i: number) => (
                      <div key={i} style={{
                        padding: '10px 14px', borderRadius: '8px',
                        background: 'rgba(255,0,128,0.06)', border: '1px solid rgba(255,0,128,0.15)',
                        fontSize: '13px', color: 'var(--text-secondary)',
                      }}>💡 {idea}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hook / CTA */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                {activeContent.hook && (
                  <div style={infoBox('rgba(255,184,0,0.08)', 'rgba(255,184,0,0.2)')}>
                    <div style={{ ...metaLabel, color: 'var(--accent-gold)' }}>🎣 Hook</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>{activeContent.hook}</div>
                  </div>
                )}
                {activeContent.cta && (
                  <div style={infoBox('rgba(0,229,160,0.08)', 'rgba(0,229,160,0.2)')}>
                    <div style={{ ...metaLabel, color: 'var(--accent-green)' }}>📣 CTA</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{activeContent.cta}</div>
                  </div>
                )}
              </div>

              {/* Hashtags */}
              {activeContent.hashtags?.length > 0 && (
                <div>
                  <div style={metaLabel}>#{activeContent.hashtags.length} Hashtags</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {activeContent.hashtags.map((tag: string, i: number) => (
                      <span key={i} style={tagStyle('rgba(0,212,255,0.08)', 'var(--accent-primary)')}>
                        {tag.startsWith('#') ? tag : `#${tag}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Images Gallery */}
      {images.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 700 }}>
              🎨 Generated Images ({images.length})
            </h3>
            {ratios.length > 1 && (
              <div style={{ display: 'flex', gap: '6px' }}>
                {ratios.map(r => (
                  <button key={r} onClick={() => setImgTab(r)} style={{
                    padding: '5px 12px', borderRadius: '8px', border: '1px solid',
                    borderColor: imgTab === r ? 'var(--accent-primary)' : 'var(--border)',
                    background: imgTab === r ? 'rgba(0,212,255,0.12)' : 'transparent',
                    color: imgTab === r ? 'var(--accent-primary)' : 'var(--text-muted)',
                    fontSize: '12px', cursor: 'pointer', fontWeight: imgTab === r ? 700 : 400,
                  }}>{r}</button>
                ))}
              </div>
            )}
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '12px',
          }}>
            {filteredImages.map((img: any, i: number) => (
              <ImageCard key={i} img={img} />
            ))}
          </div>
        </div>
      )}

      {/* Research context */}
      {results.research?.summary && (
        <details className="card" style={{ cursor: 'pointer' }}>
          <summary style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-muted)', userSelect: 'none' }}>
            🔍 Research Context Used
          </summary>
          <div style={{ marginTop: '12px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>
            {results.research.summary}
          </div>
        </details>
      )}
    </div>
  );
}

function ImageCard({ img }: { img: any }) {
  if (!img.image_url) {
    return (
      <div style={{
        aspectRatio: '1', borderRadius: '10px', background: 'var(--bg-secondary)',
        border: '1px dashed var(--border)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', flexDirection: 'column', gap: '6px',
      }}>
        <span style={{ fontSize: '24px', opacity: 0.4 }}>🖼️</span>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', padding: '0 8px' }}>
          {img.error || 'Generation failed'}
        </span>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', borderRadius: '10px', overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
      <img
        src={img.image_url} alt={`Image ${img.index || ''}`}
        style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', display: 'block' }}
        loading="lazy"
      />
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: 'linear-gradient(transparent, rgba(0,0,0,0.85))',
        padding: '20px 10px 10px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
      }}>
        <span style={{
          fontSize: '10px', fontWeight: 700, color: 'rgba(255,255,255,0.8)',
          background: 'rgba(0,0,0,0.4)', padding: '2px 6px', borderRadius: '4px',
        }}>
          {img.ratio || '1:1'} · {img.dimensions || ''}
        </span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={() => downloadFile(img.image_url, `image-${img.index || ''}.png`)}
            title="Download image"
            style={{
              padding: '4px 8px', borderRadius: '6px', border: 'none',
              background: 'rgba(0,212,255,0.9)', color: '#000',
              fontSize: '11px', fontWeight: 700, cursor: 'pointer',
            }}>⬇</button>
          <a href={img.image_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
            <button style={{
              padding: '4px 8px', borderRadius: '6px', border: 'none',
              background: 'rgba(255,255,255,0.2)', color: '#fff',
              fontSize: '11px', cursor: 'pointer',
            }}>↗</button>
          </a>
        </div>
      </div>
    </div>
  );
}

function ExtraField({ label, value, multiline }: { label: string; value: string; multiline?: boolean }) {
  return (
    <div>
      <div style={metaLabel}>{label}</div>
      <div style={{
        background: 'rgba(0,0,0,0.25)', borderRadius: '8px', padding: '12px 14px',
        fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7',
        whiteSpace: multiline ? 'pre-wrap' : 'normal',
        maxHeight: multiline ? '200px' : 'auto', overflow: multiline ? 'auto' : 'visible',
        border: '1px solid var(--border)',
      }}>
        {value}
      </div>
    </div>
  );
}

function GeneratingState() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px', gap: '24px' }}>
      <div style={{ position: 'relative', width: '80px', height: '80px' }}>
        <div className="animate-spin-slow" style={{
          width: '80px', height: '80px', borderRadius: '50%',
          border: '3px solid var(--border)', borderTopColor: 'var(--accent-primary)',
        }} />
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '28px' }}>🤖</div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontFamily: 'Space Grotesk', fontSize: '20px', fontWeight: 700, marginBottom: '8px' }} className="gradient-text">
          Agents Working...
        </div>
        <div style={{ display: 'grid', gap: '8px', textAlign: 'left' }}>
          {[
            '🌐 Web Research Agent crawling URLs...',
            '🔍 Research Agent fetching news...',
            '✍️ Content Agent generating posts...',
            '#️⃣ Hashtag Agent optimizing...',
            '🎨 Image Agent generating 5+ images...',
            '💾 Database Agent saving...',
          ].map((step, i) => (
            <div key={i} style={{ color: 'var(--text-muted)', fontSize: '13px', display: 'flex', gap: '8px' }}>
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ErrorState({ error }: { error: string }) {
  return (
    <div className="card" style={{ borderColor: 'rgba(255,56,92,0.3)' }}>
      <div style={{ color: '#FF385C', fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>⚠️ Error</div>
      <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>{error}</p>
    </div>
  );
}

const metaLabel: React.CSSProperties = {
  fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
  textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px',
};

function infoBox(bg: string, borderColor: string): React.CSSProperties {
  return { background: bg, border: `1px solid ${borderColor}`, borderRadius: '10px', padding: '14px' };
}

function tagStyle(bg: string, color: string): React.CSSProperties {
  return {
    background: bg, color, padding: '4px 12px', borderRadius: '12px',
    fontSize: '12px', border: `1px solid ${color}33`,
  };
}
