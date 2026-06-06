'use client';
import { useState } from 'react';
import { downloadFile } from '@/lib/download';

import { API_BASE_URL } from '@/lib/api';

const API = API_BASE_URL;

const PLATFORM_META: Record<string, { color: string; icon: string }> = {
  linkedin:  { color: '#0077B5', icon: '💼' },
  instagram: { color: '#E1306C', icon: '📸' },
  facebook:  { color: '#1877F2', icon: '👥' },
  twitter:   { color: '#1DA1F2', icon: '🐦' },
  youtube:   { color: '#FF0000', icon: '▶️' },
  tiktok:    { color: '#888',    icon: '🎵' },
  pinterest: { color: '#E60023', icon: '📌' },
  threads:   { color: '#888',    icon: '🧵' },
};

interface Props {
  pkg: any;
  onDelete: () => void;
}

export default function PackageCard({ pkg, onDelete }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('');
  const [copied, setCopied] = useState<string | null>(null);

  const data = pkg.data || {};
  const isFlyer = pkg.package_type === 'flyer';
  const isVideo = !isFlyer && (pkg.package_type === 'video' || pkg.has_video);

  // Content map: social packages use data.content; video packages use data.social_posts
  const contentMap: Record<string, any> = data.content || data.social_posts || {};
  const platforms = Object.keys(contentMap);

  // Images: social packages use data.images (flat list); video uses scene_images (dict)
  const images: any[] = data.images
    ? data.images
    : Object.values(data.scene_images || {}).map((v: any, i: number) => ({ ...v, index: i + 1 }));

  const videoFilename = data.video_filename;
  const audioFilename = data.audio_filename;
  const reelScript = data.reel_script;
  const voiceover = data.voiceover_script;

  if (expanded && !activeTab && platforms.length) setActiveTab(platforms[0]);

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text || '');
    setCopied(key);
    setTimeout(() => setCopied(null), 1800);
  };

  const activeContent = activeTab ? contentMap[activeTab] : null;
  const generatedImages = images.filter((i: any) => i.image_url);

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* ── Header (always visible) ── */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', gap: '16px', padding: '18px 20px', cursor: 'pointer', alignItems: 'center' }}>
        {/* Thumbnail */}
        <div style={{
          width: '64px', height: '64px', borderRadius: '12px', flexShrink: 0,
          background: 'var(--bg-secondary)', border: '1px solid var(--border)',
          overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {pkg.thumbnail_url
            ? <img src={pkg.thumbnail_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : <span style={{ fontSize: '28px' }}>{isFlyer ? '🪧' : isVideo ? '🎬' : '📱'}</span>}
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
            <span style={{
              padding: '2px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 700,
              background: isVideo ? 'rgba(167,139,250,0.15)' : 'rgba(0,212,255,0.12)',
              color: isVideo ? '#A78BFA' : 'var(--accent-primary)',
              textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>
              {isFlyer ? '🪧 Flyer' : isVideo ? '🎬 Video Package' : '📱 Social Package'}
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
              {new Date(pkg.created_at + 'Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            📌 {pkg.topic}
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
            {platforms.map(p => (
              <span key={p} title={p} style={{ fontSize: '14px' }}>{PLATFORM_META[p]?.icon || '📣'}</span>
            ))}
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '4px' }}>
              · {generatedImages.length} image{generatedImages.length !== 1 ? 's' : ''}
              {videoFilename && ' · 1 video'}
              {audioFilename && ' · voiceover'}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '8px', flexShrink: 0, alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{expanded ? '▲ Collapse' : '▼ Expand'}</span>
          <button onClick={(e) => { e.stopPropagation(); onDelete(); }}
            style={{
              padding: '8px 12px', borderRadius: '8px', border: '1px solid rgba(255,56,92,0.3)',
              background: 'rgba(255,56,92,0.1)', color: '#FF385C',
              cursor: 'pointer', fontSize: '12px', fontWeight: 500,
            }}>🗑️</button>
        </div>
      </div>

      {/* ── Expanded full package ── */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* ── FLYER ── */}
          {isFlyer && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: '20px', alignItems: 'start' }}>
              <div>
                <SectionLabel>🪧 {data.size_label || 'Flyer'} · {data.dimensions?.width}×{data.dimensions?.height}</SectionLabel>
                {data.preview_url
                  ? <img src={data.preview_url} alt="Flyer" style={{ width: '100%', borderRadius: '10px', border: '1px solid var(--border)' }} />
                  : <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Preview unavailable.</div>}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <SectionLabel>⬇️ Download</SectionLabel>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {Object.entries(data.files || {}).map(([fmt, url]: [string, any]) => (
                      <button key={fmt} onClick={() => downloadFile(url, `flyer.${fmt}`)}
                        style={{ padding: '8px', borderRadius: '8px', border: 'none', background: 'rgba(0,212,255,0.9)', color: '#000', fontWeight: 700, fontSize: '12px', cursor: 'pointer' }}>
                        ⬇ {fmt.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                {data.copy?.headline && <MetaField label="Headline" value={data.copy.headline} />}
                {data.copy?.call_to_action && <MetaField label="CTA" value={data.copy.call_to_action} />}
                {data.has_qr && <div style={{ fontSize: '11px', color: 'var(--accent-green)' }}>✓ QR → {data.display_url}</div>}
              </div>
            </div>
          )}

          {/* Website context */}
          {data.website_context?.summary && (
            <div style={{ background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.2)', borderRadius: '10px', padding: '12px 14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase', marginBottom: '6px' }}>
                🌐 {data.website_context.brand_name || 'Website Analysis'}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{data.website_context.summary}</div>
            </div>
          )}

          {/* ── VIDEO + AUDIO ── */}
          {(videoFilename || audioFilename) && (
            <div>
              <SectionLabel>🎬 Video & Audio Assets</SectionLabel>
              <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                {videoFilename && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <video controls src={`${API}/api/video-file/${videoFilename}`}
                      style={{ width: '220px', borderRadius: '12px', border: '1px solid var(--border)', background: '#000', aspectRatio: '9/16', objectFit: 'contain' }} />
                    <a href={`${API}/api/video-file/${videoFilename}?download=true`} download>
                      <button className="btn-primary" style={{ fontSize: '12px', padding: '8px 14px', width: '100%' }}>⬇️ Download MP4</button>
                    </a>
                  </div>
                )}
                <div style={{ flex: 1, minWidth: '220px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {audioFilename && (
                    <div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>🎵 Voiceover Audio</div>
                      <audio controls src={`${API}/api/video-file/${audioFilename}`} style={{ width: '100%' }} />
                      <a href={`${API}/api/video-file/${audioFilename}?download=true`} download>
                        <button className="btn-secondary" style={{ fontSize: '12px', padding: '6px 12px', marginTop: '6px' }}>⬇️ Download Audio</button>
                      </a>
                    </div>
                  )}
                  {/* Video metadata */}
                  {reelScript?.hook_line && <MetaField label="🎣 Hook" value={reelScript.hook_line} />}
                  {reelScript?.call_to_action && <MetaField label="📣 CTA" value={reelScript.call_to_action} />}
                  {reelScript?.total_duration_sec && <MetaField label="⏱ Duration" value={`${reelScript.total_duration_sec}s`} />}
                </div>
              </div>
            </div>
          )}

          {/* ── REEL SCRIPT ── */}
          {reelScript?.scenes?.length > 0 && (
            <details>
              <summary style={summaryStyle}>📝 Video Script ({reelScript.scenes.length} scenes)</summary>
              <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {reelScript.scenes.map((s: any, i: number) => (
                  <div key={i} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: '#A78BFA', marginBottom: '4px' }}>
                      Scene {s.scene_number} · {s.duration_sec}s
                    </div>
                    {s.dialogue && <div style={{ fontSize: '13px', color: 'var(--text-primary)', fontStyle: 'italic', marginBottom: '3px' }}>&quot;{s.dialogue}&quot;</div>}
                    {s.visual_direction && <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>📷 {s.visual_direction}</div>}
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* ── VOICEOVER SCRIPT ── */}
          {voiceover?.voiceover_text && (
            <details>
              <summary style={summaryStyle}>🎙️ Voiceover Script</summary>
              <div style={{ marginTop: '12px', position: 'relative' }}>
                <button onClick={() => copy(voiceover.voiceover_text, 'vo')} className="btn-secondary"
                  style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '11px', padding: '5px 10px', zIndex: 1 }}>
                  {copied === 'vo' ? '✓' : '📋 Copy'}
                </button>
                <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '10px', padding: '16px', fontSize: '14px', lineHeight: 1.8, whiteSpace: 'pre-wrap', border: '1px solid var(--border)' }}>
                  {voiceover.voiceover_text}
                </div>
              </div>
            </details>
          )}

          {/* ── PLATFORM CONTENT TABS ── */}
          {platforms.length > 0 && (
            <div>
              <SectionLabel>📱 Platform Content</SectionLabel>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
                {platforms.map(p => {
                  const meta = PLATFORM_META[p] || { color: 'var(--accent-primary)', icon: '📣' };
                  return (
                    <button key={p} onClick={() => setActiveTab(p)} style={{
                      padding: '7px 14px', borderRadius: '9px', border: '1px solid',
                      borderColor: activeTab === p ? meta.color : 'var(--border)',
                      background: activeTab === p ? `${meta.color}22` : 'transparent',
                      color: activeTab === p ? meta.color : 'var(--text-secondary)',
                      fontWeight: 600, fontSize: '12px', cursor: 'pointer',
                    }}>
                      {meta.icon} {p.charAt(0).toUpperCase() + p.slice(1)}
                    </button>
                  );
                })}
              </div>

              {activeContent && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ position: 'relative' }}>
                    <button onClick={() => copy(activeContent.content, activeTab)} className="btn-secondary"
                      style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '11px', padding: '5px 10px', zIndex: 1 }}>
                      {copied === activeTab ? '✓ Copied' : '📋 Copy'}
                    </button>
                    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '10px', padding: '16px', paddingRight: '70px', fontSize: '14px', lineHeight: 1.8, whiteSpace: 'pre-wrap', border: '1px solid var(--border)', maxHeight: '280px', overflow: 'auto' }}>
                      {activeContent.content}
                    </div>
                  </div>

                  {/* YouTube extras */}
                  {activeContent.video_title && <MetaField label="🎬 Video Title" value={activeContent.video_title} />}
                  {activeContent.video_description && <MetaField label="📄 Description" value={activeContent.video_description} />}
                  {activeContent.video_tags?.length > 0 && (
                    <TagRow label="🏷️ Tags" tags={activeContent.video_tags} bg="rgba(255,0,0,0.08)" color="#FF5555" />
                  )}
                  {activeContent.content_ideas?.length > 0 && (
                    <div>
                      <div style={metaLabelStyle}>💡 Content Ideas</div>
                      {activeContent.content_ideas.map((idea: string, i: number) => (
                        <div key={i} style={{ fontSize: '13px', color: 'var(--text-secondary)', padding: '6px 0' }}>💡 {idea}</div>
                      ))}
                    </div>
                  )}

                  {/* Hashtags */}
                  {activeContent.hashtags?.length > 0 && (
                    <TagRow label={`# Hashtags (${activeContent.hashtags.length})`} tags={activeContent.hashtags}
                      bg="rgba(0,212,255,0.08)" color="var(--accent-primary)" hash />
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── IMAGE GALLERY ── */}
          {generatedImages.length > 0 && (
            <div>
              <SectionLabel>🎨 Generated Images ({generatedImages.length})</SectionLabel>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '10px' }}>
                {generatedImages.map((img: any, i: number) => (
                  <div key={i} style={{ position: 'relative', borderRadius: '10px', overflow: 'hidden', border: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
                    <img src={img.image_url} alt="" loading="lazy"
                      style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', display: 'block' }} />
                    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'linear-gradient(transparent, rgba(0,0,0,0.8))', padding: '16px 8px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                      <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.85)', fontWeight: 700 }}>{img.ratio || ''}</span>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button onClick={() => downloadFile(img.image_url, `image-${i + 1}.png`)} title="Download" style={imgBtnStyle('rgba(0,212,255,0.9)', '#000')}>⬇</button>
                        <a href={img.image_url} target="_blank" rel="noreferrer"><button style={imgBtnStyle('rgba(255,255,255,0.2)', '#fff')}>↗</button></a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>{children}</div>;
}

function MetaField({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 12px' }}>
      <div style={metaLabelStyle}>{label}</div>
      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: '160px', overflow: 'auto' }}>{value}</div>
    </div>
  );
}

function TagRow({ label, tags, bg, color, hash }: { label: string; tags: string[]; bg: string; color: string; hash?: boolean }) {
  return (
    <div>
      <div style={metaLabelStyle}>{label}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {tags.map((t, i) => (
          <span key={i} style={{ background: bg, color, padding: '4px 11px', borderRadius: '12px', fontSize: '12px', border: `1px solid ${color}33` }}>
            {hash ? (t.startsWith('#') ? t : `#${t}`) : t}
          </span>
        ))}
      </div>
    </div>
  );
}

const metaLabelStyle: React.CSSProperties = {
  fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)',
  textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '7px',
};

const summaryStyle: React.CSSProperties = {
  fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', cursor: 'pointer', userSelect: 'none',
};

function imgBtnStyle(bg: string, color: string): React.CSSProperties {
  return { padding: '3px 7px', borderRadius: '5px', border: 'none', background: bg, color, fontSize: '11px', fontWeight: 700, cursor: 'pointer' };
}
