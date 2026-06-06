'use client';
import { useState } from 'react';

const API = 'http://localhost:8000';

type Tab = 'video' | 'script' | 'voiceover' | 'social' | 'hashtags' | 'research';

const SOCIAL_COLORS: Record<string, string> = {
  linkedin: '#0077B5', instagram: '#E1306C', twitter: '#1DA1F2',
};
const SOCIAL_ICONS: Record<string, string> = {
  linkedin: '💼', instagram: '📸', twitter: '🐦',
};

interface Props {
  results: any;
  generating: boolean;
  error: string | null;
}

export default function VideoResultsPanel({ results, generating, error }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('video');
  const [activeSocial, setActiveSocial] = useState('linkedin');
  const [copied, setCopied] = useState<string | null>(null);

  const copyText = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  if (generating) return null;
  if (error) {
    return (
      <div className="card" style={{ borderColor: 'rgba(255, 56, 92, 0.3)' }}>
        <div style={{ color: '#FF385C', fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>⚠️ Pipeline Error</div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.7 }}>{error}</p>
      </div>
    );
  }
  if (!results) return null;

  const { reel_script, voiceover_script, social_posts, hashtags, research, video_filename, audio_filename, db_project_id, pipeline_steps, video_editor_error, thumbnail_url, website_context, durations, duration_synced } = results;

  // Extract video editor error from pipeline_steps if not on the top-level key
  const videoEditorStep = (pipeline_steps || []).find((s: any) => s.step === 'video_editor');
  const videoError: string | null =
    video_editor_error ||
    (videoEditorStep?.status === 'failed' ? videoEditorStep.error : null) ||
    null;
  const scenes = reel_script?.scenes || [];
  const socialPlatforms = Object.keys(social_posts || {});

  const TABS: { key: Tab; icon: string; label: string }[] = [
    { key: 'video',      icon: '🎬', label: 'Final Video' },
    { key: 'script',     icon: '📝', label: 'Reel Script' },
    { key: 'voiceover',  icon: '🎙️', label: 'Voiceover' },
    { key: 'social',     icon: '📱', label: 'Social Posts' },
    { key: 'hashtags',   icon: '#️⃣', label: 'Hashtags' },
    { key: 'research',   icon: '🔍', label: 'Research' },
  ];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Success Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(123,94,167,0.12), rgba(167,139,250,0.08))',
        border: '1px solid rgba(167, 139, 250, 0.3)', borderRadius: '14px',
        padding: '18px 22px', display: 'flex', alignItems: 'center', gap: '14px'
      }}>
        <span style={{ fontSize: '28px' }}>🎉</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: '16px', color: '#A78BFA' }}>
            Video Pipeline Complete!
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '3px' }}>
            {scenes.length} scenes
            {durations?.final_video_sec ? ` · ${durations.final_video_sec}s reel` : ` · ${reel_script?.total_duration_sec || 45}s reel`}
            {video_filename ? ' · MP4 ready ✅' : videoError ? ' · Video render failed ❌' : ''}
            {db_project_id ? ` · Project #${db_project_id}` : ''}
          </div>
          {durations && (
            <div style={{ marginTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {[
                durations.voiceover_sec != null && `🎙️ Voiceover ${durations.voiceover_sec}s`,
                durations.final_video_sec != null && `🎬 Video ${durations.final_video_sec}s`,
                duration_synced != null && (duration_synced ? '✅ In sync' : '⚠️ Duration mismatch'),
              ].filter(Boolean).map((t: any, i: number) => (
                <span key={i} style={{
                  padding: '3px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: 600,
                  background: duration_synced === false && String(t).includes('mismatch') ? 'rgba(255,184,0,0.12)' : 'rgba(167,139,250,0.12)',
                  color: duration_synced === false && String(t).includes('mismatch') ? 'var(--accent-gold)' : '#A78BFA',
                  border: '1px solid rgba(167,139,250,0.25)',
                }}>{t}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Website Context */}
      {website_context?.summary && (
        <div style={{
          background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.2)',
          borderRadius: '12px', padding: '14px 16px',
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase', marginBottom: '6px' }}>
            🌐 Website Analysis — {website_context.brand_name}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{website_context.summary}</div>
        </div>
      )}

      {/* Tab Bar */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {TABS.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            id={`tab-${tab.key}`}
            style={{
              padding: '10px 16px', borderRadius: '10px', border: '1px solid',
              borderColor: activeTab === tab.key ? '#A78BFA' : 'var(--border)',
              background: activeTab === tab.key ? 'rgba(167, 139, 250, 0.12)' : 'transparent',
              color: activeTab === tab.key ? '#A78BFA' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '13px', cursor: 'pointer', transition: 'all 0.2s',
              display: 'flex', alignItems: 'center', gap: '6px',
            }}>
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* ── VIDEO TAB ── */}
      {activeTab === 'video' && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <h3 style={{ fontFamily: 'Space Grotesk', fontSize: '18px', fontWeight: 700 }}>
            🎬 Final MP4 Reel
          </h3>

          {videoError && !video_filename && (
            <div style={{
              background: 'rgba(255, 56, 92, 0.08)', border: '1px solid rgba(255,56,92,0.3)',
              borderRadius: '12px', padding: '16px 20px', marginBottom: '4px',
            }}>
              <div style={{ color: '#FF385C', fontWeight: 700, fontSize: '14px', marginBottom: '6px' }}>
                ❌ Video Editor Error
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.7, fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {videoError}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '10px' }}>
                Tip: ensure FFmpeg is installed and on PATH, or run <code>pip install imageio-ffmpeg</code> in the backend environment.
              </div>
            </div>
          )}

          {video_filename ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <video
                controls
                style={{
                  width: '100%', maxWidth: '400px', borderRadius: '16px',
                  border: '1px solid var(--border)', background: '#000',
                  aspectRatio: '9/16', objectFit: 'contain',
                }}
                src={`${API}/api/video-file/${video_filename}`}
              />
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <a href={`${API}/api/video-file/${video_filename}?download=true`} download>
                  <button className="btn-primary" style={{ fontSize: '14px', padding: '10px 20px' }}>
                    ⬇️ Download MP4
                  </button>
                </a>
                {audio_filename && (
                  <a href={`${API}/api/video-file/${audio_filename}?download=true`} download>
                    <button className="btn-secondary" style={{ fontSize: '14px', padding: '10px 20px' }}>
                      🎵 Download Audio
                    </button>
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div style={{
              border: '2px dashed rgba(167, 139, 250, 0.3)', borderRadius: '16px',
              padding: '48px 24px', textAlign: 'center', color: 'var(--text-muted)'
            }}>
              <div style={{ fontSize: '48px', marginBottom: '12px' }}>🎬</div>
              <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '6px' }}>Video Not Available</div>
              <div style={{ fontSize: '13px' }}>
                moviepy may not be installed, or video assembly encountered an error.
                Check the Reel Script and Voiceover tabs — all content was generated.
              </div>
            </div>
          )}

          {/* Audio Player */}
          {audio_filename && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
                🎵 Voiceover Audio
              </div>
              <audio controls style={{ width: '100%', borderRadius: '8px' }}
                src={`${API}/api/video-file/${audio_filename}`} />
            </div>
          )}
        </div>
      )}

      {/* ── SCRIPT TAB ── */}
      {activeTab === 'script' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Meta */}
          <div className="card" style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
            {reel_script?.hook_line && (
              <div style={{ flex: 1, minWidth: '200px', background: 'rgba(255, 184, 0, 0.08)', borderRadius: '10px', padding: '14px', border: '1px solid rgba(255,184,0,0.2)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-gold)', textTransform: 'uppercase', marginBottom: '6px' }}>🎣 Hook</div>
                <div style={{ fontSize: '14px', fontStyle: 'italic', color: 'var(--text-primary)' }}>&quot;{reel_script.hook_line}&quot;</div>
              </div>
            )}
            {reel_script?.call_to_action && (
              <div style={{ flex: 1, minWidth: '200px', background: 'rgba(0,229,160,0.08)', borderRadius: '10px', padding: '14px', border: '1px solid rgba(0,229,160,0.2)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-green)', textTransform: 'uppercase', marginBottom: '6px' }}>📣 CTA</div>
                <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{reel_script.call_to_action}</div>
              </div>
            )}
          </div>

          {/* Scene cards */}
          {scenes.map((scene: any, i: number) => (
            <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '10px', flexShrink: 0,
                    background: 'linear-gradient(135deg, #7B5EA7, #A78BFA)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: '16px',
                  }}>
                    {scene.scene_number}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '14px' }}>Scene {scene.scene_number}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{scene.visual_style || 'cinematic'}</div>
                  </div>
                </div>
                <div style={{
                  padding: '4px 12px', borderRadius: '20px',
                  background: 'rgba(0, 212, 255, 0.1)', border: '1px solid rgba(0,212,255,0.2)',
                  fontSize: '12px', fontWeight: 600, color: 'var(--accent-primary)'
                }}>
                  ⏱ {scene.duration_sec}s
                </div>
              </div>

              <div style={{ display: 'grid', gap: '10px' }}>
                {scene.visual_direction && (
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#A78BFA', textTransform: 'uppercase', marginBottom: '6px' }}>📷 Visual</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{scene.visual_direction}</div>
                  </div>
                )}
                {scene.dialogue && (
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent-green)', textTransform: 'uppercase', marginBottom: '6px' }}>🗣️ Dialogue</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.6, fontStyle: 'italic' }}>&quot;{scene.dialogue}&quot;</div>
                  </div>
                )}
                {scene.on_screen_text && (
                  <div style={{ background: 'rgba(255,184,0,0.06)', borderRadius: '8px', padding: '12px', border: '1px solid rgba(255,184,0,0.15)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent-gold)', textTransform: 'uppercase', marginBottom: '4px' }}>📺 On-Screen</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#fff', letterSpacing: '0.5px' }}>{scene.on_screen_text.toUpperCase()}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── VOICEOVER TAB ── */}
      {activeTab === 'voiceover' && voiceover_script && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Meta row */}
          <div className="card">
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '20px' }}>
              {[
                { label: 'Tone', value: voiceover_script.tone, color: '#A78BFA' },
                { label: 'Pace', value: voiceover_script.pace, color: 'var(--accent-primary)' },
                { label: 'Words', value: voiceover_script.estimated_word_count, color: 'var(--accent-green)' },
                { label: 'Duration', value: `${voiceover_script.estimated_duration_sec}s`, color: 'var(--accent-gold)' },
              ].map(m => (
                <div key={m.label} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '10px', padding: '12px 18px', textAlign: 'center', minWidth: '80px' }}>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: m.color }}>{m.value}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '2px' }}>{m.label}</div>
                </div>
              ))}
            </div>

            {/* Full voiceover text */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>📜 Script</div>
              <button className="btn-secondary" style={{ fontSize: '12px', padding: '6px 14px' }}
                onClick={() => copyText(voiceover_script.voiceover_text, 'vo')}>
                {copied === 'vo' ? '✓ Copied!' : '📋 Copy'}
              </button>
            </div>
            <div style={{
              background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '20px',
              fontSize: '15px', lineHeight: '2', color: 'var(--text-primary)',
              border: '1px solid var(--border)', whiteSpace: 'pre-wrap',
            }}>
              {voiceover_script.key_emphasis_words?.length > 0
                ? voiceover_script.voiceover_text?.split(' ').map((word: string, i: number) => {
                    const clean = word.replace(/[^a-zA-Z]/g, '').toLowerCase();
                    const isEmphasis = voiceover_script.key_emphasis_words
                      ?.map((w: string) => w.toLowerCase())
                      .includes(clean);
                    return (
                      <span key={i} style={{
                        color: isEmphasis ? '#A78BFA' : 'inherit',
                        fontWeight: isEmphasis ? 700 : 'inherit',
                        textDecoration: isEmphasis ? 'underline' : 'none',
                        textDecorationColor: 'rgba(167,139,250,0.4)',
                      }}>{word} </span>
                    );
                  })
                : voiceover_script.voiceover_text
              }
            </div>

            {/* Speaker notes */}
            {voiceover_script.speaker_notes && (
              <div style={{ marginTop: '16px', background: 'rgba(255,184,0,0.06)', borderRadius: '10px', padding: '14px', border: '1px solid rgba(255,184,0,0.15)' }}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent-gold)', textTransform: 'uppercase', marginBottom: '6px' }}>🎭 Speaker Notes</div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.7 }}>{voiceover_script.speaker_notes}</div>
              </div>
            )}

            {/* Key emphasis */}
            {voiceover_script.key_emphasis_words?.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                  💡 Key Emphasis Words
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {voiceover_script.key_emphasis_words.map((w: string, i: number) => (
                    <span key={i} style={{
                      padding: '4px 12px', borderRadius: '12px', fontSize: '13px', fontWeight: 600,
                      background: 'rgba(167,139,250,0.12)', color: '#A78BFA',
                      border: '1px solid rgba(167,139,250,0.25)'
                    }}>{w}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Scene timecodes */}
          {voiceover_script.scene_timecodes?.length > 0 && (
            <div className="card">
              <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '14px' }}>⏱ Scene Timecodes</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {voiceover_script.scene_timecodes.map((tc: any, i: number) => (
                  <div key={i} style={{
                    display: 'flex', gap: '12px', alignItems: 'flex-start',
                    padding: '10px 14px', borderRadius: '8px', background: 'rgba(0,0,0,0.2)'
                  }}>
                    <div style={{
                      padding: '2px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 700,
                      background: 'rgba(167,139,250,0.15)', color: '#A78BFA', flexShrink: 0
                    }}>
                      {tc.start_sec}s – {tc.end_sec}s
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>Scene {tc.scene}: </span>
                      {tc.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── SOCIAL POSTS TAB ── */}
      {activeTab === 'social' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Platform selector */}
          <div style={{ display: 'flex', gap: '8px' }}>
            {socialPlatforms.map(p => (
              <button key={p} onClick={() => setActiveSocial(p)}
                style={{
                  padding: '10px 18px', borderRadius: '10px', border: '1px solid',
                  borderColor: activeSocial === p ? SOCIAL_COLORS[p] : 'var(--border)',
                  background: activeSocial === p ? `${SOCIAL_COLORS[p]}20` : 'transparent',
                  color: activeSocial === p ? SOCIAL_COLORS[p] : 'var(--text-secondary)',
                  fontWeight: 600, fontSize: '13px', cursor: 'pointer', transition: 'all 0.2s'
                }}>
                {SOCIAL_ICONS[p]} {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
          {activeSocial && social_posts[activeSocial] && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontFamily: 'Space Grotesk', fontSize: '17px', fontWeight: 700 }}>
                  {SOCIAL_ICONS[activeSocial]} {activeSocial.charAt(0).toUpperCase() + activeSocial.slice(1)} Post
                </h3>
                <button className="btn-secondary" style={{ fontSize: '12px', padding: '7px 14px' }}
                  onClick={() => copyText(social_posts[activeSocial].content, activeSocial)}>
                  {copied === activeSocial ? '✓ Copied!' : '📋 Copy'}
                </button>
              </div>
              <div style={{
                background: 'rgba(0,0,0,0.3)', borderRadius: '12px', padding: '20px',
                whiteSpace: 'pre-wrap', fontSize: '14px', lineHeight: '1.8',
                color: 'var(--text-primary)', border: '1px solid var(--border)'
              }}>
                {social_posts[activeSocial].content}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                {social_posts[activeSocial].hook && (
                  <div style={{ background: 'rgba(255,184,0,0.08)', borderRadius: '10px', padding: '12px', border: '1px solid rgba(255,184,0,0.2)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-gold)', textTransform: 'uppercase', marginBottom: '5px' }}>🎣 Hook</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>{social_posts[activeSocial].hook}</div>
                  </div>
                )}
                {social_posts[activeSocial].cta && (
                  <div style={{ background: 'rgba(0,229,160,0.08)', borderRadius: '10px', padding: '12px', border: '1px solid rgba(0,229,160,0.2)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-green)', textTransform: 'uppercase', marginBottom: '5px' }}>📣 CTA</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{social_posts[activeSocial].cta}</div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── HASHTAGS TAB ── */}
      {activeTab === 'hashtags' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {Object.keys(hashtags || {}).length === 0 && (
            <div className="card" style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
              No hashtags were generated for this project.
            </div>
          )}
          {Object.entries(hashtags || {}).map(([platform, tags]: [string, any]) => {
            const list: string[] = Array.isArray(tags) ? tags : [];
            const formatted = list.map(t => (t.startsWith('#') ? t : `#${t}`));
            const joined = formatted.join(' ');
            const key = `ht-${platform}`;
            return (
              <div key={platform} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ fontSize: '14px', fontWeight: 600 }}>
                    {SOCIAL_ICONS[platform]} {platform.charAt(0).toUpperCase() + platform.slice(1)} Hashtags
                    <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: '6px' }}>({formatted.length})</span>
                  </div>
                  {formatted.length > 0 && (
                    <button className="btn-secondary" style={{ fontSize: '12px', padding: '6px 14px' }}
                      onClick={() => copyText(joined, key)}>
                      {copied === key ? '✓ Copied!' : '📋 Copy All'}
                    </button>
                  )}
                </div>
                {formatted.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {formatted.map((tag: string, i: number) => (
                      <span key={i} onClick={() => copyText(tag, `${key}-${i}`)} title="Click to copy"
                        style={{
                          padding: '5px 14px', borderRadius: '20px', fontSize: '12px', fontWeight: 500,
                          background: 'rgba(0,212,255,0.08)', color: 'var(--accent-primary)',
                          border: '1px solid rgba(0,212,255,0.2)', cursor: 'pointer',
                        }}>{tag}</span>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No hashtags for this platform.</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── RESEARCH TAB ── */}
      {activeTab === 'research' && research && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '10px', padding: '10px 16px', textAlign: 'center' }}>
              <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--accent-primary)' }}>{research.headlines_found || 0}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Headlines</div>
            </div>
          </div>
          {research.summary && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>🔍 Research Summary</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>{research.summary}</div>
            </div>
          )}
          {research.headlines?.length > 0 && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>📰 Headlines Used</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {research.headlines.map((h: any, i: number) => (
                  <div key={i} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '10px 14px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '3px' }}>{h.title}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{h.source}</div>
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
