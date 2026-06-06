'use client';
import { useState } from 'react';

const DURATIONS = [15, 30, 45, 60, 90];

const ASPECT_RATIOS = [
  { id: '9:16', label: '9:16', desc: 'Reels / Shorts / TikTok', icon: '📱' },
  { id: '16:9', label: '16:9', desc: 'YouTube / LinkedIn / Facebook', icon: '🖥' },
  { id: '1:1',  label: '1:1',  desc: 'Square Social Posts', icon: '⬛' },
  { id: '4:5',  label: '4:5',  desc: 'Instagram Portrait', icon: '🔲' },
];

const SUGGESTED_TOPICS = [
  'AI Automation for Startups', 'Web3 & Blockchain Explained',
  'Cloud Migration in 2025', 'Mobile App Trends',
  'Machine Learning ROI', 'Cybersecurity for Business',
];

interface VideoFormProps {
  onGenerate: (data: any) => void;
  generating: boolean;
}

export default function VideoForm({ onGenerate, generating }: VideoFormProps) {
  const [topic, setTopic]                         = useState('');
  const [runResearch, setRunResearch]             = useState(true);
  const [duration, setDuration]                   = useState(45);
  const [aspectRatio, setAspectRatio]             = useState('9:16');
  const [article, setArticle]                     = useState('');
  const [productInfo, setProductInfo]             = useState('');
  const [customContent, setCustomContent]         = useState('');
  const [websiteUrl, setWebsiteUrl]               = useState('');
  const [blogUrl, setBlogUrl]                     = useState('');
  const [landingPageUrl, setLandingPageUrl]       = useState('');
  const [companyWebsiteUrl, setCompanyWebsiteUrl] = useState('');
  const [expanded, setExpanded]                   = useState<Record<string, boolean>>({});

  const toggleSection = (key: string) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  const hasUrls = websiteUrl || blogUrl || landingPageUrl || companyWebsiteUrl;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    onGenerate({
      topic: topic.trim(),
      run_research: runResearch,
      duration_sec: duration,
      aspect_ratio: aspectRatio,
      article,
      product_info: productInfo,
      custom_content: customContent,
      website_url: websiteUrl,
      blog_url: blogUrl,
      landing_page_url: landingPageUrl,
      company_website_url: companyWebsiteUrl,
    });
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Topic */}
      <div>
        <label style={labelStyle}>📌 Video Topic *</label>
        <input
          type="text" value={topic} onChange={e => setTopic(e.target.value)}
          placeholder="e.g. AI Automation for Startups..."
          className="input-field" required disabled={generating} id="video-topic-input"
          maxLength={1000}
        />
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', textAlign: 'right' }}>
          {topic.length}/1000 — long text? use Article &amp; Custom Content below
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '12px' }}>
          {SUGGESTED_TOPICS.map(s => (
            <button key={s} type="button" onClick={() => setTopic(s)} disabled={generating}
              style={{
                padding: '5px 12px', borderRadius: '20px', border: '1px solid var(--border)',
                background: topic === s ? 'rgba(123,94,167,0.15)' : 'transparent',
                color: topic === s ? '#A78BFA' : 'var(--text-muted)',
                fontSize: '12px', cursor: 'pointer', transition: 'all 0.2s',
                fontWeight: topic === s ? 600 : 400,
              }}>{s}</button>
          ))}
        </div>
      </div>

      {/* Duration */}
      <div>
        <label style={labelStyle}>⏱ Reel Duration</label>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {DURATIONS.map(d => (
            <button key={d} type="button" onClick={() => !generating && setDuration(d)} disabled={generating}
              style={{
                flex: 1, minWidth: '52px', padding: '10px 0', borderRadius: '10px',
                border: '1px solid',
                borderColor: duration === d ? '#A78BFA' : 'var(--border)',
                background: duration === d ? 'rgba(167,139,250,0.15)' : 'transparent',
                color: duration === d ? '#A78BFA' : 'var(--text-muted)',
                fontSize: '13px', fontWeight: duration === d ? 700 : 500,
                cursor: generating ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
              }}>{d}s</button>
          ))}
        </div>
      </div>

      {/* Aspect Ratio */}
      <div>
        <label style={labelStyle}>📐 Video Aspect Ratio</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
          {ASPECT_RATIOS.map(r => (
            <button key={r.id} type="button" onClick={() => !generating && setAspectRatio(r.id)} disabled={generating}
              style={{
                padding: '10px 12px', borderRadius: '10px', border: '1px solid',
                borderColor: aspectRatio === r.id ? '#A78BFA' : 'var(--border)',
                background: aspectRatio === r.id ? 'rgba(167,139,250,0.15)' : 'transparent',
                cursor: generating ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
                textAlign: 'left',
              }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '20px' }}>{r.icon}</span>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: aspectRatio === r.id ? '#A78BFA' : 'var(--text-primary)' }}>
                    {r.label}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{r.desc}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* URL Section */}
      <div style={sectionStyle()}>
        <button type="button" onClick={() => toggleSection('urls')} style={sectionToggleStyle(expanded['urls'])}>
          <span>🌐 Website URLs {hasUrls ? <span style={{ color: 'var(--accent-green)', fontSize: '11px' }}> ✓ Set</span> : <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}> (optional)</span>}</span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{expanded['urls'] ? '▲' : '▼'}</span>
        </button>
        {expanded['urls'] && (
          <div style={{ display: 'grid', gap: '10px', marginTop: '12px' }}>
            <UrlInput label="Website URL" placeholder="https://yourwebsite.com" value={websiteUrl} onChange={setWebsiteUrl} disabled={generating} />
            <UrlInput label="Company Website" placeholder="https://company.com" value={companyWebsiteUrl} onChange={setCompanyWebsiteUrl} disabled={generating} />
            <UrlInput label="Blog URL" placeholder="https://blog.yoursite.com" value={blogUrl} onChange={setBlogUrl} disabled={generating} />
            <UrlInput label="Landing Page URL" placeholder="https://yoursite.com/landing" value={landingPageUrl} onChange={setLandingPageUrl} disabled={generating} />
          </div>
        )}
      </div>

      {/* Content Section */}
      <div style={sectionStyle()}>
        <button type="button" onClick={() => toggleSection('content')} style={sectionToggleStyle(expanded['content'])}>
          <span>📄 Article & Custom Content <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>(optional)</span></span>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{expanded['content'] ? '▲' : '▼'}</span>
        </button>
        {expanded['content'] && (
          <div style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
            <div>
              <label style={subLabelStyle}>📰 Article / Blog Post</label>
              <textarea
                value={article} onChange={e => setArticle(e.target.value)} disabled={generating}
                placeholder="Paste article or blog post to base video content on..."
                className="input-field" rows={3}
                style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
              />
            </div>
            <div>
              <label style={subLabelStyle}>🛍 Product Information</label>
              <textarea
                value={productInfo} onChange={e => setProductInfo(e.target.value)} disabled={generating}
                placeholder="Product features, pricing, USPs..."
                className="input-field" rows={2}
                style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
              />
            </div>
            <div>
              <label style={subLabelStyle}>📝 Custom Notes</label>
              <textarea
                value={customContent} onChange={e => setCustomContent(e.target.value)} disabled={generating}
                placeholder="Tone, style, messaging instructions..."
                className="input-field" rows={2}
                style={{ resize: 'vertical', fontFamily: 'inherit', fontSize: '13px' }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Options */}
      <div onClick={() => !generating && setRunResearch(!runResearch)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 16px', borderRadius: '12px', border: '1px solid var(--border)',
          cursor: generating ? 'not-allowed' : 'pointer', transition: 'all 0.2s',
          background: 'rgba(0,0,0,0.2)',
        }}>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 500 }}>🔍 Run Research Agent</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Fetch latest news &amp; context to enrich content</div>
        </div>
        <div style={{
          width: '44px', height: '24px', borderRadius: '12px', transition: 'all 0.3s',
          background: runResearch ? 'var(--accent-primary)' : 'var(--bg-card-hover)',
          position: 'relative', flexShrink: 0,
        }}>
          <div style={{
            position: 'absolute', width: '18px', height: '18px', borderRadius: '50%',
            background: '#fff', top: '3px', transition: 'all 0.3s',
            left: runResearch ? '23px' : '3px',
          }} />
        </div>
      </div>

      {/* Pipeline Preview */}
      <div style={{
        background: 'rgba(123,94,167,0.06)', borderRadius: '12px',
        border: '1px solid rgba(123,94,167,0.2)', padding: '16px',
      }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#A78BFA', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          🔄 Pipeline Preview
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
          {['🌐 URL Research', '🔍 News Research', '✍️ Content', '#️⃣ Hashtags',
            '📝 Script', `🎨 Scene Images (${aspectRatio})`, '🎙️ Voiceover', '🎬 Motion Video', '💾 Database'
          ].map((step, i, arr) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>{step}</span>
              {i < arr.length - 1 && <span style={{ color: 'rgba(123,94,167,0.5)', fontSize: '12px' }}>→</span>}
            </div>
          ))}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>
          Output: Social Posts · Script · Voiceover MP3 · <strong style={{ color: '#A78BFA' }}>Final MP4 ({duration}s)</strong>
        </div>
      </div>

      <button
        type="submit" id="video-generate-btn" className="btn-primary"
        disabled={generating || !topic.trim()}
        style={{
          width: '100%', fontSize: '16px', padding: '16px',
          background: 'linear-gradient(135deg, #7B5EA7 0%, #A78BFA 100%)',
          boxShadow: '0 4px 20px rgba(123,94,167,0.4)',
        }}>
        {generating ? '⏳ Running Pipeline...' : `🎬 Generate ${duration}s Video (${aspectRatio})`}
      </button>
    </form>
  );
}

function UrlInput({ label, placeholder, value, onChange, disabled }: {
  label: string; placeholder: string; value: string;
  onChange: (v: string) => void; disabled: boolean;
}) {
  return (
    <div>
      <div style={subLabelStyle}>{label}</div>
      <input
        type="url" value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled} className="input-field"
        style={{ fontSize: '13px' }}
      />
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: '13px', fontWeight: 600,
  color: 'var(--text-muted)', textTransform: 'uppercase',
  letterSpacing: '0.5px', marginBottom: '10px',
};

const subLabelStyle: React.CSSProperties = {
  fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)',
  marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.3px',
};

function sectionStyle(): React.CSSProperties {
  return {
    border: '1px solid var(--border)', borderRadius: '12px', padding: '14px 16px',
    background: 'rgba(0,0,0,0.15)',
  };
}

function sectionToggleStyle(open: boolean): React.CSSProperties {
  return {
    width: '100%', background: 'none', border: 'none', cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    fontSize: '14px', fontWeight: 600, color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
    padding: 0, textAlign: 'left',
  };
}
